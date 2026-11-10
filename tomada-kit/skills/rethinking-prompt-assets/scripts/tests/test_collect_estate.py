"""Tests for collect_estate.py. Run from the skill directory:

    python3 -m unittest discover -s scripts/tests -p 'test_*.py'
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import collect_estate as ce  # noqa: E402

SKILL_ALPHA = """---
name: alpha
description: >-
  Does the alpha job.
  Use when alpha is needed.
when_to_use: "alpha things"
metadata:
  platforms: claude-code, codex   # both hosts
allowed-tools:
---

# Alpha

Hand the survey to a `scout` sub-agent, then use the beta skill.
"""

SKILL_BETA = """---
name: beta
description: 'Beta job'
disable-model-invocation: true
user-invocable: false
---

# Beta

Runs on Opus at high effort.
"""


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def entry(kind: str, content: object, stamp: str = "2026-01-02T00:00:00Z", **extra: object) -> str:
    return json.dumps({"type": kind, "timestamp": stamp, "message": {"content": content}, **extra})


def skill_call(name: str, **extra: object) -> str:
    block = {"type": "tool_use", "name": "Skill", "input": {"skill": name}}
    return entry("assistant", [block], **extra)


def command(name: str, stamp: str = "2026-01-03T00:00:00Z") -> str:
    return entry("user", f"<command-message>{name}</command-message>\n<command-name>/{name}</command-name>", stamp)


class EstateFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.root = self.base / "home"
        write(self.root / "skills/alpha/SKILL.md", SKILL_ALPHA)
        write(self.root / "skills/alpha/references/notes.md", "See gamma for details.\nmodel: sonnet\n")
        (self.root / "skills/alpha/scripts").mkdir()
        write(self.root / "skills/beta/SKILL.md", SKILL_BETA)
        write(self.root / "skills/gamma/SKILL.md", "# Gamma\n\nNo frontmatter here.\n")
        write(self.root / "skills/delta/SKILL.md", "---\nname: delta\ndescription: unterminated\n")
        write(self.root / "skills/stray/README.md", "not a skill\n")
        write(self.root / "skills/.hidden/SKILL.md", "---\nname: hidden\n---\n")
        write(self.root / "skills/loose-file.md", "ignored\n")
        (self.root / "skills/dangling").symlink_to(self.base / "missing-target")
        write(self.root / "agents/scout.md", "---\nname: scout\nmodel: claude-haiku\neffort: xhigh\n---\nBody\n")
        write(self.root / "agents/plain.md", "No frontmatter\n")
        write(self.root / "commands/other-cmd.md", "Do the other thing.\n")
        write(self.root / "CLAUDE.md", "Use the beta skill.\nMain runs on Fable.\n")
        self.extra_memory = write(self.base / "repo/AGENTS.md", "Prefer alpha.\n")
        self.transcripts = self.base / "transcripts"
        write(self.transcripts / "proj-a/s1.jsonl", "\n".join([
            command("alpha"),
            skill_call("alpha", stamp="2026-01-05T00:00:00Z"),
            skill_call("/beta", isSidechain=True),
            skill_call("plugin:other"),
            entry("user", [{"type": "text", "text": "<command-name>/other-cmd</command-name>"}, "bare"]),
            entry("user", [{"type": "tool_result", "content": "<command-name>/alpha</command-name>"}]),
            entry("assistant", [{"type": "tool_use", "name": "Skill", "input": {}}]),
            '{"broken json <command-name>',
            json.dumps(["<command-name>/alpha</command-name>"]),
            json.dumps({"type": "user", "note": "<command-name>/alpha</command-name>"}),
            entry("user", "plain text with no command"),
            json.dumps({"type": "user", "message": {"content": "<command-name>/alpha</command-name>"}}),
        ]) + "\n")
        write(self.transcripts / "proj-a/s1/subagents/a1.jsonl", skill_call("alpha") + "\n")
        write(self.transcripts / "x-scratchpad-y/s2.jsonl", "\n".join([
            skill_call("alpha"), skill_call("unknown-in-scratch"),
        ]) + "\n")

    def collect(self, **kwargs: object) -> ce.Estate:
        return ce.collect(self.root, **kwargs)

    def skill(self, estate: ce.Estate, name: str) -> ce.Skill:
        return next(s for s in estate.skills if s.name == name)


class FrontmatterTests(unittest.TestCase):
    def test_scalars_blocks_and_nesting(self) -> None:
        meta, body = ce.parse_frontmatter(SKILL_ALPHA)
        self.assertEqual(meta["description"], "Does the alpha job. Use when alpha is needed.")
        self.assertEqual(meta["when_to_use"], "alpha things")
        self.assertEqual(meta["metadata"], {"platforms": "claude-code, codex"})
        self.assertEqual(meta["allowed-tools"], {})
        self.assertIn("# Alpha", body)

    def test_block_scalar_as_last_key(self) -> None:
        meta, _ = ce.parse_frontmatter("---\nname: x\ndescription: |\n  one\n\n  two\n---\nbody\n")
        self.assertEqual(meta["description"], "one two")

    def test_missing_or_unterminated(self) -> None:
        self.assertEqual(ce.parse_frontmatter("# Title\n"), ({}, "# Title\n"))
        self.assertEqual(ce.parse_frontmatter("")[0], {})
        self.assertEqual(ce.parse_frontmatter("---\nname: x\n")[0], {})

    def test_stray_indented_line_is_ignored(self) -> None:
        meta, _ = ce.parse_frontmatter("---\n  orphan: 1\nname: x\n  trailing\n---\n")
        self.assertEqual(meta, {"name": "x"})


class InventoryTests(EstateFixture):
    def test_skills_and_strays(self) -> None:
        estate = self.collect()
        self.assertEqual([s.name for s in estate.skills], ["alpha", "beta", "delta", "gamma"])
        self.assertEqual(estate.non_skill_dirs, ["dangling", "stray"])
        alpha = self.skill(estate, "alpha")
        self.assertTrue(alpha.has_description and alpha.has_scripts)
        self.assertEqual(alpha.platforms, "claude-code, codex")
        self.assertEqual((alpha.reference_files, alpha.reference_lines), (1, 2))
        self.assertEqual(alpha.description_chars, len("Does the alpha job. Use when alpha is needed.") + len("alpha things"))
        beta = self.skill(estate, "beta")
        self.assertTrue(beta.user_only and beta.model_only)
        self.assertFalse(self.skill(estate, "gamma").has_description)

    def test_reference_graph(self) -> None:
        estate = self.collect(memory=[self.extra_memory, self.base / "absent.md"])
        alpha = self.skill(estate, "alpha")
        self.assertEqual(alpha.mentions, ["beta", "gamma"])
        self.assertEqual(alpha.mentioned_by, [str(self.extra_memory)])
        self.assertEqual(self.skill(estate, "beta").mentioned_by, ["alpha", "CLAUDE.md"])
        self.assertEqual([m.lines for m in estate.memory_files], [2, 1])
        self.assertEqual(estate.memory_files[0].mentions, ["beta"])
        self.assertEqual(estate.memory_files[0].model_mention_count, 1)

    def test_tier_and_model_mentions(self) -> None:
        estate = self.collect()
        alpha = self.skill(estate, "alpha")
        self.assertEqual([(m.file, m.line) for m in alpha.tier_mentions], [("SKILL.md", 14)])
        self.assertEqual([(m.file, m.line) for m in alpha.model_mentions], [("references/notes.md", 2)])
        self.assertEqual(self.skill(estate, "beta").model_mention_count, 1)

    def test_model_mention_sample_is_capped(self) -> None:
        write(self.root / "skills/alpha/references/many.md", "opus\n" * (ce.MODEL_MENTION_SAMPLE + 5))
        write(self.root / "skills/alpha/references/zzz.md", "sonnet\n")
        alpha = self.skill(self.collect(), "alpha")
        self.assertEqual(len(alpha.model_mentions), ce.MODEL_MENTION_SAMPLE)
        self.assertEqual(alpha.model_mention_count, ce.MODEL_MENTION_SAMPLE + 7)

    def test_agents(self) -> None:
        agents = {a.name: a for a in self.collect().agents}
        self.assertEqual((agents["scout"].model, agents["scout"].effort), ("claude-haiku", "xhigh"))
        self.assertEqual(agents["plain"].model, "")

    def test_root_without_skills_or_agents(self) -> None:
        bare = self.base / "bare"
        write(bare / "AGENTS.md", "hello\n")
        estate = ce.collect(bare)
        self.assertEqual((estate.skills, estate.agents, len(estate.memory_files)), ([], [], 1))
        self.assertEqual(estate.commands, [])


class UsageTests(EstateFixture):
    def test_counts_by_kind_and_scratch(self) -> None:
        estate = self.collect(transcripts=self.transcripts)
        alpha = self.skill(estate, "alpha").usage
        self.assertEqual((alpha.user, alpha.model, alpha.sidechain, alpha.scratch), (2, 1, 1, 1))
        self.assertEqual(alpha.projects, ["proj-a"])
        self.assertEqual(alpha.last_used, "2026-01-05T00:00:00Z")
        beta = self.skill(estate, "beta").usage
        self.assertEqual((beta.user, beta.model, beta.sidechain), (0, 0, 1))
        self.assertEqual(estate.usage_window.files, 3)
        self.assertEqual(estate.usage_window.first, "2026-01-02T00:00:00Z")
        self.assertEqual(estate.usage_window.last, "2026-01-05T00:00:00Z")
        self.assertEqual(estate.unknown_invocations, [{"name": "plugin:other", "count": 1}])
        self.assertEqual([(c.name, c.lines, c.usage.user) for c in estate.commands], [("other-cmd", 1, 1)])

    def test_custom_scratch_pattern(self) -> None:
        estate = self.collect(transcripts=self.transcripts, scratch_pattern="^proj-a$")
        alpha = self.skill(estate, "alpha").usage
        self.assertEqual((alpha.user, alpha.model, alpha.scratch), (0, 1, 4))

    def test_quoted_command_deep_in_text_is_not_an_invocation(self) -> None:
        raw = entry("user", "x" * 500 + "<command-name>/alpha</command-name>").encode()
        self.assertEqual(ce.invocations_in_line(raw), [])

    def test_signals(self) -> None:
        signals = self.collect(transcripts=self.transcripts).signals
        self.assertEqual(signals["no_description"], ["delta", "gamma"])
        self.assertEqual(signals["user_only"], ["beta"])
        self.assertEqual(signals["no_evidence_of_use"], ["delta"])
        self.assertEqual(signals["reached_only_through_other_assets"], ["gamma"])
        self.assertEqual(signals["never_model_invoked"], [])
        self.assertEqual(signals["names_models_but_no_tier"], ["beta"])
        self.assertEqual(signals["delegates"], ["alpha"])

    def test_never_model_invoked(self) -> None:
        write(self.transcripts / "proj-b/s.jsonl", command("delta") + "\n")
        signals = self.collect(transcripts=self.transcripts).signals
        self.assertEqual(signals["never_model_invoked"], ["delta"])

    def test_signals_without_scan_claim_nothing_about_use(self) -> None:
        signals = self.collect().signals
        self.assertEqual(signals["no_evidence_of_use"], [])
        self.assertEqual(signals["reached_only_through_other_assets"], [])


class CliTests(EstateFixture):
    def run_main(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ce.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_json(self) -> None:
        code, out, _ = self.run_main(
            str(self.root), "--json", "--transcripts", str(self.transcripts),
            "--memory", str(self.extra_memory),
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["listing"]["skills"], 4)
        self.assertEqual(data["listing"]["longest_descriptions"][0]["name"], "alpha")
        self.assertTrue(data["usage_window"]["scanned"])
        self.assertEqual(len(data["memory_files"]), 2)

    def test_text_with_and_without_usage(self) -> None:
        code, out, _ = self.run_main(str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("usage: not scanned", out)
        self.assertIn("no_description: delta, gamma", out)
        self.assertIn("never_model_invoked: -", out)
        code, out, _ = self.run_main(str(self.root), "--transcripts", str(self.transcripts))
        self.assertEqual(code, 0)
        self.assertIn("usage window: 2026-01-02T00:00:00Z .. 2026-01-05T00:00:00Z (3 transcripts)", out)
        self.assertTrue(re.search(r"^alpha\s+2\s+1\s+1\s+0\s+2\s+\d+$", out, re.MULTILINE))

    def test_bad_invocations(self) -> None:
        empty = self.base / "empty"
        empty.mkdir()
        code, _, err = self.run_main(str(empty))
        self.assertEqual(code, 2)
        self.assertIn("holds no skills/", err)
        code, _, err = self.run_main(str(self.root), "--transcripts", str(self.base / "nope"))
        self.assertEqual(code, 2)
        self.assertIn("is not a directory", err)
        code, _, err = self.run_main(str(self.root), "--scratch-pattern", "(")
        self.assertEqual(code, 2)
        self.assertIn("not a valid regex", err)


if __name__ == "__main__":
    unittest.main()
