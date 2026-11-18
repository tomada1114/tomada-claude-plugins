#!/usr/bin/env python3
"""Tests for gate.py. Temp git repos, stub validator scripts, and a patched
run_cmd that answers for a fake `claude` binary; nothing real is evaluated."""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate  # noqa: E402

REAL_RUN_CMD = gate.run_cmd
FAKE_CLAUDE = "fake-claude"

PROMPT_A = "Please summarize the quarterly widget production report for the board meeting tomorrow morning."
PROMPT_B = "Translate the onboarding checklist for new warehouse staff into plain friendly language."

SKILL_MD = textwrap.dedent(
    """\
    ---
    name: demo
    description: Demo skill for gate tests.
    hooks:
      PreToolUse:
        - run: echo hi
    metadata:
      platforms: claude-code
    ---

    # Demo

    Do the demo thing carefully.
    """
)

VALIDATOR_STUB = textwrap.dedent(
    """\
    import json, sys
    from pathlib import Path
    here = Path(__file__).resolve().parent
    name = Path(__file__).stem
    cfg = json.loads((here / "config.json").read_text())
    parts = Path(sys.argv[1]).parts
    side = "scripts" if "scripts-check" in parts else ("base" if "base" in parts else "head")
    entry = cfg.get(name, {}).get(side, {})
    if "raw" in entry:
        print(entry["raw"])
    else:
        findings = entry.get("findings", [])
        if name == "audit_skill":
            print(json.dumps({"validate": {"findings": findings}, "audit": entry.get("audit", [])}))
        else:
            print(json.dumps({"findings": findings}))
    sys.exit(entry.get("rc", 0))
    """
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + list(args), cwd=root, capture_output=True, text=True)


def finding(level: str, code: str, location: str = "SKILL.md") -> dict:
    return {"level": level, "code": code, "message": "m", "location": location}


