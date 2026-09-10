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

# --- argv prefixes the script drives `gh` with -------------------------------
# The fake gh routes on an argv prefix, so each of these names one call the
# script makes. They are functions because every prefix carries the PR number
# or the head SHA the test is using.

SHA = "72109db377c3b1dfef84795d1157d992db712fb6"

# What GitHub actually returns when a fine-grained PAT reads check runs: the
# token has no Checks permission, because GitHub grants none.
FORBIDDEN_ERR = (
    "GraphQL: Resource not accessible by personal access token "
    "(repository.pullRequest.statusCheckRollup.nodes.0.commit"
    ".statusCheckRollup.contexts.nodes.0)\n"
)

STATE_JSON = (
    '{"state":"OPEN","isDraft":false,"mergeable":"MERGEABLE",'
    '"mergeStateStatus":"CLEAN","reviewDecision":"APPROVED"}'
)


def ROLLUP(pr):
    return ("pr", "view", pr, "--json", "statusCheckRollup")


def HEAD_OID(pr):
    return ("pr", "view", pr, "--json", "headRefOid")


def STATE(pr):
    return ("pr", "view", pr, "--json",
            "mergeable,mergeStateStatus,reviewDecision,isDraft,state")


def RUNS(sha):
    return ("run", "list", "--commit", sha)


def STATUSES(sha):
    return ("api", "repos/{owner}/{repo}/commits/%s/status" % sha)


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


def install_advancing_clock(bin_dir: Path) -> None:
    """Install a `date` that jumps 100 seconds every call.

    The fallback poll loop decides it has timed out by comparing `date +%s`
    against a deadline. With `sleep` stubbed out to keep the suite fast, the
    real clock barely moves, so the deadline would never be reached. Advancing
    a counter instead makes the timeout branch fire deterministically and
    without waiting.
    """
    install_stub(bin_dir, "date", f"""#!/usr/bin/env bash
counter="{bin_dir}/.clock"
n=$(cat "$counter" 2>/dev/null || echo 0)
n=$((n + 100))
echo "$n" > "$counter"
echo "$n"
""")


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
        # Every `gh pr view` on this PR fails, so the PR really is unreadable
        # and ERROR is the honest verdict. The three-element prefix matches
        # both the rollup read and the follow-up readability probe.
        pr = "21"
        any_pr_view = ("pr", "view", pr)
        rollup = ("pr", "view", pr, "--json", "statusCheckRollup")
        proc, calls = run_script(
            [pr],
            {any_pr_view: ""},
            exits={any_pr_view: 1},
            stderrs={any_pr_view: "GraphQL: Could not resolve to a PullRequest\n"},
        )

        self.assertEqual(proc.returncode, 4)
        self.assertIn("verdict: ERROR\n", proc.stdout)
        self.assertIn(f"detail: could not read PR #{pr}: ", proc.stdout)
        self.assertIn("Could not resolve to a PullRequest", proc.stdout)
        self.assertEqual(calls, [
            list(rollup) + ["-q", ".statusCheckRollup | length"],
            ["pr", "view", pr, "--json", "headRefOid", "-q", ".headRefOid"],
        ])

    def test_unreadable_rollup_on_a_readable_pr_is_not_reported_as_a_bad_pr(self):
        # The fine-grained-PAT shape: the PR reads fine, only its check runs
        # are forbidden. Reporting that as "could not read PR #N" hid the real
        # cause, so the two failures must stay distinguishable.
        pr = "23"
        proc, calls = run_script(
            [pr],
            {
                ROLLUP(pr): "",
                    HEAD_OID(pr): SHA,
                RUNS(SHA): "",
                STATUSES(SHA): "",
                STATE(pr): STATE_JSON,
            },
            exits={ROLLUP(pr): 1},
            stderrs={ROLLUP(pr): FORBIDDEN_ERR},
        )

        self.assertNotIn(f"could not read PR #{pr}", proc.stdout)
        self.assertIn("check_source: actions+statuses\n", proc.stdout)
        self.assertIn("check runs are not readable by this token", proc.stderr)
        self.assertIn("Resource not accessible by personal access token", proc.stderr)
        self.assertIn(
            ["pr", "view", pr, "--json", "headRefOid", "-q", ".headRefOid"], calls)

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
        self.assertIn("check_source: checks\n", proc.stdout)
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
        self.assertIn("check_source: checks\n", proc.stdout)
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
        self.assertIn("check_source: checks\n", proc.stdout)
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
        self.assertIn("check_source: checks\n", proc.stdout)
        self.assertIn(
            "  - lint [FAILURE] https://github.com/acme/widgets/actions/runs/123\n",
            proc.stdout,
        )
        self.assertIn("failed_logs:\n", proc.stdout)
        self.assertIn("--- run 123 ---\n", proc.stdout)
        self.assertIn("  line one\n  line two\n", proc.stdout)
        self.assertEqual(calls.count(list(run_view)), 1)


