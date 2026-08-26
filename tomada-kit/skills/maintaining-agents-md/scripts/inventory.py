#!/usr/bin/env python3
"""inventory.py — Enumerate and classify a project's AGENTS.md / CLAUDE.md rule files.

Usage:
    inventory.py [<root>] [--json] [--max-depth N]

<root> defaults to the git toplevel of the current directory, else the current
directory. The script only reads; it never writes.

What it reports:
    * every AGENTS.md and every effective Codex instruction source (including
      AGENTS.override.md and configured fallback filenames), with the root ->
      dir chain size against Codex's configured document budget
    * every CLAUDE.md, classified as
      stub / stub+extras / legacy / legacy-import / missing / orphan / malformed
    * CLAUDE.local.md files, `.claude/CLAUDE.md`, and `.claude/rules/*.md`
      (with each rule's `paths:` scope: directory / pattern / mixed / global)
    * findings R001-R013 and a `suggested_mode` of
      init | audit | migrate

Finding codes:
    R001 legacy CLAUDE.md body (needs migrate)      R006 malformed managed block
    R002 missing CLAUDE.md stub                     R007 .claude/CLAUDE.md has content
    R003 orphan CLAUDE.md (no AGENTS.md)            R008 .claude/rules present
    R004 `@` import inside AGENTS.md                R009 legacy-import stub (adoptable)
    R005 over the Codex document budget              R010 CLAUDE.local.md present (info)
    R011 active AGENTS.override.md                  R012 active configured fallback
    R013 Codex config could not be read completely

Exit codes:
    0 = no error/warn findings
    1 = at least one error/warn finding
    2 = bad invocation (root does not exist, etc.)
"""
from __future__ import annotations

import argparse
import ast
import textwrap
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# --- the stub contract -------------------------------------------------------
# These three lines are the managed block, byte for byte (UTF-8, LF). The HTML
# comment markers are inert for Claude Code's import parser, which is what makes
# a machine-owned region inside a hand-edited file possible.
MANAGED_BEGIN = "<!-- agents-md-sync:begin -->"
MANAGED_END = "<!-- agents-md-sync:end -->"
IMPORT_LINE = "@AGENTS.md"
MANAGED_BLOCK = "{}\n{}\n{}\n".format(MANAGED_BEGIN, IMPORT_LINE, MANAGED_END)

# Codex CLI concatenates the selected instruction chain root -> cwd into one
# shared budget. 32 KiB is the default; config.toml can change it.
CODEX_DOC_BUDGET = 32768
CODEX_CONFIG_REL = ".codex/config.toml"
AGENTS_FILENAME = "AGENTS.md"
AGENTS_OVERRIDE_FILENAME = "AGENTS.override.md"

# Directories that never hold project rule files but are expensive to walk.
# `.claude` is inspected explicitly instead; other dot-directories remain
# scannable because Codex can be launched inside `.agents`, `.github`, etc.
SKIP_DIRS = {
    "node_modules", "vendor", "dist", "build", "venv", "__pycache__", "target",
    ".git", ".claude", ".venv", ".next", ".cache", ".idea", ".tox",
    ".mypy_cache", ".pytest_cache",
}

# The default must not silently miss a deeper package. Callers can still pass a
# limit for a deliberately bounded scan.
DEFAULT_MAX_DEPTH: Optional[int] = None

FENCE_RE = re.compile(r"^\s*(```|~~~)")
IMPORT_RE = re.compile(r"^@(\S+)")
# `@AGENTS.md` and `@./AGENTS.md` import the same file; both count as adoptable.
BARE_IMPORT_RE = re.compile(r"^@(?:\./)?AGENTS\.md$")
GLOB_CHARS = set("*?[]{}")


# --- small IO helpers --------------------------------------------------------
def read_text(path: Path) -> str:
    """Read a file without any newline translation, preserving bytes exactly.

    surrogateescape round-trips undecodable bytes, so a file we read and write
    back unchanged stays byte-identical even if it is not valid UTF-8.
    """
    return path.read_bytes().decode("utf-8", "surrogateescape")


def write_text(path: Path, text: str) -> None:
    """Counterpart of read_text: no newline translation, no BOM, no re-encoding."""
    path.write_bytes(text.encode("utf-8", "surrogateescape"))


def count_lines(text: str) -> int:
    return len(text.splitlines())


