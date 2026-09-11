#!/usr/bin/env python3
"""plan.py — The whole startup of a shipping-issues run, in one call.

Steps 0 through 2c of SKILL.md used to cost eight or more tool calls before a
line of code was written: preflight, a `--select`, a `--rank-only`, two or three
`--issue` passes to read the top issues, an ad-hoc probe for the repo's hook
manager, and a judgement call about which issues can share a batch. Every one of
those either re-fetched data another had already fetched, or re-measured a fact
that is constant for the repository.

This script answers all of it once and prints a single block: where the repo
stands, what the backlog ranks to, which issues can be worked in parallel, and
the exact next command. It makes exactly one `gh` fetch pair (and none at all on
a warm digest cache), and it never puts issue prose in the caller's context —
`issue_digest.py --detail-top` is the separate, deliberate call for that.

What it does NOT do is decide anything it cannot decide mechanically. The
grouping line says which of three states it is in — MECHANICAL, PARTIAL or
SERIAL — and PARTIAL means some candidate issue declares no `touches=`, so the
proposed batch is a starting point for the caller's own judgement rather than an
answer. That degrades in the right direction: the more issues carry a ship
contract, the less there is left to judge.

Usage:
    plan.py [--mode all|light|single|<issue number>] [--max-parallel N]
            [--label L]... [--assignee A] [--milestone M]
            [--include-design] [--refresh] [--record] [--json]

Exit codes:
    0 = a plan was printed (it may say SERIAL, or say there is nothing to ship)
    1 = preflight is BLOCKED, or the digest could not be read
    2 = usage error
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent
# How many worktrees a run will hold open at once unless the caller says
# otherwise. Three is a balance struck in cost-discipline.md, not a technical
# limit; --max-parallel is how a caller who asked for more gets it.
DEFAULT_MAX_PARALLEL = 3

# `light` mode is `all` narrowed to issues triage marked as shippable by a
# lightweight model (design settled, small, low-judgment).
LIGHT_LABEL = "model: light"

# Branch-name prefix by what the issue evidently is. Read from the title's
# conventional-commit prefix first, then its labels, so a repo that writes
# `fix(test): …` titles gets `fix/…` branches without being asked.
TYPE_FROM_LABEL = {
    "bug": "fix", "defect": "fix", "regression": "fix",
    "enhancement": "feat", "feature": "feat",
    "documentation": "docs", "docs": "docs",
    "chore": "chore", "test": "test", "refactor": "refactor",
    "performance": "perf", "security": "fix",
}


def existing_worktrees(runstate: str) -> list[str]:
    """Linked worktrees that already live under this run's own root.

    Read from git rather than from the filesystem: a directory left behind after
    `git worktree remove` failed is not a worktree, and a registered worktree
    whose directory is gone still holds its branch checked out. git's own list
    is the one that decides both.
    """
    if not runstate:
        return []
    root = str(Path(runstate).resolve() / "worktrees")
    rc, out, _ = run(["git", "worktree", "list", "--porcelain"])
    if rc != 0:
        return []
    found = []
    for line in out.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):].strip()
            if path.startswith(root + "/"):
                found.append(Path(path).name)
    return found


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def parse_kv(text: str) -> dict[str, str]:
    """`key: value` lines into a dict. Later keys win; indented continuation
    lines (preflight prints the dirty files that way) are ignored."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if not line or line[0].isspace():
            continue
        key, sep, value = line.partition(": ")
        if sep:
            out[key.strip()] = value.strip()
    return out


def slugify(title: str, limit: int = 40) -> str:
    """A branch-safe slug. Non-ASCII titles collapse to nothing rather than to
    mojibake, and the caller is expected to fill in a slug of its own then."""
    body = re.sub(r"^\s*\w+(\([^)]*\))?\s*:\s*", "", title)  # drop `fix(test): `
    slug = re.sub(r"[^a-z0-9]+", "-", body.lower()).strip("-")
    if len(slug) > limit:
        slug = slug[:limit].rsplit("-", 1)[0] or slug[:limit]
    return slug.strip("-")


def branch_type(row: dict[str, Any], labels: list[str]) -> str:
    m = re.match(r"^\s*(feat|fix|docs|chore|test|refactor|perf|build|ci|style)\b",
                 row.get("title", ""), re.IGNORECASE)
    if m:
        return m.group(1).lower()
    for label in labels:
        hit = TYPE_FROM_LABEL.get(label.strip().lower())
        if hit:
            return hit
    return "chore"


