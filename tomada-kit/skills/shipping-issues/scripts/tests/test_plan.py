#!/usr/bin/env python3
"""Tests for plan.py. Stdlib-only (unittest).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the shipping-issues skill directory)

plan.py's job is to be the *only* call a run's startup makes, so what these
tests care about most is: does one invocation produce a usable plan, does the
grouping degrade honestly when issues do not declare what they touch, and does
it refuse to promise parallelism the repo cannot deliver.
"""
from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plan  # noqa: E402

PREFLIGHT = """git_repo: ok
repo_root: /repo
git_common_dir: /repo/.git
in_worktree: no
origin: git@github.com:acme/widgets.git
repo_slug: acme/widgets
default_branch: main
runstate: /state/acme__widgets
pkg_manager: pnpm
lockfile: pnpm-lock.yaml
lockfile_hash: abc123def456
verify_command: pnpm run verify
verify_source: package.json:scripts.verify
hooks: lefthook
gh_auth: ok
gh_write: yes
worktree_viable: unknown
profile_cache: WRITTEN
current_branch: main
working_tree: clean
verdict: READY
"""


def rank_row(number, tier="P1", readiness="READY", touches=None, title=None,
             depends=(), unblocks=()):
    return {
        "number": number, "title": title or f"fix(core): thing {number}",
        "score": 5, "tier": tier, "contract_tier": None,
        "confirmed_tier": tier, "suggested_tier": tier, "effective_tier": tier,
        "readiness": readiness, "reasons": ["label:bug(+3)"],
        "touches": list(touches or []), "area": None,
        "depends_on_open": list(depends), "unblocks_open": list(unblocks),
    }


def digest_payload(rows, needs_design=(), issues=None, stale_dependency=None):
    """`stale_dependency`, when given, maps issue number -> the stale label
    names it carries, and only affects the default `issues` records built
    here (an explicit `issues=` overrides it entirely, same as it does with
    `needs_design`'s design_labels)."""
    stale_dependency = stale_dependency or {}
    return {
        "open_issue_count": len(rows), "open_pr_count": 0, "cache": "MISS",
        "label_coverage": {"labeled": len(rows), "contract_ranked": 0,
                           "total": len(rows), "complete": True,
                           "unlabeled": [], "unranked": []},
        "contract_coverage": {"full": 0, "partial": 0, "total": len(rows),
                              "missing": [r["number"] for r in rows],
                              "incomplete": {}},
        "needs_design": list(needs_design),
        "stale_dependency_labels": sorted(stale_dependency),
        "ranking": rows,
        "issues": issues if issues is not None else [
            {"number": n, "labels": ["bug"],
             "stale_dependency_labels": stale_dependency.get(n, [])}
            for n in sorted({r["number"] for r in rows} | set(stale_dependency))],
    }


class SlugTest(unittest.TestCase):
    def test_drops_the_conventional_commit_prefix(self):
        self.assertEqual(plan.slugify("fix(test): the handler keys off env"),
                         "the-handler-keys-off-env")

    def test_truncates_on_a_word_boundary(self):
        slug = plan.slugify("a" * 10 + " " + "b" * 60)
        self.assertLessEqual(len(slug), 40)
        self.assertFalse(slug.endswith("-"))

    def test_non_ascii_title_yields_an_empty_slug_not_mojibake(self):
        self.assertEqual(plan.slugify("テストを直す"), "")

    def test_branch_name_takes_type_from_the_title(self):
        row = rank_row(85, title="fix(test): composed handler")
        self.assertEqual(plan.branch_name(row, []), "fix/85-composed-handler")

    def test_branch_name_falls_back_to_labels_then_chore(self):
        row = rank_row(85, title="Composed handler is wrong")
        self.assertEqual(plan.branch_name(row, ["bug"]), "fix/85-composed-handler-is-wrong")
        self.assertTrue(plan.branch_name(row, []).startswith("chore/85-"))

    def test_branch_name_survives_a_title_with_no_usable_slug(self):
        self.assertEqual(plan.branch_name(rank_row(7, title="日本語"), []), "chore/7")


