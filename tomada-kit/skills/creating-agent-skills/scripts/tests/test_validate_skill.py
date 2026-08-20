#!/usr/bin/env python3
"""Tests for validate_skill.py. Stdlib-only (unittest).

Run: python3 -m unittest scripts.tests.test_validate_skill -v
     (from the creating-agent-skills skill directory)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
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


class TestFrontmatterParsing(unittest.TestCase):
    def test_basic_fields(self):
        fields, body_start = vs.parse_frontmatter("---\nname: foo\ndescription: bar\n---\nBody\n")
        self.assertEqual(fields["name"], "foo")
        self.assertEqual(fields["description"], "bar")
        self.assertEqual(body_start, 4)

    def test_quoted_value_unquoted(self):
        fields, _ = vs.parse_frontmatter('---\nname: foo\ndescription: "quoted value"\n---\n')
        self.assertEqual(fields["description"], "quoted value")

    def test_continuation_line_joined(self):
        text = "---\nname: foo\ndescription: first part\n  second part\n---\n"
        fields, _ = vs.parse_frontmatter(text)
        self.assertEqual(fields["description"], "first part second part")

    def test_no_frontmatter_returns_empty(self):
        fields, body_start = vs.parse_frontmatter("# no frontmatter\n")
        self.assertEqual(fields, {})
        self.assertEqual(body_start, 0)


class TestRequiredFields(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_missing_skill_md_e002(self):
        d = self.root / "empty"
        d.mkdir()
        r = vs.validate(d)
        self.assertTrue(any(f.code == "E002" for f in r.errors))

    def test_missing_name_e010(self):
        skill = write_skill(self.root, skill_md="---\ndescription: d\n---\nBody\n")
        r = vs.validate(skill)
        self.assertTrue(any(f.code == "E010" for f in r.errors))

    def test_bad_name_format_e011(self):
        skill = write_skill(self.root, skill_md="---\nname: Bad_Name!\ndescription: d\n---\nBody\n")
        r = vs.validate(skill)
        self.assertTrue(any(f.code == "E011" for f in r.errors))

    def test_consecutive_hyphens_e014(self):
        skill = write_skill(self.root, skill_md="---\nname: bad--name\ndescription: d\n---\nBody\n")
        r = vs.validate(skill)
        self.assertTrue(any(f.code == "E014" for f in r.errors))

    def test_name_mismatch_w013(self):
        skill = write_skill(self.root, name="dir-name", skill_md="---\nname: other-name\ndescription: d\n---\n")
        r = vs.validate(skill)
        self.assertTrue(any(f.code == "W013" for f in r.warnings))

    def test_missing_description_e020(self):
        skill = write_skill(self.root, skill_md="---\nname: sample-skill\n---\nBody\n")
        r = vs.validate(skill)
        self.assertTrue(any(f.code == "E020" for f in r.errors))

    def test_description_too_long_e021(self):
        skill = write_skill(self.root, skill_md="---\nname: sample-skill\ndescription: " + ("x" * 1025) + "\n---\n")
        r = vs.validate(skill)
        self.assertTrue(any(f.code == "E021" for f in r.errors))

    def test_clean_skill_no_findings(self):
        skill = write_skill(self.root, skill_md="---\nname: sample-skill\ndescription: fine\n---\nBody.\n")
        r = vs.validate(skill)
        self.assertFalse(r.errors)


class TestLinkIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_broken_link_e041(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [x](references/missing.md).\n",
        )
        r = vs.validate(skill)
        self.assertTrue(any(f.code == "E041" for f in r.errors))

    def test_existing_link_ok(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [x](references/present.md).\n",
            extra={"references/present.md": "content"},
        )
        r = vs.validate(skill)
        self.assertFalse([f for f in r.findings if f.code == "E041"])

    def test_link_escaping_skill_dir_w040(self):
        skill = write_skill(
            self.root,
            skill_md="---\nname: sample-skill\ndescription: d\n---\nSee [x](../outside.md).\n",
        )
        r = vs.validate(skill)
        self.assertTrue(any(f.code == "W040" for f in r.warnings))


class TestNeutralityIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_neutrality_lint_loadable_from_sibling_skill(self):
        # This is the real integration point: dual-platform-skills must actually be
        # findable at ../../dual-platform-skills/scripts/neutrality_lint.py relative to
        # this test file's real location — not a fixture. Skip gracefully if the sibling
        # skill isn't present (e.g. this test run in isolation without the repo layout).
        mod = vs._load_neutrality_lint()
        if mod is None:
            self.skipTest("dual-platform-skills sibling skill not found in this checkout")
        self.assertTrue(hasattr(mod, "lint"))

    def test_ask_user_question_in_body_surfaces_as_n1_finding(self):
        if vs._load_neutrality_lint() is None:
            self.skipTest("dual-platform-skills sibling skill not found in this checkout")
        skill = write_skill(
            self.root,
            skill_md=(
                "---\nname: sample-skill\ndescription: d\nmetadata:\n"
                "  platforms: claude-code, codex\n---\nAsk via AskUserQuestion.\n"
            ),
        )
        r = vs.validate(skill)
        n1 = [f for f in r.findings if f.code == "N1"]
        self.assertEqual(len(n1), 1)
        self.assertEqual(n1[0].level, "error")
        self.assertTrue(r.errors)

    def test_missing_dual_platform_skills_degrades_gracefully(self):
        # Simulate the sibling skill not existing: _load_neutrality_lint should return
        # None rather than raising, and validate() must still complete check 1-8.
        import validate_skill as vs_mod
        orig = vs_mod._load_neutrality_lint
        vs_mod._load_neutrality_lint = lambda: None
        try:
            skill = write_skill(self.root, skill_md="---\nname: sample-skill\ndescription: d\n---\nBody.\n")
            r = vs_mod.validate(skill)
            self.assertFalse(r.errors)
        finally:
            vs_mod._load_neutrality_lint = orig


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_main_returns_1_on_error(self):
        skill = write_skill(self.root, skill_md="---\ndescription: d\n---\n")
        self.assertEqual(vs.main(["validate_skill.py", str(skill)]), 1)

    def test_main_returns_0_when_clean(self):
        skill = write_skill(self.root)
        self.assertEqual(vs.main(["validate_skill.py", str(skill)]), 0)

    def test_main_returns_2_bad_invocation(self):
        self.assertEqual(vs.main(["validate_skill.py"]), 2)


if __name__ == "__main__":
    unittest.main()
