#!/usr/bin/env python3
"""Tests for land_pr.sh. Stdlib-only (unittest).

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


SCRIPT = Path(__file__).resolve().parent.parent / "land_pr.sh"


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


def state_prefix(pr):
    return ("pr", "view", pr, "--json", "state")


def draft_prefix(pr):
    return ("pr", "view", pr, "--json", "isDraft")


def inspect_prefix(pr):
    return ("pr", "view", pr, "--json", "mergeable,mergeStateStatus,reviewDecision")


class LandPrTest(unittest.TestCase):
    def test_missing_pr_is_usage_error(self):
        proc, calls = run_script([], {})

        self.assertEqual(proc.returncode, 2)
        self.assertIn("Usage: land_pr.sh <pr-number>", proc.stderr)
        self.assertEqual(calls, [])

    def test_auto_merge_success_reports_result_and_issue(self):
        pr = "27"
        issue = "41"
        merge = ("pr", "merge", pr, "--squash", "--delete-branch", "--auto")
        proc, calls = run_script(
            [pr, "--issue", issue, "--method", "squash", "--auto", "--no-link-check"],
            {
                state_prefix(pr): "OPEN\n",
                draft_prefix(pr): "false\n",
                merge: "",
            },
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("method: squash\n", proc.stdout)
        self.assertIn("result: AUTO_MERGE_ARMED\n", proc.stdout)
        self.assertIn("issue: PENDING (#41 closes when auto-merge lands)\n", proc.stdout)
        self.assertIn(list(merge), calls)

    def test_merge_refusal_reports_failure(self):
        pr = "28"
        merge = ("pr", "merge", pr, "--squash", "--delete-branch")
        inspect = inspect_prefix(pr)
        proc, calls = run_script(
            [pr, "--method", "squash", "--no-link-check"],
            {
                state_prefix(pr): "OPEN\n",
                draft_prefix(pr): "false\n",
                merge: "",
                inspect: '{"mergeable":"CONFLICTING","mergeStateStatus":"BLOCKED",'
                        '"reviewDecision":"CHANGES_REQUESTED"}\n',
            },
            exits={merge: 1},
            stderrs={merge: "merge blocked\n"},
        )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("result: MERGE_REFUSED\n", proc.stdout)
        self.assertIn("  merge blocked\n", proc.stdout)
        self.assertIn(list(inspect), calls)

    def test_dry_run_never_calls_mutating_gh_commands(self):
        pr = "29"
        issue = "42"
        base = ("pr", "view", pr, "--json", "baseRefName")
        closing = ("pr", "view", pr, "--json", "closingIssuesReferences")
        default_branch = ("repo", "view", "--json", "defaultBranchRef")
        proc, calls = run_script(
            [pr, "--issue", issue, "--method", "squash", "--dry-run"],
            {
                state_prefix(pr): "OPEN\n",
                draft_prefix(pr): "false\n",
                base: "main\n",
                default_branch: "main\n",
                closing: "42\n",
                inspect_prefix(pr): '{"mergeable":"MERGEABLE","mergeStateStatus":"CLEAN",'
                                    '"reviewDecision":"APPROVED"}\n',
            },
        )

        mutating = [
            call for call in calls
            if call[:2] in (["pr", "merge"], ["pr", "ready"],
                            ["pr", "edit"], ["issue", "close"])
        ]
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("result: DRY_RUN\n", proc.stdout)
        self.assertIn("link| verdict: LINKED\n", proc.stdout)
        self.assertEqual(mutating, [])


if __name__ == "__main__":
    unittest.main()