def codex_home() -> Path:
    """The Codex home whose config and global instructions are effective."""
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def _minimal_toml_config(text: str) -> Dict[str, object]:
    """Read the two root-level Codex settings on Python versions without tomllib.

    This is intentionally not a general TOML parser. It is only a fallback for
    the two scalar/list settings this inventory needs; a modern Python uses the
    standard library parser below.
    """
    result: Dict[str, object] = {}
    section = ""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if section:
            continue
        match = re.match(r"^(project_doc_max_bytes|project_doc_fallback_filenames)\s*=\s*(.+)$", line)
        if not match:
            continue
        key, raw_value = match.groups()
        try:
            if key == "project_doc_max_bytes":
                result[key] = int(raw_value.strip())
            else:
                value = json.loads(raw_value)
                if isinstance(value, list):
                    result[key] = value
        except (ValueError, SyntaxError):
            try:
                value = ast.literal_eval(raw_value)
                if key == "project_doc_fallback_filenames" and isinstance(value, list):
                    result[key] = value
            except (ValueError, SyntaxError):
                continue
    return result


def load_codex_config(path: Path) -> Tuple[Dict[str, object], str]:
    """Return the parsed Codex config and a diagnostic error, if any."""
    try:
        text = read_text(path)
    except OSError as exc:
        return {}, str(exc)
    try:
        import tomllib  # type: ignore[import-not-found]
        data = tomllib.loads(text)
        if not isinstance(data, dict):
            return {}, "top level is not a TOML table"
        return data, ""
    except ModuleNotFoundError:
        # Python 3.10 has no tomllib. The fallback still lets the inventory
        # report the effective budget without adding a dependency to the skill.
        return _minimal_toml_config(text), ""
    except (OSError, ValueError, UnicodeError) as exc:
        return {}, str(exc)


def _valid_fallback_names(value: object) -> List[str]:
    """Keep only filename-shaped configured fallbacks we can scan safely."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    names: List[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            continue
        name = item.strip()
        if name in (AGENTS_FILENAME, AGENTS_OVERRIDE_FILENAME):
            continue
        if Path(name).name != name or name in (".", ".."):
            continue
        if name not in names:
            names.append(name)
    return names


def resolve_codex_config(root: Path) -> Tuple[int, str, List[str], List[str], List[str]]:
    """Resolve budget/fallback settings without exposing unrelated config data.

    Project-local config overrides the user config. The returned values are
    `(budget, budget_source, fallback_names, config_files, errors)`.
    """
    project_config = root / CODEX_CONFIG_REL
    global_config = codex_home() / "config.toml"
    paths: List[Tuple[str, Path]] = []
    if global_config.is_file():
        paths.append((str(global_config), global_config))
    if project_config.is_file() and project_config != global_config:
        paths.append((CODEX_CONFIG_REL, project_config))

    parsed: List[Tuple[str, Path, Dict[str, object]]] = []
    errors: List[str] = []
    labels: List[str] = []
    for label, path in paths:
        data, error = load_codex_config(path)
        labels.append(label)
        if error:
            errors.append("{}: {}".format(label, error))
        else:
            parsed.append((label, path, data))

    budget = CODEX_DOC_BUDGET
    budget_source = "default"
    fallbacks: List[str] = []
    # Global first, project last: the project value wins when both specify it.
    for label, _path, data in parsed:
        value = data.get("project_doc_max_bytes")
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            budget = value
            budget_source = label
        if "project_doc_fallback_filenames" in data:
            fallbacks = _valid_fallback_names(data.get("project_doc_fallback_filenames"))
    return budget, budget_source, fallbacks, labels, errors


def _nonempty_file(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return bool(read_text(path).strip())
    except OSError:
        return False


def codex_global_instruction() -> Optional[Path]:
    """Select the non-empty global Codex instruction file, if present."""
    home = codex_home()
    for name in (AGENTS_OVERRIDE_FILENAME, AGENTS_FILENAME):
        candidate = home / name
        if _nonempty_file(candidate):
            return candidate
    return None


def codex_candidates(directory: Path, fallback_names: Sequence[str]) -> List[Tuple[Path, str]]:
    """Return Codex's candidates in its documented priority order."""
    names: List[Tuple[str, str]] = [
        (AGENTS_OVERRIDE_FILENAME, "override"),
        (AGENTS_FILENAME, "canonical"),
    ]
    names.extend((name, "fallback") for name in fallback_names)
    seen: set[str] = set()
    candidates: List[Tuple[Path, str]] = []
    for name, kind in names:
        if name in seen:
            continue
        seen.add(name)
        path = directory / name
        if path.is_file():
            candidates.append((path, kind))
    return candidates


