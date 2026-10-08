import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import detect_toolchain as dt  # noqa: E402


def write(root: Path, rel: str, text: str = "") -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class DetectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def detect(self, run=lambda cmd: None, **kw):
        kw.setdefault("check", lambda cmd: None)
        with mock.patch.object(dt.shutil, "which", return_value=None):
            return dt.detect(self.root, run=run, **kw)

    def test_tauri_like_repo(self):
        write(self.root, "justfile", "set shell := ['bash']\ndefault:\n\t@just --list\n"
                                     "check: lint test\n\techo\nrun *args:\n\techo\nlabels:\n\techo\n")
        write(self.root, "mise.toml")
        write(self.root, "package.json", json.dumps({
            "packageManager": "pnpm@10.0.0", "scripts": {"dev": "vite", "test": "vitest"},
            "devDependencies": {"@tauri-apps/cli": "2", "vite": "7", "vitest": "3", "lefthook": "1"}}))
        write(self.root, "Cargo.toml")
        write(self.root, "src-tauri/tauri.conf.json", "{}")
        write(self.root, "typos.toml")
        write(self.root, ".github/workflows/ci.yml")
        write(self.root, "scripts/a.sh")
        write(self.root, ".claude/settings.json", json.dumps({"permissions": {"deny": ["Bash(git push -f *)"]}}))
        det = self.detect()
        for tool in ("just", "mise", "pnpm", "tauri", "vite", "lefthook", "cargo", "typos", "actionlint", "shellcheck"):
            self.assertIn(tool, det.tools)
        self.assertEqual(det.recipes, ["default", "check", "run", "labels"])
        self.assertEqual(det.human_candidates, ["run", "labels", "dev"])
        self.assertIn("Bash(just run*)", det.ask)
        self.assertIn("Bash(pnpm run dev*)", det.ask)
        self.assertIn("Bash(cargo *)", det.allow)
        self.assertIn("Bash(mise exec -- cargo *)", det.allow)
        self.assertIn("WebFetch(domain:docs.rs)", det.allow)
        self.assertEqual(det.existing["committed"]["deny"], ["Bash(git push -f *)"])
        self.assertEqual(det.existing["local"], {"allow": [], "ask": [], "deny": []})
        self.assertIn("Bash(scripts/*)", det.allow)
        self.assertNotIn("Bash(git *)", det.allow)
        self.assertIn("Bash(git *)", det.global_candidates["allow"])
        self.assertIn("WebFetch(domain:github.com)", det.global_candidates["allow"])
        self.assertEqual(det.global_candidates["domains"], dt.BASELINE_DOMAINS)
        self.assertEqual(len(det.allow), len(set(det.allow)))

    def test_just_summary_preferred_when_available(self):
        write(self.root, "justfile", "ignored:\n")
        with mock.patch.object(dt.shutil, "which", return_value="/usr/bin/just"):
            det = dt.detect(self.root, run=lambda cmd: "build deploy\n", check=lambda cmd: None)
        self.assertEqual(det.recipes, ["build", "deploy"])
        self.assertIn("Bash(just deploy*)", det.ask)

    def test_swift_xcodegen_make_python(self):
        write(self.root, "App.xcodeproj/project.pbxproj")
        write(self.root, "project.yml", "targets:\n  App: {}\n")
        write(self.root, "Makefile", ".PHONY: x\nbuild:\n\techo\nrelease: build\n\techo\n")
        write(self.root, "pyproject.toml", "[project]\nname='x'\n")
        write(self.root, ".swiftlint.yml")
        det = self.detect()
        for tool in ("swift", "xcodegen", "make", "python", "swiftlint"):
            self.assertIn(tool, det.tools)
        self.assertIn("Bash(make release*)", det.ask)
        self.assertIn("Bash(xcrun notarytool *)", det.ask)

    def test_uv_variants_go_docker_and_lockfile_manager(self):
        write(self.root, "pyproject.toml", "[tool.uv]\n")
        write(self.root, "go.mod")
        write(self.root, "compose.yaml")
        write(self.root, "package.json", "{not json")
        write(self.root, "yarn.lock")
        det = self.detect()
        for tool in ("uv", "go", "docker", "yarn"):
            self.assertIn(tool, det.tools)
        write(self.root, "uv.lock")
        self.assertEqual(self.detect().evidence["uv"], "uv.lock")

    def test_unreadable_settings_and_components(self):
        write(self.root, "components.json", "{}")
        write(self.root, ".claude/settings.json", "{broken")
        det = self.detect()
        self.assertIn("shadcn", det.tools)
        self.assertEqual(det.existing["committed"], {})

    def test_default_run(self):
        self.assertEqual(dt.default_run([sys.executable, "-c", "print('ok')"]).strip(), "ok")
        self.assertIsNone(dt.default_run([sys.executable, "-c", "raise SystemExit(3)"]))
        self.assertIsNone(dt.default_run(["/nonexistent/binary"]))

    def test_cleanup_recipes_are_not_human_candidates(self):
        write(self.root, "justfile", "clean:\n\techo\nprune-temp:\n\techo\nnuke:\n\techo\nbuild:\n\techo\n")
        det = self.detect()
        self.assertEqual(det.cleanup_recipes, ["clean", "prune-temp", "nuke"])
        self.assertEqual(det.human_candidates, [])

    def test_script_rules(self):
        write(self.root, "justfile", "build:\n")
        write(self.root, "scripts/tool.ts")
        det = self.detect()
        self.assertNotIn("Bash(scripts/*)", det.allow)
        (self.root / "scripts/tool.ts").chmod(0o755)
        write(self.root, ".agents/skills/x/scripts/a.py")
        det = self.detect()
        self.assertIn("Bash(scripts/*)", det.allow)
        self.assertIn("Bash(.agents/skills/*/scripts/*)", det.allow)
        self.assertIn("Bash(bash .agents/skills/*/scripts/*)", det.allow)

    def test_global_coverage_and_blocking(self):
        write(self.root, "justfile", "run:\n\techo\nbuild:\n")
        write(self.root, "Cargo.toml")
        g = self.root / "global.json"
        g.write_text(json.dumps({"permissions": {
            "allow": ["Bash(git *)", "Bash(rustup *)", "WebFetch(domain:docs.rs)", "WebFetch(domain:github.com)"],
            "ask": ["Bash(cargo publish *)", "Bash(just *)"],
            "deny": ["Bash(rustc *)"]}}))
        det = self.detect(global_path=g)
        self.assertNotIn("Bash(rustup *)", det.allow)
        self.assertIn({"rule": "Bash(rustup *)", "by": "Bash(rustup *)"}, det.covered_by_global)
        self.assertIn({"rule": "WebFetch(domain:docs.rs)", "by": "WebFetch(domain:docs.rs)"}, det.covered_by_global)
        self.assertIn({"rule": "Bash(cargo publish *)", "by": "Bash(cargo publish *)"}, det.covered_by_global)
        self.assertIn({"rule": "Bash(just run*)", "by": "Bash(just *)"}, det.covered_by_global)
        self.assertNotIn("Bash(cargo publish *)", det.ask)
        self.assertIn({"rule": "Bash(rustc *)", "by": "Bash(rustc *)", "kind": "deny"}, det.blocked_by_global)
        self.assertIn({"rule": "Bash(just *)", "by": "Bash(just *)", "kind": "ask"}, det.blocked_by_global)
        self.assertNotIn("Bash(just *)", det.allow)
        self.assertNotIn("Bash(rustc *)", det.allow)
        self.assertIn("Bash(cargo *)", det.allow)
        self.assertNotIn("Bash(git *)", det.global_candidates["allow"])
        self.assertNotIn("github.com", det.global_candidates["domains"])
        g.write_text("{bad")
        with self.assertRaises(ValueError):
            self.detect(global_path=g)

    def test_local_settings_and_committed_hooks(self):
        write(self.root, ".claude/settings.local.json", json.dumps({"permissions": {"allow": ["Bash(a *)"]}}))
        write(self.root, ".claude/settings.json", json.dumps({"hooks": {"PostToolUse": [{}]}}))
        det = self.detect()
        self.assertEqual(det.existing["local"]["allow"], ["Bash(a *)"])
        self.assertTrue(det.committed_hooks)

    def test_ignored_via_check(self):
        calls = []

        def check(cmd):
            calls.append(cmd)
            return {".claude/settings.local.json": 0, ".codex/rules/local.rules": 1}[cmd[-1]]
        det = self.detect(check=check)
        self.assertEqual(det.ignored, {".claude/settings.local.json": True, ".codex/rules/local.rules": False})
        self.assertEqual(calls[0][:5], ["git", "-C", str(self.root), "check-ignore", "-q"])
        det = self.detect(check=lambda cmd: 128)
        self.assertEqual(set(det.ignored.values()), {None})

    def test_default_check(self):
        self.assertEqual(dt.default_check([sys.executable, "-c", "raise SystemExit(1)"]), 1)
        self.assertIsNone(dt.default_check(["/nonexistent/binary"]))

    def test_codex_state(self):
        home = self.root / "codex"
        det = self.detect(codex_home=home)
        self.assertEqual(det.codex, {"trusted": None, "local_rules": False, "config": str(home / "config.toml")})
        write(self.root, "codex/config.toml",
              f'[projects."{self.root.resolve()}"]\ntrust_level = "trusted"\n')
        write(self.root, ".codex/rules/local.rules")
        det = self.detect(codex_home=home)
        self.assertTrue(det.codex["trusted"])
        self.assertTrue(det.codex["local_rules"])
        write(self.root, "codex/config.toml", '[projects."/elsewhere"]\ntrust_level = "trusted"\n')
        self.assertFalse(self.detect(codex_home=home).codex["trusted"])
        write(self.root, "codex/config.toml", "not = = toml")
        self.assertIsNone(self.detect(codex_home=home).codex["trusted"])
        self.assertEqual(self.detect().codex["config"], "")

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = dt.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_main_text_json_and_errors(self):
        home = ["--codex-home", str(self.root / "codex")]
        g = self.root / "g.json"
        g.write_text(json.dumps({"permissions": {"deny": ["Bash(just *)"]}}))
        code, out, _ = self.run_main([str(self.root), "--no-global", *home])
        self.assertEqual(code, 1)
        write(self.root, "justfile", "run:\n\techo\nclean:\n")
        with mock.patch.object(dt.shutil, "which", return_value=None):
            code, out, _ = self.run_main([str(self.root), "--global", str(g), *home])
            self.assertEqual(code, 0)
            self.assertIn("human-only candidates: run", out)
            self.assertIn("cleanup recipes: clean", out)
            self.assertIn("global candidates:", out)
            self.assertIn("blocked: Bash(just *) by deny Bash(just *)", out)
            self.assertIn("ignored: .claude/settings.local.json=", out)
            self.assertIn("codex: trusted=None", out)
            code, out, _ = self.run_main([str(self.root), "--json", "--no-global", *home])
        self.assertEqual(json.loads(out)["tools"], ["just"])
        code, _, err = self.run_main([str(self.root / "missing"), "--no-global"])
        self.assertEqual(code, 2)
        g.write_text("{bad")
        code, _, err = self.run_main([str(self.root), "--global", str(g), *home])
        self.assertEqual(code, 2)
        self.assertIn("global settings", err)


if __name__ == "__main__":
    unittest.main()
