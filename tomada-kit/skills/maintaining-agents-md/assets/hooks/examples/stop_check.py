#!/usr/bin/env python3
"""stop_check.py — run the project's gate before the turn is allowed to end.

Wire on Stop. Exit 2 sends stderr back to the model, which then fixes what the
gate reported. Exits 0 when this hook already ran once in the turn, when the
tree has no change a gate covers, when the gate command is not installed, or
when the root is not a git repository — the gate is a safety net, not a wall.

Tune GATES per project; the logic below it is generic.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from hook_payload import load_event, project_root

# (suffixes that trigger the gate, command run from the project root)
GATES = (
    ((".py",), ["ruff", "check", "."]),
    ((".ts", ".tsx"), ["npx", "--no-install", "tsc", "--noEmit"]),
)
TIMEOUT = 300


def changed_suffixes(root) -> set[str]:
    if not shutil.which("git"):
        return set()
    try:
        done = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "status", "--porcelain"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if done.returncode != 0:
        return set()
    suffixes = set()
    for line in done.stdout.splitlines():
        name = line[3:].split(" -> ")[-1].strip().strip('"')
        if "." in name:
            suffixes.add("." + name.rsplit(".", 1)[-1])
    return suffixes


def main() -> int:
    event = load_event()
    if event.name != "Stop" or event.stop_hook_active:
        return 0
    root = project_root()
    suffixes = changed_suffixes(root)
    if not suffixes:
        return 0
    failures = []
    for triggers, command in GATES:
        if not suffixes.intersection(triggers) or not shutil.which(command[0]):
            continue
        try:
            done = subprocess.run(  # noqa: S603
                command,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"stop_check: {command[0]} did not run: {exc}", file=sys.stderr)
            continue
        if done.returncode != 0:
            output = f"{done.stdout.strip()}\n{done.stderr.strip()}".strip()
            failures.append(f"$ {' '.join(command)}\n{output}")
    if failures:
        print(
            "stop_check: fix these before finishing:\n" + "\n\n".join(failures),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
