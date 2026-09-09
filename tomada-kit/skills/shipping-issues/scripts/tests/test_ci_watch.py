#!/usr/bin/env python3
"""Tests for ci_watch.sh. Stdlib-only (unittest).

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


def install_stub(bin_dir: Path, name: str, body: str) -> None:
    """Install an executable named `name` on `bin_dir` with the given body.

    Used to shadow a real external command (sleep, timeout) with a
    deterministic, instant stand-in, the same PATH-stubbing technique
    _fakegh.py already uses for `gh` — so a hard-coded `sleep 20` retry or a
    real `timeout`/`gtimeout` dependency doesn't make a test slow or
    environment-dependent.
    """
    stub = bin_dir / name
    stub.write_text(body, encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def run_script_with_stub_path(args, responses, stub_dir, *, exits=None, stderrs=None):
    """Like run_script, but with `stub_dir` prepended to PATH ahead of the
    fake gh's own bin dir, so stubs installed there (sleep, timeout) shadow
    both the fake gh and whatever is really on the host PATH."""
    with FakeGh(responses, exits=exits, stderrs=stderrs) as fake:
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


class CiWatchTest(unittest.TestCase):
    def test_missing_pr_is_usage_error(self):
        proc, calls = run_script([], {})

        self.assertEqual(proc.returncode, 4)
        self.assertIn("Usage: ci_watch.sh <pr-number>", proc.stderr)
        self.assertEqual(calls, [])

    def test_help_flag_prints_own_usage_and_never_calls_gh(self):
        for flag in ("-h", "--help"):
            with self.subTest(flag=flag):
                proc, calls = run_script([flag], {})

                self.assertEqual(proc.returncode, 0)
                self.assertIn("ci_watch.sh — Wait for a PR's checks", proc.stdout)
                self.assertIn("Exit codes: 0 = PASS", proc.stdout)
                self.assertEqual(calls, [])

    def test_error_when_pr_cannot_be_read(self):
        pr = "21"
        rollup = ("pr", "view", pr, "--json", "statusCheckRollup")
        proc, calls = run_script([pr], {rollup: ""}, exits={rollup: 1})

        self.assertEqual(proc.returncode, 4)
        self.assertIn("verdict: ERROR\n", proc.stdout)
        self.assertIn(f"detail: could not read PR #{pr}\n", proc.stdout)
        self.assertEqual(calls, [list(rollup) + ["-q", ".statusCheckRollup | length"]])

    def test_no_checks_reports_verdict_after_retry(self):
        # rollup answers "0" on both the first read and the post-retry read
        # (the fake always answers a given prefix the same way), so this
        # naturally exercises the sleep-then-recheck path without needing a
        # second, different fake response.
        pr = "20"
        rollup = ("pr", "view", pr, "--json", "statusCheckRollup")
        state = (
            "pr", "view", pr, "--json",
            "mergeable,mergeStateStatus,reviewDecision,isDraft,state",
        )
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td)
            install_stub(stub_dir, "sleep", "#!/usr/bin/env bash\nexit 0\n")
            proc, calls = run_script_with_stub_path(
                [pr],
                {
                    rollup: "0\n",
                    state: (
                        '{"state":"OPEN","isDraft":false,"mergeable":"MERGEABLE",'
                        '"mergeStateStatus":"CLEAN","reviewDecision":"APPROVED"}'
                    ),
                },
                stub_dir,
            )

        self.assertEqual(proc.returncode, 3)
        self.assertIn("verdict: NO_CHECKS\n", proc.stdout)
        self.assertIn("pr_state: OPEN\n", proc.stdout)
        rollup_calls = [c for c in calls if c[:5] == list(rollup)]
        self.assertEqual(len(rollup_calls), 2)

    def test_watch_timeout_reports_verdict_and_state(self):
        # Neither `timeout` nor `gtimeout` exists on every host this suite
        # runs on (this dev machine has neither), so ci_watch.sh's own guard
        # (`command -v timeout`/`gtimeout`) would otherwise skip the enforced
        # timeout entirely and this branch could never fire here. Stubbing a
        # `timeout` binary that always reports 124 makes the branch
        # reachable and deterministic without a real multi-second wait.
        pr = "22"
        rollup = ("pr", "view", pr, "--json", "statusCheckRollup")
        checks_plain = ("pr", "checks", pr)
        state = (
            "pr", "view", pr, "--json",
            "mergeable,mergeStateStatus,reviewDecision,isDraft,state",
        )
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td)
            install_stub(stub_dir, "timeout", "#!/usr/bin/env bash\nexit 124\n")
            proc, calls = run_script_with_stub_path(
                [pr, "--timeout", "5"],
                {
                    rollup: "1\n",
                    checks_plain: "lint\tSUCCESS\t\n",
                    state: (
                        '{"state":"OPEN","isDraft":false,"mergeable":"MERGEABLE",'
                        '"mergeStateStatus":"CLEAN","reviewDecision":"APPROVED"}'
                    ),
                },
                stub_dir,
            )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("verdict: TIMEOUT\n", proc.stdout)
        self.assertIn("waited_seconds: 5\n", proc.stdout)
        self.assertIn("pr_state: OPEN\n", proc.stdout)
        # The watched `gh pr checks --watch` call never actually reached the
        # fake gh: our stub `timeout` never execs its wrapped command.
        self.assertEqual([c for c in calls if "--watch" in c], [])

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