def call(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = gate.main(argv)
    return code, out.getvalue(), err.getvalue()


def mean(xs):
    return sum(xs) / len(xs)


class FakeClaude:
    """Stands in for `claude plugin eval`; other commands pass through."""

    def __init__(self, scores, retake=None):
        self.scores = scores  # {"base": {case: [scores]}, "head": {...}}
        self.retake = retake or {}
        self.calls = []
        self.partial = False
        self.rc = 0
        self.raise_timeout = False
        self.skip_write = False
        self.fail_on_case = False

    def __call__(self, argv, cwd=None, timeout=None):
        if argv[0] != FAKE_CLAUDE:
            return REAL_RUN_CMD(argv, cwd=cwd, timeout=timeout)
        self.calls.append(list(argv))
        if self.raise_timeout:
            raise subprocess.TimeoutExpired(argv, timeout)
        arm = "base" if "/wrap/base/" in argv[3] else "head"
        out = Path(argv[argv.index("--json") + 1])
        case = argv[argv.index("--case") + 1] if "--case" in argv else None
        if case and self.fail_on_case:
            return subprocess.CompletedProcess(argv, 2, "", "boom")
        table = self.retake.get(arm, {}) if case else self.scores.get(arm, {})
        cases = [
            {"name": n, "aggregates": {"score": mean(v)}, "arms": {"with": [{"score": s} for s in v]}}
            for n, v in table.items()
            if case is None or n == case
        ]
        if not self.skip_write:
            out.write_text(
                json.dumps({"partial": self.partial, "aggregates": {"overallScore": 0.5}, "cases": cases}),
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(argv, self.rc, "", "eval stderr")


class GateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gate-test-")).resolve()
        self.root = self.tmp / "repo"
        self.state = self.tmp / "state"
        self.vdir = self.tmp / "validators"
        self.root.mkdir()
        git(self.root, "init", "-q")
        git(self.root, "config", "user.name", "Gate Test")
        git(self.root, "config", "user.email", "gate@example.invalid")
        git(self.root, "config", "commit.gpgsign", "false")
        hooks = self.tmp / "hooks"
        hooks.mkdir()
        git(self.root, "config", "core.hooksPath", str(hooks))
        self.hooks = hooks
        skill = self.root / "skills" / "demo"
        write(skill / "SKILL.md", SKILL_MD)
        write(skill / "references" / "guide.md", "# Guide\n\nline one\nline two\n")
        write(skill / "scripts" / "tool.py", "#!/usr/bin/env python3\nprint('tool')\n")
        write(skill / "scripts" / "tests" / "test_tool.py", "import unittest\n\nclass T(unittest.TestCase):\n    pass\n")
        write(skill / "evals" / "case-a" / "prompt.md", f"---\ntags: [gate]\n---\n{PROMPT_A}\n")
        write(skill / "evals" / "case-b" / "prompt.md", f"---\ntags:\n  - gate\n  - holdout\n---\n{PROMPT_B}\n")
        write(skill / "evals" / "results" / "old" / "prompt.md", "stale result\n")
        write(self.root / "other.txt", "unrelated\n")
        write(self.root / "skills" / "plain" / "SKILL.md", "---\nname: plain\ndescription: x\n---\n\nPlain.\n")
        write(self.root / ".gitignore", "*.log\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "init")
        self.vdir.mkdir()
        for name in ("validate_skill", "audit_skill", "check_scripts"):
            write(self.vdir / f"{name}.py", VALIDATOR_STUB)
        self.set_validators({})
        self.env = mock.patch.dict(os.environ, {"AGENT_SKILL_STATE_DIR": str(self.tmp / "envstate")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers
    def set_validators(self, cfg):
        write(self.vdir / "config.json", json.dumps(cfg))

    def stage(self, *paths):
        argv = ["stage", "--root", str(self.root), "--state-dir", str(self.state)]
        for p in paths or ("skills/demo",):
            argv += ["--path", p]
        code, out, err = call(argv)
        self.assertEqual(code, 0, err)
        info = json.loads(out)
        self.run_dir = Path(info["run"])
        self.head = Path(info["head"]) / "skills" / "demo"
        return info

    def check(self, *extra, skip_eval=True):
        argv = ["check", "--run", str(self.run_dir), "--validators-dir", str(self.vdir)]
        if skip_eval:
            argv.append("--skip-eval")
        else:
            argv += ["--claude-bin", FAKE_CLAUDE]
        code, out, err = call(argv + list(extra))
        return code, json.loads(out) if out.strip() else None

    def edit_skill_body(self, extra="\nAlso keep answers short.\n"):
        p = self.head / "SKILL.md"
        p.write_text(p.read_text() + extra)


class TestHelpers(unittest.TestCase):
    def test_is_protected(self):
        self.assertTrue(gate.is_protected("a/evals/x/prompt.md", []))
        self.assertTrue(gate.is_protected("a/hooks/h.sh", []))
        self.assertTrue(gate.is_protected("a/scripts/tests/helper.py", []))
        self.assertFalse(gate.is_protected("a/scripts/tests", []))
        for name in ("test_x.py", "validate_a.py", "audit.py", "check_x.py", "guard.py", "gate.py",
                     "eslint.json", "lint-config.yaml", "judge.calibration.json"):
            self.assertTrue(gate.is_protected(f"s/{name}", []), name)
        self.assertFalse(gate.is_protected("s/SKILL.md", []))
        self.assertTrue(gate.is_protected("s/references/x.md", ["s/references/*"]))

    def test_parse_tags_forms(self):
        self.assertEqual(gate.parse_tags(["tags: [a, 'b']"]), ["a", "b"])
        self.assertEqual(gate.parse_tags(["tags:", "  - a", "", "  - b", "other: 1"]), ["a", "b"])
        self.assertEqual(gate.parse_tags(["tags: solo"]), ["solo"])
        self.assertEqual(gate.parse_tags(["name: x"]), [])

    def test_frontmatter_and_hooks(self):
        fm, body = gate.split_frontmatter(SKILL_MD)
        self.assertEqual(gate.frontmatter_value(fm, "name"), "demo")
        self.assertEqual(gate.hooks_block(fm)[0], "hooks:")
        self.assertEqual(len(gate.hooks_block(fm)), 3)
        self.assertIsNone(gate.hooks_block(["name: x"]))
        self.assertEqual(gate.split_frontmatter("no fm\nline"), ([], ["no fm", "line"]))

    def test_diff_helpers(self):
        self.assertTrue(gate.pure_additions(["a", "b"], ["a", "x", "b", "c"]))
        self.assertFalse(gate.pure_additions(["a", "b"], ["a"]))
        self.assertEqual(gate.added_lines(["a"], ["a", "b"]), [(2, "b")])
        self.assertEqual(gate.normalize("  A\n\tB  "), "a b")

    def test_run_cmd_and_default_state(self):
        proc = gate.run_cmd([sys.executable, "-c", "print('ok')"])
        self.assertEqual(proc.stdout.strip(), "ok")
        with mock.patch.dict(os.environ, {"AGENT_SKILL_STATE_DIR": "/x/y"}):
            self.assertEqual(gate.default_state_dir(), Path("/x/y/evolving-skills"))

    def test_parse_eval_result_errors(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "r.json"
            p.write_text("[1]")
            self.assertIsNone(gate.parse_eval_result(p)[0])
            p.write_text(json.dumps({"cases": [{"name": "c", "arms": {"with": []}, "aggregates": {}}]}))
            self.assertIn("no score", gate.parse_eval_result(p)[1])
            p.write_text(json.dumps({"cases": [{"name": "c", "aggregates": {"score": 0.5}}]}))
            self.assertEqual(gate.parse_eval_result(p)[0], {"c": [0.5]})

    def test_findings_from_and_location(self):
        with self.assertRaises(ValueError):
            gate._findings_from([1])
        d = Path("/tmp/skill")
        self.assertEqual(gate._norm_location("/tmp/skill/SKILL.md:12", [d]), "SKILL.md")
        self.assertEqual(gate._norm_location("scripts/a.py:3:4", [d]), "scripts/a.py")

    def test_resolve_case(self):
        cases = {"group/x": Path("a"), "y": Path("b"), "g1/z": Path("c"), "g2/z": Path("d")}
        self.assertEqual(gate.resolve_case("x", cases), "group/x")
        self.assertEqual(gate.resolve_case("y", cases), "y")
        self.assertIsNone(gate.resolve_case("z", cases))


class TestStage(GateTestCase):
    def test_refuses_dirty_path(self):
        write(self.root / "skills" / "demo" / "SKILL.md", SKILL_MD + "dirty\n")
        code, out, err = call(["stage", "--root", str(self.root), "--path", "skills/demo",
                               "--state-dir", str(self.state)])
        self.assertEqual(code, 3)
        self.assertIn("skills/demo/SKILL.md", err)
        self.assertFalse((self.state / "runs").exists())

    def test_copies_only_tracked_files(self):
        write(self.root / "skills" / "demo" / "notes.log", "ignored\n")
        info = self.stage()
        for side in ("base", "head"):
            top = Path(info[side])
            self.assertTrue((top / "skills/demo/SKILL.md").is_file())
            self.assertTrue((top / "skills/demo/evals/case-a/prompt.md").is_file())
            self.assertFalse((top / "skills/demo/notes.log").exists())
            self.assertFalse((top / "other.txt").exists())
        meta = json.loads((self.run_dir / "run.json").read_text())
        self.assertEqual(meta["paths"], ["skills/demo"])
        self.assertEqual(meta["root"], str(self.root))
        self.assertEqual(meta["base_commit"], git(self.root, "rev-parse", "HEAD").stdout.strip())
        self.assertRegex(self.run_dir.name, r"^\d{8}T\d{6}Z-[0-9a-f]{4}$")

    def test_default_state_dir_from_env(self):
        code, out, _ = call(["stage", "--root", str(self.root), "--path", "skills/demo"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["run"].startswith(str(self.tmp / "envstate" / "evolving-skills" / "runs")))

    def test_bad_paths(self):
        base = ["stage", "--root", str(self.root), "--state-dir", str(self.state), "--path"]
        self.assertEqual(call(base + ["../x"])[0], 3)
        self.assertEqual(call(base + ["missing"])[0], 3)
        self.assertEqual(call(base + [str(self.root / "skills")])[0], 3)
        os.symlink(self.tmp, self.root / "escape")
        self.assertEqual(call(base + ["escape"])[0], 3)
        sub = ["stage", "--root", str(self.root / "skills"), "--path", "demo", "--state-dir", str(self.state)]
        self.assertEqual(call(sub)[0], 3)
        self.assertEqual(call(["stage", "--root", str(self.tmp / "nope"), "--path", "x"])[0], 3)
        self.assertEqual(call(["stage", "--root", str(self.tmp), "--path", "repo"])[0], 3)
        self.assertEqual(call([])[0], 3)

    def test_root_path_dot(self):
        code, out, _ = call(["stage", "--root", str(self.root), "--path", ".", "--state-dir", str(self.state)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((Path(json.loads(out)["run"]) / "run.json").read_text())["paths"], ["."])


class TestGuard(GateTestCase):
    def setUp(self):
        super().setUp()
        self.stage()

    def violations(self, verdict):
        return verdict["steps"]["guard"].get("violations", [])

    def test_missing_run_and_empty_diff(self):
        code, _, _ = call(["check", "--run", str(self.tmp / "nope")])
        self.assertEqual(code, 3)
        code, v = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(v["verdict"], "fail")
        self.assertEqual(v["reasons"], ["empty-diff"])
        self.assertEqual(v["steps"]["guard"]["status"], "skipped")
        self.assertTrue((self.run_dir / "verdict.json").is_file())

    def test_protected_added_allowed(self):
        write(self.head / "evals" / "case-c" / "prompt.md", "---\ntags: [gate]\n---\nA brand new case.\n")
        write(self.head / "scripts" / "tests" / "test_more.py", "pass\n")
        code, v = self.check()
        self.assertEqual(v["steps"]["guard"]["status"], "pass")
        self.assertEqual(code, 4)
        self.assertEqual(v["verdict"], "unmeasured")
        self.assertEqual(v["steps"]["eval"]["status"], "unmeasured")
        self.assertIn("skills/demo/evals/case-c/prompt.md", v["steps"]["diff"]["added"])

    def test_protected_modified_pure_addition_allowed(self):
        p = self.head / "scripts" / "tests" / "test_tool.py"
        p.write_text(p.read_text() + "\n# extra\n")
        code, v = self.check()
        self.assertEqual(v["steps"]["guard"]["status"], "pass")

    def test_protected_modified_with_deletion_blocked(self):
        p = self.head / "scripts" / "tests" / "test_tool.py"
        p.write_text("import unittest\n")
        code, v = self.check()
        self.assertEqual(code, 2)
        self.assertEqual(v["verdict"], "blocked")
        self.assertEqual(self.violations(v)[0]["kind"], "protected-modified")
        self.assertEqual(v["steps"]["validators"]["status"], "skipped")

    def test_protected_binary_modified_blocked(self):
        p = self.head / "evals" / "case-a" / "prompt.md"
        p.write_bytes(b"\xff\xfe" + p.read_bytes())
        code, v = self.check()
        self.assertEqual(code, 2)

    def test_protected_removed_blocked(self):
        (self.head / "evals" / "case-b" / "prompt.md").unlink()
        code, v = self.check()
        self.assertEqual(code, 2)
        self.assertEqual(self.violations(v)[0], {"kind": "protected-removed", "file": "skills/demo/evals/case-b/prompt.md"})

    def test_extra_protect_glob(self):
        write(self.head / "references" / "guide.md", "# Guide\n")
        code, v = self.check("--protect", "skills/demo/references/*")
        self.assertEqual(code, 2)
        self.assertEqual(self.violations(v)[0]["kind"], "protected-modified")

    def test_frontmatter_hooks_modified_blocked(self):
        p = self.head / "SKILL.md"
        p.write_text(p.read_text().replace("run: echo hi", "run: echo bye"))
        code, v = self.check()
        self.assertEqual(code, 2)
        self.assertEqual(self.violations(v)[0]["detail"], "frontmatter hooks")

    def test_frontmatter_hooks_removed_blocked(self):
        p = self.head / "SKILL.md"
        p.write_text(p.read_text().replace("hooks:\n  PreToolUse:\n    - run: echo hi\n", ""))
        code, v = self.check()
        self.assertEqual(code, 2)

    def test_frontmatter_hooks_addition_allowed(self):
        p = self.head / "SKILL.md"
        p.write_text(p.read_text().replace("    - run: echo hi\n", "    - run: echo hi\n    - run: echo more\n"))
        code, v = self.check()
        self.assertEqual(v["steps"]["guard"]["status"], "pass")

    def write_self_check(self, root_skill, section):
        p = root_skill / "SKILL.md"
        p.write_text(p.read_text() + section + "\n## After\n\ntrailing text\n")

    def restage_with_self_check(self):
        self.write_self_check(self.root / "skills" / "demo", "\n## Self-check\n\n- Output names the file.\n- Every claim cites a source.\n")
        git(self.root, "commit", "-q", "-am", "self-check")
        self.stage()

    def test_self_check_section_helper(self):
        lines = ["# T", "## SELF-CHECK before done", "- a", "## Next", "- b"]
        self.assertEqual(gate.self_check_section(lines), ["## SELF-CHECK before done", "- a"])
        self.assertEqual(gate.self_check_section(["## Self-check", "- a"]), ["## Self-check", "- a"])
        self.assertIsNone(gate.self_check_section(["## Self-checks", "## Other"]))

    def test_self_check_addition_allowed(self):
        self.restage_with_self_check()
        p = self.head / "SKILL.md"
        p.write_text(p.read_text().replace("- Every claim cites a source.\n",
                                           "- Every claim cites a source.\n- Dates are absolute.\n"))
        code, v = self.check()
        self.assertEqual(v["steps"]["guard"]["status"], "pass", v)

    def test_self_check_loosened_blocked(self):
        self.restage_with_self_check()
        p = self.head / "SKILL.md"
        p.write_text(p.read_text().replace("- Every claim cites a source.\n", "- Most claims cite a source.\n"))
        code, v = self.check()
        self.assertEqual(code, 2)
        self.assertEqual(self.violations(v), [{"kind": "protected-modified", "file": "skills/demo/SKILL.md",
                                               "detail": "self-check section"}])

    def test_self_check_removed_blocked(self):
        self.restage_with_self_check()
        p = self.head / "SKILL.md"
        text = p.read_text()
        start = text.index("## Self-check")
        p.write_text(text[:start] + text[text.index("## After"):])
        code, v = self.check()
        self.assertEqual(code, 2)
        self.assertEqual(self.violations(v)[0]["detail"], "self-check section")

    def test_self_check_new_section_allowed(self):
        self.write_self_check(self.head, "\n## Self-check\n\n- New criterion.\n")
        code, v = self.check()
        self.assertEqual(v["steps"]["guard"]["status"], "pass", v)

    def test_budget_skill_body(self):
        self.edit_skill_body("".join(f"line {i}\n" for i in range(150)))
        code, v = self.check()
        self.assertEqual(code, 2)
        self.assertEqual(self.violations(v)[0]["kind"], "budget")
        self.assertIn("limit 150", self.violations(v)[0]["detail"])

    def test_budget_new_skill_md(self):
        write(self.head / "sub" / "SKILL.md", "---\nname: sub\n---\n" + "x\n" * 151)
        code, v = self.check()
        self.assertEqual(code, 2)
        self.assertIn("base none", self.violations(v)[0]["detail"])

    def test_budget_reference(self):
        write(self.head / "references" / "big.md", "x\n" * 401)
        write(self.head / "references" / "ok.md", "x\n" * 400)
        code, v = self.check()
        self.assertEqual(code, 2)
        self.assertEqual([x["file"] for x in self.violations(v)], ["skills/demo/references/big.md"])

    def test_leak_blocked(self):
        self.edit_skill_body("\nIntro.\nWhen asked to SUMMARIZE the quarterly   widget production report, be brief.\n")
        code, v = self.check()
        self.assertEqual(code, 2)
        leak = self.violations(v)[0]
        self.assertEqual(leak["kind"], "leak")
        self.assertEqual(leak["file"], "skills/demo/SKILL.md")
        self.assertEqual(leak["line"], 16)
        self.assertEqual(len(leak["text"]), 32)
        self.assertIn("quarterly widget", leak["text"])
        code, v = self.check("--leak-chars", "80")
        self.assertEqual(v["steps"]["guard"]["status"], "pass")

    def test_non_utf8_file_skipped(self):
        (self.head / "references" / "blob.md").write_bytes(b"\xff\xfe\x00")
        code, v = self.check()
        self.assertEqual(v["steps"]["guard"]["status"], "pass")

    def test_change_outside_staged_paths_blocked(self):
        write(self.run_dir / "head" / "other.txt", "sneaky\n")
        write(self.run_dir / "head" / "skills" / "other" / "evals" / "x" / "prompt.md", "planted\n")
        code, v = self.check()
        self.assertEqual(code, 2)
        kinds = {(x["kind"], x["file"]) for x in self.violations(v)}
        self.assertIn(("outside-staged-paths", "other.txt"), kinds)
        self.assertIn(("outside-staged-paths", "skills/other/evals/x/prompt.md"), kinds)
        self.assertTrue(gate.under_paths("a/b", ["."]))
        self.assertFalse(gate.under_paths("skills/demo2/x", ["skills/demo"]))

    def test_pycache_ignored_in_diff(self):
        write(self.head / "scripts" / "__pycache__" / "tool.pyc", "bytecode")
        code, v = self.check()
        self.assertEqual(v["reasons"], ["empty-diff"])


class TestValidators(GateTestCase):
    def setUp(self):
        super().setUp()
        self.stage()
        self.edit_skill_body()

    def test_pass_with_same_errors_on_moved_lines(self):
        self.set_validators({
            "validate_skill": {
                "base": {"findings": [finding("error", "E1", "SKILL.md:3"), finding("warning", "W1")], "rc": 1},
                "head": {"findings": [finding("error", "E1", "SKILL.md:9"), finding("warning", "W1")], "rc": 1},
            },
        })
        code, v = self.check()
        self.assertEqual(v["steps"]["validators"]["status"], "pass", v["steps"]["validators"])
        self.assertEqual(code, 4)

    def test_new_error_is_regression(self):
        self.set_validators({"audit_skill": {"head": {"audit": [finding("error", "A1")], "rc": 1}}})
        code, v = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(v["reasons"], ["validator-regression"])
        self.assertEqual(v["steps"]["validators"]["skills"]["skills/demo"]["new_errors"], ["A1@SKILL.md"])
        self.assertEqual(v["steps"]["eval"]["status"], "skipped")

    def test_more_warnings_is_regression(self):
        self.set_validators({"validate_skill": {"head": {"findings": [finding("warning", "W2")]}}})
        code, v = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(v["steps"]["validators"]["skills"]["skills/demo"]["warnings"], {"base": 0, "head": 1})

    def test_missing_validators_dir_inconclusive(self):
        code, out, _ = call(["check", "--run", str(self.run_dir), "--skip-eval",
                             "--validators-dir", str(self.tmp / "none")])
        v = json.loads(out)
        self.assertEqual(code, 4)
        self.assertEqual(v["verdict"], "inconclusive")
        self.assertEqual(v["steps"]["validators"]["status"], "unavailable")

    def test_default_validators_dir_resolution(self):
        fake_file = self.tmp / "skills" / "evolving-skills" / "scripts" / "gate.py"
        with mock.patch.object(gate, "__file__", str(fake_file)):
            code, out, _ = call(["check", "--run", str(self.run_dir), "--skip-eval"])
        v = json.loads(out)
        self.assertEqual(v["steps"]["validators"]["missing"],
                         [str(self.tmp / "skills" / "creating-agent-skills" / "scripts")])

    def test_missing_script_inconclusive(self):
        (self.vdir / "check_scripts.py").rename(self.vdir / "moved.py")
        code, v = self.check()
        self.assertEqual(code, 4)
        self.assertTrue(v["steps"]["validators"]["missing"][0].endswith("check_scripts.py"))

    def test_bad_exit_and_unparsable_output(self):
        self.set_validators({"validate_skill": {"head": {"rc": 2}}})
        code, v = self.check()
        self.assertEqual(code, 4)
        self.assertIn("exited 2", v["steps"]["validators"]["error"])
        self.set_validators({"validate_skill": {"base": {"raw": "not json"}}})
        code, v = self.check()
        self.assertEqual(code, 4)
        self.assertIn("unparsable", v["steps"]["validators"]["error"])

    def test_validator_timeout(self):
        def boom(argv, cwd=None, timeout=None):
            if argv[0] == "python3":
                raise subprocess.TimeoutExpired(argv, timeout)
            return REAL_RUN_CMD(argv, cwd=cwd, timeout=timeout)
        with mock.patch.object(gate, "run_cmd", boom):
            code, v = self.check()
        self.assertEqual(code, 4)

    def test_scripts_check_runs_on_scratch_copy(self):
        p = self.head / "scripts" / "tool.py"
        p.write_text(p.read_text() + "print('more')\n")
        self.set_validators({"check_scripts": {"scripts": {"findings": [finding("error", "S002", "scripts/tests")], "rc": 1}}})
        code, v = self.check()
        self.assertEqual(code, 1)
        self.assertIn("scripts-check", v["reasons"])
        self.assertTrue((self.run_dir / "scripts-check" / "skills__demo" / "SKILL.md").is_file())
        # A second check reuses (replaces) the scratch copy.
        self.set_validators({})
        code, v = self.check()
        self.assertEqual(v["steps"]["validators"]["status"], "pass")
        self.assertEqual(v["steps"]["validators"]["skills"]["skills/demo"]["scripts_check_errors"], [])

    def test_scripts_check_unavailable(self):
        p = self.head / "scripts" / "tool.py"
        p.write_text(p.read_text() + "print('more')\n")
        self.set_validators({"check_scripts": {"scripts": {"rc": 2}}})
        code, v = self.check()
        self.assertEqual(code, 4)

    def test_file_path_without_skill(self):
        self.stage("other.txt")
        write(self.run_dir / "head" / "other.txt", "changed\n")
        code, v = self.check()
        self.assertEqual(v["steps"]["validators"]["note"], "no staged skill directory")
        self.assertEqual(code, 4)


class EvalTestCase(GateTestCase):
    def setUp(self):
        super().setUp()
        self.stage()
        self.edit_skill_body()

    def run_eval(self, fake, *extra):
        with mock.patch.object(gate, "run_cmd", fake):
            return self.check(*extra, skip_eval=False)


class TestEval(EvalTestCase):
    def test_pass_and_command_shape(self):
        fake = FakeClaude({"base": {"case-a": [0.5, 0.5], "case-b": [0.6]},
                           "head": {"case-a": [0.7, 0.7], "case-b": [0.6]}})
        code, v = self.run_eval(fake, "--runs", "2", "--max-cost-usd", "1.5", "--tags", "gate", "smoke")
        self.assertEqual(code, 0, v)
        self.assertEqual(v["verdict"], "pass")
        self.assertEqual(len(fake.calls), 2)
        argv = fake.calls[0]
        self.assertEqual(argv[:4], [FAKE_CLAUDE, "plugin", "eval", str(self.run_dir / "wrap" / "base" / "demo")])
        for flag in ("--no-publish", "--trust-plugin"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--ablation") + 1], "none")
        self.assertEqual(argv[argv.index("--threshold") + 1], "0")
        self.assertEqual(argv[argv.index("--runs") + 1], "2")
        self.assertEqual(argv[argv.index("--max-cost-usd") + 1], "1.5")
        self.assertEqual(argv[argv.index("--json") + 1], str(self.run_dir / "eval-base-demo.json"))
        self.assertEqual(argv[-3:], ["--tag", "gate", "smoke"])
        wrap = self.run_dir / "wrap" / "head" / "demo"
        manifest = json.loads((wrap / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest, {"name": "demo", "version": "0.0.0", "description": "evolving-skills gate wrapper"})
        self.assertTrue((wrap / "skills" / "demo" / "SKILL.md").is_file())
        self.assertFalse((wrap / "skills" / "demo" / "evals").exists())
        self.assertTrue((wrap / "evals" / "case-a" / "prompt.md").is_file())
        self.assertFalse((wrap / "evals" / "results").exists())
        self.assertIn("Also keep answers short", (wrap / "skills" / "demo" / "SKILL.md").read_text())
        self.assertNotIn("Also keep answers short",
                         (self.run_dir / "wrap/base/demo/skills/demo/SKILL.md").read_text())
        cases = v["steps"]["eval"]["skills"]["skills/demo"]["cases"]
        self.assertEqual(cases["case-a"], {"head": 0.7, "new": False, "tags": ["gate"], "base": 0.5})
        self.assertEqual(cases["case-b"]["tags"], ["gate", "holdout"])
        # Re-running check rebuilds wrappers in place.
        code, v = self.run_eval(fake)
        self.assertEqual(code, 0)

    def test_r1_fail(self):
        fake = FakeClaude({"base": {"case-a": [0.6], "case-b": [0.6]}, "head": {"case-a": [0.5], "case-b": [0.6]}},
                          retake={"base": {"case-a": [0.6]}, "head": {"case-a": [0.5]}})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 1)
        r = v["steps"]["eval"]["skills"]["skills/demo"]
        self.assertEqual(r["failed_rules"], ["R1"])
        self.assertEqual(r["retaken"], ["case-a"])
        self.assertIn("skills/demo: R1", v["reasons"])

    def test_r2_fail_then_pass_after_retake(self):
        fake = FakeClaude({"base": {"case-a": [0.6], "case-b": [0.5]}, "head": {"case-a": [0.2], "case-b": [0.9]}},
                          retake={"base": {"case-a": [0.6, 0.6]}, "head": {"case-a": [1.0, 1.0]}})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 0, v)
        r = v["steps"]["eval"]["skills"]["skills/demo"]
        self.assertEqual(r["retaken"], ["case-a"])
        self.assertAlmostEqual(r["cases"]["case-a"]["head"], round((0.2 + 1.0 + 1.0) / 3, 4))
        retake_calls = [c for c in fake.calls if "--case" in c]
        self.assertEqual(len(retake_calls), 2)
        self.assertNotIn("--tag", retake_calls[0])
        self.assertTrue(retake_calls[0][retake_calls[0].index("--json") + 1].endswith("eval-base-demo-retake-case-a.json"))
        self.assertEqual(len(fake.calls), 4)

    def test_r2_fail_after_retake(self):
        fake = FakeClaude({"base": {"case-a": [0.9], "case-b": [0.1]}, "head": {"case-a": [0.3], "case-b": [1.0]}},
                          retake={"base": {"case-a": [0.9]}, "head": {"case-a": [0.3]}})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 1)
        self.assertEqual(v["steps"]["eval"]["skills"]["skills/demo"]["failed_rules"], ["R2"])

    def test_retake_inconclusive(self):
        fake = FakeClaude({"base": {"case-a": [0.6], "case-b": [0.6]}, "head": {"case-a": [0.2], "case-b": [0.6]}})
        fake.fail_on_case = True
        code, v = self.run_eval(fake)
        self.assertEqual(code, 4)
        self.assertIn("retake", v["steps"]["eval"]["skills"]["skills/demo"]["reason"])

    def add_new_case(self):
        write(self.head / "evals" / "case-new" / "prompt.md", "---\ntags: [gate]\n---\nCompletely different wording.\n")

    def test_r3_baseline_already_passes(self):
        self.add_new_case()
        fake = FakeClaude({"base": {"case-a": [0.5], "case-new": [0.8]}, "head": {"case-a": [0.5], "case-new": [0.9]}})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 1)
        r = v["steps"]["eval"]["skills"]["skills/demo"]
        self.assertEqual(r["failed_rules"], ["R3"])
        self.assertEqual(r["details"]["reason"], "baseline-already-passes")
        self.assertTrue(r["cases"]["case-new"]["new"])
        self.assertIn("skills/demo: baseline-already-passes", v["reasons"])

    def test_r3_new_case_must_reach_threshold_and_blocks_retake(self):
        self.add_new_case()
        fake = FakeClaude({"base": {"case-a": [0.9], "case-new": [0.1]}, "head": {"case-a": [0.1], "case-new": [0.5]}})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 1)
        r = v["steps"]["eval"]["skills"]["skills/demo"]
        self.assertEqual(r["failed_rules"], ["R1", "R2", "R3"])
        self.assertEqual(r["retaken"], [])
        self.assertEqual(len(fake.calls), 2)

    def test_r3_pass(self):
        self.add_new_case()
        fake = FakeClaude({"base": {"case-a": [0.5], "case-new": [0.2]}, "head": {"case-a": [0.5], "case-new": [0.7]}})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 0, v)

    def test_r4_only_on_final(self):
        scores = {"base": {"case-a": [0.2], "case-b": [0.6]}, "head": {"case-a": [0.6], "case-b": [0.5]}}
        code, v = self.run_eval(FakeClaude(scores))
        self.assertEqual(code, 0, v)
        fake = FakeClaude(scores)
        code, v = self.run_eval(fake, "--final")
        self.assertEqual(code, 1)
        self.assertTrue(v["final"])
        self.assertEqual(v["steps"]["eval"]["skills"]["skills/demo"]["failed_rules"], ["R4"])
        self.assertNotIn("--tag", fake.calls[0])

    def test_inconclusive_partial(self):
        fake = FakeClaude({"base": {"case-a": [0.5]}, "head": {"case-a": [0.5]}})
        fake.partial = True
        code, v = self.run_eval(fake)
        self.assertEqual(code, 4)
        self.assertEqual(v["verdict"], "inconclusive")
        self.assertIn("partial", v["steps"]["eval"]["skills"]["skills/demo"]["reason"])

    def test_inconclusive_nonzero_timeout_missing(self):
        for attr, val, needle in (("rc", 2, "exited 2"), ("raise_timeout", True, "timed out"),
                                  ("skip_write", True, "unreadable")):
            fake = FakeClaude({"base": {"case-a": [0.5]}, "head": {"case-a": [0.5]}})
            setattr(fake, attr, val)
            code, v = self.run_eval(fake)
            self.assertEqual(code, 4, attr)
            self.assertIn(needle, v["steps"]["eval"]["skills"]["skills/demo"]["reason"])

    def test_claude_binary_missing(self):
        argv = ["check", "--run", str(self.run_dir), "--validators-dir", str(self.vdir),
                "--claude-bin", str(self.tmp / "no-such-claude")]
        code, out, _ = call(argv)
        self.assertEqual(code, 4)
        self.assertIn("could not start", json.loads(out)["steps"]["eval"]["skills"]["skills/demo"]["reason"])

    def test_case_missing_on_base_arm(self):
        fake = FakeClaude({"base": {"case-a": [0.5]}, "head": {"case-a": [0.5], "case-b": [0.5]}})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 4)

    def test_unmeasured_when_no_case_matched(self):
        fake = FakeClaude({"base": {}, "head": {}})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 4)
        self.assertEqual(v["verdict"], "unmeasured")

    def test_unmeasured_without_evals(self):
        self.stage("skills/plain")
        p = self.run_dir / "head" / "skills" / "plain" / "SKILL.md"
        p.write_text(p.read_text() + "More.\n")
        fake = FakeClaude({})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 4)
        self.assertEqual(v["steps"]["eval"]["skills"]["skills/plain"]["reason"], "no eval cases")
        self.assertEqual(fake.calls, [])

    def add_case(self, name, front):
        write(self.head / "evals" / name / "prompt.md", f"---\n{front}---\nCompletely different wording {name}.\n")

    def test_new_case_untagged_fails_without_running(self):
        self.add_case("case-new", "tags: [smoke]\n")
        fake = FakeClaude({"base": {"case-a": [0.5]}, "head": {"case-a": [0.5]}})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 1)
        self.assertEqual(fake.calls, [])
        r = v["steps"]["eval"]["skills"]["skills/demo"]
        self.assertEqual(r["details"], {"reason": "new-case-untagged", "cases": ["case-new"]})
        self.assertIn("skills/demo: new-case-untagged", v["reasons"])

    def test_new_case_holdout_only_skips_r3(self):
        self.add_case("case-new", "tags: [holdout]\n")
        scores = {"base": {"case-a": [0.5], "case-new": [0.9]}, "head": {"case-a": [0.5], "case-new": [0.9]}}
        code, v = self.run_eval(FakeClaude(scores))
        self.assertEqual(code, 0, v)
        scores["head"]["case-new"] = [0.2]
        code, v = self.run_eval(FakeClaude(scores), "--final")
        self.assertEqual(code, 1)
        self.assertEqual(v["steps"]["eval"]["skills"]["skills/demo"]["failed_rules"], ["R4"])

    def test_two_of_three_runs_pass_threshold(self):
        self.add_case("case-new", "tags: [gate]\n")
        fake = FakeClaude({"base": {"case-a": [0.5], "case-new": [0.0, 0.0, 0.0]},
                           "head": {"case-a": [0.5], "case-new": [1.0, 1.0, 0.0]}})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 0, v)
        self.assertEqual(gate.PASS_SCORE, 0.66)
        fake = FakeClaude({"base": {"case-a": [0.5], "case-new": [1.0, 1.0, 0.0]},
                           "head": {"case-a": [0.5], "case-new": [1.0, 1.0, 1.0]}})
        code, v = self.run_eval(fake)
        self.assertEqual(v["steps"]["eval"]["skills"]["skills/demo"]["details"]["reason"], "baseline-already-passes")

    def test_frontmatter_case_name(self):
        self.add_case("dir-x", "name: custom-name\ntags: [gate]\n")
        self.add_case("custom-name", "tags: [gate]\n")
        fake = FakeClaude({"base": {"case-a": [0.5], "custom-name": [0.1], "x-dir": [0.1]},
                           "head": {"case-a": [0.5], "custom-name": [0.9], "x-dir": [0.1]}})
        code, v = self.run_eval(fake)
        cases = v["steps"]["eval"]["skills"]["skills/demo"]["cases"]
        self.assertEqual(cases["custom-name"]["tags"], ["gate"])
        self.assertTrue(cases["custom-name"]["new"])
        self.assertFalse(cases["x-dir"]["new"])
        self.assertEqual(code, 0, v)
        cases_map = gate.find_cases(self.head / "evals")
        self.assertEqual(gate.resolve_case("custom-name", cases_map), "dir-x")
        self.assertEqual(gate.resolve_case("dir-x", cases_map), None)

    def test_nested_case_names_and_case_yaml(self):
        write(self.head / "evals" / "group" / "case-y" / "case.yaml", "prompt: hi\ntags:\n  - holdout\n")
        fake = FakeClaude({"base": {"case-a": [0.5], "group/case-y": [0.1], "ghost": [0.5]},
                           "head": {"case-a": [0.5], "group/case-y": [0.8], "ghost": [0.5]}})
        code, v = self.run_eval(fake)
        self.assertEqual(code, 0, v)
        cases = v["steps"]["eval"]["skills"]["skills/demo"]["cases"]
        self.assertTrue(cases["group/case-y"]["new"])
        self.assertEqual(cases["group/case-y"]["tags"], ["holdout"])
        self.assertFalse(cases["ghost"]["new"])


