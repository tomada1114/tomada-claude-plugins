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


def issue_view_prefix(issue):
    return ("issue", "view", issue, "--json", "state")


class LandPrTest(unittest.TestCase):
    def test_missing_pr_is_usage_error(self):
        proc, calls = run_script([], {})

        self.assertEqual(proc.returncode, 2)
        self.assertIn("Usage: land_pr.sh <pr-number>", proc.stderr)
        self.assertEqual(calls, [])

    def test_help_flag_prints_own_usage_and_never_calls_gh(self):
        for flag in ("-h", "--help"):
            with self.subTest(flag=flag):
                proc, calls = run_script([flag], {})

                self.assertEqual(proc.returncode, 0)
                self.assertIn("land_pr.sh — Merge a green PR", proc.stdout)
                self.assertIn("Exit codes: 0 = merged", proc.stdout)
                self.assertNotIn("gh:", proc.stdout)
                self.assertEqual(calls, [])

    def test_already_merged_without_issue_reports_result_only(self):
        pr = "50"
        proc, calls = run_script([pr], {state_prefix(pr): "MERGED\n"})

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("result: ALREADY_MERGED\n", proc.stdout)
        self.assertEqual(calls, [list(state_prefix(pr)) + ["-q", ".state"]])

    def test_already_merged_with_issue_confirms_issue_closed(self):
        pr = "51"
        issue = "60"
        proc, calls = run_script(
            [pr, "--issue", issue],
            {
                state_prefix(pr): "MERGED\n",
                issue_view_prefix(issue): "CLOSED\n",
            },
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("result: ALREADY_MERGED\n", proc.stdout)
        self.assertIn(f"issue: CLOSED (#{issue})\n", proc.stdout)
        self.assertEqual([call[:2] for call in calls if call[:2] == ["issue", "close"]], [])

    def test_not_open_state_is_reported(self):
        pr = "52"
        proc, calls = run_script([pr], {state_prefix(pr): "CLOSED\n"})

        self.assertEqual(proc.returncode, 1)
        self.assertIn("result: NOT_OPEN\n", proc.stdout)
        self.assertIn("state: CLOSED\n", proc.stdout)
        self.assertEqual(calls, [list(state_prefix(pr)) + ["-q", ".state"]])

    def test_wrong_base_blocks_merge(self):
        pr = "53"
        issue = "61"
        base = ("pr", "view", pr, "--json", "baseRefName")
        default_branch = ("repo", "view", "--json", "defaultBranchRef")
        closing = ("pr", "view", pr, "--json", "closingIssuesReferences")
        proc, calls = run_script(
            [pr, "--issue", issue],
            {
                state_prefix(pr): "OPEN\n",
                draft_prefix(pr): "false\n",
                base: "release\n",
                default_branch: "main\n",
                # closes already includes the issue so the --fix repair block
                # (mktemp/gh pr edit) never has to run for this base check.
                closing: f"{issue}\n",
            },
        )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("result: WRONG_BASE\n", proc.stdout)
        self.assertEqual([call for call in calls if call[:2] == ["pr", "edit"]], [])

    def test_not_linked_blocks_merge(self):
        pr = "54"
        issue = "62"
        base = ("pr", "view", pr, "--json", "baseRefName")
        default_branch = ("repo", "view", "--json", "defaultBranchRef")
        closing = ("pr", "view", pr, "--json", "closingIssuesReferences")
        body = ("pr", "view", pr, "--json", "body")
        edit = ("pr", "edit", pr)
        proc, calls = run_script(
            [pr, "--issue", issue],
            {
                state_prefix(pr): "OPEN\n",
                draft_prefix(pr): "false\n",
                base: "main\n",
                default_branch: "main\n",
                # closes never includes the issue: the fix is attempted but
                # `gh pr edit` fails, so no sleep/retry and no eventual link.
                closing: "5\n",
                body: "original body\n",
            },
            exits={edit: 1},
        )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("result: NOT_LINKED\n", proc.stdout)
        self.assertTrue(any(call[:2] == ["pr", "edit"] for call in calls))

    def test_draft_no_ready_reports_draft_result(self):
        pr = "55"
        proc, calls = run_script(
            [pr, "--no-ready", "--no-link-check"],
            {state_prefix(pr): "OPEN\n", draft_prefix(pr): "true\n"},
        )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("draft: true\n", proc.stdout)
        self.assertIn("result: DRAFT\n", proc.stdout)
        self.assertEqual([call for call in calls if call[:2] == ["pr", "ready"]], [])

    def test_draft_ready_command_fails(self):
        pr = "56"
        ready = ("pr", "ready", pr)
        proc, calls = run_script(
            [pr, "--no-link-check"],
            {state_prefix(pr): "OPEN\n", draft_prefix(pr): "true\n", ready: ""},
            exits={ready: 1},
        )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("draft: true\n", proc.stdout)
        self.assertIn("result: DRAFT\n", proc.stdout)
        self.assertIn("gh pr ready", proc.stdout)
        self.assertTrue(any(call[:2] == ["pr", "ready"] for call in calls))

    def test_merge_success_but_final_state_not_confirmed_is_merge_unconfirmed(self):
        pr = "57"
        merge = ("pr", "merge", pr, "--squash", "--delete-branch")
        proc, calls = run_script(
            [pr, "--method", "squash", "--no-link-check"],
            {
                # state_prefix is queried both before the merge (must read
                # OPEN to proceed) and again afterward to confirm; the fake
                # always answers the same value for a given prefix, so
                # answering OPEN here naturally reproduces "merge succeeded
                # but gh still reports the PR as not-yet-merged".
                state_prefix(pr): "OPEN\n",
                draft_prefix(pr): "false\n",
                merge: "",
            },
        )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("result: MERGE_UNCONFIRMED\n", proc.stdout)
        self.assertIn("state: OPEN\n", proc.stdout)
        self.assertTrue(any(call[:2] == ["pr", "merge"] for call in calls))

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
