#!/usr/bin/env python3
"""Tests for neutrality_lint.py. Stdlib-only (unittest) — no pytest dependency,
so this runs identically under Claude Code and Codex CLI (or plain `python3 -m unittest`).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v
     (from the dual-platform-skills skill directory)
  or: python3 scripts/tests/test_neutrality_lint.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import neutrality_lint as nl  # noqa: E402


def write_skill(root: Path, skill_md: str, extra: dict[str, str] | None = None) -> Path:
    skill_dir = root / "sample-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    for rel, content in (extra or {}).items():
        p = skill_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return skill_dir


FM_DUAL = "---\nname: sample-skill\ndescription: test\nmetadata:\n  platforms: claude-code, codex\n---\n"
FM_CLAUDE_ONLY = "---\nname: sample-skill\ndescription: test\nmetadata:\n  platforms: claude-code\n---\n"
FM_NONE = "---\nname: sample-skill\ndescription: test\n---\n"


class TestFrontmatterParsing(unittest.TestCase):
    def test_platforms_dual_detected(self):
        vals, body_start = nl.parse_frontmatter(FM_DUAL)
        self.assertEqual(vals.get("metadata.platforms"), "claude-code, codex")
        self.assertEqual(body_start, 6)

    def test_no_frontmatter(self):
        vals, body_start = nl.parse_frontmatter("# just a heading\nno frontmatter here\n")
        self.assertEqual(vals, {})
        self.assertEqual(body_start, 0)


class TestErrorSeverityWhenDualPlatform(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_n1_raw_tool_name_is_error(self):
        skill = write_skill(self.root, FM_DUAL + "\nAsk the user via AskUserQuestion.\n")
        r = nl.lint(skill)
        n1 = [f for f in r.findings if f.code == "N1"]
        self.assertEqual(len(n1), 1)
        self.assertEqual(n1[0].level, "error")
        self.assertTrue(r.errors)

    def test_n2_platform_path_is_error(self):
        skill = write_skill(self.root, FM_DUAL + "\nSee ~/.claude/foo/bar.md\n")
        r = nl.lint(skill)
        n2 = [f for f in r.findings if f.code == "N2"]
        self.assertEqual(len(n2), 1)
        self.assertEqual(n2[0].level, "error")

    def test_claude_skill_dir_var_is_exempt_from_n2(self):
        skill = write_skill(self.root, FM_DUAL + "\nUse ${CLAUDE_SKILL_DIR}/scripts/x.py\n")
        r = nl.lint(skill)
        self.assertFalse([f for f in r.findings if f.code == "N2"])

    def test_n3_state_write_is_error(self):
        skill = write_skill(
            self.root, FM_DUAL + '\nRun `mkdir -p ~/.claude/my-skill/state` first.\n'
        )
        r = nl.lint(skill)
        n3 = [f for f in r.findings if f.code == "N3"]
        self.assertEqual(len(n3), 1)

    def test_references_and_templates_scanned(self):
        skill = write_skill(
            self.root, FM_DUAL,
            extra={
                "references/deep.md": "nested AskUserQuestion usage",
                "templates/t.md": "also uses TodoWrite here",
            },
        )
        r = nl.lint(skill)
        files_hit = {Path(f.file).name for f in r.findings if f.code == "N1"}
        self.assertEqual(files_hit, {"deep.md", "t.md"})

    def test_frontmatter_block_exempt(self):
        # allowed-tools listing AskUserQuestion in frontmatter must NOT trigger N1.
        fm = "---\nname: s\ndescription: d\nallowed-tools: Read, AskUserQuestion\nmetadata:\n  platforms: claude-code, codex\n---\nBody has none.\n"
        skill = write_skill(self.root, fm)
        r = nl.lint(skill)
        self.assertFalse([f for f in r.findings if f.code == "N1"])


class TestSeverityByPlatformsDeclaration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_claude_only_skips_n1_n3(self):
        skill = write_skill(self.root, FM_CLAUDE_ONLY + "\nAskUserQuestion is fine here.\n")
        r = nl.lint(skill)
        self.assertFalse(r.findings)
        self.assertFalse(r.errors)

    def test_no_platforms_declared_is_warning_not_error(self):
        skill = write_skill(self.root, FM_NONE + "\nAskUserQuestion appears.\n")
        r = nl.lint(skill)
        n1 = [f for f in r.findings if f.code == "N1"]
        self.assertEqual(n1[0].level, "warning")
        n4 = [f for f in r.findings if f.code == "N4"]
        self.assertEqual(len(n4), 1)
        self.assertFalse(r.errors)


class TestExemptions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_platform_annex_file_fully_skipped(self):
        skill = write_skill(
            self.root, FM_DUAL,
            extra={"references/platform-notes.md": "<!-- platform-annex -->\n# Notes\nAskUserQuestion, CLAUDE_PLUGIN_ROOT, ~/.claude/x\n"},
        )
        r = nl.lint(skill)
        self.assertFalse(r.findings)

    def test_inline_ignore_comment_suppresses_single_code(self):
        skill = write_skill(
            self.root, FM_DUAL + "\nAskUserQuestion here. <!-- neutrality-ignore: N1 -->\n"
        )
        r = nl.lint(skill)
        self.assertFalse([f for f in r.findings if f.code == "N1"])

    def test_two_ignore_comments_on_one_line_both_honored(self):
        # Regression: a line with two separate ignore comments must suppress BOTH codes,
        # not just the first one matched.
        skill = write_skill(
            self.root,
            FM_DUAL + "\nUses subagent_type and ~/.claude/x.md here."
            " <!-- neutrality-ignore: N1 --> <!-- neutrality-ignore: N2 -->\n",
        )
        r = nl.lint(skill)
        self.assertFalse(r.findings)


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_main_exit_code_1_on_error(self):
        skill = write_skill(self.root, FM_DUAL + "\nAskUserQuestion.\n")
        self.assertEqual(nl.main(["neutrality_lint.py", str(skill)]), 1)

    def test_main_exit_code_0_when_clean(self):
        skill = write_skill(self.root, FM_DUAL + "\nAll clear.\n")
        self.assertEqual(nl.main(["neutrality_lint.py", str(skill)]), 0)

    def test_main_exit_code_2_bad_invocation(self):
        self.assertEqual(nl.main(["neutrality_lint.py", str(self.root / "nope")]), 2)


if __name__ == "__main__":
    unittest.main()
