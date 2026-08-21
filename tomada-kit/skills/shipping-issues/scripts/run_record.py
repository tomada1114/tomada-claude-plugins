#!/usr/bin/env python3
"""run_record.py — Append one event to the shipping-issues run record.

The run record is a plain, append-only log of what a run actually did:
selection, labels written, PRs opened, review passes, CI verdicts, merges,
filed follow-ups, cleanup. Nothing here is ever rewritten or deleted, so a run
stopped mid-way keeps whatever landed before it stopped — the whole point of
calling this once per event, right after the event happens, instead of
composing the record from memory at the end.

The record lives outside the project, at:
    ${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}
      /shipping-issues/<owner>__<repo>/run.md

Usage:
    run_record.py --event EVENT [--repo OWNER/NAME] [--field k=v ...]
                  [--body-file FILE] [--json]

EVENT is one of: run-start, selection, labels, pr-created, review, ci, merged,
followup, cleanup, blocked, note.

--repo defaults to `gh repo view --json nameWithOwner` in cwd; pass it
explicitly whenever cwd may not be the repo being shipped.

--field k=v may repeat; each becomes "k=v" on the appended line, in the order
given. --body-file appends its contents as a fenced block under the event
line — the shape selection uses for the rubric's evidence block.

`run-start` additionally opens a `## run <UTC timestamp>` heading before its
line, so a run.md reads as a sequence of runs rather than one long list.

Exit codes:
    0 = appended
    1 = cannot resolve repo, or cannot write the record file
    2 = usage error (unknown event, malformed --field, missing body file)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_STATE_NAME = "shipping-issues"
REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")

EVENTS = (
    "run-start", "selection", "labels", "pr-created", "review", "ci",
    "merged", "followup", "cleanup", "blocked", "note",
)


def state_dir() -> Path:
    """Root of the shared agent-skill state directory (env override honoured)."""
    env = os.environ.get("AGENT_SKILL_STATE_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".local" / "state" / "agent-skills"


def record_path(repo: str) -> Path:
    # repo is validated against REPO_RE by main() before this runs, so a
    # "/"-for-"__" swap cannot escape SKILL_STATE_NAME via ".." or a stray
    # extra slash.
    owner_repo = repo.replace("/", "__")
    return state_dir() / SKILL_STATE_NAME / owner_repo / "run.md"


def resolve_repo(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    proc = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True, text=True, timeout=120,
    )
    repo = (proc.stdout or "").strip()
    return repo or None


def parse_fields(pairs: list[str]) -> list[tuple[str, str]]:
    parsed = []
    for pair in pairs:
        if "=" not in pair:
            print(f"error: --field must be k=v, got: {pair}", file=sys.stderr)
            raise SystemExit(2)
        key, _, value = pair.partition("=")
        key = key.strip()
        if not key:
            print(f"error: --field key is empty: {pair}", file=sys.stderr)
            raise SystemExit(2)
        parsed.append((key, value.strip()))
    return parsed


def _fence_for(body: str) -> str:
    """A backtick fence longer than any backtick run already in body, so a
    selection block or FOLLOW-UPS text that itself quotes a ``` code block
    cannot prematurely close ours (same rule CommonMark uses)."""
    longest = max((len(run) for run in re.findall(r"`+", body)), default=0)
    return "`" * max(3, longest + 1)


def format_entry(event: str, fields: list[tuple[str, str]], body: str | None,
                  now: datetime) -> str:
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"- {stamp} {event}"
    if fields:
        line += " — " + " ".join(f"{k}={v}" for k, v in fields)
    line += "\n"
    if body is not None:
        fence = _fence_for(body)
        line += f"\n{fence}\n" + body.rstrip("\n") + f"\n{fence}\n"
    if event == "run-start":
        line = f"## run {stamp}\n\n" + line
    return line


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--event", required=True, choices=EVENTS)
    p.add_argument("--repo", metavar="OWNER/NAME",
                    help="target repo; defaults to the one cwd resolves to")
    p.add_argument("--field", action="append", default=[], metavar="k=v",
                    help="one k=v pair, repeatable, appended in order given")
    p.add_argument("--body-file", type=Path,
                    help="path to a text file appended as a fenced block "
                         "(e.g. the rubric-shaped selection block)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args(argv)

    fields = parse_fields(args.field)

    body = None
    if args.body_file is not None:
        if not args.body_file.is_file():
            print(f"error: --body-file not found: {args.body_file}", file=sys.stderr)
            return 2
        body = args.body_file.read_text(encoding="utf-8")

    repo = resolve_repo(args.repo)
    if not repo:
        target = args.repo or "the current directory"
        print(f"error: cannot resolve {target} — run inside the repo or pass "
              "--repo OWNER/NAME", file=sys.stderr)
        return 1
    if not REPO_RE.match(repo):
        print(f"error: --repo must look like OWNER/NAME, got: {repo!r}", file=sys.stderr)
        return 2

    path = record_path(repo)
    entry = format_entry(args.event, fields, body, datetime.now(timezone.utc))

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(entry)
    except OSError as exc:
        print(f"error: cannot write {path}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"path": str(path), "bytes_appended": len(entry),
                          "event": args.event, "repo": repo}, ensure_ascii=False))
    else:
        print(f"recorded: {args.event} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