class TestBrandNewSkill(GateTestCase):
    def setUp(self):
        super().setUp()
        write(self.root / "skills" / "fresh" / ".keep", "")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "fresh dir")
        self.stage("skills/fresh")
        self.fresh = self.run_dir / "head" / "skills" / "fresh"
        write(self.fresh / "SKILL.md", "---\nname: fresh-skill\ndescription: x\n---\n\nBody.\n")
        write(self.fresh / "evals" / "c1" / "prompt.md", "Write a haiku about rivers.\n")

    def test_new_skill_pass_and_fail(self):
        fake = FakeClaude({"head": {"c1": [0.9]}})
        with mock.patch.object(gate, "run_cmd", fake):
            code, v = self.check(skip_eval=False)
        self.assertEqual(code, 0, v)
        self.assertEqual(len(fake.calls), 1)
        self.assertIn("/wrap/head/fresh-skill", fake.calls[0][3])
        self.assertTrue(v["steps"]["eval"]["skills"]["skills/fresh"]["new_skill"])
        fake = FakeClaude({"head": {"c1": [0.5]}})
        with mock.patch.object(gate, "run_cmd", fake):
            code, v = self.check(skip_eval=False)
        self.assertEqual(code, 1)
        self.assertEqual(v["steps"]["eval"]["skills"]["skills/fresh"]["failed_rules"], ["new-skill"])


