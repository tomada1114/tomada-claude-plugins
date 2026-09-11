#!/usr/bin/env python3
"""issue_digest.py — Priority- and dependency-annotated digest of open GitHub issues.

Fetches open issues (and open PRs, to detect work already in flight) via the
`gh` CLI and prints a token-lean digest. Raw `gh --json` output never has to
enter a context window.

Beyond the mechanical readiness flags (BLOCKED-BY / HAS-OPEN-PR /
NOT-READY-LABEL) it computes three things the ordering decision needs:

  * reverse dependency edges — how many *other* open issues this one unblocks,
    which is the single strongest "do this first" signal;
  * a heuristic priority score built from unblock count, priority labels,
    leverage keywords (CI, schema, interface, security, breakage…), milestone,
    and staleness;
  * a priority *tier* — the `priority: P0`…`P3` label if the issue already
    carries one (or a recognized equivalent), otherwise a suggested tier derived
    from the score, printed as `~P1`.

**The label is the persisted ranking.** A labeled backlog is ranked by reading
labels alone — no issue prose has to be re-analyzed on every run. Suggested
tiers exist to be written back by `apply_priority_labels.py`, after which they
become confirmed ones. The score survives as the within-tier tie-breaker and as
the input to those suggestions; it is a *ranking hint*, not a verdict, and is
computed from raw issue bodies even when `--body-chars 0` keeps that prose out
of the caller's context. Confirm suggested tiers against
references/priority-rubric.md before acting on them.

An issue can also state these facts outright instead of leaving them to be
inferred, in a `<!-- ship: ... -->` block (see parse_ship_contract): the tier,
what it waits on, what it blocks, and which paths it touches. A declared tier
is settled, not suggested; declared paths are what make the parallel-grouping
decision a set intersection rather than a guess.

Usage:
    issue_digest.py [--label L]... [--assignee A] [--milestone M]
                    [--issue N]... [--limit N] [--body-chars N]
                    [--rank-only] [--select N] [--with-rank]
                    [--detail N]... [--detail-top K] [--no-rank]
                    [--audit] [--cache-ttl S] [--refresh] [--json]

Output (default: markdown). `--json` emits the same data as a JSON object for
programmatic consumers.

`--select` composes: `--with-rank` appends the ranking table and
`--detail`/`--detail-top` append issue bodies, so a run's whole startup question
is one call. `--issue` narrows what is ranked; `--detail` does not.

The `gh` fetch can be cached under the repo's run-state directory, keyed on the
arguments that change what `gh` returns — but `--cache-ttl` defaults to 0, so it
is off unless a caller asks for it. `plan.py` asks for 300 seconds because a
startup's calls are seconds apart; anything reading the backlog after this run
has changed it should not. That is the safe default: a stale digest can re-select
an issue this run already merged, and nothing downstream would notice.

Exit codes:
    0 = digest printed (may contain zero issues)
    1 = gh invocation failed
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Dependency phrasings seen in real issue bodies, EN + JA.
DEP_PATTERNS = [
    (r"(?:depends?\s+on|blocked\s+by|after|requires?)\s*:?\s*#(\d+)", "depends_on"),
    (r"(?:blocks|blocking)\s*:?\s*#(\d+)", "blocks"),
    (r"#(\d+)\s*(?:に依存|の後|完了後|がマージされてから|の続き)", "depends_on"),
    (r"(?:前提|依存|ブロッカー|先行)\s*:?\s*#(\d+)", "depends_on"),
    (r"#(\d+)\s*(?:をブロック|の前提)", "blocks"),
]

# --- ship contract ---------------------------------------------------------
# A machine-readable block the issue author (or file_followup.py) leaves in the
# body, so the facts this skill would otherwise re-derive from prose on every
# run are simply read instead:
#
#   <!-- ship: tier=P1 area=test-infra blocked-by=#12 blocks=#98
#        touches=tests/,vitest.config.ts design=settled -->
#
# Every field is optional and unknown fields are ignored, so the block can grow
# without breaking older readers. Two of them carry their weight immediately:
#
#   * `tier` is a *confirmed* tier, not a suggestion — someone chose it when
#     filing — so it prints as `P1`, not `~P1`, and a backlog whose issues all
#     carry one needs no research pass even before the labels are written.
#   * `touches` is what turns the parallel-grouping decision from a guess about
#     which issues might collide into a set intersection.
SHIP_CONTRACT_RE = re.compile(r"<!--\s*ship\s*:(.*?)-->", re.DOTALL | re.IGNORECASE)
# Fields are `key=value`, whitespace-separated, values never contain spaces.
CONTRACT_FIELD_RE = re.compile(r"([A-Za-z][\w-]*)\s*=\s*(\S+)")
CONTRACT_KNOWN_FIELDS = ("tier", "area", "blocked-by", "blocks", "touches", "design")
# A contract is "complete enough to plan from" when it settles the three things
# the startup would otherwise have to derive: the tier, what it waits on, and
# what it touches. `blocked-by=none` and `touches=*` are how an author says
# "nothing" and "unknown/everything" explicitly rather than by omission.
CONTRACT_REQUIRED_FIELDS = ("tier", "blocked-by", "touches")


def parse_ship_contract(body: str) -> dict[str, Any] | None:
    """The `<!-- ship: ... -->` block's fields, or None if the body has none.

    The last block wins: an issue edited to correct its contract usually gains a
    second block rather than losing the first.
    """
    blocks = SHIP_CONTRACT_RE.findall(body or "")
    if not blocks:
        return None
    raw: dict[str, str] = {}
    for block in blocks:
        for key, value in CONTRACT_FIELD_RE.findall(block):
            raw[key.strip().lower()] = value.strip()

    def numbers(key: str) -> list[int]:
        value = raw.get(key, "")
        if value.lower() in ("", "none", "-"):
            return []
        return sorted({int(n) for n in re.findall(r"\d+", value)})

    tier = raw.get("tier", "").upper()
    design = raw.get("design", "").lower()
    touches_raw = raw.get("touches", "")
    return {
        "fields": sorted(raw),
        "unknown_fields": sorted(k for k in raw if k not in CONTRACT_KNOWN_FIELDS),
        "missing_fields": [k for k in CONTRACT_REQUIRED_FIELDS if k not in raw],
        "tier": tier if tier in TIER_ORDER else None,
        "area": raw.get("area"),
        "depends_on": numbers("blocked-by"),
        "blocks": numbers("blocks"),
        # `*` means "assume it collides with everything" — an honest unknown is
        # worth more here than an omission, which reads as "touches nothing".
        "touches": [t for t in touches_raw.split(",") if t] if touches_raw else [],
        "design": design if design in ("settled", "open") else None,
    }


CLOSING_RE = re.compile(
    r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s*#(\d+)", re.IGNORECASE
)
BARE_REF_RE = re.compile(r"(?<![\w/])#(\d+)")


def normalize_label(name: str) -> str:
    """`Priority: P0`, `priority/P0` and ` p0 ` all collapse to one lookup key."""
    return re.sub(r"\s*[:/]\s*", ":", name.strip().lower())


READY_NEGATIVE_LABELS = {
    "blocked",
    "on hold",
    "on-hold",
    "wontfix",
    "duplicate",
    "question",
    "discussion",
    "needs discussion",
    "needs-discussion",
    "wip",
    "draft",
}

# The design-not-settled label is a *soft* block, unlike READY_NEGATIVE_LABELS:
# it is excluded from automatic selection by default, but an explicit issue
# number or --include-design can still take it on (deciding the design is then
# part of the run — see SKILL.md step 2b). Kept separate from
# READY_NEGATIVE_LABELS so the two states never collapse into one meaning.
# All members are normalize_label() output, so "Blocked: Design", "blocked/design"
# and "needs-design" resolve to the same key on lookup.
DESIGN_LABEL = ("blocked: design", "5319e7",
                "Design/approach not settled - decide it before implementing")
DESIGN_BLOCK_LABELS = {
    normalize_label(n) for n in
    ("blocked: design", "needs design", "needs-design", "needs:design",
     "design-needed")
}

# Labels that assert "this issue is blocked on a dependency". Readiness never
# reads these — it is computed from the dependency edges themselves
# (depends_on_open) — so this set exists only to detect when the label has
# gone stale: the edges have all closed but the label is still sitting on the
# issue, misleading a human skimming the backlog. Kept small and literal
# (normalize_label() output) on purpose: bare "blocked" is deliberately
# excluded, since it is ambiguous with READY_NEGATIVE_LABELS's general block.
DEPENDENCY_BLOCK_LABELS = {
    normalize_label(n) for n in
    ("blocked: dependency", "blocked-by-dependency", "blocked: dependencies",
     "waiting on dependency")
}


def resolve_design_label(existing: list[str]) -> tuple[str, bool]:
    """Return (label name this repo uses for the design-not-settled state,
    whether it still needs to be created). Mirrors apply_priority_labels.py's
    tier-label resolution: prefer the canonical name, then any existing alias
    meaning the same thing (shortest wins), only fall back to creating the
    canonical one when the repo has neither.
    """
    canonical = DESIGN_LABEL[0]
    by_norm = {normalize_label(name): name for name in existing}
    if normalize_label(canonical) in by_norm:
        return by_norm[normalize_label(canonical)], False
    aliases = [name for norm, name in by_norm.items() if norm in DESIGN_BLOCK_LABELS]
    if aliases:
        return min(aliases, key=lambda n: (len(n), n)), False
    return canonical, True


# Explicit priority signals, by normalized label name (see normalize_label:
# `Priority: P0`, `priority/p0` and `p0 ` all arrive here as one key).
PRIORITY_LABEL_WEIGHTS = {
    "sev1": 8, "severity:1": 8, "security": 8, "incident": 8,
    "regression": 5, "important": 4, "broken": 4,
    "bug": 3, "defect": 3,
    "enhancement": 0, "feature": 0,
    "documentation": -1, "docs": -1, "chore": -1,
    "p4": -2,
}

# The four labels this skill writes. The tier IS the persisted ranking: it is
# read on every later run so issue prose never has to be re-analyzed. Colors and
# descriptions are what apply_priority_labels.py creates the labels with.
TIER_ORDER = ["P0", "P1", "P2", "P3"]
TIER_LABELS = {
    "P0": ("priority: P0", "b60205",
           "Ship now - unblocks other issues or damage is being taken"),
    "P1": ("priority: P1", "d93f0b",
           "Do next - leverage on the ground later issues stand on"),
    "P2": ("priority: P2", "fbca04",
           "Normal - self-contained, nothing waits on it"),
    "P3": ("priority: P3", "0e8a16",
           "Defer - nice-to-have"),
}

# Label vocabularies that already express a tier, recognized on read so a repo
# with its own convention is ranked from its existing labels instead of being
# relabeled. Only names that mean *priority* belong here — a topic label like
# `security` or `bug` stays in PRIORITY_LABEL_WEIGHTS as a score signal.
TIER_ALIASES = {
    "priority:p0": "P0", "p0": "P0", "priority:critical": "P0",
    "critical": "P0", "urgent": "P0", "incident": "P0", "blocker": "P0",
    "priority:p1": "P1", "p1": "P1", "priority:high": "P1",
    "high priority": "P1", "high-priority": "P1",
    "priority:p2": "P2", "p2": "P2", "priority:medium": "P2",
    "medium priority": "P2", "medium-priority": "P2",
    "priority:p3": "P3", "p3": "P3", "priority:low": "P3",
    "low priority": "P3", "low-priority": "P3",
    "nice to have": "P3", "nice-to-have": "P3", "someday": "P3",
}

# Leverage: work whose value spills over onto other issues. Matched against
# title + body. Contributions are summed then capped by LEVERAGE_CAP, so an
# issue that name-drops every keyword cannot outrank a genuine blocker.
LEVERAGE_RULES = [
    ("security", 5,
     r"(?i)\b(security|vulnerab\w*|cve-|injection|xss|csrf|auth bypass|secret leak|credential leak)\b"
     r"|脆弱性|セキュリティ|情報漏[洩え]"),
    ("breakage", 4,
     r"(?i)\b(crash\w*|data loss|corrupt\w*|outage|broken build|is broken|regression|blocker)\b"
     r"|クラッシュ|デグレ|データ破損|落ちる|壊れて|動かない|止まって"),
    ("infra", 4,
     r"(?i)\b(ci|cd|github actions?|workflow|pipeline|build system|toolchain|lint(?:er|ing)? setup|pre-commit)\b"
     r"|CI/CD|ワークフロー|ビルド基盤|パイプライン|開発基盤"),
    ("schema", 4,
     r"(?i)\b(schema|migration|data model|new column|new field|new table|db model)\b"
     r"|スキーマ|マイグレーション|データモデル|テーブル定義"),
    ("interface", 3,
     r"(?i)\b(interface|protocol|type definition|typing|api contract|abstract base|base class|public api)\b"
     r"|型定義|インタ[ーー]?フェ[ーー]?ス|共通化|抽象化"),
    ("foundation", 3,
     r"(?i)\b(shared|common|core|foundation|scaffold\w*|extract\w* (?:into|to) a? ?(?:module|helper|util))\b"
     r"|共通処理|基盤|土台|全体に影響"),
    ("test-harness", 3,
     r"(?i)\b(test harness|test infra\w*|flaky|test fixture|coverage setup|e2e setup)\b"
     r"|テスト基盤|テスト環境|フレーキ"),
    ("config", 2,
     r"(?i)\b(config\w*|settings|env(?:ironment)? var\w*|feature flag)\b"
     r"|設定値|環境変数|フィーチャーフラグ"),
]
LEVERAGE_CAP = 8

UNBLOCK_POINTS = 4
UNBLOCK_CAP = 12
REFERENCE_CAP = 3
STALE_DAYS = 180
FRESH_DAYS = 30

# Score thresholds for suggesting a tier on an unlabeled issue. They mirror the
# rubric's axes: unblocking others or active damage is P0 outright; the leverage
# keywords that improve shared ground are P1; the rest falls out of the score.
# 14 is roughly "unblocks nothing but carries two leverage hits and a priority
# label"; 8 is one strong leverage hit; 3 is any positive signal at all.
SUGGEST_P0_SCORE = 14
SUGGEST_P1_SCORE = 8
SUGGEST_P2_SCORE = 3
URGENT_LEVERAGE = {"security", "breakage"}
FOUNDATION_LEVERAGE = {"infra", "schema", "interface", "foundation", "test-harness"}


def run_gh(args: list[str]) -> Any:
    try:
        out = subprocess.run(
            ["gh", *args], capture_output=True, text=True, check=True, timeout=120
        ).stdout
    except FileNotFoundError:
        print("error: gh CLI not found", file=sys.stderr)
        raise SystemExit(1)
    except subprocess.TimeoutExpired:
        print(f"error: gh {' '.join(args)} timed out", file=sys.stderr)
        raise SystemExit(1)
    except subprocess.CalledProcessError as exc:
        print(f"error: gh {' '.join(args)} failed:\n{exc.stderr}", file=sys.stderr)
        raise SystemExit(1)
    return json.loads(out or "[]")


def repo_slug() -> str | None:
    """`owner/repo` from the origin remote, or None when it cannot be read.

    Derived locally from git rather than from `gh repo view`: this is only used
    to name a cache directory, and paying a network round-trip to decide where
    to cache would undo the point.
    """
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def runstate_dir() -> Path | None:
    """This repo's run-state directory — the same path SKILL.md calls `<runstate>`."""
    slug = repo_slug()
    if not slug:
        return None
    base = os.environ.get("AGENT_SKILL_STATE_DIR") or str(Path.home() / ".local/state/agent-skills")
    owner, name = slug.split("/", 1)
    return Path(base) / "shipping-issues" / f"{owner}__{name}"


