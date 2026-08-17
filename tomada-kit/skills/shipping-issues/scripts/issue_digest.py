#!/usr/bin/env python3
"""issue_digest.py — Priority- and dependency-annotated digest of open GitHub issues.

Fetches open issues (and open PRs, to detect work already in flight) via the
`gh` CLI and prints a token-lean digest. Raw `gh --json` output never has to
enter a context window.

Beyond the mechanical readiness flags (BLOCKED-BY / HAS-OPEN-PR /
NOT-READY-LABEL) it computes two things the ordering decision needs:

  * reverse dependency edges — how many *other* open issues this one unblocks,
    which is the single strongest "do this first" signal;
  * a heuristic priority score built from unblock count, priority labels,
    leverage keywords (CI, schema, interface, security, breakage…), milestone,
    and staleness.

The score is a *ranking hint*, not a verdict. It is computed from the raw issue
bodies even when `--body-chars 0` keeps that prose out of the caller's context,
so the index-only pass is still ranked. Confirm the top candidates against
references/priority-rubric.md before acting on them.

Usage:
    issue_digest.py [--label L]... [--assignee A] [--milestone M]
                    [--issue N]... [--limit N] [--body-chars N]
                    [--rank-only] [--no-rank] [--json]

Output (default: markdown). `--json` emits the same data as a JSON object for
programmatic consumers.

Exit codes:
    0 = digest printed (may contain zero issues)
    1 = gh invocation failed
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from typing import Any

# Dependency phrasings seen in real issue bodies, EN + JA.
DEP_PATTERNS = [
    (r"(?:depends?\s+on|blocked\s+by|after|requires?)\s*:?\s*#(\d+)", "depends_on"),
    (r"(?:blocks|blocking)\s*:?\s*#(\d+)", "blocks"),
    (r"#(\d+)\s*(?:に依存|の後|完了後|がマージされてから|の続き)", "depends_on"),
    (r"(?:前提|依存|ブロッカー|先行)\s*:?\s*#(\d+)", "depends_on"),
    (r"#(\d+)\s*(?:をブロック|の前提)", "blocks"),
]

CLOSING_RE = re.compile(
    r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s*#(\d+)", re.IGNORECASE
)
BARE_REF_RE = re.compile(r"(?<![\w/])#(\d+)")

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
    "needs design",
    "needs-design",
    "wip",
    "draft",
}

# Explicit priority signals, by exact (lower-cased) label name.
PRIORITY_LABEL_WEIGHTS = {
    "p0": 8, "priority:p0": 8, "priority/p0": 8, "sev1": 8, "severity:1": 8,
    "critical": 8, "urgent": 8, "security": 8, "incident": 8, "blocker": 8,
    "p1": 5, "priority:high": 5, "priority/high": 5, "high priority": 5,
    "high-priority": 5, "regression": 5,
    "important": 4, "broken": 4,
    "bug": 3, "defect": 3,
    "p2": 1, "priority:medium": 1, "priority/medium": 1,
    "enhancement": 0, "feature": 0,
    "documentation": -1, "docs": -1, "chore": -1,
    "p3": -2, "p4": -2, "priority:low": -2, "priority/low": -2,
    "low priority": -2, "low-priority": -2, "nice to have": -2,
    "nice-to-have": -2, "someday": -2,
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


def score_issue(rec: dict[str, Any], raw_body: str) -> tuple[int, list[str]]:
    """Heuristic priority score plus a human-readable breakdown.

    Weighted toward *impact on other work*: unblocking other open issues and
    touching shared foundations outrank a self-contained nice-to-have.
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
        w = PRIORITY_LABEL_WEIGHTS.get(lbl.strip().lower())
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

    return score, parts


def readiness(rec: dict[str, Any]) -> str:
    if rec["depends_on_open"]:
        return "BLOCKED-BY:" + ",".join(f"#{n}" for n in rec["depends_on_open"])
    if rec["not_ready_labels"]:
        return "LABEL:" + ",".join(rec["not_ready_labels"])
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
    p.add_argument("--no-rank", action="store_true",
                   help="omit the priority ranking table")
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

    issues = run_gh(issue_args)
    prs = run_gh([
        "pr", "list", "--state", "open", "--limit", "100",
        "--json", "number,title,body,headRefName,isDraft,url",
    ])

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
    for it in issues:
        all_deps[it["number"]] = extract_deps(
            it.get("body") or "", it.get("title", ""), it["number"]
        )
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
        blockers = [lbl for lbl in labels if lbl.lower() in READY_NEGATIVE_LABELS]
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
            "depends_on_open": [n for n in deps["depends_on"] if n in open_numbers],
            "unblocks_open": sorted(unblocks.get(num, set())),
            "referenced_by_open": sorted(referenced_by.get(num, set())),
            "not_ready_labels": blockers,
            "open_pr": {"number": pr["number"], "url": pr["url"],
                        "draft": pr["isDraft"]} if pr else None,
            "body": squeeze(body, args.body_chars),
        }
        rec["priority_score"], rec["score_reasons"] = score_issue(rec, body)
        rec["readiness"] = readiness(rec)
        records.append(rec)

    ranked = sorted(
        records,
        key=lambda r: (r["readiness"] != "READY", -r["priority_score"], r["number"]),
    )

    payload = {
        "open_issue_count": len(records),
        "open_pr_count": len(prs),
        "ranking": [
            {"number": r["number"], "score": r["priority_score"],
             "readiness": r["readiness"], "reasons": r["score_reasons"]}
            for r in ranked
        ],
        "issues": sorted(records, key=lambda r: r["number"]),
    }

    if args.as_json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    print(f"# Open issues ({len(records)}) · open PRs ({len(prs)})\n")
    if not records:
        print("_No open issues match the filter._")
        return 0

    if not args.no_rank:
        print("## Priority ranking (heuristic — verify against priority-rubric.md)\n")
        print("| issue | score | readiness | signals |")
        print("|---|---|---|---|")
        for r in ranked:
            title = r["title"].replace("|", "\\|")
            if len(title) > 60:
                title = title[:59] + "…"
            reasons = " · ".join(r["score_reasons"]) or "—"
            print(f"| #{r['number']} {title} | {r['priority_score']} | "
                  f"{r['readiness']} | {reasons} |")
        print()
        if args.rank_only:
            return 0

    for r in payload["issues"]:
        flags = []
        if r["not_ready_labels"]:
            flags.append(f"NOT-READY-LABEL:{','.join(r['not_ready_labels'])}")
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
        meta = [f"score={r['priority_score']}", f"labels={r['labels'] or '-'}",
                f"updated={r['updated_at']}"]
        if r["assignees"]:
            meta.append(f"assignees={r['assignees']}")
        if r["milestone"]:
            meta.append(f"milestone={r['milestone']}")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
