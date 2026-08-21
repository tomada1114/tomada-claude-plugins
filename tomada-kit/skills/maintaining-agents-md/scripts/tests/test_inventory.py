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



def hook_entry(command, matcher="Edit|Write", **extra):
    hook = {"type": "command", "command": command}
    hook.update(extra)
    return {"matcher": matcher, "hooks": [hook]}


def settings_json(hooks, **extra):
    data = dict(extra)
    data["hooks"] = hooks
    return json.dumps(data, indent=2) + "\n"


TOPLEVEL = inv.TOPLEVEL_EXPR
CLAUDE_COMMAND = 'uv run --script "${CLAUDE_PROJECT_DIR}/.claude/hooks/guard.py"'
SHARED_COMMAND = 'uv run --script "{}/.agents/hooks/guard.py"'.format(TOPLEVEL)


class TestHookHelpers(RepoCase):
    def test_script_tokens_strip_every_root_prefix(self):
        self.assertEqual(inv.hook_script_tokens(CLAUDE_COMMAND), [".claude/hooks/guard.py"])
        self.assertEqual(inv.hook_script_tokens(SHARED_COMMAND), [".agents/hooks/guard.py"])
        self.assertEqual(inv.hook_script_tokens("node ./hooks/g.mjs"), ["hooks/g.mjs"])
        self.assertEqual(inv.hook_script_tokens("python3 $CLAUDE_PROJECT_DIR/h/g.py"), ["h/g.py"])

    def test_script_tokens_deduplicate_and_ignore_plain_words(self):
        self.assertEqual(inv.hook_script_tokens("sh a.sh && sh a.sh"), ["a.sh"])
        self.assertEqual(inv.hook_script_tokens("npx prettier --write"), [])

    def test_root_form(self):
        self.assertEqual(inv.hook_root_form(SHARED_COMMAND), "toplevel")
        self.assertEqual(inv.hook_root_form(CLAUDE_COMMAND), "claude-env")
        self.assertEqual(inv.hook_root_form("python3 .claude/hooks/g.py"), "relative")
        self.assertEqual(inv.hook_root_form("python3 /opt/hooks/g.py"), "absolute")
        self.assertEqual(inv.hook_root_form("echo hello"), "unknown")

    def test_script_location(self):
        self.assertEqual(inv.hook_script_location(".claude/hooks/g.py"), "legacy")
        self.assertEqual(inv.hook_script_location(".agents/hooks/g.py"), "shared")
        self.assertEqual(inv.hook_script_location("scripts/g.py"), "other")

    def test_load_json_object(self):
        path = write(self.root / "a.json", '{"hooks": {}}')
        self.assertEqual(inv.load_json_object(path), ({"hooks": {}}, ""))
        bad = write(self.root / "b.json", "{oops")
        self.assertIsNone(inv.load_json_object(bad)[0])
        self.assertTrue(inv.load_json_object(bad)[1])
        array = write(self.root / "c.json", "[]")
        self.assertIn("expected an object", inv.load_json_object(array)[1])
        data, error = inv.load_json_object(self.root)
        self.assertIsNone(data)
        self.assertTrue(error)

    def test_hooks_of(self):
        self.assertEqual(inv.hooks_of(None), {})
        self.assertEqual(inv.hooks_of({}), {})
        self.assertEqual(inv.hooks_of({"hooks": []}), {})
        self.assertEqual(inv.hooks_of({"hooks": {"Stop": []}}), {"Stop": []})

    def test_shareable_hooks_keeps_the_common_events_only(self):
        hooks = {
            "PreToolUse": [hook_entry(SHARED_COMMAND, "Edit|Write|Bash", timeout=10, async_=1)],
            "Notification": [hook_entry("say done", "")],
        }
        out = inv.shareable_hooks(hooks)
        self.assertEqual(list(out), ["PreToolUse"])
        self.assertEqual(out["PreToolUse"][0]["matcher"], "Edit|Write|Bash")
        self.assertEqual(out["PreToolUse"][0]["hooks"][0]["timeout"], 10)
        self.assertNotIn("async_", out["PreToolUse"][0]["hooks"][0])

    def test_shareable_hooks_drops_unusable_fragments(self):
        hooks = {
            "Stop": "not-a-list",
            "PreCompact": ["not-a-dict", {"hooks": "x"}, {"hooks": [{"type": "prompt"}]},
                           {"hooks": [{"type": "command", "command": "  "}]},
                           {"hooks": [{"type": "command", "command": "sh a.sh"}]}],
        }
        out = inv.shareable_hooks(hooks)
        self.assertEqual(list(out), ["PreCompact"])
        self.assertEqual(len(out["PreCompact"]), 1)
        self.assertNotIn("matcher", out["PreCompact"][0])

    def test_shareable_hooks_keeps_async_flag(self):
        out = inv.shareable_hooks({"Stop": [hook_entry("sh a.sh", "", **{"async": True})]})
        self.assertTrue(out["Stop"][0]["hooks"][0]["async"])

    def test_shareable_hooks_keeps_current_codex_fields(self):
        out = inv.shareable_hooks({"Stop": [hook_entry(
            "sh a.sh", "", statusMessage="checking", additionalContextLimit=512,
            commandWindows={"windows": "sh a.sh"})]})
        hook = out["Stop"][0]["hooks"][0]
        self.assertEqual(hook["statusMessage"], "checking")
        self.assertEqual(hook["additionalContextLimit"], 512)
        self.assertEqual(hook["commandWindows"], {"windows": "sh a.sh"})

    def test_host_specific_script_heuristic(self):
        self.assertTrue(inv.host_specific_script('payload["tool_input"]["file_path"]'))
        self.assertTrue(inv.host_specific_script("os.environ['CLAUDE_PROJECT_DIR']"))
        self.assertFalse(inv.host_specific_script('if name == "apply_patch": file_path'))
        self.assertFalse(inv.host_specific_script("print('hi')"))
        # Adapted scripts keep the old names as identifiers or comments; not flagged.
        self.assertFalse(inv.host_specific_script(
            "from hook_payload import load_event\ndef _check_write(file_path: str): ..."))
        self.assertFalse(inv.host_specific_script(
            "from hook_payload import project_root\n# CLAUDE_PROJECT_DIR is host-only"))
        self.assertFalse(inv.host_specific_script("file_path = str(path)  # local name"))
        self.assertTrue(inv.host_specific_script('tool_input.get("file_path", "")'))

    def test_dump_json_is_indented_with_a_trailing_newline(self):
        self.assertEqual(inv.dump_json({"a": 1}), '{\n  "a": 1\n}\n')


