#!/usr/bin/env python3
"""review_digest.py — Read a CI review's summary comment and print a digest.

references/ci-review.md is the authoritative contract this script implements:
what the review job's summary comment looks like, what this skill's response
comment looks like, and why the marker line is what tells "reviewed, found
nothing" apart from "never ran" (the review check is green either way).

The summary comment's first line is a marker:

    <!-- claude-review v1 sha=<40-hex head sha> must=<n> should=<n> nit=<n> pre=<n> -->

followed by finding lines shaped:

    - [<severity>] R<n> `<path>:<line>` — <what is wrong> — <why it matters>

Only a comment from a **bot** account whose login is in --reviewer (default
claude[bot]) is trusted — the repo is public-facing, so anyone can post a
comment carrying the marker, and a forged `must=0` would otherwise wave a
pull request through. A marker from anyone else is reported under
`warnings:` with its author's login, never silently accepted.

Usage:
    review_digest.py <pr> [--repo OWNER/NAME] [--sha SHA]
                     [--reviewer LOGIN ...]
    review_digest.py <pr> --respond FILE [--repo OWNER/NAME] [--sha SHA]

Read mode prints:

    review: REVIEWED | NOT_REVIEWED
    sha: <sha looked for, default the PR head>
    round: <n distinct head shas the reviewer has summarized on this PR>
    counts: must=<n> should=<n> nit=<n> pre=<n>
    findings:
      R1 must-fix src/x.ts:12 — <what> — <why>
    warnings:
      <counts disagree with the parsed lines / an unparseable finding line /
       a marker comment ignored because its author is not a reviewer>

`--reviewer` is repeatable and, when given, replaces the default login list
entirely (it does not add to it) — pass every login that should count.

`--sha` is compared to a marker's sha with plain string equality only; a
value shorter than 40 hex characters can never match and is never treated
as a prefix.

--respond FILE posts FILE's content as this skill's response comment,
prefixed with:

    <!-- claude-review-response v1 sha=<40-hex sha the findings were made against> -->

sha defaults to the PR head, same as read mode. On success it prints
`responded: <sha>` and exits 0.

Exit codes:
    0 = REVIEWED (read mode), or the response comment was posted (--respond)
    2 = GitHub could not be read (read mode: prints `review: ERROR` and a
        `detail:` line instead of the digest; --respond: prints an `error:`
        line to stderr) — also used for a missing/empty --respond file
    3 = NOT_REVIEWED (read mode only)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_REVIEWER = "claude[bot]"

SHA_RE = re.compile(r"[0-9a-f]{40}")

MARKER_RE = re.compile(
    r"^<!-- claude-review v1 sha=(?P<sha>[0-9a-f]{40}) "
    r"must=(?P<must>\d+) should=(?P<should>\d+) nit=(?P<nit>\d+) "
    r"pre=(?P<pre>\d+) -->$"
)

# The separator between the location, "what", and "why" segments is meant to
# be an em dash, but the review prompt is a model's own output and sometimes
# writes "-" or "--" instead — tolerate all three rather than dropping the
# line to warnings over a cosmetic slip.
_SEP = r"(?:—|--|-)"

FINDING_RE = re.compile(
    r"^- \[(?P<sev>must-fix|should-fix|nit|pre-existing)\] "
    r"R(?P<num>\d+) `(?P<loc>[^`]+)` "
    rf"{_SEP} (?P<what>.+?) "
    rf"{_SEP} (?P<why>.+)$"
)

SEVERITY_TO_COUNT_KEY = {
    "must-fix": "must",
    "should-fix": "should",
    "nit": "nit",
    "pre-existing": "pre",
}
COUNT_KEYS = ("must", "should", "nit", "pre")


def gh_call(args: list[str]) -> tuple[bool, str, str]:
    """Run `gh <args>`. Returns (ok, stdout, error-detail-one-line)."""
    try:
        proc = subprocess.run(["gh", *args], capture_output=True, text=True,
                              timeout=120)
    except FileNotFoundError:
        return False, "", "gh CLI not found"
    except subprocess.TimeoutExpired:
        return False, "", f"gh {' '.join(args)} timed out"
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().replace("\n", " | ")
        return False, proc.stdout or "", f"gh {' '.join(args)} failed: {detail}"
    return True, proc.stdout or "", ""


def resolve_repo(explicit: str | None) -> tuple[bool, str, str]:
    if explicit:
        return True, explicit, ""
    ok, out, err = gh_call(["repo", "view", "--json", "nameWithOwner",
                            "-q", ".nameWithOwner"])
    if not ok:
        return False, "", err
    repo = out.strip()
    if not repo:
        return False, "", "gh repo view returned no repo"
    return True, repo, ""


def resolve_pr_head_sha(pr: int, repo: str) -> tuple[bool, str, str]:
    ok, out, err = gh_call(["pr", "view", str(pr), "--repo", repo,
                            "--json", "headRefOid", "-q", ".headRefOid"])
    if not ok:
        return False, "", err
    sha = out.strip()
    if not sha:
        return False, "", "gh pr view returned no head sha"
    return True, sha, ""


def parse_finding_lines(body: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse the finding lines under a summary's marker line.

    A line that starts with `- [` and fails to parse is never silently
    dropped — it goes to the returned warnings, marked unparsed. Any other
    line (free prose, headings, "No issues found.") is ignored.
    """
    findings: list[dict[str, Any]] = []
    warnings: list[str] = []
    for raw in body.splitlines()[1:]:
        line = raw.strip()
        if not line.startswith("- ["):
            continue
        m = FINDING_RE.match(line)
        if not m:
            warnings.append(f"unparsed finding line: {line}")
            continue
        findings.append({
            "n": int(m.group("num")),
            "severity": m.group("sev"),
            "loc": m.group("loc"),
            "what": m.group("what"),
            "why": m.group("why"),
        })
    return findings, warnings


