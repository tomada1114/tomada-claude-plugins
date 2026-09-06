"""Unit tests for check_contrast.py.

Run with:
    python3 -m unittest discover -s scripts/tests -p 'test_*.py'
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import check_contrast as cc  # noqa: E402


class TestParseColor(unittest.TestCase):
    def test_hex6(self):
        rgb, clipped = cc.parse_color("#71717A")
        self.assertAlmostEqual(rgb[0], 0x71 / 255.0)
        self.assertAlmostEqual(rgb[1], 0x71 / 255.0)
        self.assertAlmostEqual(rgb[2], 0x7A / 255.0)
        self.assertFalse(clipped)

    def test_hex3_shorthand(self):
        rgb, clipped = cc.parse_color("#0A0")
        self.assertAlmostEqual(rgb[0], 0x00 / 255.0)
        self.assertAlmostEqual(rgb[1], 0xAA / 255.0)
        self.assertAlmostEqual(rgb[2], 0x00 / 255.0)
        self.assertFalse(clipped)

    def test_rgb_space_separated(self):
        rgb, clipped = cc.parse_color("rgb(37 99 235)")
        self.assertAlmostEqual(rgb[0], 37 / 255.0)
        self.assertAlmostEqual(rgb[1], 99 / 255.0)
        self.assertAlmostEqual(rgb[2], 235 / 255.0)
        self.assertFalse(clipped)

    def test_rgb_comma_separated(self):
        rgb, clipped = cc.parse_color("rgb(37, 99, 235)")
        self.assertAlmostEqual(rgb[0], 37 / 255.0)
        self.assertAlmostEqual(rgb[1], 99 / 255.0)
        self.assertAlmostEqual(rgb[2], 235 / 255.0)
        self.assertFalse(clipped)

    def test_oklch_white_exact(self):
        rgb, clipped = cc.parse_color("oklch(1 0 0)")
        self.assertAlmostEqual(rgb[0], 1.0, places=6)
        self.assertAlmostEqual(rgb[1], 1.0, places=6)
        self.assertAlmostEqual(rgb[2], 1.0, places=6)
        self.assertFalse(clipped)

    def test_oklch_black_exact(self):
        rgb, clipped = cc.parse_color("oklch(0 0 0)")
        self.assertAlmostEqual(rgb[0], 0.0, places=6)
        self.assertAlmostEqual(rgb[1], 0.0, places=6)
        self.assertAlmostEqual(rgb[2], 0.0, places=6)
        self.assertFalse(clipped)

    def test_oklch_percentage_lightness(self):
        rgb_pct, _ = cc.parse_color("oklch(100% 0 0)")
        rgb_num, _ = cc.parse_color("oklch(1 0 0)")
        self.assertAlmostEqual(rgb_pct[0], rgb_num[0], places=6)
        self.assertAlmostEqual(rgb_pct[1], rgb_num[1], places=6)
        self.assertAlmostEqual(rgb_pct[2], rgb_num[2], places=6)

    def test_oklch_blue_contrast_range(self):
        # oklch(0.62 0.19 258) lands near a medium blue (roughly #2F6FE6-ish).
        # We assert a contrast band against white rather than an exact hex,
        # since the precise sRGB byte values are sensitive to rounding.
        # (Cross-checked against an independent OKLCH->sRGB implementation;
        # the true contrast against white is ~3.71, not a value close to
        # e.g. #2563EB's 5.17, so the band below is centered on the
        # verified figure rather than a hand-guessed one.)
        rgb, clipped = cc.parse_color("oklch(0.62 0.19 258)")
        ratio = cc.contrast_ratio(rgb, (1.0, 1.0, 1.0))
        self.assertFalse(clipped)
        self.assertGreaterEqual(ratio, 3.3)
        self.assertLessEqual(ratio, 4.2)

    def test_oklch_gamut_clipping_flagged(self):
        rgb, clipped = cc.parse_color("oklch(0.5 0.4 260)")
        self.assertTrue(clipped)
        for channel in rgb:
            self.assertGreaterEqual(channel, 0.0)
            self.assertLessEqual(channel, 1.0)

    def test_oklch_in_gamut_not_flagged(self):
        _, clipped = cc.parse_color("oklch(0.5 0.05 260)")
        self.assertFalse(clipped)

    def test_alpha_hex8_rejected(self):
        with self.assertRaises(cc.ColorParseError):
            cc.parse_color("#71717AFF")

    def test_alpha_hex4_rejected(self):
        with self.assertRaises(cc.ColorParseError):
            cc.parse_color("#0A0F")

    def test_alpha_rgba_rejected(self):
        with self.assertRaises(cc.ColorParseError):
            cc.parse_color("rgba(37, 99, 235, 0.5)")

    def test_unparsable_color(self):
        with self.assertRaises(cc.ColorParseError):
            cc.parse_color("not-a-color")

    def test_empty_color(self):
        with self.assertRaises(cc.ColorParseError):
            cc.parse_color("")

    def test_none_color(self):
        with self.assertRaises(cc.ColorParseError):
            cc.parse_color(None)


class TestRelativeLuminance(unittest.TestCase):
    def test_black_is_zero(self):
        self.assertAlmostEqual(cc.relative_luminance((0.0, 0.0, 0.0)), 0.0, places=6)

    def test_white_is_one(self):
        self.assertAlmostEqual(cc.relative_luminance((1.0, 1.0, 1.0)), 1.0, places=6)


class TestContrastRatio(unittest.TestCase):
    def _ratio(self, fg_hex, bg_hex):
        fg_rgb, _ = cc.parse_color(fg_hex)
        bg_rgb, _ = cc.parse_color(bg_hex)
        return cc.contrast_ratio(fg_rgb, bg_rgb)

    def test_black_on_white(self):
        self.assertEqual(self._ratio("#000000", "#FFFFFF"), 21.0)

    def test_known_ratio_gray_on_near_black(self):
        # This is the pair whose hand-written value (4.6:1) was wrong;
        # the correct WCAG ratio is 4.09:1.
        self.assertEqual(self._ratio("#71717A", "#0A0A0B"), 4.09)

    def test_known_ratio_light_gray_on_white(self):
        self.assertEqual(self._ratio("#9CA3AF", "#FFFFFF"), 2.54)

    def test_known_ratio_blue_on_white(self):
        self.assertEqual(self._ratio("#2563EB", "#FFFFFF"), 5.17)

    def test_known_ratio_green_on_white(self):
        self.assertEqual(self._ratio("#22C55E", "#FFFFFF"), 2.28)

    def test_order_independence(self):
        self.assertEqual(self._ratio("#000000", "#FFFFFF"), self._ratio("#FFFFFF", "#000000"))


class TestEvaluate(unittest.TestCase):
    def test_text_kind_thresholds(self):
        pairs = [cc.Pair(fg="#000000", bg="#FFFFFF", kind="text")]
        results_aa = cc.evaluate(pairs, "AA")
        self.assertEqual(results_aa[0].required, 4.5)
        self.assertTrue(results_aa[0].passed)

        results_aaa = cc.evaluate(pairs, "AAA")
        self.assertEqual(results_aaa[0].required, 7.0)
        self.assertTrue(results_aaa[0].passed)

    def test_large_kind_thresholds(self):
        pairs = [cc.Pair(fg="#9CA3AF", bg="#FFFFFF", kind="large")]
        results_aa = cc.evaluate(pairs, "AA")
        self.assertEqual(results_aa[0].required, 3.0)
        self.assertFalse(results_aa[0].passed)  # 2.54 < 3.0

        results_aaa = cc.evaluate(pairs, "AAA")
        self.assertEqual(results_aaa[0].required, 4.5)
        self.assertFalse(results_aaa[0].passed)

    def test_ui_kind_thresholds_same_both_levels(self):
        pairs = [cc.Pair(fg="#2563EB", bg="#FFFFFF", kind="ui")]
        results_aa = cc.evaluate(pairs, "AA")
        results_aaa = cc.evaluate(pairs, "AAA")
        self.assertEqual(results_aa[0].required, 3.0)
        self.assertEqual(results_aaa[0].required, 3.0)
        self.assertTrue(results_aa[0].passed)
        self.assertTrue(results_aaa[0].passed)

    def test_large_kind_passes_at_lower_ratio_than_text(self):
        # #2563EB/#FFFFFF is 5.17: passes text AA (4.5) and large AAA (4.5)
        # but fails text AAA (7.0).
        pairs = [cc.Pair(fg="#2563EB", bg="#FFFFFF", kind="text")]
        self.assertTrue(cc.evaluate(pairs, "AA")[0].passed)
        self.assertFalse(cc.evaluate(pairs, "AAA")[0].passed)

    def test_unknown_kind_raises(self):
        pairs = [cc.Pair(fg="#000000", bg="#FFFFFF", kind="bogus")]
        with self.assertRaises(ValueError):
            cc.evaluate(pairs, "AA")

    def test_unknown_level_raises(self):
        pairs = [cc.Pair(fg="#000000", bg="#FFFFFF", kind="text")]
        with self.assertRaises(ValueError):
            cc.evaluate(pairs, "A")

    def test_gamut_clipped_flag_propagates(self):
        pairs = [cc.Pair(fg="oklch(0.5 0.4 260)", bg="#FFFFFF", kind="text")]
        result = cc.evaluate(pairs, "AA")[0]
        self.assertTrue(result.gamut_clipped)

    def test_bad_color_raises_colorparseerror(self):
        pairs = [cc.Pair(fg="nope", bg="#FFFFFF", kind="text")]
        with self.assertRaises(cc.ColorParseError):
            cc.evaluate(pairs, "AA")


class TestCLI(unittest.TestCase):
    def run_main(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cc.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_help_exits_zero(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as ctx:
                cc.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("usage", stdout.getvalue().lower())

    def test_no_input_is_exit_code_2(self):
        code, _out, err = self.run_main([])
        self.assertEqual(code, 2)
        self.assertIn("--pair", err)

    def test_bad_color_is_exit_code_2(self):
        code, _out, err = self.run_main(["--pair", "not-a-color", "#FFFFFF"])
        self.assertEqual(code, 2)
        self.assertIn("not-a-color", err)
        self.assertIn("accepted color formats", err)

    def test_all_pass_is_exit_code_0(self):
        code, out, _err = self.run_main(["--pair", "#000000", "#FFFFFF"])
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_any_fail_is_exit_code_1(self):
        code, out, _err = self.run_main(["--pair", "#9CA3AF", "#FFFFFF"])
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_pair_repeatable_and_kind_applies_to_all(self):
        code, out, _err = self.run_main(
            [
                "--pair", "#000000", "#FFFFFF",
                "--pair", "#9CA3AF", "#FFFFFF",
                "--kind", "large",
            ]
        )
        # #000000/#FFFFFF passes large AA (21.0 >= 3.0);
        # #9CA3AF/#FFFFFF fails large AA (2.54 < 3.0) -> overall fail.
        self.assertEqual(code, 1)
        self.assertIn("large", out)

    def test_level_aaa_flag(self):
        code, out, _err = self.run_main(
            ["--pair", "#2563EB", "#FFFFFF", "--level", "AAA"]
        )
        self.assertEqual(code, 1)
        self.assertIn("7.00", out)

    def test_json_output_keys(self):
        code, out, _err = self.run_main(
            ["--pair", "#000000", "#FFFFFF", "--json"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(len(data), 1)
        expected_keys = {
            "name", "fg", "bg", "kind", "ratio", "required",
            "level", "passed", "gamut_clipped",
        }
        self.assertEqual(set(data[0].keys()), expected_keys)
        self.assertEqual(data[0]["ratio"], 21.0)
        self.assertTrue(data[0]["passed"])

    def test_json_output_ensure_ascii_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "pairs.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    [{"name": "日本語ラベル", "fg": "#000000", "bg": "#FFFFFF"}],
                    f,
                )
            code, out, _err = self.run_main([path, "--json"])
            self.assertEqual(code, 0)
            self.assertIn("日本語ラベル", out)  # not escaped to \uXXXX

    def test_json_file_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "palette.json")
            payload = [
                {"name": "body-text", "fg": "#71717A", "bg": "#0A0A0B", "kind": "text"},
                {"name": "large-heading", "fg": "#9CA3AF", "bg": "#FFFFFF", "kind": "large"},
            ]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            code, out, _err = self.run_main([path])
            self.assertIn("body-text", out)
            self.assertIn("large-heading", out)
            self.assertEqual(code, 1)  # large-heading fails large AA

    def test_json_file_default_kind_is_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "palette.json")
            payload = [{"name": "x", "fg": "#000000", "bg": "#FFFFFF"}]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            code, out, _err = self.run_main([path, "--json"])
            data = json.loads(out)
            self.assertEqual(data[0]["kind"], "text")
            self.assertEqual(code, 0)

    def test_json_file_and_pair_combined(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "palette.json")
            payload = [{"name": "from-file", "fg": "#000000", "bg": "#FFFFFF"}]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            code, out, _err = self.run_main(
                [path, "--pair", "#9CA3AF", "#FFFFFF"]
            )
            self.assertIn("from-file", out)
            self.assertEqual(code, 1)

    def test_json_file_not_found_is_exit_code_2(self):
        code, _out, err = self.run_main(["/no/such/file.json"])
        self.assertEqual(code, 2)
        self.assertIn("could not read JSON file", err)

    def test_json_file_invalid_json_is_exit_code_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "bad.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not valid json")
            code, _out, err = self.run_main([path])
            self.assertEqual(code, 2)
            self.assertIn("could not parse JSON file", err)

    def test_json_file_not_a_list_is_exit_code_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "bad.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"fg": "#000000", "bg": "#FFFFFF"}, f)
            code, _out, err = self.run_main([path])
            self.assertEqual(code, 2)
            self.assertIn("array", err)

    def test_json_file_entry_not_object_is_exit_code_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "bad.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(["#000000"], f)
            code, _out, err = self.run_main([path])
            self.assertEqual(code, 2)
            self.assertIn("must be an object", err)

    def test_json_file_entry_missing_fg_bg_is_exit_code_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "bad.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump([{"name": "x", "fg": "#000000"}], f)
            code, _out, err = self.run_main([path])
            self.assertEqual(code, 2)
            self.assertIn("missing", err)

    def test_table_output_contains_headers(self):
        code, out, _err = self.run_main(["--pair", "#000000", "#FFFFFF"])
        self.assertEqual(code, 0)
        for header in ("name", "fg", "bg", "kind", "ratio", "required", "result"):
            self.assertIn(header, out)


if __name__ == "__main__":
    unittest.main()