def branch_name(row: dict[str, Any], labels: list[str]) -> str:
    slug = slugify(row.get("title", ""))
    return f"{branch_type(row, labels)}/{row['number']}" + (f"-{slug}" if slug else "")


def normalize_path(raw: str) -> str:
    """A declared path in the one form the comparison can trust.

    `./src/`, `src`, `src/` and `/src/` are the same directory to everyone
    except a string comparison, and treating them as different is a failure in
    the direction that hurts: two issues that do collide get put in the same
    batch and meet again as a merge conflict. The trailing slash is added back
    for directories so that `src/` cannot prefix-match `src2/`.
    """
    p = raw.strip().strip("/")
    while p.startswith("./"):
        p = p[2:]
    p = "/".join(part for part in p.split("/") if part not in ("", "."))
    if not p:
        return ""
    # A path with no extension is treated as a directory, which is what a
    # `touches=` value almost always is; the slash is what makes prefix
    # matching mean "inside this directory" rather than "starts with these
    # letters".
    return p if "." in p.rsplit("/", 1)[-1] else p + "/"


def paths_collide(a: list[str], b: list[str]) -> bool:
    """Two issues collide when their declared paths overlap.

    `*` is an author saying "I do not know what this touches", which must read
    as "assume everything" — an unknown that defaults to *no* collision would
    silently put two conflicting issues in one batch, which is the expensive
    direction to be wrong in.
    """
    if "*" in a or "*" in b:
        return True
    xs = [n for n in (normalize_path(x) for x in a) if n]
    ys = [n for n in (normalize_path(y) for y in b) if n]
    for x in xs:
        for y in ys:
            if x == y or x.startswith(y) or y.startswith(x):
                return True
    return False