def _cache_key(issue_args: list[str]) -> str:
    """What makes two fetches interchangeable.

    Only the arguments that change what `gh` returns belong here. `--issue`,
    `--body-chars` and every output flag filter or format data already fetched,
    so a run that asks for one issue's detail reuses the whole-backlog fetch a
    `--select` took seconds earlier — which is the entire point of the cache.
    """
    return hashlib.sha256("\x00".join(issue_args).encode()).hexdigest()[:16]


def fetch_issues_and_prs(
    issue_args: list[str], ttl: int, refresh: bool
) -> tuple[list[Any], list[Any], str]:
    """(issues, prs, cache_status) — from the run-state cache when it is warm.

    A run's startup asks the same question several times in a row (rank, then
    select, then read the picked issues' bodies), and each `gh` pair costs two
    round-trips over data that cannot have changed in between. The cache is
    short-lived on purpose: anything that *does* change the backlog — a merge,
    a label write, a filed follow-up — is this session's own action, and the
    steps that follow one pass --refresh.
    """
    state = runstate_dir()
    path = state / "digest-cache.json" if state else None
    key = _cache_key(issue_args)
    disabled = ttl <= 0 or os.environ.get("SHIPPING_ISSUES_NO_CACHE") == "1"

    if path and not refresh and not disabled:
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
            if blob.get("key") == key and time.time() - blob["fetched_at"] <= ttl:
                return blob["issues"], blob["prs"], "HIT"
        except (OSError, ValueError, KeyError, TypeError):
            pass  # a missing, unreadable or malformed cache is a miss, not an error

    issues = run_gh(issue_args)
    prs = run_gh([
        "pr", "list", "--state", "open", "--limit", "100",
        "--json", "number,title,body,headRefName,isDraft,url",
    ])
    status = "MISS"
    if path and not disabled:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(
                {"key": key, "fetched_at": time.time(), "issues": issues, "prs": prs},
                ensure_ascii=False,
            ), encoding="utf-8")
            status = "WRITTEN"
        except OSError:
            pass  # an unwritable state dir costs a re-fetch next time, nothing more
    return issues, prs, status


