#!/usr/bin/env python3
"""Tests for assets/hooks/hook_payload.py — the helper copied into projects.

The asset is loaded by path, not imported as a sibling of scripts/: it ships to
projects, so nothing in scripts/ may depend on it and it must parse the shipped
fixtures unchanged.

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the maintaining-agents-md skill directory)
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent.parent
ASSET = SKILL_DIR / "assets" / "hooks" / "hook_payload.py"
FIXTURES = SKILL_DIR / "assets" / "hooks" / "fixtures"


def load_asset():
    spec = importlib.util.spec_from_file_location("hook_payload_asset", ASSET)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


hp = load_asset()


def event_from(name: str):
    return hp.load_event(io.StringIO((FIXTURES / name).read_text(encoding="utf-8")))


class FixtureCase(unittest.TestCase):
    def test_every_fixture_is_valid_json_with_an_event_name(self):
        names = sorted(p.name for p in FIXTURES.glob("*.json"))
        self.assertEqual(len(names), 8, names)
        for name in names:
            with self.subTest(fixture=name):
                payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
                self.assertIn("hook_event_name", payload)
                self.assertIn("cwd", payload)
                self.assertEqual(event_from(name).name, payload["hook_event_name"])

    def test_claude_edit_carries_one_absolute_file(self):
        event = event_from("claude-edit.json")
        self.assertEqual(event.tool, "edit")
        self.assertEqual(event.tool_name, "Edit")
        self.assertIsNone(event.command)
        self.assertEqual(event.files, [Path("/Users/dev/demo/src/app.py")])

    def test_claude_bash_carries_the_command(self):
        event = event_from("claude-bash.json")
        self.assertEqual(event.tool, "shell")
        self.assertEqual(event.command, "npm test -- --runInBand")
        self.assertEqual(event.files, [])

    def test_codex_apply_patch_is_an_edit_with_the_patched_file(self):
        event = event_from("codex-apply-patch.json")
        self.assertEqual(event.tool, "edit")
        self.assertEqual(event.tool_name, "apply_patch")
        self.assertIsNone(event.command, "patch text is not a shell command")
        self.assertEqual(event.files, [Path("/Users/dev/demo/note.txt")])

    def test_codex_bash_matches_the_claude_shape(self):
        codex, claude = event_from("codex-bash.json"), event_from("claude-bash.json")
        self.assertEqual((codex.tool, claude.tool), ("shell", "shell"))
        self.assertEqual(codex.tool_name, claude.tool_name)

    def test_stop_fixtures_are_not_reentrant(self):
        for name in ("claude-stop.json", "codex-stop.json"):
            with self.subTest(fixture=name):
                event = event_from(name)
                self.assertEqual(event.name, "Stop")
                self.assertFalse(event.stop_hook_active)
                self.assertIsNone(event.tool)


class ParseCase(unittest.TestCase):
    def test_patch_paths_cover_every_verb_and_resolve_relative_ones(self):
        patch = (
            "*** Begin Patch\n"
            "*** Add File: a.txt\n+x\n"
            "*** Update File: pkg/b.txt\n-y\n+z\n"
            "*** Delete File: /abs/c.txt\n"
            "*** Move to: d/e.txt\n"
            "*** End Patch\n"
        )
        self.assertEqual(
            hp.patch_files(patch, Path("/root")),
            [Path("/root/a.txt"), Path("/root/pkg/b.txt"), Path("/abs/c.txt"), Path("/root/d/e.txt")],
        )

    def test_duplicate_paths_collapse_in_order(self):
        payload = {
            "hook_event_name": "PostToolUse", "cwd": "/root", "tool_name": "apply_patch",
            "tool_input": {"command": "*** Begin Patch\n*** Update File: a.txt\n*** Move to: a.txt\n*** End Patch"},
        }
        self.assertEqual(hp.from_payload(payload).files, [Path("/root/a.txt")])

    def test_unknown_tool_is_other_and_missing_tool_is_none(self):
        self.assertEqual(hp.from_payload({"tool_name": "WebFetch"}).tool, "other")
        self.assertIsNone(hp.from_payload({"hook_event_name": "SessionStart"}).tool)

    def test_read_is_read_not_edit_but_still_carries_the_file(self):
        event = hp.from_payload({
            "hook_event_name": "PreToolUse", "tool_name": "Read",
            "tool_input": {"file_path": "/w/.env"}, "cwd": "/w",
        })
        self.assertEqual(event.tool, "read")
        self.assertEqual([str(f) for f in event.files], ["/w/.env"])

    def test_file_path_without_a_known_tool_name_still_counts_as_an_edit(self):
        event = hp.from_payload({"tool_name": "NewEditor", "cwd": "/root",
                                 "tool_input": {"file_path": "rel/f.py"}})
        self.assertEqual((event.tool, event.files), ("edit", [Path("/root/rel/f.py")]))

    def test_malformed_payloads_yield_an_empty_event(self):
        for text in ("not json", "[1, 2]", ""):
            with self.subTest(payload=text):
                event = hp.load_event(io.StringIO(text))
                self.assertIsNone(event.name)
                self.assertEqual(event.files, [])
                self.assertEqual(event.raw, {})

    def test_non_dict_tool_input_and_missing_cwd_are_tolerated(self):
        event = hp.from_payload({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": "oops"})
        self.assertEqual(event.cwd, Path.cwd())
        self.assertIsNone(event.command)


class RootCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / ".agents" / "hooks").mkdir(parents=True)

    def test_root_is_the_directory_holding_agents_hooks(self):
        script = self.root / ".agents" / "hooks" / "guard.py"
        script.write_text("", encoding="utf-8")
        self.assertEqual(hp.project_root(script), self.root)
        self.assertEqual(hp.project_root(self.root / ".agents" / "hooks"), self.root)

    def test_root_falls_back_to_the_git_top_level(self):
        if not subprocess.run(["git", "--version"], capture_output=True).returncode == 0:
            self.skipTest("git is not installed")
        repo = self.root / "repo"
        (repo / "sub").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        cwd = os.getcwd()
        os.chdir(repo / "sub")
        self.addCleanup(os.chdir, cwd)
        # The anchor is outside any .agents/hooks tree, so the walk-up fails first.
        self.assertEqual(hp.project_root(Path("/")).resolve(), repo.resolve())

    def test_relative_to_root_prefers_the_root_then_cwd_then_the_name(self):
        event = hp.from_payload({"cwd": "/Users/dev/demo"})
        self.assertEqual(hp.relative_to_root(self.root / "src" / "a.py", event, self.root), "src/a.py")
        self.assertEqual(hp.relative_to_root(Path("/Users/dev/demo/.env"), event, self.root), ".env")
        self.assertEqual(hp.relative_to_root(Path("/elsewhere/x.py"), event, self.root), "x.py")


if __name__ == "__main__":
    unittest.main()
