#!/usr/bin/env python3
"""Tests for apply_priority_labels.py. Stdlib-only (unittest).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the shipping-issues skill directory)
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _fakegh import FakeGh  # noqa: E402
import apply_priority_labels as apl  # noqa: E402


def issue(number, labels, updated="2026-01-01T00:00:00Z"):
    # `labels` mirrors issue_digest.py's *output* shape (plain name strings);
    # the raw `gh issue list --json labels` shape it consumes wraps each in
    # {"name": ...}, so that wrapping happens here.
    return {"number": number, "title": f"issue {number}",
            "labels": [{"name": n} for n in labels],
            "assignees": [], "milestone": None, "body": "", "createdAt": updated,
            "updatedAt": updated, "url": f"https://x/{number}"}


class ParseSetsTest(unittest.TestCase):
    def test_valid_pairs(self):
        self.assertEqual(apl.parse_sets(["12=P0", "9=p2"]), {12: "P0", 9: "P2"})

    def test_leading_hash_stripped(self):
        self.assertEqual(apl.parse_sets(["#12=P0"]), {12: "P0"})

    def test_unknown_tier_exits_3(self):
        with self.assertRaises(SystemExit) as cm:
            apl.parse_sets(["12=P9"])
        self.assertEqual(cm.exception.code, 3)

    def test_non_numeric_issue_exits_3(self):
        with self.assertRaises(SystemExit) as cm:
            apl.parse_sets(["abc=P0"])
        self.assertEqual(cm.exception.code, 3)


class ApplyTest(unittest.TestCase):
    def test_adds_target_when_absent(self):
        with patch("apply_priority_labels.gh") as mock_gh:
            changed = apl.apply(12, "P0", [], dry_run=False)
        self.assertTrue(changed)
        mock_gh.assert_called_once_with(
            ["issue", "edit", "12", "--add-label", "priority: P0"])

    def test_no_op_when_already_exact_label(self):
        with patch("apply_priority_labels.gh") as mock_gh:
            changed = apl.apply(12, "P0", ["priority: P0"], dry_run=False)
        self.assertFalse(changed)
        mock_gh.assert_not_called()

    def test_strips_stale_tier_labels(self):
        with patch("apply_priority_labels.gh") as mock_gh:
            changed = apl.apply(12, "P0", ["priority: P2", "bug"], dry_run=False)
        self.assertTrue(changed)
        args = mock_gh.call_args[0][0]
        self.assertIn("--add-label", args)
        self.assertIn("priority: P0", args)
        self.assertIn("--remove-label", args)
        self.assertIn("priority: P2", args)
        self.assertNotIn("bug", args)

    def test_dry_run_never_calls_gh(self):
        with patch("apply_priority_labels.gh") as mock_gh:
            changed = apl.apply(12, "P0", [], dry_run=True)
        self.assertTrue(changed)
        mock_gh.assert_not_called()

    def test_alias_label_is_treated_as_stale(self):
        # "critical" normalizes to the P0 alias set; re-applying P0 with an
        # alias present must still fire so the legacy spelling gets removed.
        with patch("apply_priority_labels.gh") as mock_gh:
            changed = apl.apply(12, "P0", ["critical"], dry_run=False)
        self.assertTrue(changed)
        args = mock_gh.call_args[0][0]
        self.assertIn("--remove-label", args)
        self.assertIn("critical", args)


class EnsureLabelsTest(unittest.TestCase):
    """ensure_labels() shells out to the real `gh` on PATH — route PATH at a
    fake one instead of mocking subprocess, so the real subprocess.run stays
    untouched (mocking it here would recurse into gh()'s own call)."""

    def test_creates_only_missing_labels(self):
        existing = json.dumps([{"name": "priority: P0"}, {"name": "priority: P1"}])
        with FakeGh({("label", "list"): existing}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                created = apl.ensure_labels(dry_run=False)
        self.assertEqual(sorted(created), ["priority: P2", "priority: P3"])

    def test_dry_run_creates_nothing_but_reports_plan(self):
        with FakeGh({("label", "list"): "[]"}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                created = apl.ensure_labels(dry_run=True)
            calls = [c for c in fake.calls if c[:2] == ["label", "create"]]
        self.assertEqual(sorted(created), ["priority: P0", "priority: P1",
                                            "priority: P2", "priority: P3"])
        self.assertEqual(calls, [])


class SetClearDesignTest(unittest.TestCase):
    """set_design()/clear_design() shell out to the real `gh` on PATH — route
    PATH at a fake one instead of mocking subprocess, same as EnsureLabelsTest."""

    def test_set_design_creates_label_when_repo_has_none(self):
        with FakeGh({("label", "list"): "[]",
                    ("label", "create"): "", ("issue", "edit"): ""}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                name = apl.set_design(12, dry_run=False)
            creates = [c for c in fake.calls if c[:2] == ["label", "create"]]
            edits = [c for c in fake.calls if c[:2] == ["issue", "edit"]]
        self.assertEqual(name, "blocked: design")
        self.assertEqual(len(creates), 1)
        self.assertEqual(edits, [["issue", "edit", "12", "--add-label", "blocked: design"]])

    def test_set_design_reuses_existing_alias_without_creating(self):
        existing = json.dumps([{"name": "needs-design"}])
        with FakeGh({("label", "list"): existing, ("issue", "edit"): ""}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                name = apl.set_design(12, dry_run=False)
            created = any(c[:2] == ["label", "create"] for c in fake.calls)
        self.assertEqual(name, "needs-design")
        self.assertFalse(created)

    def test_set_design_dry_run_makes_no_gh_mutations(self):
        with FakeGh({("label", "list"): "[]"}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                name = apl.set_design(12, dry_run=True)
            mutating = [c for c in fake.calls if c[:2] in
                       (["issue", "edit"], ["label", "create"])]
        self.assertEqual(name, "blocked: design")
        self.assertEqual(mutating, [])

    def test_clear_design_removes_carried_alias(self):
        view = json.dumps({"labels": [{"name": "needs-design"}, {"name": "priority: P1"}]})
        with FakeGh({("issue", "view"): view, ("issue", "edit"): ""}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                removed = apl.clear_design(12, dry_run=False)
            edits = [c for c in fake.calls if c[:2] == ["issue", "edit"]]
        self.assertEqual(removed, ["needs-design"])
        self.assertEqual(edits,
                         [["issue", "edit", "12", "--remove-label", "needs-design"]])

    def test_clear_design_is_a_noop_when_not_present(self):
        view = json.dumps({"labels": [{"name": "priority: P1"}]})
        with FakeGh({("issue", "view"): view}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                removed = apl.clear_design(12, dry_run=False)
            edited = any(c[:2] == ["issue", "edit"] for c in fake.calls)
        self.assertEqual(removed, [])
        self.assertFalse(edited)

    def test_clear_design_dry_run_makes_no_gh_mutations(self):
        view = json.dumps({"labels": [{"name": "blocked: design"}]})
        with FakeGh({("issue", "view"): view}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                removed = apl.clear_design(12, dry_run=True)
            edited = any(c[:2] == ["issue", "edit"] for c in fake.calls)
        self.assertEqual(removed, ["blocked: design"])
        self.assertFalse(edited)


class MainEndToEndTest(unittest.TestCase):
    """Runs main() in-process against a fake `gh` on PATH. load_digest()
    still shells out to issue_digest.py as a real subprocess (that is its
    actual design), so only apply_priority_labels.py's own lines are covered
    here — issue_digest.py has its own in-process tests."""

    def _run(self, args, responses, path_override=None):
        with FakeGh(responses) as fake:
            env = dict(fake.env)
            if path_override is not None:
                env["PATH"] = path_override
            out, err = io.StringIO(), io.StringIO()
            with patch.dict("os.environ", env, clear=False), \
                    patch.object(sys, "argv", ["apply_priority_labels.py", *args]), \
                    redirect_stdout(out), redirect_stderr(err):
                try:
                    rc = apl.main()
                except SystemExit as exc:
                    rc = exc.code
            return rc, out.getvalue(), err.getvalue(), fake

    def test_backfill_labels_unlabeled_open_issue(self):
        issues = json.dumps([issue(12, [])])
        rc, out, err, fake = self._run(
            ["--backfill", "--json"],
            {
                ("label", "list"): "[]",
                ("issue", "list"): issues,
                ("pr", "list"): "[]",
                ("issue", "edit"): "",
                ("label", "create"): "",
            },
        )
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["verdict"], "OK")
        self.assertEqual(len(payload["changed"]), 1)
        self.assertEqual(payload["changed"][0]["number"], 12)
        # #12 had no leverage signal, an empty body and no unblocks, so the
        # heuristic suggestion is the lowest tier.
        self.assertEqual(payload["changed"][0]["tier"], "P3")

    def test_set_overrides_backfill_suggestion(self):
        issues = json.dumps([issue(9, [])])
        rc, out, err, fake = self._run(
            ["--set", "9=P0", "--json"],
            {
                ("label", "list"): "[]",
                ("issue", "list"): issues,
                ("pr", "list"): "[]",
                ("issue", "edit"): "",
                ("label", "create"): "",
            },
        )
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["changed"][0]["tier"], "P0")
        self.assertEqual(payload["changed"][0]["why"], "explicit")

    def test_quiet_suppresses_per_issue_lines(self):
        issues = json.dumps([issue(12, [])])
        rc, out, err, fake = self._run(
            ["--backfill", "--quiet"],
            {
                ("label", "list"): "[]",
                ("issue", "list"): issues,
                ("pr", "list"): "[]",
                ("issue", "edit"): "",
                ("label", "create"): "",
            },
        )
        self.assertEqual(rc, 0, err)
        self.assertNotIn("#12:", out)
        self.assertIn("verdict: OK", out)

    def test_dry_run_makes_no_gh_mutations(self):
        issues = json.dumps([issue(12, [])])
        rc, out, err, fake = self._run(
            ["--backfill", "--dry-run"],
            {
                ("label", "list"): "[]",
                ("issue", "list"): issues,
                ("pr", "list"): "[]",
            },
        )
        self.assertEqual(rc, 0, err)
        mutating = [c for c in fake.calls if c[:2] in
                    (["issue", "edit"], ["label", "create"])]
        self.assertEqual(mutating, [])

    def test_no_arguments_is_a_usage_error(self):
        rc, out, err, fake = self._run([], {})
        self.assertNotEqual(rc, 0)

    def test_set_design_combined_with_backfill_is_a_usage_error(self):
        rc, out, err, fake = self._run(["--set-design", "12", "--backfill"], {})
        self.assertNotEqual(rc, 0)
        self.assertIn("standalone", err)

    def test_gh_not_found_reports_error(self):
        rc, out, err, fake = self._run(["--backfill"], {}, path_override="/nonexistent-only")
        self.assertEqual(rc, 1)
        self.assertIn("gh CLI not found", err)

    def test_ensure_labels_only_skips_the_digest(self):
        rc, out, err, fake = self._run(
            ["--ensure-labels"],
            {("label", "list"): "[]", ("label", "create"): ""},
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("verdict: OK", out)
        # No issue/pr calls means load_digest() (and thus issue_digest.py)
        # never ran — --ensure-labels alone must not touch the backlog.
        self.assertFalse(any(c[:2] == ["issue", "list"] for c in fake.calls))

    def test_set_on_issue_not_in_open_digest_still_labels_it(self):
        # #99 is a valid --set target that the digest does not return (closed,
        # or filtered out) — it must still get labeled, not treated as an error.
        issues = json.dumps([issue(12, [])])
        rc, out, err, fake = self._run(
            ["--set", "99=P1", "--json"],
            {
                ("label", "list"): "[]",
                ("issue", "list"): issues,
                ("pr", "list"): "[]",
                ("issue", "edit"): "",
                ("label", "create"): "",
            },
        )
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["not_open"], [99])
        self.assertEqual(payload["changed"][0]["was"], "not-open")

    def test_set_design_via_main_never_calls_the_digest(self):
        # --set-design alone must not shell out to issue_digest.py — it needs
        # only the repo's label list and the one issue, not the whole backlog.
        # Written without self._run(): that helper returns `fake` only after
        # its own `with FakeGh(...)` block has already exited and cleaned up
        # its tmpdir, so a `fake.calls` check made after it returns is
        # vacuously true/false regardless of what actually ran. Read calls
        # here, inside the block, while the log file still exists.
        responses = {
            ("label", "list"): "[]",
            ("label", "create"): "",
            ("issue", "edit"): "",
        }
        with FakeGh(responses) as fake:
            out, err = io.StringIO(), io.StringIO()
            with patch.dict("os.environ", fake.env, clear=False), \
                    patch.object(sys, "argv", ["apply_priority_labels.py",
                                               "--set-design", "12"]), \
                    redirect_stdout(out), redirect_stderr(err):
                try:
                    rc = apl.main()
                except SystemExit as exc:
                    rc = exc.code
            issue_list_called = any(c[:2] == ["issue", "list"] for c in fake.calls)
        self.assertEqual(rc, 0, err.getvalue())
        self.assertIn("verdict: OK", out.getvalue())
        self.assertFalse(issue_list_called)

    def test_clear_design_via_main_reports_cleared(self):
        view = json.dumps({"labels": [{"name": "blocked: design"}]})
        rc, out, err, fake = self._run(
            ["--clear-design", "12"],
            {("issue", "view"): view, ("issue", "edit"): ""},
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("#12: needs-design cleared", out)

    def test_clear_design_via_main_json_output(self):
        view = json.dumps({"labels": []})
        rc, out, err, fake = self._run(
            ["--clear-design", "12", "--json"],
            {("issue", "view"): view},
        )
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["design_cleared"], [{"number": 12, "removed": []}])

    def test_set_on_already_correct_label_is_unchanged(self):
        issues = json.dumps([issue(12, ["priority: P0"])])
        rc, out, err, fake = self._run(
            ["--set", "12=P0", "--json"],
            {
                ("label", "list"): "[]",
                ("issue", "list"): issues,
                ("pr", "list"): "[]",
            },
        )
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["changed"], [])
        self.assertEqual(payload["unchanged"], [12])


class GhErrorBranchesTest(unittest.TestCase):
    """The direct-exec error paths in gh() and load_digest() — narrow enough
    that unit-level mocks are clearer than routing another fake gh."""

    def test_gh_missing_binary_exits_1(self):
        with patch("apply_priority_labels.subprocess.run",
                   side_effect=FileNotFoundError()):
            with self.assertRaises(SystemExit) as cm:
                apl.gh(["label", "list"])
        self.assertEqual(cm.exception.code, 1)

    def test_gh_timeout_exits_1(self):
        with patch("apply_priority_labels.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=120)):
            with self.assertRaises(SystemExit) as cm:
                apl.gh(["label", "list"])
        self.assertEqual(cm.exception.code, 1)

    def test_gh_generic_failure_exits_1(self):
        with patch("apply_priority_labels.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["gh"], output="", stderr="some other gh error")
            with self.assertRaises(SystemExit) as cm:
                apl.gh(["label", "list"])
        self.assertEqual(cm.exception.code, 1)

    def test_load_digest_nonzero_exit_raises_1(self):
        class FakeProc:
            returncode = 1
            stderr = "boom"
            stdout = ""
        with patch("apply_priority_labels.subprocess.run", return_value=FakeProc()):
            with self.assertRaises(SystemExit) as cm:
                apl.load_digest()
        self.assertEqual(cm.exception.code, 1)

    def test_no_write_access_exits_2(self):
        # The gh() wrapper is what maps a 403 to exit 2 — covered directly
        # rather than via a full subprocess round-trip.
        with patch("apply_priority_labels.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["gh"], output="", stderr="HTTP 403: Resource not accessible")
            with self.assertRaises(SystemExit) as cm:
                apl.gh(["label", "create", "x"])
            self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
