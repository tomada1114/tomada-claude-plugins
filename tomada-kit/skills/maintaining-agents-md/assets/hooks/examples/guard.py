#!/usr/bin/env python3
"""guard.py — refuse edits and shell commands that must not happen.

Wire on PreToolUse with matcher `Edit|Write|Bash` (that matcher also fires for
`apply_patch`). Exit 2 blocks the call and shows stderr to the model; exit 0
allows it.

Tune the four constants below per project; the logic below them is generic.
"""

from __future__ import annotations

import fnmatch
import re
import shlex
import sys
from pathlib import Path

from hook_payload import load_event, project_root, relative_to_root

# Paths that no agent-driven edit may touch, relative to the project root.
PROTECTED = ("uv.lock", ".env*", "secrets/**")
# Shell patterns that bypass a review gate. (regex, why it is refused)
FORBIDDEN_COMMANDS = (
    (
        r"\bgit\s+commit\b(?=.*(?:--no-verify|\s-n\b))",
        "git commit --no-verify skips the pre-commit gate",
    ),
    (
        r"\bgit\s+push\b(?=.*(?:--force\b|\s-f\b))(?!.*--force-with-lease)",
        "plain force-push can drop other people's commits; use --force-with-lease",
    ),
    (
        r"\bgh\s+pr\s+merge\b(?=.*--admin)",
        "gh pr merge --admin merges past required checks",
    ),
)
# Shell commands whose arguments are write targets.
WRITE_COMMANDS = {"cp", "mv", "tee", "rm", "install", "truncate", "dd", "touch"}
SEGMENT_RE = re.compile(r"&&|\|\||;|\|")


def is_protected(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    for pattern in PROTECTED:
        if pattern.endswith("/**"):
            if rel == pattern[:-3] or rel.startswith(pattern[:-2]):
                return True
        elif "/" in pattern:
            if fnmatch.fnmatch(rel, pattern):
                return True
        elif fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern):
            return True
    return False


def write_targets(command: str) -> list[str]:
    """Paths a shell command would write: redirects, and the arguments of a
    write command."""
    targets: list[str] = []
    for segment in SEGMENT_RE.split(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        if not tokens:
            continue
        head = tokens[0].rsplit("/", 1)[-1]
        takes_args = head in WRITE_COMMANDS or (head == "sed" and "-i" in tokens)
        expect_redirect = False
        for token in tokens[1:]:
            if expect_redirect:
                targets.append(token)
                expect_redirect = False
            elif token in (">", ">>", ">|"):
                expect_redirect = True
            elif token.startswith(">"):
                targets.append(token.lstrip(">"))
            elif takes_args and not token.startswith("-"):
                targets.append(token)
    return [t for t in targets if t]


def refuse(reason: str) -> None:
    print(f"guard: {reason}", file=sys.stderr)
    raise SystemExit(2)


def main() -> int:
    event = load_event()
    if event.name != "PreToolUse":
        return 0
    root = project_root()

    for path in event.files:
        rel = relative_to_root(path, event, root)
        if is_protected(rel):
            refuse(f"{rel} is protected — edit it yourself or ask the user")

    if event.command:
        for pattern, why in FORBIDDEN_COMMANDS:
            if re.search(pattern, event.command):
                refuse(why)
        for target in write_targets(event.command):
            candidate = Path(target)
            if not candidate.is_absolute():
                candidate = event.cwd / candidate
            rel = relative_to_root(candidate, event, root)
            if is_protected(rel):
                refuse(f"the command writes to {rel}, which is protected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