class TestLand(GateTestCase):
    def setUp(self):
        super().setUp()
        self.stage()
        self.edit_skill_body()
        write(self.head / "references" / "new.md", "# New\n")
        (self.head / "references" / "guide.md").unlink()
        self.msg = self.tmp / "msg.txt"
        self.msg.write_text("evolving-skills: tighten demo\n")

    def land(self, *extra):
        return call(["land", "--run", str(self.run_dir), "--message-file", str(self.msg)] + list(extra))

    def make_pass(self):
        self.run_eval_pass()

    def run_eval_pass(self):
        fake = FakeClaude({"base": {"case-a": [0.5]}, "head": {"case-a": [0.6]}})
        with mock.patch.object(gate, "run_cmd", fake):
            code, v = self.check(skip_eval=False)
        self.assertEqual(code, 0, v)

    def test_refuses_without_verdict(self):
        code, _, err = self.land()
        self.assertEqual(code, 3)
        self.assertIn("verdict.json", err)

    def test_refuses_failed_and_unmeasured(self):
        code, v = self.check()  # --skip-eval -> unmeasured
        self.assertEqual(v["verdict"], "unmeasured")
        code, _, err = self.land()
        self.assertEqual(code, 3)
        self.assertIn("unmeasured", err)
        verdict = json.loads((self.run_dir / "verdict.json").read_text())
        verdict["verdict"] = "fail"
        (self.run_dir / "verdict.json").write_text(json.dumps(verdict))
        self.assertEqual(self.land("--allow-unmeasured")[0], 3)

    def test_refuses_digest_change(self):
        self.make_pass()
        self.edit_skill_body("\nsneaky\n")
        code, _, err = self.land()
        self.assertEqual(code, 3)
        self.assertIn("head/ changed", err)

    def test_refuses_dirty_paths(self):
        self.make_pass()
        write(self.root / "skills" / "demo" / "scratch.txt", "x")
        code, _, err = self.land()
        self.assertEqual(code, 3)
        self.assertIn("uncommitted", err)

    def test_refuses_moved_repo(self):
        self.make_pass()
        write(self.root / "skills" / "demo" / "references" / "guide.md", "# Changed upstream\n")
        git(self.root, "commit", "-q", "-am", "upstream")
        code, _, err = self.land()
        self.assertEqual(code, 3)
        self.assertIn("changed in the repository", err)

    def test_refuses_bad_base_commit(self):
        self.make_pass()
        meta = json.loads((self.run_dir / "run.json").read_text())
        meta["base_commit"] = "0" * 40
        (self.run_dir / "run.json").write_text(json.dumps(meta))
        code, _, err = self.land()
        self.assertEqual(code, 3)
        self.assertIn("base-tampered", err)

    def test_refuses_git_diff_error(self):
        self.make_pass()

        def fake(argv, cwd=None, timeout=None):
            if argv[:2] == ["git", "diff"]:
                return subprocess.CompletedProcess(argv, 128, "", "bad object")
            return REAL_RUN_CMD(argv, cwd=cwd, timeout=timeout)
        with mock.patch.object(gate, "run_cmd", fake):
            code, _, err = self.land()
        self.assertEqual(code, 3)
        self.assertIn("git diff failed", err)

    def test_refuses_tampered_base_after_check(self):
        self.make_pass()
        (self.run_dir / "base" / "skills" / "demo" / "evals" / "case-a" / "prompt.md").write_text("weakened\n")
        code, _, err = self.land()
        self.assertEqual(code, 3)
        self.assertIn("base-tampered: skills/demo/evals/case-a/prompt.md", err)

    def test_refuses_run_json_changed_after_check(self):
        self.make_pass()
        meta = json.loads((self.run_dir / "run.json").read_text())
        meta["paths"] = ["skills/demo", "skills/demo/references"]
        (self.run_dir / "run.json").write_text(json.dumps(meta))
        code, _, err = self.land()
        self.assertEqual(code, 3)
        self.assertIn("base-tampered: run.json paths", err)

    def test_refuses_empty_message(self):
        self.make_pass()
        self.msg.write_text("  \n")
        self.assertEqual(self.land()[0], 3)

    def test_land_success_leaves_unrelated_alone(self):
        self.make_pass()
        write(self.root / "other.txt", "locally edited\n")
        write(self.root / "untracked.txt", "mine\n")
        code, out, err = self.land()
        self.assertEqual(code, 0, err)
        info = json.loads(out)
        self.assertEqual(info["commit"], git(self.root, "rev-parse", "HEAD").stdout.strip())
        self.assertEqual(sorted(info["files"]), ["skills/demo/SKILL.md", "skills/demo/references/guide.md",
                                                 "skills/demo/references/new.md"])
        shown = git(self.root, "show", "--name-status", "--format=%s", "HEAD").stdout
        self.assertIn("evolving-skills: tighten demo", shown)
        self.assertIn("D\tskills/demo/references/guide.md", shown)
        self.assertIn("A\tskills/demo/references/new.md", shown)
        self.assertNotIn("other.txt", shown)
        status = git(self.root, "status", "--porcelain").stdout
        self.assertIn(" M other.txt", status)
        self.assertIn("?? untracked.txt", status)
        self.assertNotIn("skills/demo", status)
        self.assertEqual((self.root / "other.txt").read_text(), "locally edited\n")
        self.assertTrue((self.run_dir / "landed.json").is_file())

    def test_land_unmeasured_with_flag(self):
        self.check()
        code, out, err = self.land("--allow-unmeasured")
        self.assertEqual(code, 0, err)

    def test_commit_failure_exit_5(self):
        self.make_pass()
        hook = self.hooks / "pre-commit"
        hook.write_text("#!/bin/sh\necho hook says no >&2\nexit 1\n")
        hook.chmod(0o755)
        code, _, err = self.land()
        self.assertEqual(code, 5)
        self.assertIn("skills/demo/SKILL.md", err)
        self.assertIn("hook says no", err)

    def test_git_rm_and_add_failures(self):
        self.make_pass()
        for failing in ("rm", "add"):
            git(self.root, "reset", "-q", "--hard")
            git(self.root, "clean", "-fdq", "skills")

            def fake(argv, cwd=None, timeout=None, failing=failing):
                if argv[:2] == ["git", failing]:
                    return subprocess.CompletedProcess(argv, 1, "", f"{failing} failed")
                return REAL_RUN_CMD(argv, cwd=cwd, timeout=timeout)
            with mock.patch.object(gate, "run_cmd", fake):
                code, _, err = self.land()
            self.assertEqual(code, 5, failing)
            self.assertIn(f"{failing} failed", err)


