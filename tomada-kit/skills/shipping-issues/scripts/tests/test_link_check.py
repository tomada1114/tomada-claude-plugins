#!/usr/bin/env python3
"""Tests for link_check.sh. Stdlib-only (unittest).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the shipping-issues skill directory)
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _fakegh import FakeGh  # noqa: E402


SCRIPT = Path(__file__).resolve().parent.parent / "link_check.sh"


def run_script(args, responses, *, exits=None, stderrs=None):
    with FakeGh(responses, exits=exits, stderrs=stderrs) as fake:
        proc = subprocess.run(
            ["bash", str(SCRIPT), *args],
            env=fake.env,
            text=True,
            capture_output=True,
        )
        calls = list(fake.calls)
    return proc, calls


def run_script_with_broken_mktemp(args, responses, *, exits=None, stderrs=None):
    """Like run_script, but shadows `mktemp` on PATH with a stub that always
    fails, so the script's own `mktemp ... || { ...; exit 3; }` guard fires
    deterministically without touching the real filesystem's temp handling."""
    with FakeGh(responses, exits=exits, stderrs=stderrs) as fake:
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td)
            stub = stub_dir / "mktemp"
            stub.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            env = dict(fake.env)
            env["PATH"] = f"{stub_dir}{os.pathsep}{env['PATH']}"
            proc = subprocess.run(
                ["bash", str(SCRIPT), *args],
                env=env,
                text=True,
                capture_output=True,
            )
        calls = list(fake.calls)
    return proc, calls


def base_prefix(pr):
    return ("pr", "view", pr, "--json", "baseRefName")


def closing_prefix(pr):
    return ("pr", "view", pr, "--json", "closingIssuesReferences")


class LinkCheckTest(unittest.TestCase):
    def test_missing_pr_is_usage_error(self):
        proc, calls = run_script([], {})

        self.assertEqual(proc.returncode, 3)
        self.assertIn("Usage: link_check.sh <pr-number>", proc.stderr)
        self.assertEqual(calls, [])

    def test_linked_issue_reports_base_closes_and_verdict(self):
        pr = "31"
        proc, calls = run_script(
            [pr, "--issue", "7"],
            {
                base_prefix(pr): "main\n",
                ("repo", "view", "--json", "defaultBranchRef"): "main\n",
                closing_prefix(pr): "7,8\n",
            },
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("base: main (default: main)\n", proc.stdout)
        self.assertIn("closes: 7,8\n", proc.stdout)
        self.assertIn("verdict: LINKED\n", proc.stdout)
        self.assertEqual(
            sum(call[:5] == list(closing_prefix(pr)) for call in calls), 1
        )

    def test_non_default_base_is_failure(self):
        pr = "32"
        proc, calls = run_script(
            [pr, "--issue", "7"],
            {
                base_prefix(pr): "release\n",
                ("repo", "view", "--json", "defaultBranchRef"): "main\n",
                closing_prefix(pr): "7\n",
            },
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("base: release (default: main)\n", proc.stdout)
        self.assertIn("verdict: WRONG_BASE\n", proc.stdout)
        self.assertEqual(calls.count(["pr", "edit"]), 0)

    def test_help_flag_prints_own_usage_and_never_calls_gh(self):
        for flag in ("-h", "--help"):
            with self.subTest(flag=flag):
                proc, calls = run_script([flag], {})

                self.assertEqual(proc.returncode, 0)
                self.assertIn(
                    "link_check.sh — Verify a PR will auto-close its issue",
                    proc.stdout,
                )
                self.assertIn("Exit codes: 0 = LINKED", proc.stdout)
                self.assertEqual(calls, [])

    def test_fix_dry_run_prints_intended_append_without_mutating_pr(self):
        pr = "33"
        issue = "7"
        proc, calls = run_script(
            [pr, "--issue", issue, "--fix", "--dry-run"],
            {
                base_prefix(pr): "main\n",
                ("repo", "view", "--json", "defaultBranchRef"): "main\n",
                # closes does not yet include the target issue, so the
                # repair block's dry-run branch is what runs.
                closing_prefix(pr): "5\n",
            },
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(
            f"fix: would append 'Closes #{issue}' to PR #{pr} body (dry run — no change made)\n",
            proc.stdout,
        )
        self.assertIn("verdict: LINKED\n", proc.stdout)
        self.assertEqual([call for call in calls if call[:2] == ["pr", "edit"]], [])

    def test_fix_mktemp_failure_reports_error(self):
        pr = "34"
        issue = "7"
        proc, calls = run_script_with_broken_mktemp(
            [pr, "--issue", issue, "--fix"],
            {
                base_prefix(pr): "main\n",
                ("repo", "view", "--json", "defaultBranchRef"): "main\n",
                closing_prefix(pr): "5\n",
            },
        )

        self.assertEqual(proc.returncode, 3)
        self.assertIn("verdict: ERROR\n", proc.stdout)
        self.assertIn("detail: mktemp failed\n", proc.stdout)
        self.assertEqual([call for call in calls if call[:2] == ["pr", "edit"]], [])

    def test_fix_gh_pr_edit_failure_reports_failed_and_stays_not_linked(self):
        pr = "35"
        issue = "7"
        body = ("pr", "view", pr, "--json", "body")
        edit = ("pr", "edit", pr)
        proc, calls = run_script(
            [pr, "--issue", issue, "--fix"],
            {
                base_prefix(pr): "main\n",
                ("repo", "view", "--json", "defaultBranchRef"): "main\n",
                closing_prefix(pr): "5\n",
                body: "original body\n",
                edit: "",
            },
            exits={edit: 1},
        )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("fix: FAILED (could not edit PR body)\n", proc.stdout)
        self.assertIn("verdict: NOT_LINKED\n", proc.stdout)
        self.assertTrue(any(call[:2] == ["pr", "edit"] for call in calls))


if __name__ == "__main__":
    unittest.main()
