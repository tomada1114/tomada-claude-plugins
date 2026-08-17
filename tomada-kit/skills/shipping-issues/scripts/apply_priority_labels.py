#!/usr/bin/env python3
"""apply_priority_labels.py — Write the `priority: P0..P3` labels this skill ranks by.

The tier label is the backlog's persisted priority. Once every open issue
carries one, `issue_digest.py` orders the backlog by reading labels, and no
model has to re-read issue prose to re-derive priority on the next run.

Two ways to write them, both cheap for the caller:

  --backfill        every open issue without a tier gets the digest's suggested
                    one. Pure heuristic, no model involved, one summary line out.
  --set N=P0 ...    explicit assignments, for the handful the research pass in
                    references/priority-rubric.md judged differently. Run by the
                    triage sub-agent that did the judging, not by the parent.

Missing label definitions are created first (name, color, description from
issue_digest.TIER_LABELS). Applying a tier removes any other tier label the
issue carries, including legacy spellings like `critical` or `priority/high`,
so an issue always ends with exactly one.

Usage:
    apply_priority_labels.py --backfill [--quiet] [--dry-run] [--json]
    apply_priority_labels.py --set 12=P0 [--set 9=P2 ...] [--quiet] [--dry-run]
    apply_priority_labels.py --ensure-labels [--dry-run]

Exit codes:
    0 = labels applied (possibly zero changes)
    1 = gh invocation failed
    2 = no write access to this repo — labels cannot be used here; rank from the
        digest's suggested tiers instead and do not retry
    3 = invalid argument (unknown tier, unparseable --set)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from issue_digest import TIER_ALIASES, TIER_LABELS, TIER_ORDER, normalize_label

DIGEST = Path(__file__).resolve().parent / "issue_digest.py"

# gh prints these when the token lacks push access; the caller must stop asking
# for labels rather than retry.
PERMISSION_MARKERS = ("HTTP 403", "Resource not accessible", "must have admin",
                      "does not have permission", "HTTP 404: Not Found")


def gh(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["gh", *args], capture_output=True, text=True,
                              check=check, timeout=120)
    except FileNotFoundError:
        print("error: gh CLI not found", file=sys.stderr)
        raise SystemExit(1)
    except subprocess.TimeoutExpired:
        print(f"error: gh {' '.join(args)} timed out", file=sys.stderr)
        raise SystemExit(1)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        if any(m in stderr for m in PERMISSION_MARKERS):
            print(f"verdict: NO_WRITE_ACCESS\nerror: gh {' '.join(args)}:\n{stderr}",
                  file=sys.stderr)
            raise SystemExit(2)
        print(f"error: gh {' '.join(args)} failed:\n{stderr}", file=sys.stderr)
        raise SystemExit(1)


def load_digest() -> dict[str, Any]:
    """Open issues with their tiers and suggestions — bodies deliberately omitted."""
    proc = subprocess.run(
        [sys.executable, str(DIGEST), "--json", "--body-chars", "0"],
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        print(f"error: issue_digest.py failed:\n{proc.stderr}", file=sys.stderr)
        raise SystemExit(1)
    return json.loads(proc.stdout)


def ensure_labels(dry_run: bool) -> list[str]:
    """Create whichever of the four tier labels this repo is missing."""
    existing = {lbl["name"].lower()
                for lbl in json.loads(gh(["label", "list", "--limit", "500",
                                          "--json", "name"]).stdout or "[]")}
    created = []
    for tier in TIER_ORDER:
        name, color, desc = TIER_LABELS[tier]
        if name.lower() in existing:
            continue
        created.append(name)
        if not dry_run:
            gh(["label", "create", name, "--color", color, "--description", desc])
    return created


def parse_sets(pairs: list[str]) -> dict[int, str]:
    out: dict[int, str] = {}
    for pair in pairs:
        num, _, tier = pair.partition("=")
        tier = tier.strip().upper()
        if not num.strip().lstrip("#").isdigit() or tier not in TIER_ORDER:
            print(f"error: --set expects N=P0|P1|P2|P3, got {pair!r}", file=sys.stderr)
            raise SystemExit(3)
        out[int(num.strip().lstrip("#"))] = tier
    return out


def apply(number: int, tier: str, current_labels: list[str], dry_run: bool) -> bool:
    """Add the tier label to an issue and strip any other tier it carries.

    Returns False when the issue already carries exactly that label.
    """
    target = TIER_LABELS[tier][0]
    stale = [lbl for lbl in current_labels
             if normalize_label(lbl) in TIER_ALIASES and lbl != target]
    if target in current_labels and not stale:
        return False
    args = ["issue", "edit", str(number), "--add-label", target]
    for lbl in stale:
        args += ["--remove-label", lbl]
    if not dry_run:
        gh(args)
    return True


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--backfill", action="store_true",
                   help="label every open issue that has no tier yet")
    p.add_argument("--set", action="append", default=[], metavar="N=TIER",
                   help="assign a tier explicitly, e.g. --set 12=P0")
    p.add_argument("--ensure-labels", action="store_true",
                   help="only create the four label definitions")
    p.add_argument("--dry-run", action="store_true",
                   help="print the plan without touching GitHub")
    p.add_argument("--quiet", action="store_true",
                   help="print only the summary line, not one line per issue")
    p.add_argument("--json", action="store_true", dest="as_json")
    args = p.parse_args()

    if not (args.backfill or args.set or args.ensure_labels):
        p.error("one of --backfill, --set, or --ensure-labels is required")
    if not shutil.which("gh"):
        print("error: gh CLI not found", file=sys.stderr)
        return 1

    created = ensure_labels(args.dry_run)
    if args.ensure_labels and not (args.backfill or args.set):
        print(f"verdict: OK\ncreated: {', '.join(created) or 'none (all four existed)'}")
        return 0

    payload = load_digest()
    issues = {r["number"]: r for r in payload["issues"]}

    plan: list[tuple[int, str, str]] = []  # number, tier, why
    if args.backfill:
        for rec in payload["issues"]:
            if not rec["priority_tier"]:
                plan.append((rec["number"], rec["suggested_tier"], rec["suggested_reason"]))
    for number, tier in parse_sets(args.set).items():
        plan = [row for row in plan if row[0] != number]
        plan.append((number, tier, "explicit"))

    changed, unchanged, missing = [], [], []
    for number, tier, why in sorted(plan):
        rec = issues.get(number)
        if rec is None:
            # Not in the open-issue digest: closed, or filtered out. Still label
            # it — an explicit --set on a just-closed issue is not an error.
            missing.append(number)
            if apply(number, tier, [], args.dry_run):
                changed.append((number, tier, why, "not-open"))
            continue
        if apply(number, tier, rec["labels"], args.dry_run):
            changed.append((number, tier, why, rec["priority_tier"] or "none"))
        else:
            unchanged.append(number)

    verb = "would set" if args.dry_run else "set"
    breakdown = " ".join(
        f"{t}×{sum(1 for _, tier, _, _ in changed if tier == t)}"
        for t in TIER_ORDER if any(tier == t for _, tier, _, _ in changed)
    )
    if args.as_json:
        json.dump({"verdict": "OK", "dry_run": args.dry_run,
                   "created_labels": created,
                   "changed": [{"number": n, "tier": t, "why": w, "was": was}
                               for n, t, w, was in changed],
                   "unchanged": unchanged, "not_open": missing},
                  sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    if not args.quiet:
        for number, tier, why, was in changed:
            print(f"#{number}: {was} -> {TIER_LABELS[tier][0]}  ({why})")

    coverage = payload["label_coverage"]
    # Only issues that had no tier at all move the coverage number; a re-tier of
    # an already-labeled issue does not, and a closed one is not counted here.
    after = coverage["labeled"] + sum(1 for _, _, _, was in changed if was == "none")
    print(f"verdict: OK\n"
          f"labels-{'to-create' if args.dry_run else 'created'}: "
          f"{', '.join(created) or 'none'}\n"
          f"{verb}: {len(changed)}{f' ({breakdown})' if breakdown else ''} · "
          f"already-correct: {len(unchanged)} · "
          f"coverage: {min(after, coverage['total'])}/{coverage['total']} open issues labeled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
