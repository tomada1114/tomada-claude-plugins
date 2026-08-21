#!/usr/bin/env python3
"""classify_skill.py — Scan a skill and report platform-specific constructs + a dual-platform Tier.

Usage:
    classify_skill.py <skill-path> [--json]

Scans SKILL.md + references/**/*.md + templates/**/*.md for Claude-Code-specific
constructs that block or complicate running the same skill under OpenAI Codex CLI,
then assigns a Tier. `construct_locations` in the output gives file:line detail for
every hit (used by skill-analyzer to plan edits outside SKILL.md, not just inside it):

    A = trivially dual-platform (only name/description-ish; no orchestration)
    B = medium (extra frontmatter / AskUserQuestion / MCP / hardcoded paths / single subagent)
    C = hard (Task fan-out / cross-skill Skill calls / tmux / /batch / context:fork)

Output: human-readable by default, machine-readable with --json.

Exit codes:
    0 = scanned ok (any tier)
    2 = bad invocation / skill not found
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Frontmatter fields that are Claude-Code-only (Codex reads only name/description/metadata).
CLAUDE_FM_FIELDS = {
    "allowed-tools", "disallowed-tools", "argument-hint", "arguments", "model",
    "effort", "context", "agent", "hooks", "paths", "shell",
    "disable-model-invocation", "user-invocable", "when_to_use",
}

# Body patterns. Each maps a label -> compiled regex.
# task_orchestration is intentionally STRICT: the bare word "task" / a passing
# mention of "サブエージェント" is not enough — require an actual Task-tool call.
PATTERNS = {
    "task_orchestration": re.compile(
        r"subagent_type|Task\s*(?:tool|ツール|sub-?agent|サブエージェント|\()", re.IGNORECASE),
    "skill_cross_call": re.compile(r"\bSkill\s*tool\b|Skill\(|内部呼び出し|内部で.*呼び出", re.IGNORECASE),
    "ask_user_question": re.compile(r"AskUserQuestion"),
    "mcp_tools": re.compile(r"mcp__[a-zA-Z0-9_]+"),
    "tmux": re.compile(r"\btmux\b", re.IGNORECASE),
    "batch_command": re.compile(r"(?<!\w)/batch\b"),
    "context_fork": re.compile(r"context:\s*fork"),
    "plan_mode": re.compile(r"plan mode|ExitPlanMode|EnterPlanMode|プランモード", re.IGNORECASE),
    "hardcoded_claude_path": re.compile(r"\.claude/(skills|agents|commands)/"),
}

SUBAGENT_TYPE_RE = re.compile(r"""subagent_type\s*[=:]\s*["']?([a-z0-9][a-z0-9-]*)["']?""", re.IGNORECASE)
CLAUDE_AGENT_REF_RE = re.compile(r"\.claude/agents/([A-Za-z0-9_\-/]+?)(?:\.md)?\b")
CLAUDE_SKILL_REF_RE = re.compile(r"\.claude/skills/([a-z0-9][a-z0-9-]*)/")


@dataclass
class Classification:
    skill_path: str
    skill_name: str = ""
    tier: str = "A"
    claude_frontmatter_fields: list[str] = field(default_factory=list)
    constructs: dict[str, int] = field(default_factory=dict)
    construct_locations: list[dict] = field(default_factory=list)
    dependent_subagents: list[str] = field(default_factory=list)
    cross_skill_refs: list[str] = field(default_factory=list)
    references_files: int = 0
    scripts_files: int = 0
    notes: list[str] = field(default_factory=list)


def _claude_root(skill_path: Path) -> Path | None:
    for parent in skill_path.parents:
        if parent.name == ".claude":
            return parent
    return None


def agent_registry(skill_path: Path) -> dict[str, str]:
    """Map subagent name stem -> defining file path.

    Sources (broadest-first):
      - ~/.claude/agents (user)
      - <repo>/.claude/agents (project)
      - <repo>/.claude/skills/*/agents (skill-LOCAL subagents — the per-skill
        `agents/` convention; the 5 cc-book evaluators live here, NOT in .claude/agents)
    """
    reg: dict[str, str] = {}
    dirs: list[Path] = [Path.home() / ".claude" / "agents"]
    root = _claude_root(skill_path)
    if root is not None:
        dirs.append(root / "agents")
        skills_dir = root / "skills"
        if skills_dir.is_dir():
            for sk in skills_dir.iterdir():
                if (sk / "agents").is_dir():
                    dirs.append(sk / "agents")
    for d in dirs:
        if d.is_dir():
            for f in d.rglob("*.md"):
                reg.setdefault(f.stem.lower(), str(f))
    return reg


def skill_registry(skill_path: Path) -> set[str]:
    """Names of sibling skills (same .claude/skills tree) + user ~/.claude/skills."""  # scripts-ignore: S006
    names: set[str] = set()
    dirs: list[Path] = [Path.home() / ".claude" / "skills"]
    root = _claude_root(skill_path)
    if root is not None:
        dirs.append(root / "skills")
    for d in dirs:
        if d.is_dir():
            for sk in d.iterdir():
                if (sk / "SKILL.md").exists():
                    names.add(sk.name.lower())
    return names


def parse_frontmatter_keys(text: str) -> tuple[list[str], str, int]:
    """Return (top-level frontmatter keys, name value, body_start_index)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], "", 0
    keys: list[str] = []
    name = ""
    end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
        line = lines[i]
        if not line.startswith((" ", "\t")) and ":" in line:
            key = line.split(":", 1)[0].strip()
            if key and not key.startswith("#"):
                keys.append(key)
                if key == "name":
                    name = line.split(":", 1)[1].strip().strip("\"'")
    body_start = end + 1 if end != -1 else 0
    return keys, name, body_start


def classify(skill_path: Path) -> Classification:
    c = Classification(skill_path=str(skill_path))
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        c.notes.append("SKILL.md not found")
        return c
    text = skill_md.read_text(encoding="utf-8")
    keys, name, body_start = parse_frontmatter_keys(text)
    c.skill_name = name or skill_path.name
    c.claude_frontmatter_fields = [k for k in keys if k in CLAUDE_FM_FIELDS]
    body = "\n".join(text.splitlines()[body_start:])

    # Count construct hits across SKILL.md body + references/**/*.md + templates/**/*.md.
    # SKILL.md line numbers account for the frontmatter offset; other files count from their own line 1.
    def _scan(label_text: str, line_offset: int, file_label: str) -> None:
        lines = label_text.splitlines()
        for label, rx in PATTERNS.items():
            for i, line in enumerate(lines, start=1 + line_offset):
                for m in rx.finditer(line):
                    c.constructs[label] = c.constructs.get(label, 0) + 1
                    c.construct_locations.append({
                        "label": label, "file": file_label, "line": i, "match": m.group(0),
                    })

    _scan(body, body_start, "SKILL.md")
    for sub in ("references", "templates"):
        d = skill_path / sub
        if d.is_dir():
            for f in sorted(d.rglob("*.md")):
                _scan(f.read_text(encoding="utf-8"), 0, str(f.relative_to(skill_path)))

    # Combined text for subagent/cross-skill detection: SKILL.md (full, incl. frontmatter,
    # matching prior behavior for CLAUDE_AGENT_REF_RE/CLAUDE_SKILL_REF_RE) + references/templates.
    extra_text_parts = []
    for sub in ("references", "templates"):
        d = skill_path / sub
        if d.is_dir():
            for f in sorted(d.rglob("*.md")):
                extra_text_parts.append(f.read_text(encoding="utf-8"))
    all_text = text + "\n" + "\n".join(extra_text_parts)
    all_body_lowered = (body + "\n" + "\n".join(extra_text_parts)).lower()

    # Dependent subagents: subagent_type values + .claude/agents references +
    # registry name matches (agent names from .claude/agents that appear anywhere in the skill).
    deps: set[str] = set()
    for m in SUBAGENT_TYPE_RE.finditer(all_body_lowered):
        deps.add(m.group(1).lower())
    for m in CLAUDE_AGENT_REF_RE.finditer(all_text):
        deps.add(m.group(1).split("/")[-1].lower())
    a_reg = agent_registry(skill_path)
    for agent_name in a_reg:
        if len(agent_name) >= 5 and re.search(rf"(?<![a-z0-9-]){re.escape(agent_name)}(?![a-z0-9-])", all_body_lowered):
            deps.add(agent_name)
    c.dependent_subagents = sorted(deps)

    # Cross-skill references: (a) explicit .claude/skills/<name>/ paths, AND
    # (b) sibling/user skill NAMES that appear anywhere in the skill (catches Skill-tool / /name calls).
    cross: set[str] = set()
    for m in CLAUDE_SKILL_REF_RE.finditer(all_text):
        if m.group(1) != c.skill_name:
            cross.add(m.group(1))
    for sk_name in skill_registry(skill_path):
        if sk_name != c.skill_name and len(sk_name) >= 5 and \
                re.search(rf"(?<![a-z0-9-]){re.escape(sk_name)}(?![a-z0-9-])", all_body_lowered):
            cross.add(sk_name)
    c.cross_skill_refs = sorted(cross)

    # Resource inventory (shared-core candidates).
    refs = skill_path / "references"
    scr = skill_path / "scripts"
    c.references_files = sum(1 for _ in refs.rglob("*") if _.is_file()) if refs.is_dir() else 0
    c.scripts_files = sum(1 for _ in scr.rglob("*") if _.is_file()) if scr.is_dir() else 0

    # Tier assignment.
    # HARD (C): genuine multi-agent fan-out or cross-skill/host orchestration that
    # has no Codex equivalent and needs real redesign.
    hard = any(k in c.constructs for k in ("task_orchestration", "tmux", "batch_command", "skill_cross_call")) \
        or bool(c.cross_skill_refs)
    # MEDIUM (B): Claude-specific surface that degrades cleanly (strip/inline), incl.
    # context:fork (just run inline under Codex), AskUserQuestion, MCP, hardcoded paths.
    medium = bool(c.claude_frontmatter_fields) or bool(c.dependent_subagents) or c.references_files > 0 \
        or any(k in c.constructs for k in
               ("ask_user_question", "mcp_tools", "plan_mode", "hardcoded_claude_path", "context_fork"))
    if hard:
        c.tier = "C"
    elif medium:
        c.tier = "B"
    else:
        c.tier = "A"
    return c


def render_human(c: Classification) -> str:
    out = [
        f"Skill: {c.skill_name}  ({c.skill_path})",
        f"  Tier: {c.tier}",
    ]
    if c.claude_frontmatter_fields:
        out.append(f"  Claude-only frontmatter: {', '.join(c.claude_frontmatter_fields)}")
    if c.constructs:
        out.append("  Constructs: " + ", ".join(f"{k}×{v}" for k, v in sorted(c.constructs.items())))
    if c.dependent_subagents:
        out.append(f"  Dependent subagents: {', '.join(c.dependent_subagents)}")
    if c.cross_skill_refs:
        out.append(f"  Cross-skill refs: {', '.join(c.cross_skill_refs)}")
    out.append(f"  Resources: references={c.references_files} files, scripts={c.scripts_files} files")
    if c.notes:
        out.append("  Notes: " + "; ".join(c.notes))
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__, file=sys.stderr)
        return 2
    skill_path = Path(argv[1]).expanduser().resolve()
    if not skill_path.is_dir():
        print(f"Error: not a directory: {skill_path}", file=sys.stderr)
        return 2
    c = classify(skill_path)
    if "--json" in argv[2:]:
        print(json.dumps(asdict(c), indent=2, ensure_ascii=False))
    else:
        print(render_human(c))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
