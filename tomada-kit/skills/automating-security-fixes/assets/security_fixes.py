"""Turn open Dependabot alerts into a lock change the 7-day window admits.

The repository refuses any release younger than its supply-chain window
(`[tool.uv] exclude-newer` in pyproject.toml, `minimumReleaseAge` in
pnpm-workspace.yaml). Dependabot security updates skip their cooldown but not
that window, so a fix younger than it never reaches a pull request on its own.
This script, run daily by `.github/workflows/security-fixes.yml`, closes that gap
for `uv.lock` and `pnpm-lock.yaml`:

- It reads the repository's open Dependabot alerts and, per package, takes the
  highest first patched version among the alerts that still match a locked
  version. Only that version, the one an advisory names, may skip the window.
- A fix already older than the window is locked as is: `uv lock
  --upgrade-package` or `pnpm update --lockfile-only`, the same window bounding
  what they pick.
- A fix inside the window first gets a one-package exception: an absolute
  upload cutoff just after the fix in `[tool.uv.exclude-newer-package]`, or the
  exact `<name>@<version>` in `minimumReleaseAgeExclude`. Its comment names the
  advisories and the day the window admits the fix.
- An exception whose fix the window now admits is dropped, and the lock must not
  move when it is (`uv lock` keeps every version, `pnpm install
  --frozen-lockfile --lockfile-only` still passes).
- After locking, every version the lock newly holds is checked against the
  GitHub Advisory Database: Dependabot alerts only describe the versions locked
  before, so the newest release the window admits can carry an advisory of its
  own. One that does raises its package's target, and the lock is redone, a few
  rounds at most.
- No locked version may then still match an alert's or advisory's vulnerable
  range.

It edits the working tree only; the workflow commits, pushes, and opens the
pull request, and the owner merges it. Nothing runs while a pull request from
an earlier run is still open, so two runs never contend for a lockfile.

Usage:
    uv run --locked python scripts/security_fixes.py --out <dir> [--repo owner/name]

With a change, `<dir>` receives `title.txt` and `body.md` for the pull request;
without one it stays empty. Needs `gh` (authenticated, with Dependabot alerts
read access), `uv`, and `pnpm` on PATH, and network access to pypi.org and
registry.npmjs.org. Run by hand, it rewrites the lockfiles of your checkout.

Exit codes:
    0  a change was planned, or nothing needed one
    1  a failure, reported on stderr as ERR_FIXES_<KIND>; a failure in one
       lockfile leaves it as it was and still plans the other's change
    2  invalid arguments
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    type Entries = list[tuple[list[str], str]]

REPO_ROOT = Path(__file__).resolve().parents[1]
BRANCH_PREFIX = "automation/security-fixes/"
UV = "uv"
PNPM = "pnpm"
# Where Dependabot reports a package each lockfile locks.
MANIFESTS = {
    UV: frozenset({"uv.lock", "pyproject.toml", "backend/pyproject.toml"}),
    PNPM: frozenset(
        {"pnpm-lock.yaml", "package.json", "frontend/package.json", "e2e/package.json"}
    ),
}
ECOSYSTEMS = {UV: "pip", PNPM: "npm"}
UV_TABLE = "[tool.uv.exclude-newer-package]"
PNPM_KEY = "minimumReleaseAgeExclude"
TITLE_LIMIT = 72
# Relock rounds while newly locked versions keep turning up advisories.
ADVISORY_ROUNDS = 3
# Package specs per `affects=` query, to keep the URL short.
AFFECTS_BATCH = 20

_REPO = re.compile(r"^[\w.-]+/[\w.-]+$")
_VERSION = re.compile(r"^v?(\d+(?:\.\d+)*)$")
_COMPARATOR = re.compile(r"^\s*(<=|>=|<|>|=)?\s*(\S+)\s*$")
_UV_ENTRY = re.compile(
    r'^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*=\s*"(?P<value>[^"]+)"\s*$'
)
_UV_DAYS = re.compile(r"^\s*(\d+)\s*days?\s*$")
_UV_SPAN = re.compile(r"^P(\d+)D$")
_PNPM_AGE = re.compile(r"^minimumReleaseAge:\s*(\d+)\s*(?:#.*)?$", re.MULTILINE)
_PNPM_ITEM = re.compile(r"""^  - (?P<quote>["']?)(?P<value>[^"'#]+?)(?P=quote)\s*$""")
_PNPM_EXACT = re.compile(r"^(?P<name>@?[^@\s]+)@(?P<version>\d[\w.+-]*)$")
_PNPM_LOCK_KEY = re.compile(r"^  '?(?P<name>@?[^@'\s]+)@(?P<version>[^'():\s]+)'?:")


class SecurityFixError(Exception):
    """A failure reported as ``ERR_FIXES_<kind>`` with what was expected and what next."""

    def __init__(
        self, *, code: str, detail: str, expected: str, next_step: str
    ) -> None:
        """Keep the parts of the stderr report."""
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.expected = expected
        self.next_step = next_step


@dataclass(frozen=True, slots=True)
class Alert:
    """An advisory against one package.

    Either an open Dependabot alert, or a match in the GitHub Advisory Database
    for a version this run locked.
    """

    ecosystem: str
    package: str
    ghsa: str
    severity: str
    vulnerable: str
    patched: str | None
    url: str


@dataclass(slots=True)
class Fix:
    """The version one package must reach, and the alerts it closes."""

    ecosystem: str
    package: str
    target: str
    alerts: list[Alert]
    published: datetime | None = None
    exception: bool = False
    entry: str = ""


@dataclass(slots=True)
class Plan:
    """What one run changed, for the pull request body."""

    fixes: list[Fix] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    changes: dict[str, list[str]] = field(default_factory=dict)
    new_packages: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    failures: list[SecurityFixError] = field(default_factory=list)


# --------------------------------------------------------------------------- #
#  Versions
# --------------------------------------------------------------------------- #


def version_key(version: str) -> tuple[int, ...]:
    """Return a comparable key for a plain dotted release version.

    Raises:
        SecurityFixError: For anything but digits and dots (a pre-release, a
            post-release, a local version): this script will not guess an order.
    """
    match = _VERSION.match(version.strip())
    if match is None:
        raise SecurityFixError(
            code="ERR_FIXES_VERSION",
            detail=f"cannot compare version {version!r}",
            expected="a release version of digits and dots, such as 2026.10.19 or 1.4.2",
            next_step="fix this alert's package by hand (managing-dependencies)",
        )
    return tuple(int(part) for part in match[1].split("."))


def _compare(left: str, right: str) -> int:
    a, b = version_key(left), version_key(right)
    width = max(len(a), len(b))
    a += (0,) * (width - len(a))
    b += (0,) * (width - len(b))
    return (a > b) - (a < b)


def in_range(version: str, vulnerable: str) -> bool:
    """Return whether ``version`` matches a GitHub vulnerable version range.

    The range is comma-separated comparators, such as ``>= 20.26.6, <= 21.14.1``.
    """
    for part in vulnerable.split(","):
        match = _COMPARATOR.match(part)
        if match is None:
            raise SecurityFixError(
                code="ERR_FIXES_VERSION",
                detail=f"cannot read vulnerable range {vulnerable!r}",
                expected="comma-separated comparators such as '>= 1.0, < 1.4.2'",
                next_step="fix this alert's package by hand (managing-dependencies)",
            )
        op, bound = match[1] or "=", match[2]
        order = _compare(version, bound)
        held = {
            "<": order < 0,
            "<=": order <= 0,
            ">": order > 0,
            ">=": order >= 0,
            "=": order == 0,
        }[op]
        if not held:
            return False
    return True


def highest(versions: Iterable[str]) -> str:
    """Return the highest of ``versions``."""
    best: str | None = None
    for version in versions:
        if best is None or _compare(version, best) > 0:
            best = version
    if best is None:
        msg = "no versions"
        raise ValueError(msg)
    return best


def _normalize(ecosystem: str, name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower() if ecosystem == UV else name


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: str) -> datetime:
    moment = datetime.fromisoformat(value)
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


# --------------------------------------------------------------------------- #
#  External calls (tests replace these)
# --------------------------------------------------------------------------- #


def call(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a fixed argv (gh, uv, pnpm) in ``cwd``, capturing its output.

    Raises:
        SecurityFixError: When the program cannot start.
    """
    try:
        return subprocess.run(  # noqa: S603 -- fixed argv, no shell
            list(argv), cwd=cwd, check=False, capture_output=True, text=True
        )
    except OSError as error:
        raise SecurityFixError(
            code="ERR_FIXES_TOOL",
            detail=f"cannot run {argv[0]}: {error}",
            expected=f"{argv[0]} available on PATH and executable",
            next_step=f"install {argv[0]}, then rerun",
        ) from error


def fetch_json(url: str) -> Any:
    """Fetch a registry document over HTTPS.

    Raises:
        SecurityFixError: When the registry cannot be read.
    """
    request = urllib.request.Request(url, headers={"Accept": "application/json"})  # noqa: S310 -- fixed https hosts
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 -- fixed https hosts
            return json.load(response)
    except (OSError, ValueError) as error:
        raise SecurityFixError(
            code="ERR_FIXES_REGISTRY",
            detail=f"{url}: {error}",
            expected="the package registry reachable and the version published",
            next_step="rerun the workflow; if it persists, check the advisory's patched version",
        ) from error


def _gh_lines(path: str, jq: str, root: Path) -> list[dict[str, Any]]:
    result = call(["gh", "api", "--paginate", path, "--jq", jq], root)
    if result.returncode != 0:
        raise SecurityFixError(
            code="ERR_FIXES_GH",
            detail=f"gh api {path}: {result.stderr.strip()}",
            expected="gh authenticated with Dependabot alerts and pull requests read access",
            next_step=(
                "grant `vulnerability-alerts: read` and `pull-requests: read` "
                "(the workflow's plan job), or `gh auth login` locally"
            ),
        )
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def published_at(ecosystem: str, package: str, version: str) -> datetime:
    """Return when ``version`` became installable: its last file's upload time."""
    if ecosystem == UV:
        quoted = urllib.parse.quote(package, safe="")
        document = fetch_json(f"https://pypi.org/pypi/{quoted}/{version}/json")
        times = [file["upload_time_iso_8601"] for file in document.get("urls", [])]
        if not times:
            raise SecurityFixError(
                code="ERR_FIXES_REGISTRY",
                detail=f"PyPI lists no files for {package} {version}",
                expected="the advisory's patched version published with files",
                next_step="fix this package by hand (managing-dependencies)",
            )
        return max(_parse_time(stamp) for stamp in times)
    quoted = urllib.parse.quote(package, safe="@")
    document = fetch_json(f"https://registry.npmjs.org/{quoted}")
    stamp = document.get("time", {}).get(version)
    if not stamp:
        raise SecurityFixError(
            code="ERR_FIXES_REGISTRY",
            detail=f"the npm registry has no publish time for {package}@{version}",
            expected="the advisory's patched version published",
            next_step="fix this package by hand (managing-dependencies)",
        )
    return _parse_time(stamp)


# --------------------------------------------------------------------------- #
#  Alerts and pull requests
# --------------------------------------------------------------------------- #


def open_automation_pr(repo: str, root: Path) -> str | None:
    """Return the URL of an open pull request from an earlier run, if any."""
    for pull in _gh_lines(
        f"repos/{repo}/pulls?state=open&per_page=100",
        ".[] | {ref: .head.ref, url: .html_url}",
        root,
    ):
        if str(pull["ref"]).startswith(BRANCH_PREFIX):
            return str(pull["url"])
    return None


def read_alerts(repo: str, root: Path, notes: list[str]) -> list[Alert]:
    """Return the open alerts on `uv.lock` and the pnpm workspace; note the rest."""
    alerts: list[Alert] = []
    for raw in _gh_lines(
        f"repos/{repo}/dependabot/alerts?state=open&per_page=100", ".[]", root
    ):
        package = raw["dependency"]["package"]
        manifest = raw["dependency"].get("manifest_path", "")
        advisory = raw["security_advisory"]
        if advisory.get("withdrawn_at"):
            continue
        ecosystem = next(
            (
                name
                for name, upstream in ECOSYSTEMS.items()
                if package["ecosystem"] == upstream and manifest in MANIFESTS[name]
            ),
            None,
        )
        if ecosystem is None:
            notes.append(
                f"{advisory['ghsa_id']} ({package['ecosystem']} {package['name']} in "
                f"{manifest}): not a lockfile this workflow handles"
            )
            continue
        vulnerability = raw["security_vulnerability"]
        patched = (vulnerability.get("first_patched_version") or {}).get("identifier")
        alerts.append(
            Alert(
                ecosystem=ecosystem,
                package=_normalize(ecosystem, package["name"]),
                ghsa=advisory["ghsa_id"],
                severity=advisory.get("severity", ""),
                vulnerable=vulnerability["vulnerable_version_range"],
                patched=patched,
                url=raw.get("html_url", ""),
            )
        )
    return alerts


def plan_fixes(
    alerts: Sequence[Alert], locked: dict[str, set[str]], notes: list[str]
) -> list[Fix]:
    """Group one ecosystem's alerts by package and pick each package's target.

    An alert counts only while some locked version still matches its range. The
    target is the highest first patched version among those alerts, so one
    version closes all of them.
    """
    grouped: dict[str, list[Alert]] = {}
    for alert in alerts:
        grouped.setdefault(alert.package, []).append(alert)
    fixes: list[Fix] = []
    for package, group in sorted(grouped.items()):
        versions = locked.get(package, set())
        live = [a for a in group if any(in_range(v, a.vulnerable) for v in versions)]
        if not live:
            notes.append(
                f"{package}: no locked version matches its alerts any more; "
                "they close when the dependency graph next updates"
            )
            continue
        unpatched = [a.ghsa for a in live if a.patched is None]
        if unpatched:
            notes.append(
                f"{package}: no patched version yet for {', '.join(unpatched)}"
            )
        patched = [a for a in live if a.patched is not None]
        if patched:
            target = highest(a.patched for a in patched if a.patched is not None)
            fixes.append(Fix(group[0].ecosystem, package, target, patched))
    return fixes


def advisories_for(
    ecosystem: str, versions: dict[str, set[str]], root: Path
) -> list[Alert]:
    """Return the reviewed advisories that affect any of ``versions``.

    Reads the GitHub Advisory Database (`GET /advisories?affects=`), which any
    token can read, so a version no Dependabot alert describes yet is still
    judged.
    """
    upstream = ECOSYSTEMS[ecosystem]
    specs = sorted(
        f"{name}@{version}" for name, found in versions.items() for version in found
    )
    alerts: list[Alert] = []
    for start in range(0, len(specs), AFFECTS_BATCH):
        affects = urllib.parse.quote(
            ",".join(specs[start : start + AFFECTS_BATCH]), safe="@,/"
        )
        for raw in _gh_lines(
            f"advisories?ecosystem={upstream}&affects={affects}&per_page=100",
            ".[]",
            root,
        ):
            if raw.get("withdrawn_at"):
                continue
            for vulnerability in raw.get("vulnerabilities") or []:
                package = vulnerability.get("package") or {}
                name = _normalize(ecosystem, str(package.get("name", "")))
                vulnerable = vulnerability.get("vulnerable_version_range")
                if (
                    package.get("ecosystem") != upstream
                    or name not in versions
                    or not vulnerable
                    or not any(in_range(v, vulnerable) for v in versions[name])
                ):
                    continue
                patched = vulnerability.get("first_patched_version")
                if isinstance(patched, dict):
                    patched = patched.get("identifier")
                alerts.append(
                    Alert(
                        ecosystem=ecosystem,
                        package=name,
                        ghsa=raw["ghsa_id"],
                        severity=raw.get("severity", ""),
                        vulnerable=vulnerable,
                        patched=patched or None,
                        url=raw.get("html_url", ""),
                    )
                )
    return alerts


def unresolved(fix: Fix, locked: dict[str, set[str]]) -> list[str]:
    """Return the locked versions of ``fix.package`` that an alert still matches."""
    return sorted(
        version
        for version in locked.get(fix.package, set())
        if any(in_range(version, alert.vulnerable) for alert in fix.alerts)
    )


# --------------------------------------------------------------------------- #
#  The uv lockfile and its exceptions
# --------------------------------------------------------------------------- #


def uv_window(pyproject: str) -> timedelta:
    """Return `[tool.uv] exclude-newer` as a duration."""
    value = str(
        tomllib.loads(pyproject).get("tool", {}).get("uv", {}).get("exclude-newer", "")
    )
    match = _UV_DAYS.match(value) or _UV_SPAN.match(value)
    if match is None:
        raise SecurityFixError(
            code="ERR_FIXES_FILE",
            detail=f"pyproject.toml: [tool.uv] exclude-newer is {value!r}",
            expected='a relative day count such as "7 days"',
            next_step="restore the window (managing-dependencies)",
        )
    return timedelta(days=int(match[1]))


def uv_locked(lock: str) -> dict[str, set[str]]:
    """Return every package `uv.lock` locks, by normalized name."""
    locked: dict[str, set[str]] = {}
    for package in tomllib.loads(lock).get("package", []):
        if "version" in package:
            locked.setdefault(_normalize(UV, package["name"]), set()).add(
                package["version"]
            )
    return locked


def _uv_table_span(lines: list[str]) -> tuple[int, int]:
    try:
        start = lines.index(UV_TABLE)
    except ValueError:
        raise SecurityFixError(
            code="ERR_FIXES_FILE",
            detail=f"pyproject.toml has no {UV_TABLE} line",
            expected=f'the {UV_TABLE} table, empty or holding name = "cutoff" entries',
            next_step="restore the table (managing-dependencies)",
        ) from None
    end = start + 1
    while end < len(lines) and not lines[end].startswith("["):
        end += 1
    return start, end


def uv_exceptions(pyproject: str) -> dict[str, str]:
    """Return the `[tool.uv.exclude-newer-package]` entries."""
    lines = pyproject.splitlines()
    start, end = _uv_table_span(lines)
    entries: dict[str, str] = {}
    for line in lines[start + 1 : end]:
        match = _UV_ENTRY.match(line)
        if match:
            entries[_normalize(UV, match["name"])] = match["value"]
        elif line.strip() and not line.lstrip().startswith("#"):
            raise SecurityFixError(
                code="ERR_FIXES_FILE",
                detail=f"pyproject.toml: cannot read {line!r} in {UV_TABLE}",
                expected='one name = "YYYY-MM-DDTHH:MM:SSZ" entry per line, comments above it',
                next_step="rewrite the entry in that shape (managing-dependencies)",
            )
    return entries


def uv_drop(pyproject: str, package: str) -> str:
    """Remove ``package``'s entry and the comment lines directly above it."""
    lines = pyproject.splitlines()
    start, end = _uv_table_span(lines)
    for index in range(start + 1, end):
        match = _UV_ENTRY.match(lines[index])
        if match and _normalize(UV, match["name"]) == package:
            first = index
            while first - 1 > start and lines[first - 1].lstrip().startswith("#"):
                first -= 1
            del lines[first : index + 1]
            return "\n".join(lines) + "\n"
    return pyproject


def uv_add(pyproject: str, package: str, cutoff: str, comment: Sequence[str]) -> str:
    """Set ``package``'s cutoff, replacing an earlier entry for it."""
    lines = uv_drop(pyproject, package).splitlines()
    start, end = _uv_table_span(lines)
    last = start
    for index in range(start + 1, end):
        if _UV_ENTRY.match(lines[index]):
            last = index
    lines[last + 1 : last + 1] = [
        *(f"# {line}" for line in comment),
        f'{package} = "{cutoff}"',
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
#  The pnpm lockfile and its exceptions
# --------------------------------------------------------------------------- #


def pnpm_window(workspace: str) -> timedelta:
    """Return `minimumReleaseAge` (minutes) as a duration."""
    match = _PNPM_AGE.search(workspace)
    if match is None:
        raise SecurityFixError(
            code="ERR_FIXES_FILE",
            detail="pnpm-workspace.yaml has no integer minimumReleaseAge",
            expected="minimumReleaseAge: <minutes>",
            next_step="restore the window (managing-dependencies)",
        )
    return timedelta(minutes=int(match[1]))


def pnpm_locked(lock: str) -> dict[str, set[str]]:
    """Return every package `pnpm-lock.yaml`'s `packages:` sections lock."""
    locked: dict[str, set[str]] = {}
    inside = False
    for line in lock.splitlines():
        if line and not line.startswith(" "):
            inside = line.rstrip() == "packages:"
            continue
        match = _PNPM_LOCK_KEY.match(line) if inside else None
        if match:
            locked.setdefault(match["name"], set()).add(match["version"])
    return locked


def _pnpm_block(workspace: str) -> tuple[list[str], int, int, Entries]:
    lines = workspace.splitlines()
    key = next(
        (i for i, line in enumerate(lines) if line.startswith(f"{PNPM_KEY}:")), None
    )
    if key is None:
        raise SecurityFixError(
            code="ERR_FIXES_FILE",
            detail=f"pnpm-workspace.yaml has no {PNPM_KEY} key",
            expected=f"{PNPM_KEY}: [] or a block list of quoted entries",
            next_step="restore the key (managing-dependencies' references/pnpm.md)",
        )
    rest = lines[key][len(PNPM_KEY) + 1 :].split("#", 1)[0].strip()
    entries: Entries = []
    end = key + 1
    if rest == "[]":
        return lines, key, end, entries
    if rest:
        raise SecurityFixError(
            code="ERR_FIXES_FILE",
            detail=f"pnpm-workspace.yaml: {PNPM_KEY} is the flow value {rest!r}",
            expected=f"{PNPM_KEY}: [] or a block list, one '  - \"entry\"' per line",
            next_step="rewrite it as a block list",
        )
    comments: list[str] = []
    while end < len(lines) and lines[end].startswith("  "):
        line = lines[end]
        if line.lstrip().startswith("#"):
            comments.append(line.strip()[1:].strip())
        else:
            match = _PNPM_ITEM.match(line)
            if match is None:
                raise SecurityFixError(
                    code="ERR_FIXES_FILE",
                    detail=f"pnpm-workspace.yaml: cannot read {line!r} in {PNPM_KEY}",
                    expected="one '  - \"entry\"' per line, comments above it",
                    next_step="rewrite the entry in that shape",
                )
            entries.append((comments, match["value"].strip()))
            comments = []
        end += 1
    return lines, key, end, entries


def pnpm_exceptions(workspace: str) -> list[str]:
    """Return the `minimumReleaseAgeExclude` entries."""
    return [value for _, value in _pnpm_block(workspace)[3]]


def _pnpm_render(workspace: str, update: Callable[[Entries], Entries]) -> str:
    lines, key, end, entries = _pnpm_block(workspace)
    entries = update(entries)
    block = [f"{PNPM_KEY}: []"] if not entries else [f"{PNPM_KEY}:"]
    for comments, value in entries:
        block.extend(f"  # {comment}" for comment in comments)
        block.append(f'  - "{value}"')
    lines[key:end] = block
    return "\n".join(lines) + "\n"


def pnpm_drop(workspace: str, value: str) -> str:
    """Remove one `minimumReleaseAgeExclude` entry and its comments."""
    return _pnpm_render(
        workspace, lambda entries: [entry for entry in entries if entry[1] != value]
    )


def pnpm_add(workspace: str, value: str, comment: Sequence[str]) -> str:
    """Append one `minimumReleaseAgeExclude` entry, once."""
    return _pnpm_render(
        workspace,
        lambda entries: (
            entries
            if any(existing == value for _, existing in entries)
            else [*entries, (list(comment), value)]
        ),
    )


# --------------------------------------------------------------------------- #
#  The run
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Context:
    """One run: the checkout it edits, the time it judges by, and its windows."""

    root: Path
    now: datetime
    windows: dict[str, timedelta]
    plan: Plan

    @property
    def pyproject(self) -> Path:
        """The workspace root's pyproject.toml."""
        return self.root / "pyproject.toml"

    @property
    def uv_lock(self) -> Path:
        """The workspace's uv.lock."""
        return self.root / "uv.lock"

    @property
    def workspace(self) -> Path:
        """pnpm-workspace.yaml."""
        return self.root / "pnpm-workspace.yaml"

    @property
    def pnpm_lock(self) -> Path:
        """pnpm-lock.yaml."""
        return self.root / "pnpm-lock.yaml"


def _checked(argv: Sequence[str], root: Path, what: str) -> None:
    result = call(argv, root)
    if result.returncode != 0:
        tail = "\n".join((result.stderr or result.stdout).strip().splitlines()[-15:])
        raise SecurityFixError(
            code="ERR_FIXES_LOCK",
            detail=f"`{' '.join(argv)}` failed while {what}:\n{tail}",
            expected="the lockfile resolves under the window and the exceptions above",
            next_step=(
                "read the output; a fix that needs another too-new package or a "
                "parent's wider range is the owner's call (managing-dependencies)"
            ),
        )


def _comment(fix: Fix, published: datetime, admitted: datetime) -> list[str]:
    ghsas = ", ".join(sorted({alert.ghsa for alert in fix.alerts}))
    return [
        # No package name: typos would flag some, and the entry below names it.
        f"{ghsas}: version {fix.target}, published {_stamp(published)}.",
        f"The window admits it from {_stamp(admitted)}; the next run after drops this.",
    ]


def _record_changes(
    ctx: Context,
    ecosystem: str,
    before: dict[str, set[str]],
    after: dict[str, set[str]],
) -> None:
    for name in sorted(before.keys() | after.keys()):
        old, new = before.get(name, set()), after.get(name, set())
        if old != new:
            ctx.plan.changes.setdefault(ecosystem, []).append(
                f"`{name}`: {', '.join(sorted(old)) or '(none)'} → "
                f"{', '.join(sorted(new)) or '(none)'}"
            )
    ctx.plan.new_packages.extend(
        f"`{name}` ({ecosystem})" for name in sorted(after.keys() - before.keys())
    )


def drop_expired_uv(ctx: Context) -> None:
    """Drop every uv exception the window has caught up with; the lock must not move."""
    pyproject = ctx.pyproject.read_text(encoding="utf-8")
    window = ctx.windows[UV]
    expired = {
        name: cutoff
        for name, cutoff in uv_exceptions(pyproject).items()
        if ctx.now >= _parse_time(cutoff) + window
    }
    if not expired:
        return
    lock = ctx.uv_lock.read_text(encoding="utf-8")
    edited = pyproject
    for name in expired:
        edited = uv_drop(edited, name)
    ctx.pyproject.write_text(edited, encoding="utf-8")
    _checked(["uv", "lock"], ctx.root, "dropping expired exclude-newer-package entries")
    if uv_locked(ctx.uv_lock.read_text(encoding="utf-8")) != uv_locked(lock):
        ctx.pyproject.write_text(pyproject, encoding="utf-8")
        ctx.uv_lock.write_text(lock, encoding="utf-8")
        raise SecurityFixError(
            code="ERR_FIXES_EXPIRY",
            detail=f"dropping {sorted(expired)} would move locked versions",
            expected="an expired entry's fix inside the window, so the lock stays put",
            next_step="compare the entry's cutoff with the release's upload times by hand",
        )
    ctx.plan.dropped.extend(
        f"`{name}` (uv.lock): cutoff {cutoff}; the window has admitted it since "
        f"{_parse_time(cutoff) + window:%Y-%m-%d}"
        for name, cutoff in expired.items()
    )


def drop_expired_pnpm(ctx: Context) -> None:
    """Drop every exact-version pnpm exception the window admits; installs must pass."""
    workspace = ctx.workspace.read_text(encoding="utf-8")
    expired: list[str] = []
    for value in pnpm_exceptions(workspace):
        match = _PNPM_EXACT.match(value)
        if match is None:
            ctx.plan.notes.append(f"`{value}` in {PNPM_KEY} is not one exact version")
        else:
            published = published_at(PNPM, match["name"], match["version"])
            if ctx.now >= published + ctx.windows[PNPM]:
                expired.append(value)
    if not expired:
        return
    edited = workspace
    for value in expired:
        edited = pnpm_drop(edited, value)
    ctx.workspace.write_text(edited, encoding="utf-8")
    try:
        _checked(
            ["pnpm", "install", "--frozen-lockfile", "--lockfile-only"],
            ctx.root,
            f"checking the lock without {expired}",
        )
    except SecurityFixError as error:
        ctx.workspace.write_text(workspace, encoding="utf-8")
        raise SecurityFixError(
            code="ERR_FIXES_EXPIRY",
            detail=f"the lock fails the window without {expired}:\n{error.detail}",
            expected="an expired entry's version inside the window, so installs still pass",
            next_step="compare the entry's version with its npm publish time by hand",
        ) from error
    ctx.plan.dropped.extend(
        f"`{value}` (pnpm-lock.yaml): the window admits it now" for value in expired
    )


def _add_exception(ctx: Context, fix: Fix, published: datetime) -> None:
    admitted = published + ctx.windows[fix.ecosystem]
    comment = _comment(fix, published, admitted)
    if fix.ecosystem == UV:
        # uv admits a file uploaded before the cutoff, so a second past the
        # fix's last upload admits the fix and nothing published after it.
        cutoff = _stamp(published.replace(microsecond=0) + timedelta(seconds=1))
        text = ctx.pyproject.read_text(encoding="utf-8")
        ctx.pyproject.write_text(
            uv_add(text, fix.package, cutoff, comment), encoding="utf-8"
        )
    else:
        text = ctx.workspace.read_text(encoding="utf-8")
        ctx.workspace.write_text(
            pnpm_add(text, f"{fix.package}@{fix.target}", comment), encoding="utf-8"
        )


def _raise_targets(
    ecosystem: str, fixes: dict[str, Fix], found: list[Alert]
) -> set[str]:
    """Fold advisories on newly locked versions into the fixes; return raised ones."""
    raised: set[str] = set()
    for alert in found:
        fix = fixes.get(alert.package)
        if fix is None:
            if alert.patched is None:
                fix = Fix(ecosystem, alert.package, "0", [])
            else:
                fix = Fix(ecosystem, alert.package, alert.patched, [])
                raised.add(alert.package)
            fixes[alert.package] = fix
        if all(
            (a.ghsa, a.vulnerable) != (alert.ghsa, alert.vulnerable) for a in fix.alerts
        ):
            fix.alerts.append(alert)
        if alert.patched is not None and _compare(alert.patched, fix.target) > 0:
            fix.target = alert.patched
            raised.add(alert.package)
    return raised


def _set_exception(ctx: Context, fix: Fix) -> None:
    """Judge ``fix.target`` against the window and add its exception if needed."""
    previous = f"{fix.package}@{fix.target}"
    if fix.ecosystem == PNPM and fix.exception and fix.entry and fix.entry != previous:
        text = ctx.workspace.read_text(encoding="utf-8")
        ctx.workspace.write_text(pnpm_drop(text, fix.entry), encoding="utf-8")
    fix.published = published_at(fix.ecosystem, fix.package, fix.target)
    fix.exception = ctx.now < fix.published + ctx.windows[fix.ecosystem]
    if fix.exception:
        _add_exception(ctx, fix, fix.published)
        fix.entry = previous


def apply_fixes(ctx: Context, ecosystem: str, fixes: list[Fix]) -> None:
    """Add the exceptions the fixes need, relock, and check no advisory still matches.

    Every version the relock newly holds is looked up in the GitHub Advisory
    Database; an advisory there raises its package's target (or adds the
    package), and the lock is redone, up to ``ADVISORY_ROUNDS`` times.
    """
    if not fixes:
        return
    lock_path = ctx.uv_lock if ecosystem == UV else ctx.pnpm_lock
    read_locked = uv_locked if ecosystem == UV else pnpm_locked
    before = read_locked(lock_path.read_text(encoding="utf-8"))
    by_package = {fix.package: fix for fix in fixes}
    pending = set(by_package)
    argv: list[str] = []
    after = before
    for _ in range(ADVISORY_ROUNDS):
        for name in sorted(pending):
            if by_package[name].target != "0":
                _set_exception(ctx, by_package[name])
        names = sorted(name for name, fix in by_package.items() if fix.target != "0")
        if ecosystem == UV:
            argv = ["uv", "lock", *(f"--upgrade-package={name}" for name in names)]
        else:
            argv = [
                "pnpm",
                "update",
                "--recursive",
                "--lockfile-only",
                "--no-save",
                *names,
            ]
        _checked(argv, ctx.root, f"upgrading {', '.join(names)}")
        after = read_locked(lock_path.read_text(encoding="utf-8"))
        moved = {
            name: found - before.get(name, set())
            for name, found in after.items()
            if found - before.get(name, set())
        }
        pending = _raise_targets(
            ecosystem, by_package, advisories_for(ecosystem, moved, ctx.root)
        )
        if not pending:
            break
    for fix in by_package.values():
        left = unresolved(fix, after)
        if left:
            unpatched = sorted(
                {
                    a.ghsa
                    for a in fix.alerts
                    if a.patched is None
                    and any(in_range(v, a.vulnerable) for v in left)
                }
            )
            reason = (
                f"{', '.join(unpatched)} has no patched version"
                if unpatched
                else f"{fix.target} closes its advisories"
            )
            raise SecurityFixError(
                code="ERR_FIXES_UNRESOLVED",
                detail=(
                    f"{fix.package} is still locked at {', '.join(left)} after "
                    f"`{' '.join(argv)}`; {reason}"
                ),
                expected=f"no locked {fix.package} inside its advisories' vulnerable ranges",
                next_step=(
                    "a dependent's range likely holds it back, or the newest admitted "
                    "release is itself vulnerable: an override or a parent upgrade is "
                    "the owner's call (managing-dependencies)"
                ),
            )
    _record_changes(ctx, ecosystem, before, after)
    ctx.plan.fixes.extend(by_package.values())


def title(plan: Plan) -> str:
    """Return a Conventional Commits title within the PR title limit."""
    if not plan.fixes:
        return "deps: drop expired release-window exceptions"
    prefix = "deps: fix security alerts in "
    names = [fix.package for fix in plan.fixes]
    for count in range(len(names), 0, -1):
        more = len(names) - count
        listed = ", ".join(names[:count]) + (f" and {more} more" if more else "")
        if len(prefix + listed) <= TITLE_LIMIT:
            return prefix + listed
    return f"{prefix}{len(names)} packages"


def _fix_row(fix: Fix, window: timedelta) -> str:
    lockfile = "uv.lock" if fix.ecosystem == UV else "pnpm-lock.yaml"
    advisories = ", ".join(
        f"[{alert.ghsa}]({alert.url}) ({alert.severity})" if alert.url else alert.ghsa
        for alert in sorted(fix.alerts, key=lambda a: a.ghsa)
    )
    if fix.exception and fix.published is not None:
        status = f"exception until {fix.published + window:%Y-%m-%d}"
    else:
        status = "already outside the window"
    return f"| `{fix.package}` | {lockfile} | {fix.target} | {advisories} | {status} |"


def body(plan: Plan, windows: dict[str, timedelta], run_url: str) -> str:
    """Return the pull request body, in the PR template's order."""
    source = f" ([run]({run_url}))" if run_url else ""
    lines = [
        "## Summary",
        "",
        (
            f"Opened by `.github/workflows/security-fixes.yml`{source} from the open "
            "Dependabot alerts. Nothing merges on its own: the owner reviews and merges "
            "(managing-dependencies, merging-dependency-prs)."
        ),
    ]
    if plan.fixes:
        lines += [
            "",
            "### Fixes",
            "",
            "| Package | Lockfile | Target | Advisories | Window |",
            "|---|---|---|---|---|",
        ]
        lines += [_fix_row(fix, windows[fix.ecosystem]) for fix in plan.fixes]
    if plan.dropped:
        lines += ["", "### Expired exceptions dropped", ""]
        lines += [f"- {item}" for item in plan.dropped]
    if plan.changes:
        lines += ["", "### Locked versions that moved", ""]
        for ecosystem, items in plan.changes.items():
            lines += [f"- {ecosystem}: {item}" for item in items]
    if plan.new_packages:
        lines += [
            "",
            "### Needs the owner's review",
            "",
            (
                "The lock gained packages it did not hold before. Each needs "
                "managing-dependencies' review record before this merges:"
            ),
            "",
        ]
        lines += [f"- {item}" for item in plan.new_packages]
    if plan.failures:
        lines += [
            "",
            "### Failed in this run",
            "",
            "These left their lockfile as it was; the run's log has the full report.",
            "",
        ]
        lines += [
            f"- `{error.code}`: {error.detail.splitlines()[0]}"
            for error in plan.failures
        ]
    if plan.notes:
        lines += ["", "### Alerts not handled here", ""]
        lines += [f"- {note}" for note in plan.notes]
    lines += ["", "## Test Plan", ""]
    if plan.fixes:
        lines.append(
            "- The workflow relocked under the window and the exceptions above, "
            "checked every newly locked version against the GitHub Advisory Database, "
            "and checked that no locked version still matches an advisory's vulnerable "
            "range."
        )
    if plan.dropped:
        lines.append(
            "- Dropped exceptions: `uv lock` kept every locked version, and "
            "`pnpm install --frozen-lockfile --lockfile-only` passed without them."
        )
    lines += [
        "- The workflow ran no `just verify` and no commit hooks; CI on this PR is the gate.",
        "",
        "## Checklist",
        "",
        (
            "- [ ] Local verification evidence recorded for the committed tree "
            "(`just verify`; any host restriction documented)"
        ),
        "- [ ] Every expected CI check passes on the current head before merge",
        "- [ ] Docs updated, if a user-facing behavior, command, or setting changed",
        "- [ ] Breaking changes called out in the Summary",
        "",
    ]
    return "\n".join(lines)


def plan_run(repo: str, root: Path, now: datetime) -> Context | None:
    """Edit the working tree for one run; return None when an earlier PR is open."""
    pull = open_automation_pr(repo, root)
    if pull is not None:
        print(f"An earlier security-fix pull request is still open: {pull}")
        return None
    windows = {
        UV: uv_window((root / "pyproject.toml").read_text(encoding="utf-8")),
        PNPM: pnpm_window((root / "pnpm-workspace.yaml").read_text(encoding="utf-8")),
    }
    ctx = Context(root=root, now=now, windows=windows, plan=Plan())
    alerts = read_alerts(repo, root, ctx.plan.notes)
    for ecosystem in (UV, PNPM):
        _plan_ecosystem(ctx, ecosystem, [a for a in alerts if a.ecosystem == ecosystem])
    return ctx


def _plan_ecosystem(ctx: Context, ecosystem: str, alerts: list[Alert]) -> None:
    """Change one ecosystem's files, or leave them and its plan as they were.

    A failure in one lockfile must not hold back the other's fixes, so it is
    recorded and the run goes on; `main` still exits 1 for it.
    """
    paths = (
        (ctx.pyproject, ctx.uv_lock)
        if ecosystem == UV
        else (ctx.workspace, ctx.pnpm_lock)
    )
    saved = {path: path.read_text(encoding="utf-8") for path in paths}
    plan = ctx.plan
    sizes = (
        len(plan.fixes),
        len(plan.dropped),
        len(plan.new_packages),
        len(plan.notes),
    )
    try:
        if ecosystem == UV:
            drop_expired_uv(ctx)
        else:
            drop_expired_pnpm(ctx)
        read_locked = uv_locked if ecosystem == UV else pnpm_locked
        locked = read_locked(paths[1].read_text(encoding="utf-8"))
        apply_fixes(ctx, ecosystem, plan_fixes(alerts, locked, plan.notes))
    except SecurityFixError as error:
        for path, text in saved.items():
            path.write_text(text, encoding="utf-8")
        del plan.fixes[sizes[0] :], plan.dropped[sizes[1] :]
        del plan.new_packages[sizes[2] :], plan.notes[sizes[3] :]
        plan.changes.pop(ecosystem, None)
        plan.failures.append(error)
        _report(error)


def _report(error: SecurityFixError) -> None:
    print(f"{error.code}: {error.detail}", file=sys.stderr)
    print(f"Expected: {error.expected}", file=sys.stderr)
    print(f"Next: {error.next_step}", file=sys.stderr)


def main(argv: list[str] | None = None, root: Path = REPO_ROOT) -> int:
    """Plan one run's lock change into the working tree and return an exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", type=Path, required=True, help="where title.txt and body.md go"
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="owner/name (default: $GITHUB_REPOSITORY)",
    )
    parser.add_argument(
        "--now", help="ISO 8601 time to judge the windows against (default: now)"
    )
    args = parser.parse_args(argv)
    if not _REPO.match(args.repo):
        parser.error(f"--repo must be owner/name, not {args.repo!r}")
    try:
        now = _parse_time(args.now) if args.now else datetime.now(UTC)
    except ValueError:
        parser.error(f"--now must be an ISO 8601 time, not {args.now!r}")
    try:
        ctx = plan_run(args.repo, root, now)
    except SecurityFixError as error:
        _report(error)
        return 1
    if ctx is None:
        return 0
    plan = ctx.plan
    failed = 1 if plan.failures else 0
    for note in plan.notes:
        print(f"note: {note}")
    if not plan.fixes and not plan.dropped:
        print("No security fix or expired exception to act on.")
        return failed
    server = os.environ.get("GITHUB_SERVER_URL", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_url = f"{server}/{args.repo}/actions/runs/{run_id}" if server and run_id else ""
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "title.txt").write_text(title(plan) + "\n", encoding="utf-8")
    (args.out / "body.md").write_text(
        body(plan, ctx.windows, run_url), encoding="utf-8"
    )
    print(title(plan))
    return failed


if __name__ == "__main__":
    sys.exit(main())
