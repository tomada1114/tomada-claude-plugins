#!/usr/bin/env python3
"""file_followup.py — File a follow-up issue found while shipping another one.

A shipping run turns up real defects that are not the issue being shipped:
a sibling of the bug just fixed, a latent gap the diff walked past, a scope
the implementation agent deliberately declined. Fixing them inline silently
widens the PR; dropping them loses them. This files them instead, so the
finding survives the run as a ranked backlog entry.

The tier label is resolved against what the repo *already uses*. A repo whose
convention is `p2` gets `p2`, not a second parallel `priority: P2` vocabulary
that would split its own backlog in two. Only a repo with no tier label at all
gets the canonical name created.

The target repo is resolved once and echoed on every line of output. This
script writes to GitHub from whatever directory it is invoked in, and a
sub-agent's cwd is not always the repo being shipped — an unqualified `gh`
would happily file the finding against an unrelated repo that merely happens
to be the working directory. Pass `--repo` when in any doubt.

Usage:
    file_followup.py --title T --body-file F --tier P2 [--label L ...]
                     [--needs-design] [--found-while N] [--repo OWNER/NAME]
                     [--dry-run] [--json]

`--needs-design` marks the new issue design-not-settled (`blocked: design` or
this repo's existing equivalent) — use it only when the finding names an open
design question rather than a verified fix. See
references/filing-followups.md. `--tier` is still required even then, so the
issue ranks correctly the moment the design is decided.

Exit codes:
    0 = issue created (or --dry-run resolved cleanly)
    1 = usage/environment error
    2 = no write access to this repo — report the finding in the run summary
        instead, and do not retry
    3 = invalid argument (unknown tier, missing body file)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from issue_digest import (DESIGN_LABEL, TIER_ALIASES, TIER_LABELS, TIER_ORDER,
                          normalize_label, resolve_design_label)

PERMISSION_MARKERS = ("HTTP 403", "Resource not accessible", "must have admin",
                      "does not have permission", "HTTP 404: Not Found")

# Set once in main(); every gh call is qualified with it so cwd cannot decide
# which repo a finding lands in.
REPO: str | None = None


def gh(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    if REPO:
        args = [*args, "--repo", REPO]
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


def repo_labels() -> list[str]:
    raw = gh(["label", "list", "--limit", "500", "--json", "name"]).stdout or "[]"
    return [lbl["name"] for lbl in json.loads(raw)]


def resolve_tier_label(tier: str, existing: list[str], dry_run: bool) -> str:
    """Return the label name this repo uses for `tier`, creating it if absent.

    Preference order: the canonical `priority: Pn` if the repo already has it,
    then any existing alias that means the same tier (`p2`, `high priority`,
    ...), then create the canonical one. Picking an alias the repo already
    carries is the whole point — `issue_digest.py` ranks by whatever spelling
    is present, so introducing a second one would leave half the backlog
    ranked by a label nobody else writes.
    """
    canonical = TIER_LABELS[tier][0]
    by_norm = {normalize_label(name): name for name in existing}

    if normalize_label(canonical) in by_norm:
        return by_norm[normalize_label(canonical)]

    aliases = [name for norm, name in by_norm.items()
               if TIER_ALIASES.get(norm) == tier]
    if aliases:
        # Shortest wins: `p2` over `priority: medium` when a repo has drifted
        # into carrying both, since the shorter form is the one being typed.
        return min(aliases, key=lambda n: (len(n), n))

    name, color, desc = TIER_LABELS[tier]
    if not dry_run:
        gh(["label", "create", name, "--color", color, "--description", desc])
    return name


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--title", required=True,
                   help="issue title; follow the repo's commit/title convention")
    p.add_argument("--body-file", required=True, type=Path,
                   help="path to the issue body (write it to a file first)")
    p.add_argument("--tier", required=True, choices=TIER_ORDER,
                   help="priority tier for the finding, per references/priority-rubric.md")
    p.add_argument("--label", action="append", default=[], metavar="NAME",
                   help="extra label (repeatable); silently skipped if the repo lacks it")
    p.add_argument("--needs-design", action="store_true",
                   help="mark the new issue design-not-settled (blocked: "
                        "design or this repo's equivalent) — excludes it "
                        "from automatic selection until the design is decided")
    p.add_argument("--found-while", type=int, metavar="N",
                   help="issue number this was found while shipping; appends a "
                        "provenance line to the body")
    p.add_argument("--repo", metavar="OWNER/NAME",
                   help="target repo; defaults to the one cwd resolves to. Pass "
                        "it explicitly when cwd may not be the repo being shipped")
    p.add_argument("--dry-run", action="store_true",
                   help="resolve labels and print what would be filed")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args()

    # Resolve before any other gh call, and echo it, so cwd can never quietly
    # decide which repo a finding lands in. `gh repo view` takes the repo as a
    # positional, not --repo, so this one call bypasses the gh() wrapper.
    global REPO
    view = ["gh", "repo", "view"] + ([args.repo] if args.repo else [])
    proc = subprocess.run([*view, "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                          capture_output=True, text=True, timeout=120)
    REPO = (proc.stdout or "").strip()
    if proc.returncode != 0 or not REPO:
        target = args.repo or "the current directory"
        print(f"error: cannot resolve {target} — run inside the repo or pass "
              f"--repo OWNER/NAME\n{(proc.stderr or '').strip()}", file=sys.stderr)
        return 1

    if not args.body_file.is_file():
        print(f"error: --body-file not found: {args.body_file}", file=sys.stderr)
        return 3
    body = args.body_file.read_text(encoding="utf-8").strip()
    if not body:
        print(f"error: --body-file is empty: {args.body_file}", file=sys.stderr)
        return 3
    if args.found_while:
        body += f"\n\n---\n\n*#{args.found_while} の作業中に発見 / found while shipping #{args.found_while}.*\n"

    existing = repo_labels()
    tier_label = resolve_tier_label(args.tier, existing, args.dry_run)

    design_label = None
    if args.needs_design:
        design_label, needs_create = resolve_design_label(existing)
        if needs_create and not args.dry_run:
            name, color, desc = DESIGN_LABEL
            gh(["label", "create", name, "--color", color, "--description", desc])

    by_norm = {normalize_label(n): n for n in existing}
    extra, missing = [], []
    for name in args.label:
        match = by_norm.get(normalize_label(name))
        (extra.append(match) if match else missing.append(name))

    labels = [tier_label, *([design_label] if design_label else []), *dict.fromkeys(extra)]

    if args.dry_run:
        out = {"dry_run": True, "repo": REPO, "title": args.title,
               "labels": labels, "skipped_labels": missing, "body_chars": len(body)}
        print(json.dumps(out, ensure_ascii=False) if args.json
              else f"would file in {REPO}: {args.title}\n  labels: {', '.join(labels)}"
                   + (f"\n  skipped (not in repo): {', '.join(missing)}" if missing else ""))
        return 0

    # gh reads the body from a file so no shell quoting can mangle it.
    tmp = args.body_file.with_suffix(args.body_file.suffix + ".filed")
    tmp.write_text(body, encoding="utf-8")
    try:
        cmd = ["issue", "create", "--title", args.title, "--body-file", str(tmp)]
        for name in labels:
            cmd += ["--label", name]
        # gh prints the new issue's URL last; anything else means it changed
        # its output and the caller must not be told a URL that is not there.
        lines = [ln.strip() for ln in (gh(cmd).stdout or "").splitlines() if ln.strip()]
        if not lines:
            print("error: gh issue create produced no output; check the repo "
                  "manually before re-running (it may have been filed)",
                  file=sys.stderr)
            return 1
        url = lines[-1]
    finally:
        tmp.unlink(missing_ok=True)

    if args.json:
        print(json.dumps({"url": url, "repo": REPO, "labels": labels,
                          "skipped_labels": missing}, ensure_ascii=False))
    else:
        print(f"filed: {url}  [{', '.join(labels)}]"
              + (f"  skipped: {', '.join(missing)}" if missing else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
