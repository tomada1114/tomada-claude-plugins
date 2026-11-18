#!/usr/bin/env python3
"""Tests for auto_run.py. Temp state dirs only; every process launch is patched."""

import contextlib
import datetime
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import auto_run as ar  # noqa: E402


def skill_event(name):
    return {"type": "assistant", "sessionId": "S1", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": name}}]}}


def user_event(text):
    return {"type": "user", "sessionId": "S1", "message": {"content": text}}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        env = {k: v for k, v in os.environ.items()
               if k not in ("EVOLVING_SKILLS_CHILD", "EVOLVING_SKILLS_AUTO")}
        env["AGENT_SKILL_STATE_DIR"] = str(self.dir / "state")
        self.env_patch = mock.patch.dict(os.environ, env, clear=True)
        self.env_patch.start()
        self.skills_root = self.dir / "skills"
        (self.skills_root / "alpha").mkdir(parents=True)
        (self.skills_root / "alpha" / "SKILL.md").write_text("x")
        self.root_patch = mock.patch.object(ar, "SKILLS_ROOT", self.skills_root)
        self.root_patch.start()
        self.config_patch = mock.patch.object(ar, "CONFIG_PATH", self.dir / "no-config.json")
        self.config_patch.start()
        self.auto = self.dir / "state" / "evolving-skills" / "auto"
        self.cwd = self.dir / "project"
        self.cwd.mkdir()

    def tearDown(self):
        self.config_patch.stop()
        self.root_patch.stop()
        self.env_patch.stop()
        self.tmp.cleanup()

    def transcript(self, skill="alpha", followups=2):
        path = self.dir / "t.jsonl"
        events = [user_event("start"), skill_event(skill)] + [
            user_event("followup %d" % i) for i in range(followups)]
        path.write_text("\n".join(json.dumps(e) for e in events) + "\n")
        return path

    def call(self, argv, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(stdin)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ar.main(argv)
        return code, out.getvalue(), err.getvalue()

    def hook_log(self):
        path = self.auto / "hook.log"
        return path.read_text().splitlines() if path.exists() else []


class HookTests(Base):
    def payload(self, transcript=None, session="S1"):
        data = {"session_id": session, "cwd": str(self.cwd), "hook_event_name": "SessionEnd",
                "reason": "exit"}
        if transcript is not None:
            data["transcript_path"] = str(transcript)
        return json.dumps(data)

    def run_hook(self, stdin, promotable_out="[]", extra=()):
        calls = {"run": [], "spawn": []}

        def fake_run(argv, cwd=None, timeout=None, **kw):
            calls["run"].append((argv, cwd, timeout, kw))
            return 0, promotable_out

        def fake_spawn(argv, cwd, env, log_path):
            calls["spawn"].append((argv, cwd, env, log_path))
            return 4242

        with mock.patch.object(ar, "run_cmd", side_effect=fake_run), \
                mock.patch.object(ar, "spawn_detached", side_effect=fake_spawn):
            code, out, err = self.call(["hook"] + list(extra), stdin)
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        return calls, self.hook_log()

    def decision(self, lines):
        self.assertTrue(lines)
        parts = lines[-1].split(" ")
        self.assertEqual(parts[1], "S1")
        return parts[2]

    def test_skip_child(self):
        os.environ["EVOLVING_SKILLS_CHILD"] = "1"
        calls, lines = self.run_hook(self.payload(self.transcript()))
        self.assertEqual(self.decision(lines), "skip-child")
        self.assertEqual(calls["spawn"], [])

    def test_skip_disabled_by_file(self):
        self.auto.mkdir(parents=True)
        (self.auto / "disabled").write_text("x")
        calls, lines = self.run_hook(self.payload(self.transcript()))
        self.assertEqual(self.decision(lines), "skip-disabled")
        self.assertEqual(calls["run"], [])

    def test_skip_disabled_by_env(self):
        os.environ["EVOLVING_SKILLS_AUTO"] = "0"
        _, lines = self.run_hook(self.payload(self.transcript()))
        self.assertEqual(self.decision(lines), "skip-disabled")
        self.assertIn("EVOLVING_SKILLS_AUTO", lines[-1])

    def test_skip_no_transcript(self):
        _, lines = self.run_hook(self.payload())
        self.assertEqual(self.decision(lines), "skip-no-transcript")
        _, lines = self.run_hook(self.payload(self.dir / "missing.jsonl"))
        self.assertEqual(self.decision(lines), "skip-no-transcript")

    def test_bad_stdin_is_no_transcript(self):
        for stdin in ("not json", "[1]", ""):
            calls, lines = self.run_hook(stdin)
            self.assertIn(" skip-no-transcript", lines[-1])
            self.assertEqual(lines[-1].split(" ")[1], "-")

    def test_skip_nothing_to_do(self):
        calls, lines = self.run_hook(self.payload(self.transcript(followups=1)))
        self.assertEqual(self.decision(lines), "skip-nothing-to-do")
        self.assertEqual(calls["spawn"], [])
        argv, cwd, timeout, _ = calls["run"][0]
        self.assertEqual(argv, [sys.executable, str(SCRIPTS / "signals.py"), "promotable", "--json"])
        self.assertLess(timeout, 15)

    def test_unknown_skill_is_nothing_to_do(self):
        _, lines = self.run_hook(self.payload(self.transcript(skill="not-here")))
        self.assertEqual(self.decision(lines), "skip-nothing-to-do")

    def make_project_skill(self):
        proj_root = self.cwd / ".claude" / "skills" / "beta"
        proj_root.mkdir(parents=True)
        (proj_root / "SKILL.md").write_text("x")

    def test_project_skills_ignored_by_default(self):
        self.make_project_skill()
        calls, lines = self.run_hook(self.payload(self.transcript(skill="beta")))
        self.assertEqual(self.decision(lines), "skip-nothing-to-do")
        self.assertEqual(calls["spawn"], [])

    def test_project_skills_count_when_enabled(self):
        self.make_project_skill()
        cfg_path = self.dir / "cfg.json"
        cfg_path.write_text(json.dumps({"project_roots": True}))
        with mock.patch.object(ar, "CONFIG_PATH", cfg_path):
            calls, lines = self.run_hook(self.payload(self.transcript(skill="beta")))
        self.assertEqual(self.decision(lines), "launch")
        digest = json.loads(Path(calls["spawn"][0][0][-1]).read_text())
        self.assertEqual(digest["skills_used"][0]["root"], str(self.cwd / ".claude" / "skills"))

    def test_project_roots_requires_true(self):
        self.make_project_skill()
        cfg_path = self.dir / "cfg.json"
        cfg_path.write_text(json.dumps({"project_roots": "yes"}))
        with mock.patch.object(ar, "CONFIG_PATH", cfg_path):
            _, lines = self.run_hook(self.payload(self.transcript(skill="beta")))
        self.assertEqual(self.decision(lines), "skip-nothing-to-do")

    def test_skip_locked(self):
        self.auto.mkdir(parents=True)
        (self.auto / "lock").write_text(json.dumps({"pid": 1, "time": ar.iso(ar.utcnow())}))
        calls, lines = self.run_hook(self.payload(self.transcript()))
        self.assertEqual(self.decision(lines), "skip-locked")
        self.assertEqual(calls["spawn"], [])

    def test_launch_with_digest(self):
        calls, lines = self.run_hook(self.payload(self.transcript()))
        self.assertEqual(self.decision(lines), "launch")
        self.assertEqual(len(calls["spawn"]), 1)
        argv, cwd, env, log_path = calls["spawn"][0]
        digest_path = self.auto / "digests" / "S1.json"
        self.assertEqual(argv, [sys.executable, str(SCRIPTS / "auto_run.py"), "run",
                                "--cwd", str(self.cwd), "--digest", str(digest_path)])
        self.assertEqual(cwd, str(self.cwd))
        self.assertEqual(env["EVOLVING_SKILLS_CHILD"], "1")
        self.assertTrue(str(log_path).startswith(str(self.auto / "logs")))
        digest = json.loads(digest_path.read_text())
        self.assertEqual(len(digest["followups"]), 2)

    def test_launch_without_digest_and_claude_bin(self):
        calls, lines = self.run_hook(self.payload(self.transcript(followups=0)),
                                     promotable_out='[{"group": 1}]',
                                     extra=["--claude-bin", "/opt/fake-claude"])
        self.assertEqual(self.decision(lines), "launch")
        argv = calls["spawn"][0][0]
        self.assertNotIn("--digest", argv)
        self.assertEqual(argv[-2:], ["--claude-bin", "/opt/fake-claude"])
        self.assertFalse((self.auto / "digests").exists())

    def test_launch_when_lock_stale(self):
        self.auto.mkdir(parents=True)
        old = ar.utcnow() - datetime.timedelta(minutes=500)
        (self.auto / "lock").write_text(json.dumps({"pid": 1, "time": ar.iso(old)}))
        _, lines = self.run_hook(self.payload(self.transcript()))
        self.assertEqual(self.decision(lines), "launch")

    def test_hook_survives_internal_exception(self):
        with mock.patch.object(ar, "hook_decide", side_effect=RuntimeError("kaboom")):
            code, out, _ = self.call(["hook"], self.payload(self.transcript()))
        self.assertEqual((code, out), (0, ""))
        self.assertIn(" error ", self.hook_log()[-1])
        self.assertIn("kaboom", self.hook_log()[-1])

    def test_hook_survives_bad_args_and_unwritable_log(self):
        os.environ["EVOLVING_SKILLS_CHILD"] = "1"
        code, out, _ = self.call(["hook", "--claude-bin"], self.payload())
        self.assertEqual((code, out), (0, ""))
        with mock.patch("builtins.open", side_effect=OSError("ro")):
            ar.hook_log("S1", "x", "y")  # must not raise

    def test_promotable_bad_output(self):
        for result in ((1, "[1]"), (0, "not json"), (0, "{}"), (0, "[]")):
            with mock.patch.object(ar, "run_cmd", return_value=result):
                self.assertFalse(ar.promotable())
        with mock.patch.object(ar, "run_cmd", return_value=(0, "[1]")):
            self.assertTrue(ar.promotable())


class RunTests(Base):
    def setUp(self):
        super().setUp()
        self.calls = []
        self.promotable = ["[]"]
        self.git_top = str(self.dir / "repo")

        def fake_run(argv, cwd=None, timeout=None, env=None, log_path=None):
            self.calls.append({"argv": argv, "cwd": cwd, "timeout": timeout, "env": env,
                               "log_path": log_path})
            if argv[:2] == ["git", "rev-parse"]:
                return 0, self.git_top + "\n"
            if len(argv) > 1 and argv[1].endswith("signals.py"):
                return 0, self.promotable[0]
            return 0, ""

        self.run_patch = mock.patch.object(ar, "run_cmd", side_effect=fake_run)
        self.run_patch.start()

    def tearDown(self):
        self.run_patch.stop()
        super().tearDown()

    def claude_calls(self):
        return [c for c in self.calls if c["argv"][0] == "claude"]

    def test_harvest_then_improve_exact_argv(self):
        self.promotable[0] = '[{"g": 1}]'
        code, out, _ = self.call(["run", "--cwd", str(self.cwd), "--digest", "/d/S1.json"])
        self.assertEqual(code, 0)
        harvest, improve = self.claude_calls()
        bash_rule = "Bash(python3 %s/*)" % SCRIPTS
        self.assertEqual(harvest["argv"], [
            "claude", "-p", "/evolving-skills harvest /d/S1.json", "--agent", "scout",
            "--max-budget-usd", "0.5", "--allowedTools", "Read", "Glob", "Grep", "Skill", bash_rule])
        self.assertEqual(harvest["cwd"], str(self.cwd))
        self.assertEqual(harvest["timeout"], 20 * 60)
        self.assertEqual(harvest["env"]["EVOLVING_SKILLS_CHILD"], "1")
        self.assertTrue(str(harvest["log_path"]).endswith("-harvest.log"))
        self.assertEqual(improve["argv"], [
            "claude", "-p", "/evolving-skills improve --max-groups 2 --eval-max-cost-usd 1",
            "--agent", "executor",
            "--max-budget-usd", "5", "--allowedTools", "Read", "Glob", "Grep", "Skill", "Edit",
            "Write", bash_rule])
        self.assertEqual(improve["cwd"], self.git_top)
        self.assertEqual(improve["timeout"], 60 * 60)
        self.assertEqual(improve["env"]["EVOLVING_SKILLS_CHILD"], "1")
        self.assertTrue(str(improve["log_path"]).endswith("-improve.log"))
        git_call = [c for c in self.calls if c["argv"][0] == "git"][0]
        self.assertEqual(git_call["cwd"], str(self.skills_root))
        self.assertEqual(ar.read_counts(), {"harvest": 1, "improve": 1})
        self.assertEqual([r["pass"] for r in json.loads(out)["ran"]], ["harvest", "improve"])
        self.assertFalse((self.auto / "lock").exists())
        self.assertTrue((self.auto / "lock.done").exists())

    def test_no_digest_no_promotable_runs_nothing(self):
        code, out, _ = self.call(["run", "--cwd", str(self.cwd), "--claude-bin", "cc"])
        self.assertEqual(code, 0)
        self.assertEqual(self.claude_calls(), [])
        self.assertEqual(json.loads(out), {"ran": []})

    def test_daily_caps_respected(self):
        self.promotable[0] = "[1]"
        self.auto.mkdir(parents=True)
        ar.counts_path().write_text(json.dumps({"harvest": 6, "improve": 2}))
        self.call(["run", "--cwd", str(self.cwd), "--digest", "/d.json"])
        self.assertEqual(self.claude_calls(), [])
        self.assertEqual(ar.read_counts(), {"harvest": 6, "improve": 2})

    def test_count_increments_on_failure(self):
        def failing(argv, cwd=None, timeout=None, env=None, log_path=None):
            return (124, "") if argv[0] == "claude" else (0, "[]")

        with mock.patch.object(ar, "run_cmd", side_effect=failing):
            self.call(["run", "--cwd", str(self.cwd), "--digest", "/d.json"])
        self.assertEqual(ar.read_counts()["harvest"], 1)

    def test_stale_lock_replaced(self):
        self.auto.mkdir(parents=True)
        old = ar.utcnow() - datetime.timedelta(minutes=121)
        (self.auto / "lock").write_text(json.dumps({"pid": 1, "time": ar.iso(old)}))
        code, _, _ = self.call(["run", "--cwd", str(self.cwd), "--digest", "/d.json"])
        self.assertEqual(code, 0)
        self.assertEqual(len(self.claude_calls()), 1)
        self.assertEqual(len(list(self.auto.glob("lock.stale-*"))), 1)
        self.assertTrue((self.auto / "lock.done").exists())

    def test_stale_lock_by_mtime_when_unparseable(self):
        self.auto.mkdir(parents=True)
        lock = self.auto / "lock"
        lock.write_text("garbage")
        old = (ar.utcnow() - datetime.timedelta(hours=5)).timestamp()
        os.utime(str(lock), (old, old))
        self.call(["run", "--cwd", str(self.cwd), "--digest", "/d.json"])
        self.assertEqual(len(self.claude_calls()), 1)

    def test_live_lock_blocks_run(self):
        self.auto.mkdir(parents=True)
        (self.auto / "lock").write_text(json.dumps({"pid": 1, "time": ar.iso(ar.utcnow())}))
        code, out, _ = self.call(["run", "--cwd", str(self.cwd), "--digest", "/d.json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["skipped"], "locked")
        self.assertEqual(self.claude_calls(), [])
        self.assertTrue((self.auto / "lock").exists())

    def test_lock_released_on_exception(self):
        with mock.patch.object(ar, "claude_argv", side_effect=RuntimeError("x")):
            with self.assertRaises(RuntimeError):
                self.call(["run", "--cwd", str(self.cwd), "--digest", "/d.json"])
        self.assertFalse((self.auto / "lock").exists())
        self.assertTrue((self.auto / "lock.done").exists())

    def test_lock_edge_cases(self):
        cfg = ar.load_config()
        self.auto.mkdir(parents=True)
        (self.auto / "lock").write_text("{}")
        with mock.patch.object(ar, "lock_info", return_value=(True, True, None)), \
                mock.patch.object(ar.os, "replace", side_effect=OSError("busy")):
            self.assertFalse(ar.acquire_lock(cfg))
        with mock.patch.object(ar, "lock_info", return_value=(False, False, None)):
            self.assertFalse(ar.acquire_lock(cfg))
        with mock.patch.object(Path, "stat", side_effect=OSError("gone")):
            self.assertEqual(ar.lock_info(cfg), (False, False, None))
        ar.release_lock()
        ar.release_lock()  # no lock: no error

    def test_git_toplevel_fallback(self):
        with mock.patch.object(ar, "run_cmd", return_value=(128, "")):
            self.assertEqual(ar.git_toplevel(self.skills_root), self.skills_root)

    def test_read_counts_ignores_bad_file(self):
        self.auto.mkdir(parents=True)
        ar.counts_path().write_text("not json")
        self.assertEqual(ar.read_counts(), {"harvest": 0, "improve": 0})
        ar.counts_path().write_text('{"harvest": "x", "improve": 3}')
        self.assertEqual(ar.read_counts(), {"harvest": 0, "improve": 3})


class CommandTests(Base):
    def test_status(self):
        self.auto.mkdir(parents=True)
        (self.auto / "hook.log").write_text("".join("line %d\n" % i for i in range(15)))
        (self.auto / "lock").write_text(json.dumps({"pid": 7, "time": ar.iso(ar.utcnow())}))
        code, out, _ = self.call(["status"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["enabled"])
        self.assertEqual(data["counts"], {"harvest": 0, "improve": 0})
        self.assertEqual(data["caps"], {"harvest": 6, "improve": 2})
        self.assertTrue(data["lock"]["held"])
        self.assertEqual(data["hook_log_tail"], ["line %d" % i for i in range(5, 15)])
        self.assertEqual(data["config"]["harvest"]["agent"], "scout")
        self.assertIs(data["config"]["project_roots"], False)
        self.assertEqual(data["config"]["improve"]["max_groups"], 2)
        self.assertEqual(data["config"]["improve"]["eval_max_cost_usd"], 1)

    def test_disable_enable_cycle(self):
        code, _, _ = self.call(["disable"])
        self.assertEqual(code, 0)
        self.assertTrue((self.auto / "disabled").exists())
        data = json.loads(self.call(["status"])[1])
        self.assertFalse(data["enabled"])
        self.assertEqual(data["lock"], {"held": False, "exists": False, "stale": False, "info": None})
        self.assertEqual(data["hook_log_tail"], [])
        code, _, _ = self.call(["enable"])
        self.assertEqual(code, 0)
        self.assertFalse((self.auto / "disabled").exists())
        self.assertEqual(len(list(self.auto.glob("disabled.off-*"))), 1)
        os.environ["EVOLVING_SKILLS_AUTO"] = "0"
        code, out, err = self.call(["enable"])
        self.assertIn("already enabled", out)
        self.assertIn("EVOLVING_SKILLS_AUTO", err)

    def test_settings_snippet(self):
        code, out, _ = self.call(["settings-snippet"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        hook = data["SessionEnd"][0]["hooks"][0]
        self.assertEqual(hook["type"], "command")
        self.assertEqual(hook["timeout"], 15)
        self.assertEqual(hook["command"], 'python3 "%s" hook' % (SCRIPTS / "auto_run.py"))

    def test_bad_invocation_exit_3(self):
        for argv in ([], ["nope"], ["run"], ["status", "--bogus"]):
            code, out, err = self.call(argv)
            self.assertEqual(code, 3, argv)
            self.assertIn("error", err)

    def test_config_defaults_when_keys_missing(self):
        cfg_path = self.dir / "cfg.json"
        cfg_path.write_text(json.dumps({"min_followups": 5, "harvest": {"daily_cap": 1},
                                        "unknown": 1}))
        with mock.patch.object(ar, "CONFIG_PATH", cfg_path):
            cfg = ar.load_config()
        self.assertEqual(cfg["min_followups"], 5)
        self.assertEqual(cfg["harvest"]["daily_cap"], 1)
        self.assertEqual(cfg["harvest"]["agent"], "scout")
        self.assertEqual(cfg["improve"], ar.DEFAULT_CONFIG["improve"])
        self.assertEqual(cfg["lock_stale_minutes"], 120)
        self.assertIs(cfg["project_roots"], False)
        self.assertNotIn("unknown", cfg)
        cfg_path.write_text("[1, 2]")
        with mock.patch.object(ar, "CONFIG_PATH", cfg_path):
            self.assertEqual(ar.load_config(), ar.DEFAULT_CONFIG)
        cfg_path.write_text("{bad")
        with mock.patch.object(ar, "CONFIG_PATH", cfg_path):
            self.assertEqual(ar.load_config(), ar.DEFAULT_CONFIG)

    def test_improve_prompt_uses_config_values(self):
        self.promotable_cfg = self.dir / "cfg2.json"
        self.promotable_cfg.write_text(json.dumps({"improve": {"max_groups": 1,
                                                               "eval_max_cost_usd": 0.25}}))
        with mock.patch.object(ar, "CONFIG_PATH", self.promotable_cfg):
            cfg = ar.load_config()
        self.assertEqual(ar.improve_prompt(cfg["improve"]),
                         "/evolving-skills improve --max-groups 1 --eval-max-cost-usd 0.25")
        self.assertEqual(cfg["improve"]["agent"], "executor")

    def test_shipped_config_matches_defaults(self):
        shipped = json.loads((SCRIPTS.parent / "assets" / "auto-config.json").read_text())
        self.assertEqual(shipped, ar.DEFAULT_CONFIG)

    def test_state_dir_default(self):
        del os.environ["AGENT_SKILL_STATE_DIR"]
        self.assertEqual(ar.state_dir(),
                         Path("~/.local/state/agent-skills").expanduser() / "evolving-skills")


class LaunchHelperTests(Base):
    def test_spawn_detached(self):
        log = self.dir / "logs" / "w.log"
        fake = mock.Mock(pid=99)
        with mock.patch.object(ar.subprocess, "Popen", return_value=fake) as popen:
            pid = ar.spawn_detached(["x", "y"], str(self.cwd), {"A": "1"}, str(log))
        self.assertEqual(pid, 99)
        kwargs = popen.call_args.kwargs
        self.assertEqual(popen.call_args.args[0], ["x", "y"])
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.STDOUT)
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(kwargs["env"], {"A": "1"})
        self.assertTrue(log.exists())

    def test_run_cmd_capture_and_log(self):
        done = subprocess.CompletedProcess(["x"], 0, stdout="out")
        with mock.patch.object(ar.subprocess, "run", return_value=done) as run:
            self.assertEqual(ar.run_cmd(["x"], cwd=self.cwd, timeout=3), (0, "out"))
            self.assertEqual(run.call_args.kwargs["timeout"], 3)
            self.assertTrue(run.call_args.kwargs["capture_output"])
            log = self.dir / "l" / "x.log"
            self.assertEqual(ar.run_cmd(["x"], log_path=log, env={"B": "2"}), (0, ""))
            self.assertEqual(run.call_args.kwargs["env"], {"B": "2"})
            self.assertIsNone(run.call_args.kwargs["cwd"])
        with mock.patch.object(ar.subprocess, "run",
                               side_effect=subprocess.TimeoutExpired(["x"], 1)):
            self.assertEqual(ar.run_cmd(["x"]), (124, ""))
        with mock.patch.object(ar.subprocess, "run", side_effect=FileNotFoundError("x")):
            self.assertEqual(ar.run_cmd(["x"]), (127, ""))


if __name__ == "__main__":
    unittest.main()
