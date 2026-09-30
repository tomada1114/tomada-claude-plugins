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

    def detect(self, run=lambda cmd: None):
        with mock.patch.object(dt.shutil, "which", return_value=None):
            return dt.detect(self.root, run=run)

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
        self.assertEqual(det.existing["deny"], ["Bash(git push -f *)"])
        self.assertEqual(len(det.allow), len(set(det.allow)))

    def test_just_summary_preferred_when_available(self):
        write(self.root, "justfile", "ignored:\n")
        with mock.patch.object(dt.shutil, "which", return_value="/usr/bin/just"):
            det = dt.detect(self.root, run=lambda cmd: "build deploy\n")
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
        self.assertEqual(det.existing, {})

    def test_default_run(self):
        self.assertEqual(dt.default_run([sys.executable, "-c", "print('ok')"]).strip(), "ok")
        self.assertIsNone(dt.default_run([sys.executable, "-c", "raise SystemExit(3)"]))
        self.assertIsNone(dt.default_run(["/nonexistent/binary"]))

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = dt.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_main_text_json_and_errors(self):
        code, out, _ = self.run_main([str(self.root)])
        self.assertEqual(code, 1)
        write(self.root, "justfile", "run:\n\techo\n")
        with mock.patch.object(dt.shutil, "which", return_value=None):
            code, out, _ = self.run_main([str(self.root)])
            self.assertEqual(code, 0)
            self.assertIn("human-only candidates: run", out)
            code, out, _ = self.run_main([str(self.root), "--json"])
        self.assertEqual(json.loads(out)["tools"], ["just"])
        code, _, err = self.run_main([str(self.root / "missing")])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
