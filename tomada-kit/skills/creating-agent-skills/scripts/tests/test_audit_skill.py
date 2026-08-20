#!/usr/bin/env python3
"""Tests for audit_skill.py. Stdlib-only (unittest).

Run: python3 -m unittest scripts.tests.test_audit_skill -v
     (from the creating-agent-skills skill directory)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import audit_skill as au  # noqa: E402
import validate_skill as vs  # noqa: E402


def write_skill(root: Path, name: str = "sample-skill", skill_md: str | None = None,
                 extra: dict[str, str] | None = None) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    default = f"---\nname: {name}\ndescription: test skill\n---\nBody.\n"
    (skill_dir / "SKILL.md").write_text(skill_md if skill_md is not None else default, encoding="utf-8")
    for rel, content in (extra or {}).items():
        p = skill_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return skill_dir


class TestNeutralityInheritedFromValidate(unittest.TestCase):
    """audit_skill.py must NOT reimplement N1-N4 — it inherits them via
    validate_skill.validate() as the base report. This locks in that design so
    a future edit doesn't silently duplicate (and drift from) neutrality_lint.py.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_n1_finding_appears_in_base_report_not_extras(self):
        if vs._load_neutrality_lint() is None:
            self.skipTest("dual-platform-skills sibling skill not found in this checkout")
        skill = write_skill(
            self.root,
            skill_md=(
                "---\nname: sample-skill\ndescription: d\nmetadata:\n"
                "  platforms: claude-code, codex\n---\nAsk via AskUserQuestion.\n"
            ),
        )
        report, extras = au.audit(skill)
        self.assertTrue(any(f.code == "N1" for f in report.findings))
        self.assertFalse(any(f.code == "N1" for f in extras))

    def test_markdown_report_includes_n1_finding(self):
        if vs._load_neutrality_lint() is None:
            self.skipTest("dual-platform-skills sibling skill not found in this checkout")
        skill = write_skill(
            self.root,
            skill_md=(
                "---\nname: sample-skill\ndescription: d\nmetadata:\n"
                "  platforms: claude-code, codex\n---\nAsk via AskUserQuestion.\n"
            ),
        )
        report, extras = au.audit(skill)
        md = au.render_markdown(skill, report, extras)
        self.assertIn("N1", md)
        self.assertIn("AskUserQuestion", md)


class TestOwnChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_a001_trigger_heading_in_body(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\n## When to Use\nSome text.\n",
        )
        _, extras = au.audit(skill)
        self.assertTrue(any(f.code == "A001" for f in extras))

    def test_a002_duplicate_heading(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\n## Setup\ntext\n## Setup\nmore\n",
        )
        _, extras = au.audit(skill)
        self.assertTrue(any(f.code == "A002" for f in extras))

    def test_a003_orphan_reference(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nNo links here.\n",
            extra={"references/orphan.md": "content"},
        )
        _, extras = au.audit(skill)
        self.assertTrue(any(f.code == "A003" for f in extras))

    def test_a003_not_flagged_when_linked(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [x](references/linked.md).\n",
            extra={"references/linked.md": "content"},
        )
        _, extras = au.audit(skill)
        self.assertFalse([f for f in extras if f.code == "A003"])

    def test_a005_proactive_framing_hint(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: Use PROACTIVELY when doing X.\n---\nBody.\n",
        )
        _, extras = au.audit(skill)
        self.assertTrue(any(f.code == "A005" for f in extras))

    def test_a009_japanese_in_frontmatter(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: これは日本語です\n---\nBody.\n",
        )
        _, extras = au.audit(skill)
        self.assertTrue(any(f.code == "A009" for f in extras))

    def test_a006_ignore_comment_suppresses(self):
        # scan_legacy_phrasings has its own ignore mechanism; smoke-test that a clean
        # body with no legacy phrasing produces no A006, establishing a false-positive baseline.
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nOrdinary body text.\n",
        )
        _, extras = au.audit(skill)
        self.assertFalse([f for f in extras if f.code == "A006"])


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_main_writes_report_file(self):
        skill = write_skill(self.root)
        report_path = self.root / "report.md"
        au.main(["audit_skill.py", str(skill), "--report", str(report_path)])
        self.assertTrue(report_path.exists())
        self.assertIn("Audit Report", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
