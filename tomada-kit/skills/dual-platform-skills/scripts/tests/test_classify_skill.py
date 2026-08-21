#!/usr/bin/env python3
"""Tests for classify_skill.py. Stdlib-only (unittest).

Run: python3 -m unittest scripts.tests.test_classify_skill -v
     (from the dual-platform-skills skill directory)
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

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

    def test_main_help_returns_2(self):
        self.assertEqual(cs.main(["classify_skill.py", "--help"]), 2)

    def test_main_no_args_returns_2(self):
        self.assertEqual(cs.main(["classify_skill.py"]), 2)

    def test_main_json_output_has_tier(self):
        skill = write_skill(self.root)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cs.main(["classify_skill.py", str(skill), "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("tier", data)


class TestMissingSkillMd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_classify_notes_missing_skill_md(self):
        empty_dir = self.root / "no-skill-md"
        empty_dir.mkdir()
        c = cs.classify(empty_dir)
        self.assertIn("SKILL.md not found", c.notes)
        self.assertEqual(c.tier, "A")


class TestFrontmatterParsingEdgeCase(unittest.TestCase):
    def test_no_frontmatter_returns_empty(self):
        keys, name, body_start = cs.parse_frontmatter_keys("no frontmatter\njust body text\n")
        self.assertEqual((keys, name, body_start), ([], "", 0))


class TestAgentRegistryAndDependents(unittest.TestCase):
    """agent_registry()/skill_registry() read Path.home(); patch it to a tmpdir
    so results don't depend on the real user's ~/.claude contents."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fake_home = self.root / "fake-home"
        (self.fake_home / ".claude").mkdir(parents=True)
        patcher = patch.object(Path, "home", return_value=self.fake_home)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_skill_local_agents_dir_is_registered(self):
        # <claude-root>/skills/<sibling>/agents/*.md is a registry source distinct
        # from <claude-root>/agents/ — exercises the skills_dir.iterdir() branch.
        claude_skills = self.fake_home / ".claude" / "skills"
        sibling_agents = claude_skills / "reviewer-skill" / "agents"
        sibling_agents.mkdir(parents=True)
        (sibling_agents / "codelens.md").write_text("---\nname: codelens\n---\nDoes review.\n")
        skill = write_skill(claude_skills, skill_md=FM + "\nDelegate to codelens for review.\n")
        c = cs.classify(skill)
        self.assertIn("codelens", c.dependent_subagents)

    def test_claude_agents_path_reference_is_dependent_subagent(self):
        skill = write_skill(
            self.root,
            skill_md=FM + "\nSee .claude/agents/planner.md for instructions.\n",
        )
        c = cs.classify(skill)
        self.assertIn("planner", c.dependent_subagents)

    def test_explicit_cross_skill_path_is_recorded(self):
        skill = write_skill(
            self.root,
            skill_md=FM + "\nSee .claude/skills/helper-skill/references/x.md for details.\n",
        )
        c = cs.classify(skill)
        self.assertIn("helper-skill", c.cross_skill_refs)


class TestBuiltinSlashCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_builtin_slash_command_positive_hits(self):
        skill = write_skill(
            self.root,
            skill_md=FM + "\nRun /code-review high --fix, then /security-review, "
                          "then /init, /simplify, /run, /loop 5m, /schedule create, "
                          "/compact, and /model opus.\n",
        )
        c = cs.classify(skill)
        hits = {loc["match"] for loc in c.construct_locations if loc["label"] == "builtin_slash_command"}
        self.assertEqual(
            hits,
            {"/code-review", "/security-review", "/init", "/simplify", "/run",
             "/loop", "/schedule", "/compact", "/model"},
        )

    def test_url_path_does_not_fire(self):
        skill = write_skill(self.root, skill_md=FM + "\nSee https://example.com/code-review for docs.\n")
        c = cs.classify(skill)
        self.assertNotIn("builtin_slash_command", c.constructs)

    def test_relative_paths_do_not_fire(self):
        skill = write_skill(self.root, skill_md=FM + "\nRelative path docs/foo or src/lib/x here.\n")
        c = cs.classify(skill)
        self.assertNotIn("builtin_slash_command", c.constructs)

    def test_date_does_not_fire(self):
        skill = write_skill(self.root, skill_md=FM + "\nThe date is 2026/08/21.\n")
        c = cs.classify(skill)
        self.assertNotIn("builtin_slash_command", c.constructs)

    def test_word_with_no_slash_does_not_fire(self):
        skill = write_skill(self.root, skill_md=FM + "\nThe word digital containing no slash.\n")
        c = cs.classify(skill)
        self.assertNotIn("builtin_slash_command", c.constructs)

    def test_multi_segment_path_does_not_fire(self):
        skill = write_skill(self.root, skill_md=FM + "\nOutput goes to /docs/foo or /model/output.\n")
        c = cs.classify(skill)
        self.assertNotIn("builtin_slash_command", c.constructs)

    def test_inline_code_command_fires(self):
        skill = write_skill(self.root, skill_md=FM + "\nInvoke `/code-review` before merging.\n")
        c = cs.classify(skill)
        hits = {loc["match"] for loc in c.construct_locations if loc["label"] == "builtin_slash_command"}
        self.assertEqual(hits, {"/code-review"})

    def test_bare_prose_command_fires(self):
        skill = write_skill(self.root, skill_md=FM + "\nRun /init to bootstrap.\n")
        c = cs.classify(skill)
        hits = {loc["match"] for loc in c.construct_locations if loc["label"] == "builtin_slash_command"}
        self.assertEqual(hits, {"/init"})

    def test_unknown_command_does_not_fire(self):
        skill = write_skill(self.root, skill_md=FM + "\nRun /deploy-staging when ready.\n")
        c = cs.classify(skill)
        self.assertNotIn("builtin_slash_command", c.constructs)

    def test_closing_tag_issue_does_not_fire(self):
        skill = write_skill(self.root, skill_md=FM + "\n<issue>Body text</issue>\n")
        c = cs.classify(skill)
        self.assertNotIn("builtin_slash_command", c.constructs)

    def test_closing_tag_context_does_not_fire(self):
        skill = write_skill(self.root, skill_md=FM + "\n<context>Body text</context>\n")
        c = cs.classify(skill)
        self.assertNotIn("builtin_slash_command", c.constructs)

    def test_backtick_slash_word_does_not_fire(self):
        skill = write_skill(
            self.root,
            skill_md=FM + "\nneither this context nor any sub-agent hand-rolls a "
                          "`sleep`/poll loop around `gh`.\n",
        )
        c = cs.classify(skill)
        self.assertNotIn("builtin_slash_command", c.constructs)

    def test_templated_path_segment_does_not_fire(self):
        skill = write_skill(
            self.root,
            skill_md=FM + "\n`${AGENT_SKILL_STATE_DIR}/shipping-issues/<owner>__<repo>/run.md`\n",
        )
        c = cs.classify(skill)
        self.assertNotIn("builtin_slash_command", c.constructs)

    def test_batch_stays_its_own_label(self):
        skill = write_skill(self.root, skill_md=FM + "\nUse /batch to run these in parallel.\n")
        c = cs.classify(skill)
        self.assertNotIn("builtin_slash_command", c.constructs)
        self.assertIn("batch_command", c.constructs)

    def test_tier_a_bumped_to_b_on_builtin_slash_command(self):
        skill = write_skill(self.root, skill_md=FM + "\nRun /init here.\n")
        c = cs.classify(skill)
        self.assertIn("builtin_slash_command", c.constructs)
        self.assertEqual(c.tier, "B")

    def test_notes_mention_degradation_mode(self):
        skill = write_skill(self.root, skill_md=FM + "\nRun /init here.\n")
        c = cs.classify(skill)
        self.assertTrue(any("degradation mode" in n for n in c.notes))
        self.assertTrue(any("builtin_slash_command" in n for n in c.notes))

    def test_construct_locations_report_file_and_line(self):
        skill = write_skill(self.root, skill_md=FM + "\nline one\nRun /init here.\n")
        c = cs.classify(skill)
        hits = [loc for loc in c.construct_locations if loc["label"] == "builtin_slash_command"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["file"], "SKILL.md")
        self.assertEqual(hits[0]["match"], "/init")


class TestSandboxWriteOp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_positive_hits_cover_git_pkg_manager_and_cache_paths(self):
        skill = write_skill(
            self.root,
            skill_md=FM + "\ngit fetch origin\n"
                          "git worktree add ../wt\n"
                          "git branch -D old-branch\n"
                          "gh pr merge 123 --delete-branch\n"
                          "uv sync\n"
                          "npm ci\n"
                          "pytest -q\n"
                          "cache lives at ~/.cache/uv\n"
                          "or $HOME/.cache/pip\n"
                          "or via XDG_CACHE_HOME\n",
        )
        c = cs.classify(skill)
        self.assertEqual(c.constructs.get("sandbox_write_op", 0), 11)
        matches = {loc["match"] for loc in c.construct_locations if loc["label"] == "sandbox_write_op"}
        self.assertIn("git fetch", matches)
        self.assertIn("git worktree add", matches)
        self.assertIn("git branch -D", matches)
        self.assertIn("--delete-branch", matches)
        self.assertIn("uv ", matches)
        self.assertIn("npm ci", matches)
        self.assertIn("pytest", matches)
        self.assertIn("~/.cache/", matches)
        self.assertIn("$HOME/.cache/", matches)
        self.assertIn("XDG_CACHE_HOME", matches)

    def test_read_only_git_worktree_list_does_not_fire(self):
        skill = write_skill(self.root, skill_md=FM + "\ngit worktree list\n")
        c = cs.classify(skill)
        self.assertNotIn("sandbox_write_op", c.constructs)

    def test_does_not_affect_tier(self):
        skill = write_skill(self.root, skill_md=FM + "\ngit fetch origin\n")
        c = cs.classify(skill)
        self.assertIn("sandbox_write_op", c.constructs)
        self.assertEqual(c.tier, "A")

    def test_notes_mention_sandbox_failure_and_recovery(self):
        skill = write_skill(self.root, skill_md=FM + "\ngit fetch origin\n")
        c = cs.classify(skill)
        note = next((n for n in c.notes if "sandbox_write_op" in n), None)
        self.assertIsNotNone(note)
        self.assertIn("Operation not permitted", note)
        self.assertIn("elevated execution path", note)
        self.assertIn("cache env var", note)


class TestRenderHumanFields(unittest.TestCase):
    def test_render_includes_frontmatter_cross_refs_and_notes(self):
        c = cs.Classification(
            skill_path="/tmp/x",
            skill_name="x",
            tier="C",
            claude_frontmatter_fields=["allowed-tools"],
            cross_skill_refs=["other-skill"],
            notes=["SKILL.md not found"],
        )
        out = cs.render_human(c)
        self.assertIn("Claude-only frontmatter: allowed-tools", out)
        self.assertIn("Cross-skill refs: other-skill", out)
        self.assertIn("Notes: SKILL.md not found", out)


if __name__ == "__main__":
    unittest.main()
