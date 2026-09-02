#!/usr/bin/env python3
"""Tests for check_scripts.py. Stdlib-only (unittest).

Run: python3 -m unittest scripts.tests.test_check_scripts -v
     (from the creating-agent-skills skill directory)
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_scripts as cs  # noqa: E402


def make_script(path: Path, content: str, *, shebang: bool = True, exec_bit: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = content if not shebang else "#!/usr/bin/env python3\n" + content
    path.write_text(text, encoding="utf-8")
    mode = path.stat().st_mode
    if exec_bit:
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    else:
        path.chmod(mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)
    return path


PASSING_SCRIPT = "def add(a, b):\n    return a + b\n"

PASSING_TEST = (
    "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n"
    "import unittest\nimport foo\n\nclass T(unittest.TestCase):\n"
    "    def test_add(self):\n        self.assertEqual(foo.add(1, 2), 3)\n\n"
    "if __name__ == '__main__':\n    unittest.main()\n"
)

FAILING_TEST = (
    "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n"
    "import unittest\nimport foo\n\nclass T(unittest.TestCase):\n"
    "    def test_add(self):\n        self.assertEqual(foo.add(1, 2), 999)\n\n"
    "if __name__ == '__main__':\n    unittest.main()\n"
)

# A test that only exercises half of foo.py's branches, so total coverage
# lands below 90% for a script with more than one function.
PARTIAL_SCRIPT = (
    "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n\n\n"
    "def mul(a, b):\n    return a * b\n\n\ndef div(a, b):\n    return a / b\n\n\n"
    "def mod(a, b):\n    return a % b\n\n\ndef pow_(a, b):\n    return a ** b\n\n\n"
    "def neg(a):\n    return -a\n\n\ndef zero():\n    return 0\n\n\n"
    "def one():\n    return 1\n\n\ndef two():\n    return 2\n"
)
PARTIAL_TEST = (
    "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n"
    "import unittest\nimport foo\n\nclass T(unittest.TestCase):\n"
    "    def test_add(self):\n        self.assertEqual(foo.add(1, 2), 3)\n\n"
    "if __name__ == '__main__':\n    unittest.main()\n"
)


class TestFindScripts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "skill"
        self.root.mkdir()

    def test_no_scripts_dir(self):
        self.assertEqual(cs.find_scripts(self.root), [])

    def test_finds_py_and_sh_excludes_underscore_and_tests_dir(self):
        make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        make_script(self.root / "scripts" / "bar.sh", "echo hi\n")
        make_script(self.root / "scripts" / "_helper.py", "x = 1\n")
        make_script(self.root / "scripts" / "tests" / "test_foo.py", PASSING_TEST)
        found = {p.name for p in cs.find_scripts(self.root)}
        self.assertEqual(found, {"foo.py", "bar.sh"})


class TestS000(unittest.TestCase):
    def test_no_scripts_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skill"
            root.mkdir()
            report = cs.check(root, with_tests=False)
            self.assertFalse(report.has_scripts)
            self.assertTrue(any(f.code == "S000" and f.level == "info" for f in report.findings))
            self.assertEqual(report.errors, [])


class TestS001(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "skill"
        self.root.mkdir()

    def test_py_without_test_is_warning(self):
        make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        findings = cs.check_test_presence(self.root, cs.find_scripts(self.root))
        s001 = [f for f in findings if f.code == "S001"]
        self.assertEqual(len(s001), 1)
        self.assertEqual(s001[0].level, "warning")

    def test_sh_without_test_is_info(self):
        make_script(self.root / "scripts" / "bar.sh", "echo hi\n")
        findings = cs.check_test_presence(self.root, cs.find_scripts(self.root))
        s001 = [f for f in findings if f.code == "S001"]
        self.assertEqual(len(s001), 1)
        self.assertEqual(s001[0].level, "info")

    def test_present_test_suppresses_finding(self):
        make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        make_script(self.root / "scripts" / "tests" / "test_foo.py", PASSING_TEST)
        findings = cs.check_test_presence(self.root, cs.find_scripts(self.root))
        self.assertFalse([f for f in findings if f.code == "S001"])


class TestS002(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "skill"
        self.root.mkdir()

    def test_passing_tests_no_s002(self):
        make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        make_script(self.root / "scripts" / "tests" / "test_foo.py", PASSING_TEST)
        report = cs.check(self.root, with_tests=True)
        self.assertTrue(report.tests.ran)
        self.assertEqual(report.tests.returncode, 0)
        self.assertFalse([f for f in report.findings if f.code == "S002" and f.level == "error"])

    def test_failing_tests_error_s002(self):
        make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        make_script(self.root / "scripts" / "tests" / "test_foo.py", FAILING_TEST)
        report = cs.check(self.root, with_tests=True)
        self.assertTrue(report.tests.ran)
        self.assertNotEqual(report.tests.returncode, 0)
        s002 = [f for f in report.findings if f.code == "S002"]
        self.assertTrue(any(f.level == "error" for f in s002))
        self.assertTrue(report.errors)

    def test_no_tests_flag_skips(self):
        make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        make_script(self.root / "scripts" / "tests" / "test_foo.py", PASSING_TEST)
        report = cs.check(self.root, with_tests=False)
        self.assertFalse(report.tests.ran)
        self.assertTrue(any(f.code == "S002" and f.level == "info" for f in report.findings))

    def test_missing_tests_dir_skips(self):
        make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        report = cs.check(self.root, with_tests=True)
        self.assertFalse(report.tests.ran)
        self.assertTrue(any(f.code == "S002" and f.level == "info" for f in report.findings))


class TestS003S004(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "skill"
        self.root.mkdir()

    def test_s004_when_coverage_unavailable(self):
        make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        make_script(self.root / "scripts" / "tests" / "test_foo.py", PASSING_TEST)
        orig = cs.coverage_available
        cs.coverage_available = lambda: False
        try:
            report = cs.check(self.root, with_tests=True)
        finally:
            cs.coverage_available = orig
        self.assertTrue(any(f.code == "S004" and f.level == "info" for f in report.findings))
        self.assertFalse([f for f in report.findings if f.code == "S003"])

    @unittest.skipUnless(cs.coverage_available(), "coverage package not installed")
    def test_s003_below_threshold(self):
        make_script(self.root / "scripts" / "foo.py", PARTIAL_SCRIPT)
        make_script(self.root / "scripts" / "tests" / "test_foo.py", PARTIAL_TEST)
        report = cs.check(self.root, with_tests=True, min_coverage=90)
        self.assertIsNotNone(report.coverage.percent)
        self.assertLess(report.coverage.percent, 90)
        self.assertTrue(any(f.code == "S003" and f.level == "warning" for f in report.findings))

    @unittest.skipUnless(cs.coverage_available(), "coverage package not installed")
    def test_s003_not_fired_when_fully_covered(self):
        make_script(self.root / "scripts" / "foo.py", "def add(a, b):\n    return a + b\n")
        make_script(self.root / "scripts" / "tests" / "test_foo.py", PASSING_TEST)
        report = cs.check(self.root, with_tests=True, min_coverage=90)
        self.assertIsNotNone(report.coverage.percent)
        self.assertGreaterEqual(report.coverage.percent, 90)
        self.assertFalse([f for f in report.findings if f.code == "S003"])


class TestS005(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "skill"
        self.root.mkdir()

    def test_missing_shebang(self):
        p = make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT, shebang=False)
        findings = cs.check_headers(self.root, [p])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "S005")
        self.assertIn("shebang", findings[0].message)

    def test_missing_exec_bit(self):
        p = make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT, exec_bit=False)
        findings = cs.check_headers(self.root, [p])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "S005")
        self.assertIn("exec", findings[0].message)

    def test_clean_script_no_finding(self):
        p = make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        findings = cs.check_headers(self.root, [p])
        self.assertFalse(findings)


class TestS006(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "skill"
        self.root.mkdir()

    def test_hardcoded_path_hit(self):
        p = make_script(
            self.root / "scripts" / "foo.py",
            'PATH = "/Users/tomada/.claude/skills/other-skill"\n',
        )
        findings = cs.check_hardcoded_paths(self.root, [p])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "S006")

    def test_ignored_marker_suppresses(self):
        p = make_script(
            self.root / "scripts" / "foo.py",
            'PATH = "/Users/tomada/.claude/skills/other-skill"  # scripts-ignore: S006\n',
        )
        findings = cs.check_hardcoded_paths(self.root, [p])
        self.assertFalse(findings)

    def test_no_hit_on_clean_script(self):
        p = make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        findings = cs.check_hardcoded_paths(self.root, [p])
        self.assertFalse(findings)


class TestS007(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "skill"
        self.root.mkdir()

    def _git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, check=True)

    def test_not_a_git_repo_is_info(self):
        findings = cs.check_gitignore(self.root)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "S007")
        self.assertEqual(findings[0].level, "info")

    def test_git_repo_with_full_gitignore_is_clean(self):
        self._git("init", "-q")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        (self.root / ".gitignore").write_text(
            "scripts/__pycache__/\n.coverage\n", encoding="utf-8"
        )
        findings = cs.check_gitignore(self.root)
        self.assertFalse(findings)

    def test_git_repo_without_gitignore_is_warning(self):
        self._git("init", "-q")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        findings = cs.check_gitignore(self.root)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "S007")
        self.assertEqual(findings[0].level, "warning")


class TestMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "skill"
        self.root.mkdir()

    def test_exit_0_clean(self):
        rc = cs.main(["check_scripts.py", str(self.root)])
        self.assertEqual(rc, 0)

    def test_exit_1_on_failing_tests(self):
        make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        make_script(self.root / "scripts" / "tests" / "test_foo.py", FAILING_TEST)
        rc = cs.main(["check_scripts.py", str(self.root), "--no-tests"])
        # with --no-tests the failing suite never runs, so this should be clean
        self.assertEqual(rc, 0)
        rc2 = cs.main(["check_scripts.py", str(self.root)])
        self.assertEqual(rc2, 1)

    def test_exit_2_bad_path(self):
        rc = cs.main(["check_scripts.py", str(self.root / "does-not-exist")])
        self.assertEqual(rc, 2)

    def test_json_output_keys(self):
        make_script(self.root / "scripts" / "foo.py", PASSING_SCRIPT)
        make_script(self.root / "scripts" / "tests" / "test_foo.py", PASSING_TEST)
        old_stdout = sys.stdout
        from io import StringIO
        sys.stdout = buf = StringIO()
        try:
            cs.main(["check_scripts.py", str(self.root), "--json"])
        finally:
            sys.stdout = old_stdout
        data = json.loads(buf.getvalue())
        for key in ("skill_path", "has_scripts", "scripts", "tests", "coverage", "findings"):
            self.assertIn(key, data)
        self.assertIn("ran", data["tests"])
        self.assertIn("returncode", data["tests"])
        self.assertIn("summary", data["tests"])
        self.assertIn("percent", data["coverage"])
        self.assertIn("threshold", data["coverage"])
        self.assertIn("below_threshold_files", data["coverage"])


class TestRenderHuman(unittest.TestCase):
    def test_no_findings(self):
        report = cs.ScriptsReport(skill_path="/tmp/skill", has_scripts=False)
        out = cs.render_human(report)
        self.assertIn("OK", out)

    def test_with_findings(self):
        report = cs.ScriptsReport(skill_path="/tmp/skill", has_scripts=True, scripts=["foo.py"])
        report.add("error", "S002", "boom")
        report.add("warning", "S005", "no shebang")
        report.add("info", "S000", "info msg")
        out = cs.render_human(report)
        self.assertIn("S002", out)
        self.assertIn("S005", out)
        self.assertIn("S000", out)
        self.assertIn("ERRORS", out)
        self.assertIn("WARNINGS", out)
        self.assertIn("INFOS", out)


if __name__ == "__main__":
    unittest.main()