def outside_fences(text: str) -> List[Tuple[int, str]]:
    """[(1-based line number, line text)] for lines outside ``` / ~~~ fences."""
    result: List[Tuple[int, str]] = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            result.append((i, line))
    return result


# --- stub parsing ------------------------------------------------------------
@dataclass
class StubParse:
    """Result of looking at one CLAUDE.md, ignoring whether AGENTS.md exists."""

    state: str  # stub | stub+extras | legacy | legacy-import | malformed
    free_section: str = ""  # raw text after the end marker, byte for byte
    preamble: str = ""  # text before the begin marker (malformed only)
    repairable: bool = False
    detail: str = ""


def _marker_index(lines: Sequence[str], marker: str) -> int:
    for i, line in enumerate(lines):
        if line.strip() == marker:
            return i
    return -1


def parse_claude_md(text: str) -> StubParse:
    """Classify the body of a CLAUDE.md against the managed-block contract."""
    lines = text.splitlines(keepends=True)
    begin = _marker_index(lines, MANAGED_BEGIN)
    end = _marker_index(lines, MANAGED_END)

    if begin < 0 and end < 0:
        for _, line in outside_fences(text):
            if BARE_IMPORT_RE.match(line.strip()):
                return StubParse("legacy-import", detail="bare import line present")
        return StubParse("legacy", detail="no managed block")

    if begin < 0 or end < 0 or end < begin:
        return StubParse(
            "malformed",
            repairable=False,
            detail="unbalanced markers (begin at {}, end at {})".format(begin + 1, end + 1),
        )

    preamble = "".join(lines[:begin])
    inner = "".join(lines[begin + 1 : end])
    free = "".join(lines[end + 1 :])

    if preamble.strip():
        return StubParse(
            "malformed", free_section=free, preamble=preamble, repairable=True,
            detail="managed block is not at the top of the file",
        )
    if inner.strip() != IMPORT_LINE:
        return StubParse(
            "malformed", free_section=free, preamble=preamble, repairable=True,
            detail="managed block contains {!r}, expected {!r}".format(inner.strip(), IMPORT_LINE),
        )
    if free.strip():
        return StubParse("stub+extras", free_section=free)
    return StubParse("stub", free_section=free)


def compose_stub(free_section: str = "") -> str:
    """Managed block first, then the free section exactly as given."""
    return MANAGED_BLOCK + free_section


def block_equivalent(text: str, desired: str) -> bool:
    """True when `text` differs from `desired` only by whole blank lines inside the
    managed block — what a markdown formatter inserts around the import line.
    Sync must not undo a formatter on every run. Leading blank lines and a
    padded import line are still drift: the file must start with the marker,
    and an indented import line is a code block, not an import."""
    if not text.startswith(MANAGED_BEGIN):
        return False

    def lines(value: str) -> List[str]:
        return [line for line in value.splitlines() if line.strip()]

    return lines(text) == lines(desired)


def adopt_free_section(text: str) -> str:
    """Free section for a legacy-import CLAUDE.md: everything except the import line.

    The remaining lines keep their original order and bytes; only the blank
    lines that surrounded the removed import are normalized to one.
    """
    lines = text.splitlines(keepends=True)
    dropped = False
    kept: List[str] = []
    for line in lines:
        if not dropped and BARE_IMPORT_RE.match(line.strip()):
            dropped = True
            continue
        kept.append(line)
    rest = "".join(kept).lstrip("\n")
    return "\n" + rest if rest.strip() else ""


def repair_free_section(parse: StubParse) -> str:
    """Free section for a malformed-but-repairable stub: preamble, then the tail."""
    chunks = [c for c in (parse.preamble.strip("\n"), parse.free_section.strip("\n")) if c.strip()]
    return "\n" + "\n\n".join(chunks) + "\n" if chunks else ""