def squeeze(text: str | None, limit: int) -> str:
    """Collapse whitespace, drop HTML comments and images, then truncate.

    A limit of 0 omits the body entirely — used for the index-only pass that
    keeps issue prose out of the orchestrating context.
    """
    if not text or limit <= 0:
        return ""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"```.*?```", " [code block] ", text, flags=re.DOTALL)
    # Demote body headings so they cannot collide with the digest's own ## rows.
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "▸ ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + " …[truncated]"
    return text


def extract_deps(body: str, title: str, self_number: int) -> dict[str, list[int]]:
    haystack = f"{title}\n{body or ''}"
    deps: dict[str, set[int]] = {"depends_on": set(), "blocks": set(), "mentions": set()}
    for pattern, kind in DEP_PATTERNS:
        for m in re.finditer(pattern, haystack, re.IGNORECASE):
            n = int(m.group(1))
            if n != self_number:
                deps[kind].add(n)
    for m in BARE_REF_RE.finditer(haystack):
        n = int(m.group(1))
        if n != self_number and n not in deps["depends_on"] and n not in deps["blocks"]:
            deps["mentions"].add(n)
    return {k: sorted(v) for k, v in deps.items()}


def days_since(iso_date: str) -> int | None:
    try:
        d = _dt.date.fromisoformat(iso_date[:10])
    except (ValueError, TypeError):
        return None
    return (_dt.date.today() - d).days