class TestBaseIntegrity(GateTestCase):
    def setUp(self):
        super().setUp()
        self.stage()
        self.edit_skill_body()
        self.base = self.run_dir / "base" / "skills" / "demo"

    def assert_tampered(self, needle):
        code, out, err = call(["check", "--run", str(self.run_dir), "--skip-eval", "--validators-dir", str(self.vdir)])
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("base-tampered", err)
        self.assertIn(needle, err)
        self.assertFalse((self.run_dir / "verdict.json").exists())

    def test_clean_base_passes(self):
        self.assertEqual(gate.base_mismatches(self.run_dir, json.loads((self.run_dir / "run.json").read_text())), [])
        v = json.loads(call(["check", "--run", str(self.run_dir), "--skip-eval",
                             "--validators-dir", str(self.vdir)])[1])
        self.assertEqual(v["paths"], ["skills/demo"])
        self.assertEqual(v["new_paths"], [])
        self.assertEqual(v["base_commit"], git(self.root, "rev-parse", "HEAD").stdout.strip())

    def test_modified_base_file(self):
        (self.base / "scripts" / "tests" / "test_tool.py").write_text("")
        self.assert_tampered("skills/demo/scripts/tests/test_tool.py")

    def test_extra_base_file(self):
        write(self.base / "references" / "padding.md", "x\n")
        self.assert_tampered("skills/demo/references/padding.md")

    def test_missing_base_file(self):
        (self.base / "references" / "guide.md").unlink()
        self.assert_tampered("skills/demo/references/guide.md")

    def test_base_file_outside_paths(self):
        write(self.run_dir / "base" / "other.txt", "unrelated\n")
        self.assert_tampered("other.txt")

    def test_symlink_blob_and_sha256_ids(self):
        self.assertEqual(gate.git_blob_id(b"", 40), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")
        self.assertEqual(len(gate.git_blob_id(b"", 64)), 64)
        os.symlink("SKILL.md", self.root / "skills" / "demo" / "link.md")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "link")
        self.stage()
        self.assertTrue((self.run_dir / "base" / "skills" / "demo" / "link.md").is_symlink())
        self.assertEqual(gate.base_mismatches(self.run_dir, json.loads((self.run_dir / "run.json").read_text())), [])


