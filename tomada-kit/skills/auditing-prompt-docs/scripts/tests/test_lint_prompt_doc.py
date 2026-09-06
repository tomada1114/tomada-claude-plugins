"""Tests for lint_prompt_doc.py."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lint_prompt_doc as lint  # noqa: E402


def findings_for(text: str, kind: str = "memory") -> list[lint.Finding]:
    return lint.lint_text(text, "doc.md", kind)


def rules_in(text: str, kind: str = "memory") -> set[str]:
    return {f.rule for f in findings_for(text, kind)}


class ClassifyTests(unittest.TestCase):
    def test_known_filenames(self):
        self.assertEqual(lint.classify(Path("a/SKILL.md")), "skill")
        self.assertEqual(lint.classify(Path("a/CLAUDE.md")), "memory")
        self.assertEqual(lint.classify(Path("a/AGENTS.md")), "memory")

    def test_directory_based(self):
        self.assertEqual(lint.classify(Path("x/agents/reviewer.md")), "agent")
        self.assertEqual(lint.classify(Path("x/commands/ship.md")), "command")
        self.assertEqual(lint.classify(Path("x/references/rules.md")), "reference")
        self.assertEqual(lint.classify(Path("x/docs/notes.md")), "other")


class HelperTests(unittest.TestCase):
    def test_parse_ignores(self):
        got = lint.parse_ignores(
            "<!-- prompt-lint-ignore-file: p001, D002 -->", lint.IGNORE_FILE_RE
        )
        self.assertEqual(got, {"P001", "D002"})

    def test_strip_frontmatter(self):
        body, offset = lint.strip_frontmatter(["---", "name: x", "---", "body"])
        self.assertEqual(body, ["body"])
        self.assertEqual(offset, 4)

    def test_strip_frontmatter_absent(self):
        body, offset = lint.strip_frontmatter(["body"])
        self.assertEqual((body, offset), (["body"], 1))

    def test_strip_frontmatter_unterminated(self):
        body, offset = lint.strip_frontmatter(["---", "name: x"])
        self.assertEqual(offset, 1)
        self.assertEqual(len(body), 2)

    def test_normalize(self):
        self.assertEqual(lint.normalize("- **Never** do `x`."), "never do x")
        self.assertEqual(lint.normalize("1. Run the thing"), "run the thing")


class LineRuleTests(unittest.TestCase):
    def test_forced_verification(self):
        self.assertIn("P001", rules_in("Please double-check your answer."))
        self.assertIn("P001", rules_in("Add a final verification step for each task."))

    def test_severity_self_filtering(self):
        self.assertIn("P002", rules_in("Only report high-severity issues."))
        self.assertIn("P002", rules_in("Be conservative when reviewing."))
        self.assertIn("P002", rules_in("Skip minor issues in the report."))

    def test_reasoning_echo(self):
        self.assertIn("P003", rules_in("Show your reasoning before answering."))
        self.assertIn("P003", rules_in("Explain how you arrived at the number."))

    def test_emphasis_shouting(self):
        self.assertIn("P004", rules_in("CRITICAL: read the config first."))
        self.assertIn("P004", rules_in("You MUST call the tool."))

    def test_tool_overtrigger(self):
        self.assertIn("P005", rules_in("If in doubt, use the search tool."))
        self.assertIn("P005", rules_in("Default to using the repository index."))

    def test_recommended_when_in_doubt_phrasing_is_not_flagged(self):
        self.assertNotIn("P005", rules_in("When in doubt, respond directly."))

    def test_fixed_progress_scaffolding(self):
        self.assertIn("P006", rules_in("After every 3 tool calls, summarize progress."))

    def test_blanket_thoroughness(self):
        self.assertIn("P008", rules_in("Go above and beyond on every task."))

    def test_open_ended_delegation(self):
        self.assertIn("P009", rules_in("Use subagents whenever it seems useful."))

    def test_legacy_api(self):
        self.assertIn("P010", rules_in("Set budget_tokens to 10000."))
        self.assertIn("P010", rules_in("Use an assistant prefill to force JSON."))

    def test_sampling_params(self):
        self.assertIn("P011", rules_in("temperature: 0.7"))

    def test_negative_formatting_rule(self):
        self.assertIn("P012", rules_in("Do not use markdown in your response."))

    def test_narration_suppression(self):
        self.assertIn("P013", rules_in("Hold all findings for the final response."))
        self.assertIn("P013", rules_in("No running commentary while you work."))

    def test_clean_document_has_no_line_findings(self):
        text = "# Guide\n\nUse the search tool when it clarifies the problem.\n"
        self.assertEqual(rules_in(text), set())


class MetricRuleTests(unittest.TestCase):
    def test_negative_density(self):
        text = "\n".join(f"- Do not do thing number {i}." for i in range(20))
        self.assertIn("P007", rules_in(text))

    def test_negative_density_below_threshold(self):
        text = "\n".join(["- Do not do the one bad thing."] + ["Normal line."] * 40)
        self.assertNotIn("P007", rules_in(text))

    def test_size_budget_warn_and_error(self):
        warn_doc = "\n".join(["line"] * 250)
        error_doc = "\n".join(["line"] * 500)
        warn = [f for f in findings_for(warn_doc) if f.rule == "D001"]
        err = [f for f in findings_for(error_doc) if f.rule == "D001"]
        self.assertEqual(warn[0].severity, "warn")
        self.assertEqual(err[0].severity, "error")

    def test_size_budget_uses_kind(self):
        doc = "\n".join(["line"] * 180)
        self.assertNotIn("D001", rules_in(doc, "memory"))
        self.assertIn("D001", rules_in(doc, "command"))

    def test_unknown_kind_falls_back_to_other_budget(self):
        doc = "\n".join(["line"] * 450)
        self.assertIn("D001", rules_in(doc, "no-such-kind"))

    def test_duplicate_directive(self):
        line = "Preserve unrelated changes and never weaken the project gates."
        text = f"{line}\n\nSomething else entirely happens here.\n\n{line}\n"
        dupes = [f for f in findings_for(text) if f.rule == "D002"]
        self.assertEqual(len(dupes), 1)

    def test_duplicate_headings_and_short_lines_ignored(self):
        text = "## Setup\n\nRun it.\n\n## Setup\n\nRun it.\n"
        self.assertNotIn("D002", rules_in(text))


class SuppressionTests(unittest.TestCase):
    def test_file_level_ignore(self):
        text = "<!-- prompt-lint-ignore-file: P002 -->\nOnly report high-severity issues.\n"
        self.assertNotIn("P002", rules_in(text))

    def test_file_level_ignore_all(self):
        text = "<!-- prompt-lint-ignore-file: all -->\nYou MUST double-check your work.\n"
        self.assertEqual(rules_in(text), set())

    def test_inline_ignore_same_line(self):
        text = "Be conservative. <!-- prompt-lint-ignore: P002 -->\n"
        self.assertNotIn("P002", rules_in(text))

    def test_inline_ignore_preceding_line(self):
        text = "<!-- prompt-lint-ignore: P004 -->\nCRITICAL: do the thing.\n"
        self.assertNotIn("P004", rules_in(text))

    def test_metric_rules_respect_file_ignore(self):
        text = "<!-- prompt-lint-ignore-file: D001,P007,D002 -->\n" + "\n".join(
            ["Do not do the thing repeatedly here."] * 300
        )
        self.assertEqual(rules_in(text), set())


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, rel: str, text: str = "Be conservative.\n") -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def test_discovers_supported_documents(self):
        self.write("CLAUDE.md")
        self.write("skills/a/SKILL.md")
        self.write("agents/reviewer.md")
        self.write("commands/ship.md")
        self.write("skills/a/references/rules.md")
        self.write("docs/readme.md")
        self.write("node_modules/pkg/AGENTS.md")
        found = {p.name for p in lint.discover([self.root])}
        self.assertEqual(
            found, {"CLAUDE.md", "SKILL.md", "reviewer.md", "ship.md", "rules.md"}
        )

    def test_explicit_file_is_always_scanned(self):
        p = self.write("docs/readme.md")
        self.assertEqual(lint.discover([p]), [p])


class RenderTests(unittest.TestCase):
    def test_render_empty(self):
        self.assertIn("No findings", lint.render([], [Path("a.md")]))

    def test_render_lists_findings(self):
        out = lint.render(findings_for("Be conservative."), [Path("doc.md")])
        self.assertIn("P002", out)
        self.assertIn("1 finding(s)", out)


class MainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = lint.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_clean_document_exits_zero(self):
        p = self.root / "CLAUDE.md"
        p.write_text("Use the search tool when it clarifies the problem.\n", encoding="utf-8")
        code, out, _ = self.run_main([str(p)])
        self.assertEqual(code, 0)
        self.assertIn("No findings", out)

    def test_findings_exit_one_with_json(self):
        p = self.root / "CLAUDE.md"
        p.write_text("Only report high-severity issues.\n", encoding="utf-8")
        code, out, _ = self.run_main([str(p), "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertEqual(payload["findings"][0]["rule"], "P002")
        self.assertEqual(payload["summary"]["error"], 1)

    def test_ignore_flag(self):
        p = self.root / "CLAUDE.md"
        p.write_text("Only report high-severity issues.\n", encoding="utf-8")
        code, _, _ = self.run_main([str(p), "--ignore", "p002"])
        self.assertEqual(code, 0)

    def test_min_severity_filter(self):
        p = self.root / "CLAUDE.md"
        p.write_text("Go above and beyond on every task.\n", encoding="utf-8")
        self.assertEqual(self.run_main([str(p)])[0], 1)
        self.assertEqual(self.run_main([str(p), "--min-severity", "warn"])[0], 0)

    def test_missing_path_exits_two(self):
        code, _, err = self.run_main([str(self.root / "nope.md")])
        self.assertEqual(code, 2)
        self.assertIn("Path not found", err)

    def test_no_documents_exits_two(self):
        (self.root / "docs").mkdir()
        code, _, err = self.run_main([str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn("No prompt documents found", err)

    def test_non_utf8_file_is_skipped(self):
        p = self.root / "CLAUDE.md"
        p.write_bytes(b"\xff\xfe\x00bad")
        code, _, err = self.run_main([str(p)])
        self.assertEqual(code, 0)
        self.assertIn("not UTF-8", err)

    def test_list_rules_text_and_json(self):
        code, out, _ = self.run_main(["--list-rules", "x"])
        self.assertEqual(code, 0)
        self.assertIn("P001", out)
        code, out, _ = self.run_main(["--list-rules", "--json", "x"])
        self.assertEqual(code, 0)
        ids = [r["rule"] for r in json.loads(out)["rules"]]
        self.assertIn("D002", ids)
        self.assertEqual(ids, sorted(ids))


if __name__ == "__main__":
    unittest.main()
