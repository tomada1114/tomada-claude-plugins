#!/usr/bin/env python3
"""neutrality_lint.py — Detect platform-specific (Claude-only) surface leaking into skill body text.

Usage:
    neutrality_lint.py <skill-path> [--json]

Scans SKILL.md + references/**/*.md + templates/**/*.md + assets/**/*.md for
raw Claude tool names, Claude/Codex namespace paths, and out-of-convention
state directories that should instead live behind a `references/platform-notes.md`
platform annex (see references/neutral-phrasing.md).

Checks:
    N1  raw Claude-only tool name in body text (AskUserQuestion, TodoWrite,
        subagent_type, Task(, Skill(, context: fork, run_in_background, /batch)
    N2  platform-namespaced path in body text (CLAUDE_PLUGIN_ROOT, ~/.claude/,
        $HOME/.claude/, ~/.codex/) — ${CLAUDE_SKILL_DIR} is exempt
    N3  out-of-convention persistent state path (~/.claude/<name>/ used as a
        write target, e.g. via mkdir/Write/appended-to record) instead of the
        ${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/<skill>/ convention
    N4  frontmatter missing metadata.platforms

Severity depends on frontmatter `metadata.platforms`:
    - "claude-code, codex" (or any value containing "codex")  -> N1-N3 are errors
    - "claude-code" only (no "codex")                          -> skip N1-N3 (declared Claude-only)
    - metadata.platforms absent                                -> N1-N3 are warnings, plus N4

Exemptions:
    - Any file whose first 5 lines contain `<!-- platform-annex -->` is skipped entirely
      (this is the one place tool names belong: references/platform-notes.md).
    - A line with a trailing `<!-- neutrality-ignore: N00X -->` suppresses that code on that line.
    - Frontmatter block (between the leading `---` pair) is exempt from N1/N2 — Claude-only
      frontmatter fields like `allowed-tools: ... AskUserQuestion` are fine (Codex ignores them).

Exit codes: 0 = no errors (warnings ok), 1 = errors, 2 = bad invocation
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

TOOL_RE = re.compile(
    r"\bAskUserQuestion\b|\bTodoWrite\b|\bsubagent_type\b|\bTask\s*\(|\bSkill\s*\("
    r"|context:\s*fork|\brun_in_background\b|(?<!\w)/batch\b"
)
PLATFORM_PATH_RE = re.compile(
    r"CLAUDE_PLUGIN_ROOT|(?<!\$\{CLAUDE_SKILL_DIR\})(?:~|\$HOME)/\.claude/|~/\.codex/"
)
STATE_WRITE_RE = re.compile(
    r"(?:mkdir(?:\s+-p)?|write_text|Write\(|appended?)[^\n]*(?:~|\$HOME)/\.claude/(?!skills/|agents/|commands/|hooks/)"
)
IGNORE_LINE_RE = re.compile(r"<!--\s*neutrality-ignore:\s*(N\d+)\s*-->")
ANNEX_MARK = "<!-- platform-annex -->"


@dataclass
class Finding:
    level: str
    code: str
    file: str
    line: int
    message: str


@dataclass
class Report:
    skill_path: str
    skill_name: str = ""
    platforms: str = ""
    findings: list = field(default_factory=list)

    def add(self, level: str, code: str, file: str, line: int, msg: str) -> None:
        self.findings.append(Finding(level, code, file, line, msg))

    @property
    def errors(self):
        return [f for f in self.findings if f.level == "error"]


def parse_frontmatter(text: str) -> tuple[dict, int]:
    """Return (flat key->value dict incl. dotted metadata.* keys, body_start_index)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0
    vals: dict[str, str] = {}
    end = -1
    in_metadata = False
    for i in range(1, len(lines)):
        raw = lines[i]
        if raw.strip() == "---":
            end = i
            break
        if not raw.startswith((" ", "\t")):
            in_metadata = raw.strip().startswith("metadata:")
            if ":" in raw:
                k, v = raw.split(":", 1)
                vals[k.strip()] = v.strip().strip("\"'")
        elif in_metadata and ":" in raw:
            k, v = raw.strip().split(":", 1)
            vals[f"metadata.{k.strip()}"] = v.strip().strip("\"'")
    return vals, (end + 1 if end != -1 else 0)


