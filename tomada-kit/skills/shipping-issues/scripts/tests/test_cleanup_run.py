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

    def test_runs_when_origin_head_is_unset(self):
        """A repo with an origin remote but no origin/HEAD ref.

        `git clone` sets origin/HEAD; `git remote add` + fetch does not, so
        plenty of real repos lack it. Under `set -e` with `pipefail` the
        failing symbolic-ref used to take the whole command substitution's
        exit status with it and abort before printing a single line.
        """
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            make_repo(repo)
            add_local_origin(repo, Path(td))
            git(repo, "symbolic-ref", "-d", "refs/remotes/origin/HEAD")
            git(repo, "branch", "feat/1-merged")

            proc, calls = run_script([], repo, {MERGED_LIST: "feat/1-merged", OPEN_LIST: ""})

            branches = git(repo, "branch", "--format=%(refname:short)").stdout.splitlines()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("cleanup: done\n", proc.stdout)
        self.assertNotIn("feat/1-merged", branches)

    def test_removes_merged_and_internal_branches_keeps_unmerged(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            make_repo(repo)
            add_local_origin(repo, Path(td))
            git(repo, "branch", "worktree-agent-one")
            git(repo, "branch", "feat/1-merged")
            git(repo, "branch", "feat/2-open")

            proc, calls = run_script(
                [],
                repo,
                {MERGED_LIST: "feat/1-merged", OPEN_LIST: "feat/2-open"},
            )

            branches = git(repo, "branch", "--format=%(refname:short)").stdout.splitlines()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("cleanup: done\n", proc.stdout)
        self.assertIn("deleted local branch: feat/1-merged\n", proc.stdout)
        self.assertNotIn("worktree-agent-one", branches)
        self.assertNotIn("feat/1-merged", branches)
        self.assertIn("feat/2-open", branches)
        self.assertEqual(calls, [list(MERGED_LIST), list(OPEN_LIST)])

    def test_no_worktree_root_skips_worktree_pass(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td).resolve()
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            add_local_origin(repo, td)
            wtroot = td / "wtroot"
            wtroot.mkdir()
            git(repo, "worktree", "add", "-q", str(wtroot / "1"), "-b", "feat/1")

            proc, calls = run_script([], repo, {MERGED_LIST: "", OPEN_LIST: ""})

            worktrees = git(repo, "worktree", "list").stdout

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("worktree pass: skipped", proc.stdout)
        self.assertIn(str(wtroot / "1"), worktrees)

    def test_worktree_under_root_is_removed(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td).resolve()
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            add_local_origin(repo, td)
            wtroot = td / "wtroot"
            wtroot.mkdir()
            wt = wtroot / "1"
            git(repo, "worktree", "add", "-q", str(wt), "-b", "feat/1")

            proc, calls = run_script(
                ["--worktree-root", str(wtroot)],
                repo,
                {MERGED_LIST: "", OPEN_LIST: ""},
            )

            worktrees = git(repo, "worktree", "list").stdout

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(f"removed worktree: {wt}\n", proc.stdout)
        self.assertNotIn(str(wt), worktrees)

    def test_worktree_outside_root_is_never_touched(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td).resolve()
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            add_local_origin(repo, td)
            wtroot = td / "wtroot"
            wtroot.mkdir()
            outside = td / "outside"
            outside.mkdir()
            inside_wt = wtroot / "1"
            outside_wt = outside / "1"
            git(repo, "worktree", "add", "-q", str(inside_wt), "-b", "feat/inside")
            git(repo, "worktree", "add", "-q", str(outside_wt), "-b", "feat/outside")

            proc, calls = run_script(
                ["--worktree-root", str(wtroot)],
                repo,
                {MERGED_LIST: "", OPEN_LIST: ""},
            )

            worktrees = git(repo, "worktree", "list").stdout

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn(str(inside_wt), worktrees)
        self.assertIn(str(outside_wt), worktrees)

    def test_merged_only_keeps_unmerged_removes_merged(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td).resolve()
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            add_local_origin(repo, td)
            wtroot = td / "wtroot"
            wtroot.mkdir()
            merged_wt = wtroot / "merged"
            unmerged_wt = wtroot / "unmerged"
            git(repo, "worktree", "add", "-q", str(merged_wt), "-b", "feat/merged")
            git(repo, "worktree", "add", "-q", str(unmerged_wt), "-b", "feat/unmerged")

            proc, calls = run_script(
                ["--worktree-root", str(wtroot), "--merged-only"],
                repo,
                {MERGED_LIST: "feat/merged", OPEN_LIST: ""},
            )

            worktrees = git(repo, "worktree", "list").stdout

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(f"removed worktree: {merged_wt}\n", proc.stdout)
        self.assertIn(f"SKIPPED (no merged PR / open PR on feat/unmerged): {unmerged_wt}\n", proc.stdout)
        self.assertNotIn(str(merged_wt), worktrees)
        self.assertIn(str(unmerged_wt), worktrees)

    def test_dirty_worktree_skipped_then_removed_with_force(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td).resolve()
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            add_local_origin(repo, td)
            wtroot = td / "wtroot"
            wtroot.mkdir()
            wt = wtroot / "dirty"
            git(repo, "worktree", "add", "-q", str(wt), "-b", "feat/dirty")
            (wt / "scratch.txt").write_text("dirty\n", encoding="utf-8")

            proc, calls = run_script(
                ["--worktree-root", str(wtroot)],
                repo,
                {MERGED_LIST: "", OPEN_LIST: ""},
            )
            worktrees_after_default = git(repo, "worktree", "list").stdout

            proc2, calls2 = run_script(
                ["--worktree-root", str(wtroot), "--force"],
                repo,
                {MERGED_LIST: "", OPEN_LIST: ""},
            )
            worktrees_after_force = git(repo, "worktree", "list").stdout

        self.assertIn(f"SKIPPED (dirty — salvage, then rerun with --force): {wt}\n", proc.stdout)
        self.assertIn(str(wt), worktrees_after_default)

        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        self.assertIn(f"removed worktree: {wt}\n", proc2.stdout)
        self.assertNotIn(str(wt), worktrees_after_force)

    def test_merged_branch_checked_out_in_surviving_worktree_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td).resolve()
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            add_local_origin(repo, td)
            wtroot = td / "wtroot"
            wtroot.mkdir()
            wt = wtroot / "1"
            git(repo, "worktree", "add", "-q", str(wt), "-b", "feat/1")
            (wt / "scratch.txt").write_text("dirty\n", encoding="utf-8")

            proc, calls = run_script(
                ["--worktree-root", str(wtroot)],
                repo,
                {MERGED_LIST: "feat/1", OPEN_LIST: ""},
            )

            branches = git(repo, "branch", "--format=%(refname:short)").stdout.splitlines()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(f"SKIPPED (checked out in worktree {wt}): feat/1\n", proc.stdout)
        self.assertNotIn("deleted local branch: feat/1", proc.stdout)
        self.assertIn("feat/1", branches)

    def test_dry_run_removes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td).resolve()
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            add_local_origin(repo, td)
            wtroot = td / "wtroot"
            wtroot.mkdir()
            wt = wtroot / "1"
            git(repo, "worktree", "add", "-q", str(wt), "-b", "feat/1")
            git(repo, "branch", "feat/2-merged")

            proc, calls = run_script(
                ["--dry-run", "--worktree-root", str(wtroot)],
                repo,
                {MERGED_LIST: "feat/2-merged", OPEN_LIST: ""},
            )

            worktrees = git(repo, "worktree", "list").stdout
            branches = git(repo, "branch", "--format=%(refname:short)").stdout.splitlines()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(str(wt), worktrees)
        self.assertIn("feat/2-merged", branches)

    def test_gh_lookup_failure_stops_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            make_repo(repo)
            add_local_origin(repo, Path(td))
            git(repo, "branch", "worktree-agent-one")

            proc, calls = run_script(
                [], repo, {MERGED_LIST: "", OPEN_LIST: ""}, exits={MERGED_LIST: 1}
            )

            branches = git(repo, "branch", "--format=%(refname:short)").stdout.splitlines()

        self.assertEqual(proc.returncode, 1)
        self.assertEqual(calls, [list(MERGED_LIST)])
        self.assertNotIn("cleanup: done", proc.stdout)
        self.assertIn("worktree-agent-one", branches)


if __name__ == "__main__":
    unittest.main()
