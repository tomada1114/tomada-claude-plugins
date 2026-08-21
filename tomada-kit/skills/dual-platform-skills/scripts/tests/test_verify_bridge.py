#!/usr/bin/env python3
"""Tests for verify_bridge.py. Stdlib-only (unittest).

Run: python3 -m unittest scripts.tests.test_verify_bridge -v
     (from the dual-platform-skills skill directory)
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
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

    def test_codex_home_symlink_is_found(self):
        # CODEX_HOME/skills/<name> is the primary discovery path (find_codex_links'
        # first candidate); point it at a tmpdir so this doesn't depend on the
        # real user's ~/.codex.
        skill = write_skill(self.root)
        codex_home = self.root / "fake-codex-home"
        (codex_home / "skills").mkdir(parents=True)
        link = codex_home / "skills" / skill.name
        link.symlink_to(skill)
        old = os.environ.get("CODEX_HOME")
        os.environ["CODEX_HOME"] = str(codex_home)
        try:
            found = vb.find_codex_links(skill, [])
        finally:
            if old is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = old
        self.assertEqual(found, [str(link)])

    def test_same_link_passed_as_extra_is_not_duplicated(self):
        # When a link already found via CODEX_HOME is also passed via --codex-link,
        # `seen` must prevent it from appearing twice.
        skill = write_skill(self.root)
        codex_home = self.root / "fake-codex-home"
        (codex_home / "skills").mkdir(parents=True)
        link = codex_home / "skills" / skill.name
        link.symlink_to(skill)
        old = os.environ.get("CODEX_HOME")
        os.environ["CODEX_HOME"] = str(codex_home)
        try:
            found = vb.find_codex_links(skill, [str(link)])
        finally:
            if old is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = old
        self.assertEqual(found, [str(link)])


class TestFrontmatterParsing(unittest.TestCase):
    def test_no_frontmatter_returns_empty(self):
        keys, vals, body_start = vb.fm_keys_and_required("no frontmatter here\njust text\n")
        self.assertEqual((keys, vals, body_start), ([], {}, 0))

    def test_missing_name_is_v2_error(self):
        with tempfile.TemporaryDirectory() as td:
            skill = write_skill(Path(td), "---\ndescription: test\n---\nBody.\n")
            r = vb.verify(skill, [])
            v2 = [f for f in r.errors if f.code == "V2"]
            self.assertTrue(any("name" in f.message for f in v2))


class TestV3ExtraFrontmatterFields(unittest.TestCase):
    def test_non_codex_field_is_v3_warning(self):
        with tempfile.TemporaryDirectory() as td:
            fm = "---\nname: sample-skill\ndescription: test\nallowed-tools: Read\n---\n"
            skill = write_skill(Path(td), fm + "\nBody.\n")
            r = vb.verify(skill, [])
            v3 = [f for f in r.findings if f.code == "V3"]
            self.assertEqual(len(v3), 1)
            self.assertIn("allowed-tools", v3[0].message)


class TestV7SkipsExternalLinks(unittest.TestCase):
    def test_http_mailto_and_absolute_links_are_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            body = (
                FM
                + "\nSee [ext](https://example.com/x), [mail](mailto:a@example.com), "
                + "and [abs](/etc/passwd).\n"
            )
            skill = write_skill(Path(td), body)
            r = vb.verify(skill, [])
            self.assertFalse([f for f in r.findings if f.code == "V7"])


class TestRenderHuman(unittest.TestCase):
    def test_clean_report_renders_ok(self):
        with tempfile.TemporaryDirectory() as td:
            skill = write_skill(Path(td))
            codex_dir = Path(td) / "codex-skills"
            codex_dir.mkdir()
            (codex_dir / skill.name).symlink_to(skill)
            r = vb.verify(skill, [str(codex_dir / skill.name)])
            out = vb.render_human(r)
            self.assertIn("OK — fully bridged, no issues.", out)
            self.assertIn(skill.name, out)

    def test_report_with_findings_groups_by_level(self):
        with tempfile.TemporaryDirectory() as td:
            skill = write_skill(Path(td), "---\ndescription: test\n---\nBody.\n")
            r = vb.verify(skill, [])
            out = vb.render_human(r)
            self.assertIn("ERRORS:", out)
            self.assertIn("V2:", out)


class TestMainCLI(unittest.TestCase):
    def test_help_returns_2(self):
        self.assertEqual(vb.main(["verify_bridge.py", "--help"]), 2)

    def test_no_args_returns_2(self):
        self.assertEqual(vb.main(["verify_bridge.py"]), 2)

    def test_clean_skill_returns_0_and_json_has_codex_runnable(self):
        with tempfile.TemporaryDirectory() as td:
            skill = write_skill(Path(td))
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = vb.main(["verify_bridge.py", str(skill), "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertIn("codex_runnable", data)
            self.assertTrue(data["codex_runnable"])

    def test_broken_link_skill_returns_1(self):
        with tempfile.TemporaryDirectory() as td:
            skill = write_skill(Path(td), FM + "\nSee [x](references/missing.md).\n")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = vb.main(["verify_bridge.py", str(skill)])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