def counts_from_findings(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {k: 0 for k in COUNT_KEYS}
    for f in findings:
        counts[SEVERITY_TO_COUNT_KEY[f["severity"]]] += 1
    return counts


def format_counts(counts: dict[str, int]) -> str:
    return " ".join(f"{k}={counts[k]}" for k in COUNT_KEYS)


def do_review(pr: int, repo: str, sha: str | None,
              reviewer_logins: list[str]) -> int:
    target_sha = sha
    if not target_sha:
        ok, target_sha, err = resolve_pr_head_sha(pr, repo)
        if not ok:
            print("review: ERROR")
            print(f"detail: {err}")
            return 2

    # One JSON object per line: `--paginate` alone prints each page's array
    # back to back (`[...][...]`), which is not one JSON document once a PR
    # has more than a page of comments.
    ok, out, err = gh_call(["api", f"repos/{repo}/issues/{pr}/comments",
                            "--paginate", "--jq", ".[] | @json"])
    if not ok:
        print("review: ERROR")
        print(f"detail: {err}")
        return 2
    comments = []
    for line in (out or "").splitlines():
        if not line.strip():
            continue
        try:
            comments.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print("review: ERROR")
            print(f"detail: could not parse a gh api comment line as JSON: {exc}")
            return 2

    accepted: list[dict[str, Any]] = []
    warnings: list[str] = []
    for c in comments:
        if not isinstance(c, dict):
            continue
        body = c.get("body") or ""
        lines = body.splitlines()
        first = lines[0].strip() if lines else ""
        m = MARKER_RE.match(first)
        if not m:
            continue
        user = c.get("user") or {}
        login = user.get("login") or "<unknown>"
        utype = user.get("type") or ""
        if utype == "Bot" and login in reviewer_logins:
            accepted.append({
                "sha": m.group("sha"),
                "must": int(m.group("must")), "should": int(m.group("should")),
                "nit": int(m.group("nit")), "pre": int(m.group("pre")),
                "body": body,
            })
        else:
            warnings.append(
                f"ignored review marker from non-reviewer {login} "
                f"(type={utype or 'unknown'}, sha={m.group('sha')})")

    round_n = len({a["sha"] for a in accepted})

    # Plain equality only: a --sha shorter than 40 hex characters can never
    # equal a marker's sha, and that is deliberate — never prefix-match.
    matches = [a for a in accepted if a["sha"] == target_sha]
    winner = matches[-1] if matches else None  # last one wins

    findings: list[dict[str, Any]] = []
    counts = {k: 0 for k in COUNT_KEYS}
    if winner is not None:
        findings, parse_warnings = parse_finding_lines(winner["body"])
        warnings.extend(parse_warnings)
        parsed_counts = counts_from_findings(findings)
        marker_counts = {k: winner[k] for k in COUNT_KEYS}
        if marker_counts != parsed_counts:
            warnings.append(
                f"marker counts ({format_counts(marker_counts)}) disagree "
                f"with parsed findings ({format_counts(parsed_counts)}); "
                "using the parsed counts")
        counts = parsed_counts

    lines_out = [
        f"review: {'REVIEWED' if winner is not None else 'NOT_REVIEWED'}",
        f"sha: {target_sha}",
        f"round: {round_n}",
        f"counts: {format_counts(counts)}",
        "findings:",
    ]
    for f in findings:
        lines_out.append(
            f"  R{f['n']} {f['severity']} {f['loc']} — {f['what']} — {f['why']}")
    lines_out.append("warnings:")
    for w in warnings:
        lines_out.append(f"  {w}")
    print("\n".join(lines_out))
    return 0 if winner is not None else 3


def do_respond(pr: int, repo: str, sha: str | None, respond_file: Path) -> int:
    if not respond_file.is_file():
        print(f"error: --respond file not found: {respond_file}", file=sys.stderr)
        return 2
    content = respond_file.read_text(encoding="utf-8")
    if not content.strip():
        print(f"error: --respond file is empty: {respond_file}", file=sys.stderr)
        return 2

    target_sha = sha
    if not target_sha:
        ok, target_sha, err = resolve_pr_head_sha(pr, repo)
        if not ok:
            print(f"error: cannot resolve PR head sha: {err}", file=sys.stderr)
            return 2

    body = f"<!-- claude-review-response v1 sha={target_sha} -->\n" + content

    tmp_fd, tmp_name = tempfile.mkstemp(prefix="claude-review-response-",
                                        suffix=".md")
    tmp_path = Path(tmp_name)
    try:
        with open(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(body)
        ok, _out, err = gh_call(["pr", "comment", str(pr), "--repo", repo,
                                 "--body-file", str(tmp_path)])
        if not ok:
            print(f"error: gh pr comment failed: {err}", file=sys.stderr)
            return 2
    finally:
        tmp_path.unlink(missing_ok=True)

    print(f"responded: {target_sha}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pr", type=int, help="pull request number")
    p.add_argument("--repo", metavar="OWNER/NAME",
                   help="target repo; defaults to `gh repo view` in cwd")
    p.add_argument("--sha", metavar="SHA",
                   help="40-hex sha to look for (read mode) or to stamp the "
                        "response marker with (--respond); default: the PR head")
    p.add_argument("--reviewer", action="append", metavar="LOGIN",
                   help="bot login whose marker counts as a real review "
                        "(repeatable; replaces, does not add to, the "
                        f"default of {DEFAULT_REVIEWER!r})")
    p.add_argument("--respond", metavar="FILE", type=Path,
                   help="post FILE's content as this skill's response "
                        "comment, prefixed with the response marker")
    args = p.parse_args(argv)

    reviewer_logins = args.reviewer if args.reviewer else [DEFAULT_REVIEWER]

    if args.sha is not None and not SHA_RE.fullmatch(args.sha):
        detail = f"--sha must be a full 40-hex commit sha, got {args.sha!r}"
        if args.respond:
            print(f"error: {detail}", file=sys.stderr)
        else:
            print("review: ERROR")
            print(f"detail: {detail}")
        return 2

    ok, repo, err = resolve_repo(args.repo)
    if not ok:
        if args.respond:
            print(f"error: cannot resolve repo: {err}", file=sys.stderr)
        else:
            print("review: ERROR")
            print(f"detail: cannot resolve repo: {err}")
        return 2

    if args.respond:
        return do_respond(args.pr, repo, args.sha, args.respond)
    return do_review(args.pr, repo, args.sha, reviewer_logins)


if __name__ == "__main__":
    raise SystemExit(main())
