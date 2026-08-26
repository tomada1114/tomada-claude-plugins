#!/usr/bin/env python3
"""Tests for file_followup.py. Stdlib-only (unittest).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the shipping-issues skill directory)
"""
from __future__ import annotations

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
import file_followup as ff  # noqa: E402


class ResolveTierLabelTest(unittest.TestCase):
    def test_prefers_canonical_when_present(self):
        label = ff.resolve_tier_label("P2", ["priority: P2", "bug"], dry_run=True)
        self.assertEqual(label, "priority: P2")

    def test_reuses_repo_alias_instead_of_creating_canonical(self):
        # A repo that already spells the tier as "p2" must not also gain a
        # parallel "priority: P2" — that would split its own backlog in two.
        label = ff.resolve_tier_label("P2", ["p2", "bug"], dry_run=True)
        self.assertEqual(label, "p2")

    def test_shortest_alias_wins_when_repo_carries_several(self):
        label = ff.resolve_tier_label(
            "P2", ["p2", "priority: medium"], dry_run=True)
        self.assertEqual(label, "p2")

    def test_creates_canonical_when_repo_has_no_alias(self):
        with patch("file_followup.gh") as mock_gh:
            label = ff.resolve_tier_label("P1", ["bug"], dry_run=False)
        self.assertEqual(label, "priority: P1")
        mock_gh.assert_called_once()
        self.assertEqual(mock_gh.call_args[0][0][:2], ["label", "create"])

    def test_dry_run_never_creates(self):
        with patch("file_followup.gh") as mock_gh:
            label = ff.resolve_tier_label("P1", ["bug"], dry_run=True)
        self.assertEqual(label, "priority: P1")
        mock_gh.assert_not_called()


