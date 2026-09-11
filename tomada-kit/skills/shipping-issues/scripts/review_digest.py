#!/usr/bin/env python3
"""review_digest.py — Find a CI review of a PR's head and print it for the model to read.

references/ci-review.md is the convention this script implements: what the
review job's summary comment looks like, what this skill's response comment
looks like, and why the summary's marker is what tells "reviewed, found
nothing" apart from "never ran" (the review check is green either way).

This script decides only what a script can decide exactly: whether the
reviewer bot summarized this head commit, how many distinct heads it has
summarized (the round), and which comments are the reviewer's at all. It does
NOT parse findings. The summary and the inline comments are written by a model
and read by one: the caller reads them verbatim and decides what each finding
is and how severe it is. A script that parsed them would turn every formatting
slip into a silently dropped finding — the failure this design removes.

A summary is a comment by the reviewer bot containing, on one line, the marker
`claude-review v<n>` and `sha=<40-hex>` — tolerant of spacing, case, and
position in the comment. The response marker `claude-review-response` never
counts as one.

Only comments from a **bot** account whose login is in --reviewer (default
claude[bot]) are trusted — the repo is public-facing, so anyone can post a
comment carrying the marker, and a forged "no findings" would otherwise wave
a pull request through. A marker from anyone else is reported under
`warnings:` with its author's login, never silently accepted.

Usage:
    review_digest.py <pr> [--repo OWNER/NAME] [--sha SHA]
                     [--reviewer LOGIN ...]
    review_digest.py <pr> --respond FILE [--repo OWNER/NAME] [--sha SHA]

Read mode prints:

    review: REVIEWED | NOT_REVIEWED
    sha: <sha looked for, default the PR head>
    round: <n distinct head shas the reviewer has summarized on this PR>
    declared: <the counts the marker line states, e.g. must=0 should=1, or none>
    summary:
      | <the summary comment, verbatim, one line per line>
    inline:
      - <path>:<line>
        | <an inline comment by the reviewer on this sha, verbatim>
    warnings:
      <markers ignored because their author is not a reviewer / inline
       comments that could not be read>

`declared:` is the reviewer's own tally, printed for reference only — read the
findings themselves; a tally and its list can disagree.

`--reviewer` is repeatable and, when given, replaces the default login list
entirely (it does not add to it) — pass every login that should count.

`--sha` is compared to a marker's sha by exact (case-insensitive) equality; a
value shorter than 40 hex characters is rejected rather than prefix-matched.

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

# `claude-review v1`, followed on the same line by `sha=<40 hex>`. The negative
# lookahead keeps this skill's own `claude-review-response` marker out.
MARKER_LINE_RE = re.compile(r"claude-review(?!-)\s+v\d+\b(?P<rest>[^\n]*)",
                            re.IGNORECASE)
MARKER_SHA_RE = re.compile(r"\bsha\s*[=:]\s*(?P<sha>[0-9a-fA-F]{40})\b")
DECLARED_RE = re.compile(r"\b(must|should|nit|pre)\s*=\s*(\d+)", re.IGNORECASE)


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


def gh_json_lines(path: str) -> tuple[bool, list[Any], str]:
    """Every item of a paginated list endpoint, one JSON object per line:
    `--paginate` alone prints each page's array back to back (`[...][...]`),
    which is not one JSON document once there is more than a page."""
    ok, out, err = gh_call(["api", path, "--paginate", "--jq", ".[] | @json"])
    if not ok:
        return False, [], err
    items = []
    for line in (out or "").splitlines():
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as exc:
            return False, [], f"could not parse a gh api line as JSON: {exc}"
    return True, items, ""


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


def find_marker(body: str) -> tuple[str, str] | None:
    """(sha, marker line) of the first line naming a review and a sha, or None."""
    for line in body.splitlines():
        m = MARKER_LINE_RE.search(line)
        if not m:
            continue
        s = MARKER_SHA_RE.search(m.group("rest"))
        if s:
            return s.group("sha").lower(), line.strip()
    return None


def is_reviewer(user: dict[str, Any], reviewer_logins: list[str]) -> bool:
    return user.get("type") == "Bot" and user.get("login") in reviewer_logins


def declared_counts(marker_line: str) -> str:
    found = DECLARED_RE.findall(marker_line)
    return " ".join(f"{k.lower()}={v}" for k, v in found) or "none"


def quoted(text: str, indent: str) -> list[str]:
    return [f"{indent}| {line}".rstrip() for line in text.splitlines()] \
        or [f"{indent}|"]


def do_review(pr: int, repo: str, sha: str | None,
              reviewer_logins: list[str]) -> int:
    target_sha = sha
    if not target_sha:
        ok, target_sha, err = resolve_pr_head_sha(pr, repo)
        if not ok:
            print("review: ERROR")
            print(f"detail: {err}")
            return 2
    target_sha = target_sha.lower()

    ok, comments, err = gh_json_lines(f"repos/{repo}/issues/{pr}/comments")
    if not ok:
        print("review: ERROR")
        print(f"detail: {err}")
        return 2

    accepted: list[dict[str, Any]] = []
    warnings: list[str] = []
    for c in comments:
        if not isinstance(c, dict):
            continue
        found = find_marker(c.get("body") or "")
        if not found:
            continue
        user = c.get("user") or {}
        if is_reviewer(user, reviewer_logins):
            accepted.append({"sha": found[0], "marker": found[1],
                             "body": c.get("body") or ""})
        else:
            warnings.append(
                f"ignored review marker from non-reviewer "
                f"{user.get('login') or '<unknown>'} "
                f"(type={user.get('type') or 'unknown'}, sha={found[0]})")

    round_n = len({a["sha"] for a in accepted})
    matches = [a for a in accepted if a["sha"] == target_sha]
    winner = matches[-1] if matches else None  # last one wins

    inline_lines: list[str] = []
    if winner is not None:
        ok, inline, err = gh_json_lines(f"repos/{repo}/pulls/{pr}/comments")
        if not ok:
            warnings.append(f"inline comments not read: {err}")
        for c in inline if ok else []:
            if not isinstance(c, dict) or c.get("in_reply_to_id"):
                continue
            if not is_reviewer(c.get("user") or {}, reviewer_logins):
                continue
            made_on = (c.get("original_commit_id") or c.get("commit_id") or "").lower()
            if made_on != target_sha:
                continue
            line = c.get("line") or c.get("original_line") or "?"
            inline_lines.append(f"  - {c.get('path') or '?'}:{line}")
            inline_lines.extend(quoted(c.get("body") or "", "    "))

    out = [
        f"review: {'REVIEWED' if winner is not None else 'NOT_REVIEWED'}",
        f"sha: {target_sha}",
        f"round: {round_n}",
    ]
    if winner is not None:
        out.append(f"declared: {declared_counts(winner['marker'])}")
        out.append("summary:")
        out.extend(quoted(winner["body"], "  "))
        out.append("inline:")
        out.extend(inline_lines)
    out.append("warnings:")
    out.extend(f"  {w}" for w in warnings)
    print("\n".join(out))
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
                   help="bot login whose comments count as the review "
                        "(repeatable; replaces, does not add to, the "
                        f"default of {DEFAULT_REVIEWER!r})")
    p.add_argument("--respond", metavar="FILE", type=Path,
                   help="post FILE's content as this skill's response "
                        "comment, prefixed with the response marker")
    args = p.parse_args(argv)

    reviewer_logins = args.reviewer if args.reviewer else [DEFAULT_REVIEWER]

    if args.sha is not None and not SHA_RE.fullmatch(args.sha.lower()):
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
