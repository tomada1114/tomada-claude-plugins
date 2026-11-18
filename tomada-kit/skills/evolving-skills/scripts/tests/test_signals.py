"""Tests for signals.py. Every test uses its own temporary state directory."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import signals  # noqa: E402


class SignalsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.state = Path(self._tmp.name) / "state"
        self.ledger = self.state / "signals.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_cli(self, *argv: str, as_json: bool = True):
        args = list(argv) + ["--state-dir", str(self.state)]
        if as_json:
            args.append("--json")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = signals.main(args)
            except SystemExit as exc:
                code = exc.code
        text = out.getvalue()
        payload = json.loads(text) if as_json and code == 0 else text
        return code, payload, err.getvalue()

    def add(self, *, skill="demo", kind="correction", key="wrong-tone", summary="s",
            session="", explicit=False, extra=()):
        argv = ["add", "--skill", skill, "--kind", kind, "--key", key, "--summary", summary]
        if session:
            argv += ["--session", session]
        if explicit:
            argv.append("--explicit")
        argv += list(extra)
        code, payload, err = self.run_cli(*argv)
        self.assertEqual(code, 0, err)
        return payload["id"]

    def raw_rows(self):
        return [json.loads(line) for line in self.ledger.read_text().splitlines() if line]


class AddTests(SignalsTestCase):
    def test_add_writes_full_row(self):
        sig_id = self.add(session="s1", extra=["--evidence", "user said no",
                                                "--source", "user"])
        self.assertRegex(sig_id, r"^SIG-[0-9a-f]{8}$")
        rows = self.raw_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(set(row), {"id", "ts", "skill", "kind", "key", "summary", "evidence",
                                    "session", "source", "explicit", "status"})
        self.assertEqual(row["status"], "open")
        self.assertEqual(row["evidence"], "user said no")
        self.assertEqual(row["source"], "user")
        self.assertFalse(row["explicit"])
        self.assertTrue(row["ts"].endswith("Z"))

    def test_identical_readd_is_idempotent(self):
        first = self.add(session="s1", summary="same")
        second = self.add(session="s1", summary="same")
        self.assertEqual(first, second)
        self.assertEqual(len(self.raw_rows()), 1)
        code, payload, _ = self.run_cli("add", "--skill", "demo", "--kind", "correction",
                                        "--key", "wrong-tone", "--summary", "same",
                                        "--session", "s1")
        self.assertEqual(payload, {"id": first, "created": False})

    def test_different_session_or_summary_appends(self):
        a = self.add(session="s1", summary="same")
        b = self.add(session="s2", summary="same")
        c = self.add(session="s1", summary="other")
        self.assertEqual(len({a, b, c}), 3)

    def test_text_output_prints_id(self):
        code, text, _ = self.run_cli("add", "--skill", "demo", "--kind", "friction", "--key",
                                     "retry-loop", "--summary", "x", as_json=False)
        self.assertEqual(code, 0)
        self.assertRegex(text.strip(), r"^SIG-[0-9a-f]{8}$")

    def test_key_validation(self):
        for bad in ("Bad-Key", "-leading", "a", "has space", "under_score", "x" * 65):
            code, _, err = self.run_cli("add", "--skill", "demo", "--kind", "correction",
                                        "--key", bad, "--summary", "s")
            self.assertEqual(code, 3, bad)
            self.assertIn("--key", err)
        self.assertFalse(self.ledger.exists())
        self.add(key="ok")
        self.add(key="a1-b2-" + "c" * 58)

    def test_bad_kind_and_empty_fields(self):
        code, _, _ = self.run_cli("add", "--skill", "demo", "--kind", "nope", "--key",
                                  "abc", "--summary", "s")
        self.assertEqual(code, 3)
        code, _, err = self.run_cli("add", "--skill", " ", "--kind", "correction", "--key",
                                    "abc", "--summary", "s")
        self.assertEqual(code, 3)
        self.assertIn("--skill", err)
        code, _, err = self.run_cli("add", "--skill", "demo", "--kind", "correction", "--key",
                                    "abc", "--summary", "  ")
        self.assertEqual(code, 3)
        self.assertIn("--summary", err)

    def test_add_signal_rejects_bad_kind_and_source_directly(self):
        with self.assertRaises(signals.UsageError):
            signals.add_signal(self.state, skill="d", kind="nope", key="abc", summary="s")
        with self.assertRaises(signals.UsageError):
            signals.add_signal(self.state, skill="d", kind="friction", key="abc",
                               summary="s", source="nope")

    def test_new_id_avoids_collisions(self):
        with mock.patch.object(signals.secrets, "token_hex", side_effect=["aaaaaaaa", "bbbbbbbb"]):
            self.assertEqual(signals.new_id({"SIG-aaaaaaaa"}), "SIG-bbbbbbbb")


class MergeAndListTests(SignalsTestCase):
    def test_merge_by_id_later_wins_and_keeps_ts(self):
        sig_id = self.add(session="s1")
        created_ts = self.raw_rows()[0]["ts"]
        code, _, _ = self.run_cli("set", "--id", sig_id, "--status", "applied",
                                  "--commit", "abc123", "--note", "done")
        self.assertEqual(code, 0)
        code, _, _ = self.run_cli("set", "--id", sig_id, "--status", "reverted")
        self.assertEqual(code, 0)
        code, rows, _ = self.run_cli("list")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["status"], "reverted")
        self.assertEqual(row["commit"], "abc123")  # not erased by the later update
        self.assertEqual(row["note"], "done")
        self.assertEqual(row["ts"], created_ts)
        self.assertIn("updated", row)
        self.assertEqual(len(self.raw_rows()), 3)

    def test_merge_function(self):
        rows = [{"id": "A", "x": 1, "y": 1}, {"id": "B", "x": 5}, {"id": "A", "y": 2}]
        self.assertEqual(signals.merge(rows), [{"id": "A", "x": 1, "y": 2}, {"id": "B", "x": 5}])

    def test_list_filters_and_order(self):
        a = self.add(skill="one", key="k-a", summary="1")
        b = self.add(skill="two", key="k-b", summary="2")
        c = self.add(skill="one", key="k-b", summary="3")
        self.run_cli("set", "--id", b, "--status", "rejected")
        _, rows, _ = self.run_cli("list")
        self.assertEqual([r["id"] for r in rows], [a, b, c])
        _, rows, _ = self.run_cli("list", "--skill", "one")
        self.assertEqual([r["id"] for r in rows], [a, c])
        _, rows, _ = self.run_cli("list", "--key", "k-b")
        self.assertEqual([r["id"] for r in rows], [b, c])
        _, rows, _ = self.run_cli("list", "--status", "rejected", "blocked")
        self.assertEqual([r["id"] for r in rows], [b])
        _, rows, _ = self.run_cli("list", "--status", "open", "--status", "rejected")
        self.assertEqual([r["id"] for r in rows], [a, b, c])

    def test_list_text_and_empty(self):
        code, text, _ = self.run_cli("list", as_json=False)
        self.assertEqual((code, text.strip()), (0, "(no signals)"))
        self.add(session="s9", explicit=True, summary="hello")
        code, text, _ = self.run_cli("list", as_json=False)
        self.assertIn("demo/wrong-tone", text)
        self.assertIn("explicit", text)
        self.assertIn("session=s9", text)

    def test_malformed_lines_are_skipped_with_warning(self):
        sig_id = self.add()
        with self.ledger.open("a") as fh:
            fh.write("{not json\n\n[1, 2]\n{\"no\": \"id\"}\n")
        code, rows, err = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertEqual([r["id"] for r in rows], [sig_id])
        self.assertEqual(err.count("malformed"), 3)


class PromotableTests(SignalsTestCase):
    def promotable(self, *extra):
        code, groups, err = self.run_cli("promotable", *extra)
        self.assertEqual(code, 0, err)
        return groups

    def test_empty_ledger(self):
        self.assertEqual(self.promotable(), [])
        code, text, _ = self.run_cli("promotable", as_json=False)
        self.assertEqual(text.strip(), "(nothing promotable)")

    def test_explicit_flag_promotes_single_signal(self):
        sig_id = self.add(kind="instruction", key="always-cite", explicit=True, session="s1")
        groups = self.promotable()
        self.assertEqual(len(groups), 1)
        g = groups[0]
        self.assertEqual(g["signals"], [sig_id])
        self.assertTrue(g["explicit"])
        self.assertEqual(g["sessions"], 1)
        self.assertEqual(g["kinds"], ["instruction"])
        self.assertEqual(set(g), {"skill", "key", "signals", "sessions", "explicit", "kinds",
                                  "summaries"})

    def test_two_sessions_promote(self):
        a = self.add(session="s1", summary="first", kind="correction")
        b = self.add(session="s2", summary="second", kind="self-check-fail")
        groups = self.promotable()
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["signals"], [a, b])
        self.assertEqual(groups[0]["sessions"], 2)
        self.assertFalse(groups[0]["explicit"])
        self.assertEqual(groups[0]["kinds"], ["correction", "self-check-fail"])
        self.assertEqual(groups[0]["summaries"], ["first", "second"])
        code, text, _ = self.run_cli("promotable", as_json=False)
        self.assertIn("demo/wrong-tone  sessions=2", text)

    def test_two_signals_one_session_do_not_promote(self):
        self.add(session="s1", summary="first")
        self.add(session="s1", summary="second")
        self.add(session="", summary="no session")
        self.add(session="   ", summary="blank session")
        self.assertEqual(self.promotable(), [])
        self.assertEqual(len(self.promotable("--min-sessions", "1")), 1)

    def test_groups_are_per_skill_and_key(self):
        self.add(skill="one", key="k-a", session="s1")
        self.add(skill="two", key="k-a", session="s2")
        self.add(skill="one", key="k-b", session="s2")
        self.assertEqual(self.promotable(), [])
        self.add(skill="one", key="k-a", session="s3")
        groups = self.promotable()
        self.assertEqual([(g["skill"], g["key"]) for g in groups], [("one", "k-a")])
        self.assertEqual(self.promotable("--skill", "two"), [])

    def test_rejected_do_not_count_and_fresh_signals_bring_group_back(self):
        a = self.add(session="s1", summary="first")
        b = self.add(session="s2", summary="second")
        code, _, _ = self.run_cli("set", "--id", a, "--id", b, "--status", "rejected",
                                  "--run", "/tmp/run-1")
        self.assertEqual(code, 0)
        self.assertEqual(self.promotable(), [])
        # Re-harvesting the same incident returns the old id and does not revive the group.
        self.assertEqual(self.add(session="s1", summary="first"), a)
        self.assertEqual(self.promotable(), [])
        # One fresh signal alone is not enough.
        c = self.add(session="s3", summary="third")
        self.assertEqual(self.promotable(), [])
        d = self.add(session="s4", summary="fourth")
        groups = self.promotable()
        self.assertEqual(groups[0]["signals"], [c, d])

    def test_deferred_counts(self):
        a = self.add(session="s1", summary="first")
        self.run_cli("set", "--id", a, "--status", "deferred")
        self.add(session="s2", summary="second")
        self.assertEqual(len(self.promotable()), 1)

    def test_min_sessions_must_be_positive(self):
        code, _, err = self.run_cli("promotable", "--min-sessions", "0")
        self.assertEqual(code, 3)
        self.assertIn("min-sessions", err)


class SetTests(SignalsTestCase):
    def test_unknown_id_exits_3_and_writes_nothing(self):
        a = self.add()
        before = self.ledger.read_text()
        code, _, err = self.run_cli("set", "--id", a, "--id", "SIG-deadbeef",
                                    "--status", "rejected")
        self.assertEqual(code, 3)
        self.assertIn("SIG-deadbeef", err)
        self.assertEqual(self.ledger.read_text(), before)

    def test_unknown_id_on_empty_ledger(self):
        code, _, _ = self.run_cli("set", "--id", "SIG-00000000", "--status", "open")
        self.assertEqual(code, 3)

    def test_applied_requires_commit(self):
        a = self.add()
        code, _, err = self.run_cli("set", "--id", a, "--status", "applied")
        self.assertEqual(code, 3)
        self.assertIn("--commit", err)
        self.assertEqual(len(self.raw_rows()), 1)

    def test_bad_status(self):
        a = self.add()
        code, _, _ = self.run_cli("set", "--id", a, "--status", "done")
        self.assertEqual(code, 3)
        with self.assertRaises(signals.UsageError):
            signals.set_status(self.state, [a], "done")

    def test_set_writes_only_given_fields_and_dedupes_ids(self):
        a = self.add()
        code, updates, _ = self.run_cli("set", "--id", a, "--id", a, "--status", "blocked",
                                        "--run", "runs/1")
        self.assertEqual(code, 0)
        self.assertEqual(len(updates), 1)
        self.assertEqual(set(updates[0]), {"id", "updated", "status", "run"})
        code, text, _ = self.run_cli("set", "--id", a, "--status", "open", as_json=False)
        self.assertEqual(text.strip(), f"{a} -> open")

    def test_missing_required_argument_exits_3(self):
        code, _, _ = self.run_cli("set", "--status", "open")
        self.assertEqual(code, 3)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                signals.main([])
        self.assertEqual(ctx.exception.code, 3)


class StatsTests(SignalsTestCase):
    def test_stats(self):
        a = self.add(skill="one", key="k-a", session="s1")
        self.add(skill="one", key="k-a", session="s2")
        b = self.add(skill="two", key="k-b", session="s1")
        self.add(skill="two", key="k-c", explicit=True)
        self.run_cli("set", "--id", b, "--status", "rejected")
        self.run_cli("set", "--id", a, "--status", "deferred")
        code, stats, _ = self.run_cli("stats")
        self.assertEqual(code, 0)
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["skills"], {"one": {"deferred": 1, "open": 1},
                                           "two": {"open": 1, "rejected": 1}})
        self.assertEqual(stats["promotable_groups"], 2)
        _, stats, _ = self.run_cli("stats", "--skill", "two")
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["promotable_groups"], 1)
        code, text, _ = self.run_cli("stats", as_json=False)
        self.assertIn("one: deferred=1, open=1", text)
        self.assertIn("promotable_groups=2", text)

    def test_stats_empty(self):
        _, stats, _ = self.run_cli("stats")
        self.assertEqual(stats, {"total": 0, "skills": {}, "promotable_groups": 0})


class StateDirTests(unittest.TestCase):
    def test_default_state_dir_uses_env(self):
        with mock.patch.dict(os.environ, {"AGENT_SKILL_STATE_DIR": "/x/y"}):
            self.assertEqual(signals.default_state_dir(), Path("/x/y/evolving-skills"))
        env = {k: v for k, v in os.environ.items() if k != "AGENT_SKILL_STATE_DIR"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(signals.default_state_dir(),
                             Path("~/.local/state/agent-skills").expanduser() / "evolving-skills")

    def test_env_state_dir_used_without_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"AGENT_SKILL_STATE_DIR": tmp}):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = signals.main(["add", "--skill", "d", "--kind", "friction", "--key",
                                         "abc", "--summary", "s"])
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / "evolving-skills" / "signals.jsonl").exists())

    def test_script_runs_as_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "signals.py"), "stats", "--json",
                 "--state-dir", tmp], capture_output=True, text=True, env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["total"], 0)


if __name__ == "__main__":
    unittest.main()
