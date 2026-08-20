#!/usr/bin/env python3
"""Tests for classify_skill.py. Stdlib-only (unittest).

Run: python3 -m unittest scripts.tests.test_classify_skill -v
     (from the dual-platform-skills skill directory)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import classify_skill as cs  # noqa: E402

FM = "---\nname: sample-skill\ndescription: test\n---\n"


def write_skill(root: Path, name: str = "sample-skill", skill_md: str | None = None,
                 extra: dict[str, str] | None = None) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm = f"---\nname: {name}\ndescription: test\n---\n"
    (skill_dir / "SKILL.md").write_text(skill_md if skill_md is not None else fm + "\nBody.\n",
                                         encoding="utf-8")
    for rel, content in (extra or {}).items():
        p = skill_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return skill_dir


class TestTierAssignment(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_tier_a_when_no_constructs(self):
        skill = write_skill(self.root, skill_md=FM + "\nJust prose, nothing special.\n")
        c = cs.classify(skill)
        self.assertEqual(c.tier, "A")

    def test_tier_b_on_ask_user_question(self):
        skill = write_skill(self.root, skill_md=FM + "\nConfirm via AskUserQuestion.\n")
        c = cs.classify(skill)
        self.assertEqual(c.tier, "B")
        self.assertIn("ask_user_question", c.constructs)

    def test_tier_c_on_task_orchestration(self):
        skill = write_skill(self.root, skill_md=FM + "\nSpawn with subagent_type: general-purpose.\n")
        c = cs.classify(skill)
        self.assertEqual(c.tier, "C")

    def test_tier_c_on_cross_skill_ref(self):
        # skill_registry() walks up looking for a ".claude" dir, then scans "<that>/skills/";
        # the fixture must sit under <root>/.claude/skills/ for sibling detection to fire.
        claude_skills = self.root / ".claude" / "skills"
        write_skill(claude_skills, name="other-skill")
        skill = write_skill(claude_skills, skill_md=FM + "\nUse other-skill for the next step.\n")
        c = cs.classify(skill)
        self.assertIn("other-skill", c.cross_skill_refs)
        self.assertEqual(c.tier, "C")


class TestConstructLocationsAcrossFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_hits_in_references_reported_with_file_and_line(self):
        skill = write_skill(
            self.root,
            extra={"references/deep.md": "line one\nline two has AskUserQuestion here\n"},
        )
        c = cs.classify(skill)
        hits = [loc for loc in c.construct_locations if loc["label"] == "ask_user_question"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["file"], "references/deep.md")
        self.assertEqual(hits[0]["line"], 2)

    def test_hits_in_templates_also_scanned(self):
        skill = write_skill(
            self.root,
            extra={"templates/t.md": "uses subagent_type: general-purpose\n"},
        )
        c = cs.classify(skill)
        hits = [loc for loc in c.construct_locations if loc["file"] == "templates/t.md"]
        self.assertTrue(hits)

    def test_skill_md_line_offset_accounts_for_frontmatter(self):
        # frontmatter is 4 lines (--- name description ---), body starts at line 5;
        # "AskUserQuestion" on the first body line should report as SKILL.md line 5.
        skill = write_skill(self.root, skill_md=FM + "AskUserQuestion right here.\n")
        c = cs.classify(skill)
        hits = [loc for loc in c.construct_locations if loc["file"] == "SKILL.md"]
        self.assertEqual(hits[0]["line"], 5)


class TestResourceInventory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_counts_references_and_scripts_files(self):
        skill = write_skill(
            self.root,
            extra={"references/a.md": "x", "references/b.md": "y", "scripts/run.sh": "#!/bin/sh"},
        )
        c = cs.classify(skill)
        self.assertEqual(c.references_files, 2)
        self.assertEqual(c.scripts_files, 1)


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_main_returns_0_even_for_tier_c(self):
        skill = write_skill(self.root, skill_md=FM + "\nsubagent_type: general-purpose\n")
        self.assertEqual(cs.main(["classify_skill.py", str(skill)]), 0)

    def test_main_bad_path_returns_2(self):
        self.assertEqual(cs.main(["classify_skill.py", str(self.root / "missing")]), 2)


if __name__ == "__main__":
    unittest.main()
