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
        report, extras, _profile = au.audit(skill)
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
        report, extras, profile = au.audit(skill)
        md = au.render_markdown(skill, report, extras, profile)
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
        _, extras, _profile = au.audit(skill)
        self.assertTrue(any(f.code == "A001" for f in extras))

    def test_a002_duplicate_heading(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\n## Setup\ntext\n## Setup\nmore\n",
        )
        _, extras, _profile = au.audit(skill)
        self.assertTrue(any(f.code == "A002" for f in extras))

    def test_a003_orphan_reference(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nNo links here.\n",
            extra={"references/orphan.md": "content"},
        )
        _, extras, _profile = au.audit(skill)
        self.assertTrue(any(f.code == "A003" for f in extras))

    def test_a003_not_flagged_when_linked(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [x](references/linked.md).\n",
            extra={"references/linked.md": "content"},
        )
        _, extras, _profile = au.audit(skill)
        self.assertFalse([f for f in extras if f.code == "A003"])

    def test_a005_proactive_framing_hint(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: Use PROACTIVELY when doing X.\n---\nBody.\n",
        )
        _, extras, _profile = au.audit(skill)
        self.assertTrue(any(f.code == "A005" for f in extras))

    def test_a009_japanese_in_frontmatter(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: これは日本語です\n---\nBody.\n",
        )
        _, extras, _profile = au.audit(skill)
        self.assertTrue(any(f.code == "A009" for f in extras))

    def test_a006_ignore_comment_suppresses(self):
        # scan_legacy_phrasings has its own ignore mechanism; smoke-test that a clean
        # body with no legacy phrasing produces no A006, establishing a false-positive baseline.
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nOrdinary body text.\n",
        )
        _, extras, _profile = au.audit(skill)
        self.assertFalse([f for f in extras if f.code == "A006"])


class TestA006LegacyPhrasing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_hit(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nPlease double-check your work.\n",
        )
        _, extras, _profile = au.audit(skill)
        self.assertTrue(any(f.code == "A006" for f in extras))

    def test_line_level_ignore_suppresses(self):
        skill = write_skill(
            self.root,
            skill_md=(
                "---\nname: sample-skill\ndescription: d\n---\n"
                "Please double-check your work. <!-- audit-ignore: A006 -->\n"
            ),
        )
        _, extras, _profile = au.audit(skill)
        self.assertFalse([f for f in extras if f.code == "A006"])

    def test_file_level_ignore_suppresses_whole_file(self):
        # audit-ignore-file must be honored only within the first 5 lines.
        skill_md = (
            "---\nname: sample-skill\ndescription: d\n---\n"
            "<!-- audit-ignore-file: A006 -->\n"
            "Please double-check your work.\n"
        )
        skill = write_skill(self.root, skill_md=skill_md)
        _, extras, _profile = au.audit(skill)
        self.assertFalse([f for f in extras if f.code == "A006"])

    def test_file_level_ignore_outside_header_not_honored(self):
        # Push the directive past line 5 of the body (frontmatter ends body_start
        # at line 4, so this directive lands beyond IGNORE_FILE_HEADER_LINES).
        skill_md = (
            "---\nname: sample-skill\ndescription: d\n---\n"
            "line one\nline two\nline three\nline four\nline five\nline six\n"
            "<!-- audit-ignore-file: A006 -->\n"
            "Please double-check your work.\n"
        )
        skill = write_skill(self.root, skill_md=skill_md)
        _, extras, _profile = au.audit(skill)
        self.assertTrue(any(f.code == "A006" for f in extras))


class TestA007RefToRefLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_ref_to_ref_link_flagged(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [a](references/a.md).\n",
            extra={
                "references/a.md": "See [b](b.md) for more.",
                "references/b.md": "content",
            },
        )
        _, extras, _profile = au.audit(skill)
        a007 = [f for f in extras if f.code == "A007"]
        self.assertEqual(len(a007), 1)
        self.assertIn("b.md", a007[0].message)

    def test_external_anchor_and_self_links_not_flagged(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [a](references/a.md).\n",
            extra={
                "references/a.md": (
                    "See [external](https://example.com/b.md), "
                    "[anchor](#section), and [self](a.md#section).\n"
                ),
            },
        )
        _, extras, _profile = au.audit(skill)
        self.assertFalse([f for f in extras if f.code == "A007"])

    def test_file_level_ignore_suppresses_a007(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [a](references/a.md).\n",
            extra={
                "references/a.md": "<!-- audit-ignore-file: A007 -->\nSee [b](b.md).\n",
                "references/b.md": "content",
            },
        )
        _, extras, _profile = au.audit(skill)
        self.assertFalse([f for f in extras if f.code == "A007"])


