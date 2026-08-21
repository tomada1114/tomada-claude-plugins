#!/usr/bin/env python3
"""format.py — format the files the last tool call touched.

Wire on PostToolUse with matcher `Edit|Write` (that matcher also fires for
`apply_patch`). Always exits 0: a formatter that is missing or unhappy must
never block the session. A formatter that is not installed is skipped.

Tune FORMATTERS per project; the logic below it is generic.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from hook_payload import load_event, project_root

# (suffixes, command). The file path is appended to the command.
FORMATTERS = (
    ((".py",), ["ruff", "format"]),
    (
        (".ts", ".tsx", ".js", ".jsx", ".mjs"),
        ["npx", "--no-install", "prettier", "--write"],
    ),
    ((".rs",), ["rustfmt"]),
)
TIMEOUT = 60


def formatter_for(suffix: str) -> list[str] | None:
    for suffixes, command in FORMATTERS:
        if suffix in suffixes and shutil.which(command[0]):
            return command
    return None


def main() -> int:
    event = load_event()
    if not event.files:
        return 0
    root = project_root()
    for path in event.files:
        if not path.is_file():
            continue
        command = formatter_for(path.suffix)
        if command is None:
            continue
        try:
            subprocess.run(  # noqa: S603
                [*command, str(path)],
                cwd=root,
                timeout=TIMEOUT,
                capture_output=True,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            print(
                f"format: {command[0]} did not run on {path.name}: {exc}",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
