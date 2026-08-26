#!/usr/bin/env python3
"""Tests for link_check.sh. Stdlib-only (unittest).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the shipping-issues skill directory)
"""
from __future__ import annotations

import subprocess
import sys
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

    def test_dry_run_flag_is_rejected_without_mutating_gh(self):
        # link_check.sh documents --fix, but has no --dry-run mode; preserve
        # that observed contract and prove the unsupported flag cannot reach gh.
        proc, calls = run_script(["33", "--issue", "7", "--dry-run"], {})

        self.assertEqual(proc.returncode, 3)
        self.assertIn("Unknown argument: --dry-run", proc.stderr)
        self.assertEqual(calls, [])
        self.assertEqual([call for call in calls if call[:2] == ["pr", "edit"]], [])


if __name__ == "__main__":
    unittest.main()