class PathCollisionTest(unittest.TestCase):
    def test_identical_and_prefix_paths_collide(self):
        self.assertTrue(plan.paths_collide(["src/"], ["src/"]))
        self.assertTrue(plan.paths_collide(["src/"], ["src/api/handler.ts"]))

    def test_disjoint_paths_do_not(self):
        self.assertFalse(plan.paths_collide(["src/api/"], ["tests/unit/"]))

    def test_a_star_collides_with_everything(self):
        self.assertTrue(plan.paths_collide(["*"], ["tests/"]))
        self.assertTrue(plan.paths_collide(["tests/"], ["*"]))

    def test_the_same_directory_written_differently_still_collides(self):
        # The failure that matters: two issues editing one directory land in the
        # same batch and meet again as a merge conflict.
        for a, b in ((["./src/"], ["src/"]), (["src"], ["src/"]),
                     (["/src/api"], ["src/api/"]), (["src/api/"], ["src/"])):
            with self.subTest(a=a, b=b):
                self.assertTrue(plan.paths_collide(a, b))

    def test_a_shared_prefix_that_is_not_a_shared_directory_does_not_collide(self):
        self.assertFalse(plan.paths_collide(["src/"], ["src2/"]))
        self.assertFalse(plan.paths_collide(["lib"], ["library"]))

    def test_a_file_and_its_directory_collide(self):
        self.assertTrue(plan.paths_collide(["src/api/handler.ts"], ["src/api/"]))

    def test_an_undeclared_side_does_not_collide_on_its_own(self):
        # Emptiness is handled by the PARTIAL confidence signal, not by
        # pretending an unknown is a conflict — otherwise no repo without
        # contracts could ever group.
        self.assertFalse(plan.paths_collide([], ["tests/"]))


class GroupBatchesTest(unittest.TestCase):
    def test_disjoint_issues_share_a_batch_and_report_mechanical(self):
        rows = [rank_row(1, touches=["src/a/"]), rank_row(2, touches=["src/b/"])]
        batches, confidence, undeclared = plan.group_batches(rows, 3)
        self.assertEqual([[r["number"] for r in b] for b in batches], [[1, 2]])
        self.assertEqual(confidence, "MECHANICAL")
        self.assertEqual(undeclared, [])

    def test_colliding_issues_split_into_consecutive_batches(self):
        rows = [rank_row(1, touches=["src/"]), rank_row(2, touches=["src/api/"])]
        batches, _, _ = plan.group_batches(rows, 3)
        self.assertEqual([[r["number"] for r in b] for b in batches], [[1], [2]])

    def test_max_parallel_caps_the_batch(self):
        rows = [rank_row(n, touches=[f"src/{n}/"]) for n in range(1, 6)]
        batches, _, _ = plan.group_batches(rows, 2)
        self.assertEqual([len(b) for b in batches], [2, 2, 1])

    def test_a_raised_cap_is_honoured(self):
        rows = [rank_row(n, touches=[f"src/{n}/"]) for n in range(1, 11)]
        batches, _, _ = plan.group_batches(rows, 10)
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]), 10)

    def test_dependency_edges_split_a_batch_even_with_disjoint_paths(self):
        rows = [rank_row(1, touches=["src/a/"], unblocks=[2]),
                rank_row(2, touches=["src/b/"], depends=[1])]
        batches, _, _ = plan.group_batches(rows, 3)
        self.assertEqual([[r["number"] for r in b] for b in batches], [[1], [2]])

    def test_an_undeclared_issue_makes_the_lead_batch_partial(self):
        rows = [rank_row(1, touches=["src/a/"]), rank_row(2)]
        batches, confidence, undeclared = plan.group_batches(rows, 3)
        self.assertEqual(confidence, "PARTIAL")
        self.assertEqual(undeclared, [2])

    def test_one_ready_issue_is_serial(self):
        _, confidence, _ = plan.group_batches([rank_row(1, touches=["a/"])], 3)
        self.assertEqual(confidence, "SERIAL")

    def test_no_ready_issue_is_serial_and_empty(self):
        batches, confidence, _ = plan.group_batches([], 3)
        self.assertEqual(batches, [])
        self.assertEqual(confidence, "SERIAL")