def canonical_tier(labels: list[str]) -> str | None:
    """The issue's priority tier from its labels, or None if it carries none.

    Highest tier wins when an issue somehow carries two (a repo migrating from
    `critical` to `priority: P1` can briefly have both).
    """
    tiers = {TIER_ALIASES[n] for n in map(normalize_label, labels) if n in TIER_ALIASES}
    return min(tiers, key=TIER_ORDER.index) if tiers else None


def suggest_tier(rec: dict[str, Any], hits: set[str], score: int) -> tuple[str, str]:
    """Tier to write on an issue that has none, plus the one-line reason.

    Deliberately mechanical: this runs over the whole backlog for free, and the
    rubric's research pass only has to correct the handful it gets wrong.
    """
    if rec["unblocks_open"]:
        return "P0", "unblocks " + ",".join(f"#{n}" for n in rec["unblocks_open"])
    urgent = sorted(hits & URGENT_LEVERAGE)
    if urgent:
        return "P0", "+".join(urgent)
    if score >= SUGGEST_P0_SCORE:
        return "P0", f"score {score}"
    foundation = sorted(hits & FOUNDATION_LEVERAGE)
    if foundation:
        return "P1", "+".join(foundation)
    if score >= SUGGEST_P1_SCORE:
        return "P1", f"score {score}"
    if score >= SUGGEST_P2_SCORE:
        return "P2", f"score {score}"
    return "P3", f"score {score}"


