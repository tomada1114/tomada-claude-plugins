"""_fakegh.py — Shared helper: install a fake `gh` on PATH for scripts/ tests.

Adapted from shipping-issues/scripts/tests/_fakegh.py for this skill (copied,
not imported — skills do not share code across their own scripts/ trees).
One addition beyond the original: a response may be a *list* of stdout
strings instead of one string, consumed in call order — create_issues.py
issues several structurally-identical `gh api .../issues --method POST`
calls (tracking, then each issue) that must return different `number`/`id`
values, which a single canned response per argv-prefix cannot express.

create_issues.py shells out to the real `gh` CLI. Tests never touch a real
GitHub repo, so this writes a stand-in `gh` executable that answers from a
small routing table instead: each entry matches an argv *prefix* (the
longest matching prefix wins, so a generic ("api",) entry and a specific
("api", "repos/acme/widgets/issues") entry can both be registered and the
more specific one wins when both apply) and returns a fixed (or queued)
stdout/exit code.

Usage (inside a test) — prefer running the script's main() in-process, via
`fake.env`, over a real subprocess: coverage instrumentation only sees code
executed in this interpreter, not in a spawned child:

    from _fakegh import FakeGh

    def test_something(self):
        with FakeGh({
            ("label", "create"): "",
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                json.dumps({"number": 10, "id": 900, "html_url": "..."}),
                json.dumps({"number": 11, "id": 901, "html_url": "..."}),
            ],
        }) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                rc = create_issues.main([...])
            ...
            fake.calls  # list[list[str]] of every argv `gh` was invoked with
"""
from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path

_RUNNER = '''#!/usr/bin/env python3
import json, sys, os
config = json.loads(open(os.environ["FAKE_GH_CONFIG"], encoding="utf-8").read())
argv = sys.argv[1:]
with open(os.environ["FAKE_GH_CALLS"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(argv) + "\\n")
best = None
best_i = None
for i, entry in enumerate(config):
    prefix = entry["prefix"]
    if argv[: len(prefix)] == prefix:
        if best is None or len(prefix) > len(best["prefix"]):
            best = entry
            best_i = i
if best is None:
    print("[]")
    sys.exit(0)

# Every field (stdout/stderr/exit) may be a plain value (used for every call
# that matches this prefix) or a list (one entry per call, in order, the
# last repeating once exhausted) — the same counter drives all three so a
# fixture can make call N of a repeated prefix behave differently from call
# N+1 (e.g. the first of several issue creates succeeds, the second fails).
counts_path = os.environ["FAKE_GH_COUNTS"]
counts = json.loads(open(counts_path, encoding="utf-8").read()) if os.path.exists(counts_path) else {}
key = str(best_i)
seen = counts.get(key, 0)
counts[key] = seen + 1
with open(counts_path, "w", encoding="utf-8") as fh:
    fh.write(json.dumps(counts))


def pick(value, default):
    if value is None:
        return default
    if isinstance(value, list):
        return value[seen] if seen < len(value) else value[-1]
    return value


sys.stderr.write(pick(best.get("stderr"), ""))
sys.stdout.write(pick(best.get("stdout"), "[]"))
sys.exit(pick(best.get("exit"), 0))
'''


class FakeGh:
    """Context manager: installs a fake `gh` and yields an object exposing
    `.env` (subprocess env with PATH pointed at the fake) and `.calls`
    (populated after each subprocess call reads the shared log file).

    A value in `responses`, `exits` or `stderrs` is either a single value
    (used for every matching call) or a list (one entry per call, in order,
    sharing one counter per prefix; the last entry repeats once exhausted) —
    e.g. `exits={prefix: [0, 1]}` makes the first call to that prefix
    succeed and the second fail, so a plan with two issues can exercise a
    failure on the second `gh api .../issues --method POST` without the
    first one failing too."""

    def __init__(self, responses: dict[tuple[str, ...], str | list[str]] | None = None,
                 *, exits: dict[tuple[str, ...], int | list[int]] | None = None,
                 stderrs: dict[tuple[str, ...], str | list[str]] | None = None):
        self._responses = responses or {}
        self._exits = exits or {}
        self._stderrs = stderrs or {}
        self._tmpdir: tempfile.TemporaryDirectory | None = None
        self.env: dict[str, str] = {}

    def __enter__(self) -> "FakeGh":
        self._tmpdir = tempfile.TemporaryDirectory()
        bin_dir = Path(self._tmpdir.name) / "bin"
        bin_dir.mkdir()
        gh_path = bin_dir / "gh"
        gh_path.write_text(_RUNNER, encoding="utf-8")
        gh_path.chmod(gh_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        # Union the three dicts' keys: a prefix named only in `exits` or
        # `stderrs` (a failure fixture that doesn't care what stdout would
        # have been) still needs a config entry, or its exit/stderr override
        # would silently never apply.
        all_prefixes = dict.fromkeys((*self._responses, *self._exits, *self._stderrs))
        config = [
            {"prefix": list(prefix), "stdout": self._responses.get(prefix, ""),
             "exit": self._exits.get(prefix, 0),
             "stderr": self._stderrs.get(prefix, "")}
            for prefix in all_prefixes
        ]
        config_path = Path(self._tmpdir.name) / "gh_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        calls_path = Path(self._tmpdir.name) / "gh_calls.jsonl"
        calls_path.write_text("", encoding="utf-8")
        counts_path = Path(self._tmpdir.name) / "gh_counts.json"

        self.env = dict(os.environ)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}{self.env.get('PATH', '')}"
        self.env["FAKE_GH_CONFIG"] = str(config_path)
        self.env["FAKE_GH_CALLS"] = str(calls_path)
        self.env["FAKE_GH_COUNTS"] = str(counts_path)
        self._calls_path = calls_path
        return self

    def __exit__(self, *exc_info) -> None:
        if self._tmpdir is not None:
            self._tmpdir.cleanup()
            self._tmpdir = None

    @property
    def calls(self) -> list[list[str]]:
        if not self._calls_path.exists():
            return []
        lines = self._calls_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(ln) for ln in lines if ln.strip()]
