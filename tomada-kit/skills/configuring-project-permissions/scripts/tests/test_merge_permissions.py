import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import merge_permissions as mp  # noqa: E402


class MergeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.settings = self.dir / ".claude" / "settings.json"
        self.rules = self.dir / "rules.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = mp.main([str(self.settings), "--rules", str(self.rules), *extra])
        return code, out.getvalue(), err.getvalue()

    def test_merge_keeps_other_keys_and_order(self):
        self.settings.parent.mkdir()
        self.settings.write_text(json.dumps({
            "permissions": {"allow": ["Bash(just check)"], "deny": ["Bash(git push -f *)"]},
            "hooks": {"PostToolUse": []}}))
        self.rules.write_text(json.dumps({"allow": ["Bash(just *)", "Bash(just check)", "Bash(just *)", ""],
                                          "ask": ["Bash(just run*)"]}))
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        data = json.loads(self.settings.read_text())
        self.assertEqual(data["permissions"]["allow"], ["Bash(just check)", "Bash(just *)"])
        self.assertEqual(data["permissions"]["ask"], ["Bash(just run*)"])
        self.assertEqual(data["permissions"]["deny"], ["Bash(git push -f *)"])
        self.assertIn("hooks", data)
        self.assertIn("+1 allow", out)
        self.assertTrue(self.settings.read_text().endswith("\n"))

    def test_creates_missing_file_and_reports_conflicts(self):
        self.rules.write_text(json.dumps({"allow": ["Bash(x *)"], "ask": ["Bash(x *)"], "deny": ["Bash(x *)"]}))
        code, out, _ = self.run_main("--json")
        report = json.loads(out)
        self.assertTrue(report["created"])
        self.assertEqual(len(report["conflicts"]), 2)
        self.assertTrue(self.settings.exists())

    def test_dry_run_and_nothing_to_change(self):
        self.rules.write_text(json.dumps({"allow": ["Bash(y *)"]}))
        code, out, _ = self.run_main("--dry-run")
        self.assertFalse(self.settings.exists())
        self.rules.write_text(json.dumps({}))
        code, out, _ = self.run_main()
        self.assertIn("nothing to change", out)

    def test_text_conflict_output(self):
        self.rules.write_text(json.dumps({"allow": ["Bash(z *)"], "deny": ["Bash(z *)"]}))
        code, out, _ = self.run_main()
        self.assertIn("conflict: Bash(z *) is in allow and deny", out)

    def test_global_redundant_and_shadowed(self):
        g = self.dir / "global.json"
        g.write_text(json.dumps({"permissions": {"allow": ["Bash(git *)"], "ask": ["Bash(gh pr merge *)"],
                                                 "deny": ["Bash(rm -rf *)"]}}))
        self.rules.write_text(json.dumps({"allow": ["Bash(git status *)", "Bash(gh pr merge 1)",
                                                    "Bash(rm -rf build)", "Bash(just *)"],
                                          "ask": ["Bash(git push *)"], "deny": ["Bash(git push -f *)"]}))
        code, out, _ = self.run_main("--global", str(g), "--json")
        report = json.loads(out)
        self.assertEqual(report["redundant"], [{"rule": "Bash(git status *)", "by": "Bash(git *)"}])
        self.assertEqual(report["shadowed"], [
            {"rule": "Bash(gh pr merge 1)", "by": "Bash(gh pr merge *)", "kind": "ask"},
            {"rule": "Bash(rm -rf build)", "by": "Bash(rm -rf *)", "kind": "deny"}])
        perms = json.loads(self.settings.read_text())["permissions"]
        self.assertEqual(perms["allow"], ["Bash(just *)"])
        self.assertEqual(perms["ask"], ["Bash(git push *)"])
        self.assertEqual(perms["deny"], ["Bash(git push -f *)"])
        code, out, _ = self.run_main("--global", str(g))
        self.assertIn("redundant: Bash(git status *)", out)
        self.assertIn("shadowed: Bash(rm -rf build) (global deny", out)
        g.write_text("{bad")
        code, _, _ = self.run_main("--global", str(g))
        self.assertEqual(code, 1)

    def test_hooks_merge_and_dedupe(self):
        hook = {"matcher": "Edit", "hooks": [{"type": "command", "command": "fmt"}]}
        self.settings.parent.mkdir()
        self.settings.write_text(json.dumps({"hooks": {"PostToolUse": [hook]}}))
        other = {"hooks": [{"command": "x", "type": "command"}], "matcher": "Write"}
        self.rules.write_text(json.dumps({"hooks": {
            "PostToolUse": [{"hooks": [{"command": "fmt", "type": "command"}], "matcher": "Edit"}, other, other],
            "Stop": [hook], "Bad": "x"}}))
        code, out, _ = self.run_main("--json")
        self.assertEqual(json.loads(out)["hooks_added"], {"PostToolUse": 1, "Stop": 1})
        data = json.loads(self.settings.read_text())
        self.assertEqual(data["hooks"]["PostToolUse"], [hook, other])
        code, out, _ = self.run_main()
        self.assertIn("nothing to change", out)
        self.rules.write_text(json.dumps({"hooks": {"Pre": [hook]}}))
        code, out, _ = self.run_main()
        self.assertIn("+1 hooks.Pre", out)
        self.assertEqual(mp.merge_hooks({}, []), {})

    def test_bad_inputs(self):
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.rules.write_text("[]")
        code, _, err = self.run_main()
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
