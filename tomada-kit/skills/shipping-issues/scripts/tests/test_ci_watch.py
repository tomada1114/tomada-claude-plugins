#!/usr/bin/env python3
"""Tests for ci_watch.sh. Stdlib-only (unittest).

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


SCRIPT = Path(__file__).resolve().parent.parent / "ci_watch.sh"


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


class CiWatchTest(unittest.TestCase):
    def test_missing_pr_is_usage_error(self):
        proc, calls = run_script([], {})

        self.assertEqual(proc.returncode, 4)
        self.assertIn("Usage: ci_watch.sh <pr-number>", proc.stderr)
        self.assertEqual(calls, [])

    def test_terminal_pass_reports_state_on_first_poll(self):
        pr = "17"
        rollup = ("pr", "view", pr, "--json", "statusCheckRollup")
        checks_watch = ("pr", "checks", pr, "--watch", "--interval", "20")
        checks_result = ("pr", "checks", pr, "--json", "name,state,link")
        state = (
            "pr", "view", pr, "--json",
            "mergeable,mergeStateStatus,reviewDecision,isDraft,state",
        )
        proc, calls = run_script(
            [pr, "--timeout", "1"],
            {
                rollup: "1\n",
                checks_watch: "",
                checks_result: "",
                state: (
                    '{"state":"OPEN","isDraft":false,"mergeable":"MERGEABLE",'
                    '"mergeStateStatus":"CLEAN","reviewDecision":"APPROVED"}'
                ),
            },
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("verdict: PASS\n", proc.stdout)
        self.assertIn("pr_state: OPEN\n", proc.stdout)
        self.assertIn("draft: false\n", proc.stdout)
        self.assertIn("mergeable: MERGEABLE\n", proc.stdout)
        self.assertIn("merge_state: CLEAN\n", proc.stdout)
        self.assertIn("review_decision: APPROVED\n", proc.stdout)
        check_calls = [call for call in calls if call[:2] == ["pr", "checks"]]
        self.assertEqual(check_calls[0], list(checks_watch))
        self.assertEqual(check_calls[1][:5], list(checks_result))
        self.assertEqual(check_calls[1][5], "-q")

    def test_failed_check_reports_check_name_and_log_tail(self):
        pr = "18"
        rollup = ("pr", "view", pr, "--json", "statusCheckRollup")
        checks_watch = ("pr", "checks", pr, "--watch", "--interval", "20")
        checks_result = ("pr", "checks", pr, "--json", "name,state,link")
        state = (
            "pr", "view", pr, "--json",
            "mergeable,mergeStateStatus,reviewDecision,isDraft,state",
        )
        run_view = ("run", "view", "123", "--log-failed")
        proc, calls = run_script(
            [pr, "--timeout", "1", "--log-bytes", "32"],
            {
                rollup: "1\n",
                checks_watch: "",
                checks_result: (
                    "lint\tFAILURE\t"
                    "https://github.com/acme/widgets/actions/runs/123\n"
                ),
                state: (
                    '{"state":"OPEN","isDraft":false,"mergeable":"CONFLICTING",'
                    '"mergeStateStatus":"BLOCKED","reviewDecision":"CHANGES_REQUESTED"}'
                ),
                run_view: "line one\nline two\n",
            },
            exits={checks_watch: 1},
        )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("verdict: FAIL\n", proc.stdout)
        self.assertIn(
            "  - lint [FAILURE] https://github.com/acme/widgets/actions/runs/123\n",
            proc.stdout,
        )
        self.assertIn("failed_logs:\n", proc.stdout)
        self.assertIn("--- run 123 ---\n", proc.stdout)
        self.assertIn("  line one\n  line two\n", proc.stdout)
        self.assertEqual(calls.count(list(run_view)), 1)


if __name__ == "__main__":
    unittest.main()
