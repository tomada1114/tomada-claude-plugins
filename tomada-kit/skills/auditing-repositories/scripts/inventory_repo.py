#!/usr/bin/env python3
"""Collect the deterministic facts an audit starts from.

Reads only tracked files (git ls-files) and git history; writes nothing.

Usage:
    inventory_repo.py <repo-root> [--json] [--top N] [--churn-commits N] [--since REV]

Exit codes: 0 = inventory printed, 2 = bad invocation (not a git work tree).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

SOURCE_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".swift",
    ".kt", ".kts", ".java", ".rb", ".php", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".cs", ".m", ".mm", ".vue", ".svelte", ".sh", ".bash", ".zsh", ".lua",
    ".ex", ".exs", ".scala", ".dart", ".sql",
}
DOC_EXTS = {".md", ".mdx", ".rst", ".txt", ".adoc"}
CONFIG_EXTS = {".json", ".jsonc", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".xcconfig"}
CONFIG_NAMES = {"justfile", "makefile", "dockerfile", "procfile", "brewfile"}
LOCKFILES = {
    "pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lockb", "uv.lock",
    "poetry.lock", "pipfile.lock", "cargo.lock", "gemfile.lock", "go.sum",
    "package.resolved", "composer.lock", "mix.lock", "pubspec.lock",
}
VENDORED_DIRS = {"node_modules", "vendor", "dist", "build", ".venv", "venv", "third_party"}
MANIFESTS = {
    "package.json", "pyproject.toml", "setup.py", "requirements.txt", "cargo.toml",
    "go.mod", "package.swift", "project.yml", "gemfile", "composer.json",
    "pubspec.yaml", "build.gradle", "build.gradle.kts", "pom.xml", "mise.toml",
    "pnpm-workspace.yaml", "deno.json",
}
TEST_DIR_NAMES = {"test", "tests", "__tests__", "spec", "specs", "e2e", "testing"}
TEST_FILE_RES = [
    re.compile(r"^test_.+\.py$"),
    re.compile(r"^.+_test\.(py|go|rs|exs|dart)$"),
    re.compile(r"^.+\.(test|spec)\.[cm]?[jt]sx?$"),
    re.compile(r"^.+Tests?\.(swift|kt|java|cs)$"),
    re.compile(r"^.+_spec\.rb$"),
    re.compile(r"^conftest\.py$"),
]
TEST_DIR_SUFFIX_RE = re.compile(r".+(Tests|UITests|Test)$")
MARKER_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
JUST_RECIPE_RE = re.compile(r"^@?([A-Za-z_][\w-]*)(?:\s+[^:=]*)?:(?!=)")
MAKE_TARGET_RE = re.compile(r"^([A-Za-z_][\w.-]*)\s*:(?!=)")
REMOTE_RE = re.compile(r"github\.com[:/]+([^/]+)/(.+?)(?:\.git)?/?$")
SKILL_RE = re.compile(r"^(?:.*/)?(\.claude|\.agents)/skills/([^/]+)/SKILL\.md$")
GENERATED_RE = re.compile(r"(^|/)(generated|__generated__)/|\.(gen|generated|pb|pb2)\.|_pb2\.py$")
SMALL_SOURCE_FILES = 80
SMALL_SOURCE_LINES = 8000


@dataclass
class FileStat:
    path: str
    kind: str
    lines: int


@dataclass
class Marker:
    path: str
    line: int
    tag: str
    text: str


@dataclass
class Inventory:
    root: str
    remote: str | None
    head: str | None
    branch: str | None
    template_origin: dict[str, str]
    scale: str
    totals: dict[str, dict[str, int]]
    languages: dict[str, int]
    areas: dict[str, dict[str, int]]
    largest_files: list[FileStat]
    churn_hotspots: list[dict[str, object]]
    untested_candidates: list[FileStat]
    markers_total: int
    markers: list[Marker]
    manifests: list[str]
    ci_workflows: list[str]
    gate_entrypoints: dict[str, list[str]]
    instruction_files: list[str]
    repo_skills: dict[str, list[str]]
    repo_agents: list[str]
    issue_conventions: dict[str, object]
    changes_since: dict[str, object] | None = None
    notes: list[str] = field(default_factory=list)


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def git_or_none(root: Path, *args: str) -> str | None:
    try:
        return run_git(root, *args).strip() or None
    except RuntimeError:
        return None


def parse_remote(url: str | None) -> str | None:
    if not url:
        return None
    match = REMOTE_RE.search(url.strip())
    return f"{match.group(1)}/{match.group(2)}" if match else url.strip()


def is_excluded(path: str) -> bool:
    parts = PurePosixPath(path).parts
    name = parts[-1].lower()
    if name in LOCKFILES or name.endswith((".min.js", ".min.css", ".map", ".snap")):
        return True
    return any(part in VENDORED_DIRS for part in parts[:-1])


def is_test_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    if any(p.lower() in TEST_DIR_NAMES or TEST_DIR_SUFFIX_RE.match(p) for p in parts[:-1]):
        return True
    return any(regex.match(parts[-1]) for regex in TEST_FILE_RES)


def classify(path: str) -> str:
    if GENERATED_RE.search(path):
        return "generated"
    pure = PurePosixPath(path)
    name = pure.name.lower()
    ext = pure.suffix.lower()
    if ext in SOURCE_EXTS:
        return "test" if is_test_path(path) else "source"
    if ext in DOC_EXTS:
        return "doc"
    if ext in CONFIG_EXTS or name in CONFIG_NAMES or name.startswith("."):
        return "config"
    return "other"


def read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def find_markers(path: str, text: str) -> list[Marker]:
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = MARKER_RE.search(line)
        if match:
            found.append(Marker(path, number, match.group(1), line.strip()[:160]))
    return found


def parse_just_recipes(text: str) -> list[str]:
    names = []
    for line in text.splitlines():
        if not line or line[0] in " \t#[" or line.startswith(("set ", "import ", "mod ", "alias ", "export ")):
            continue
        match = JUST_RECIPE_RE.match(line)
        if match:
            names.append(match.group(1))
    return names


def parse_make_targets(text: str) -> list[str]:
    names = []
    for line in text.splitlines():
        match = MAKE_TARGET_RE.match(line)
        if match and not match.group(1).startswith("."):
            names.append(match.group(1))
    return names


def parse_package_scripts(text: str) -> list[str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    scripts = data.get("scripts") if isinstance(data, dict) else None
    return sorted(scripts) if isinstance(scripts, dict) else []


def parse_template_origin(text: str | None) -> dict[str, str]:
    origin: dict[str, str] = {}
    for line in (text or "").splitlines():
        if line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        if key.strip() and " " not in key.strip():
            origin[key.strip()] = value.strip()
    return origin


def area_of(path: str) -> str:
    parts = PurePosixPath(path).parts
    return parts[0] if len(parts) > 1 else "."


def test_stems(test_paths: list[str]) -> set[str]:
    stems = set()
    for path in test_paths:
        stem = PurePosixPath(path).name.split(".")[0].lower()
        for affix in ("test_", "_test", "_spec", "tests", "test"):
            stem = stem.removeprefix(affix) if affix.endswith("_") else stem.removesuffix(affix)
        stems.add(stem)
    return stems


def untested(sources: list[FileStat], stems: set[str], top: int) -> list[FileStat]:
    candidates = [
        stat for stat in sources
        if PurePosixPath(stat.path).name.split(".")[0].lower() not in stems
        and PurePosixPath(stat.path).name.split(".")[0].lower() not in {"__init__", "index", "main", "types"}
    ]
    return sorted(candidates, key=lambda s: -s.lines)[:top]


def tracked_entries(root: Path) -> list[tuple[str, str, str]]:
    """Return (mode, blob, path) for every tracked file."""
    entries = []
    for record in run_git(root, "ls-files", "-s", "-z").split("\0"):
        if not record:
            continue
        meta, _, path = record.partition("\t")
        mode, blob = meta.split()[:2]
        entries.append((mode, blob, path))
    return entries


def primary_paths(entries: list[tuple[str, str, str]]) -> tuple[list[str], int]:
    """Drop symlinks and byte-identical mirrors (e.g. .agents/skills copied to .claude/skills).

    The first path in sorted order holds each blob; returns the kept paths and the mirror count.
    """
    seen: set[str] = set()
    kept, mirrors = [], 0
    for mode, blob, path in sorted(entries, key=lambda e: e[2]):
        if mode == "120000" or mode == "160000":
            continue
        if blob in seen:
            mirrors += 1
            continue
        seen.add(blob)
        kept.append(path)
    return kept, mirrors


def churn(root: Path, commits: int, tracked: set[str], top: int) -> list[dict[str, object]]:
    log = git_or_none(root, "log", f"-n{commits}", "--name-only", "--format=")
    counts = Counter(line for line in (log or "").splitlines() if line in tracked and not is_excluded(line))
    return [{"path": path, "commits": n} for path, n in counts.most_common(top)]


def changes_since(root: Path, base: str) -> dict[str, object]:
    """Files changed between `base` and HEAD, for an incremental audit.

    `reachable` is False when `base` is not a commit in this clone (rewritten or never fetched);
    the caller then falls back to a full audit.
    """
    if git_or_none(root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}") is None:
        return {"base": base, "reachable": False, "commits": 0, "files": [], "by_area": {}}
    diff = git_or_none(root, "diff", "--name-status", "--no-renames", f"{base}..HEAD") or ""
    files = []
    for line in diff.splitlines():
        status, _, path = line.partition("\t")
        if path and not is_excluded(path):
            files.append({"status": status, "path": path, "kind": classify(path)})
    by_area = Counter(area_of(f["path"]) for f in files)
    commits = git_or_none(root, "rev-list", "--count", f"{base}..HEAD") or "0"
    return {
        "base": base,
        "reachable": True,
        "commits": int(commits),
        "files": files,
        "by_area": dict(by_area.most_common()),
    }


def build_inventory(
    root: Path, top: int = 15, churn_commits: int = 300, since: str | None = None
) -> Inventory:
    entries = tracked_entries(root)
    tracked = [path for _, _, path in entries]
    tracked_set = set(tracked)
    primary, mirrors = primary_paths(entries)
    stats: list[FileStat] = []
    markers: list[Marker] = []
    totals: dict[str, dict[str, int]] = {}
    languages: Counter[str] = Counter()
    areas: dict[str, dict[str, int]] = {}
    gates: dict[str, list[str]] = {}
    notes: list[str] = []

    if mirrors:
        notes.append(f"{mirrors} tracked files are byte-identical mirrors of another path and were counted once.")
    for path in primary:
        if is_excluded(path):
            continue
        text = read_text(root / path)
        if text is None:
            continue
        kind = classify(path)
        lines = count_lines(text)
        stats.append(FileStat(path, kind, lines))
        bucket = totals.setdefault(kind, {"files": 0, "lines": 0})
        bucket["files"] += 1
        bucket["lines"] += lines
        if kind in ("source", "test"):
            languages[PurePosixPath(path).suffix.lower()] += lines
            area = areas.setdefault(area_of(path), {"source_files": 0, "test_files": 0, "lines": 0})
            area["source_files" if kind == "source" else "test_files"] += 1
            area["lines"] += lines
            markers.extend(find_markers(path, text))
        name = PurePosixPath(path).name
        if name.lower() == "justfile" or name.endswith(".just"):
            gates[path] = parse_just_recipes(text)
        elif name.lower() in ("makefile", "gnumakefile"):
            gates[path] = parse_make_targets(text)
        elif name == "package.json":
            scripts = parse_package_scripts(text)
            if scripts:
                gates[path] = scripts

    sources = [s for s in stats if s.kind == "source"]
    tests = [s.path for s in stats if s.kind == "test"]
    source_lines = sum(s.lines for s in sources)
    scale = "small" if len(sources) < SMALL_SOURCE_FILES and source_lines < SMALL_SOURCE_LINES else "large"
    if not tests:
        notes.append("No test files matched the test-path heuristics.")

    skills: dict[str, list[str]] = {}
    for path in tracked:
        match = SKILL_RE.match(path)
        if match:
            skills.setdefault(path[: path.index("/skills/") + len("/skills")], []).append(match.group(2))

    origin_text = read_text(root / ".template-origin") if ".template-origin" in tracked_set else None
    return Inventory(
        root=str(root),
        remote=parse_remote(git_or_none(root, "remote", "get-url", "origin")),
        head=git_or_none(root, "rev-parse", "HEAD"),
        branch=git_or_none(root, "rev-parse", "--abbrev-ref", "HEAD"),
        template_origin=parse_template_origin(origin_text),
        scale=scale,
        totals=totals,
        languages=dict(languages.most_common()),
        areas=dict(sorted(areas.items(), key=lambda kv: -kv[1]["lines"])),
        largest_files=sorted(
            (s for s in stats if s.kind in ("source", "test")), key=lambda s: -s.lines
        )[:top],
        churn_hotspots=churn(root, churn_commits, tracked_set, top),
        untested_candidates=untested(sources, test_stems(tests), top),
        markers_total=len(markers),
        markers=markers[: top * 2],
        manifests=sorted(p for p in tracked if PurePosixPath(p).name.lower() in MANIFESTS and not is_excluded(p)),
        ci_workflows=sorted(p for p in tracked if p.startswith(".github/workflows/")),
        gate_entrypoints=gates,
        instruction_files=sorted(p for p in tracked if PurePosixPath(p).name in ("AGENTS.md", "CLAUDE.md")),
        repo_skills={k: sorted(v) for k, v in sorted(skills.items())},
        repo_agents=sorted(
            p for p in tracked if p.startswith((".claude/agents/", ".codex/agents/"))
        ),
        issue_conventions={
            "issue_templates": sorted(p for p in tracked if p.startswith(".github/ISSUE_TEMPLATE/")),
            "labels_file": next((p for p in (".github/labels.yml", ".github/labels.yaml") if p in tracked_set), None),
            "security_policy": next((p for p in ("SECURITY.md", ".github/SECURITY.md") if p in tracked_set), None),
            "issue_skills": sorted({n for names in skills.values() for n in names if n in ("triaging-issues", "shipping-issues", "planning-tickets", "tdd")}),
        },
        changes_since=changes_since(root, since) if since else None,
        notes=notes,
    )


def render_text(inv: Inventory) -> str:
    out = [
        f"repo: {inv.remote or '(no origin)'} @ {inv.branch} {(inv.head or '')[:12]}",
        f"scale: {inv.scale}",
        "totals: " + ", ".join(f"{k} {v['files']} files/{v['lines']} lines" for k, v in sorted(inv.totals.items())),
    ]
    if inv.template_origin:
        out.append(f"template: {inv.template_origin.get('template')} (commit {inv.template_origin.get('commit')})")
    out.append("areas: " + ", ".join(f"{k} ({v['lines']})" for k, v in inv.areas.items()))
    out.append("largest: " + ", ".join(f"{s.path} ({s.lines})" for s in inv.largest_files[:5]))
    out.append("churn: " + ", ".join(f"{c['path']} ({c['commits']})" for c in inv.churn_hotspots[:5]))
    out.append(f"markers: {inv.markers_total}")
    out.append("gates: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in inv.gate_entrypoints.items()))
    out.append("skills: " + "; ".join(f"{k}: {len(v)}" for k, v in inv.repo_skills.items()))
    out.append(f"issue conventions: {json.dumps(inv.issue_conventions, ensure_ascii=False)}")
    if inv.changes_since is not None:
        cs = inv.changes_since
        if cs["reachable"]:
            out.append(f"since {cs['base']}: {cs['commits']} commits, {len(cs['files'])} files ({cs['by_area']})")
        else:
            out.append(f"since {cs['base']}: base not reachable; run a full audit")
    out.extend(f"note: {n}" for n in inv.notes)
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect deterministic repository facts for an audit.")
    parser.add_argument("root", help="repository work tree to inventory")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a text summary")
    parser.add_argument("--top", type=int, default=15, help="entries per ranked list (default 15)")
    parser.add_argument("--churn-commits", type=int, default=300, help="commits scanned for churn (default 300)")
    parser.add_argument("--since", metavar="REV", help="also list files changed from REV to HEAD (incremental audit)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        top_level = run_git(root, "rev-parse", "--show-toplevel").strip()
    except (RuntimeError, OSError):
        print(f"error: {root} is not inside a git work tree; pass the repository root.", file=sys.stderr)
        return 2
    inventory = build_inventory(Path(top_level), args.top, args.churn_commits, args.since)
    if args.json:
        print(json.dumps(asdict(inventory), ensure_ascii=False, indent=2))
    else:
        print(render_text(inventory))
    return 0


if __name__ == "__main__":
    sys.exit(main())
