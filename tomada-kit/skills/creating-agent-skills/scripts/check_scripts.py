#!/usr/bin/env python3
"""check_scripts.py — Verify scripts/ conventions for a Claude Code skill.

Wraps unittest + coverage subprocess runs and a handful of static checks
over a skill's scripts/ directory.

Usage:
    check_scripts.py <skill-path> [--json] [--no-tests] [--min-coverage N]

Checks:
    S000  scripts/ directory does not exist — nothing to check (info).
    S001  a .py script has no scripts/tests/test_<stem>.py (warning); a .sh
          script has no scripts/tests/test_<stem>.py (info — a subprocess
          smoke test is recommended, not required, for shell scripts).
    S002  scripts/tests/ test run failed (error). Skipped, with an info
          finding, when scripts/tests/ does not exist or --no-tests is given.
    S003  total or per-file coverage is below --min-coverage (default 90).
          Only measured when tests actually ran.
    S004  the `coverage` package is not importable — S003 is skipped.
    S005  a script's first line is not a shebang, or it lacks the owner
          execute bit.
    S006  a script hardcodes a personal skills path (home dir + .claude/skills).
          Suppress a legitimate use with `scripts-ignore: S006` on that line.
    S007  scripts/__pycache__, .pytest_cache, or .coverage are not covered
          by .gitignore (only checked inside a git work tree).

Output:
    Human-readable by default, machine-readable with --json.

Exit codes:
    0 = no errors (warnings/hints allowed)
    1 = at least one error
    2 = bad invocation / skill path is not a directory
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Reuse validate_skill.Finding in-process, the same way audit_skill.py does.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import validate_skill  # type: ignore  # noqa: E402

# S006: hardcoded personal skills path. A line carrying `scripts-ignore: S006`
# is exempt (same convention as `audit-ignore` / `neutrality-ignore`); this
# regex line needs it because it literally contains the pattern it hunts.
PERSONAL_SKILLS_PATH_RE = re.compile(
    r"(?:~|\$HOME|/Users/[^/\s]+|/home/[^/\s]+)/\.claude/skills"  # scripts-ignore: S006
)
IGNORE_LINE_RE = re.compile(r"scripts-ignore:\s*S006\b")


@dataclass
class TestRun:
    ran: bool = False
    returncode: int | None = None
    summary: str = ""


@dataclass
class CoverageResult:
    percent: float | None = None
    threshold: int = 90
    below_threshold_files: list[str] = field(default_factory=list)


@dataclass
class ScriptsReport:
    skill_path: str
    has_scripts: bool = False
    scripts: list[str] = field(default_factory=list)
    tests: TestRun = field(default_factory=TestRun)
    coverage: CoverageResult = field(default_factory=CoverageResult)
    findings: list[validate_skill.Finding] = field(default_factory=list)

    def add(self, level: str, code: str, message: str, location: str = "") -> None:
        self.findings.append(validate_skill.Finding(level, code, message, location))

    @property
    def errors(self) -> list[validate_skill.Finding]:
        return [f for f in self.findings if f.level == "error"]


def find_scripts(skill: Path) -> list[Path]:
    """Files directly under scripts/ with suffix .py or .sh, excluding _-prefixed
    names. scripts/tests/ is a subdirectory, so iterdir() never descends into it."""
    scripts_dir = skill / "scripts"
    if not scripts_dir.is_dir():
        return []
    result = []
    for p in sorted(scripts_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix not in (".py", ".sh"):
            continue
        if p.name.startswith("_"):
            continue
        result.append(p)
    return result


def check_test_presence(skill: Path, scripts: list[Path]) -> list[validate_skill.Finding]:
    tests_dir = skill / "scripts" / "tests"
    findings: list[validate_skill.Finding] = []
    for s in scripts:
        test_file = tests_dir / f"test_{s.stem}.py"
        if test_file.exists():
            continue
        level = "warning" if s.suffix == ".py" else "info"
        findings.append(
            validate_skill.Finding(
                level,
                "S001",
                f"no scripts/tests/test_{s.stem}.py for {s.name}",
                f"scripts/{s.name}",
            )
        )
    return findings


def _extract_test_summary(stderr: str) -> str:
    lines = [l for l in stderr.splitlines() if l.strip()]
    summary_lines = [
        l for l in lines
        if l.startswith("Ran ") or l.strip() == "OK" or l.startswith("OK ") or l.startswith("FAILED")
    ]
    if summary_lines:
        return " / ".join(summary_lines[-3:])
    return lines[-1] if lines else ""


def run_tests(skill: Path) -> TestRun:
    """Run scripts/tests/ via unittest discover, cwd=skill. Caller must ensure
    scripts/tests/ exists first."""
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "scripts/tests", "-p", "test_*.py"],
        cwd=skill,
        capture_output=True,
        text=True,
    )
    return TestRun(ran=True, returncode=proc.returncode, summary=_extract_test_summary(proc.stderr))



def coverage_available() -> bool:
    """Whether the `coverage` package is importable. A function (not a module-level
    constant) so tests can monkeypatch it without needing the package installed."""
    return importlib.util.find_spec("coverage") is not None


def measure_coverage(skill: Path, threshold: int) -> CoverageResult:
    """Measure scripts/ coverage via a `coverage` subprocess. Caller must ensure
    scripts/tests/ exists and coverage_available() is True first. Uses a tempfile
    data-file path so no .coverage file lands inside the skill directory."""
    with tempfile.TemporaryDirectory() as td:
        data_file = str(Path(td) / ".coverage")
        json_file = f"{data_file}.json"
        subprocess.run(
            [
                sys.executable, "-m", "coverage", "run",
                f"--data-file={data_file}",
                "--source=scripts",
                "--omit=scripts/tests/*",
                "-m", "unittest", "discover", "-s", "scripts/tests", "-p", "test_*.py",
            ],
            cwd=skill,
            capture_output=True,
            text=True,
        )
        json_proc = subprocess.run(
            [sys.executable, "-m", "coverage", "json", f"--data-file={data_file}", "-o", json_file],
            cwd=skill,
            capture_output=True,
            text=True,
        )
        if json_proc.returncode != 0 or not Path(json_file).exists():
            return CoverageResult(percent=None, threshold=threshold)
        data = json.loads(Path(json_file).read_text(encoding="utf-8"))
        total = data.get("totals", {}).get("percent_covered")
        below = []
        for fname, finfo in data.get("files", {}).items():
            pct = finfo.get("summary", {}).get("percent_covered")
            if pct is not None and pct < threshold:
                below.append(fname)
        return CoverageResult(percent=total, threshold=threshold, below_threshold_files=sorted(below))


def check_headers(skill: Path, scripts: list[Path]) -> list[validate_skill.Finding]:
    findings: list[validate_skill.Finding] = []
    for s in scripts:
        try:
            text = s.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        first_line = text.splitlines()[0] if text else ""
        has_shebang = first_line.startswith("#!")
        has_exec = bool(s.stat().st_mode & stat.S_IXUSR)
        problems = []
        if not has_shebang:
            problems.append("missing shebang")
        if not has_exec:
            problems.append("missing owner-exec bit")
        if problems:
            findings.append(
                validate_skill.Finding(
                    "warning", "S005", f"{s.name}: {', '.join(problems)}", f"scripts/{s.name}"
                )
            )
    return findings


def check_hardcoded_paths(skill: Path, scripts: list[Path]) -> list[validate_skill.Finding]:
    findings: list[validate_skill.Finding] = []
    for s in scripts:
        try:
            text = s.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if IGNORE_LINE_RE.search(line):
                continue
            m = PERSONAL_SKILLS_PATH_RE.search(line)
            if m:
                findings.append(
                    validate_skill.Finding(
                        "warning",
                        "S006",
                        f"hardcoded personal skills path: {m.group(0)!r}",
                        f"scripts/{s.name}:{lineno}",
                    )
                )
    return findings


def _run_git(skill: Path, args: list[str]) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", *args], cwd=skill, capture_output=True, text=True)
    except FileNotFoundError:
        return None


def check_gitignore(skill: Path) -> list[validate_skill.Finding]:
    proc = _run_git(skill, ["rev-parse", "--is-inside-work-tree"])
    if proc is None or proc.returncode != 0 or proc.stdout.strip() != "true":
        return [
            validate_skill.Finding(
                "info", "S007", "not inside a git repository — .gitignore not checked", ""
            )
        ]
    # Directory candidates get a trailing slash in the query: git check-ignore only
    # matches a trailing-slash .gitignore pattern (scripts/__pycache__/) against a
    # queried path it can tell is a directory, and these paths need not exist yet.
    candidates = [
        (skill / "scripts" / "__pycache__", True),
        (skill / ".pytest_cache", True),
        (skill / ".coverage", False),
    ]
    unignored = []
    for c, is_dir in candidates:
        query = f"{c}/" if is_dir else str(c)
        cproc = _run_git(skill, ["check-ignore", "-q", query])
        if cproc is None:
            return [
                validate_skill.Finding(
                    "info", "S007", "not inside a git repository — .gitignore not checked", ""
                )
            ]
        if cproc.returncode != 0:
            unignored.append(str(c.relative_to(skill)))
    if unignored:
        return [
            validate_skill.Finding(
                "warning", "S007", f"not covered by .gitignore: {', '.join(unignored)}", ""
            )
        ]
    return []


def check(skill: Path, *, with_tests: bool = True, min_coverage: int = 90) -> ScriptsReport:
    report = ScriptsReport(skill_path=str(skill))

    scripts_dir = skill / "scripts"
    if not scripts_dir.is_dir():
        report.add("info", "S000", "no scripts/ directory — nothing to check")
        return report

    report.has_scripts = True
    scripts = find_scripts(skill)
    report.scripts = [s.relative_to(skill).as_posix() for s in scripts]

    report.findings.extend(check_test_presence(skill, scripts))

    tests_dir = scripts_dir / "tests"
    if not tests_dir.is_dir():
        report.add("info", "S002", "no scripts/tests/ directory — tests not run")
    elif not with_tests:
        report.add("info", "S002", "tests skipped (--no-tests)")
    else:
        tr = run_tests(skill)
        report.tests = tr
        if tr.returncode != 0:
            report.add("error", "S002", f"test run failed: {tr.summary}".rstrip())

        if not coverage_available():
            report.coverage = CoverageResult(threshold=min_coverage)
            report.add(
                "info", "S004",
                "coverage package not installed — run: python3 -m pip install coverage",
            )
        else:
            cr = measure_coverage(skill, min_coverage)
            report.coverage = cr
            if cr.percent is not None and (cr.percent < min_coverage or cr.below_threshold_files):
                below_msg = f"; below threshold: {', '.join(cr.below_threshold_files)}" if cr.below_threshold_files else ""
                report.add(
                    "warning", "S003",
                    f"coverage {cr.percent:.1f}% (threshold {min_coverage}%){below_msg}",
                )

    report.findings.extend(check_headers(skill, scripts))
    report.findings.extend(check_hardcoded_paths(skill, scripts))
    report.findings.extend(check_gitignore(skill))

    return report


def render_human(report: ScriptsReport) -> str:
    lines = [f"Skill: {report.skill_path}"]
    lines.append(f"  has_scripts: {report.has_scripts}")
    if report.has_scripts:
        lines.append(f"  scripts:     {len(report.scripts)}")
    if report.tests.ran:
        lines.append(f"  tests:       {report.tests.summary or '(no summary)'} (exit {report.tests.returncode})")
    else:
        lines.append("  tests:       not run")
    if report.coverage.percent is not None:
        lines.append(f"  coverage:    {report.coverage.percent:.1f}% (threshold {report.coverage.threshold}%)")
    lines.append("")

    if not report.findings:
        lines.append("OK — no issues.")
        return "\n".join(lines)

    by_level: dict[str, list[validate_skill.Finding]] = {"error": [], "warning": [], "info": []}
    for f in report.findings:
        by_level[f.level].append(f)
    for level in ("error", "warning", "info"):
        items = by_level[level]
        if not items:
            continue
        lines.append(f"{level.upper()}S ({len(items)}):")
        for f in items:
            loc = f" [{f.location}]" if f.location else ""
            lines.append(f"  {f.code}: {f.message}{loc}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="check_scripts.py",
        description="Verify scripts/ conventions (tests, coverage, headers, hardcoded paths, .gitignore) for a Claude Code skill.",
    )
    parser.add_argument("skill_path", type=Path, help="Path to the skill directory")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--no-tests", action="store_true", help="Skip running scripts/tests/")
    parser.add_argument("--min-coverage", type=int, default=90, help="Minimum coverage %% per file/total (default 90)")
    args = parser.parse_args(argv[1:])

    skill_path = args.skill_path.expanduser().resolve()
    if not skill_path.is_dir():
        print(f"error: not a directory: {skill_path}", file=sys.stderr)
        return 2

    report = check(skill_path, with_tests=not args.no_tests, min_coverage=args.min_coverage)

    if args.json:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    else:
        print(render_human(report))

    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