class TestNewPath(GateTestCase):
    def stage_new(self, *extra):
        code, out, err = call(["stage", "--root", str(self.root), "--state-dir", str(self.state),
                               "--new-path", "skills/brand"] + list(extra))
        self.assertEqual(code, 0, err)
        info = json.loads(out)
        self.run_dir = Path(info["run"])
        self.brand = Path(info["head"]) / "skills" / "brand"
        return info

    def fill(self):
        write(self.brand / "SKILL.md", "---\nname: brand\ndescription: x\n---\n\nBody.\n")
        write(self.brand / "evals" / "c1" / "prompt.md", "---\ntags: [smoke]\n---\nWrite a haiku about rivers.\n")

    def test_stage_new_path(self):
        info = self.stage_new("--path", "skills/demo")
        meta = json.loads((self.run_dir / "run.json").read_text())
        self.assertEqual(meta["new_paths"], ["skills/brand"])
        self.assertEqual(meta["paths"], ["skills/demo"])
        self.assertTrue(self.brand.is_dir())
        self.assertEqual(list(self.brand.iterdir()), [])
        self.assertFalse((Path(info["base"]) / "skills" / "brand").exists())

    def test_stage_new_path_refusals(self):
        base = ["stage", "--root", str(self.root), "--state-dir", str(self.state), "--new-path"]
        self.assertEqual(call(base + ["skills/demo"])[0], 3)
        self.assertEqual(call(base + ["../x"])[0], 3)
        self.assertEqual(call(base + ["."])[0], 3)
        os.symlink(self.tmp, self.root / "escape")
        self.assertEqual(call(base + ["escape/inner"])[0], 3)
        (self.root / "other.txt").unlink()  # tracked but missing from the work tree
        code, _, err = call(base + ["other.txt"])
        self.assertEqual(code, 3)
        self.assertIn("tracked", err)
        self.assertEqual(call(["stage", "--root", str(self.root), "--state-dir", str(self.state)])[0], 3)

    def check(self, *extra, skip_eval=True):
        argv = ["check", "--run", str(self.run_dir), "--validators-dir", str(self.vdir)]
        argv += ["--skip-eval"] if skip_eval else ["--claude-bin", FAKE_CLAUDE]
        code, out, err = call(argv + list(extra))
        return code, json.loads(out) if out.strip() else None

    def test_new_skill_validators_allow_warnings_not_errors(self):
        self.stage_new()
        self.fill()
        self.set_validators({"validate_skill": {"head": {"findings": [finding("warning", "W1")]}}})
        code, v = self.check()
        self.assertEqual(v["steps"]["validators"]["status"], "pass", v)
        self.assertEqual(v["steps"]["guard"]["status"], "pass")
        self.set_validators({"validate_skill": {"head": {"findings": [finding("error", "E1")], "rc": 1}}})
        code, v = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(v["reasons"], ["validator-regression"])

    def test_new_skill_eval_head_only_and_land(self):
        self.stage_new()
        self.fill()
        fake = FakeClaude({"head": {"c1": [1.0, 1.0, 0.0]}})
        with mock.patch.object(gate, "run_cmd", fake):
            code, v = self.check(skip_eval=False)
        self.assertEqual(code, 0, v)
        self.assertEqual(len(fake.calls), 1)
        msg = self.tmp / "msg.txt"
        msg.write_text("add brand skill\n")
        (self.root / "skills" / "brand").mkdir()  # an empty dir git status cannot see
        code, _, err = call(["land", "--run", str(self.run_dir), "--message-file", str(msg)])
        self.assertEqual(code, 3)
        self.assertIn("new path now exists", err)
        os.rename(self.root / "skills" / "brand", self.tmp / "squatter-moved")
        code, out, err = call(["land", "--run", str(self.run_dir), "--message-file", str(msg)])
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["files"], ["skills/brand/SKILL.md", "skills/brand/evals/c1/prompt.md"])
        self.assertIn("skills/brand/SKILL.md", git(self.root, "show", "--name-only", "--format=", "HEAD").stdout)

    def test_new_path_base_must_stay_empty(self):
        self.stage_new()
        self.fill()
        write(self.run_dir / "base" / "skills" / "brand" / "SKILL.md", "planted\n")
        code, _, err = call(["check", "--run", str(self.run_dir), "--skip-eval", "--validators-dir", str(self.vdir)])
        self.assertEqual(code, 3)
        self.assertIn("skills/brand/SKILL.md", err)


