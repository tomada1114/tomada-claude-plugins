#!/usr/bin/env python3
"""Tests for cleanup_run.sh. Stdlib-only (unittest).

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


SCRIPT = Path(__file__).resolve().parent.parent / "cleanup_run.sh"


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


def add_local_origin(repo, parent):
    origin = parent / "origin.git"
    git(parent, "init", "--bare", "-q", str(origin))
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-q", "-u", "origin", "main")
    git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")


def run_script(args, repo, responses, *, exits=None, stderrs=None):
    with FakeGh(responses, exits=exits, stderrs=stderrs) as fake:
        proc = subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=repo,
            env=fake.env,
            text=True,
            capture_output=True,
        )
        calls = list(fake.calls)
    return proc, calls


MERGED_LIST = (
    "pr", "list", "--state", "merged", "--limit", "200", "--json",
    "headRefName", "-q", ".[].headRefName",
)
OPEN_LIST = (
    "pr", "list", "--state", "open", "--limit", "200", "--json",
    "headRefName", "-q", ".[].headRefName",
)


class CleanupRunTest(unittest.TestCase):
    def test_unknown_flag_is_usage_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            make_repo(repo)
            proc, calls = run_script(["--no-such-flag"], repo, {})

        self.assertEqual(proc.returncode, 2)
        self.assertIn("unknown flag: --no-such-flag", proc.stderr)
        self.assertEqual(calls, [])

    def test_removes_clean_agent_worktree_and_internal_branch(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            make_repo(repo)
            add_local_origin(repo, Path(td))
            worktree = repo / ".claude" / "worktrees" / "agent-one"
            worktree.parent.mkdir(parents=True)
            git(repo, "worktree", "add", "-q", "-b", "worktree-agent-one",
                str(worktree), "HEAD")
            reported_worktree = worktree.resolve()

            proc, calls = run_script(
                [], repo, {MERGED_LIST: "", OPEN_LIST: ""}
            )

            branches = git(repo, "branch", "--format=%(refname:short)").stdout.splitlines()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(f"removed worktree: {reported_worktree}\n", proc.stdout)
        self.assertIn("cleanup: done\n", proc.stdout)
        self.assertFalse(worktree.exists())
        self.assertNotIn("worktree-agent-one", branches)
        self.assertEqual(calls, [list(MERGED_LIST), list(OPEN_LIST)])

    def test_gh_lookup_failure_stops_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            make_repo(repo)
            add_local_origin(repo, Path(td))
            worktree = repo / ".claude" / "worktrees" / "agent-one"
            worktree.parent.mkdir(parents=True)
            git(repo, "worktree", "add", "-q", "-b", "worktree-agent-one",
                str(worktree), "HEAD")

            proc, calls = run_script(
                [], repo, {MERGED_LIST: "", OPEN_LIST: ""}, exits={MERGED_LIST: 1}
            )

            self.assertTrue(worktree.exists())

        self.assertEqual(proc.returncode, 1)
        self.assertEqual(calls, [list(MERGED_LIST)])
        self.assertNotIn("cleanup: done", proc.stdout)


if __name__ == "__main__":
    unittest.main()