class TestHooksInventory(RepoCase):
    def analyze(self):
        return inv.analyze_hooks(self.root)

    def codes(self, findings):
        return sorted({f.code for f in findings})

    def test_no_hooks_at_all(self):
        info, findings = self.analyze()
        self.assertEqual(info.state, "none")
        self.assertEqual(findings, [])
        self.assertEqual(info.events, {})

    def test_claude_only_template(self):
        write(self.root / ".claude/hooks/guard.py", "x\n")
        write(self.root / ".claude/settings.json",
              settings_json({"PreToolUse": [hook_entry(CLAUDE_COMMAND, "Edit|Write|Bash")],
                             "Notification": [hook_entry("say done", "")]},
                            permissions={"allow": []}))
        info, findings = self.analyze()
        self.assertEqual(info.state, "claude-only")
        self.assertEqual(info.claude_settings, ".claude/settings.json")
        self.assertIsNone(info.codex_hooks)
        self.assertEqual(info.legacy_dir, ".claude/hooks")
        self.assertIsNone(info.shared_dir)
        self.assertEqual(info.events["PreToolUse"],
                         {"claude": True, "codex": False, "shareable": True})
        self.assertEqual(info.events["Notification"]["shareable"], False)
        self.assertEqual([s.path for s in info.scripts], [".claude/hooks/guard.py"])
        self.assertEqual(info.scripts[0].wired_by, ["claude"])
        self.assertEqual(info.scripts[0].location, "legacy")
        self.assertEqual(info.commands[0].root_form, "claude-env")
        self.assertEqual(info.commands[0].matcher, "Edit|Write|Bash")
        self.assertEqual(self.codes(findings), ["H001", "H002", "H003", "H006"])

    def test_shared_state_is_clean(self):
        write(self.root / ".agents/hooks/guard.py", "apply_patch file_path\n")
        write(self.root / ".claude/settings.json",
              settings_json({"PreToolUse": [hook_entry(SHARED_COMMAND)]}))
        write(self.root / ".codex/hooks.json",
              settings_json({"PreToolUse": [hook_entry(SHARED_COMMAND)]}))
        info, findings = self.analyze()
        self.assertEqual(info.state, "shared")
        self.assertEqual(info.shared_dir, ".agents/hooks")
        self.assertEqual(info.scripts[0].wired_by, ["claude", "codex"])
        self.assertEqual(findings, [])

    def test_codex_only_command_does_not_make_shared_projection_drift(self):
        write(self.root / ".agents/hooks/guard.py", "apply_patch\n")
        write(self.root / ".claude/settings.json",
              settings_json({"Stop": [hook_entry(SHARED_COMMAND, "")]}))
        write(self.root / ".codex/hooks.json",
              settings_json({"Stop": [
                  hook_entry(SHARED_COMMAND.replace("guard.py", "codex-only.py"), ""),
                  hook_entry(SHARED_COMMAND, ""),
              ]}))
        info, findings = self.analyze()
        self.assertEqual(info.state, "shared")
        self.assertEqual(findings, [])

    def test_inline_codex_hooks_are_reported_without_being_loaded_or_rewritten(self):
        write(self.root / ".codex/config.toml", "[hooks]\n")
        info, findings = self.analyze()
        self.assertEqual(info.codex_config, ".codex/config.toml")
        self.assertEqual([finding.code for finding in findings], ["H009"])

    def test_drift_between_the_two_configs(self):
        write(self.root / ".agents/hooks/guard.py", "apply_patch\n")
        write(self.root / ".claude/settings.json",
              settings_json({"PreToolUse": [hook_entry(SHARED_COMMAND)],
                             "Stop": [hook_entry(SHARED_COMMAND, "")]}))
        write(self.root / ".codex/hooks.json",
              settings_json({"PreToolUse": [hook_entry(SHARED_COMMAND)]}))
        info, findings = self.analyze()
        self.assertEqual(info.state, "drift")
        h004 = [f for f in findings if f.code == "H004"]
        self.assertEqual(len(h004), 1)
        self.assertIn("Stop", h004[0].message)

    def test_codex_only_wiring(self):
        write(self.root / ".codex/hooks.json",
              settings_json({"Stop": [hook_entry(SHARED_COMMAND, "")]}))
        info, findings = self.analyze()
        self.assertEqual(info.state, "drift")
        self.assertEqual(self.codes(findings), ["H005"])
        self.assertEqual(info.scripts[0].wired_by, ["codex"])

    def test_shared_directory_without_any_wiring(self):
        write(self.root / ".agents/hooks/guard.py", "x\n")
        info, findings = self.analyze()
        self.assertEqual(info.state, "claude-only")
        self.assertEqual(findings, [])

    def test_host_specific_shared_script_is_info_only(self):
        write(self.root / ".agents/hooks/guard.py", 'payload["tool_input"]["file_path"]\n')
        write(self.root / ".agents/hooks/notes.md", "file_path\n")
        write(self.root / ".claude/settings.json",
              settings_json({"PreToolUse": [hook_entry(SHARED_COMMAND)]}))
        write(self.root / ".codex/hooks.json",
              settings_json({"PreToolUse": [hook_entry(SHARED_COMMAND)]}))
        info, findings = self.analyze()
        self.assertEqual([(f.code, f.severity, f.path) for f in findings],
                         [("H007", "info", ".agents/hooks/guard.py")])
        self.assertEqual(info.state, "shared")

    def test_invalid_json_on_both_sides(self):
        write(self.root / ".claude/settings.json", "{oops")
        write(self.root / ".codex/hooks.json", "{oops")
        info, findings = self.analyze()
        h008 = [f for f in findings if f.code == "H008"]
        self.assertEqual([f.path for f in h008], [".claude/settings.json", ".codex/hooks.json"])
        self.assertEqual(h008[0].severity, "error")
        self.assertEqual(info.state, "drift")

    def test_relative_command_is_flagged(self):
        write(self.root / ".claude/settings.json",
              settings_json({"Stop": [hook_entry("python3 .claude/hooks/guard.py", "")]}))
        _, findings = self.analyze()
        self.assertIn("H006", self.codes(findings))

    def test_absolute_command_is_not_flagged_as_host_only(self):
        write(self.root / ".agents/hooks/guard.py", "apply_patch\n")
        write(self.root / ".claude/settings.json",
              settings_json({"Stop": [hook_entry("python3 /opt/g.py", "")]}))
        write(self.root / ".codex/hooks.json",
              settings_json({"Stop": [hook_entry("python3 /opt/g.py", "")]}))
        info, findings = self.analyze()
        self.assertEqual(info.commands[0].root_form, "absolute")
        self.assertEqual(self.codes(findings), ["H002"])

    def test_personal_settings_file_is_never_read(self):
        write(self.root / ".claude/settings.local.json", "{oops")
        info, findings = self.analyze()
        self.assertEqual(info.state, "none")
        self.assertEqual(findings, [])

    def test_suggested_mode_hooks(self):
        write(self.root / "AGENTS.md", "# Root\n")
        write(self.root / "CLAUDE.md", STUB)
        write(self.root / ".claude/hooks/guard.py", "x\n")
        write(self.root / ".claude/settings.json",
              settings_json({"PreToolUse": [hook_entry(CLAUDE_COMMAND)]}))
        result = inv.build_inventory(self.root)
        self.assertEqual(result.suggested_mode, "hooks")
        self.assertEqual(result.hooks.state, "claude-only")
        self.assertTrue(inv.has_blocking_findings(result))

    def test_migrate_wins_over_hooks(self):
        write(self.root / "AGENTS.md", "# Root\n")
        write(self.root / "CLAUDE.md", LEGACY_BODY)
        write(self.root / ".claude/hooks/guard.py", "x\n")
        self.assertEqual(inv.build_inventory(self.root).suggested_mode, "migrate")

    def test_info_only_hook_findings_do_not_change_the_mode(self):
        write(self.root / "AGENTS.md", "# Root\n")
        write(self.root / "CLAUDE.md", STUB)
        write(self.root / ".agents/hooks/guard.py", 'payload["file_path"]\n')
        write(self.root / ".claude/settings.json",
              settings_json({"PreToolUse": [hook_entry(SHARED_COMMAND)]}))
        write(self.root / ".codex/hooks.json",
              settings_json({"PreToolUse": [hook_entry(SHARED_COMMAND)]}))
        result = inv.build_inventory(self.root)
        self.assertEqual(result.suggested_mode, "audit")
        self.assertFalse(inv.has_blocking_findings(result))

    def test_json_and_text_output_carry_the_hooks_block(self):
        write(self.root / "AGENTS.md", "# Root\n")
        write(self.root / "CLAUDE.md", STUB)
        write(self.root / ".claude/hooks/guard.py", "x\n")
        write(self.root / ".claude/settings.json",
              settings_json({"PreToolUse": [hook_entry(CLAUDE_COMMAND)]}))
        code, out, _ = run_main([str(self.root), "--json"])
        self.assertEqual(code, 1)
        hooks = json.loads(out)["hooks"]
        self.assertEqual(hooks["state"], "claude-only")
        self.assertEqual(hooks["claude_settings"], ".claude/settings.json")
        self.assertIsNone(hooks["codex_hooks"])
        self.assertEqual(hooks["legacy_dir"], ".claude/hooks")
        self.assertEqual(hooks["events"]["PreToolUse"]["shareable"], True)
        self.assertEqual(hooks["scripts"][0]["location"], "legacy")
        self.assertEqual(hooks["commands"][0]["root_form"], "claude-env")

        _, text, _ = run_main([str(self.root)])
        self.assertIn("hooks: claude-only", text)
        self.assertIn("script dirs: .claude/hooks / -", text)
        self.assertIn("PreToolUse — claude=True codex=False shareable=True", text)
        self.assertIn(".claude/hooks/guard.py — legacy, wired by claude", text)
        self.assertIn("suggested mode: hooks", text)

    def test_text_output_hides_the_hooks_block_when_there_are_none(self):
        write(self.root / "AGENTS.md", "# Root\n")
        write(self.root / "CLAUDE.md", STUB)
        _, text, _ = run_main([str(self.root)])
        self.assertNotIn("hooks:", text)


if __name__ == "__main__":
    unittest.main()