def group_batches(
    ready: list[dict[str, Any]], max_parallel: int
) -> tuple[list[list[dict[str, Any]]], str, list[int]]:
    """Split the READY issues into batches that can be worked concurrently.

    Returns (batches, confidence, undeclared) where confidence is MECHANICAL
    when every issue in the leading batch declared its paths, and PARTIAL when
    at least one did not — in which case the batch is a proposal and the caller
    still owes it a look.
    """
    batches: list[list[dict[str, Any]]] = []
    remaining = list(ready)
    while remaining:
        batch = [remaining.pop(0)]
        rest: list[dict[str, Any]] = []
        for row in remaining:
            in_batch = {r["number"] for r in batch}
            depends = set(row.get("depends_on_open") or [])
            unblocks = set(row.get("unblocks_open") or [])
            conflict = (
                len(batch) >= max_parallel
                # An issue that waits on, or is waited on by, something already
                # in the batch has to follow it — that ordering is the whole
                # reason dependency edges are read at all.
                or depends & in_batch
                or unblocks & in_batch
                or any(paths_collide(row.get("touches") or [],
                                     b.get("touches") or []) for b in batch)
            )
            (rest if conflict else batch).append(row)
        batches.append(batch)
        remaining = rest
    lead = batches[0] if batches else []
    undeclared = [r["number"] for r in lead if not r.get("touches")]
    confidence = ("SERIAL" if len(lead) < 2
                  else "PARTIAL" if undeclared else "MECHANICAL")
    return batches, confidence, undeclared


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", default="single",
                   help="all | light | single | an issue number (the skill's argument)")
    p.add_argument("--max-parallel", type=int, default=DEFAULT_MAX_PARALLEL,
                   help=f"worktrees held open at once in all mode "
                        f"(default {DEFAULT_MAX_PARALLEL}); the user asking for "
                        f"more is the only reason to raise it")
    p.add_argument("--label", action="append", default=[])
    p.add_argument("--assignee")
    p.add_argument("--milestone")
    p.add_argument("--include-design", action="store_true")
    p.add_argument("--refresh", action="store_true",
                   help="re-fetch instead of reading the digest cache")
    p.add_argument("--record", action="store_true",
                   help="write run-start and selection to the run record")
    p.add_argument("--allow-existing-worktrees", action="store_true",
                   help="do not stop on worktrees already under this run's own "
                        "root. Required for the re-plans at steps 7 and 8c, "
                        "where the run's own worktrees are supposed to be there")
    p.add_argument("--json", action="store_true", dest="as_json")
    args = p.parse_args()

    explicit_issue = None
    if args.mode not in ("all", "light", "single"):
        if not args.mode.lstrip("#").isdigit():
            print("error: --mode takes 'all', 'light', 'single' or an issue number",
                  file=sys.stderr)
            return 2
        explicit_issue = int(args.mode.lstrip("#"))
    if args.mode == "light" and LIGHT_LABEL not in args.label:
        args.label.append(LIGHT_LABEL)
    if args.max_parallel < 1:
        print("error: --max-parallel must be at least 1", file=sys.stderr)
        return 2

    # --- 1. preflight, including the repo profile it now carries -----------
    # Two calls, deliberately: preflight is the only thing that knows where this
    # repo's run state lives, and the profile cache lives inside it. The first
    # call is local-only and costs nothing; `--with-github` is held back for the
    # second so the one `gh` probe is not paid for twice.
    profile_cache_placeholder = "<runstate>/repo-profile.json"
    rc, out, err = run([str(SKILL_DIR / "preflight.sh")])
    pre = parse_kv(out)
    runstate = pre.get("runstate", "")
    if rc != 0:
        print(out.rstrip())
        print(err.rstrip(), file=sys.stderr)
        print("verdict: BLOCKED")
        return 1
    cmd = [str(SKILL_DIR / "preflight.sh"), "--with-github"]
    if runstate:
        profile_cache_placeholder = str(Path(runstate) / "repo-profile.json")
        cmd += ["--profile-cache", profile_cache_placeholder]
    rc2, out2, _ = run(cmd)
    if rc2 == 0:
        pre = parse_kv(out2)

    # Everything below reads preflight by key name. A key that is missing —
    # preflight renamed it, or failed halfway and still exited 0 — used to
    # degrade silently: `verify_command` defaulting to NONE meant the batch was
    # provisioned with no baseline at all and nothing said so, which quietly
    # removes the check that catches a broken repo before three implementation
    # runs are spent on it. Missing keys are now a stop.
    missing_keys = [k for k in ("repo_slug", "default_branch", "runstate",
                                "verify_command", "pkg_manager", "hooks")
                    if k not in pre]
    if missing_keys:
        print("# shipping-issues plan")
        print("preflight-keys-missing: " + ",".join(missing_keys))
        print("plan.py reads preflight.sh by key name and will not guess at a "
              "missing one. Run preflight.sh directly to see what it printed.")
        print("verdict: BLOCKED")
        return 1

    # --- 1b. leftovers under this run's own root --------------------------
    # A worktree under <runstate>/worktrees on the opening call belongs to an
    # earlier run that did not clean up, or to a run happening right now. Either
    # way it is someone else's work by the skill's stop-condition rule, and the
    # branch inside it is stale: provisioning over it returns EXISTS and the run
    # would then implement on top of a branch it never created. Reported, not
    # silently reused. The re-plans at steps 7 and 8c pass
    # --allow-existing-worktrees because by then the worktrees are the run's own.
    leftovers = existing_worktrees(runstate)
    if leftovers and not args.allow_existing_worktrees:
        print("# shipping-issues plan")
        print(f"repo: {pre.get('repo_slug', '?')} · runstate: {runstate}")
        print("existing-worktrees: " + ", ".join(leftovers))
        print("These are under this run's own root and this run did not create "
              "them. Confirm nothing is running in them, then either remove "
              "them or re-run with --allow-existing-worktrees:")
        print(f"  {SKILL_DIR}/cleanup_run.sh --dry-run "
              f"--worktree-root {runstate}/worktrees")
        print("verdict: BLOCKED")
        return 1

    # --- 2. the digest, in one fetch --------------------------------------
    # --json returns the whole payload regardless of the text-output flags, and
    # --body-chars 0 is what keeps issue prose out of it: the plan is a decision
    # block, and reading bodies is the separate, deliberate --detail-top call.
    digest_cmd = [sys.executable, str(SKILL_DIR / "issue_digest.py"),
                  "--json", "--body-chars", "0", "--cache-ttl", "300"]
    for label in args.label:
        digest_cmd += ["--label", label]
    if args.assignee:
        digest_cmd += ["--assignee", args.assignee]
    if args.milestone:
        digest_cmd += ["--milestone", args.milestone]
    if args.include_design or explicit_issue is not None:
        digest_cmd.append("--include-design")
    if args.refresh:
        digest_cmd.append("--refresh")
    rc, out, err = run(digest_cmd)
    if rc != 0:
        print(err.rstrip() or out.rstrip(), file=sys.stderr)
        print("verdict: BLOCKED")
        return 1
    try:
        digest = json.loads(out)
    except ValueError:
        print("error: issue_digest.py did not return JSON", file=sys.stderr)
        return 1

    labels_by_number = {i["number"]: i["labels"] for i in digest["issues"]}
    ranking = digest["ranking"]
    ready = [r for r in ranking if r["readiness"] == "READY"]
    if explicit_issue is not None:
        ready = [r for r in ranking if r["number"] == explicit_issue]

    # --- 3. grouping -------------------------------------------------------
    if args.mode in ("all", "light") and explicit_issue is None:
        batches, confidence, undeclared = group_batches(ready, args.max_parallel)
    else:
        # One issue means one branch in the main checkout: a worktree for it
        # costs a dependency install and buys nothing.
        batches = [ready[:1]] if ready else []
        confidence, undeclared = "SERIAL", []
    # A repo already known not to survive a worktree cannot go parallel however
    # cleanly the issues group.
    if pre.get("worktree_viable") == "no" and confidence != "SERIAL":
        confidence = "SERIAL"

    lead = batches[0] if batches else []
    plan_mode = "parallel" if confidence in ("MECHANICAL", "PARTIAL") else "serial"
    branches = {r["number"]: branch_name(r, labels_by_number.get(r["number"], []))
                for r in lead}
    if plan_mode == "parallel":
        specs = " ".join(f"--spec {n}:{b}" for n, b in branches.items())
        verify = pre["verify_command"]
        next_cmd = (
            f"{SKILL_DIR}/worktree_setup.sh {specs} "
            f"--base {pre['default_branch']} "
            f"--root {runstate}/worktrees --log-dir {runstate}/verify"
            + (f' --verify "{verify}"' if verify != "NONE" else "")
        )
    elif lead:
        n = lead[0]["number"]
        next_cmd = (f"git switch {pre.get('default_branch', 'main')} && "
                    f"git pull --ff-only && git switch -c {branches[n]}")
    else:
        next_cmd = "nothing to ship — see held:/needs-design: above"

    payload = {
        "preflight": pre,
        "mode": args.mode,
        "plan_mode": plan_mode,
        "grouping": confidence,
        "undeclared_touches": undeclared,
        "max_parallel": args.max_parallel,
        "batches": [[r["number"] for r in b] for b in batches],
        "branches": branches,
        "select": lead[0]["number"] if lead else None,
        "next_command": next_cmd,
        "label_coverage": digest["label_coverage"],
        "contract_coverage": digest["contract_coverage"],
        "needs_design": digest["needs_design"],
        "cache": digest.get("cache"),
        "open_issue_count": digest["open_issue_count"],
        "open_pr_count": digest["open_pr_count"],
        "profile_cache": profile_cache_placeholder,
    }

    if args.record:
        record = [sys.executable, str(SKILL_DIR / "run_record.py"),
                  "--event", "run-start", "--field", f"mode={args.mode}"]
        slug = pre.get("repo_slug")
        if slug and slug != "UNKNOWN":
            record += ["--repo", slug]
        run(record)
        if lead:
            sel = [sys.executable, str(SKILL_DIR / "run_record.py"),
                   "--event", "selection",
                   "--field", f"issue={lead[0]['number']}",
                   "--field", f"tier={lead[0]['effective_tier']}",
                   "--field", f"plan={plan_mode}",
                   "--field", f"batch={','.join(str(r['number']) for r in lead)}"]
            if slug and slug != "UNKNOWN":
                sel += ["--repo", slug]
            run(sel)
        if plan_mode == "parallel":
            grp = [sys.executable, str(SKILL_DIR / "run_record.py"),
                   "--event", "parallel-group",
                   "--field", f"issues={','.join(str(r['number']) for r in lead)}",
                   "--field", "mode=parallel",
                   "--field", f"reason=grouping={confidence}"]
            if slug and slug != "UNKNOWN":
                grp += ["--repo", slug]
            run(grp)

    if args.as_json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    ccov = digest["contract_coverage"]
    print("# shipping-issues plan")
    print(f"repo: {pre.get('repo_slug', '?')} · default: "
          f"{pre.get('default_branch', '?')} · runstate: {runstate or '?'}")
    print(f"preflight: {pre.get('verdict', '?')} · tree: "
          f"{pre.get('working_tree', '?')} · worktrees: "
          f"{pre.get('existing_worktrees', 'none')}")
    print(f"profile: pkg={pre.get('pkg_manager', '?')} "
          f"verify={pre.get('verify_command', '?')!r} "
          f"hooks={pre.get('hooks', '?')} "
          f"worktree_viable={pre.get('worktree_viable', 'unknown')} "
          f"(cache {pre.get('profile_cache', 'off')})")
    print(f"github: auth={pre.get('gh_auth', '?')} write={pre.get('gh_write', '?')}")
    # The verify command is a guess from script names, and it gets executed as
    # the baseline. Saying where it came from is what lets the caller notice
    # that `test` was picked in a repo whose real gate is `lint && typecheck &&
    # test`, or that the chosen script starts a watcher and will never exit.
    verify = pre["verify_command"]
    if verify == "NONE":
        print("verify-check: NONE found — decide the baseline command yourself, "
              "or run without one and say so in the report")
    else:
        print(f"verify-check: {verify!r} (from {pre.get('verify_source', '?')}) "
              "— confirm it is this repo's real gate and that it terminates")
    print()
    print(f"backlog: {digest['open_issue_count']} open · "
          f"{digest['open_pr_count']} open PRs · digest-cache {digest.get('cache')}")
    cov = digest["label_coverage"]
    print(f"labels: {cov['labeled']}/{cov['total']}"
          + (f" · contract-ranked {cov['contract_ranked']}"
             if cov["contract_ranked"] else "")
          + (" COMPLETE" if cov["complete"] else
             " — no tier: " + ",".join(f"#{n}" for n in cov["unranked"][:10])))
    if ccov["missing"] or ccov["incomplete"]:
        print(f"contract: {ccov['full']}/{ccov['total']} complete — "
              f"{len(ccov['missing'])} missing, {ccov['partial']} partial "
              "(issue_digest.py --audit for the list)")
    print()
    print(f"mode: {args.mode} · plan: {plan_mode} · grouping: {confidence}"
          + (f" · max-parallel {args.max_parallel}" if plan_mode == "parallel" else ""))
    if plan_mode == "parallel":
        print("  ⚠ the batch below is a PROPOSAL, not a decision — confirm it "
              "before provisioning (step 2c)")
        if confidence == "PARTIAL":
            print("    no touches= on " + ",".join(f"#{n}" for n in undeclared)
                  + ": those were grouped on dependency edges alone")
    for i, batch in enumerate(batches[:3]):
        tag = "batch " + chr(ord("A") + i)
        rows = ", ".join(
            f"#{r['number']}[{r['effective_tier']}]"
            + ("" if r.get("touches") else "(no touches)")
            for r in batch
        )
        print(f"{tag}: {rows}")
    if len(batches) > 3:
        print(f"  (+{len(batches) - 3} more batches after those)")
    if lead:
        top = lead[0]
        print(f"select: #{top['number']} [{top['effective_tier']}] {top['title']} "
              f"(score {top['score']} · {' · '.join(top['reasons']) or '—'})")
        print("branch: " + " ".join(f"#{n}→{b}" for n, b in branches.items()))
    else:
        print("select: none — no READY issue matches the filter")
    if digest["needs_design"]:
        print("needs-design: "
              + ",".join(f"#{n}" for n in digest["needs_design"])
              + " → step 8b background agents (spawn now, do not wait)")
    held = [r for r in ranking
            if r["readiness"] != "READY" and not r["readiness"].startswith("DESIGN:")]
    if held:
        more = f" (+{len(held) - 6} more)" if len(held) > 6 else ""
        print("held: " + ", ".join(
            f"#{r['number']} {r['readiness']}" for r in held[:6]) + more)
    print()
    print(f"next: {next_cmd}")
    print("verdict: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
