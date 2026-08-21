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
               "open_pr": {"number": 1}}
        self.assertEqual(idg.readiness(rec), "BLOCKED-BY:#3")

    def test_not_ready_label_next(self):
        rec = {"depends_on_open": [], "not_ready_labels": ["question"],
               "open_pr": {"number": 1}}
        self.assertEqual(idg.readiness(rec), "LABEL:question")

    def test_open_pr_next(self):
        rec = {"depends_on_open": [], "not_ready_labels": [],
               "open_pr": {"number": 7}}
        self.assertEqual(idg.readiness(rec), "HAS-PR:#7")

    def test_ready_when_nothing_blocks(self):
        rec = {"depends_on_open": [], "not_ready_labels": [], "open_pr": None}
        self.assertEqual(idg.readiness(rec), "READY")


class MainEndToEndTest(unittest.TestCase):
    """Runs main() in-process (not via subprocess) against a fake `gh` on
    PATH, so coverage sees the code these tests exercise. Only the external
    `gh` process itself is out of process — issue_digest.py's own code runs
    in this interpreter."""

    def _run(self, args, issues, prs=None, path_override=None):
        responses = {
            ("issue", "list"): json.dumps(issues),
            ("pr", "list"): json.dumps(prs or []),
        }
        with FakeGh(responses) as fake:
            env = dict(fake.env)
            if path_override is not None:
                env["PATH"] = path_override
            out, err = io.StringIO(), io.StringIO()
            with patch.dict("os.environ", env, clear=False), \
                    patch.object(sys, "argv", ["issue_digest.py", *args]), \
                    redirect_stdout(out), redirect_stderr(err):
                try:
                    rc = idg.main()
                except SystemExit as exc:
                    rc = exc.code
        return rc, out.getvalue(), err.getvalue()

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