def score_issue(rec: dict[str, Any], raw_body: str) -> tuple[int, list[str], set[str]]:
    """Heuristic priority score, a readable breakdown, and the leverage hits.

    Weighted toward *impact on other work*: unblocking other open issues and
    touching shared foundations outrank a self-contained nice-to-have. Labels
    that are themselves a tier are skipped — the tier is applied as a sort key,
    so counting it here too would drown the signals that break within-tier ties.
    """
    score = 0
    parts: list[str] = []

    n_unblocks = len(rec["unblocks_open"])
    if n_unblocks:
        pts = min(UNBLOCK_POINTS * n_unblocks, UNBLOCK_CAP)
        score += pts
        parts.append(f"unblocks×{n_unblocks}(+{pts})")

    n_ref = len(rec["referenced_by_open"])
    if n_ref:
        pts = min(n_ref, REFERENCE_CAP)
        score += pts
        parts.append(f"referenced×{n_ref}(+{pts})")

    for lbl in rec["labels"]:
        key = normalize_label(lbl)
        if key in TIER_ALIASES:
            continue
        w = PRIORITY_LABEL_WEIGHTS.get(key)
        if w:
            score += w
            parts.append(f"label:{lbl}({w:+d})")

    haystack = f"{rec['title']}\n{raw_body or ''}"
    leverage = 0
    hits: list[str] = []
    for name, pts, pattern in LEVERAGE_RULES:
        if re.search(pattern, haystack):
            leverage += pts
            hits.append(name)
    if leverage:
        capped = min(leverage, LEVERAGE_CAP)
        score += capped
        parts.append(f"{'+'.join(hits)}(+{capped})")

    if rec["milestone"]:
        score += 2
        parts.append("milestone(+2)")

    age = days_since(rec["updated_at"])
    if age is not None:
        if age >= STALE_DAYS:
            score -= 1
            parts.append(f"stale {age}d(-1)")
        elif age <= FRESH_DAYS:
            score += 1
            parts.append("fresh(+1)")

    return score, parts, set(hits)


def tier_cell(rec: dict[str, Any]) -> str:
    """`P1` for a tier a human settled, `~P1` for one this script is guessing.

    "Settled" is either the written label or the filing contract's `tier=` — both
    were chosen by a person, so neither needs a research pass to be trusted.

    `P2(~P0)` means the written label is *lower* than the signals now justify —
    usually a label written before the issue started blocking something. The
    label still ranks; the marker is the prompt to re-label it.
    """
    tier = rec["priority_tier"] or rec.get("contract_tier")
    sugg = rec["suggested_tier"]
    if not tier:
        return f"~{sugg}"
    if TIER_ORDER.index(sugg) < TIER_ORDER.index(tier):
        return f"{tier}(~{sugg})"
    return tier