class TestRevert(GateTestCase):
    def commit_change(self):
        write(self.root / "skills" / "demo" / "references" / "guide.md", "# Guide v2\n")
        git(self.root, "commit", "-q", "-am", "change")
        return git(self.root, "rev-parse", "HEAD").stdout.strip()

    def test_revert_success(self):
        sha = self.commit_change()
        code, out, err = call(["revert", "--root", str(self.root), "--commit", sha])
        self.assertEqual(code, 0, err)
        info = json.loads(out)
        self.assertEqual(info["reverted"], sha)
        self.assertEqual(info["commit"], git(self.root, "rev-parse", "HEAD").stdout.strip())
        self.assertEqual((self.root / "skills/demo/references/guide.md").read_text(), "# Guide\n\nline one\nline two\n")

    def test_revert_refuses_dirty(self):
        sha = self.commit_change()
        write(self.root / "skills" / "demo" / "references" / "guide.md", "dirty\n")
        code, _, err = call(["revert", "--root", str(self.root), "--commit", sha])
        self.assertEqual(code, 3)
        self.assertIn("uncommitted", err)

    def test_revert_git_failure(self):
        sha = self.commit_change()

        def fake(argv, cwd=None, timeout=None):
            if argv[:2] == ["git", "revert"]:
                return subprocess.CompletedProcess(argv, 1, "", "conflict")
            return REAL_RUN_CMD(argv, cwd=cwd, timeout=timeout)
        with mock.patch.object(gate, "run_cmd", fake):
            code, _, err = call(["revert", "--root", str(self.root), "--commit", sha])
        self.assertEqual(code, 5)
        self.assertIn("conflict", err)

    def test_revert_unknown_commit(self):
        code, _, _ = call(["revert", "--root", str(self.root), "--commit", "deadbeef"])
        self.assertEqual(code, 3)


if __name__ == "__main__":
    unittest.main()
