#!/usr/bin/env python3
"""Collect the deterministic facts a prompt-estate rethink starts from.

Inventories skills, commands, agent definitions and memory files under a configuration
root, builds the reference graph between them, lists tier and model mentions,
and counts skill invocations in session transcripts. Reads only; writes nothing.

Usage:
    collect_estate.py <root> [--json] [--transcripts DIR] [--memory FILE ...]
                      [--scratch-pattern REGEX]

Exit codes: 0 = estate printed, 2 = bad invocation (root holds no assets).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

MEMORY_NAMES = ("CLAUDE.md", "AGENTS.md")
# Transcript directories whose sessions are experiments, not real use: scratch
# and eval runs would otherwise dominate the counts.
DEFAULT_SCRATCH_PATTERN = r"scratchpad|^-private-tmp|-tmp-|eval-runs"
MODEL_RE = re.compile(
    r"\b(?:opus|sonnet|haiku|fable|mythos)\b|\bmodel:\s*\S+|\beffort:\s*\S+|\bxhigh\b",
    re.IGNORECASE,
)
# A subject-of-models skill mentions models hundreds of times; the count says
# so, and a sample is enough to locate the rest.
MODEL_MENTION_SAMPLE = 20
MENTION_TEXT_WIDTH = 160
COMMAND_RE = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
SKILL_CALL_MARKERS = (b'"name":"Skill"', b'"name": "Skill"')
COMMAND_MARKER = b"<command-name>"
UNKNOWN_INVOCATIONS_TOP = 40
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")
NESTED_KEY_RE = re.compile(r"^\s+([A-Za-z_][\w-]*):\s*(.*)$")
BLOCK_SCALARS = {">", ">-", ">+", "|", "|-", "|+"}


@dataclass
class Mention:
    file: str
    line: int
    text: str


@dataclass
class Usage:
    user: int = 0
    model: int = 0
    sidechain: int = 0
    scratch: int = 0
    projects: list[str] = field(default_factory=list)
    last_used: str | None = None


@dataclass
class Skill:
    name: str
    path: str
    symlink: bool
    has_description: bool
    description_chars: int
    user_only: bool
    model_only: bool
    platforms: str
    body_lines: int
    reference_files: int
    reference_lines: int
    has_scripts: bool
    mentions: list[str] = field(default_factory=list)
    mentioned_by: list[str] = field(default_factory=list)
    tier_mentions: list[Mention] = field(default_factory=list)
    model_mention_count: int = 0
    model_mentions: list[Mention] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)


@dataclass
class Agent:
    name: str
    path: str
    model: str
    effort: str
    lines: int


@dataclass
class Command:
    name: str
    path: str
    lines: int
    usage: Usage = field(default_factory=Usage)


@dataclass
class MemoryFile:
    path: str
    lines: int
    mentions: list[str] = field(default_factory=list)
    model_mention_count: int = 0


@dataclass
class UsageWindow:
    scanned: bool = False
    files: int = 0
    first: str | None = None
    last: str | None = None


@dataclass
class Estate:
    root: str
    skills: list[Skill] = field(default_factory=list)
    agents: list[Agent] = field(default_factory=list)
    commands: list[Command] = field(default_factory=list)
    memory_files: list[MemoryFile] = field(default_factory=list)
    non_skill_dirs: list[str] = field(default_factory=list)
    listing: dict = field(default_factory=dict)
    usage_window: UsageWindow = field(default_factory=UsageWindow)
    unknown_invocations: list[dict] = field(default_factory=list)
    signals: dict = field(default_factory=dict)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter, body). Handles scalars, block scalars and one nesting level."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, text
    data: dict = {}
    key: str | None = None
    block: list[str] | None = None
    for raw in lines[1:end]:
        top = TOP_LEVEL_KEY_RE.match(raw)
        if top:
            if key is not None and block is not None:
                data[key] = " ".join(block)
            key, value = top.group(1), top.group(2).strip()
            if value in BLOCK_SCALARS:
                block = []
            elif value == "" or value.startswith("#"):
                block = None
                data[key] = {}
            else:
                block = None
                data[key] = _unquote(value)
            continue
        if key is None or not raw.strip():
            continue
        if block is not None:
            block.append(raw.strip())
            continue
        nested = NESTED_KEY_RE.match(raw)
        if nested and isinstance(data.get(key), dict):
            data[key][nested.group(1)] = _unquote(nested.group(2).split(" #")[0].strip())
    if key is not None and block is not None:
        data[key] = " ".join(block)
    return data, "\n".join(lines[end + 1:])


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _is_true(value: object) -> bool:
    return str(value).strip().lower() == "true"


def _name_re(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w-]){re.escape(name)}(?![\w-])")


def _markdown_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*.md") if p.is_file())


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _mention(file: str, number: int, line: str) -> Mention:
    return Mention(file, number, line.strip()[:MENTION_TEXT_WIDTH])


def scan_text(
    rel: str, text: str, tier_res: dict[str, re.Pattern[str]]
) -> tuple[list[Mention], list[Mention]]:
    """Return (tier mentions, model mentions) for one file's text."""
    tiers: list[Mention] = []
    models: list[Mention] = []
    for number, line in enumerate(text.splitlines(), 1):
        if any(pattern.search(line) for pattern in tier_res.values()):
            tiers.append(_mention(rel, number, line))
        if MODEL_RE.search(line):
            models.append(_mention(rel, number, line))
    return tiers, models


