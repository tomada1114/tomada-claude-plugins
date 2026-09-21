#!/usr/bin/env python3
"""create_issues.py — Turn a transplant plan.json into GitHub issues.

Reads the fixed `plan.json` contract (see references/github-mechanics.md) —
one tracking issue plus a set of dependent issues, each with a Markdown body
file — and either previews the creation order (default) or files everything
on GitHub (`--apply`). The model that wrote plan.json does not touch GitHub
directly; this script is deterministic so the same plan always produces the
same issues, labels and dependency edges.

Usage:
    create_issues.py <plan.json> [--apply] [--json]

Without --apply this is a dry run: the plan is validated and the creation
order is printed. No GitHub write of any kind is made (a best-effort local
`git remote` read is the only external call, used to catch a plan.json
pointed at the wrong repo before anything is filed).

With --apply, in order:
    1. every label in plan.json plus the `priority: Pn` / `blocked: design`
       labels actually used are created or updated (never deleted);
    2. existing issues carrying this plan's `<!-- harness-transplant: ... -->`
       marker are found and reused instead of re-created;
    3. the tracking issue, then every issue in creation order, is filed via
       the REST API with its body's `{{#key}}` placeholders still unresolved;
    4. every body is PATCHed with placeholders resolved, a `## Dependencies`
       section, the `<!-- ship: ... -->` contract and the marker appended;
    5. native sub-issue / blocked-by links are attempted — a failure here is
       a warning, never fatal, because the same edges are already carried in
       the body text and the ship contract.

`created.json`, written next to plan.json after every successful creation,
is what lets a crashed or interrupted run resume without filing duplicates.

Exit codes:
    0 = dry run printed, or --apply completed (link warnings do not affect this)
    1 = a `gh` call failed (ERR_GH_*) — created.json reflects what succeeded
    2 = plan.json is missing/malformed, or fails validation (ERR_PLAN_*) —
        every error is reported, not just the first
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# --- constants ---------------------------------------------------------

# P0 is the highest urgency; index doubles as the sort/comparison rank.
PRIORITY_ORDER = ["P0", "P1", "P2", "P3"]

# Default colors/descriptions for the labels this script may need to create
# on a repo that does not already define them. Deliberately independent of
# any sibling skill's copy of the same idea (shipping-issues/scripts/issue_digest.py
# defines its own) — nothing here is imported across skills.
PRIORITY_LABELS: dict[str, tuple[str, str, str]] = {
    "P0": ("priority: P0", "b60205", "Ship now"),
    "P1": ("priority: P1", "d93f0b", "Do next"),
    "P2": ("priority: P2", "fbca04", "Normal"),
    "P3": ("priority: P3", "0e8a16", "Defer"),
}
DESIGN_LABEL: tuple[str, str, str] = (
    "blocked: design", "5319e7", "Design/approach not settled — decide it before implementing",
)
DEFAULT_LABEL_COLOR = "ededed"

KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PLACEHOLDER_RE = re.compile(r"\{\{#([a-zA-Z0-9_-]+)\}\}")

# Reserved-content detection: a body this script will own must not already
# carry a hand-written copy of what pass 2 appends.
DEPENDENCIES_HEADING_RE = re.compile(r"(?im)^##\s+Dependencies\s*$")
# Same shape as shipping-issues/scripts/issue_digest.py's SHIP_CONTRACT_RE —
# kept in sync by hand since a script never imports a sibling skill's code.
SHIP_CONTRACT_RE = re.compile(r"<!--\s*ship\s*:(.*?)-->", re.DOTALL | re.IGNORECASE)
RESERVED_MARKER_RE = re.compile(r"<!--\s*harness-transplant\s*:.*?-->", re.DOTALL | re.IGNORECASE)
# Downstream tooling (shipping-issues' issue_digest.py) scrapes dependency edges out
# of prose with phrasings like these and unions them with the declared ones, so
# "after {{#x}}" in a sentence becomes a real blocker. Mirrors its DEP_PATTERNS, with
# the placeholder standing in for the number that does not exist yet.
_PH = r"\{\{#([a-zA-Z0-9_-]+)\}\}"
STRAY_DEP_PATTERNS = [
    (re.compile(r"(?:depends?\s+on|blocked\s+by|after|requires?)\s*:?\s*" + _PH, re.IGNORECASE), "depends_on"),
    (re.compile(r"(?:blocks|blocking)\s*:?\s*" + _PH, re.IGNORECASE), "blocks"),
    (re.compile(_PH + r"\s*(?:に依存|の後|完了後|がマージされてから|の続き)"), "depends_on"),
    (re.compile(r"(?:前提|依存|ブロッカー|先行)\s*:?\s*" + _PH), "depends_on"),
    (re.compile(_PH + r"\s*(?:をブロック|の前提)"), "blocks"),
]

# Things only the planning session can see. An implementer reads the issue in
# another checkout, where neither the plan file nor a home-directory path exists.
OUT_OF_REPO_RE = re.compile(r"plan\.json|(?<![\w.])/(?:Users|home)/[^\s`)]+|~/[^\s`)]+")
# The strict form this script itself writes and later scans for, capturing
# the key back out.
SCAN_MARKER_RE = re.compile(
    r"<!--\s*harness-transplant\s*:\s*key=([a-z0-9][a-z0-9-]*|tracking)\s*-->",
    re.IGNORECASE,
)


def marker(key: str) -> str:
    return f"<!-- harness-transplant: key={key} -->"


# --- data model ----------------------------------------------------------


@dataclass
class PlanIssue:
    key: str
    title: str
    body_file: str
    body: str
    priority: str
    labels: list[str]
    depends_on: list[str]
    area: str
    touches: list[str]
    design: str  # "settled" | "open"


@dataclass
class TrackingInfo:
    title: str
    body_file: str
    body: str
    labels: list[str]


@dataclass
class Plan:
    repo: str
    labels: list[dict[str, str]]
    tracking: TrackingInfo
    issues: list[PlanIssue]
    path: Path


@dataclass
class CreatedEntry:
    number: int
    id: int
    url: str


@dataclass
class ValidationError:
    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code}: {self.message}"


class GhError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


# --- plan loading ----------------------------------------------------------


def load_plan_json(path: Path) -> tuple[Any, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, f"ERR_PLAN_NOT_FOUND: {path} does not exist"
    except OSError as exc:
        return None, f"ERR_PLAN_NOT_FOUND: cannot read {path}: {exc}"
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f"ERR_PLAN_INVALID_JSON: {path}: {exc}"


def read_body_file(path: Path) -> tuple[str, tuple[str, str] | None]:
    """(text, None) on success, or ("", (code, message)) naming the problem."""
    if not path.is_file():
        return "", ("ERR_PLAN_BODY_MISSING", f"body file not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return "", ("ERR_PLAN_BODY_MISSING", f"cannot read body file {path}: {exc}")
    if not text.strip():
        return "", ("ERR_PLAN_BODY_EMPTY", f"body file is empty: {path}")
    return text, None


def reserved_content_errors(label: str, body: str) -> list[ValidationError]:
    found: list[ValidationError] = []
    if DEPENDENCIES_HEADING_RE.search(body):
        found.append(ValidationError(
            "ERR_PLAN_RESERVED_CONTENT",
            f"{label} body already contains a hand-written '## Dependencies' heading "
            "— the script owns that section",
        ))
    if SHIP_CONTRACT_RE.search(body):
        found.append(ValidationError(
            "ERR_PLAN_RESERVED_CONTENT",
            f"{label} body already contains a '<!-- ship: ... -->' contract — the "
            "script owns that comment",
        ))
    if RESERVED_MARKER_RE.search(body):
        found.append(ValidationError(
            "ERR_PLAN_RESERVED_CONTENT",
            f"{label} body already contains a '<!-- harness-transplant: ... -->' "
            "marker — the script owns that comment",
        ))
    leaks = sorted(set(OUT_OF_REPO_RE.findall(body)))
    if leaks:
        found.append(ValidationError(
            "ERR_PLAN_OUT_OF_REPO_REF",
            f"{label} body refers to something the implementer cannot open "
            f"({', '.join(leaks[:5])}) — cite in-repo paths and the issue's own "
            "Dependencies section instead",
        ))
    return found


def stray_dependency_errors(key: str, body: str, depends_on: list[str],
                            blocks: list[str]) -> list[ValidationError]:
    declared = {"depends_on": set(depends_on), "blocks": set(blocks)}
    found: list[ValidationError] = []
    for pattern, kind in STRAY_DEP_PATTERNS:
        for m in pattern.finditer(body):
            other = m.group(1)
            if other == key or other in declared[kind]:
                continue
            phrase = " ".join(m.group(0).split())
            found.append(ValidationError(
                "ERR_PLAN_STRAY_DEPENDENCY_PHRASE",
                f"issue {key!r} body says '{phrase}', which downstream tooling reads as a "
                f"{kind} edge that the plan does not declare — add {other!r} to the plan's "
                "edges or reword (e.g. 'once ... lands')",
            ))
    return found


def resolve_local_repo(cwd: Path) -> str | None:
    """`owner/repo` from `git remote get-url origin` at cwd, or None.

    Best-effort and silent on any failure: this is a courtesy check (plan.json
    pointed at the wrong repo), not a hard requirement, so a caller validating
    a plan outside a git checkout — including every test in this suite —
    simply gets no repo-mismatch check rather than a crash.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(cwd), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    url = (proc.stdout or "").strip()
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def validate_plan(
    raw: Any, plan_path: Path, *, local_repo: str | None = None
) -> tuple[Plan | None, list[ValidationError]]:
    """Validate plan.json's contract, collecting every error rather than
    stopping at the first. Returns (Plan, []) only when there are none."""
    errors: list[ValidationError] = []

    def err(code: str, message: str) -> None:
        errors.append(ValidationError(code, message))

    if not isinstance(raw, dict):
        err("ERR_PLAN_MISSING_FIELD", "plan.json must contain a JSON object")
        return None, errors

    repo = raw.get("repo")
    if not isinstance(repo, str) or not repo.strip():
        err("ERR_PLAN_MISSING_FIELD", "top-level 'repo' is required and must be a non-empty string")
        repo = None
    elif "/" not in repo.strip("/"):
        err("ERR_PLAN_MISSING_FIELD", f"'repo' must look like owner/name, got {repo!r}")

    if repo and local_repo and repo.lower() != local_repo.lower():
        err(
            "ERR_PLAN_REPO_MISMATCH",
            f"plan.json targets {repo!r} but this command is running against "
            f"{local_repo!r} — run from inside the target repository or fix plan.repo",
        )

    labels_raw = raw.get("labels", [])
    if not isinstance(labels_raw, list):
        err("ERR_PLAN_MISSING_FIELD", "top-level 'labels' must be a list")
        labels_raw = []
    labels: list[dict[str, str]] = []
    for i, entry in enumerate(labels_raw):
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not entry["name"].strip():
            err("ERR_PLAN_MISSING_FIELD", f"labels[{i}] must be an object with a non-empty 'name'")
            continue
        labels.append({
            "name": entry["name"],
            "color": (entry.get("color") or DEFAULT_LABEL_COLOR),
            "description": (entry.get("description") or ""),
        })

    tracking_raw = raw.get("tracking")
    tracking: TrackingInfo | None = None
    if not isinstance(tracking_raw, dict):
        err("ERR_PLAN_MISSING_FIELD", "top-level 'tracking' object is required")
    else:
        t_title = tracking_raw.get("title")
        t_body_file = tracking_raw.get("body_file")
        t_labels_raw = tracking_raw.get("labels", [])
        tracking_ok = True
        if not isinstance(t_title, str) or not t_title.strip():
            err("ERR_PLAN_MISSING_FIELD", "tracking.title is required")
            tracking_ok = False
        if not isinstance(t_body_file, str) or not t_body_file.strip():
            err("ERR_PLAN_MISSING_FIELD", "tracking.body_file is required")
            tracking_ok = False
        if not isinstance(t_labels_raw, list):
            err("ERR_PLAN_MISSING_FIELD", "tracking.labels must be a list")
            t_labels_raw = []
        t_body = ""
        if tracking_ok:
            body_text, body_err = read_body_file(plan_path.parent / t_body_file)
            if body_err:
                err(body_err[0], f"tracking.body_file: {body_err[1]}")
                tracking_ok = False
            else:
                t_body = body_text
                errors.extend(reserved_content_errors("tracking", t_body))
        if tracking_ok:
            tracking = TrackingInfo(
                title=t_title, body_file=t_body_file, body=t_body,
                labels=[str(x) for x in t_labels_raw],
            )

    issues_raw = raw.get("issues")
    if not isinstance(issues_raw, list) or not issues_raw:
        err("ERR_PLAN_MISSING_FIELD", "top-level 'issues' must be a non-empty list")
        issues_raw = []

    raw_keys = [e["key"] for e in issues_raw if isinstance(e, dict) and isinstance(e.get("key"), str)]
    key_counts = Counter(raw_keys)

    # by_key holds everything needed for the cross-issue checks below, built
    # only from entries whose key is well-formed and unique — an entry with a
    # broken key already has its own error and cannot be referenced anyway.
    by_key: dict[str, dict[str, Any]] = {}

    for idx, entry in enumerate(issues_raw):
        loc = f"issues[{idx}]"
        if not isinstance(entry, dict):
            err("ERR_PLAN_MISSING_FIELD", f"{loc} must be an object")
            continue

        key = entry.get("key")
        key_ok = True
        if not isinstance(key, str) or not key:
            err("ERR_PLAN_MISSING_FIELD", f"{loc}.key is required")
            key_ok = False
        elif not KEY_RE.match(key):
            err("ERR_PLAN_INVALID_KEY", f"{loc}.key {key!r} must match [a-z0-9][a-z0-9-]*")
            key_ok = False
        elif key == "tracking":
            err("ERR_PLAN_INVALID_KEY", f"{loc}.key 'tracking' is reserved for the tracking issue")
            key_ok = False
        elif key_counts[key] > 1:
            err("ERR_PLAN_DUPLICATE_KEY", f"key {key!r} is used by more than one issue")
            key_ok = False

        title = entry.get("title")
        if not isinstance(title, str) or not title.strip():
            err("ERR_PLAN_MISSING_FIELD", f"{loc}.title is required")
            title = title if isinstance(title, str) else ""

        body_file = entry.get("body_file")
        body_text = ""
        body_ok = False
        if not isinstance(body_file, str) or not body_file.strip():
            err("ERR_PLAN_MISSING_FIELD", f"{loc}.body_file is required")
        else:
            text, body_err = read_body_file(plan_path.parent / body_file)
            if body_err:
                err(body_err[0], f"{loc}.body_file: {body_err[1]}")
            else:
                body_text = text
                body_ok = True
                errors.extend(reserved_content_errors(
                    f"issue {key!r}" if key_ok else loc, body_text))

        priority = entry.get("priority")
        if not isinstance(priority, str) or priority not in PRIORITY_ORDER:
            err("ERR_PLAN_INVALID_PRIORITY",
                f"{loc}.priority must be one of {PRIORITY_ORDER}, got {priority!r}")
            priority = None

        area = entry.get("area")
        if not isinstance(area, str) or not area.strip():
            err("ERR_PLAN_MISSING_FIELD", f"{loc}.area is required")
            area = area if isinstance(area, str) else ""

        raw_labels = entry.get("labels", [])
        if not isinstance(raw_labels, list):
            err("ERR_PLAN_MISSING_FIELD", f"{loc}.labels must be a list")
            raw_labels = []

        raw_depends = entry.get("depends_on", [])
        if not isinstance(raw_depends, list):
            err("ERR_PLAN_MISSING_FIELD", f"{loc}.depends_on must be a list")
            raw_depends = []

        raw_touches = entry.get("touches", [])
        if not isinstance(raw_touches, list):
            err("ERR_PLAN_MISSING_FIELD", f"{loc}.touches must be a list")
            raw_touches = []

        design = entry.get("design", "settled")
        if design not in ("settled", "open"):
            err("ERR_PLAN_INVALID_DESIGN",
                f"{loc}.design must be 'settled' or 'open', got {design!r}")
            design = None

        if key_ok and key in raw_depends:
            err("ERR_PLAN_SELF_DEPENDENCY", f"issue {key!r} cannot depend on itself")

        if key_ok and body_ok and priority is not None and design is not None:
            by_key[key] = {
                "title": title,
                "body_file": body_file,
                "body": body_text,
                "priority": priority,
                "labels": [str(x) for x in raw_labels],
                "depends_on": [str(x) for x in raw_depends if x != key],
                "area": area,
                "touches": [str(x) for x in raw_touches],
                "design": design,
            }

    # Cross-issue checks, run over whatever parsed cleanly so far. A dep that
    # names a raw key which failed its OWN validation (bad format, duplicate,
    # unreadable body, ...) is not re-flagged here — that key already carries
    # its own error, and reporting it again from every issue that depends on
    # it would just be noise.
    all_raw_keys = set(raw_keys)
    for key, info in by_key.items():
        for dep in info["depends_on"]:
            if dep not in by_key and dep not in all_raw_keys:
                err("ERR_PLAN_UNKNOWN_DEPENDENCY",
                    f"issue {key!r} depends on unknown key {dep!r}")

    graph = {k: [d for d in info["depends_on"] if d in by_key] for k, info in by_key.items()}
    cycle = find_cycle(graph)
    if cycle:
        err("ERR_PLAN_CYCLE", "dependency cycle: " + " -> ".join(cycle))

    for key, deps in graph.items():
        for dep in deps:
            dep_priority = by_key[dep]["priority"]
            own_priority = by_key[key]["priority"]
            if PRIORITY_ORDER.index(dep_priority) > PRIORITY_ORDER.index(own_priority):
                err(
                    "ERR_PLAN_PRIORITY_INVERSION",
                    f"issue {key!r} ({own_priority}) depends on {dep!r} ({dep_priority}) "
                    "— the blocker has a lower priority than the issue waiting on it",
                )

    reverse: dict[str, list[str]] = {k: [] for k in by_key}
    for key, deps in graph.items():
        for dep in deps:
            reverse[dep].append(key)
    for key, info in by_key.items():
        errors.extend(stray_dependency_errors(key, info["body"], info["depends_on"], reverse[key]))

    known_placeholder_keys = set(by_key) | {"tracking"}
    for key, info in by_key.items():
        for m2 in PLACEHOLDER_RE.finditer(info["body"]):
            if m2.group(1) not in known_placeholder_keys:
                err("ERR_PLAN_UNKNOWN_PLACEHOLDER",
                    f"issue {key!r} body references unknown placeholder "
                    f"'{{{{#{m2.group(1)}}}}}'")
    if tracking is not None:
        for m2 in PLACEHOLDER_RE.finditer(tracking.body):
            if m2.group(1) not in known_placeholder_keys:
                err("ERR_PLAN_UNKNOWN_PLACEHOLDER",
                    f"tracking body references unknown placeholder "
                    f"'{{{{#{m2.group(1)}}}}}'")

    if errors:
        return None, errors

    assert repo is not None and tracking is not None  # guaranteed: no errors were collected
    issues = [
        PlanIssue(
            key=k, title=info["title"], body_file=info["body_file"], body=info["body"],
            priority=info["priority"], labels=info["labels"], depends_on=info["depends_on"],
            area=info["area"], touches=info["touches"], design=info["design"],
        )
        for k, info in by_key.items()
    ]
    return Plan(repo=repo, labels=labels, tracking=tracking, issues=issues, path=plan_path), []


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """A cyclic key sequence like ['a', 'b', 'c', 'a'], or None if acyclic."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in graph}
    parent: dict[str, str] = {}
    result: list[str] | None = None

    def visit(u: str) -> bool:
        nonlocal result
        color[u] = GRAY
        for v in graph.get(u, []):
            if color.get(v) == GRAY:
                path = [u]
                cur = u
                while cur != v:
                    cur = parent[cur]
                    path.append(cur)
                path.reverse()
                path.append(v)
                result = path
                return True
            if color.get(v) == WHITE:
                parent[v] = u
                if visit(v):
                    return True
        color[u] = BLACK
        return False

    for k in graph:
        if color[k] == WHITE and visit(k):
            return result
    return None


def topo_order(issues: list[PlanIssue]) -> list[PlanIssue]:
    """Topological order, ties broken by priority then original plan order.

    Only called after validate_plan has confirmed the graph is acyclic and
    every dependency resolves, so this never raises.
    """
    by_key = {i.key: i for i in issues}
    plan_index = {i.key: idx for idx, i in enumerate(issues)}
    dependents: dict[str, list[str]] = {k: [] for k in by_key}
    indegree: dict[str, int] = {}
    for i in issues:
        deps = [d for d in i.depends_on if d in by_key]
        indegree[i.key] = len(deps)
        for d in deps:
            dependents[d].append(i.key)

    def sort_key(k: str) -> tuple[int, int]:
        return (PRIORITY_ORDER.index(by_key[k].priority), plan_index[k])

    ready = sorted([k for k, deg in indegree.items() if deg == 0], key=sort_key)
    result: list[PlanIssue] = []
    while ready:
        k = ready.pop(0)
        result.append(by_key[k])
        newly_ready = []
        for dep_k in dependents[k]:
            indegree[dep_k] -= 1
            if indegree[dep_k] == 0:
                newly_ready.append(dep_k)
        if newly_ready:
            ready = sorted(ready + newly_ready, key=sort_key)
    return result


# --- body assembly -----------------------------------------------------


def resolve_placeholders(text: str, numbers: dict[str, int]) -> str:
    return PLACEHOLDER_RE.sub(lambda m: f"#{numbers[m.group(1)]}", text)


def dependencies_section(depends_on_numbers: list[int], blocks_numbers: list[int]) -> str:
    lines = [f"- Depends on #{n}" for n in depends_on_numbers]
    lines += [f"- Blocks #{n}" for n in blocks_numbers]
    body = "\n".join(lines) if lines else "None"
    return f"## Dependencies\n\n{body}"


def contract_line(
    tier: str, area: str, blocked_by: list[int], blocks: list[int],
    touches: list[str], design: str,
) -> str:
    bb = ",".join(f"#{n}" for n in blocked_by) if blocked_by else "none"
    bl = ",".join(f"#{n}" for n in blocks) if blocks else "none"
    tc = ",".join(touches) if touches else "*"
    return f"<!-- ship: tier={tier} area={area} blocked-by={bb} blocks={bl} touches={tc} design={design} -->"


def sub_issues_section(rows: list[tuple[int, str]]) -> str:
    lines = [f"- [ ] #{n} {title}" for n, title in rows]
    return "## Sub-issues\n\n" + "\n".join(lines)


def pass1_body(raw_body: str, key: str) -> str:
    return f"{raw_body.rstrip()}\n\n{marker(key)}\n"


def pass2_issue_body(issue: PlanIssue, numbers: dict[str, int], blocks_numbers: list[int]) -> str:
    resolved = resolve_placeholders(issue.body, numbers).rstrip()
    dep_nums = [numbers[d] for d in issue.depends_on]
    section = dependencies_section(dep_nums, blocks_numbers)
    contract = contract_line(issue.priority, issue.area, dep_nums, blocks_numbers,
                              issue.touches, issue.design)
    return f"{resolved}\n\n{section}\n\n{contract}\n\n{marker(issue.key)}\n"


def pass2_tracking_body(tracking: TrackingInfo, numbers: dict[str, int],
                         rows: list[tuple[int, str]]) -> str:
    resolved = resolve_placeholders(tracking.body, numbers).rstrip()
    # The umbrella is not work. Declaring every sub-issue as its blocker keeps a
    # downstream shipping run from selecting it while anything is still open.
    contract = contract_line("P3", "tracking", [n for n, _ in rows], [], [], "settled")
    return f"{resolved}\n\n{sub_issues_section(rows)}\n\n{contract}\n\n{marker('tracking')}\n"


# --- gh plumbing -----------------------------------------------------------


def run_gh(args: list[str], input_data: str | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["gh", *args], input=input_data, capture_output=True, text=True, timeout=120,
        )
    except FileNotFoundError:
        raise GhError("ERR_GH_NOT_FOUND", "gh CLI not found on PATH")
    except subprocess.TimeoutExpired:
        raise GhError("ERR_GH_TIMEOUT", f"gh {' '.join(args)} timed out")


def parse_concatenated_json(text: str) -> list[Any]:
    """Flatten one or more whitespace-separated JSON documents into one list.

    `gh api ... --paginate` prints each page's response one after another —
    on older gh this is not itself valid JSON (no enclosing array), so
    json.loads on the raw text fails. Reading with repeated raw_decode calls
    handles one page or many the same way.
    """
    decoder = json.JSONDecoder()
    text = text.strip()
    idx = 0
    items: list[Any] = []
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        obj, end = decoder.raw_decode(text, idx)
        items.extend(obj) if isinstance(obj, list) else items.append(obj)
        idx = end
    return items


def upsert_label(repo: str, name: str, color: str, description: str) -> None:
    proc = run_gh([
        "label", "create", name, "--repo", repo,
        "--color", color, "--description", description, "--force",
    ])
    if proc.returncode != 0:
        raise GhError("ERR_GH_LABEL_FAILED",
                       f"label create --force {name!r} failed: {(proc.stderr or '').strip()}")


def fetch_all_issues(repo: str) -> list[dict[str, Any]]:
    proc = run_gh([
        "api", f"repos/{repo}/issues", "--method", "GET",
        "-f", "state=all", "-f", "per_page=100", "--paginate",
    ])
    if proc.returncode != 0:
        raise GhError("ERR_GH_LIST_FAILED", f"listing issues failed: {(proc.stderr or '').strip()}")
    items = parse_concatenated_json(proc.stdout or "[]")
    return [it for it in items if isinstance(it, dict) and "pull_request" not in it]


def scan_existing_by_key(repo: str) -> dict[str, CreatedEntry]:
    found: dict[str, CreatedEntry] = {}
    for it in fetch_all_issues(repo):
        m = SCAN_MARKER_RE.search(it.get("body") or "")
        if not m:
            continue
        found[m.group(1)] = CreatedEntry(
            number=it["number"], id=it["id"], url=it.get("html_url", ""),
        )
    return found


def create_issue(repo: str, title: str, body: str, labels: list[str]) -> CreatedEntry:
    payload = json.dumps({"title": title, "body": body, "labels": labels})
    proc = run_gh(["api", f"repos/{repo}/issues", "--method", "POST", "--input", "-"],
                   input_data=payload)
    if proc.returncode != 0:
        raise GhError("ERR_GH_CREATE_FAILED",
                       f"creating issue {title!r} failed: {(proc.stderr or '').strip()}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise GhError("ERR_GH_CREATE_FAILED",
                       f"creating issue {title!r}: unexpected response: {proc.stdout!r}")
    return CreatedEntry(number=data["number"], id=data["id"], url=data.get("html_url", ""))


def patch_issue_body(repo: str, number: int, body: str) -> None:
    payload = json.dumps({"body": body})
    proc = run_gh(["api", f"repos/{repo}/issues/{number}", "--method", "PATCH", "--input", "-"],
                   input_data=payload)
    if proc.returncode != 0:
        raise GhError("ERR_GH_PATCH_FAILED",
                       f"updating issue #{number} failed: {(proc.stderr or '').strip()}")


def _is_already_exists(stderr: str) -> bool:
    # These two link endpoints answer a duplicate request with 422; the exact
    # wording varies ("already a sub-issue", "already blocked by ..."), so the
    # status code alone is treated as the idempotent-success signal.
    return "422" in stderr


def link_sub_issue(repo: str, tracking_number: int, issue_id: int) -> tuple[bool, str]:
    proc = run_gh([
        "api", f"repos/{repo}/issues/{tracking_number}/sub_issues", "--method", "POST",
        "-F", f"sub_issue_id={issue_id}",
    ])
    if proc.returncode == 0:
        return True, ""
    stderr = (proc.stderr or "").strip()
    if _is_already_exists(stderr):
        return True, ""
    return False, f"sub-issue link tracking#{tracking_number} <- id {issue_id} failed: {stderr}"


def link_blocked_by(repo: str, number: int, blocker_issue_id: int) -> tuple[bool, str]:
    proc = run_gh([
        "api", f"repos/{repo}/issues/{number}/dependencies/blocked_by", "--method", "POST",
        "-F", f"issue_id={blocker_issue_id}",
    ])
    if proc.returncode == 0:
        return True, ""
    stderr = (proc.stderr or "").strip()
    if _is_already_exists(stderr):
        return True, ""
    return False, f"blocked-by link #{number} <- id {blocker_issue_id} failed: {stderr}"


def load_created(path: Path) -> dict[str, CreatedEntry]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    result: dict[str, CreatedEntry] = {}
    for k, v in raw.items():
        try:
            result[k] = CreatedEntry(number=v["number"], id=v["id"], url=v.get("url", ""))
        except (KeyError, TypeError):
            continue
    return result


def save_created(path: Path, created: dict[str, CreatedEntry]) -> None:
    payload = {k: {"number": v.number, "id": v.id, "url": v.url} for k, v in created.items()}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --- apply -----------------------------------------------------------------


def apply_plan(plan: Plan, order: list[PlanIssue], plan_path: Path) -> dict[str, Any]:
    if shutil.which("gh") is None:
        raise GhError("ERR_GH_NOT_FOUND", "gh CLI not found on PATH")

    repo = plan.repo
    created_path = plan_path.parent / "created.json"
    created = load_created(created_path)

    # 1. Labels: the plan's own, then priority/design labels actually used.
    for lbl in plan.labels:
        upsert_label(repo, lbl["name"], lbl["color"], lbl["description"])
    used_priorities = sorted({i.priority for i in plan.issues}, key=PRIORITY_ORDER.index)
    for p in used_priorities:
        name, color, desc = PRIORITY_LABELS[p]
        upsert_label(repo, name, color, desc)
    if any(i.design == "open" for i in plan.issues):
        name, color, desc = DESIGN_LABEL
        upsert_label(repo, name, color, desc)

    # 2. Idempotency: reuse anything already marked, merge into created.json.
    scanned = scan_existing_by_key(repo)
    merged = False
    for key, entry in scanned.items():
        if key not in created:
            created[key] = entry
            merged = True
    if merged:
        save_created(created_path, created)

    statuses: dict[str, str] = {}

    def ensure_created(key: str, title: str, raw_body: str, labels: list[str]) -> None:
        if key in created:
            statuses[key] = "reused"
            return
        entry = create_issue(repo, title, pass1_body(raw_body, key), labels)
        created[key] = entry
        statuses[key] = "created"
        save_created(created_path, created)

    # 3. Pass 1 — tracking first, then every issue in creation order.
    ensure_created("tracking", plan.tracking.title, plan.tracking.body,
                   list(dict.fromkeys(plan.tracking.labels)))
    for issue in order:
        labels = list(dict.fromkeys([
            *issue.labels,
            PRIORITY_LABELS[issue.priority][0],
            *([DESIGN_LABEL[0]] if issue.design == "open" else []),
        ]))
        ensure_created(issue.key, issue.title, issue.body, labels)

    # 4. Pass 2 — resolve placeholders, append Dependencies/contract/marker.
    numbers = {k: v.number for k, v in created.items()}
    for issue in order:
        blocks_numbers = sorted(
            numbers[other.key] for other in plan.issues if issue.key in other.depends_on
        )
        final_body = pass2_issue_body(issue, numbers, blocks_numbers)
        patch_issue_body(repo, created[issue.key].number, final_body)

    rows = [(created[i.key].number, i.title) for i in order]
    tracking_body = pass2_tracking_body(plan.tracking, numbers, rows)
    patch_issue_body(repo, created["tracking"].number, tracking_body)

    # 5. Native links — warnings only, never fatal.
    link_warnings: list[str] = []
    tracking_number = created["tracking"].number
    for issue in order:
        ok, warning = link_sub_issue(repo, tracking_number, created[issue.key].id)
        if not ok:
            link_warnings.append(warning)
            print(f"warning: {warning}", file=sys.stderr)
    for issue in order:
        for dep_key in issue.depends_on:
            ok, warning = link_blocked_by(repo, created[issue.key].number, created[dep_key].id)
            if not ok:
                link_warnings.append(warning)
                print(f"warning: {warning}", file=sys.stderr)

    counts = {
        "created": sum(1 for s in statuses.values() if s == "created"),
        "reused": sum(1 for s in statuses.values() if s == "reused"),
        "link_warnings": len(link_warnings),
    }
    return {
        "repo": repo,
        "tracking": {
            "number": tracking_number, "url": created["tracking"].url,
            "status": statuses["tracking"],
        },
        "issues": [
            {"key": i.key, "number": created[i.key].number, "url": created[i.key].url,
             "status": statuses[i.key]}
            for i in order
        ],
        "counts": counts,
        "link_warnings": link_warnings,
    }


# --- output ----------------------------------------------------------------


def print_dry_run(plan: Plan, order: list[PlanIssue], as_json: bool) -> None:
    rows = [
        {"order": idx, "key": i.key, "priority": i.priority, "title": i.title,
         "depends_on": list(i.depends_on)}
        for idx, i in enumerate(order, start=1)
    ]
    if as_json:
        print(json.dumps({
            "repo": plan.repo, "dry_run": True,
            "tracking_title": plan.tracking.title, "order": rows,
        }, ensure_ascii=False, indent=2))
        return
    print(f"Tracking: {plan.tracking.title}\n")
    print(f"# Creation order for {plan.repo} ({len(order)} issue(s))\n")
    print("| order | key | priority | title | depends-on |")
    print("|---|---|---|---|---|")
    for r in rows:
        dep = ", ".join(r["depends_on"]) if r["depends_on"] else "-"
        title = r["title"].replace("|", "\\|")
        print(f"| {r['order']} | {r['key']} | {r['priority']} | {title} | {dep} |")
    print("\nDry run: no GitHub writes were made. Re-run with --apply to create issues.")


def print_apply_summary(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    tracking = result["tracking"]
    print(f"Tracking: {tracking['url']} (#{tracking['number']}, {tracking['status']})\n")
    print("| key | issue | status |")
    print("|---|---|---|")
    for row in result["issues"]:
        print(f"| {row['key']} | #{row['number']} | {row['status']} |")
    c = result["counts"]
    print(f"\ncreated: {c['created']}, reused: {c['reused']}, link warnings: {c['link_warnings']}")
    if result["link_warnings"]:
        print("\nLink warnings:")
        for w in result["link_warnings"]:
            print(f"  - {w}")


# --- CLI ---------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="create_issues.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("plan_json", type=Path, help="path to plan.json")
    parser.add_argument("--apply", action="store_true",
                         help="create/update issues on GitHub (default: dry run, no writes)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                         help="machine-readable output")
    args = parser.parse_args(argv)

    raw, load_err = load_plan_json(args.plan_json)
    if load_err:
        print(load_err, file=sys.stderr)
        return 2

    local_repo = resolve_local_repo(Path.cwd())
    plan, errors = validate_plan(raw, args.plan_json, local_repo=local_repo)
    if errors:
        for e in errors:
            print(str(e), file=sys.stderr)
        print(f"\n{len(errors)} error(s) in {args.plan_json}", file=sys.stderr)
        return 2

    assert plan is not None
    order = topo_order(plan.issues)

    if not args.apply:
        print_dry_run(plan, order, args.as_json)
        return 0

    try:
        result = apply_plan(plan, order, args.plan_json)
    except GhError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print_apply_summary(result, args.as_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