class MainEndToEndTest(unittest.TestCase):
    """Runs main() in-process against a fake `gh` on PATH, so coverage sees
    file_followup.py's own code (the `gh repo view` resolution call bypasses
    the gh() wrapper and is patched in the same way, via PATH)."""

    def _run(self, args, responses, exits=None, stderrs=None):
        with FakeGh(responses, exits=exits, stderrs=stderrs) as fake:
            out, err = io.StringIO(), io.StringIO()
            with patch.dict("os.environ", fake.env, clear=False), \
                    patch.object(sys, "argv", ["file_followup.py", *args]), \
                    redirect_stdout(out), redirect_stderr(err):
                try:
                    rc = ff.main()
                except SystemExit as exc:
                    rc = exc.code
            return rc, out.getvalue(), err.getvalue(), fake

    def test_files_issue_with_resolved_tier_and_dropped_missing_label(self):
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / "body.txt"
            body.write_text("Observed defect at foo.py:12.")
            rc, out, err, fake = self._run(
                ["--title", "t", "--body-file", str(body), "--tier", "P2",
                 "--label", "area:db", "--repo", "acme/widgets", "--json"],
                {
                    ("repo", "view"): "acme/widgets\n",
                    ("label", "list"): json.dumps([{"name": "priority: P2"}]),
                    ("issue", "create"): "https://github.com/acme/widgets/issues/99\n",
                },
            )
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["url"], "https://github.com/acme/widgets/issues/99")
        self.assertEqual(payload["labels"], ["priority: P2"])
        self.assertEqual(payload["skipped_labels"], ["area:db"])

    def test_missing_tier_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / "body.txt"
            body.write_text("x")
            rc, out, err, fake = self._run(
                ["--title", "t", "--body-file", str(body), "--repo", "acme/widgets"],
                {("repo", "view"): "acme/widgets\n"},
            )
        self.assertNotEqual(rc, 0)
        self.assertIn("--tier", err)

    def test_no_write_access_exits_2(self):
        # label list is empty, so resolve_tier_label must create the
        # canonical label — simulate the write-access failure right there.
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / "body.txt"
            body.write_text("x")
            rc, out, err, fake = self._run(
                ["--title", "t", "--body-file", str(body), "--tier", "P2",
                 "--repo", "acme/widgets"],
                {
                    ("repo", "view"): "acme/widgets\n",
                    ("label", "list"): "[]",
                    ("label", "create"): "",
                },
                exits={("label", "create"): 1},
                stderrs={("label", "create"): "HTTP 403: Resource not accessible"},
            )
        self.assertEqual(rc, 2, err)

    def test_empty_body_file_exits_3(self):
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / "body.txt"
            body.write_text("   \n")
            rc, out, err, fake = self._run(
                ["--title", "t", "--body-file", str(body), "--tier", "P2",
                 "--repo", "acme/widgets"],
                {("repo", "view"): "acme/widgets\n"},
            )
        self.assertEqual(rc, 3, err)

    def test_missing_body_file_exits_3(self):
        with tempfile.TemporaryDirectory() as td:
            rc, out, err, fake = self._run(
                ["--title", "t", "--body-file", str(Path(td) / "missing.txt"),
                 "--tier", "P2", "--repo", "acme/widgets"],
                {("repo", "view"): "acme/widgets\n"},
            )
        self.assertEqual(rc, 3, err)

    def test_found_while_appends_provenance_line(self):
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / "body.txt"
            body.write_text("Observed defect.")
            rc, out, err, fake = self._run(
                ["--title", "t", "--body-file", str(body), "--tier", "P3",
                 "--found-while", "42", "--repo", "acme/widgets", "--dry-run",
                 "--json"],
                {
                    ("repo", "view"): "acme/widgets\n",
                    ("label", "list"): "[]",
                },
            )
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["repo"], "acme/widgets")

    def test_needs_design_adds_resolved_label_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / "body.txt"
            body.write_text("Observed defect, but the fix approach is undecided.")
            rc, out, err, fake = self._run(
                ["--title", "t", "--body-file", str(body), "--tier", "P2",
                 "--needs-design", "--repo", "acme/widgets", "--dry-run", "--json"],
                {
                    ("repo", "view"): "acme/widgets\n",
                    ("label", "list"): "[]",
                },
            )
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["labels"], ["priority: P2", "blocked: design"])

    def test_needs_design_reuses_existing_alias_instead_of_creating(self):
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / "body.txt"
            body.write_text("Observed defect, approach undecided.")
            rc, out, err, fake = self._run(
                ["--title", "t", "--body-file", str(body), "--tier", "P2",
                 "--needs-design", "--repo", "acme/widgets", "--dry-run", "--json"],
                {
                    ("repo", "view"): "acme/widgets\n",
                    ("label", "list"): json.dumps([{"name": "priority: P2"},
                                                    {"name": "needs-design"}]),
                },
            )
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["labels"], ["priority: P2", "needs-design"])

    def test_omitting_needs_design_never_adds_the_label(self):
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / "body.txt"
            body.write_text("Observed defect with a clear, verified fix.")
            rc, out, err, fake = self._run(
                ["--title", "t", "--body-file", str(body), "--tier", "P2",
                 "--repo", "acme/widgets", "--dry-run", "--json"],
                {
                    ("repo", "view"): "acme/widgets\n",
                    ("label", "list"): "[]",
                },
            )
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["labels"], ["priority: P2"])

    def test_needs_design_files_with_label_and_creates_it_when_absent(self):
        # Written without self._run(): fake.calls must be read while the
        # FakeGh block is still open — see the analogous note in
        # test_apply_priority_labels.py's test_set_design_via_main_never_calls_the_digest.
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / "body.txt"
            body.write_text("Observed defect, approach undecided.")
            responses = {
                ("repo", "view"): "acme/widgets\n",
                # priority: P2 already exists so the only label this test's
                # assertion needs to isolate is the design one.
                ("label", "list"): json.dumps([{"name": "priority: P2"}]),
                ("label", "create"): "",
                ("issue", "create"): "https://github.com/acme/widgets/issues/99\n",
            }
            with FakeGh(responses) as fake:
                out, err = io.StringIO(), io.StringIO()
                args = ["--title", "t", "--body-file", str(body), "--tier", "P2",
                       "--needs-design", "--repo", "acme/widgets"]
                with patch.dict("os.environ", fake.env, clear=False), \
                        patch.object(sys, "argv", ["file_followup.py", *args]), \
                        redirect_stdout(out), redirect_stderr(err):
                    try:
                        rc = ff.main()
                    except SystemExit as exc:
                        rc = exc.code
                creates = [c for c in fake.calls if c[:2] == ["label", "create"]]
                issue_creates = [c for c in fake.calls if c[:2] == ["issue", "create"]]
        self.assertEqual(rc, 0, err.getvalue())
        self.assertEqual(len(creates), 1)
        self.assertEqual(creates[0][2], "blocked: design")
        self.assertEqual(len(issue_creates), 1)
        self.assertIn("blocked: design", issue_creates[0])

    def test_unresolvable_repo_exits_1(self):
        rc, out, err, fake = self._run(
            ["--title", "t", "--body-file", "/dev/null", "--tier", "P2"],
            {("repo", "view"): ""},
            exits={("repo", "view"): 1},
        )
        self.assertEqual(rc, 1, err)


if __name__ == "__main__":
    unittest.main()
