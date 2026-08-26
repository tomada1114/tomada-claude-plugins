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


REPO_META = (
    "repo", "view", "--json",
    "nameWithOwner,defaultBranchRef,squashMergeAllowed,mergeCommitAllowed,"
    "rebaseMergeAllowed,deleteBranchOnMerge",
)
REPO_DEFAULT = ("repo", "view", "--json", "defaultBranchRef")
PROTECTION = ("api", "repos/{owner}/{repo}/branches/main/protection")


class PreflightTest(unittest.TestCase):
    def test_ready_repo_reports_metadata_and_ready_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            make_repo(repo, origin=True)
            proc, calls = run_script(
                [], repo,
                {
                    REPO_META: (
                        '{"nameWithOwner":"acme/widgets","defaultBranchRef":{"name":"main"},'
                        '"squashMergeAllowed":true,"mergeCommitAllowed":false,'
                        '"rebaseMergeAllowed":true,"deleteBranchOnMerge":true}'
                    ),
                    REPO_DEFAULT: "main\n",
                    PROTECTION: "",
                },
            )
            reported_root = git(repo, "rev-parse", "--show-toplevel").stdout.strip()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        expected_lines = [
            "gh_cli: ok",
            "gh_auth: ok",
            "git_repo: ok",
            f"repo_root: {reported_root}",
            "origin: https://example.invalid/acme/widgets.git",
            "current_branch: main",
            "working_tree: clean",
            "repo: acme/widgets",
            "default_branch: main",
            "merge_methods:  squash rebase",
            "delete_branch_on_merge: true",
            "branch_protection: unknown_or_none",
            "verdict: READY",
        ]
        for line in expected_lines:
            self.assertIn(f"{line}\n", proc.stdout)
        self.assertIn(["auth", "status"], calls)
        self.assertIn(list(REPO_META), calls)
        self.assertIn(list(PROTECTION), calls)

    def test_missing_origin_blocks_before_repo_metadata_lookup(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            make_repo(repo)
            proc, calls = run_script([], repo, {})

        self.assertEqual(proc.returncode, 1)
        self.assertIn("origin: MISSING\n", proc.stdout)
        self.assertIn("verdict: BLOCKED\n", proc.stdout)
        self.assertIn(["auth", "status"], calls)
        self.assertNotIn(["repo", "view"], [call[:2] for call in calls])


if __name__ == "__main__":
    unittest.main()