class TestA008MissingToc(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _long_body(self, header_lines: list[str]) -> str:
        body_lines = list(header_lines)
        while len(body_lines) <= 100:
            body_lines.append(f"line {len(body_lines)}")
        return "\n".join(body_lines) + "\n"

    def test_long_reference_without_toc_flagged(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [a](references/a.md).\n",
            extra={"references/a.md": self._long_body(["# A"])},
        )
        _, extras, _profile = au.audit(skill)
        self.assertTrue(any(f.code == "A008" for f in extras))

    def test_toc_heading_suppresses(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [a](references/a.md).\n",
            extra={"references/a.md": self._long_body(["# A", "## Table of Contents"])},
        )
        _, extras, _profile = au.audit(skill)
        self.assertFalse([f for f in extras if f.code == "A008"])

    def test_anchor_links_suppress(self):
        header = ["# A", "[one](#one)", "[two](#two)", "[three](#three)"]
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [a](references/a.md).\n",
            extra={"references/a.md": self._long_body(header)},
        )
        _, extras, _profile = au.audit(skill)
        self.assertFalse([f for f in extras if f.code == "A008"])

    def test_file_level_ignore_suppresses_a008(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [a](references/a.md).\n",
            extra={"references/a.md": self._long_body(["# A", "<!-- audit-ignore-file: A008 -->"])},
        )
        _, extras, _profile = au.audit(skill)
        self.assertFalse([f for f in extras if f.code == "A008"])


class TestBuildProfile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_phases_scripts_and_tests_detected(self):
        skill_md = (
            "---\nname: sample-skill\ndescription: d\nmetadata:\n"
            "  platforms: claude-code, codex\n---\n"
            "## Phase 1: Setup\nDelegate this to a sub-agent, in parallel.\n"
        )
        skill = write_skill(
            self.root,
            skill_md=skill_md,
            extra={
                "scripts/foo.py": "print('hi')\n",
                "scripts/tests/test_foo.py": "import unittest\n",
            },
        )
        _, _extras, profile = au.audit(skill)
        self.assertTrue(profile.has_phases)
        self.assertTrue(profile.has_scripts)
        self.assertTrue(profile.has_tests)
        self.assertTrue(profile.spawns_subagents)
        self.assertEqual(profile.platforms, "claude-code, codex")

    def test_audit_missing_skill_md_returns_default_profile(self):
        skill_dir = self.root / "no-skill-md"
        skill_dir.mkdir()
        report, extras, profile = au.audit(skill_dir)
        self.assertEqual(extras, [])
        self.assertEqual(profile, au.Profile())


class TestRenderMarkdownNoFindings(unittest.TestCase):
    def test_no_issues_detected(self):
        skill_path = Path("/tmp/does-not-matter")
        report = vs.Report(skill_path=str(skill_path), skill_name="x", description_length=1, body_lines=1)
        profile = au.Profile()
        md = au.render_markdown(skill_path, report, [], profile)
        self.assertIn("No issues detected", md)
        self.assertIn("## Profile", md)


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

    def test_main_json_payload_includes_profile(self):
        skill = write_skill(self.root)
        old_stdout = sys.stdout
        from io import StringIO
        sys.stdout = buf = StringIO()
        try:
            au.main(["audit_skill.py", str(skill), "--json"])
        finally:
            sys.stdout = old_stdout
        import json
        data = json.loads(buf.getvalue())
        for key in ("validate", "audit", "profile"):
            self.assertIn(key, data)
        for key in (
            "body_lines", "reference_count", "has_scripts", "has_tests",
            "spawns_subagents", "has_phases", "code_blocks", "platforms",
        ):
            self.assertIn(key, data["profile"])


if __name__ == "__main__":
    unittest.main()