class MainTest(unittest.TestCase):
    """main() with preflight.sh and issue_digest.py stubbed at the run()
    boundary — the two are covered by their own test modules, and what matters
    here is how plan.py combines them."""

    def _run(self, argv, rows, preflight=PREFLIGHT, preflight_rc=0,
             needs_design=(), issues=None, worktrees=(), worktree_paths=(),
             stale_dependency=None):
        self.recorded: list[list[str]] = []
        paths = [f"/state/acme__widgets/worktrees/{n}" for n in worktrees]
        paths += list(worktree_paths)
        self.worktree_list = "".join(
            f"worktree {path}\nHEAD abc\n\n" for path in paths)
        payload = json.dumps(
            digest_payload(rows, needs_design, issues, stale_dependency))

        self.preflight_calls: list[list[str]] = []

        def fake_run(cmd):
            if cmd[:2] == ["git", "worktree"]:
                return 0, self.worktree_list, ""
            name = Path(cmd[0]).name if cmd[0] != sys.executable else Path(cmd[1]).name
            if name == "preflight.sh":
                self.preflight_calls.append(cmd)
                return preflight_rc, preflight, ""
            if name == "issue_digest.py":
                self.digest_cmd = cmd
                return 0, payload, ""
            if name == "run_record.py":
                self.recorded.append(cmd)
                return 0, "", ""
            raise AssertionError(f"unexpected command: {cmd}")

        out, err = io.StringIO(), io.StringIO()
        with patch.object(plan, "run", fake_run), \
                patch.object(sys, "argv", ["plan.py", *argv]), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                rc = plan.main()
            except SystemExit as exc:
                rc = exc.code
        return rc, out.getvalue(), err.getvalue()

    def test_single_mode_prints_a_serial_plan_with_a_branch_command(self):
        rc, out, err = self._run([], [rank_row(85, touches=["src/a/"])])
        self.assertEqual(rc, 0, err)
        self.assertIn("plan: serial", out)
        self.assertIn("select: #85", out)
        self.assertIn("git switch -c fix/85-thing-85", out)
        self.assertIn("verdict: READY", out)

    def test_all_mode_emits_one_ready_to_run_worktree_command(self):
        rows = [rank_row(85, touches=["src/a/"]), rank_row(106, touches=["src/b/"])]
        rc, out, err = self._run(["--mode", "all"], rows)
        self.assertEqual(rc, 0, err)
        self.assertIn("plan: parallel", out)
        self.assertIn("grouping: MECHANICAL", out)
        self.assertIn("--spec 85:fix/85-thing-85", out)
        self.assertIn("--spec 106:fix/106-thing-106", out)
        self.assertIn('--verify "pnpm run verify"', out)

    def test_the_next_command_never_decides_viability_for_the_caller(self):
        rows = [rank_row(1, touches=["a/"]), rank_row(2, touches=["b/"])]
        rc, out, err = self._run(["--mode", "all"], rows)
        self.assertIn('--verify "pnpm run verify"', out)
        self.assertNotIn("--gate-first", out)
        self.assertIn("PROPOSAL, not a decision", out)

    def test_the_verify_command_is_flagged_for_confirmation(self):
        rc, out, err = self._run([], [rank_row(1, touches=["a/"])])
        self.assertIn("verify-check: 'pnpm run verify'", out)
        self.assertIn("package.json:scripts.verify", out)
        self.assertIn("confirm it is this repo's real gate", out)

    def test_no_verify_command_says_so_rather_than_going_quiet(self):
        pre = PREFLIGHT.replace("verify_command: pnpm run verify",
                                "verify_command: NONE")
        rc, out, err = self._run([], [rank_row(1, touches=["a/"])], preflight=pre)
        self.assertIn("verify-check: NONE found", out)

    def test_a_missing_preflight_key_stops_the_run(self):
        # The silent version of this used to drop --verify from the batch
        # command, removing the baseline check with no message at all.
        pre = "\n".join(l for l in PREFLIGHT.splitlines()
                        if not l.startswith("verify_command:")) + "\n"
        rc, out, err = self._run([], [rank_row(1, touches=["a/"])], preflight=pre)
        self.assertEqual(rc, 1)
        self.assertIn("preflight-keys-missing: verify_command", out)
        self.assertIn("verdict: BLOCKED", out)

    def test_a_known_unviable_repo_is_forced_serial(self):
        rows = [rank_row(1, touches=["a/"]), rank_row(2, touches=["b/"])]
        pre = PREFLIGHT.replace("worktree_viable: unknown", "worktree_viable: no")
        rc, out, err = self._run(["--mode", "all"], rows, preflight=pre)
        self.assertIn("plan: serial", out)
        self.assertNotIn("--spec", out)

    def test_partial_grouping_is_flagged_as_a_proposal(self):
        rows = [rank_row(1, touches=["a/"]), rank_row(2)]
        rc, out, err = self._run(["--mode", "all"], rows)
        self.assertIn("grouping: PARTIAL", out)
        self.assertIn("no touches= on #2", out)
        self.assertIn("PROPOSAL, not a decision", out)

    def test_max_parallel_reaches_the_grouping(self):
        rows = [rank_row(n, touches=[f"src/{n}/"]) for n in range(1, 11)]
        rc, out, err = self._run(["--mode", "all", "--max-parallel", "10"], rows)
        self.assertIn("max-parallel 10", out)
        self.assertIn("--spec 10:", out)

    def test_light_mode_filters_on_the_light_label_and_groups_like_all(self):
        rows = [rank_row(1, touches=["src/a/"]), rank_row(2, touches=["src/b/"])]
        rc, out, err = self._run(["--mode", "light"], rows)
        self.assertEqual(rc, 0, err)
        i = self.digest_cmd.index("--label")
        self.assertEqual(self.digest_cmd[i + 1], plan.LIGHT_LABEL)
        self.assertIn("plan: parallel", out)
        self.assertIn("--spec 1:", out)
        self.assertIn("--spec 2:", out)

    def test_light_mode_does_not_repeat_a_label_the_caller_passed(self):
        rc, _, err = self._run(["--mode", "light", "--label", plan.LIGHT_LABEL],
                               [rank_row(1)])
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.digest_cmd.count(plan.LIGHT_LABEL), 1)

    @staticmethod
    def _labels(light, rows):
        return [{"number": r["number"],
                 "labels": ["bug", plan.LIGHT_LABEL] if r["number"] in light
                 else ["bug"]} for r in rows]

    def test_all_mode_defers_a_light_issue_nothing_heavier_waits_on(self):
        rows = [rank_row(1, touches=["a/"]), rank_row(2, touches=["b/"])]
        rc, out, err = self._run(["--mode", "all"], rows,
                                 issues=self._labels({2}, rows))
        self.assertEqual(rc, 0, err)
        self.assertIn("deferred-light: #2", out)
        self.assertIn("select: #1", out)
        self.assertNotIn("#2[", out)

    def test_no_argument_defers_a_light_issue_even_when_it_ranks_first(self):
        rows = [rank_row(1, tier="P0", touches=["a/"]),
                rank_row(2, tier="P1", touches=["b/"])]
        rc, out, err = self._run([], rows, issues=self._labels({1}, rows))
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #2", out)
        self.assertIn("deferred-light: #1", out)

    def test_a_light_issue_a_heavier_one_waits_on_is_kept(self):
        rows = [rank_row(1, touches=["a/"], unblocks=[3]),
                rank_row(3, readiness="BLOCKED-BY:#1", depends=[1])]
        rc, out, err = self._run(["--mode", "all"], rows,
                                 issues=self._labels({1}, rows))
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #1", out)
        self.assertNotIn("deferred-light", out)

    def test_a_chain_of_light_issues_ending_in_a_heavier_one_is_kept(self):
        rows = [rank_row(1, touches=["a/"], unblocks=[2]),
                rank_row(2, readiness="BLOCKED-BY:#1", depends=[1], unblocks=[3]),
                rank_row(3, readiness="BLOCKED-BY:#2", depends=[2])]
        rc, out, err = self._run(["--mode", "all"], rows,
                                 issues=self._labels({1, 2}, rows))
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #1", out)
        self.assertNotIn("deferred-light", out)

    def test_a_light_issue_only_light_ones_wait_on_is_deferred(self):
        rows = [rank_row(1, touches=["a/"], unblocks=[2]),
                rank_row(2, readiness="BLOCKED-BY:#1", depends=[1]),
                rank_row(3, touches=["c/"])]
        rc, out, err = self._run(["--mode", "all"], rows,
                                 issues=self._labels({1, 2}, rows))
        self.assertEqual(rc, 0, err)
        self.assertIn("deferred-light: #1", out)
        self.assertIn("select: #3", out)

    def test_include_light_takes_them_anyway(self):
        rows = [rank_row(1, touches=["a/"]), rank_row(2, touches=["b/"])]
        rc, out, err = self._run(["--mode", "all", "--include-light"], rows,
                                 issues=self._labels({2}, rows))
        self.assertEqual(rc, 0, err)
        self.assertNotIn("deferred-light", out)
        self.assertIn("--spec 2:", out)

    def test_light_mode_never_defers_the_issues_it_exists_to_ship(self):
        rows = [rank_row(1, touches=["a/"])]
        rc, out, err = self._run(["--mode", "light"], rows,
                                 issues=self._labels({1}, rows))
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #1", out)
        self.assertNotIn("deferred-light", out)

    def test_a_named_light_issue_is_taken(self):
        rows = [rank_row(1, touches=["a/"]), rank_row(42, touches=["b/"])]
        rc, out, err = self._run(["--mode", "42"], rows,
                                 issues=self._labels({42}, rows))
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #42", out)
        self.assertNotIn("deferred-light", out)

    def test_explicit_issue_number_selects_only_that_issue(self):
        rows = [rank_row(1, touches=["a/"]), rank_row(42, touches=["b/"])]
        rc, out, err = self._run(["--mode", "42"], rows)
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #42", out)
        self.assertIn("plan: serial", out)
        self.assertIn("--include-design", self.digest_cmd)

    def test_nothing_ready_says_so_instead_of_proposing_a_branch(self):
        rows = [rank_row(1, readiness="BLOCKED-BY:#2")]
        rc, out, err = self._run([], rows)
        self.assertEqual(rc, 0, err)
        self.assertIn("select: none", out)
        self.assertIn("nothing to ship", out)
        self.assertIn("held: #1 BLOCKED-BY:#2", out)

    def test_design_blocked_issues_are_pointed_at_step_8b(self):
        rows = [rank_row(1, touches=["a/"])]
        rc, out, err = self._run([], rows, needs_design=[7, 9])
        self.assertIn("needs-design: #7,#9", out)
        self.assertIn("step 8b", out)

    def test_stale_dependency_labels_print_the_clear_command(self):
        rows = [rank_row(1, touches=["a/"])]
        rc, out, err = self._run(
            [], rows,
            stale_dependency={12: ["blocked: dependency"], 15: ["blocked: dependency"]})
        self.assertIn(
            "stale-labels: #12,#15 → blocked: dependency with every "
            "dependency closed; clear with apply_priority_labels.py "
            "--clear-dependency 12 --clear-dependency 15",
            out,
        )

    def test_no_stale_dependency_labels_prints_nothing(self):
        rows = [rank_row(1, touches=["a/"])]
        rc, out, err = self._run([], rows)
        self.assertNotIn("stale-labels:", out)

    def test_blocked_preflight_stops_the_run(self):
        rc, out, err = self._run([], [rank_row(1)],
                                 preflight="git_repo: NOT_A_REPO\nverdict: BLOCKED\n",
                                 preflight_rc=1)
        self.assertEqual(rc, 1)
        self.assertIn("verdict: BLOCKED", out)

    def test_record_writes_run_start_selection_and_the_group(self):
        rows = [rank_row(1, touches=["a/"]), rank_row(2, touches=["b/"])]
        self._run(["--mode", "all", "--record"], rows)
        events = [cmd[cmd.index("--event") + 1] for cmd in self.recorded]
        self.assertEqual(events, ["run-start", "selection", "parallel-group"])
        self.assertIn("--repo", self.recorded[0])
        self.assertIn("acme/widgets", self.recorded[0])

    def test_serial_run_records_no_parallel_group(self):
        self._run(["--record"], [rank_row(1, touches=["a/"])])
        events = [cmd[cmd.index("--event") + 1] for cmd in self.recorded]
        self.assertEqual(events, ["run-start", "selection"])

    def test_refresh_is_passed_through_to_the_digest(self):
        self._run(["--refresh"], [rank_row(1)])
        self.assertIn("--refresh", self.digest_cmd)

    def test_json_output_carries_the_batches_and_branches(self):
        rows = [rank_row(1, touches=["a/"]), rank_row(2, touches=["b/"])]
        rc, out, err = self._run(["--mode", "all", "--json"], rows)
        payload = json.loads(out)
        self.assertEqual(payload["batches"], [[1, 2]])
        self.assertEqual(payload["grouping"], "MECHANICAL")
        self.assertEqual(payload["branches"]["1"], "fix/1-thing-1")
        self.assertEqual(payload["preflight"]["hooks"], "lefthook")

    def test_json_output_carries_stale_dependency_labels(self):
        rows = [rank_row(1, touches=["a/"])]
        rc, out, err = self._run(
            ["--json"], rows, stale_dependency={12: ["blocked: dependency"]})
        payload = json.loads(out)
        self.assertEqual(payload["stale_dependency_labels"], [12])

    def test_the_github_probe_is_paid_for_once(self):
        # preflight is called twice — the first call is what reveals where the
        # profile cache lives — but only the second one may reach GitHub.
        self._run([], [rank_row(1, touches=["a/"])])
        self.assertEqual(len(self.preflight_calls), 2)
        self.assertNotIn("--with-github", self.preflight_calls[0])
        self.assertIn("--with-github", self.preflight_calls[1])
        self.assertIn("/state/acme__widgets/repo-profile.json",
                      self.preflight_calls[1])

    def test_leftover_worktrees_stop_the_opening_plan(self):
        rc, out, err = self._run([], [rank_row(1, touches=["a/"])],
                                 worktrees=[90, 94])
        self.assertEqual(rc, 1)
        self.assertIn("existing-worktrees: 90, 94", out)
        self.assertIn("verdict: BLOCKED", out)
        self.assertNotIn("select:", out)

    def test_a_re_plan_may_carry_its_own_worktrees(self):
        rc, out, err = self._run(["--allow-existing-worktrees"],
                                 [rank_row(1, touches=["a/"])], worktrees=[90])
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #1", out)

    def test_worktrees_outside_this_runs_root_are_not_leftovers(self):
        # The developer's own worktree elsewhere on disk, plus the main
        # checkout git always lists first: neither is this run's business.
        rc, out, err = self._run([], [rank_row(1, touches=["a/"])],
                                 worktree_paths=["/repo",
                                                 "/somewhere/else/feature-x"])
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #1", out)

    def test_bad_mode_is_a_usage_error(self):
        rc, out, err = self._run(["--mode", "sometimes"], [rank_row(1)])
        self.assertEqual(rc, 2)
        self.assertIn("--mode takes", err)

    def test_zero_max_parallel_is_a_usage_error(self):
        rc, out, err = self._run(["--max-parallel", "0"], [rank_row(1)])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
