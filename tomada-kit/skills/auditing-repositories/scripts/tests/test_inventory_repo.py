"""Tests for inventory_repo.py."""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import inventory_repo as inv  # noqa: E402


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def make_repo(files: dict[str, str | bytes], commits: int = 1) -> Path:
    root = Path(tempfile.mkdtemp())
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    git(root, "remote", "add", "origin", "git@github.com:owner/sample.git")
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    for n in range(1, commits):
        (root / "src/app.py").write_text(f"x = {n}\n")
        git(root, "commit", "-q", "-am", f"change {n}")
    return root


SAMPLE = {
    "src/app.py": "x = 0\n",
    "src/service.py": "# TODO: split this\ndef run():\n    return 1\n",
    "src/lonely.py": "a = 1\nb = 2\nc = 3\n",
    "tests/test_app.py": "def test_x():\n    pass\n",
    "tests/test_service.py": "def test_run():\n    pass",
    "api/types.gen.ts": "export type A = 1;\n",
    "README.md": "# sample\n",
    "pyproject.toml": "[project]\nname = 'sample'\n",
    "uv.lock": "lock\n",
    "node_modules/x/index.js": "module.exports = 1;\n",
    "justfile": "set shell := ['bash']\n# comment\ndefault:\n    just --list\n\ntest *args:\n    pytest\n@lint:\n    ruff\nx := 'y'\n",
    "web/package.json": json.dumps({"scripts": {"build": "vite", "test": "vitest"}}),
    "Makefile": "all: build\n.PHONY: all\nbuild:\n\tcc\nV := 1\n",
    ".github/workflows/ci.yml": "on: push\n",
    ".github/ISSUE_TEMPLATE/bug.yml": "name: bug\n",
    ".github/labels.yml": "- name: bug\n",
    "SECURITY.md": "report privately\n",
    "AGENTS.md": "# guide\n",
    "backend/AGENTS.md": "# backend guide\n",
    ".agents/skills/triaging-issues/SKILL.md": "---\nname: triaging-issues\n---\n",
    ".claude/skills/triaging-issues/SKILL.md": "---\nname: triaging-issues\n---\n",
    ".claude/agents/scout.md": "scout\n",
    ".template-origin": "# header\ntemplate: https://github.com/owner/tpl\ncommit: unknown\nnot a pair line: x\n",
    "logo.png": b"\x89PNG\x00\x00binary",
}


class InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = make_repo(SAMPLE, commits=3)
        cls.inv = inv.build_inventory(cls.root, top=10, churn_commits=50)

    def test_identity(self):
        self.assertEqual(self.inv.remote, "owner/sample")
        self.assertEqual(self.inv.branch, "main")
        self.assertEqual(len(self.inv.head or ""), 40)
        self.assertEqual(self.inv.template_origin, {"template": "https://github.com/owner/tpl", "commit": "unknown"})
        self.assertEqual(self.inv.scale, "small")

    def test_classification_and_exclusion(self):
        self.assertEqual(self.inv.totals["source"]["files"], 3)
        self.assertEqual(self.inv.totals["test"]["files"], 2)
        self.assertEqual(self.inv.totals["generated"]["files"], 1)
        paths = {s.path for s in self.inv.largest_files}
        self.assertNotIn("node_modules/x/index.js", paths)
        self.assertNotIn("api/types.gen.ts", paths)
        self.assertEqual(self.inv.languages, {".py": 11})

    def test_mirrors_counted_once(self):
        self.assertEqual(self.inv.repo_skills, {
            ".agents/skills": ["triaging-issues"],
            ".claude/skills": ["triaging-issues"],
        })
        self.assertTrue(any("mirror" in n for n in self.inv.notes))

    def test_markers_and_untested(self):
        self.assertEqual(self.inv.markers_total, 1)
        self.assertEqual(self.inv.markers[0].path, "src/service.py")
        self.assertEqual(self.inv.markers[0].line, 1)
        self.assertEqual([s.path for s in self.inv.untested_candidates], ["src/lonely.py"])

    def test_churn(self):
        self.assertEqual(self.inv.churn_hotspots[0], {"path": "src/app.py", "commits": 3})

    def test_gates_and_conventions(self):
        self.assertEqual(self.inv.gate_entrypoints["justfile"], ["default", "test", "lint"])
        self.assertEqual(self.inv.gate_entrypoints["Makefile"], ["all", "build"])
        self.assertEqual(self.inv.gate_entrypoints["web/package.json"], ["build", "test"])
        self.assertEqual(self.inv.manifests, ["pyproject.toml", "web/package.json"])
        self.assertEqual(self.inv.ci_workflows, [".github/workflows/ci.yml"])
        self.assertEqual(self.inv.instruction_files, ["AGENTS.md", "backend/AGENTS.md"])
        self.assertEqual(self.inv.repo_agents, [".claude/agents/scout.md"])
        conv = self.inv.issue_conventions
        self.assertEqual(conv["labels_file"], ".github/labels.yml")
        self.assertEqual(conv["security_policy"], "SECURITY.md")
        self.assertEqual(conv["issue_skills"], ["triaging-issues"])
        self.assertEqual(conv["issue_templates"], [".github/ISSUE_TEMPLATE/bug.yml"])