def readiness(rec: dict[str, Any], allow_design: bool = False) -> str:
    if rec["depends_on_open"]:
        return "BLOCKED-BY:" + ",".join(f"#{n}" for n in rec["depends_on_open"])
    if rec["not_ready_labels"]:
        return "LABEL:" + ",".join(rec["not_ready_labels"])
    if rec["design_labels"] and not allow_design:
        return "DESIGN:" + ",".join(rec["design_labels"])
    if rec["open_pr"]:
        return f"HAS-PR:#{rec['open_pr']['number']}"
    return "READY"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--label", action="append", default=[])
    p.add_argument("--assignee")
    p.add_argument("--milestone")
    p.add_argument("--issue", action="append", type=int, default=[],
                   help="restrict the digest to these issue numbers")
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--body-chars", type=int, default=1200,
                   help="truncate issue bodies to this many chars; 0 omits them")
    p.add_argument("--rank-only", action="store_true",
                   help="print only the priority ranking table")
    p.add_argument("--select", nargs="?", type=int, const=1, default=None,
                   metavar="N",
                   help="print only the top N READY issues (default 1) plus label "
                        "coverage — the cheapest way to get the pick")
    p.add_argument("--no-rank", action="store_true",
                   help="omit the priority ranking table")
    p.add_argument("--include-design", action="store_true",
                   help="treat design-not-settled issues (blocked: design and "
                        "equivalents) as selectable — use only when deciding "
                        "the design is itself part of this run")
    p.add_argument("--with-rank", action="store_true",
                   help="print the ranking table alongside --select instead of "
                        "instead of it (one call where two were needed)")
    p.add_argument("--detail", action="append", type=int, default=[], metavar="N",
                   help="print full detail for these issues WITHOUT restricting "
                        "the ranking to them (unlike --issue)")
    p.add_argument("--detail-top", type=int, default=0, metavar="K",
                   help="print full detail for the top K READY issues — replaces "
                        "hand-listing the numbers a --select just printed")
    p.add_argument("--audit", action="store_true",
                   help="report which issues carry a usable ship: contract and "
                        "what the rest are missing, then exit")
    p.add_argument("--cache-ttl", type=int, default=0, metavar="SECONDS",
                   help="reuse a run-state cache of the gh fetch this many "
                        "seconds. OFF by default: a cache that is on unless "
                        "someone remembers --refresh can serve a backlog from "
                        "before this run's own merge. plan.py opts in for the "
                        "startup, where the calls are seconds apart. Env "
                        "SHIPPING_ISSUES_NO_CACHE=1 forces it off.")
    p.add_argument("--refresh", action="store_true",
                   help="ignore the cache for this call and re-fetch — required "
                        "after anything this run did changes the backlog")
    p.add_argument("--json", action="store_true", dest="as_json")
    args = p.parse_args()

    if not shutil.which("gh"):
        print("error: gh CLI not found", file=sys.stderr)
        return 1

    issue_args = [
        "issue", "list", "--state", "open", "--limit", str(args.limit),
        "--json", "number,title,labels,assignees,milestone,body,createdAt,updatedAt,url",
    ]
    for label in args.label:
        issue_args += ["--label", label]
    if args.assignee:
        issue_args += ["--assignee", args.assignee]
    if args.milestone:
        issue_args += ["--milestone", args.milestone]

    issues, prs, cache_status = fetch_issues_and_prs(
        issue_args, args.cache_ttl, args.refresh
    )

    # Map issue number -> open PR that claims to close it.
    claimed: dict[int, dict[str, Any]] = {}
    for pr in prs:
        text = f"{pr.get('title', '')}\n{pr.get('body') or ''}\n{pr.get('headRefName', '')}"
        refs = {int(n) for n in CLOSING_RE.findall(text)}
        # Branch-name conventions that unambiguously encode an issue number:
        # "123-slug", "feat/123-slug", "issue-123". A bare digit anywhere in the
        # branch is not enough — "bump-foo-2-3-4" must not claim issue #2.
        branch = pr.get("headRefName", "")
        refs |= {int(n) for n in re.findall(r"(?:^|/)(\d{1,6})-", branch)}
        refs |= {int(n) for n in re.findall(r"(?i)issues?[-_/](\d{1,6})", branch)}
        for n in refs:
            claimed.setdefault(n, pr)

    # Dependency edges are read from every open issue, not just the filtered
    # subset: an issue excluded by --issue/--label can still be what makes the
    # selected one high-leverage.
    all_deps: dict[int, dict[str, list[int]]] = {}
    contracts: dict[int, dict[str, Any] | None] = {}
    for it in issues:
        num = it["number"]
        body = it.get("body") or ""
        deps = extract_deps(body, it.get("title", ""), num)
        contract = parse_ship_contract(body)
        contracts[num] = contract
        if contract:
            # An explicit contract edge is a stated fact; the regex scrape is an
            # inference from prose. Union rather than override — an author who
            # writes both a `blocked-by=` field and "depends on #12" in the body
            # means the same thing, and dropping either would lose an edge the
            # other caught.
            for kind in ("depends_on", "blocks"):
                merged = set(deps[kind]) | set(contract[kind])
                deps[kind] = sorted(n for n in merged if n != num)
            # Anything now a declared edge stops counting as a bare mention.
            declared = set(deps["depends_on"]) | set(deps["blocks"])
            deps["mentions"] = [n for n in deps["mentions"] if n not in declared]
        all_deps[num] = deps
    open_numbers = set(all_deps)

    # Reverse edges: who is waiting on whom.
    unblocks: dict[int, set[int]] = {n: set() for n in open_numbers}
    referenced_by: dict[int, set[int]] = {n: set() for n in open_numbers}
    for num, deps in all_deps.items():
        # "#M depends on me" — the edge is declared by the waiting issue.
        for target in deps["depends_on"]:
            if target in unblocks:
                unblocks[target].add(num)
        # "I block #M" — the edge is declared by this issue itself.
        for target in deps["blocks"]:
            if target in open_numbers:
                unblocks[num].add(target)
        for target in deps["mentions"]:
            if target in referenced_by:
                referenced_by[target].add(num)

    wanted = set(args.issue)
    records = []
    for it in issues:
        num = it["number"]
        if wanted and num not in wanted:
            continue
        labels = [lbl["name"] for lbl in it.get("labels", [])]
        body = it.get("body") or ""
        deps = all_deps[num]
        blockers = [lbl for lbl in labels
                    if normalize_label(lbl) in READY_NEGATIVE_LABELS]
        design_labels = [lbl for lbl in labels
                          if normalize_label(lbl) in DESIGN_BLOCK_LABELS]
        depends_on_open = [n for n in deps["depends_on"] if n in open_numbers]
        # Stale only when there IS a recorded dependency and every one of them
        # has closed. An issue carrying the label with no recorded dependency
        # is left alone — the edge may be expressed somewhere the regex/contract
        # scrape misses, and this script has no way to tell "no edge" from
        # "edge it couldn't see".
        stale_dependency_labels = (
            [lbl for lbl in labels if normalize_label(lbl) in DEPENDENCY_BLOCK_LABELS]
            if deps["depends_on"] and not depends_on_open else []
        )
        pr = claimed.get(num)
        rec = {
            "number": num,
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "labels": labels,
            "assignees": [a["login"] for a in it.get("assignees", [])],
            "milestone": (it.get("milestone") or {}).get("title"),
            "created_at": it.get("createdAt", "")[:10],
            "updated_at": it.get("updatedAt", "")[:10],
            "depends_on": deps["depends_on"],
            "blocks": deps["blocks"],
            "mentions": deps["mentions"],
            "depends_on_open": depends_on_open,
            "unblocks_open": sorted(unblocks.get(num, set())),
            "referenced_by_open": sorted(referenced_by.get(num, set())),
            "not_ready_labels": blockers,
            "design_labels": design_labels,
            "stale_dependency_labels": stale_dependency_labels,
            "open_pr": {"number": pr["number"], "url": pr["url"],
                        "draft": pr["isDraft"]} if pr else None,
            "body": squeeze(body, args.body_chars),
        }
        contract = contracts.get(num)
        rec["contract"] = contract
        rec["contract_tier"] = contract["tier"] if contract else None
        rec["area"] = contract["area"] if contract else None
        rec["touches"] = contract["touches"] if contract else []
        # `design=open` in the contract is the label's equal — an author who
        # writes it has said the approach is not settled, and the run should
        # hold the issue for step 8b whether or not the label was ever applied.
        # `design=settled` does NOT clear a label: the label is what this skill
        # writes and clears, and a stale contract must not override it.
        if contract and contract["design"] == "open" and not design_labels:
            design_labels = rec["design_labels"] = ["ship:design=open"]
        rec["priority_score"], rec["score_reasons"], hits = score_issue(rec, body)
        rec["priority_tier"] = canonical_tier(labels)
        rec["suggested_tier"], rec["suggested_reason"] = suggest_tier(
            rec, hits, rec["priority_score"]
        )
        # Two kinds of tier a human settled — the written label and the filing
        # contract — and one this script guessed. Only the first two rank
        # without a research pass.
        rec["confirmed_tier"] = rec["priority_tier"] or rec["contract_tier"]
        # What the ordering actually uses: a settled tier when there is one, the
        # suggestion otherwise, so a half-labeled backlog still ranks sanely.
        rec["effective_tier"] = rec["confirmed_tier"] or rec["suggested_tier"]
        # An explicit --issue N is itself the override: naming an issue means
        # taking it on deliberately, same as --include-design.
        rec["readiness"] = readiness(rec, allow_design=args.include_design or bool(wanted))
        records.append(rec)

    ranked = sorted(
        records,
        key=lambda r: (
            r["readiness"] != "READY",
            TIER_ORDER.index(r["effective_tier"]),
            r["confirmed_tier"] is None,  # a settled tier outranks a guess
            -r["priority_score"],
            r["number"],
        ),
    )

    labeled = [r for r in records if r["priority_tier"]]
    unlabeled = [r for r in records if not r["priority_tier"]]
    contract_ranked = [r for r in records if not r["priority_tier"] and r["contract_tier"]]
    unranked = [r for r in records if not r["confirmed_tier"]]
    with_contract = [r for r in records if r["contract"]]
    full_contract = [r for r in with_contract if not r["contract"]["missing_fields"]]
    needs_design = [r for r in records if r["design_labels"]]
    stale_dependency = [r for r in records if r["stale_dependency_labels"]]
    payload = {
        "open_issue_count": len(records),
        "open_pr_count": len(prs),
        "cache": cache_status,
        "label_coverage": {
            "labeled": len(labeled),
            "contract_ranked": len(contract_ranked),
            "total": len(records),
            # COMPLETE means "every issue has a tier a human settled", which is
            # the condition that makes the research pass unnecessary — the label
            # is still what gets written back, so `unlabeled` stays reported.
            "complete": not unranked,
            "unlabeled": [r["number"] for r in unlabeled],
            "unranked": [r["number"] for r in unranked],
        },
        "contract_coverage": {
            "full": len(full_contract),
            "partial": len(with_contract) - len(full_contract),
            "total": len(records),
            "missing": [r["number"] for r in records if not r["contract"]],
            "incomplete": {
                str(r["number"]): r["contract"]["missing_fields"]
                for r in with_contract if r["contract"]["missing_fields"]
            },
        },
        "needs_design": [r["number"] for r in needs_design],
        "stale_dependency_labels": [r["number"] for r in stale_dependency],
        "ranking": [
            {"number": r["number"], "title": r["title"],
             "score": r["priority_score"],
             "tier": r["priority_tier"], "contract_tier": r["contract_tier"],
             "confirmed_tier": r["confirmed_tier"],
             "suggested_tier": r["suggested_tier"],
             "effective_tier": r["effective_tier"],
             "readiness": r["readiness"], "reasons": r["score_reasons"],
             "touches": r["touches"], "area": r["area"],
             "depends_on_open": r["depends_on_open"],
             "unblocks_open": r["unblocks_open"]}
            for r in ranked
        ],
        "issues": sorted(records, key=lambda r: r["number"]),
    }

    if args.as_json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    cov = payload["label_coverage"]
    ccov = payload["contract_coverage"]
    # `contract: N` only earns a slot on the line when some issue actually has
    # one — a repo that has not adopted the block should not read a running
    # complaint about it on every call.
    contract_part = (
        f" · contract: {cov['contract_ranked']}/{cov['total']}"
        if cov["contract_ranked"] else ""
    )
    if not records:
        coverage_line = "labels: 0/0 — no open issue matches the filter"
    elif cov["complete"]:
        tail = (
            "rank by label; no research pass needed" if not cov["unlabeled"]
            else "every tier is settled; "
                 f"{len(cov['unlabeled'])} still need the label written "
                 "(apply_priority_labels.py --backfill)"
        )
        coverage_line = (
            f"labels: {cov['labeled']}/{cov['total']}{contract_part} COMPLETE — {tail}"
        )
    else:
        shown = ",".join(f"#{n}" for n in cov["unranked"][:15])
        more = "…" if len(cov["unranked"]) > 15 else ""
        coverage_line = (
            f"labels: {cov['labeled']}/{cov['total']}{contract_part} — no tier: "
            f"{shown}{more} "
            "(~Pn = suggested; write them with apply_priority_labels.py --backfill)"
        )

    if args.audit:
        print(f"contract: {ccov['full']}/{ccov['total']} complete · "
              f"{ccov['partial']} partial · {len(ccov['missing'])} missing")
        if ccov["missing"]:
            print("missing: " + ",".join(f"#{n}" for n in ccov["missing"]))
        for num, fields in sorted(ccov["incomplete"].items(), key=lambda kv: int(kv[0])):
            print(f"partial: #{num} — no {','.join(fields)}")
        unknown = {r["number"]: r["contract"]["unknown_fields"]
                   for r in records if r["contract"] and r["contract"]["unknown_fields"]}
        for num, fields in sorted(unknown.items()):
            print(f"unknown-fields: #{num} — {','.join(fields)}")
        print(coverage_line)
        return 0


    def print_rank_table() -> None:
        print("## Priority ranking (label tier first, score breaks ties)\n")
        print("| issue | priority | score | readiness | signals |")
        print("|---|---|---|---|---|")
        for r in ranked:
            title = r["title"].replace("|", "\\|")
            if len(title) > 60:
                title = title[:59] + "…"
            reasons = " · ".join(r["score_reasons"]) or "—"
            print(f"| #{r['number']} {title} | {tier_cell(r)} | {r['priority_score']} | "
                  f"{r['readiness']} | {reasons} |")
        print()

    def print_details(rows: list[dict[str, Any]]) -> None:
        for r in rows:
            flags = []
            if r["not_ready_labels"]:
                flags.append(f"NOT-READY-LABEL:{','.join(r['not_ready_labels'])}")
            if r["design_labels"]:
                flags.append(f"NEEDS-DESIGN:{','.join(r['design_labels'])}")
            if r["open_pr"]:
                flags.append(
                    f"HAS-OPEN-PR:#{r['open_pr']['number']}"
                    + ("(draft)" if r["open_pr"]["draft"] else "")
                )
            if r["depends_on_open"]:
                flags.append("BLOCKED-BY:" + ",".join(f"#{n}" for n in r["depends_on_open"]))
            if r["unblocks_open"]:
                flags.append("UNBLOCKS:" + ",".join(f"#{n}" for n in r["unblocks_open"]))
            head = f"## #{r['number']} {r['title']}"
            if flags:
                head += "  ⟨" + " | ".join(flags) + "⟩"
            print(head)
            meta = [f"priority={tier_cell(r)}", f"score={r['priority_score']}",
                    f"labels={r['labels'] or '-'}", f"updated={r['updated_at']}"]
            if r["assignees"]:
                meta.append(f"assignees={r['assignees']}")
            if r["milestone"]:
                meta.append(f"milestone={r['milestone']}")
            if r["area"]:
                meta.append(f"area={r['area']}")
            if r["touches"]:
                meta.append("touches=" + ",".join(r["touches"]))
            if r["referenced_by_open"]:
                meta.append("referenced-by=" + ",".join(f"#{n}" for n in r["referenced_by_open"]))
            if r["mentions"]:
                meta.append("mentions=" + ",".join(f"#{n}" for n in r["mentions"]))
            print("- " + " · ".join(meta))
            print(f"- {r['url']}")
            if r["body"]:
                print(f"\n{r['body']}\n")
            elif args.body_chars <= 0:
                print()
            else:
                print("\n_(empty body)_\n")

    # --select is the cheap path, and it composes: --with-rank appends the
    # ranking table and --detail/--detail-top append issue bodies, so the one
    # question a run's startup actually asks — "what is the pick, what is behind
    # it, and what do the top few say?" — is one call and one gh fetch instead of
    # three. Unlike --issue, neither narrows the ranking they were chosen from.
    if args.select is not None:
        print(coverage_line)
        picks = [r for r in ranked if r["readiness"] == "READY"][: args.select]
        for i, r in enumerate(picks):
            print(f"{'select' if i == 0 else 'next  '}: #{r['number']} "
                  f"[{tier_cell(r)}] {r['title']} "
                  f"(score {r['priority_score']} · {' · '.join(r['score_reasons']) or '—'})")
        if not picks:
            print("select: none — no READY issue matches the filter")
        # Design-not-settled issues get their own line, not buried in `held:`
        # with dependency/label blocks — the reason to unblock them is
        # different (decide the design, not wait on something else).
        needs_design = [r for r in ranked if r["readiness"].startswith("DESIGN:")]
        if needs_design:
            print("needs-design: " + ", ".join(
                f"#{r['number']}[{tier_cell(r)}]" for r in needs_design)
                + " — 設計未確定のため保留(明示指定 / --include-design で着手可)")
        # Held issues explain why the pick is what it is; the top of that list
        # is where a merge will free something up, so 10 is plenty.
        held = [r for r in ranked
                if r["readiness"] != "READY" and not r["readiness"].startswith("DESIGN:")]
        if held:
            more = f" (+{len(held) - 10} more)" if len(held) > 10 else ""
            print("held: " + ", ".join(
                f"#{r['number']}[{tier_cell(r)}] {r['readiness']}" for r in held[:10])
                + more)
        if args.with_rank:
            print()
            print_rank_table()
        detail_numbers = list(dict.fromkeys(
            [r["number"] for r in ranked
             if r["readiness"] == "READY"][: args.detail_top] + args.detail
        ))
        if detail_numbers:
            by_number = {r["number"]: r for r in records}
            rows = [by_number[n] for n in detail_numbers if n in by_number]
            missing = [n for n in detail_numbers if n not in by_number]
            print()
            print_details(rows)
            if missing:
                print("not-in-digest: " + ",".join(f"#{n}" for n in missing))
        return 0

    print(f"# Open issues ({len(records)}) · open PRs ({len(prs)})\n")
    if not records:
        print("_No open issues match the filter._")
        return 0
    print(coverage_line + "\n")

    if not args.no_rank:
        print_rank_table()
        if args.rank_only:
            return 0

    print_details(payload["issues"])
    return 0




if __name__ == "__main__":
    raise SystemExit(main())