def collect_agents(root: Path) -> list[Agent]:
    agents = []
    for path in sorted((root / "agents").glob("*.md")) if (root / "agents").is_dir() else []:
        text = _read(path)
        meta, _ = parse_frontmatter(text)
        agents.append(Agent(
            name=str(meta.get("name") or path.stem),
            path=str(path),
            model=str(meta.get("model", "")),
            effort=str(meta.get("effort", "")),
            lines=len(text.splitlines()),
        ))
    return agents


def collect_commands(root: Path) -> list[Command]:
    directory = root / "commands"
    return [
        Command(name=path.stem, path=str(path), lines=len(_read(path).splitlines()))
        for path in (sorted(directory.glob("*.md")) if directory.is_dir() else [])
    ]


def collect_skills(root: Path, agent_names: list[str]) -> tuple[list[Skill], dict[str, str], list[str]]:
    """Return (skills, {skill name: all of its markdown text}, non-skill dirs)."""
    skills: list[Skill] = []
    texts: dict[str, str] = {}
    strays: list[str] = []
    skills_dir = root / "skills"
    tier_res = {name: _name_re(name) for name in agent_names}
    for directory in sorted(skills_dir.iterdir()) if skills_dir.is_dir() else []:
        if directory.name.startswith(".") or not (directory.is_dir() or directory.is_symlink()):
            continue
        skill_md = directory / "SKILL.md"
        if not skill_md.is_file():
            # A directory without SKILL.md, or a symlink whose target is gone:
            # either way nothing is listed for it.
            strays.append(directory.name)
            continue
        meta, body = parse_frontmatter(_read(skill_md))
        description = meta.get("description", "")
        description = description if isinstance(description, str) else ""
        metadata = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
        skill = Skill(
            name=directory.name,
            path=str(directory),
            symlink=directory.is_symlink(),
            has_description=bool(description.strip()),
            description_chars=len(description) + len(str(meta.get("when_to_use", ""))),
            user_only=_is_true(meta.get("disable-model-invocation", "")),
            model_only=str(meta.get("user-invocable", "")).strip().lower() == "false",
            platforms=str(metadata.get("platforms", "")),
            body_lines=len(body.splitlines()),
            reference_files=0,
            reference_lines=0,
            has_scripts=(directory / "scripts").is_dir(),
        )
        chunks = []
        for path in _markdown_files(directory):
            text = _read(path)
            rel = str(path.relative_to(directory))
            chunks.append(text)
            if path != skill_md:
                skill.reference_files += 1
                skill.reference_lines += len(text.splitlines())
            tiers, models = scan_text(rel, text, tier_res)
            skill.tier_mentions.extend(tiers)
            skill.model_mention_count += len(models)
            room = MODEL_MENTION_SAMPLE - len(skill.model_mentions)
            skill.model_mentions.extend(models[:max(room, 0)])
        texts[skill.name] = "\n".join(chunks)
        skills.append(skill)
    return skills, texts, strays


def collect_memory(root: Path, extra: list[Path]) -> tuple[list[MemoryFile], dict[str, str]]:
    files: list[MemoryFile] = []
    texts: dict[str, str] = {}
    candidates = [root / name for name in MEMORY_NAMES] + extra
    for path in candidates:
        if not path.is_file():
            continue
        text = _read(path)
        label = path.name if path.parent == root else str(path)
        files.append(MemoryFile(
            path=str(path),
            lines=len(text.splitlines()),
            model_mention_count=sum(1 for line in text.splitlines() if MODEL_RE.search(line)),
        ))
        texts[label] = text
    return files, texts


