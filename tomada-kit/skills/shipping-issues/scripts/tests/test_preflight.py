#!/usr/bin/env python3
"""Tests for preflight.sh. Stdlib-only (unittest).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the shipping-issues skill directory)
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _fakegh import FakeGh  # noqa: E402


SCRIPT = Path(__file__).resolve().parent.parent / "preflight.sh"


def git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )


def make_repo(path, *, origin=False):
    git(path, "init", "-q")
    git(path, "config", "user.email", "tests@example.invalid")
    git(path, "config", "user.name", "shipping-issues tests")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    git(path, "add", "README.md")
    git(path, "commit", "-qm", "fixture")
    git(path, "branch", "-M", "main")
    if origin:
        git(path, "remote", "add", "origin", "https://example.invalid/acme/widgets.git")


def run_script(args, repo):
    # preflight.sh makes no `gh` calls at all; FakeGh is installed anyway so a
    # regression that adds one back is caught as an unexpected call instead of
    # silently hitting a real `gh` on the test runner's PATH.
    with FakeGh({}) as fake:
        proc = subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=repo,
            env=fake.env,
            text=True,
            capture_output=True,
        )
        calls = list(fake.calls)
    return proc, calls


class PreflightTest(unittest.TestCase):
    def test_ready_repo_reports_ready_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            make_repo(repo, origin=True)
            proc, calls = run_script([], repo)
            reported_root = git(repo, "rev-parse", "--show-toplevel").stdout.strip()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        expected_lines = [
            "git_repo: ok",
            f"repo_root: {reported_root}",
            "origin: https://example.invalid/acme/widgets.git",
            "current_branch: main",
            "working_tree: clean",
            "verdict: READY",
        ]
        for line in expected_lines:
            self.assertIn(f"{line}\n", proc.stdout)
        self.assertEqual(calls, [])

    def test_missing_origin_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            make_repo(repo)
            proc, calls = run_script([], repo)

        self.assertEqual(proc.returncode, 1)
        self.assertIn("origin: MISSING\n", proc.stdout)
        self.assertIn("verdict: BLOCKED\n", proc.stdout)
        self.assertEqual(calls, [])

    def test_not_a_repo_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            proc, calls = run_script([], repo)

        self.assertEqual(proc.returncode, 1)
        self.assertIn("git_repo: NOT_A_REPO\n", proc.stdout)
        self.assertIn("verdict: BLOCKED\n", proc.stdout)
        self.assertEqual(calls, [])

    def test_dirty_tree_warns_but_is_ready(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            make_repo(repo, origin=True)
            (repo / "README.md").write_text("changed\n", encoding="utf-8")
            proc, calls = run_script([], repo)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("working_tree: DIRTY\n", proc.stdout)
        self.assertIn("verdict: READY_WITH_WARNINGS\n", proc.stdout)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
