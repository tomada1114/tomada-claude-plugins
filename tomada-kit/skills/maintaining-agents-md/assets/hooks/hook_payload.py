"""hook_payload.py — one payload shape for hooks that run on either host.

Copy this file into `<project root>/.agents/hooks/` next to the hook scripts
that import it, then:

    from hook_payload import load_event, project_root

    event = load_event()
    if event.name is None:
        raise SystemExit(0)          # unreadable payload: never block on it

It normalises the two dialects a hook payload arrives in. One host sends
`tool_input.file_path` for an edit; the other sends `tool_name: "apply_patch"`
with the patch text in `tool_input.command`. Both end up in `event.files` as
absolute paths.

Detect the host from the payload, never from environment variables: a project
variable that looks host-specific can be inherited from whatever process
started the session.

Standard library only, Python >= 3.10. Imported, never executed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

SHELL_TOOLS = {"bash", "shell"}
READ_TOOLS = {"read"}
EDIT_TOOLS = {"edit", "write", "multiedit", "notebookedit", "apply_patch"}

# `*** Add File: path`, `*** Update File: path`, `*** Delete File: path`,
# `*** Move to: path` — the four lines in a patch that name a file.
PATCH_PATH_RE = re.compile(
    r"^\*\*\*\s+(?:Add File|Update File|Delete File|Move to):\s*(\S.*?)\s*$",
    re.MULTILINE,
)


@dataclass
class Event:
    """A hook payload, host-independent."""

    # hook_event_name. None means "do not trust this payload": it was unreadable,
    # not an object, or carried no event name; callers exit 0 on it.
    name: str | None = None
    # "shell" | "read" | "edit" | "other" | None. A Read call is "read", not
    # "edit", although it also carries file_path; branch on this (or tool_name)
    # when reads and writes must be told apart.
    tool: str | None = None
    tool_name: str | None = None  # the host's own name for the tool
    command: str | None = None  # shell command, only when tool == "shell"
    files: list[Path] = field(default_factory=list)  # absolute
    cwd: Path = field(default_factory=Path.cwd)
    stop_hook_active: bool = False  # this Stop hook already ran once
    raw: dict = field(default_factory=dict)


def _absolute(value: str, base: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    return Path(os.path.normpath(str(path)))


def patch_files(patch: str, base: Path) -> list[Path]:
    """Absolute paths touched by a patch, in the order the patch names them."""
    return [_absolute(m.group(1), base) for m in PATCH_PATH_RE.finditer(patch)]


def from_payload(raw: dict) -> Event:
    """Build an Event from an already-parsed payload."""
    tool_input = raw.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    tool_name = raw.get("tool_name") or None
    key = str(tool_name or "").lower()
    if key in SHELL_TOOLS:
        tool = "shell"
    elif key in READ_TOOLS:
        tool = "read"
    elif key in EDIT_TOOLS or isinstance(tool_input.get("file_path"), str):
        tool = "edit"
    elif tool_name:
        tool = "other"
    else:
        tool = None

    cwd_value = raw.get("cwd")
    cwd = Path(cwd_value) if isinstance(cwd_value, str) and cwd_value else Path.cwd()

    command = tool_input.get("command") if tool == "shell" else None
    if not isinstance(command, str):
        command = None

    files: list[Path] = []
    file_path = tool_input.get("file_path")
    if isinstance(file_path, str) and file_path:
        files.append(_absolute(file_path, cwd))
    if tool == "edit":
        patch = tool_input.get("command")
        if isinstance(patch, str) and "*** " in patch:
            files.extend(patch_files(patch, cwd))
    seen: dict[Path, None] = {}
    for path in files:
        seen.setdefault(path, None)

    return Event(
        name=raw.get("hook_event_name") or None,
        tool=tool,
        tool_name=tool_name,
        command=command,
        files=list(seen),
        cwd=cwd,
        stop_hook_active=bool(raw.get("stop_hook_active")),
        raw=raw,
    )


def load_event(stream: IO[str] | None = None) -> Event:
    """Read one JSON payload (default: stdin). Unreadable input -> name is None."""
    try:
        raw = json.load(stream if stream is not None else sys.stdin)
    except Exception:
        return Event()
    if not isinstance(raw, dict):
        return Event()
    return from_payload(raw)


def project_root(anchor: str | Path = __file__) -> Path:
    """The project root, resolved from this file's own location.

    Walks up from `anchor` to the directory holding `.agents/hooks`. Falls back
    to the git top level of the working directory, then to the working
    directory itself.
    """
    start = Path(anchor).resolve()
    base = start if start.is_dir() else start.parent
    for candidate in (base, *base.parents):
        if (candidate / ".agents" / "hooks").is_dir():
            return candidate
    try:
        done = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "--show-toplevel"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if done.returncode == 0 and done.stdout.strip():
            return Path(done.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return Path.cwd()


def relative_to_root(path: Path, event: Event, root: Path | None = None) -> str:
    """`path` as a slash-separated path relative to the root, for matching."""
    root = root or project_root()
    for base in (root, event.cwd):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.name