def link_references(
    skills: list[Skill], skill_texts: dict[str, str],
    memory: list[MemoryFile], memory_texts: dict[str, str],
) -> None:
    """Fill mentions / mentioned_by from name occurrences in each asset's text."""
    by_name = {skill.name: skill for skill in skills}
    patterns = {name: _name_re(name) for name in by_name}
    for source in skills:
        for name, pattern in patterns.items():
            if name != source.name and pattern.search(skill_texts[source.name]):
                source.mentions.append(name)
                by_name[name].mentioned_by.append(source.name)
    for memory_file, (label, text) in zip(memory, memory_texts.items()):
        for name, pattern in patterns.items():
            if pattern.search(text):
                memory_file.mentions.append(name)
                by_name[name].mentioned_by.append(label)


def invocations_in_line(raw: bytes) -> list[tuple[str, str, str]]:
    """Return [(skill name, kind, timestamp)] for one transcript line.

    kind is "user" (typed as a command) or "model" (loaded by a tool call).
    """
    if COMMAND_MARKER not in raw and not any(marker in raw for marker in SKILL_CALL_MARKERS):
        return []
    try:
        entry = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(entry, dict) or not isinstance(entry.get("message"), dict):
        return []
    stamp = str(entry.get("timestamp") or "")
    content = entry["message"].get("content")
    blocks = content if isinstance(content, list) else [{"type": "text", "text": content}]
    found: list[tuple[str, str, str]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if entry.get("type") == "user" and block.get("type") == "text":
            # A typed command opens the entry; a quoted tag deeper in pasted
            # text is not an invocation.
            match = COMMAND_RE.search(str(block.get("text") or "")[:400])
            if match:
                found.append((match.group(1), "user", stamp))
        elif entry.get("type") == "assistant" and block.get("type") == "tool_use":
            name = (block.get("input") or {}).get("skill")
            if block.get("name") == "Skill" and isinstance(name, str):
                found.append((name.lstrip("/"), "sidechain" if entry.get("isSidechain") else "model", stamp))
    return found


def scan_transcripts(
    transcripts: Path, targets: dict[str, Usage], scratch_re: re.Pattern[str]
) -> tuple[UsageWindow, list[dict]]:
    """Count invocations of each named target (a skill or a command) into its Usage."""
    by_name = targets
    projects: dict[str, set[str]] = {name: set() for name in by_name}
    unknown: dict[str, int] = {}
    window = UsageWindow(scanned=True)
    for path in sorted(transcripts.rglob("*.jsonl")):
        window.files += 1
        relative = path.relative_to(transcripts)
        project = relative.parts[0]
        scratch = bool(scratch_re.search(project))
        in_subagent_dir = "subagents" in relative.parts
        with path.open("rb") as handle:
            for raw in handle:
                for name, kind, stamp in invocations_in_line(raw):
                    if stamp:
                        window.first = min(window.first or stamp, stamp)
                        window.last = max(window.last or stamp, stamp)
                    usage = by_name.get(name)
                    if usage is None:
                        if not scratch:
                            unknown[name] = unknown.get(name, 0) + 1
                        continue
                    if scratch:
                        usage.scratch += 1
                        continue
                    if kind == "model" and in_subagent_dir:
                        kind = "sidechain"
                    setattr(usage, kind, getattr(usage, kind) + 1)
                    projects[name].add(project)
                    if stamp and stamp > (usage.last_used or ""):
                        usage.last_used = stamp
    for name, usage in by_name.items():
        usage.projects = sorted(projects[name])
    ranked = sorted(unknown.items(), key=lambda item: (-item[1], item[0]))
    return window, [{"name": n, "count": c} for n, c in ranked[:UNKNOWN_INVOCATIONS_TOP]]


def derive_signals(estate: Estate) -> dict:
    """Name the assets each cross-cutting check should look at first. Hints, not verdicts."""
    scanned = estate.usage_window.scanned
    direct = lambda s: s.usage.user + s.usage.model + s.usage.sidechain  # noqa: E731
    return {
        "no_description": sorted(s.name for s in estate.skills if not s.has_description),
        "user_only": sorted(s.name for s in estate.skills if s.user_only),
        "no_evidence_of_use": sorted(
            s.name for s in estate.skills if scanned and direct(s) == 0 and not s.mentioned_by
        ),
        "reached_only_through_other_assets": sorted(
            s.name for s in estate.skills if scanned and direct(s) == 0 and s.mentioned_by
        ),
        "never_model_invoked": sorted(
            s.name for s in estate.skills
            if scanned and s.usage.user > 0 and s.usage.model + s.usage.sidechain == 0
        ),
        "names_models_but_no_tier": sorted(
            s.name for s in estate.skills if s.model_mention_count and not s.tier_mentions
        ),
        "delegates": sorted(s.name for s in estate.skills if s.tier_mentions),
    }


def collect(
    root: Path, transcripts: Path | None = None,
    memory: list[Path] | None = None, scratch_pattern: str = DEFAULT_SCRATCH_PATTERN,
) -> Estate:
    estate = Estate(root=str(root))
    estate.agents = collect_agents(root)
    estate.commands = collect_commands(root)
    estate.skills, skill_texts, estate.non_skill_dirs = collect_skills(
        root, [agent.name for agent in estate.agents]
    )
    estate.memory_files, memory_texts = collect_memory(root, memory or [])
    link_references(estate.skills, skill_texts, estate.memory_files, memory_texts)
    estate.listing = {
        "skills": len(estate.skills),
        "description_chars_total": sum(s.description_chars for s in estate.skills),
        "longest_descriptions": [
            {"name": s.name, "chars": s.description_chars}
            for s in sorted(estate.skills, key=lambda s: -s.description_chars)[:5]
        ],
    }
    if transcripts is not None:
        # A skill wins over a command of the same name, as it does in Claude Code.
        targets = {command.name: command.usage for command in estate.commands}
        targets.update({skill.name: skill.usage for skill in estate.skills})
        estate.usage_window, estate.unknown_invocations = scan_transcripts(
            transcripts, targets, re.compile(scratch_pattern)
        )
    estate.signals = derive_signals(estate)
    return estate


def render_text(estate: Estate) -> str:
    window = estate.usage_window
    lines = [
        f"root: {estate.root}",
        f"skills: {len(estate.skills)}  agents: {len(estate.agents)}  "
        f"commands: {len(estate.commands)}  memory files: {len(estate.memory_files)}",
        f"listing: {estate.listing['description_chars_total']} description chars",
    ]
    if window.scanned:
        lines.append(f"usage window: {window.first} .. {window.last} ({window.files} transcripts)")
    else:
        lines.append("usage: not scanned (pass --transcripts)")
    lines.append("")
    lines.append(f"{'skill':<36}{'user':>5}{'model':>6}{'sub':>5}{'in':>4}{'out':>4}{'lines':>7}")
    for s in estate.skills:
        lines.append(
            f"{s.name:<36}{s.usage.user:>5}{s.usage.model:>6}{s.usage.sidechain:>5}"
            f"{len(s.mentioned_by):>4}{len(s.mentions):>4}{s.body_lines + s.reference_lines:>7}"
        )
    lines.append("")
    for key, names in estate.signals.items():
        lines.append(f"{key}: {', '.join(names) if names else '-'}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inventory skills, agents and memory files under a configuration "
        "root, with their reference graph, tier/model mentions and transcript usage."
    )
    parser.add_argument("root", type=Path, help="directory holding skills/, agents/, CLAUDE.md, AGENTS.md")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--transcripts", type=Path, help="directory of session transcripts (*.jsonl, walked recursively)")
    parser.add_argument("--memory", type=Path, action="append", default=[], help="an extra memory file to include (repeatable)")
    parser.add_argument("--scratch-pattern", default=DEFAULT_SCRATCH_PATTERN, help="regex on a transcript project directory name; matches are counted apart as scratch")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.expanduser()
    has_assets = any((root / name).is_dir() for name in ("skills", "agents", "commands")) or any(
        (root / name).is_file() for name in MEMORY_NAMES
    )
    if not has_assets:
        print(
            f"error: {root} holds no skills/, agents/, CLAUDE.md or AGENTS.md. "
            "Pass the configuration root itself (for a repository, its .claude or .agents directory).",
            file=sys.stderr,
        )
        return 2
    if args.transcripts is not None and not args.transcripts.expanduser().is_dir():
        print(f"error: --transcripts {args.transcripts} is not a directory.", file=sys.stderr)
        return 2
    try:
        re.compile(args.scratch_pattern)
    except re.error as exc:
        print(f"error: --scratch-pattern is not a valid regex: {exc}", file=sys.stderr)
        return 2
    estate = collect(
        root,
        transcripts=args.transcripts.expanduser() if args.transcripts else None,
        memory=[path.expanduser() for path in args.memory],
        scratch_pattern=args.scratch_pattern,
    )
    if args.json:
        print(json.dumps(asdict(estate), ensure_ascii=False, indent=2))
    else:
        print(render_text(estate))
    return 0


if __name__ == "__main__":
    sys.exit(main())
