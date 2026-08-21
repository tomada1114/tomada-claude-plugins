#!/usr/bin/env python3
"""Tests for share_hooks.py. Stdlib-only (unittest).

Every test points AGENT_SKILL_STATE_DIR at a temporary directory, so snapshots
never touch the real home directory.

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the maintaining-agents-md skill directory)
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import inventory as inv  # noqa: E402
import share_hooks as share  # noqa: E402
import snapshot as snap  # noqa: E402

TOPLEVEL = inv.TOPLEVEL_EXPR
SCRIPT_BODY = '#!/usr/bin/env python3\nimport json, sys\nprint("guard")\n'
HOST_SPECIFIC_BODY = (
    '#!/usr/bin/env python3\nimport json, sys\n'
    'payload = json.load(sys.stdin)\npath = payload["tool_input"]["file_path"]\n'
)


def has_git() -> bool:
    return shutil.which("git") is not None


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = share.main(argv)
    return code, out.getvalue(), err.getvalue()


def hook_entry(command: str, matcher: str = "Edit|Write", **extra):
    hook = {"type": "command", "command": command}
    hook.update(extra)
    return {"matcher": matcher, "hooks": [hook]}


class ShareCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        self.root = base / "project"
        self.root.mkdir()
        self.state = base / "state"
        self.codex_home = base / "codex-home"
        patcher = mock.patch.dict(os.environ, {
            "AGENT_SKILL_STATE_DIR": str(self.state),
            "CODEX_HOME": str(self.codex_home),
        })
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, rel: str, data) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
        return path

    def write_json(self, rel: str, data) -> Path:
        return self.write(rel, json.dumps(data, indent=2) + "\n")

    def read(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def read_json(self, rel: str):
        return json.loads(self.read(rel))

    def build_template(self, **settings_extra):
        """The shape the project templates ship: three scripts, three events."""
        for name in ("guard", "format", "stop_check"):
            self.write(".claude/hooks/{}.py".format(name), SCRIPT_BODY)
        settings = {
            "permissions": {"allow": ["Bash(uv run:*)"]},
            "hooks": {
                "PreToolUse": [hook_entry(
                    'uv run --script "${CLAUDE_PROJECT_DIR}/.claude/hooks/guard.py"',
                    "Edit|Write|Bash", timeout=10)],
                "PostToolUse": [hook_entry(
                    'uv run --script "${CLAUDE_PROJECT_DIR}/.claude/hooks/format.py"')],
                "Stop": [hook_entry(
                    'uv run --script "${CLAUDE_PROJECT_DIR}/.claude/hooks/stop_check.py"',
                    "")],
                "Notification": [{"hooks": [{"type": "command", "command": "say done"}]}],
            },
        }
        settings.update(settings_extra)
        self.write_json(".claude/settings.json", settings)
        return settings

    def actions(self, plan, kind: str):
        return [a for a in plan.actions if a.kind == kind]


class TestRewriteCommand(ShareCase):
    def test_braced_project_variable(self):
        self.assertEqual(
            share.rewrite_command('uv run --script "${CLAUDE_PROJECT_DIR}/.claude/hooks/g.py"'),
            'uv run --script "{}/.agents/hooks/g.py"'.format(TOPLEVEL))

    def test_bare_project_variable(self):
        self.assertEqual(
            share.rewrite_command("python3 $CLAUDE_PROJECT_DIR/.claude/hooks/g.py"),
            'python3 "{}/.agents/hooks/g.py"'.format(TOPLEVEL))

    def test_dot_slash_relative(self):
        self.assertEqual(share.rewrite_command("node ./.claude/hooks/g.mjs"),
                         'node "{}/.agents/hooks/g.mjs"'.format(TOPLEVEL))

    def test_bare_relative_gains_quotes(self):
        self.assertEqual(share.rewrite_command("python3 .claude/hooks/g.py"),
                         'python3 "{}/.agents/hooks/g.py"'.format(TOPLEVEL))

    def test_single_quoted(self):
        self.assertEqual(share.rewrite_command("sh '.claude/hooks/g.sh'"),
                         'sh "{}/.agents/hooks/g.sh"'.format(TOPLEVEL))

    def test_toplevel_form_pointing_at_the_retired_directory(self):
        self.assertEqual(
            share.rewrite_command('sh "{}/.claude/hooks/g.sh"'.format(TOPLEVEL)),
            'sh "{}/.agents/hooks/g.sh"'.format(TOPLEVEL))

    def test_nested_subdirectory_is_kept(self):
        self.assertEqual(share.rewrite_command("python3 .claude/hooks/lib/g.py"),
                         'python3 "{}/.agents/hooks/lib/g.py"'.format(TOPLEVEL))

    def test_already_shared_is_untouched(self):
        command = 'uv run --script "{}/.agents/hooks/g.py"'.format(TOPLEVEL)
        self.assertEqual(share.rewrite_command(command), command)

    def test_personal_directory_is_untouched(self):
        for command in ("python3 ~/.claude/hooks/g.py", "python3 $HOME/.claude/hooks/g.py"):
            self.assertEqual(share.rewrite_command(command), command)

    def test_extra_arguments_survive(self):
        self.assertEqual(
            share.rewrite_command('python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/g.py" --strict'),
            'python3 "{}/.agents/hooks/g.py" --strict'.format(TOPLEVEL))

    def test_rewrite_hooks_counts_and_tolerates_junk(self):
        hooks = {
            "PreToolUse": [hook_entry("python3 .claude/hooks/g.py")],
            "PostToolUse": "not-a-list",
            "Stop": ["not-a-dict", {"hooks": "not-a-list"}, {"hooks": [7, {"type": "command"}]}],
        }
        self.assertEqual(share.rewrite_hooks(hooks), 1)
        self.assertIn(TOPLEVEL, hooks["PreToolUse"][0]["hooks"][0]["command"])


class TestLegacyFiles(ShareCase):
    def test_nested_layout_and_cache_pruning(self):
        self.write(".claude/hooks/guard.py", SCRIPT_BODY)
        self.write(".claude/hooks/lib/util.mjs", "export const x = 1;\n")
        self.write(".claude/hooks/__pycache__/guard.pyc", b"\x00")
        self.assertEqual(share.legacy_files(self.root, 6),
                         [".claude/hooks/guard.py", ".claude/hooks/lib/util.mjs"])

    def test_max_depth_prunes(self):
        self.write(".claude/hooks/a/b/deep.py", SCRIPT_BODY)
        self.assertEqual(share.legacy_files(self.root, 1), [])
        self.assertEqual(len(share.legacy_files(self.root, 3)), 1)

    def test_no_directory(self):
        self.assertEqual(share.legacy_files(self.root, 6), [])


class TestPlan(ShareCase):
    def test_template_plan(self):
        self.build_template()
        plan = share.build_plan(self.root)
        self.assertEqual(plan.state, "claude-only")
        self.assertEqual([a.path for a in self.actions(plan, "relocate")],
                         [".claude/hooks/format.py", ".claude/hooks/guard.py",
                          ".claude/hooks/stop_check.py"])
        self.assertEqual(len(self.actions(plan, "rewrite-wiring")), 1)
        self.assertEqual(len(self.actions(plan, "create-codex")), 1)
        self.assertEqual(len(plan.pending), 5)
        only = self.actions(plan, "claude-only-event")
        self.assertEqual(len(only), 1)
        self.assertIn("Notification", only[0].detail)

    def test_generated_codex_keeps_matcher_timeout_and_drops_extras(self):
        self.write(".claude/hooks/g.py", SCRIPT_BODY)
        self.write_json(".claude/settings.json", {"hooks": {"PreToolUse": [{
            "matcher": "Edit|Write",
            "hooks": [{"type": "command", "command": "python3 .claude/hooks/g.py",
                       "timeout": 5, "async": False, "unknownKey": 1}],
        }]}})
        plan = share.build_plan(self.root)
        generated = json.loads(plan.codex_text)["hooks"]["PreToolUse"][0]
        self.assertEqual(generated["matcher"], "Edit|Write")
        self.assertEqual(generated["hooks"][0]["timeout"], 5)
        self.assertEqual(generated["hooks"][0]["async"], False)
        self.assertNotIn("unknownKey", generated["hooks"][0])
        self.assertIn(TOPLEVEL, generated["hooks"][0]["command"])

    def test_codex_up_to_date_is_no_action(self):
        self.build_template()
        share.apply_plan(self.root, share.build_plan(self.root))
        plan = share.build_plan(self.root)
        self.assertEqual(plan.pending, [])
        self.assertIsNone(plan.codex_text)

    def test_codex_merge_when_it_differs(self):
        self.write_json(".claude/settings.json", {"hooks": {"Stop": [hook_entry(
            'sh "{}/.agents/hooks/s.sh"'.format(TOPLEVEL), "")]}})
        self.write_json(".codex/hooks.json", {"hooks": {"Stop": [hook_entry("sh stale.sh", "")]}})
        plan = share.build_plan(self.root)
        self.assertEqual([a.kind for a in plan.pending], ["merge-codex"])
        self.assertTrue(plan.codex_existed)

    def test_codex_only_hooks_and_top_level_settings_are_preserved(self):
        self.write_json(".claude/settings.json", {"hooks": {"Stop": [hook_entry(
            'sh "{}/.agents/hooks/s.sh"'.format(TOPLEVEL), "")]}})
        self.write_json(".codex/hooks.json", {
            "description": "Codex-specific policy",
            "hooks": {
                "Stop": [hook_entry("sh codex-only.sh", "")],
                "UserPromptSubmit": [hook_entry("sh another-codex-only.sh", "")],
            },
        })
        plan = share.build_plan(self.root)
        merged = json.loads(plan.codex_text)
        self.assertEqual(merged["description"], "Codex-specific policy")
        commands = [
            h["command"]
            for entry in merged["hooks"]["Stop"]
            for h in entry["hooks"]
        ]
        self.assertIn("sh codex-only.sh", commands)
        self.assertIn('sh "{}/.agents/hooks/s.sh"'.format(TOPLEVEL), commands)
        self.assertIn("another-codex-only.sh", json.dumps(merged))

    def test_no_shareable_event_leaves_the_other_config_alone(self):
        self.write_json(".codex/hooks.json", {"hooks": {"Stop": [hook_entry("sh s.sh", "")]}})
        self.write_json(".claude/settings.json",
                        {"hooks": {"Notification": [{"hooks": [
                            {"type": "command", "command": "say done"}]}]}})
        plan = share.build_plan(self.root)
        self.assertEqual(plan.pending, [])
        self.assertEqual(len(self.actions(plan, "skip-codex")), 1)

    def test_duplicate_destination_drops_the_retired_copy(self):
        self.write(".claude/hooks/g.py", SCRIPT_BODY)
        self.write(".agents/hooks/g.py", SCRIPT_BODY)
        self.write_json(".claude/settings.json",
                        {"hooks": {"Stop": [hook_entry("python3 .claude/hooks/g.py", "")]}})
        plan = share.build_plan(self.root)
        self.assertTrue(plan.moves[0].duplicate)
        self.assertIn("same bytes", plan.actions[0].detail)
        share.apply_plan(self.root, plan)
        self.assertFalse((self.root / ".claude/hooks").exists())
        self.assertEqual(self.read(".agents/hooks/g.py"), SCRIPT_BODY)

    def test_scripts_without_any_wiring_are_still_relocated(self):
        self.write(".claude/hooks/guard.py", SCRIPT_BODY)
        plan = share.build_plan(self.root)
        self.assertEqual([a.kind for a in plan.pending], ["relocate"])
        share.apply_plan(self.root, plan)
        self.assertEqual(self.read(".agents/hooks/guard.py"), SCRIPT_BODY)
        self.assertFalse((self.root / ".codex").exists())

    def test_conflicting_destination_is_refused(self):
        self.write(".claude/hooks/g.py", SCRIPT_BODY)
        self.write(".agents/hooks/g.py", "# different\n")
        with self.assertRaises(share.ShareError) as ctx:
            share.build_plan(self.root)
        self.assertIn("differs", str(ctx.exception))

    def test_nothing_to_share_is_refused(self):
        self.write_json(".claude/settings.json", {"permissions": {"allow": []}})
        with self.assertRaises(share.ShareError) as ctx:
            share.build_plan(self.root)
        self.assertIn("Nothing to share", str(ctx.exception))

    def test_invalid_settings_json_is_refused(self):
        self.write(".claude/settings.json", "{not json")
        self.write(".claude/hooks/g.py", SCRIPT_BODY)
        with self.assertRaises(share.ShareError) as ctx:
            share.build_plan(self.root)
        self.assertIn(".claude/settings.json", str(ctx.exception))

    def test_invalid_codex_json_is_refused(self):
        self.write(".claude/hooks/g.py", SCRIPT_BODY)
        self.write_json(".claude/settings.json",
                        {"hooks": {"Stop": [hook_entry("python3 .claude/hooks/g.py", "")]}})
        self.write(".codex/hooks.json", "[]")
        with self.assertRaises(share.ShareError) as ctx:
            share.build_plan(self.root)
        self.assertIn(".codex/hooks.json", str(ctx.exception))

    def test_host_specific_script_is_flagged_at_its_new_path(self):
        self.write(".claude/hooks/guard.py", HOST_SPECIFIC_BODY)
        self.write_json(".claude/settings.json",
                        {"hooks": {"Stop": [hook_entry("python3 .claude/hooks/guard.py", "")]}})
        plan = share.build_plan(self.root)
        self.assertEqual([a.path for a in self.actions(plan, "adapt-script")],
                         [".agents/hooks/guard.py"])

    def test_unreadable_candidate_is_skipped(self):
        self.write(".agents/hooks/guard.py", HOST_SPECIFIC_BODY)
        self.write_json(".claude/settings.json", {"hooks": {"Stop": [hook_entry(
            'python3 "{}/.agents/hooks/guard.py"'.format(TOPLEVEL), "")]}})
        real_read = inv.read_text

        def fail_on_the_script(path):
            if path.name == "guard.py":
                raise OSError("gone")
            return real_read(path)

        with mock.patch("share_hooks.inventory.read_text", side_effect=fail_on_the_script):
            plan = share.build_plan(self.root)
        self.assertEqual(self.actions(plan, "adapt-script"), [])


class TestApply(ShareCase):
    def test_full_run_moves_rewrites_and_generates(self):
        self.build_template()
        plan = share.build_plan(self.root)
        snap_dir = share.apply_plan(self.root, plan)

        self.assertFalse((self.root / ".claude/hooks").exists())
        for name in ("guard", "format", "stop_check"):
            self.assertEqual(self.read(".agents/hooks/{}.py".format(name)), SCRIPT_BODY)
        settings = self.read_json(".claude/settings.json")
        self.assertEqual(settings["permissions"], {"allow": ["Bash(uv run:*)"]})
        self.assertEqual(list(settings["hooks"]),
                         ["PreToolUse", "PostToolUse", "Stop", "Notification"])
        command = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertEqual(
            command, 'uv run --script "{}/.agents/hooks/guard.py"'.format(TOPLEVEL))
        codex = self.read_json(".codex/hooks.json")
        self.assertEqual(list(codex["hooks"]), ["PreToolUse", "PostToolUse", "Stop"])
        self.assertEqual(codex["hooks"]["PreToolUse"][0]["hooks"][0]["command"], command)
        self.assertTrue(self.read(".codex/hooks.json").endswith("}\n"))

        by_rel = {f.rel: f.status for f in snap.load_manifest(snap_dir).files}
        self.assertEqual(by_rel[".claude/hooks/guard.py"], "copied")
        self.assertEqual(by_rel[".agents/hooks/guard.py"], "created")
        self.assertEqual(by_rel[".claude/settings.json"], "copied")
        self.assertEqual(by_rel[".codex/hooks.json"], "created")
        self.assertEqual((snap_dir / ".claude/hooks/guard.py").read_text(), SCRIPT_BODY)

    def test_second_run_changes_nothing(self):
        self.build_template()
        share.apply_plan(self.root, share.build_plan(self.root))
        before = self.read(".claude/settings.json"), self.read(".codex/hooks.json")
        plan = share.build_plan(self.root)
        self.assertIsNone(share.apply_plan(self.root, plan))
        self.assertEqual((self.read(".claude/settings.json"),
                          self.read(".codex/hooks.json")), before)

    def test_no_leftover_findings_for_the_shared_state(self):
        self.build_template()
        share.apply_plan(self.root, share.build_plan(self.root))
        result = inv.build_inventory(self.root)
        self.assertEqual(result.hooks.state, "shared")
        self.assertEqual([f.code for f in result.findings
                          if f.code in inv.HOOK_MODE_CODES], [])

    def test_nested_layout_survives_the_move(self):
        self.write(".claude/hooks/lib/util.mjs", "export const x = 1;\n")
        self.write(".claude/hooks/__pycache__/g.pyc", b"\x00")
        self.write_json(".claude/settings.json", {"hooks": {"Stop": [hook_entry(
            "node .claude/hooks/lib/util.mjs", "")]}})
        share.apply_plan(self.root, share.build_plan(self.root))
        self.assertEqual(self.read(".agents/hooks/lib/util.mjs"), "export const x = 1;\n")
        self.assertFalse((self.root / ".claude/hooks").exists())

    def test_retired_directory_is_kept_when_something_is_left_behind(self):
        self.write(".claude/hooks/a/b/c/d/e/deep.py", SCRIPT_BODY)
        self.write(".claude/hooks/g.py", SCRIPT_BODY)
        self.write_json(".claude/settings.json",
                        {"hooks": {"Stop": [hook_entry("python3 .claude/hooks/g.py", "")]}})
        share.apply_plan(self.root, share.build_plan(self.root, max_depth=2))
        self.assertTrue((self.root / ".claude/hooks/a/b/c/d/e/deep.py").is_file())
        self.assertEqual(self.read(".agents/hooks/g.py"), SCRIPT_BODY)

    def test_merge_snapshots_the_previous_generated_file(self):
        self.write_json(".claude/settings.json", {"hooks": {"Stop": [hook_entry(
            'sh "{}/.agents/hooks/s.sh"'.format(TOPLEVEL), "")]}})
        self.write_json(".codex/hooks.json", {"hooks": {"Stop": [hook_entry("sh stale.sh", "")]}})
        snap_dir = share.apply_plan(self.root, share.build_plan(self.root))
        self.assertIn("stale.sh", (snap_dir / ".codex/hooks.json").read_text())
        self.assertIn("stale.sh", self.read(".codex/hooks.json"))
        self.assertIn(".agents/hooks/s.sh", self.read(".codex/hooks.json"))

    def test_no_snapshot_flag(self):
        self.build_template()
        share.apply_plan(self.root, share.build_plan(self.root), snapshot=False)
        self.assertEqual(snap.list_snapshots(self.root), [])
        self.assertTrue((self.root / ".codex/hooks.json").is_file())

    @unittest.skipUnless(has_git(), "git is not installed")
    def test_tracked_files_move_with_version_control(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "d@example.com"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "dev"],
                       check=True, capture_output=True)
        self.build_template()
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "init"],
                       check=True, capture_output=True)
        share.apply_plan(self.root, share.build_plan(self.root))
        status = subprocess.run(
            ["git", "-C", str(self.root), "status", "--porcelain"],
            capture_output=True, text=True, check=True).stdout
        self.assertIn("R  .claude/hooks/guard.py -> .agents/hooks/guard.py", status)

    @unittest.skipUnless(has_git(), "git is not installed")
    def test_tracked_duplicate_is_removed_from_the_index(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        self.write(".claude/hooks/g.py", SCRIPT_BODY)
        self.write(".agents/hooks/g.py", SCRIPT_BODY)
        self.write_json(".claude/settings.json",
                        {"hooks": {"Stop": [hook_entry("python3 .claude/hooks/g.py", "")]}})
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True, capture_output=True)
        share.apply_plan(self.root, share.build_plan(self.root))
        tracked = subprocess.run(["git", "-C", str(self.root), "ls-files"],
                                 capture_output=True, text=True, check=True).stdout
        self.assertNotIn(".claude/hooks/g.py", tracked)

    def test_move_falls_back_when_version_control_refuses(self):
        self.write(".claude/hooks/g.py", SCRIPT_BODY)
        self.write_json(".claude/settings.json",
                        {"hooks": {"Stop": [hook_entry("python3 .claude/hooks/g.py", "")]}})
        with mock.patch("share_hooks._git_ok", return_value=False):
            share.apply_plan(self.root, share.build_plan(self.root), snapshot=False)
        self.assertEqual(self.read(".agents/hooks/g.py"), SCRIPT_BODY)

    def test_duplicate_without_version_control_is_unlinked(self):
        self.write(".claude/hooks/g.py", SCRIPT_BODY)
        self.write(".agents/hooks/g.py", SCRIPT_BODY)
        self.write_json(".claude/settings.json",
                        {"hooks": {"Stop": [hook_entry("python3 .claude/hooks/g.py", "")]}})
        with mock.patch("share_hooks._git_ok", return_value=False):
            share.apply_plan(self.root, share.build_plan(self.root), snapshot=False)
        self.assertFalse((self.root / ".claude/hooks").exists())

    def test_git_helper_reports_failure_without_git(self):
        with mock.patch("share_hooks.subprocess.run", side_effect=OSError("no git")):
            self.assertFalse(share._git_ok(self.root, "status"))

    def test_prune_without_the_directory(self):
        self.assertFalse(share._prune_legacy_dir(self.root))


class TestCli(ShareCase):
    def test_dry_run_reports_and_writes_nothing(self):
        self.build_template()
        code, out, _ = run_main([str(self.root), "--dry-run"])
        self.assertEqual(code, 1)
        self.assertIn("mode: dry-run", out)
        self.assertIn("relocate", out)
        self.assertIn("would change 5 file(s)", out)
        self.assertTrue((self.root / ".claude/hooks/guard.py").is_file())
        self.assertFalse((self.root / ".codex/hooks.json").exists())

    def test_check_is_terse_then_clean(self):
        self.build_template()
        code, out, _ = run_main([str(self.root), "--check"])
        self.assertEqual(code, 1)
        self.assertIn("mode: check", out)
        self.assertIn("5 pending action(s)", out)
        self.assertNotIn("adapt-script", out)

        self.assertEqual(run_main([str(self.root)])[0], 0)
        code, out, _ = run_main([str(self.root), "--check"])
        self.assertEqual(code, 0)
        self.assertIn("state: shared", out)
        self.assertIn("0 pending action(s)", out)

    def test_apply_json_output(self):
        self.build_template()
        code, out, _ = run_main([str(self.root), "--json"])
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["pending"], 5)
        self.assertEqual(data["state"], "claude-only")
        self.assertTrue(data["snapshot_dir"].startswith(str(self.state)))
        self.assertEqual(data["actions"][0]["kind"], "relocate")

    def test_apply_text_output_names_the_snapshot(self):
        self.build_template()
        code, out, _ = run_main([str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("snapshot: {}".format(self.state), out)
        self.assertIn("changed 5 file(s)", out)

    def test_nothing_pending_prints_the_shared_note(self):
        self.write(".agents/hooks/g.sh", "echo ok\n")
        self.write_json(".claude/settings.json", {"hooks": {"Stop": [hook_entry(
            'sh "{}/.agents/hooks/g.sh"'.format(TOPLEVEL), "")]}})
        run_main([str(self.root)])
        code, out, _ = run_main([str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("(hooks are already shared)", out)

    def test_no_snapshot_is_refused_when_files_move(self):
        self.build_template()
        code, _, err = run_main([str(self.root), "--no-snapshot"])
        self.assertEqual(code, 2)
        self.assertIn("--no-snapshot", err)
        self.assertTrue((self.root / ".claude/hooks/guard.py").is_file())
        code, _, _ = run_main([str(self.root), "--no-snapshot", "--dry-run"])
        self.assertEqual(code, 1)

    def test_no_snapshot_is_allowed_for_a_first_generation(self):
        self.write(".agents/hooks/g.sh", "echo ok\n")
        self.write_json(".claude/settings.json", {"hooks": {"Stop": [hook_entry(
            'sh "{}/.agents/hooks/g.sh"'.format(TOPLEVEL), "")]}})
        code, out, _ = run_main([str(self.root), "--no-snapshot", "--json"])
        self.assertEqual(code, 0)
        self.assertIsNone(json.loads(out)["snapshot_dir"])
        self.assertTrue((self.root / ".codex/hooks.json").is_file())

    def test_nothing_to_share_exits_2(self):
        self.write_json(".claude/settings.json", {"permissions": {"allow": []}})
        code, _, err = run_main([str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn("Nothing to share", err)

    def test_missing_root_exits_2(self):
        code, _, err = run_main([str(self.root / "nope")])
        self.assertEqual(code, 2)
        self.assertIn("Pass an existing directory", err)

    def test_bad_max_depth_exits_2(self):
        code, _, err = run_main([str(self.root), "--max-depth", "0"])
        self.assertEqual(code, 2)
        self.assertIn("--max-depth", err)

    def test_snapshot_error_exits_2(self):
        self.build_template()
        with mock.patch("share_hooks.save_snapshot",
                        side_effect=share.SnapshotError("state dir unwritable")):
            code, _, err = run_main([str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn("state dir unwritable", err)

    def test_write_failure_exits_2(self):
        self.build_template()
        with mock.patch("share_hooks.inventory.write_text",
                        side_effect=OSError("Read-only file system")):
            code, _, err = run_main([str(self.root), "--json"])
        self.assertEqual(code, 2)
        self.assertIn("Read-only file system", err)

    def test_default_root_when_omitted(self):
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        self.build_template()
        code, _, _ = run_main(["--json"])
        self.assertEqual(code, 0)
        self.assertTrue((self.root / ".codex/hooks.json").is_file())


if __name__ == "__main__":
    unittest.main()
