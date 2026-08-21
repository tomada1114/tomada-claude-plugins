"""_fakegh.py — Shared helper: install a fake `gh` on PATH for scripts/ tests.

The scripts under test shell out to the real `gh` CLI. Tests never touch a
real GitHub repo, so this writes a stand-in `gh` executable that answers from
a small routing table instead: each entry matches an argv *prefix* (the
longest matching prefix wins, so "issue list" and "issue list --state open"
can both be registered and the more specific one wins when both apply) and
returns a fixed stdout/exit code.

Usage (inside a test) — prefer running the script's main() in-process, via
`fake.env`, over a real subprocess: coverage instrumentation only sees code
executed in this interpreter, not in a spawned child:

    from _fakegh import FakeGh

    def test_something(self):
        with FakeGh({
            ("issue", "list"): json.dumps([...]),
            ("pr", "list"): "[]",
            ("label", "list"): json.dumps([{"name": "priority: P0"}]),
        }) as fake:
            with patch.dict("os.environ", fake.env, clear=False), \
                    patch.object(sys, "argv", ["script.py", "--json"]):
                rc = some_module.main()
            ...
            fake.calls  # list[list[str]] of every argv `gh` was invoked with

A real subprocess.run([sys.executable, str(SCRIPT), ...], env=fake.env) still
works when in-process coverage isn't the point (e.g. checking the script's
final exit code and stdout/stderr framing as an external caller would see it).
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from pathlib import Path

_RUNNER = '''#!/usr/bin/env python3
import json, sys, os
config = json.loads(open(os.environ["FAKE_GH_CONFIG"], encoding="utf-8").read())
argv = sys.argv[1:]
with open(os.environ["FAKE_GH_CALLS"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(argv) + "\\n")
best = None
for entry in config:
    prefix = entry["prefix"]
    if argv[: len(prefix)] == prefix:
        if best is None or len(prefix) > len(best["prefix"]):
            best = entry
if best is None:
    print("[]")
    sys.exit(0)
sys.stderr.write(best.get("stderr", ""))
sys.stdout.write(best.get("stdout", "[]"))
sys.exit(best.get("exit", 0))
'''


class FakeGh:
    """Context manager: installs a fake `gh` and yields an object exposing
    `.env` (subprocess env with PATH pointed at the fake) and `.calls`
    (populated after each subprocess call reads the shared log file)."""

    def __init__(self, responses: dict[tuple[str, ...], str] | None = None,
                 *, exits: dict[tuple[str, ...], int] | None = None,
                 stderrs: dict[tuple[str, ...], str] | None = None):
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

        config = [
            {"prefix": list(prefix), "stdout": stdout,
             "exit": self._exits.get(prefix, 0),
             "stderr": self._stderrs.get(prefix, "")}
            for prefix, stdout in self._responses.items()
        ]
        config_path = Path(self._tmpdir.name) / "gh_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        calls_path = Path(self._tmpdir.name) / "gh_calls.jsonl"
        calls_path.write_text("", encoding="utf-8")

        self.env = dict(os.environ)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}{self.env.get('PATH', '')}"
        self.env["FAKE_GH_CONFIG"] = str(config_path)
        self.env["FAKE_GH_CALLS"] = str(calls_path)
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