class CiWatchFallbackTest(unittest.TestCase):
    """The fine-grained-PAT path.

    GitHub's fine-grained PATs have no Checks permission, so every one of
    these starts from a rollup read that fails with "Resource not accessible
    by personal access token" and asserts the script still reaches a correct
    verdict from Actions runs plus commit statuses.
    """

    def forbidden(self, pr, extra, *, exits=None, stderrs=None, stub_dir=None):
        responses = {
            ROLLUP(pr): "",
            HEAD_OID(pr): SHA,
            RUNS(SHA): "",
            STATUSES(SHA): "",
            STATE(pr): STATE_JSON,
        }
        responses.update(extra)
        all_exits = {ROLLUP(pr): 1}
        all_exits.update(exits or {})
        all_stderrs = {ROLLUP(pr): FORBIDDEN_ERR}
        all_stderrs.update(stderrs or {})
        if stub_dir is not None:
            return run_script_with_stub_path(
                self.args, responses, stub_dir,
                exits=all_exits, stderrs=all_stderrs)
        return run_script(self.args, responses,
                          exits=all_exits, stderrs=all_stderrs)

    def test_pass_from_a_successful_actions_run(self):
        pr = "30"
        self.args = [pr]
        proc, calls = self.forbidden(pr, {
            RUNS(SHA): (
                "456\tCI\tcompleted\tsuccess\t"
                "https://github.com/acme/widgets/actions/runs/456\n"
            ),
        })

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("verdict: PASS\n", proc.stdout)
        self.assertIn("check_source: actions+statuses\n", proc.stdout)
        self.assertIn(f"head_sha: {SHA}\n", proc.stdout)
        self.assertIn("pr_state: OPEN\n", proc.stdout)
        # It must never fall back to a call the token cannot make.
        self.assertEqual([c for c in calls if c[:2] == ["pr", "checks"]], [])

    def test_completions_that_do_not_fail_a_pr_still_pass(self):
        # A skipped or neutral run is a completion, not a failure; treating
        # either as red would block every PR that skips a path-filtered job.
        pr = "31"
        self.args = [pr]
        proc, _ = self.forbidden(pr, {
            RUNS(SHA): (
                "1\tCI\tcompleted\tsuccess\thttps://x/actions/runs/1\n"
                "2\tDocs\tcompleted\tskipped\thttps://x/actions/runs/2\n"
                "3\tLint\tcompleted\tneutral\thttps://x/actions/runs/3\n"
            ),
        })

        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("verdict: PASS\n", proc.stdout)

    def test_failed_run_reports_name_and_log_tail(self):
        pr = "32"
        self.args = [pr, "--log-bytes", "32"]
        run_view = ("run", "view", "456", "--log-failed")
        proc, calls = self.forbidden(pr, {
            RUNS(SHA): (
                "456\tCI\tcompleted\tfailure\t"
                "https://github.com/acme/widgets/actions/runs/456\n"
            ),
            run_view: "line one\nline two\n",
        })

        self.assertEqual(proc.returncode, 1)
        self.assertIn("verdict: FAIL\n", proc.stdout)
        self.assertIn("check_source: actions+statuses\n", proc.stdout)
        self.assertIn(
            "  - CI [completed/failure] "
            "https://github.com/acme/widgets/actions/runs/456\n",
            proc.stdout,
        )
        self.assertIn("failed_logs:\n", proc.stdout)
        self.assertIn("--- run 456 ---\n", proc.stdout)
        self.assertIn("  line one\n  line two\n", proc.stdout)
        self.assertEqual(calls.count(list(run_view)), 1)

    def test_only_the_failing_run_is_reported(self):
        pr = "33"
        self.args = [pr]
        proc, calls = self.forbidden(pr, {
            RUNS(SHA): (
                "1\tCI\tcompleted\tsuccess\thttps://x/actions/runs/1\n"
                "2\tDeploy\tcompleted\ttimed_out\thttps://x/actions/runs/2\n"
            ),
            ("run", "view", "2", "--log-failed"): "boom\n",
        })

        self.assertEqual(proc.returncode, 1)
        self.assertIn("  - Deploy [completed/timed_out] ", proc.stdout)
        self.assertNotIn("  - CI [completed/success]", proc.stdout)
        self.assertEqual([c for c in calls if c[:2] == ["run", "view"]],
                         [["run", "view", "2", "--log-failed"]])

    def test_failing_commit_status_fails_without_an_actions_run(self):
        # Commit statuses are the other half of what a fine-grained PAT can
        # read, and the CI systems that post them have no Actions run to fetch
        # a log from — so the check is listed but no log dump is attempted.
        pr = "34"
        self.args = [pr]
        proc, calls = self.forbidden(pr, {
            STATUSES(SHA): "ci/external\tfailure\thttps://ci.example.com/build/9\n",
        })

        self.assertEqual(proc.returncode, 1)
        self.assertIn("verdict: FAIL\n", proc.stdout)
        self.assertIn(
            "  - ci/external [failure] https://ci.example.com/build/9\n",
            proc.stdout,
        )
        self.assertEqual([c for c in calls if c[:2] == ["run", "view"]], [])

    def test_successful_commit_status_passes(self):
        pr = "35"
        self.args = [pr]
        proc, _ = self.forbidden(pr, {
            STATUSES(SHA): "ci/external\tsuccess\thttps://ci.example.com/build/9\n",
        })

        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("verdict: PASS\n", proc.stdout)

    def test_no_checks_after_an_empty_repoll(self):
        # Neither source reports anything, twice in a row. The first empty
        # answer only means GitHub may not have registered a freshly triggered
        # workflow yet; the second settles it.
        pr = "36"
        self.args = [pr, "--timeout", "600"]
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td)
            install_stub(stub_dir, "sleep", "#!/usr/bin/env bash\nexit 0\n")
            proc, calls = self.forbidden(pr, {}, stub_dir=stub_dir)

        self.assertEqual(proc.returncode, 3)
        self.assertIn("verdict: NO_CHECKS\n", proc.stdout)
        self.assertIn("check_source: actions+statuses\n", proc.stdout)
        self.assertIn("pr_state: OPEN\n", proc.stdout)
        self.assertEqual(len([c for c in calls if c[:3] == list(RUNS(SHA))[:3]]), 2)

    def test_timeout_while_a_run_is_still_going(self):
        pr = "37"
        self.args = [pr, "--timeout", "60"]
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td)
            install_stub(stub_dir, "sleep", "#!/usr/bin/env bash\nexit 0\n")
            install_advancing_clock(stub_dir)
            proc, calls = self.forbidden(pr, {
                RUNS(SHA): (
                    "456\tCI\tin_progress\t\t"
                    "https://github.com/acme/widgets/actions/runs/456\n"
                ),
            }, stub_dir=stub_dir)

        self.assertEqual(proc.returncode, 2)
        self.assertIn("verdict: TIMEOUT\n", proc.stdout)
        self.assertIn("check_source: actions+statuses\n", proc.stdout)
        self.assertIn("waited_seconds: 60\n", proc.stdout)
        self.assertIn(
            "  - CI [in_progress] "
            "https://github.com/acme/widgets/actions/runs/456\n",
            proc.stdout,
        )
        self.assertIn("pr_state: OPEN\n", proc.stdout)
        self.assertEqual([c for c in calls if c[:2] == ["run", "view"]], [])

    def test_a_pending_commit_status_also_holds_the_verdict(self):
        pr = "38"
        self.args = [pr, "--timeout", "60"]
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td)
            install_stub(stub_dir, "sleep", "#!/usr/bin/env bash\nexit 0\n")
            install_advancing_clock(stub_dir)
            proc, _ = self.forbidden(pr, {
                RUNS(SHA): (
                    "456\tCI\tcompleted\tsuccess\thttps://x/actions/runs/456\n"
                ),
                STATUSES(SHA): "ci/external\tpending\thttps://ci.example.com/build/9\n",
            }, stub_dir=stub_dir)

        self.assertEqual(proc.returncode, 2)
        self.assertIn("verdict: TIMEOUT\n", proc.stdout)

    def test_error_when_the_head_commit_cannot_be_read(self):
        # The head-commit read doubles as the readability probe, so losing it
        # means the PR itself could not be read.
        pr = "39"
        self.args = [pr]
        proc, _ = self.forbidden(pr, {HEAD_OID(pr): ""},
                                 exits={HEAD_OID(pr): 1},
                                 stderrs={HEAD_OID(pr): "gh: boom\n"})

        self.assertEqual(proc.returncode, 4)
        self.assertIn("verdict: ERROR\n", proc.stdout)
        self.assertIn(f"detail: could not read PR #{pr}: ", proc.stdout)
        self.assertNotIn("head_sha:", proc.stdout)

    def test_a_number_only_read_is_not_accepted_as_proof_the_pr_exists(self):
        # `gh pr view N --json number` answers {"number": N} locally without
        # ever reaching GitHub, so it succeeds for a PR that does not exist.
        # Nothing may treat it as evidence the PR is readable.
        pr = "40"
        self.args = [pr]
        proc, calls = run_script(
            [pr],
            {("pr", "view", pr): ""},
            exits={("pr", "view", pr): 1},
            stderrs={("pr", "view", pr):
                     "GraphQL: Could not resolve to a PullRequest\n"},
        )

        self.assertEqual(proc.returncode, 4)
        self.assertIn(f"detail: could not read PR #{pr}: ", proc.stdout)
        self.assertEqual(
            [c for c in calls if c[:5] == ["pr", "view", pr, "--json", "number"]],
            [])


if __name__ == "__main__":
    unittest.main()
