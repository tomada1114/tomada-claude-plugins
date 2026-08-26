#!/usr/bin/env python3
"""Tests for inventory.py. Stdlib-only (unittest).

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

STUB = inv.MANAGED_BLOCK
LEGACY_BODY = "# Project\n\nRun `npm test` before pushing.\n"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def has_git() -> bool:
    return shutil.which("git") is not None


def run_main(argv):
    """Return (exit_code, stdout, stderr) for a main() call."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = inv.main(argv)
    return code, out.getvalue(), err.getvalue()


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.codex_home = self.root / "codex-home"
        patcher = mock.patch.dict(os.environ, {"CODEX_HOME": str(self.codex_home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def build(self, **files: str) -> Path:
        for rel, text in files.items():
            write(self.root / rel, text)
        return self.root


class TestParseClaudeMd(RepoCase):
    def test_pure_stub(self):
        p = inv.parse_claude_md(STUB)
        self.assertEqual(p.state, "stub")
        self.assertEqual(p.free_section, "")

    def test_stub_tolerates_trailing_whitespace_only(self):
        self.assertEqual(inv.parse_claude_md(STUB + "\n\n").state, "stub")

    def test_stub_with_extras(self):
        p = inv.parse_claude_md(STUB + "\n# Claude Code specifics\n\n- hooks\n")
        self.assertEqual(p.state, "stub+extras")
        self.assertEqual(p.free_section, "\n# Claude Code specifics\n\n- hooks\n")

    def test_legacy(self):
        p = inv.parse_claude_md(LEGACY_BODY)
        self.assertEqual(p.state, "legacy")

    def test_legacy_import_bare(self):
        self.assertEqual(inv.parse_claude_md("@AGENTS.md\n\n# Extra\n").state, "legacy-import")

    def test_legacy_import_dot_slash(self):
        self.assertEqual(inv.parse_claude_md("@./AGENTS.md\n").state, "legacy-import")

    def test_import_inside_a_fence_is_not_an_import(self):
        text = "# Doc\n\n```\n@AGENTS.md\n```\n"
        self.assertEqual(inv.parse_claude_md(text).state, "legacy")

    def test_malformed_begin_without_end(self):
        p = inv.parse_claude_md(inv.MANAGED_BEGIN + "\n@AGENTS.md\n")
        self.assertEqual(p.state, "malformed")
        self.assertFalse(p.repairable)

    def test_malformed_end_without_begin(self):
        p = inv.parse_claude_md("@AGENTS.md\n" + inv.MANAGED_END + "\n")
        self.assertEqual(p.state, "malformed")
        self.assertFalse(p.repairable)

    def test_malformed_wrong_inner_content(self):
        text = inv.MANAGED_BEGIN + "\n@OTHER.md\n" + inv.MANAGED_END + "\ntail\n"
        p = inv.parse_claude_md(text)
        self.assertEqual(p.state, "malformed")
        self.assertTrue(p.repairable)
        self.assertIn("@OTHER.md", p.detail)

    def test_malformed_block_not_at_top(self):
        text = "# Title\n\n" + STUB + "\nfree\n"
        p = inv.parse_claude_md(text)
        self.assertEqual(p.state, "malformed")
        self.assertTrue(p.repairable)
        self.assertEqual(p.preamble, "# Title\n\n")

    def test_compose_is_byte_stable(self):
        text = STUB + "\n# Claude Code specifics\r\n\r\nCRLF body\r\n"
        p = inv.parse_claude_md(text)
        self.assertEqual(inv.compose_stub(p.free_section), text)

    def test_adopt_free_section_keeps_order(self):
        text = "@AGENTS.md\n\n# Claude Code Specifics\n\n- hooks\n"
        self.assertEqual(inv.adopt_free_section(text), "\n# Claude Code Specifics\n\n- hooks\n")

    def test_adopt_free_section_import_only(self):
        self.assertEqual(inv.adopt_free_section("@AGENTS.md\n"), "")

    def test_adopt_free_section_keeps_lines_before_the_import(self):
        self.assertEqual(inv.adopt_free_section("# Top\n@AGENTS.md\nafter\n"),
                         "\n# Top\nafter\n")

    def test_repair_free_section_merges_preamble_and_tail(self):
        p = inv.parse_claude_md("# Title\n\n" + STUB + "\ntail\n")
        self.assertEqual(inv.repair_free_section(p), "\n# Title\n\ntail\n")

    def test_repair_free_section_empty(self):
        p = inv.parse_claude_md(inv.MANAGED_BEGIN + "\nwrong\n" + inv.MANAGED_END + "\n")
        self.assertEqual(inv.repair_free_section(p), "")


class TestIO(RepoCase):
    def test_read_write_roundtrip_preserves_crlf_and_bad_bytes(self):
        path = self.root / "CLAUDE.md"
        path.write_bytes(b"a\r\nb\xff\n")
        text = inv.read_text(path)
        inv.write_text(path, text)
        self.assertEqual(path.read_bytes(), b"a\r\nb\xff\n")

    def test_count_lines(self):
        self.assertEqual(inv.count_lines("a\nb\n"), 2)


class TestFrontmatter(RepoCase):
    def test_single_string(self):
        self.assertEqual(inv.parse_frontmatter_paths('---\npaths: "src/**"\n---\n'), ["src/**"])

    def test_unquoted_string(self):
        self.assertEqual(inv.parse_frontmatter_paths("---\npaths: src/**\n---\n"), ["src/**"])

    def test_inline_list(self):
        self.assertEqual(
            inv.parse_frontmatter_paths('---\npaths: ["a/**", \'b/**\']\n---\n'),
            ["a/**", "b/**"])

    def test_empty_inline_list(self):
        self.assertEqual(inv.parse_frontmatter_paths("---\npaths: []\n---\n"), [])

    def test_block_list(self):
        text = '---\npaths:\n  - "src/**/*.jsx"\n  - scripts/**\n---\n'
        self.assertEqual(inv.parse_frontmatter_paths(text), ["src/**/*.jsx", "scripts/**"])

    def test_block_list_stops_at_next_key(self):
        text = "---\npaths:\n  - a/**\nother: x\n---\n"
        self.assertEqual(inv.parse_frontmatter_paths(text), ["a/**"])

    def test_no_frontmatter(self):
        self.assertIsNone(inv.parse_frontmatter_paths("# Rule\n"))

    def test_unterminated_frontmatter(self):
        self.assertIsNone(inv.parse_frontmatter_paths("---\npaths: a\n"))

    def test_frontmatter_without_paths(self):
        self.assertIsNone(inv.parse_frontmatter_paths("---\nname: x\n---\n"))

    def test_empty_file(self):
        self.assertIsNone(inv.parse_frontmatter_paths(""))


class TestRuleScope(RepoCase):
    def test_global(self):
        self.assertEqual(inv.classify_rule_scope(None, self.root), ("global", None, False))

    def test_directory(self):
        (self.root / "src").mkdir()
        self.assertEqual(inv.classify_rule_scope(["src/**/*.jsx"], self.root),
                         ("directory", "src", False))

    def test_nested_directory(self):
        (self.root / "packages" / "api").mkdir(parents=True)
        self.assertEqual(inv.classify_rule_scope(["packages/api/**"], self.root),
                         ("directory", "packages/api", False))

    def test_pattern_only(self):
        self.assertEqual(inv.classify_rule_scope(["**/*.test.ts", "*.md"], self.root),
                         ("pattern", None, True))

    def test_directory_that_does_not_exist_is_a_pattern(self):
        self.assertEqual(inv.classify_rule_scope(["nope/**"], self.root),
                         ("pattern", None, True))

    def test_two_dirs_share_a_parent(self):
        (self.root / "src" / "a").mkdir(parents=True)
        (self.root / "src" / "b").mkdir(parents=True)
        self.assertEqual(inv.classify_rule_scope(["src/a/**", "src/b/**"], self.root),
                         ("directory", "src", False))

    def test_disjoint_dirs_are_mixed(self):
        (self.root / "src").mkdir()
        (self.root / "docs").mkdir()
        self.assertEqual(inv.classify_rule_scope(["src/**", "docs/**"], self.root),
                         ("mixed", None, False))

    def test_dir_plus_pattern_is_mixed(self):
        (self.root / "src").mkdir()
        self.assertEqual(inv.classify_rule_scope(["src/**", "**/*.md"], self.root),
                         ("mixed", None, False))

    def test_empty_paths_list_is_pattern(self):
        self.assertEqual(inv.classify_rule_scope([], self.root), ("pattern", None, True))

    def test_literal_prefix_dir(self):
        self.assertEqual(inv.literal_prefix_dir("src/**/*.jsx"), "src")
        self.assertEqual(inv.literal_prefix_dir("*.md"), "")
        self.assertEqual(inv.literal_prefix_dir("a/b/c.ts"), "a/b")


class TestBuildInventory(RepoCase):
    def test_states_across_a_repo(self):
        self.build(**{
            "AGENTS.md": "# Root\n",
            "CLAUDE.md": STUB,
            "packages/api/AGENTS.md": "# API\n",
            "packages/web/AGENTS.md": "# Web\n",
            "packages/web/CLAUDE.md": LEGACY_BODY,
            "docs/CLAUDE.md": "# Docs only\n",
        })
        result = inv.build_inventory(self.root)
        states = {c.path: c.state for c in result.claude_md}
        self.assertEqual(states["CLAUDE.md"], "stub")
        self.assertEqual(states["packages/api/CLAUDE.md"], "missing")
        self.assertEqual(states["packages/web/CLAUDE.md"], "legacy")
        self.assertEqual(states["docs/CLAUDE.md"], "orphan")
        codes = {f.code for f in result.findings}
        self.assertEqual(codes, {"R001", "R002", "R003"})
        self.assertEqual(result.suggested_mode, "migrate")
        self.assertTrue(inv.has_blocking_findings(result))

    def test_stub_with_extras_counts_free_lines(self):
        self.build(**{"AGENTS.md": "x\n", "CLAUDE.md": STUB + "\n# Claude\n- hooks\n"})
        entry = inv.build_inventory(self.root).claude_md[0]
        self.assertEqual(entry.state, "stub+extras")
        self.assertEqual(entry.free_section_lines, 2)

    def test_inverted_import_finding(self):
        self.build(**{"AGENTS.md": "@./CLAUDE.md\n\n# Project\n", "CLAUDE.md": STUB})
        result = inv.build_inventory(self.root)
        self.assertEqual(result.agents_md[0].inverted_imports,
                         [{"line": 1, "text": "@./CLAUDE.md"}])
        r004 = [f for f in result.findings if f.code == "R004"]
        self.assertEqual(r004[0].line, 1)
        self.assertEqual(r004[0].severity, "error")
        self.assertEqual(result.suggested_mode, "migrate")

    def test_fenced_import_in_agents_md_is_ignored(self):
        self.build(**{"AGENTS.md": "# P\n\n```md\n@AGENTS.md\n```\n", "CLAUDE.md": STUB})
        result = inv.build_inventory(self.root)
        self.assertEqual(result.agents_md[0].inverted_imports, [])
        self.assertEqual(result.suggested_mode, "audit")

    def test_codex_budget_chain(self):
        big = "x" * 20000 + "\n"
        self.build(**{
            "AGENTS.md": big, "CLAUDE.md": STUB,
            "packages/api/AGENTS.md": big, "packages/api/CLAUDE.md": STUB,
        })
        result = inv.build_inventory(self.root)
        by_dir = {e.dir: e for e in result.agents_md}
        self.assertFalse(by_dir["."].over_codex_budget)
        self.assertTrue(by_dir["packages/api"].over_codex_budget)
        self.assertGreater(by_dir["packages/api"].chain_bytes, inv.CODEX_DOC_BUDGET)
        self.assertTrue(any(f.code == "R005" for f in result.findings))

    def test_legacy_import_and_local_and_alt_and_rules(self):
        (self.root / "src").mkdir()
        self.build(**{
            "AGENTS.md": "# Root\n",
            "CLAUDE.md": "@AGENTS.md\n\n# Claude Code Specifics\n",
            "CLAUDE.local.md": "personal\n",
            ".claude/CLAUDE.md": "alt content\n",
            ".claude/rules/component-rules.md": '---\npaths:\n  - "src/**/*.jsx"\n---\n\n- rule\n',
        })
        result = inv.build_inventory(self.root)
        self.assertEqual(result.claude_md[0].state, "legacy-import")
        self.assertEqual(result.claude_local_md, ["CLAUDE.local.md"])
        self.assertEqual(result.dot_claude_claude_md, [".claude/CLAUDE.md"])
        self.assertEqual(result.rules[0].scope, "directory")
        self.assertEqual(result.rules[0].scope_dir, "src")
        self.assertFalse(result.rules[0].pattern_only)
        codes = {f.code for f in result.findings}
        self.assertTrue({"R007", "R008", "R009", "R010"} <= codes)
        self.assertEqual(result.suggested_mode, "migrate")

    def test_empty_alt_claude_md_is_not_a_finding(self):
        self.build(**{"AGENTS.md": "# Root\n", "CLAUDE.md": STUB, ".claude/CLAUDE.md": ""})
        result = inv.build_inventory(self.root)
        self.assertFalse(any(f.code == "R007" for f in result.findings))
        self.assertEqual(result.suggested_mode, "audit")

    def test_rules_alone_suggest_migrate(self):
        self.build(**{"AGENTS.md": "# Root\n", "CLAUDE.md": STUB,
                      ".claude/rules/r.md": "- rule\n"})
        result = inv.build_inventory(self.root)
        self.assertEqual(result.rules[0].scope, "global")
        self.assertIsNone(result.rules[0].paths)
        self.assertEqual(result.suggested_mode, "migrate")

    def test_malformed_finding(self):
        self.build(**{"AGENTS.md": "x\n", "CLAUDE.md": inv.MANAGED_BEGIN + "\n@AGENTS.md\n"})
        result = inv.build_inventory(self.root)
        self.assertTrue(any(f.code == "R006" for f in result.findings))

    def test_suggested_mode_init_on_empty_project(self):
        (self.root / "src").mkdir()
        result = inv.build_inventory(self.root)
        self.assertEqual(result.suggested_mode, "init")
        self.assertEqual(result.findings, [])
        self.assertFalse(inv.has_blocking_findings(result))

    def test_suggested_mode_init_ignores_an_empty_claude_md(self):
        self.build(**{"CLAUDE.md": "\n\n"})
        self.assertEqual(inv.build_inventory(self.root).suggested_mode, "init")

    def test_suggested_mode_audit_when_clean(self):
        self.build(**{"AGENTS.md": "# Root\n", "CLAUDE.md": STUB})
        result = inv.build_inventory(self.root)
        self.assertEqual(result.suggested_mode, "audit")
        self.assertEqual(result.findings, [])

    def test_skips_noise_directories(self):
        self.build(**{
            "AGENTS.md": "# Root\n", "CLAUDE.md": STUB,
            "node_modules/pkg/AGENTS.md": "# vendored\n",
            ".venv/lib/AGENTS.md": "# venv\n",
        })
        result = inv.build_inventory(self.root)
        self.assertEqual([e.path for e in result.agents_md], ["AGENTS.md"])

    def test_max_depth_prunes(self):
        self.build(**{"a/b/c/AGENTS.md": "# deep\n"})
        self.assertEqual(inv.build_inventory(self.root, max_depth=2).agents_md, [])
        self.assertEqual(len(inv.build_inventory(self.root, max_depth=3).agents_md), 1)

    def test_default_scan_reaches_deep_directories(self):
        self.build(**{"a/b/c/d/e/f/AGENTS.md": "# deep\n"})
        self.assertEqual(
            [entry.path for entry in inv.build_inventory(self.root).agents_md],
            ["a/b/c/d/e/f/AGENTS.md"],
        )

    def test_codex_override_shadows_canonical_file(self):
        self.build(**{
            "AGENTS.md": "# shared\n",
            "CLAUDE.md": STUB,
            "AGENTS.override.md": "# Codex-only\n",
        })
        result = inv.build_inventory(self.root)
        self.assertEqual(result.agents_md[0].codex_source, "AGENTS.override.md")
        active = [source.path for source in result.codex.sources if source.active]
        self.assertEqual(active, ["AGENTS.override.md"])
        self.assertTrue(any(f.code == "R011" for f in result.findings))

    def test_project_codex_config_selects_fallback_and_budget(self):
        self.build(**{
            ".codex/config.toml": (
                "project_doc_max_bytes = 100\n"
                'project_doc_fallback_filenames = ["agents.local.md"]\n'
            ),
            "agents.local.md": "# fallback\n",
        })
        result = inv.build_inventory(self.root)
        self.assertEqual(result.codex.budget, 100)
        self.assertEqual(result.codex.budget_source, ".codex/config.toml")
        self.assertEqual(result.codex.fallback_names, ["agents.local.md"])
        self.assertEqual(
            [(source.path, source.active) for source in result.codex.sources],
            [("agents.local.md", True)],
        )
        self.assertTrue(any(f.code == "R012" for f in result.findings))

    def test_noncanonical_agents_filename_is_not_loaded_without_a_configured_fallback(self):
        self.build(**{"agent-rules.md": "# not automatic\n"})
        result = inv.build_inventory(self.root)
        self.assertEqual(result.codex.sources, [])
        self.assertEqual(result.agents_md, [])


class TestGit(RepoCase):
    def test_git_info_for_non_repo(self):
        info = inv.git_info(self.root)
        self.assertFalse(info["is_repo"])
        self.assertEqual(info["dirty_paths"], [])

    @unittest.skipUnless(has_git(), "git is not installed")
    def test_git_info_lists_dirty_rule_files(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True,
                       capture_output=True)
        self.build(**{"AGENTS.md": "# Root\n", "CLAUDE.md": STUB, "src.py": "x\n"})
        info = inv.git_info(self.root)
        self.assertTrue(info["is_repo"])
        self.assertEqual(info["dirty_paths"], ["AGENTS.md", "CLAUDE.md"])
        self.assertEqual(Path(str(info["toplevel"])).resolve(), self.root)

    @unittest.skipUnless(has_git(), "git is not installed")
    def test_default_root_is_the_git_toplevel(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True,
                       capture_output=True)
        sub = self.root / "packages" / "api"
        sub.mkdir(parents=True)
        self.assertEqual(inv.default_root(sub).resolve(), self.root)

    def test_default_root_without_git_is_cwd(self):
        self.assertEqual(inv.default_root(self.root), self.root)


class TestCli(RepoCase):
    def test_json_output_and_exit_1(self):
        self.build(**{"AGENTS.md": "# Root\n"})
        code, out, _ = run_main([str(self.root), "--json"])
        data = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(data["claude_md"][0]["state"], "missing")
        self.assertIn("findings", data)
        self.assertEqual(data["root"], str(self.root))

    def test_text_output_and_exit_0(self):
        self.build(**{"AGENTS.md": "# Root\n", "CLAUDE.md": STUB})
        code, out, _ = run_main([str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("suggested mode: audit", out)
        self.assertIn("(none)", out)

    def test_text_output_full_report(self):
        (self.root / "src").mkdir()
        self.build(**{
            "AGENTS.md": "@./CLAUDE.md\n# Root\n",
            "CLAUDE.md": STUB + "\n# Claude\n",
            "CLAUDE.local.md": "mine\n",
            ".claude/CLAUDE.md": "alt\n",
            ".claude/rules/r.md": "---\npaths: src/**\n---\n",
        })
        code, out, _ = run_main([str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn("CLAUDE.local.md", out)
        self.assertIn(".claude/rules", out)
        self.assertIn("free section 1 lines", out)
        self.assertIn("line 1: @./CLAUDE.md", out)

    def test_text_output_on_empty_project(self):
        code, out, _ = run_main([str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("AGENTS.md (0)", out)
        self.assertIn("(none)", out)

    def test_missing_root_exits_2(self):
        code, _, err = run_main([str(self.root / "nope")])
        self.assertEqual(code, 2)
        self.assertIn("Pass an existing directory", err)

    def test_bad_max_depth_exits_2(self):
        code, _, err = run_main([str(self.root), "--max-depth", "0"])
        self.assertEqual(code, 2)
        self.assertIn("--max-depth", err)

    def test_default_root_when_omitted(self):
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        write(self.root / "AGENTS.md", "# Root\n")
        write(self.root / "CLAUDE.md", STUB)
        code, out, _ = run_main(["--json"])
        self.assertEqual(code, 0)
        self.assertIn("suggested_mode", out)

    @unittest.skipUnless(has_git(), "git is not installed")
    def test_dirty_paths_render_in_text_output(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        self.build(**{"AGENTS.md": "# Root\n", "CLAUDE.md": STUB})
        _, out, _ = run_main([str(self.root)])
        self.assertIn("uncommitted rule files", out)


if __name__ == "__main__":
    unittest.main()
