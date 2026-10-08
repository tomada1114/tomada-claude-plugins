import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rule_match as rm  # noqa: E402


class RuleMatchTest(unittest.TestCase):
    def test_split_rule(self):
        self.assertEqual(rm.split_rule("Bash(just *)"), ("Bash", "just *"))
        self.assertEqual(rm.split_rule("WebSearch"), ("WebSearch", None))
        self.assertEqual(rm.split_rule("Bash(npm run:*)"), ("Bash", "npm run *"))

    def test_rule_regex(self):
        self.assertTrue(rm.rule_regex("just *").fullmatch("just"))
        self.assertTrue(rm.rule_regex("just *").fullmatch("just check"))
        self.assertFalse(rm.rule_regex("just *").fullmatch("justify"))
        self.assertTrue(rm.rule_regex("a.b").fullmatch("a.b"))
        self.assertFalse(rm.rule_regex("a.b").fullmatch("axb"))

    def test_covers_required_examples(self):
        yes = [("Bash(just *)", "Bash(just run*)"), ("Bash(just *)", "Bash(just)"),
               ("Bash(just *)", "Bash(just check)"), ("Bash(cargo *)", "Bash(cargo publish *)"),
               ("WebFetch(domain:github.com)", "WebFetch(domain:github.com)"),
               ("Read(*)", "Read(src/**)"), ("Bash(just run*)", "Bash(just run)"),
               ("Bash(just run*)", "Bash(just run --release)"), ("Bash", "Bash(x)"),
               ("Bash(*)", "Bash"), ("WebSearch", "WebSearch")]
        no = [("Bash(git status *)", "Bash(git *)"), ("WebFetch(domain:github.com)", "WebFetch(domain:docs.github.com)"),
              ("Read(*)", "Bash(ls)"), ("Bash(x *)", "Bash")]
        for g, s in yes:
            self.assertTrue(rm.covers(g, s), (g, s))
        for g, s in no:
            self.assertFalse(rm.covers(g, s), (g, s))

    def test_first_cover(self):
        self.assertEqual(rm.first_cover("Bash(just)", ["Bash(git *)", "Bash(just *)"]), "Bash(just *)")
        self.assertIsNone(rm.first_cover("Bash(ls)", ["Bash(git *)"]))

    def test_load_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            self.assertEqual(rm.load_permissions(p), {"allow": [], "ask": [], "deny": []})
            p.write_text(json.dumps({"permissions": {"allow": ["Bash(x *)"]}}))
            self.assertEqual(rm.load_permissions(p), {"allow": ["Bash(x *)"], "ask": [], "deny": []})
            p.write_text(json.dumps({"hooks": {}}))
            self.assertEqual(rm.load_permissions(p)["deny"], [])
            p.write_text("{bad")
            with self.assertRaisesRegex(ValueError, "s.json"):
                rm.load_permissions(p)


if __name__ == "__main__":
    unittest.main()