# --- frontmatter / rule scope ------------------------------------------------
def parse_frontmatter_paths(text: str) -> Optional[List[str]]:
    """`paths:` from a rule file's YAML frontmatter, or None when absent.

    Minimal YAML subset, by design: a single string, an inline list
    `["a", "b"]`, or a block list of `- a` items. No PyYAML.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    body: List[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    else:
        return None

    for i, line in enumerate(body):
        if not line.startswith("paths:"):
            continue
        value = line[len("paths:") :].strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if not inner:
                return []
            return [_unquote(p) for p in inner.split(",") if p.strip()]
        if value:
            return [_unquote(value)]
        items: List[str] = []
        for follow in body[i + 1 :]:
            stripped = follow.strip()
            if not stripped:
                continue
            if not stripped.startswith("- "):
                break
            items.append(_unquote(stripped[2:]))
        return items
    return None


def _unquote(value: str) -> str:
    value = value.strip().strip(",").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def literal_prefix_dir(pattern: str) -> str:
    """Longest leading directory of a glob that contains no glob metacharacter."""
    parts = pattern.replace("\\", "/").split("/")
    kept: List[str] = []
    for part in parts[:-1]:  # the last segment is the filename, never a dir prefix
        if any(ch in GLOB_CHARS for ch in part):
            break
        kept.append(part)
    return "/".join(kept)


def classify_rule_scope(patterns: Optional[Sequence[str]], root: Path) -> Tuple[str, Optional[str], bool]:
    """(scope, scope_dir, pattern_only) for one rule file's `paths:` value.

    directory-shaped = the glob starts with a literal directory that exists on
    disk; that directory is where the rule's content belongs as its own
    AGENTS.md. Anything else is pattern-only and folds into the root AGENTS.md.
    """
    if patterns is None:
        return "global", None, False
    if not patterns:
        return "pattern", None, True

    dirs: List[str] = []
    pattern_only = 0
    for pattern in patterns:
        prefix = literal_prefix_dir(pattern)
        if prefix and (root / prefix).is_dir():
            dirs.append(prefix)
        else:
            pattern_only += 1

    if not dirs:
        return "pattern", None, True
    if pattern_only:
        return "mixed", None, False

    common = dirs[0].split("/")
    for d in dirs[1:]:
        parts = d.split("/")
        keep = []
        for a, b in zip(common, parts):
            if a != b:
                break
            keep.append(a)
        common = keep
    if not common:
        return "mixed", None, False
    return "directory", "/".join(common), False


# --- git ---------------------------------------------------------------------
def _git(root: Path, *args: str) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root)] + list(args),
            capture_output=True, text=True, check=False,
        )
    except (OSError, ValueError):  # git not installed
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def git_info(root: Path) -> Dict[str, object]:
    """{is_repo, toplevel, dirty_paths} — dirty_paths lists rule files only."""
    top = _git(root, "rev-parse", "--show-toplevel")
    if top is None:
        return {"is_repo": False, "toplevel": None, "dirty_paths": []}
    toplevel = top.strip()
    status = _git(root, "status", "--porcelain") or ""
    dirty: List[str] = []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:  # rename: report the destination
            path = path.split(" -> ", 1)[1]
        name = path.rsplit("/", 1)[-1]
        if name in (AGENTS_FILENAME, AGENTS_OVERRIDE_FILENAME, "CLAUDE.md", "CLAUDE.local.md") \
                or "/.claude/" in "/" + path or "/.codex/" in "/" + path:
            dirty.append(path)
    return {"is_repo": True, "toplevel": toplevel, "dirty_paths": sorted(dirty)}


def default_root(cwd: Optional[Path] = None) -> Path:
    """git toplevel of cwd when there is one, else cwd."""
    cwd = (cwd or Path.cwd()).resolve()
    top = _git(cwd, "rev-parse", "--show-toplevel")
    if top and top.strip():
        return Path(top.strip())
    return cwd


# --- inventory ---------------------------------------------------------------
@dataclass
class Finding:
    code: str
    severity: str  # error | warn | info
    path: str
    line: int
    message: str


@dataclass
class AgentsMdEntry:
    path: str
    dir: str
    bytes: int
    lines: int
    inverted_imports: List[Dict[str, object]] = field(default_factory=list)
    chain_bytes: int = 0
    over_codex_budget: bool = False
    project_chain_bytes: int = 0
    codex_source: Optional[str] = None


@dataclass
class CodexSourceEntry:
    path: str
    dir: str
    kind: str  # override | canonical | fallback
    bytes: int
    lines: int
    active: bool = False
    project_chain_bytes: int = 0
    chain_bytes: int = 0
    over_codex_budget: bool = False


@dataclass
class CodexInfo:
    budget: int = CODEX_DOC_BUDGET
    budget_source: str = "default"
    fallback_names: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    config_errors: List[str] = field(default_factory=list)
    global_source: Optional[str] = None
    global_bytes: int = 0
    sources: List[CodexSourceEntry] = field(default_factory=list)


@dataclass
class ClaudeMdEntry:
    path: str
    dir: str
    state: str
    bytes: int
    lines: int
    has_agents_md: bool
    free_section_lines: int = 0


@dataclass
class RuleEntry:
    path: str
    bytes: int
    lines: int
    paths: Optional[List[str]]
    scope: str
    scope_dir: Optional[str]
    pattern_only: bool


@dataclass
class Inventory:
    root: str
    git: Dict[str, object]
    agents_md: List[AgentsMdEntry] = field(default_factory=list)
    claude_md: List[ClaudeMdEntry] = field(default_factory=list)
    claude_local_md: List[str] = field(default_factory=list)
    dot_claude_claude_md: List[str] = field(default_factory=list)
    rules: List[RuleEntry] = field(default_factory=list)
    codex: CodexInfo = field(default_factory=CodexInfo)
    findings: List[Finding] = field(default_factory=list)
    suggested_mode: str = "audit"


def walk_dirs(root: Path, max_depth: Optional[int]) -> List[Path]:
    """Directories under root worth scanning, root first, then sorted."""
    found = [root]
    for current, dirnames, _files in os.walk(root):
        rel_parts = Path(current).relative_to(root).parts
        if max_depth is not None and len(rel_parts) >= max_depth:
            dirnames[:] = []
            continue
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for d in dirnames:
            found.append(Path(current) / d)
    return found


def rel_of(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    return rel or "."


def build_inventory(root: Path, max_depth: Optional[int] = DEFAULT_MAX_DEPTH) -> Inventory:
    """Read the whole project and return the full classification. Never writes."""
    root = root.resolve()
    inv = Inventory(root=str(root), git=git_info(root))

    budget, budget_source, fallback_names, config_files, config_errors = resolve_codex_config(root)
    global_instruction = codex_global_instruction()
    global_bytes = global_instruction.stat().st_size if global_instruction else 0
    inv.codex = CodexInfo(
        budget=budget, budget_source=budget_source, fallback_names=fallback_names,
        config_files=config_files, config_errors=config_errors,
        global_source=str(global_instruction) if global_instruction else None,
        global_bytes=global_bytes,
    )

    dirs = walk_dirs(root, max_depth)
    active_sources: Dict[Path, Path] = {}
    source_bytes: Dict[str, int] = {}
    for d in dirs:
        candidates = codex_candidates(d, fallback_names)
        active: Optional[Tuple[Path, str]] = None
        for path, kind in candidates:
            try:
                text = read_text(path)
            except OSError:
                continue
            entry = CodexSourceEntry(
                path=rel_of(root, path), dir=rel_of(root, d), kind=kind,
                bytes=path.stat().st_size, lines=count_lines(text), active=False,
            )
            inv.codex.sources.append(entry)
            if active is None and text.strip():
                active = (path, kind)
        if active is not None:
            active_sources[d] = active[0]
            source_bytes[rel_of(root, d)] = active[0].stat().st_size
            for source in inv.codex.sources:
                if source.dir == rel_of(root, d) and source.path == rel_of(root, active[0]):
                    source.active = True
                    break
    inv.codex.sources.sort(key=lambda source: source.path)

    for directory, source in active_sources.items():
        project_chain = _chain_bytes(root, directory, source_bytes)
        chain = project_chain + global_bytes
        source_path = rel_of(root, source)
        for entry in inv.codex.sources:
            if entry.active and entry.path == source_path:
                entry.project_chain_bytes = project_chain
                entry.chain_bytes = chain
                entry.over_codex_budget = chain > budget
                break

    agents_dirs: List[Path] = []
    for d in dirs:
        agents = d / AGENTS_FILENAME
        if agents.is_file():
            agents_dirs.append(d)

    for d in agents_dirs:
        agents = d / AGENTS_FILENAME
        text = read_text(agents)
        inverted = [
            {"line": num, "text": line.strip()}
            for num, line in outside_fences(text)
            if IMPORT_RE.match(line)
        ]
        project_chain = _chain_bytes(root, d, source_bytes)
        chain = project_chain + global_bytes
        source = active_sources.get(d)
        inv.agents_md.append(
            AgentsMdEntry(
                path=rel_of(root, agents), dir=rel_of(root, d),
                bytes=agents.stat().st_size, lines=count_lines(text),
                inverted_imports=inverted, chain_bytes=chain,
                over_codex_budget=chain > budget,
                project_chain_bytes=project_chain,
                codex_source=rel_of(root, source) if source else None,
            )
        )

    for d in dirs:
        claude = d / "CLAUDE.md"
        has_agents = (d / AGENTS_FILENAME).is_file()
        if not claude.is_file():
            if has_agents:
                inv.claude_md.append(
                    ClaudeMdEntry(
                        path=rel_of(root, claude), dir=rel_of(root, d), state="missing",
                        bytes=0, lines=0, has_agents_md=True,
                    )
                )
            continue
        text = read_text(claude)
        parse = parse_claude_md(text)
        state = parse.state if has_agents else "orphan"
        free_lines = count_lines(parse.free_section.strip("\n")) if parse.free_section.strip() else 0
        inv.claude_md.append(
            ClaudeMdEntry(
                path=rel_of(root, claude), dir=rel_of(root, d), state=state,
                bytes=claude.stat().st_size, lines=count_lines(text),
                has_agents_md=has_agents, free_section_lines=free_lines,
            )
        )

    for d in dirs:
        local = d / "CLAUDE.local.md"
        if local.is_file():
            inv.claude_local_md.append(rel_of(root, local))
    inv.claude_local_md.sort()

    alt = root / ".claude" / "CLAUDE.md"
    if alt.is_file():
        inv.dot_claude_claude_md.append(rel_of(root, alt))

    rules_dir = root / ".claude" / "rules"
    if rules_dir.is_dir():
        for rule in sorted(rules_dir.rglob("*.md")):
            text = read_text(rule)
            patterns = parse_frontmatter_paths(text)
            scope, scope_dir, pattern_only = classify_rule_scope(patterns, root)
            inv.rules.append(
                RuleEntry(
                    path=rel_of(root, rule), bytes=rule.stat().st_size,
                    lines=count_lines(text), paths=patterns, scope=scope,
                    scope_dir=scope_dir, pattern_only=pattern_only,
                )
            )

    findings = collect_findings(root, inv)
    findings.sort(key=lambda f: (f.path, f.code, f.line))
    inv.findings = findings
    inv.suggested_mode = suggest_mode(root, inv)
    return inv


def _chain_bytes(root: Path, target: Path, agents_bytes: Dict[str, int]) -> int:
    """Bytes Codex would load for a session started in `target`: root -> target."""
    total = 0
    rel = target.relative_to(root)
    chain = [Path(".")] + [Path(*rel.parts[: i + 1]) for i in range(len(rel.parts))]
    for part in chain:
        total += agents_bytes.get(part.as_posix(), 0)
    return total


def collect_findings(root: Path, inv: Inventory) -> List[Finding]:
    findings: List[Finding] = []
    canonical_dirs = {entry.dir for entry in inv.agents_md}
    for source in inv.codex.sources:
        if not source.active:
            continue
        if source.kind == "override":
            findings.append(
                Finding(
                    "R011", "warn", source.path, 0,
                    "Codex selects {} instead of the sibling AGENTS.md; Claude's stub imports "
                    "the canonical file, so the hosts do not share this directory's rules. "
                    "Keep the override only when that divergence is intentional; otherwise "
                    "fold it into AGENTS.md and remove the override by hand".format(source.path),
                )
            )
        elif source.kind == "fallback":
            findings.append(
                Finding(
                    "R012", "warn", source.path, 0,
                    "Codex selects configured fallback {} here; this skill manages AGENTS.md "
                    "and Claude's stub does not import the fallback. Rename it to AGENTS.md "
                    "or document the deliberate host-specific source".format(source.path),
                )
            )
        if source.over_codex_budget and source.dir not in canonical_dirs:
            findings.append(
                Finding(
                    "R005", "warn", source.path, 0,
                    "effective Codex instruction chain for {} is {} bytes, over the {} byte "
                    "budget (project chain {} B); Codex stops adding documents once the cap "
                    "is reached".format(
                        source.dir, source.chain_bytes, inv.codex.budget, source.project_chain_bytes),
                )
            )

    for error in inv.codex.config_errors:
        label, _, detail = error.partition(": ")
        findings.append(
            Finding(
                "R013", "warn", label, 0,
                "could not fully read Codex config ({}); verify project_doc_max_bytes and "
                "project_doc_fallback_filenames by hand".format(detail or error),
            )
        )

    for entry in inv.agents_md:
        for imp in entry.inverted_imports:
            findings.append(
                Finding(
                    "R004", "error", entry.path, int(imp["line"]),
                    "`{}` is an import Codex cannot follow; fold the target's content "
                    "into AGENTS.md and delete the line".format(imp["text"]),
                )
            )
        if entry.over_codex_budget:
            findings.append(
                Finding(
                    "R005", "warn", entry.path, 0,
                    "effective Codex instruction chain for {} is {} bytes, over the {} byte "
                    "budget (project chain {} B); Codex stops adding documents once the cap "
                    "is reached".format(
                        entry.dir, entry.chain_bytes, inv.codex.budget, entry.project_chain_bytes),
                )
            )

    for entry in inv.claude_md:
        if entry.state == "legacy":
            findings.append(
                Finding("R001", "warn", entry.path, 0,
                        "legacy CLAUDE.md body; run migrate to fold it into AGENTS.md"))
        elif entry.state == "missing":
            findings.append(
                Finding("R002", "error", entry.path, 0,
                        "AGENTS.md here has no CLAUDE.md stub, so Claude Code never loads it; "
                        "run sync_stubs.py"))
        elif entry.state == "orphan":
            findings.append(
                Finding("R003", "warn", entry.path, 0,
                        "CLAUDE.md with no AGENTS.md beside it; run migrate to fold its content "
                        "into a new AGENTS.md and stub this file"))
        elif entry.state == "malformed":
            findings.append(
                Finding("R006", "error", entry.path, 0,
                        "managed block is malformed; run sync_stubs.py to repair it"))
        elif entry.state == "legacy-import":
            findings.append(
                Finding("R009", "warn", entry.path, 0,
                        "bare @AGENTS.md import without the managed block; sync_stubs.py adopts it"))

    for alt in inv.dot_claude_claude_md:
        if (root / alt).stat().st_size > 0:
            findings.append(
                Finding("R007", "warn", alt, 0,
                        "alternative project memory location with content; fold it into the root "
                        "AGENTS.md to avoid duplicate or ordering-dependent rules"))

    if inv.rules:
        findings.append(
            Finding("R008", "warn", ".claude/rules", 0,
                    "{} rule file(s) Codex cannot see; migrate moves each one to its scope's "
                    "AGENTS.md".format(len(inv.rules))))

    for local in inv.claude_local_md:
        findings.append(
            Finding("R010", "info", local, 0,
                    "personal, gitignored memory file; never migrated or synced"))

    findings.sort(key=lambda f: (f.path, f.code, f.line))
    return findings


def suggest_mode(root: Path, inv: Inventory) -> str:
    has_content_claude = any(
        e.state != "missing" and (root / e.path).is_file() and read_text(root / e.path).strip()
        for e in inv.claude_md
    )
    if not inv.agents_md and not has_content_claude \
            and not any(source.active for source in inv.codex.sources):
        return "init"
    if any(e.state == "legacy" for e in inv.claude_md):
        return "migrate"
    if any(e.inverted_imports for e in inv.agents_md):
        return "migrate"
    if any((root / p).stat().st_size > 0 for p in inv.dot_claude_claude_md):
        return "migrate"
    if inv.rules:
        return "migrate"
    return "audit"


def has_blocking_findings(inv: Inventory) -> bool:
    return any(f.severity in ("error", "warn") for f in inv.findings)


# --- output ------------------------------------------------------------------
def format_text(inv: Inventory) -> str:
    out: List[str] = []
    git = inv.git
    git_note = "git repo" if git.get("is_repo") else "not a git repo"
    dirty = git.get("dirty_paths") or []
    if dirty:
        git_note += ", uncommitted rule files: {}".format(", ".join(dirty))  # type: ignore[arg-type]
    out.append("root: {} ({})".format(inv.root, git_note))

    out.append("")
    out.append("Codex instruction resolution:")
    out.append("  budget: {} B (source: {})".format(inv.codex.budget, inv.codex.budget_source))
    if inv.codex.global_source:
        out.append("  global: {} — {} B".format(inv.codex.global_source, inv.codex.global_bytes))
    else:
        out.append("  global: (none detected)")
    if inv.codex.fallback_names:
        out.append("  fallback names: {}".format(", ".join(inv.codex.fallback_names)))
    if inv.codex.sources:
        for source in inv.codex.sources:
            status = "active" if source.active else "candidate"
            chain = ", chain {} B".format(source.chain_bytes) if source.active else ""
            out.append("  {} — {} {} ({} B, {} lines{})".format(
                source.path, status, source.kind, source.bytes, source.lines, chain))
    else:
        out.append("  project sources: (none)")

    out.append("")
    out.append("AGENTS.md ({}):".format(len(inv.agents_md)))
    for e in inv.agents_md:
        flag = "  OVER CODEX BUDGET" if e.over_codex_budget else ""
        out.append("  {} — {} B, {} lines, chain {} B{}".format(
            e.path, e.bytes, e.lines, e.chain_bytes, flag))
        if e.codex_source and e.codex_source != e.path:
            out.append("      Codex selects: {}".format(e.codex_source))
        for imp in e.inverted_imports:
            out.append("      line {}: {}".format(imp["line"], imp["text"]))
    if not inv.agents_md:
        out.append("  (none)")

    out.append("")
    out.append("CLAUDE.md ({}):".format(len(inv.claude_md)))
    for c in inv.claude_md:
        extra = ", free section {} lines".format(c.free_section_lines) if c.free_section_lines else ""
        out.append("  {} — {}, {} B, {} lines{}".format(c.path, c.state, c.bytes, c.lines, extra))
    if not inv.claude_md:
        out.append("  (none)")

    if inv.claude_local_md:
        out.append("")
        out.append("CLAUDE.local.md: {}".format(", ".join(inv.claude_local_md)))
    if inv.dot_claude_claude_md:
        out.append("alt location: {}".format(", ".join(inv.dot_claude_claude_md)))

    if inv.rules:
        out.append("")
        out.append(".claude/rules ({}):".format(len(inv.rules)))
        for r in inv.rules:
            target = r.scope_dir or "-"
            out.append("  {} — scope={} dir={} paths={}".format(
                r.path, r.scope, target, r.paths if r.paths is not None else "(none)"))

    out.append("")
    out.append("findings ({}):".format(len(inv.findings)))
    for f in inv.findings:
        where = "{}:{}".format(f.path, f.line) if f.line else f.path
        out.append("  [{}] {} {} — {}".format(f.severity, f.code, where, f.message))
    if not inv.findings:
        out.append("  (none)")

    out.append("")
    out.append("suggested mode: {}".format(inv.suggested_mode))
    return "\n".join(out)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="inventory.py",
        description="Classify a project's AGENTS.md / CLAUDE.md rule files. Read-only.",
        epilog="Finding codes:\n" + textwrap.dedent(
            __doc__.split("Finding codes:", 1)[1].split("Exit codes:", 1)[0]).strip("\n")
        + "\n\nExit codes:\n" + textwrap.dedent(__doc__.split("Exit codes:", 1)[1]).strip("\n"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", nargs="?", default=None,
                        help="project root (default: git toplevel of cwd, else cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH,
                        help="directory levels below root to scan (default: no limit)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = Path(args.root).expanduser() if args.root else default_root()
    if not root.is_dir():
        print("Project root not found: {}. Pass an existing directory as the first "
              "argument.".format(root), file=sys.stderr)
        return 2
    if args.max_depth is not None and args.max_depth < 1:
        print("--max-depth must be at least 1 (got {}).".format(args.max_depth), file=sys.stderr)
        return 2

    inv = build_inventory(root, args.max_depth)
    if args.json:
        print(json.dumps(asdict(inv), indent=2, ensure_ascii=False))
    else:
        print(format_text(inv))
    return 1 if has_blocking_findings(inv) else 0


if __name__ == "__main__":
    sys.exit(main())
