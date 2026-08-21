#!/usr/bin/env python3
"""Tests for run_record.py. Stdlib-only (unittest).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the shipping-issues skill directory)
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_record as rr  # noqa: E402


class StateDirTest(unittest.TestCase):
    def test_env_override_wins(self):
        with patch.dict("os.environ", {"AGENT_SKILL_STATE_DIR": "/tmp/custom-state"}):
            self.assertEqual(rr.state_dir(), Path("/tmp/custom-state"))

    def test_default_is_xdg_style_home_path(self):
        env = dict(os.environ)
        env.pop("AGENT_SKILL_STATE_DIR", None)
        with patch.dict("os.environ", env, clear=True):
            self.assertEqual(rr.state_dir(),
                              Path.home() / ".local" / "state" / "agent-skills")


class RecordPathTest(unittest.TestCase):
    def test_owner_repo_becomes_double_underscore_dir(self):
        with patch.dict("os.environ", {"AGENT_SKILL_STATE_DIR": "/state"}):
            self.assertEqual(
                rr.record_path("acme/widgets"),
                Path("/state/shipping-issues/acme__widgets/run.md"),
            )


class ParseFieldsTest(unittest.TestCase):
    def test_parses_multiple_pairs_in_order(self):
        self.assertEqual(
            rr.parse_fields(["pr=12", "issue=7", "tier=P1"]),
            [("pr", "12"), ("issue", "7"), ("tier", "P1")],
        )

    def test_value_may_contain_equals_sign(self):
        self.assertEqual(rr.parse_fields(["url=https://x/y?z=1"]),
                          [("url", "https://x/y?z=1")])

    def test_missing_equals_exits_2(self):
        with self.assertRaises(SystemExit) as cm:
            rr.parse_fields(["not-a-pair"])
        self.assertEqual(cm.exception.code, 2)

    def test_empty_key_exits_2(self):
        with self.assertRaises(SystemExit) as cm:
            rr.parse_fields(["=value"])
        self.assertEqual(cm.exception.code, 2)


class FormatEntryTest(unittest.TestCase):
    NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    def test_plain_event_no_fields(self):
        entry = rr.format_entry("note", [], None, self.NOW)
        self.assertEqual(entry, "- 2026-01-02T03:04:05Z note\n")

    def test_fields_render_as_k_equals_v(self):
        entry = rr.format_entry("merged", [("pr", "12"), ("issue", "7")], None, self.NOW)
        self.assertEqual(entry, "- 2026-01-02T03:04:05Z merged — pr=12 issue=7\n")

    def test_body_appends_fenced_block(self):
        entry = rr.format_entry("selection", [], "Selected: #12\nWhy: reasons", self.NOW)
        self.assertIn("- 2026-01-02T03:04:05Z selection\n", entry)
        self.assertIn("```\nSelected: #12\nWhy: reasons\n```\n", entry)

    def test_run_start_gets_a_heading(self):
        entry = rr.format_entry("run-start", [], None, self.NOW)
        self.assertTrue(entry.startswith("## run 2026-01-02T03:04:05Z\n\n"))
        self.assertIn("- 2026-01-02T03:04:05Z run-start\n", entry)

    def test_non_run_start_event_has_no_heading(self):
        entry = rr.format_entry("ci", [], None, self.NOW)
        self.assertNotIn("## run", entry)

    def test_body_with_embedded_triple_backtick_gets_longer_fence(self):
        body = "before\n```\ncode\n```\nafter"
        entry = rr.format_entry("selection", [], body, self.NOW)
        # A 3-backtick fence would prematurely close on the embedded block;
        # the fence actually used must be longer than any run inside body.
        self.assertNotIn("\n```\nbefore", entry)
        self.assertIn("\n````\nbefore\n```\ncode\n```\nafter\n````\n", entry)


class FenceForTest(unittest.TestCase):
    def test_no_backticks_uses_minimum_fence(self):
        self.assertEqual(rr._fence_for("plain text"), "```")

    def test_fence_longer_than_longest_run(self):
        self.assertEqual(rr._fence_for("has ``` and ```` runs"), "`````")


class ResolveRepoTest(unittest.TestCase):
    def test_explicit_repo_short_circuits_gh(self):
        with patch("run_record.subprocess.run") as mock_run:
            self.assertEqual(rr.resolve_repo("acme/widgets"), "acme/widgets")
            mock_run.assert_not_called()

    def test_falls_back_to_gh_repo_view(self):
        class FakeProc:
            stdout = "acme/widgets\n"
        with patch("run_record.subprocess.run", return_value=FakeProc()):
            self.assertEqual(rr.resolve_repo(None), "acme/widgets")

    def test_empty_gh_output_returns_none(self):
        class FakeProc:
            stdout = ""
        with patch("run_record.subprocess.run", return_value=FakeProc()):
            self.assertIsNone(rr.resolve_repo(None))


class MainTest(unittest.TestCase):
    def test_appends_and_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state"
            with patch.dict("os.environ", {"AGENT_SKILL_STATE_DIR": str(state)}):
                rc = rr.main(["--repo", "acme/widgets", "--event", "run-start"])
                self.assertEqual(rc, 0)
                rc = rr.main(["--repo", "acme/widgets", "--event", "merged",
                              "--field", "pr=1", "--field", "issue=2"])
                self.assertEqual(rc, 0)
            content = (state / "shipping-issues" / "acme__widgets" / "run.md").read_text()
            self.assertIn("## run ", content)
            self.assertIn("run-start", content)
            self.assertIn("merged — pr=1 issue=2", content)

    def test_second_call_appends_not_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state"
            with patch.dict("os.environ", {"AGENT_SKILL_STATE_DIR": str(state)}):
                rr.main(["--repo", "acme/widgets", "--event", "note", "--field", "a=1"])
                rr.main(["--repo", "acme/widgets", "--event", "note", "--field", "a=2"])
            content = (state / "shipping-issues" / "acme__widgets" / "run.md").read_text()
            self.assertEqual(content.count("note"), 2)
            self.assertIn("a=1", content)
            self.assertIn("a=2", content)

    def test_json_output_reports_path_and_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state"
            with patch.dict("os.environ", {"AGENT_SKILL_STATE_DIR": str(state)}):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = rr.main(["--repo", "acme/widgets", "--event", "note", "--json"])
                self.assertEqual(rc, 0)
                out = json.loads(buf.getvalue())
                self.assertEqual(out["event"], "note")
                self.assertEqual(out["repo"], "acme/widgets")
                self.assertGreater(out["bytes_appended"], 0)
                self.assertTrue(out["path"].endswith("shipping-issues/acme__widgets/run.md"))

    def test_body_file_appended_as_fence(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state"
            body = Path(td) / "body.txt"
            body.write_text("Selected: #9\nWhy: leverage")
            with patch.dict("os.environ", {"AGENT_SKILL_STATE_DIR": str(state)}):
                rc = rr.main(["--repo", "acme/widgets", "--event", "selection",
                              "--body-file", str(body)])
                self.assertEqual(rc, 0)
            content = (state / "shipping-issues" / "acme__widgets" / "run.md").read_text()
            self.assertIn("Selected: #9\nWhy: leverage", content)

    def test_missing_body_file_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state"
            with patch.dict("os.environ", {"AGENT_SKILL_STATE_DIR": str(state)}):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    rc = rr.main(["--repo", "acme/widgets", "--event", "note",
                                  "--body-file", str(Path(td) / "missing.txt")])
                self.assertEqual(rc, 2)

    def test_unresolvable_repo_exits_1(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state"
            with patch.dict("os.environ", {"AGENT_SKILL_STATE_DIR": str(state)}):
                with patch("run_record.resolve_repo", return_value=None):
                    buf = io.StringIO()
                    with redirect_stderr(buf):
                        rc = rr.main(["--event", "note"])
                    self.assertEqual(rc, 1)

    def test_unwritable_parent_exits_1(self):
        with tempfile.TemporaryDirectory() as td:
            # A file where a directory needs to go makes mkdir(parents=True) fail.
            blocker = Path(td) / "state"
            blocker.write_text("not a directory")
            with patch.dict("os.environ", {"AGENT_SKILL_STATE_DIR": str(blocker)}):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    rc = rr.main(["--repo", "acme/widgets", "--event", "note"])
                self.assertEqual(rc, 1)

    def test_repo_without_slash_rejected(self):
        # No "/" means record_path()'s replace("/", "__") is a no-op, so a
        # value of exactly ".." would otherwise become a literal parent-dir
        # path component — reject anything that isn't OWNER/NAME up front.
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state"
            with patch.dict("os.environ", {"AGENT_SKILL_STATE_DIR": str(state)}):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    rc = rr.main(["--repo", "..", "--event", "note"])
                self.assertEqual(rc, 2)
                self.assertFalse(state.exists())

    def test_repo_with_extra_slash_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state"
            with patch.dict("os.environ", {"AGENT_SKILL_STATE_DIR": str(state)}):
                rc = rr.main(["--repo", "a/b/c", "--event", "note"])
                self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
