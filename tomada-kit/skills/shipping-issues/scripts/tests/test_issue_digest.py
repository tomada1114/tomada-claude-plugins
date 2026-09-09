#!/usr/bin/env python3
"""Tests for issue_digest.py. Stdlib-only (unittest).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the shipping-issues skill directory)
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _fakegh import FakeGh  # noqa: E402
import issue_digest as idg  # noqa: E402


def gh_issue(number, title="issue", labels=None, body="", updated=None,
             created=None, milestone=None, assignees=None):
    updated = updated or "2026-01-01T00:00:00Z"
    created = created or updated
    return {
        "number": number, "title": title,
        "labels": [{"name": n} for n in (labels or [])],
        "assignees": [{"login": a} for a in (assignees or [])],
        "milestone": {"title": milestone} if milestone else None,
        "body": body, "createdAt": created, "updatedAt": updated,
        "url": f"https://github.com/acme/widgets/issues/{number}",
    }


def gh_pr(number, title="pr", body="", head="feature", draft=False):
    return {"number": number, "title": title, "body": body,
            "headRefName": head, "isDraft": draft,
            "url": f"https://github.com/acme/widgets/pull/{number}"}


class NormalizeLabelTest(unittest.TestCase):
    def test_collapses_separators_and_case(self):
        self.assertEqual(idg.normalize_label("Priority: P0"), "priority:p0")
        self.assertEqual(idg.normalize_label("priority/P0"), "priority:p0")
        self.assertEqual(idg.normalize_label(" p0 "), "p0")


class SqueezeTest(unittest.TestCase):
    def test_zero_limit_returns_empty(self):
        self.assertEqual(idg.squeeze("hello world", 0), "")

    def test_none_text_returns_empty(self):
        self.assertEqual(idg.squeeze(None, 100), "")

    def test_strips_html_comments_and_images(self):
        text = "before <!-- hidden --> ![alt](x.png) after"
        self.assertEqual(idg.squeeze(text, 100), "before after")

    def test_collapses_code_blocks(self):
        text = "see\n```\ndef f(): pass\n```\ndone"
        self.assertIn("[code block]", idg.squeeze(text, 200))

    def test_demotes_headings(self):
        text = "# Title\nbody"
        self.assertTrue(idg.squeeze(text, 200).startswith("▸ Title"))

    def test_truncates_over_limit(self):
        text = "x" * 50
        out = idg.squeeze(text, 10)
        self.assertTrue(out.endswith("…[truncated]"))
        self.assertLessEqual(len(out) - len(" …[truncated]"), 10)


class ExtractDepsTest(unittest.TestCase):
    def test_depends_on_pattern(self):
        deps = idg.extract_deps("blocked by #5", "t", self_number=1)
        self.assertEqual(deps["depends_on"], [5])

    def test_blocks_pattern(self):
        deps = idg.extract_deps("this blocks #9", "t", self_number=1)
        self.assertEqual(deps["blocks"], [9])

    def test_self_reference_excluded(self):
        deps = idg.extract_deps("depends on #1", "t", self_number=1)
        self.assertEqual(deps["depends_on"], [])

    def test_bare_reference_becomes_mention(self):
        deps = idg.extract_deps("see #7 for context", "t", self_number=1)
        self.assertEqual(deps["mentions"], [7])
        self.assertEqual(deps["depends_on"], [])

    def test_bare_reference_not_double_counted_with_explicit(self):
        deps = idg.extract_deps("depends on #5, see also #5", "t", self_number=1)
        self.assertEqual(deps["depends_on"], [5])
        self.assertEqual(deps["mentions"], [])

    def test_japanese_dependency_phrasing(self):
        deps = idg.extract_deps("#5 に依存", "t", self_number=1)
        self.assertEqual(deps["depends_on"], [5])


class DaysSinceTest(unittest.TestCase):
    def test_recent_date_is_zero_or_more(self):
        today = _dt.date.today().isoformat()
        self.assertEqual(idg.days_since(today), 0)

    def test_invalid_date_returns_none(self):
        self.assertIsNone(idg.days_since("not-a-date"))

    def test_none_returns_none(self):
        self.assertIsNone(idg.days_since(None))


class CanonicalTierTest(unittest.TestCase):
    def test_no_label_returns_none(self):
        self.assertIsNone(idg.canonical_tier(["bug"]))

    def test_recognizes_canonical_and_alias(self):
        self.assertEqual(idg.canonical_tier(["priority: P1"]), "P1")
        self.assertEqual(idg.canonical_tier(["critical"]), "P0")

    def test_highest_tier_wins_when_both_present(self):
        self.assertEqual(idg.canonical_tier(["priority: P2", "critical"]), "P0")


class SuggestTierTest(unittest.TestCase):
    def _rec(self, unblocks_open=()):
        return {"unblocks_open": list(unblocks_open)}

    def test_unblocking_others_is_p0(self):
        tier, reason = idg.suggest_tier(self._rec(unblocks_open=[3]), set(), 0)
        self.assertEqual(tier, "P0")
        self.assertIn("unblocks", reason)

    def test_urgent_leverage_is_p0(self):
        tier, reason = idg.suggest_tier(self._rec(), {"security"}, 0)
        self.assertEqual(tier, "P0")
        self.assertEqual(reason, "security")

    def test_high_score_alone_is_p0(self):
        tier, reason = idg.suggest_tier(self._rec(), set(), idg.SUGGEST_P0_SCORE)
        self.assertEqual(tier, "P0")

    def test_foundation_leverage_is_p1(self):
        tier, reason = idg.suggest_tier(self._rec(), {"schema"}, 0)
        self.assertEqual(tier, "P1")

    def test_mid_score_is_p1(self):
        tier, _ = idg.suggest_tier(self._rec(), set(), idg.SUGGEST_P1_SCORE)
        self.assertEqual(tier, "P1")

    def test_low_positive_score_is_p2(self):
        tier, _ = idg.suggest_tier(self._rec(), set(), idg.SUGGEST_P2_SCORE)
        self.assertEqual(tier, "P2")

    def test_zero_score_is_p3(self):
        tier, _ = idg.suggest_tier(self._rec(), set(), 0)
        self.assertEqual(tier, "P3")


class ScoreIssueTest(unittest.TestCase):
    def _base_rec(self, **over):
        # Neither stale (>= STALE_DAYS) nor fresh (<= FRESH_DAYS): a neutral
        # age so the staleness/freshness bonus never perturbs the assertions
        # below, which are about the *other* scoring inputs.
        neutral = (_dt.date.today() - _dt.timedelta(days=90)).isoformat()
        rec = {"unblocks_open": [], "referenced_by_open": [], "labels": [],
               "title": "t", "milestone": None, "updated_at": neutral}
        rec.update(over)
        return rec

    def test_unblocks_scored_and_capped(self):
        rec = self._base_rec(unblocks_open=[1, 2, 3])
        score, parts, hits = idg.score_issue(rec, "")
        self.assertEqual(score, idg.UNBLOCK_POINTS * 3)
        self.assertTrue(any("unblocks" in p for p in parts))

    def test_unblocks_capped_at_ceiling(self):
        rec = self._base_rec(unblocks_open=list(range(10)))
        score, _, _ = idg.score_issue(rec, "")
        self.assertEqual(score, idg.UNBLOCK_CAP)

    def test_tier_label_does_not_add_score(self):
        rec = self._base_rec(labels=["priority: P0"])
        score, parts, _ = idg.score_issue(rec, "")
        self.assertEqual(score, 0)
        self.assertEqual(parts, [])

    def test_weighted_label_adds_score(self):
        rec = self._base_rec(labels=["bug"])
        score, parts, _ = idg.score_issue(rec, "")
        self.assertEqual(score, idg.PRIORITY_LABEL_WEIGHTS["bug"])

    def test_leverage_keyword_detected_and_capped(self):
        rec = self._base_rec(title="fix CVE-2026-1 injection vulnerability")
        score, parts, hits = idg.score_issue(rec, "")
        self.assertIn("security", hits)
        self.assertLessEqual(score, idg.LEVERAGE_CAP)

    def test_milestone_adds_two(self):
        rec = self._base_rec(milestone="v1")
        score, parts, _ = idg.score_issue(rec, "")
        self.assertEqual(score, 2)

    def test_stale_issue_penalized(self):
        old = (_dt.date.today() - _dt.timedelta(days=idg.STALE_DAYS + 1)).isoformat()
        rec = self._base_rec(updated_at=old)
        score, parts, _ = idg.score_issue(rec, "")
        self.assertEqual(score, -1)

    def test_fresh_issue_rewarded(self):
        recent = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
        rec = self._base_rec(updated_at=recent)
        score, parts, _ = idg.score_issue(rec, "")
        self.assertEqual(score, 1)


class TierCellTest(unittest.TestCase):
    def test_no_label_shows_suggestion_only(self):
        rec = {"priority_tier": None, "suggested_tier": "P1"}
        self.assertEqual(idg.tier_cell(rec), "~P1")

    def test_matching_label_shown_plain(self):
        rec = {"priority_tier": "P1", "suggested_tier": "P1"}
        self.assertEqual(idg.tier_cell(rec), "P1")

    def test_label_lower_than_suggestion_shows_both(self):
        rec = {"priority_tier": "P2", "suggested_tier": "P0"}
        self.assertEqual(idg.tier_cell(rec), "P2(~P0)")

    def test_label_higher_than_suggestion_shown_plain(self):
        rec = {"priority_tier": "P0", "suggested_tier": "P2"}
        self.assertEqual(idg.tier_cell(rec), "P0")


class ReadinessTest(unittest.TestCase):
    def test_blocked_by_wins_over_everything(self):
        rec = {"depends_on_open": [3], "not_ready_labels": ["blocked"],
               "design_labels": [], "open_pr": {"number": 1}}
        self.assertEqual(idg.readiness(rec), "BLOCKED-BY:#3")

    def test_not_ready_label_next(self):
        rec = {"depends_on_open": [], "not_ready_labels": ["question"],
               "design_labels": [], "open_pr": {"number": 1}}
        self.assertEqual(idg.readiness(rec), "LABEL:question")

    def test_open_pr_next(self):
        rec = {"depends_on_open": [], "not_ready_labels": [],
               "design_labels": [], "open_pr": {"number": 7}}
        self.assertEqual(idg.readiness(rec), "HAS-PR:#7")

    def test_ready_when_nothing_blocks(self):
        rec = {"depends_on_open": [], "not_ready_labels": [],
               "design_labels": [], "open_pr": None}
        self.assertEqual(idg.readiness(rec), "READY")

    def test_design_label_blocks_by_default(self):
        rec = {"depends_on_open": [], "not_ready_labels": [],
               "design_labels": ["blocked: design"], "open_pr": None}
        self.assertEqual(idg.readiness(rec), "DESIGN:blocked: design")

    def test_design_label_wins_over_open_pr(self):
        rec = {"depends_on_open": [], "not_ready_labels": [],
               "design_labels": ["needs-design"], "open_pr": {"number": 7}}
        self.assertEqual(idg.readiness(rec), "DESIGN:needs-design")

    def test_not_ready_label_wins_over_design_label(self):
        rec = {"depends_on_open": [], "not_ready_labels": ["blocked"],
               "design_labels": ["blocked: design"], "open_pr": None}
        self.assertEqual(idg.readiness(rec), "LABEL:blocked")

    def test_allow_design_treats_design_label_as_ready(self):
        rec = {"depends_on_open": [], "not_ready_labels": [],
               "design_labels": ["blocked: design"], "open_pr": None}
        self.assertEqual(idg.readiness(rec, allow_design=True), "READY")

    def test_allow_design_still_respects_open_pr(self):
        rec = {"depends_on_open": [], "not_ready_labels": [],
               "design_labels": ["blocked: design"], "open_pr": {"number": 7}}
        self.assertEqual(idg.readiness(rec, allow_design=True), "HAS-PR:#7")


class DesignBlockLabelsTest(unittest.TestCase):
    def test_normalized_equivalents_all_recognized(self):
        for name in ("blocked: design", "Blocked: Design", "blocked/design",
                     "needs design", "needs-design", "needs:design",
                     "design-needed"):
            self.assertIn(idg.normalize_label(name), idg.DESIGN_BLOCK_LABELS,
                          f"{name!r} should be a recognized design-block label")

    def test_unrelated_label_not_recognized(self):
        self.assertNotIn(idg.normalize_label("bug"), idg.DESIGN_BLOCK_LABELS)


class ResolveDesignLabelTest(unittest.TestCase):
    def test_canonical_present_is_reused(self):
        name, needs_create = idg.resolve_design_label(["blocked: design", "bug"])
        self.assertEqual(name, "blocked: design")
        self.assertFalse(needs_create)

    def test_alias_present_is_reused_not_duplicated(self):
        name, needs_create = idg.resolve_design_label(["needs-design"])
        self.assertEqual(name, "needs-design")
        self.assertFalse(needs_create)

    def test_shortest_alias_wins_when_repo_carries_several(self):
        name, needs_create = idg.resolve_design_label(
            ["needs design", "needs-design", "design-needed"])
        # "needs design"/"needs-design" tie on length (12); the tie-break is
        # plain string ordering (min()'s documented behavior) rather than a
        # meaningful preference, and a space sorts before a hyphen.
        self.assertEqual(name, "needs design")
        self.assertFalse(needs_create)

    def test_no_equivalent_creates_canonical(self):
        name, needs_create = idg.resolve_design_label(["bug", "priority: P0"])
        self.assertEqual(name, "blocked: design")
        self.assertTrue(needs_create)


class DigestRunner:
    """Runs main() in-process (not via subprocess) against a fake `gh` on
    PATH, so coverage sees the code these tests exercise. Only the external
    `gh` process itself is out of process — issue_digest.py's own code runs
    in this interpreter.

    A mixin rather than a base TestCase: several classes below need `_run`, and
    inheriting it from a TestCase would re-run that class's own tests inside
    each of them."""

    def _run(self, args, issues, prs=None, path_override=None,
             state_dir=None, cache=False):
        """Run main() once. `cache=True` re-enables the digest cache (FakeGh
        disables it by default) and `state_dir` pins where it lives, so a test
        can drive two calls through one cache and count the gh invocations."""
        responses = {
            ("issue", "list"): json.dumps(issues),
            ("pr", "list"): json.dumps(prs or []),
        }
        with FakeGh(responses) as fake:
            env = dict(fake.env)
            if path_override is not None:
                env["PATH"] = path_override
            if cache:
                env.pop("SHIPPING_ISSUES_NO_CACHE", None)
            if state_dir is not None:
                env["AGENT_SKILL_STATE_DIR"] = str(state_dir)
            self.last_calls = fake
            out, err = io.StringIO(), io.StringIO()
            with patch.dict("os.environ", env, clear=False), \
                    patch.object(sys, "argv", ["issue_digest.py", *args]), \
                    redirect_stdout(out), redirect_stderr(err):
                try:
                    rc = idg.main()
                except SystemExit as exc:
                    rc = exc.code
            self.gh_calls = fake.calls
        return rc, out.getvalue(), err.getvalue()


class MainEndToEndTest(DigestRunner, unittest.TestCase):
    def test_select_reports_top_ready_issue(self):
        issues = [
            gh_issue(1, title="unlabeled small thing"),
            gh_issue(2, title="ship now", labels=["priority: P0"]),
        ]
        rc, out, err = self._run(["--select", "--json"], issues)
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["ranking"][0]["number"], 2)
        self.assertEqual(payload["ranking"][0]["tier"], "P0")

    def test_select_text_output_names_the_pick(self):
        issues = [gh_issue(2, title="ship now", labels=["priority: P0"])]
        rc, out, err = self._run(["--select"], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #2", out)

    def test_blocked_issue_is_never_selected(self):
        issues = [
            gh_issue(1, title="blocked one", labels=["priority: P0"],
                     body="depends on #2"),
            gh_issue(2, title="the blocker", labels=["priority: P3"]),
        ]
        rc, out, err = self._run(["--select"], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #2", out)
        self.assertNotIn("select: #1", out)

    def test_design_labeled_issue_excluded_from_select_by_default(self):
        issues = [
            gh_issue(3, title="needs a design call", labels=["priority: P0",
                     "blocked: design"]),
            gh_issue(4, title="ready to go", labels=["priority: P2"]),
        ]
        rc, out, err = self._run(["--select"], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #4", out)
        self.assertNotIn("select: #3", out)
        self.assertIn("needs-design: #3", out)
        # Not duplicated into `held:` alongside genuinely blocked issues.
        self.assertNotIn("held:", out)

    def test_include_design_makes_it_selectable(self):
        issues = [gh_issue(3, title="needs a design call",
                            labels=["priority: P0", "blocked: design"])]
        rc, out, err = self._run(["--select", "--include-design"], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #3", out)
        self.assertNotIn("needs-design:", out)

    def test_explicit_issue_number_also_bypasses_design_block(self):
        issues = [gh_issue(3, title="needs a design call",
                            labels=["priority: P0", "blocked: design"])]
        rc, out, err = self._run(["--select", "--issue", "3"], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #3", out)

    def test_design_label_recognized_via_alias_and_normalization(self):
        issues = [gh_issue(3, title="needs a design call",
                            labels=["priority: P0", "Blocked: Design"])]
        rc, out, err = self._run(["--select"], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("needs-design: #3", out)

    def test_needs_design_flag_and_payload_field(self):
        issues = [gh_issue(3, title="needs a design call",
                            labels=["priority: P0", "blocked: design"])]
        rc, out, err = self._run(["--json"], issues)
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["needs_design"], [3])
        rec = payload["issues"][0]
        self.assertEqual(rec["design_labels"], ["blocked: design"])
        self.assertEqual(rec["readiness"], "DESIGN:blocked: design")

    def test_needs_design_flag_shown_in_markdown_output(self):
        issues = [gh_issue(3, title="needs a design call",
                            labels=["priority: P0", "blocked: design"])]
        rc, out, err = self._run([], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("NEEDS-DESIGN:blocked: design", out)

    def test_issue_filter_restricts_output_but_not_dependency_graph(self):
        issues = [
            gh_issue(1, title="alone", body="blocks #2"),
            gh_issue(2, title="other"),
        ]
        rc, out, err = self._run(["--issue", "1", "--json"], issues)
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual([r["number"] for r in payload["issues"]], [1])
        # #1 still gets credit for unblocking #2 even though #2 is filtered out.
        self.assertEqual(payload["issues"][0]["unblocks_open"], [2])

    def test_label_coverage_complete_when_all_labeled(self):
        issues = [gh_issue(1, labels=["priority: P1"])]
        rc, out, err = self._run(["--select"], issues)
        self.assertIn("COMPLETE", out)

    def test_open_pr_marks_has_open_pr_flag(self):
        issues = [gh_issue(5, title="claimed")]
        prs = [gh_pr(10, body="Closes #5")]
        rc, out, err = self._run(["--json"], issues, prs)
        payload = json.loads(out)
        rec = payload["issues"][0]
        self.assertIsNotNone(rec["open_pr"])
        self.assertEqual(rec["open_pr"]["number"], 10)

    def test_pr_draft_flag_surfaces_in_markdown(self):
        issues = [gh_issue(5, title="claimed")]
        prs = [gh_pr(10, body="Closes #5", draft=True)]
        rc, out, err = self._run([], issues, prs)
        self.assertIn("(draft)", out)

    def test_no_issues_matches_filter_gracefully(self):
        rc, out, err = self._run(["--label", "nonexistent"], [])
        self.assertEqual(rc, 0, err)
        self.assertIn("No open issues match the filter", out)

    def test_rank_only_stops_after_the_table(self):
        issues = [gh_issue(1, labels=["priority: P2"])]
        rc, out, err = self._run(["--rank-only"], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("Priority ranking", out)
        self.assertNotIn("## #1", out)

    def test_no_rank_omits_the_table(self):
        issues = [gh_issue(1, labels=["priority: P2"])]
        rc, out, err = self._run(["--no-rank"], issues)
        self.assertEqual(rc, 0, err)
        self.assertNotIn("Priority ranking", out)
        self.assertIn("## #1", out)

    def test_body_chars_zero_omits_body_text(self):
        issues = [gh_issue(1, body="secret detail", labels=["priority: P2"])]
        rc, out, err = self._run(["--body-chars", "0"], issues)
        self.assertEqual(rc, 0, err)
        self.assertNotIn("secret detail", out)

    def test_gh_not_found_reports_error(self):
        rc, out, err = self._run([], [], path_override="/nonexistent-only")
        self.assertEqual(rc, 1)
        self.assertIn("gh CLI not found", err)


if __name__ == "__main__":
    unittest.main()


CONTRACT = ("<!-- ship: tier=P1 area=test-infra blocked-by=none "
            "blocks=#98 touches=tests/,vitest.config.ts design=settled -->")


class ShipContractTest(unittest.TestCase):
    """The `<!-- ship: ... -->` block: the half of the ranking decision that is
    supposed to be read rather than re-derived."""

    def test_parses_every_known_field(self):
        c = idg.parse_ship_contract(f"Some prose.\n\n{CONTRACT}\n\nMore prose.")
        self.assertEqual(c["tier"], "P1")
        self.assertEqual(c["area"], "test-infra")
        self.assertEqual(c["depends_on"], [])
        self.assertEqual(c["blocks"], [98])
        self.assertEqual(c["touches"], ["tests/", "vitest.config.ts"])
        self.assertEqual(c["design"], "settled")
        self.assertEqual(c["missing_fields"], [])
        self.assertEqual(c["unknown_fields"], [])

    def test_absent_block_is_none(self):
        self.assertIsNone(idg.parse_ship_contract("no contract here #12"))
        self.assertIsNone(idg.parse_ship_contract(""))
        self.assertIsNone(idg.parse_ship_contract(None))

    def test_later_block_wins_field_by_field(self):
        body = ("<!-- ship: tier=P3 touches=a/ -->\n"
                "<!-- ship: tier=P0 blocked-by=#7 -->")
        c = idg.parse_ship_contract(body)
        self.assertEqual(c["tier"], "P0")
        self.assertEqual(c["depends_on"], [7])
        # A field only the first block set survives — the blocks are merged,
        # not swapped, so correcting one field does not silently drop the rest.
        self.assertEqual(c["touches"], ["a/"])

    def test_missing_required_fields_are_reported(self):
        c = idg.parse_ship_contract("<!-- ship: area=api -->")
        self.assertEqual(c["missing_fields"], ["tier", "blocked-by", "touches"])

    def test_unknown_fields_are_kept_but_flagged(self):
        c = idg.parse_ship_contract("<!-- ship: tier=P1 owner=someone -->")
        self.assertEqual(c["tier"], "P1")
        self.assertEqual(c["unknown_fields"], ["owner"])

    def test_garbage_tier_and_design_are_dropped_not_trusted(self):
        c = idg.parse_ship_contract("<!-- ship: tier=URGENT design=maybe -->")
        self.assertIsNone(c["tier"])
        self.assertIsNone(c["design"])

    def test_numbers_parse_with_or_without_hash(self):
        c = idg.parse_ship_contract("<!-- ship: blocked-by=12,#13 -->")
        self.assertEqual(c["depends_on"], [12, 13])


class ContractIntegrationTest(DigestRunner, unittest.TestCase):
    """The contract as it changes ranking, readiness and grouping input."""

    def test_contract_tier_ranks_without_a_label(self):
        issues = [
            gh_issue(1, title="guessed", body="small tweak"),
            gh_issue(2, title="declared", body="<!-- ship: tier=P0 -->"),
        ]
        rc, out, err = self._run(["--select"], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #2", out)
        # Settled, so it prints plain — not as the `~P0` a score guess gets.
        self.assertIn("[P0]", out)
        self.assertNotIn("[~P0]", out)

    def test_written_label_outranks_a_stale_contract_tier(self):
        issues = [gh_issue(1, labels=["priority: P3"], body="<!-- ship: tier=P0 -->")]
        rc, out, err = self._run(["--select", "--json"], issues)
        row = json.loads(out)["ranking"][0]
        self.assertEqual(row["tier"], "P3")
        self.assertEqual(row["contract_tier"], "P0")
        self.assertEqual(row["confirmed_tier"], "P3")

    def test_coverage_reads_complete_when_contracts_cover_the_gap(self):
        issues = [
            gh_issue(1, labels=["priority: P1"]),
            gh_issue(2, body="<!-- ship: tier=P2 -->"),
        ]
        rc, out, err = self._run(["--select"], issues)
        self.assertIn("COMPLETE", out)
        self.assertIn("contract: 1/2", out)
        # The label is still owed even though the tier is settled.
        self.assertIn("still need the label written", out)

    def test_contract_edges_block_and_unblock(self):
        issues = [
            gh_issue(1, labels=["priority: P0"], body="<!-- ship: blocked-by=#2 -->"),
            gh_issue(2, labels=["priority: P3"]),
        ]
        rc, out, err = self._run(["--select"], issues)
        self.assertIn("select: #2", out)
        self.assertIn("#1[P0] BLOCKED-BY:#2", out)

    def test_design_open_holds_the_issue_without_a_label(self):
        issues = [gh_issue(1, labels=["priority: P0"], body="<!-- ship: design=open -->")]
        rc, out, err = self._run(["--select"], issues)
        self.assertIn("select: none", out)
        self.assertIn("needs-design: #1", out)

    def test_touches_and_area_reach_the_json_ranking(self):
        issues = [gh_issue(1, body="<!-- ship: tier=P1 area=api touches=src/api/ -->")]
        rc, out, err = self._run(["--select", "--json"], issues)
        row = json.loads(out)["ranking"][0]
        self.assertEqual(row["touches"], ["src/api/"])
        self.assertEqual(row["area"], "api")

    def test_audit_names_what_each_issue_is_missing(self):
        issues = [
            gh_issue(1, body=CONTRACT),
            gh_issue(2, body="<!-- ship: tier=P1 -->"),
            gh_issue(3, body="nothing"),
        ]
        rc, out, err = self._run(["--audit"], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("contract: 1/3 complete · 1 partial · 1 missing", out)
        self.assertIn("missing: #3", out)
        self.assertIn("partial: #2 — no blocked-by,touches", out)


class ComposableOutputTest(DigestRunner, unittest.TestCase):
    """--select composing with --with-rank/--detail is what collapses a
    startup's three digest calls into one."""

    def test_with_rank_appends_the_table_to_select(self):
        issues = [gh_issue(1, labels=["priority: P0"]), gh_issue(2, labels=["priority: P2"])]
        rc, out, err = self._run(["--select", "--with-rank"], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #1", out)
        self.assertIn("## Priority ranking", out)
        self.assertLess(out.index("select: #1"), out.index("## Priority ranking"))

    def test_detail_top_prints_bodies_without_narrowing_the_rank(self):
        issues = [
            gh_issue(1, labels=["priority: P0"], body="the P0 body"),
            gh_issue(2, labels=["priority: P1"], body="the P1 body"),
            gh_issue(3, labels=["priority: P2"], body="the P2 body"),
        ]
        rc, out, err = self._run(["--select", "3", "--detail-top", "2"], issues)
        self.assertEqual(rc, 0, err)
        self.assertIn("the P0 body", out)
        self.assertIn("the P1 body", out)
        self.assertNotIn("the P2 body", out)
        # All three still ranked — unlike --issue, --detail-top does not filter.
        self.assertIn("next  : #3", out)

    def test_detail_takes_explicit_numbers_too(self):
        issues = [
            gh_issue(1, labels=["priority: P0"], body="first body"),
            gh_issue(9, labels=["priority: P3"], body="ninth body"),
        ]
        rc, out, err = self._run(["--select", "--detail", "9"], issues)
        self.assertIn("ninth body", out)
        self.assertNotIn("first body", out)

    def test_detail_for_an_issue_outside_the_digest_says_so(self):
        rc, out, err = self._run(
            ["--select", "--detail", "404"], [gh_issue(1, labels=["priority: P0"])])
        self.assertIn("not-in-digest: #404", out)

    def test_plain_select_is_unchanged(self):
        rc, out, err = self._run(["--select"], [gh_issue(1, labels=["priority: P0"])])
        self.assertNotIn("## Priority ranking", out)
        self.assertNotIn("## #1", out)


class DigestCacheTest(DigestRunner, unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name)

    def _gh_fetches(self):
        return [c for c in self.gh_calls if c[:2] in (["issue", "list"], ["pr", "list"])]

    def test_second_call_serves_from_cache(self):
        issues = [gh_issue(1, labels=["priority: P0"], body="cached body")]
        self._run(["--select", "--cache-ttl", "300"], issues,
                  state_dir=self.state, cache=True)
        self.assertEqual(len(self._gh_fetches()), 2)
        # A second, differently-shaped call within the TTL: no gh at all, and
        # the detail comes out of the same fetch the --select paid for.
        rc, out, err = self._run(["--select", "--detail", "1", "--cache-ttl", "300"],
                                 issues, state_dir=self.state, cache=True)
        self.assertEqual(rc, 0, err)
        self.assertEqual(self._gh_fetches(), [])
        self.assertIn("cached body", out)

    def test_refresh_bypasses_a_warm_cache(self):
        issues = [gh_issue(1, labels=["priority: P0"])]
        self._run(["--select", "--cache-ttl", "300"], issues,
                  state_dir=self.state, cache=True)
        self._run(["--select", "--refresh", "--cache-ttl", "300"], issues,
                  state_dir=self.state, cache=True)
        self.assertEqual(len(self._gh_fetches()), 2)

    def test_zero_ttl_disables_the_cache(self):
        issues = [gh_issue(1, labels=["priority: P0"])]
        self._run(["--select", "--cache-ttl", "300"], issues,
                  state_dir=self.state, cache=True)
        self._run(["--select", "--cache-ttl", "0"], issues,
                  state_dir=self.state, cache=True)
        self.assertEqual(len(self._gh_fetches()), 2)

    def test_a_different_filter_is_a_different_cache_entry(self):
        issues = [gh_issue(1, labels=["priority: P0", "bug"])]
        self._run(["--select", "--cache-ttl", "300"], issues,
                  state_dir=self.state, cache=True)
        self._run(["--select", "--label", "bug", "--cache-ttl", "300"], issues,
                  state_dir=self.state, cache=True)
        self.assertEqual(len(self._gh_fetches()), 2)

    def test_expired_cache_refetches(self):
        issues = [gh_issue(1, labels=["priority: P0"])]
        self._run(["--select", "--cache-ttl", "300"], issues,
                  state_dir=self.state, cache=True)
        self._run(["--select", "--cache-ttl", "1"], issues,
                  state_dir=self.state, cache=True)
        cache_file = next(self.state.glob("shipping-issues/*/digest-cache.json"))
        blob = json.loads(cache_file.read_text())
        blob["fetched_at"] -= 3600
        cache_file.write_text(json.dumps(blob))
        self._run(["--select", "--cache-ttl", "300"], issues,
                  state_dir=self.state, cache=True)
        self.assertEqual(len(self._gh_fetches()), 2)

    def test_malformed_cache_is_a_miss_not_an_error(self):
        issues = [gh_issue(1, labels=["priority: P0"])]
        self._run(["--select", "--cache-ttl", "300"], issues,
                  state_dir=self.state, cache=True)
        cache_file = next(self.state.glob("shipping-issues/*/digest-cache.json"))
        cache_file.write_text("{ not json")
        rc, out, err = self._run(["--select", "--cache-ttl", "300"], issues,
                  state_dir=self.state, cache=True)
        self.assertEqual(rc, 0, err)
        self.assertIn("select: #1", out)
        self.assertEqual(len(self._gh_fetches()), 2)

    def test_env_kill_switch_disables_the_cache(self):
        issues = [gh_issue(1, labels=["priority: P0"])]
        self._run(["--select", "--cache-ttl", "300"], issues,
                  state_dir=self.state, cache=True)
        # cache=False leaves FakeGh's SHIPPING_ISSUES_NO_CACHE=1 in place.
        self._run(["--select"], issues, state_dir=self.state)
        self.assertEqual(len(self._gh_fetches()), 2)

    def test_the_cache_is_off_unless_a_caller_asks_for_it(self):
        # The dangerous default is on-by-default: a digest served from before
        # this run's own merge can re-select an issue that is already closed,
        # and nothing downstream would notice. Opting in is the caller's job.
        issues = [gh_issue(1, labels=["priority: P0"])]
        self._run(["--select"], issues, state_dir=self.state, cache=True)
        self._run(["--select"], issues, state_dir=self.state, cache=True)
        self.assertEqual(len(self._gh_fetches()), 2)