class HelperTests(unittest.TestCase):
    def test_parse_remote(self):
        self.assertEqual(inv.parse_remote("https://github.com/a/b.git"), "a/b")
        self.assertEqual(inv.parse_remote("git@github.com:a/b"), "a/b")
        self.assertEqual(inv.parse_remote("https://gitlab.com/a/b"), "https://gitlab.com/a/b")
        self.assertIsNone(inv.parse_remote(None))

    def test_is_test_path(self):
        for path in ("x/tests/a.py", "a_test.go", "a.spec.tsx", "App/FooTests.swift",
                     "MyAppTests/x.swift", "spec/a_spec.rb", "conftest.py"):
            self.assertTrue(inv.is_test_path(path), path)
        self.assertFalse(inv.is_test_path("src/latest.py"))

    def test_classify_other_kinds(self):
        self.assertEqual(inv.classify("docs/a.md"), "doc")
        self.assertEqual(inv.classify("Dockerfile"), "config")
        self.assertEqual(inv.classify(".editorconfig"), "config")
        self.assertEqual(inv.classify("assets/a.bin"), "other")
        self.assertEqual(inv.classify("x/generated/a.py"), "generated")

    def test_count_lines(self):
        self.assertEqual(inv.count_lines(""), 0)
        self.assertEqual(inv.count_lines("a"), 1)
        self.assertEqual(inv.count_lines("a\nb\n"), 2)

    def test_parse_package_scripts_bad_input(self):
        self.assertEqual(inv.parse_package_scripts("{"), [])
        self.assertEqual(inv.parse_package_scripts("[]"), [])
        self.assertEqual(inv.parse_package_scripts('{"scripts": 1}'), [])

    def test_read_text_missing(self):
        self.assertIsNone(inv.read_text(Path("/nonexistent/file")))

    def test_primary_paths_skips_links(self):
        entries = [("120000", "a", "link"), ("160000", "b", "sub"), ("100644", "c", "x"), ("100644", "c", "y")]
        self.assertEqual(inv.primary_paths(entries), (["x"], 1))

    def test_no_tests_note(self):
        root = make_repo({"src/a.py": "a = 1\n"})
        result = inv.build_inventory(root)
        self.assertTrue(any("No test files" in n for n in result.notes))
        self.assertEqual(result.template_origin, {})


class ChangesSinceTests(unittest.TestCase):
    def test_lists_changes_since_base(self):
        root = make_repo(SAMPLE)
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
        (root / "src/app.py").write_text("x = 9\n")
        (root / "src/new.py").write_text("y = 1\n")
        (root / "uv.lock").write_text("changed\n")
        (root / "README.md").unlink()
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "next")
        result = inv.build_inventory(root, since=base).changes_since
        self.assertTrue(result["reachable"])
        self.assertEqual(result["commits"], 1)
        self.assertEqual(
            {(f["status"], f["path"], f["kind"]) for f in result["files"]},
            {("M", "src/app.py", "source"), ("A", "src/new.py", "source"), ("D", "README.md", "doc")},
        )
        self.assertEqual(result["by_area"], {"src": 2, ".": 1})

    def test_unreachable_base(self):
        root = make_repo({"a.py": "a = 1\n"})
        result = inv.changes_since(root, "0123456789abcdef0123456789abcdef01234567")
        self.assertFalse(result["reachable"])
        self.assertEqual(result["files"], [])

    def test_absent_without_since(self):
        root = make_repo({"a.py": "a = 1\n"})
        self.assertIsNone(inv.build_inventory(root).changes_since)


class MainTests(unittest.TestCase):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = inv.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_json_output(self):
        root = make_repo(SAMPLE)
        code, out, _ = self.run_main([str(root / "src"), "--json", "--top", "3"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["remote"], "owner/sample")
        self.assertLessEqual(len(data["largest_files"]), 3)

    def test_text_output(self):
        root = make_repo(SAMPLE)
        code, out, _ = self.run_main([str(root)])
        self.assertEqual(code, 0)
        self.assertIn("repo: owner/sample", out)
        self.assertIn("template: https://github.com/owner/tpl", out)
        self.assertIn("note:", out)

    def test_text_output_since(self):
        root = make_repo(SAMPLE, commits=2)
        code, out, _ = self.run_main([str(root), "--since", "HEAD~1"])
        self.assertEqual(code, 0)
        self.assertIn("since HEAD~1: 1 commits, 1 files", out)
        code, out, _ = self.run_main([str(root), "--since", "nope"])
        self.assertIn("base not reachable", out)

    def test_not_a_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = self.run_main([tmp])
        self.assertEqual(code, 2)
        self.assertIn("not inside a git work tree", err)

    def test_run_git_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                inv.run_git(Path(tmp), "rev-parse", "HEAD")
            self.assertIsNone(inv.git_or_none(Path(tmp), "rev-parse", "HEAD"))


if __name__ == "__main__":
    unittest.main()
