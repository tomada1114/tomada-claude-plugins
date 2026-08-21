#!/usr/bin/env python3
"""Tests for init_skill.sh. Stdlib-only (unittest), driven via subprocess.

Run: python3 -m unittest scripts.tests.test_init_skill -v
     (from the creating-agent-skills skill directory)
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "init_skill.sh"


def run_init(args: list[str], home: Path, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        cwd=str(cwd) if cwd else str(home),
        capture_output=True,
        text=True,
    )


class TestBasicScaffold(unittest.TestCase):
    def test_basic_creates_skill_md_with_name_substituted(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            proc = run_init(["my-new-skill"], home)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            skill_md = home / ".claude" / "skills" / "my-new-skill" / "SKILL.md"
            self.assertTrue(skill_md.exists())
            text = skill_md.read_text(encoding="utf-8")
            self.assertIn("name: my-new-skill", text)
            self.assertNotIn("name: your-skill-name", text)

    def test_basic_does_not_create_extra_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            proc = run_init(["my-basic-skill"], home)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            target = home / ".claude" / "skills" / "my-basic-skill"
            self.assertFalse((target / "references").exists())
            self.assertFalse((target / "scripts").exists())
            self.assertFalse((target / "assets").exists())


class TestAdvancedScaffold(unittest.TestCase):
    def test_advanced_creates_subdirectories(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            proc = run_init(["my-advanced-skill", "advanced"], home)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            target = home / ".claude" / "skills" / "my-advanced-skill"
            skill_md = target / "SKILL.md"
            self.assertTrue(skill_md.exists())
            text = skill_md.read_text(encoding="utf-8")
            self.assertIn("name: my-advanced-skill", text)
            self.assertTrue((target / "references").is_dir())
            self.assertTrue((target / "assets").is_dir())
            self.assertTrue((target / "scripts").is_dir())
            self.assertTrue((target / "scripts" / "tests").is_dir())


class TestScope(unittest.TestCase):
    def test_project_scope_creates_under_cwd(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            proc = run_init(["my-project-skill", "--scope", "project"], home, cwd=home)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            target = home / ".claude" / "skills" / "my-project-skill"
            self.assertTrue((target / "SKILL.md").exists())


class TestErrors(unittest.TestCase):
    def test_bad_name_exit_1(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            proc = run_init(["Bad_Name"], home)
            self.assertEqual(proc.returncode, 1)

    def test_existing_target_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            first = run_init(["dup-skill"], home)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = run_init(["dup-skill"], home)
            self.assertEqual(second.returncode, 2)

    # Exit 3 (template not found) is hard to trigger without touching assets/,
    # which is out of scope for these tests — skipped per spec.


if __name__ == "__main__":
    unittest.main()
