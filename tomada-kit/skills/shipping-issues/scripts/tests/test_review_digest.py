#!/usr/bin/env python3
"""Tests for review_digest.py. Stdlib-only (unittest).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the shipping-issues skill directory)
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _fakegh import FakeGh  # noqa: E402
import review_digest as rd  # noqa: E402

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
REPO = "acme/widgets"


def marker(sha: str, *, must: int = 0, should: int = 0, nit: int = 0,
           pre: int = 0) -> str:
    return (f"<!-- claude-review v1 sha={sha} must={must} should={should} "
            f"nit={nit} pre={pre} -->")


def comment(login: str, utype: str, body: str) -> dict:
    return {"user": {"login": login, "type": utype}, "body": body}


def api_lines(comments: list[dict]) -> str:
    """What `gh api --paginate --jq '.[] | @json'` prints: one object a line."""
    return "".join(json.dumps(c) + "\n" for c in comments)


class ReviewDigestEndToEndTest(unittest.TestCase):
    """Runs main() in-process against a fake `gh` on PATH."""

    def _run(self, args, responses, exits=None, stderrs=None):
        with FakeGh(responses, exits=exits, stderrs=stderrs) as fake:
            out, err = io.StringIO(), io.StringIO()
            with patch.dict("os.environ", fake.env, clear=False), \
                    patch.object(sys, "argv", ["review_digest.py", *args]), \
                    redirect_stdout(out), redirect_stderr(err):
                try:
                    rc = rd.main()
                except SystemExit as exc:
                    rc = exc.code
            # Read inside the block: the fake's call log is deleted on exit.
            return rc, out.getvalue(), err.getvalue(), fake.calls

    # -- REVIEWED with findings -------------------------------------------

    def test_reviewed_with_findings(self):
        body = (marker(SHA_A, must=1) + "\n"
                + "- [must-fix] R1 `src/x.ts:12` — bad thing — why it matters\n")
        comments = [comment("claude[bot]", "Bot", body)]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("review: REVIEWED", out)
        self.assertIn(f"sha: {SHA_A}", out)
        self.assertIn("round: 1", out)
        self.assertIn("counts: must=1 should=0 nit=0 pre=0", out)
        self.assertIn(
            "R1 must-fix src/x.ts:12 — bad thing — why it matters", out)

    # -- REVIEWED with zero findings ---------------------------------------

    def test_reviewed_zero_findings(self):
        body = marker(SHA_A) + "\nNo issues found.\n"
        comments = [comment("claude[bot]", "Bot", body)]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("review: REVIEWED", out)
        self.assertIn("counts: must=0 should=0 nit=0 pre=0", out)
        findings_block = out.split("findings:\n", 1)[1].split("warnings:\n", 1)[0]
        self.assertEqual(findings_block.strip(), "")

    # -- NOT_REVIEWED (no marker) -------------------------------------------

    def test_not_reviewed_no_marker(self):
        comments = [comment("claude[bot]", "Bot", "Just a comment, no marker.")]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 3, err)
        self.assertIn("review: NOT_REVIEWED", out)
        self.assertIn("round: 0", out)

    # -- marker for a different sha only -------------------------------------

    def test_marker_for_different_sha_only(self):
        comments = [comment("claude[bot]", "Bot", marker(SHA_B))]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 3, err)
        self.assertIn("review: NOT_REVIEWED", out)
        # The other sha's summary still counts toward round.
        self.assertIn("round: 1", out)

    # -- forged markers -------------------------------------------------------

    def test_forged_marker_from_non_bot_is_ignored_with_warning(self):
        comments = [comment("claude[bot]", "User", marker(SHA_A))]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 3, err)
        self.assertIn("round: 0", out)
        self.assertIn("ignored review marker from non-reviewer claude[bot]", out)

    def test_forged_marker_from_disallowed_bot_is_ignored_with_warning(self):
        comments = [comment("evil-bot[bot]", "Bot", marker(SHA_A))]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 3, err)
        self.assertIn("round: 0", out)
        self.assertIn("ignored review marker from non-reviewer evil-bot[bot]", out)

    # -- last of several wins --------------------------------------------------

    def test_last_of_several_summaries_for_the_same_sha_wins(self):
        first = (marker(SHA_A, must=1) + "\n"
                 + "- [must-fix] R1 `a.ts:1` — first — first-why\n")
        second = (marker(SHA_A, must=1, should=1) + "\n"
                  + "- [must-fix] R1 `b.ts:2` — second — second-why\n"
                  + "- [should-fix] R2 `c.ts:3` — third — third-why\n")
        comments = [comment("claude[bot]", "Bot", first),
                    comment("claude[bot]", "Bot", second)]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("counts: must=1 should=1 nit=0 pre=0", out)
        self.assertIn("R1 must-fix b.ts:2", out)
        self.assertIn("R2 should-fix c.ts:3", out)
        self.assertNotIn("a.ts:1", out)
        # Same sha twice still counts as one round.
        self.assertIn("round: 1", out)

    # -- count mismatch warning -------------------------------------------------

    def test_marker_counts_disagreeing_with_parsed_lines_is_a_warning(self):
        body = (marker(SHA_A, must=2) + "\n"
                + "- [must-fix] R1 `a.ts:1` — bad — why\n")
        comments = [comment("claude[bot]", "Bot", body)]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 0, err)
        # The parsed count wins for counts:, not the marker's claimed count.
        self.assertIn("counts: must=1 should=0 nit=0 pre=0", out)
        self.assertIn("marker counts (must=2 should=0 nit=0 pre=0)", out)
        self.assertIn("disagree with parsed findings (must=1 should=0 nit=0 pre=0)", out)

    # -- unparsed line warning ------------------------------------------------

    def test_unparsed_finding_line_goes_to_warnings_not_dropped(self):
        # No backticks around the location, so it fails FINDING_RE.
        body = (marker(SHA_A) + "\n"
                + "- [must-fix] R1 src/x.ts:12 — bad — why\n")
        comments = [comment("claude[bot]", "Bot", body)]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("review: REVIEWED", out)
        self.assertIn(
            "unparsed finding line: - [must-fix] R1 src/x.ts:12 — bad — why", out)
        # Not counted as a finding.
        self.assertIn("counts: must=0 should=0 nit=0 pre=0", out)

    # -- separator tolerance ----------------------------------------------------

    def test_finding_line_tolerates_plain_hyphen_separator(self):
        body = (marker(SHA_A, must=1) + "\n"
                + "- [must-fix] R1 `a.ts:1` - bad -- why\n")
        comments = [comment("claude[bot]", "Bot", body)]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("counts: must=1 should=0 nit=0 pre=0", out)
        self.assertIn("R1 must-fix a.ts:1 — bad — why", out)

    # -- round counting -----------------------------------------------------

    def test_round_counts_distinct_shas_not_distinct_comments(self):
        comments = [
            comment("claude[bot]", "Bot", marker(SHA_A)),
            comment("claude[bot]", "Bot",
                   marker(SHA_A, must=1) + "\n- [must-fix] R1 `x` — a — b\n"),
            comment("claude[bot]", "Bot", marker(SHA_B)),
        ]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_C],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 3, err)
        self.assertIn("review: NOT_REVIEWED", out)
        self.assertIn("round: 2", out)

    # -- --reviewer override -------------------------------------------------

    def test_reviewer_override_accepts_a_non_default_bot_login(self):
        body = (marker(SHA_A, must=1) + "\n"
                + "- [must-fix] R1 `x.ts:1` — bad — why\n")
        comments = [comment("other-bot[bot]", "Bot", body)]

        rc_default, out_default, err_default, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc_default, 3, err_default)
        self.assertIn("ignored review marker from non-reviewer other-bot[bot]",
                      out_default)

        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A,
             "--reviewer", "other-bot[bot]"],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("review: REVIEWED", out)
        self.assertIn("R1 must-fix x.ts:1", out)

    # -- default sha resolution ----------------------------------------------

    def test_default_sha_resolved_from_pr_view_head(self):
        body = (marker(SHA_A, must=1) + "\n"
                + "- [must-fix] R1 `x.ts:1` — bad — why\n")
        comments = [comment("claude[bot]", "Bot", body)]
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO],
            {
                ("pr", "view"): f"{SHA_A}\n",
                ("api",): api_lines(comments),
            },
        )
        self.assertEqual(rc, 0, err)
        self.assertIn(f"sha: {SHA_A}", out)
        self.assertIn("review: REVIEWED", out)

    # -- gh read failure -> exit 2 --------------------------------------------

    def test_gh_read_failure_exits_2_with_detail(self):
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): ""},
            exits={("api",): 1},
            stderrs={("api",): "HTTP 500: something broke"},
        )
        self.assertEqual(rc, 2, err)
        self.assertIn("review: ERROR", out)
        self.assertIn("detail:", out)
        self.assertIn("something broke", out)

    def test_repo_resolution_failure_exits_2(self):
        rc, out, err, _fake = self._run(
            [str(7), "--sha", SHA_A],
            {("repo", "view"): ""},
            exits={("repo", "view"): 1},
            stderrs={("repo", "view"): "not a git repository"},
        )
        self.assertEqual(rc, 2, err)
        self.assertIn("review: ERROR", out)
        self.assertIn("detail:", out)

    # -- more than one page of comments ---------------------------------------

    def test_reads_every_comment_across_pages_one_json_line_each(self):
        noise = [comment("someone", "User", f"comment {i}\nsecond line")
                 for i in range(34)]
        body = (marker(SHA_A, nit=1) + "\n"
                + "- [nit] R1 `x.ts:1` — naming — clarity\n")
        comments = [*noise, comment("claude[bot]", "Bot", body)]
        rc, out, err, calls = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): api_lines(comments)},
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("counts: must=0 should=0 nit=1 pre=0", out)
        api_call = next(c for c in calls if c[:1] == ["api"])
        self.assertIn("--paginate", api_call)
        self.assertEqual(api_call[api_call.index("--jq") + 1], ".[] | @json")

    def test_unreadable_comment_line_exits_2(self):
        rc, out, err, _fake = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A],
            {("api",): '[{"body": "a"}][{"body": "b"}]\n'},
        )
        self.assertEqual(rc, 2, err)
        self.assertIn("review: ERROR", out)

    # -- --sha validation ---------------------------------------------------------

    def test_short_sha_is_rejected_rather_than_prefix_matched(self):
        rc, out, err, calls = self._run(
            [str(7), "--repo", REPO, "--sha", SHA_A[:7]],
            {("api",): api_lines([comment("claude[bot]", "Bot", marker(SHA_A))])},
        )
        self.assertEqual(rc, 2, err)
        self.assertIn("review: ERROR", out)
        self.assertIn("40-hex", out)
        self.assertEqual(calls, [])


class RespondModeTest(unittest.TestCase):
    def test_respond_posts_marker_prefixed_body(self):
        captured: dict[str, object] = {}

        def fake_gh_call(args):
            self.assertEqual(args[:2], ["pr", "comment"])
            idx = args.index("--body-file")
            path = Path(args[idx + 1])
            captured["body"] = path.read_text(encoding="utf-8")
            captured["args"] = args
            return True, "https://github.com/acme/widgets/pull/7#issuecomment-1\n", ""

        with tempfile.TemporaryDirectory() as td:
            respond_file = Path(td) / "resp.md"
            respond_file.write_text("- R1 fixed — did X\n", encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with patch("review_digest.gh_call", side_effect=fake_gh_call), \
                    patch.object(sys, "argv", [
                        "review_digest.py", "7", "--repo", REPO,
                        "--sha", SHA_A, "--respond", str(respond_file)]), \
                    redirect_stdout(out), redirect_stderr(err):
                try:
                    rc = rd.main()
                except SystemExit as exc:
                    rc = exc.code

        self.assertEqual(rc, 0, err.getvalue())
        self.assertIn(f"responded: {SHA_A}", out.getvalue())
        self.assertEqual(
            captured["body"],
            f"<!-- claude-review-response v1 sha={SHA_A} -->\n- R1 fixed — did X\n")

    def test_respond_missing_file_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing.md"
            out, err = io.StringIO(), io.StringIO()
            with patch.object(sys, "argv", [
                    "review_digest.py", "7", "--repo", REPO,
                    "--sha", SHA_A, "--respond", str(missing)]), \
                    redirect_stdout(out), redirect_stderr(err):
                try:
                    rc = rd.main()
                except SystemExit as exc:
                    rc = exc.code
        self.assertEqual(rc, 2, out.getvalue() + err.getvalue())
        self.assertIn("not found", err.getvalue())

    def test_respond_gh_failure_exits_2(self):
        def fake_gh_call(args):
            return False, "", "gh pr comment failed: HTTP 403"

        with tempfile.TemporaryDirectory() as td:
            respond_file = Path(td) / "resp.md"
            respond_file.write_text("- R1 fixed — did X\n", encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with patch("review_digest.gh_call", side_effect=fake_gh_call), \
                    patch.object(sys, "argv", [
                        "review_digest.py", "7", "--repo", REPO,
                        "--sha", SHA_A, "--respond", str(respond_file)]), \
                    redirect_stdout(out), redirect_stderr(err):
                try:
                    rc = rd.main()
                except SystemExit as exc:
                    rc = exc.code
        self.assertEqual(rc, 2, out.getvalue() + err.getvalue())
        self.assertIn("gh pr comment failed", err.getvalue())


if __name__ == "__main__":
    unittest.main()