def is_annex(text: str) -> bool:
    return ANNEX_MARK in "\n".join(text.splitlines()[:5])


def lint_file(path: Path, body_only_from: int, severity_n1_n3: str) -> list[Finding]:
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8")
    if is_annex(text):
        return findings
    lines = text.splitlines()
    for i, line in enumerate(lines[body_only_from:], start=body_only_from + 1):
        ignored_codes = set(IGNORE_LINE_RE.findall(line))
        if severity_n1_n3:
            for m in TOOL_RE.finditer(line):
                if "N1" in ignored_codes:
                    continue
                findings.append(Finding(severity_n1_n3, "N1", str(path), i,
                                         f"raw platform-specific construct in body: {m.group(0)!r}"))
            for m in PLATFORM_PATH_RE.finditer(line):
                if "N2" in ignored_codes:
                    continue
                findings.append(Finding(severity_n1_n3, "N2", str(path), i,
                                         f"platform-namespaced path in body: {m.group(0)!r}"))
            if STATE_WRITE_RE.search(line) and "N3" not in ignored_codes:
                findings.append(Finding(severity_n1_n3, "N3", str(path), i,
                                         "writes into ~/.claude/<name>/ instead of the "
                                         "${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/<skill>/ convention"))
    return findings


def lint(skill_path: Path) -> Report:
    r = Report(skill_path=str(skill_path))
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        r.add("error", "N0", str(skill_md), 0, "SKILL.md not found")
        return r
    fm_text = skill_md.read_text(encoding="utf-8")
    vals, body_start = parse_frontmatter(fm_text)
    r.skill_name = vals.get("name", skill_path.name)
    platforms = vals.get("metadata.platforms", "")
    r.platforms = platforms

    if not platforms:
        severity = "warning"
        r.add("warning", "N4", str(skill_md), 1, "frontmatter missing metadata.platforms")
    elif "codex" in platforms.lower():
        severity = "error"
    else:
        severity = ""  # declared claude-code only -> skip N1-N3

    # SKILL.md body (skip frontmatter block for N1/N2/N3)
    r.findings.extend(lint_file(skill_md, body_start, severity))

    # references/, templates/, assets/ — full file (no frontmatter to skip)
    for sub in ("references", "templates", "assets"):
        d = skill_path / sub
        if d.is_dir():
            for f in sorted(d.rglob("*.md")):
                r.findings.extend(lint_file(f, 0, severity))

    return r


def render_human(r: Report) -> str:
    out = [f"Neutrality lint: {r.skill_name}  ({r.skill_path})",
           f"  metadata.platforms: {r.platforms or '(none)'}"]
    if not r.findings:
        out.append("  OK — no issues.")
        return "\n".join(out)
    for lvl in ("error", "warning", "info"):
        items = [f for f in r.findings if f.level == lvl]
        if items:
            out.append(f"  {lvl.upper()}S:")
            for f in items:
                rel = Path(f.file)
                try:
                    rel = rel.relative_to(Path(r.skill_path))
                except ValueError:
                    pass
                out.append(f"    {f.code} {rel}:{f.line}: {f.message}")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__, file=sys.stderr)
        return 2
    skill_path = Path(argv[1]).expanduser().resolve()
    if not skill_path.is_dir():
        print(f"Error: not a directory: {skill_path}", file=sys.stderr)
        return 2
    r = lint(skill_path)
    if "--json" in argv[2:]:
        print(json.dumps(asdict(r), indent=2, ensure_ascii=False))
    else:
        print(render_human(r))
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
