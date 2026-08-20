#!/usr/bin/env python3
"""Tests for verify_bridge.py. Stdlib-only (unittest).

Run: python3 -m unittest scripts.tests.test_verify_bridge -v
     (from the dual-platform-skills skill directory)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import verify_bridge as vb  # noqa: E402

FM = "---\nname: sample-skill\ndescription: test\nmetadata:\n  platforms: claude-code, codex\n---\n"


def write_skill(root: Path, skill_md: str = FM + "\nBody.\n", extra: dict[str, str] | None = None) -> Path:
    skill_dir = root / "sample-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    for rel, content in (extra or {}).items():
        p = skill_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return skill_dir


class TestBasicChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_v1_symlink_is_error(self):
        real = write_skill(self.root)
        link = self.root / "linked-skill"
        link.symlink_to(real)
        r = vb.verify(link, [])
        self.assertTrue(any(f.code == "V1" for f in r.errors))
        self.assertFalse(r.codex_runnable)

    def test_v1_missing_skill_md_is_error(self):
        d = self.root / "empty-dir"
        d.mkdir()
        r = vb.verify(d, [])
        self.assertTrue(any(f.code == "V1" for f in r.errors))

    def test_v2_missing_description_is_error(self):
        skill = write_skill(self.root, "---\nname: sample-skill\n---\nBody.\n")
        r = vb.verify(skill, [])
        self.assertTrue(any(f.code == "V2" for f in r.errors))

    def test_clean_dual_platform_skill_is_codex_runnable(self):
        skill = write_skill(self.root)
        r = vb.verify(skill, [])
        self.assertTrue(r.codex_runnable)
        self.assertFalse(r.errors)


class TestV4V5ScanReferencesToo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_v4_finds_abs_claude_path_in_references(self):
        skill = write_skill(
            self.root,
            extra={"references/x.md": "call `~/.claude/skills/self/scripts/y.py`"},
        )
        r = vb.verify(skill, [])
        v4 = [f for f in r.findings if f.code == "V4"]
        self.assertEqual(len(v4), 1)

    def test_v5_finds_cross_skill_ref_in_templates(self):
        skill = write_skill(
            self.root,
            extra={"templates/t.md": "see `.claude/skills/other-skill/references/x.md`"},
        )
        r = vb.verify(skill, [])
        v5 = [f for f in r.findings if f.code == "V5"]
        self.assertEqual(len(v5), 1)
        self.assertIn("other-skill", v5[0].message)

    def test_v4_v5_skip_annex_marked_files(self):
        # A platform-notes.md documenting `~/.claude/skills/other-skill/...` as illustrative
        # content must not trip V4/V5 — same exemption neutrality_lint N1-N4 honor.
        skill = write_skill(
            self.root,
            extra={"references/platform-notes.md":
                   "<!-- platform-annex -->\n~/.claude/skills/other-skill/references/x.md\n"},
        )
        r = vb.verify(skill, [])
        self.assertFalse([f for f in r.findings if f.code in ("V4", "V5")])


class TestV8NeutralityIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_v8_error_makes_not_codex_runnable(self):
        skill = write_skill(self.root, FM + "\nAsk via AskUserQuestion.\n")
        r = vb.verify(skill, [])
        v8 = [f for f in r.findings if f.code == "V8"]
        self.assertTrue(v8)
        self.assertFalse(r.codex_runnable)

    def test_v8_annex_file_does_not_trip_lint(self):
        skill = write_skill(
            self.root,
            extra={"references/platform-notes.md": "<!-- platform-annex -->\nAskUserQuestion\n"},
        )
        r = vb.verify(skill, [])
        self.assertFalse([f for f in r.findings if f.code == "V8"])
        self.assertTrue(r.codex_runnable)


class TestV7LinkIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_v7_broken_relative_link_is_error(self):
        skill = write_skill(self.root, FM + "\nSee [x](references/missing.md).\n")
        r = vb.verify(skill, [])
        self.assertTrue(any(f.code == "V7" for f in r.errors))
        self.assertFalse(r.codex_runnable)

    def test_v7_existing_relative_link_ok(self):
        skill = write_skill(
            self.root, FM + "\nSee [x](references/present.md).\n",
            extra={"references/present.md": "content"},
        )
        r = vb.verify(skill, [])
        self.assertFalse([f for f in r.findings if f.code == "V7"])


class TestCodexLinkDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_v6_warns_when_no_link_found(self):
        skill = write_skill(self.root)
        r = vb.verify(skill, [])
        self.assertTrue(any(f.code == "V6" and f.level == "warning" for f in r.findings))

    def test_extra_link_recognized(self):
        skill = write_skill(self.root)
        codex_dir = self.root / "codex-skills"
        codex_dir.mkdir()
        link = codex_dir / skill.name
        link.symlink_to(skill)
        found = vb.find_codex_links(skill, [str(link)])
        self.assertEqual(found, [str(link)])


if __name__ == "__main__":
    unittest.main()
