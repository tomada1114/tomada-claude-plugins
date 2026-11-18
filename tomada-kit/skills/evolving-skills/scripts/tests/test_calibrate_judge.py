"""Tests for calibrate_judge.py. Every test works in its own temporary directory."""

from __future__ import annotations

import contextlib
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import calibrate_judge as cj  # noqa: E402


def example(i: int, label: str, **extra) -> dict:
    row = {"id": f"ex-{i:02d}", "input": f"ask {i}", "output": f"made {i}", "label": label}
    row.update(extra)
    return row


def balanced(n_accept: int = 10, n_reject: int = 10) -> list[dict]:
    rows = [example(i, "accept", source="session", note="liked") for i in range(n_accept)]
    rows += [example(n_accept + i, "reject") for i in range(n_reject)]
    return rows


def ideal_verdicts(examples: list[dict]) -> list[dict]:
    return [{"id": e["id"], "verdict": "PASS" if e["label"] == "accept" else "FAIL",
             "reason": "fits rubric"} for e in examples]


class CalibrateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.examples = self.dir / "examples.jsonl"
        self.verdicts = self.dir / "verdicts.jsonl"
        self.rubric = self.dir / "rubric.md"
        self.calibration = self.dir / "out" / "calibration.json"
        self.rubric.write_text("PASS when the output answers the question.\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    @staticmethod
    def write_jsonl(path: Path, rows) -> None:
        path.write_text("".join((r if isinstance(r, str) else json.dumps(r)) + "\n"
                                for r in rows))

    def run_cli(self, *argv: str):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cj.main(list(argv))
            except SystemExit as exc:
                code = exc.code
        text = out.getvalue()
        return code, (json.loads(text) if text.strip() else None), err.getvalue()

    def score(self, *extra):
        return self.run_cli("score", "--examples", str(self.examples), "--verdicts",
                            str(self.verdicts), "--rubric", str(self.rubric), "--out",
                            str(self.calibration), *extra)

    def status(self):
        return self.run_cli("status", "--rubric", str(self.rubric), "--examples",
                            str(self.examples), "--calibration", str(self.calibration))


class CheckExamplesTests(CalibrateTestCase):
    def check(self, *extra):
        return self.run_cli("check-examples", "--examples", str(self.examples), *extra)

    def test_ready(self):
        self.write_jsonl(self.examples, balanced(15, 5))
        code, report, _ = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(report, {"total": 20, "counts": {"accept": 15, "reject": 5},
                                  "ready": True, "shortfall": {}})

    def test_not_ready_reports_shortfall(self):
        self.write_jsonl(self.examples, balanced(14, 3))
        code, report, _ = self.check()
        self.assertEqual(code, 1)
        self.assertFalse(report["ready"])
        self.assertEqual(report["shortfall"], {"total": 3, "reject": 2})
        code, report, _ = self.check("--min-total", "10", "--min-per-label", "3")
        self.assertEqual(code, 0)

    def test_blank_lines_are_ignored(self):
        self.write_jsonl(self.examples, ["", json.dumps(example(1, "accept")), "   "])
        code, report, _ = self.check("--min-total", "1", "--min-per-label", "0")
        self.assertEqual((code, report["total"]), (0, 1))

    def test_invalid_rows(self):
        cases = {
            "missing field": [{"id": "a", "input": "i", "label": "accept"}],
            "null field": [{"id": "a", "input": "i", "output": None, "label": "accept"}],
            "bad label": [example(1, "maybe")],
            "uppercase label": [example(1, "ACCEPT")],
            "duplicate id": [example(1, "accept"), example(1, "reject")],
            "empty id": [{"id": " ", "input": "i", "output": "o", "label": "accept"}],
            "numeric id": [{"id": 3, "input": "i", "output": "o", "label": "accept"}],
            "not an object": ["[1, 2]"],
            "bad json": ["{oops"],
        }
        for name, rows in cases.items():
            with self.subTest(name):
                self.write_jsonl(self.examples, rows)
                code, report, err = self.check()
                self.assertEqual(code, 3)
                self.assertIsNone(report)
                self.assertIn("error", err)

    def test_all_problems_listed(self):
        self.write_jsonl(self.examples, [example(1, "maybe"), {"id": "x"}])
        code, _, err = self.check()
        self.assertEqual(code, 3)
        self.assertIn(":1:", err)
        self.assertIn(":2:", err)

    def test_missing_file(self):
        code, _, err = self.run_cli("check-examples", "--examples", str(self.dir / "nope"))
        self.assertEqual(code, 3)
        self.assertIn("cannot read", err)

    def test_bad_invocation_exits_3(self):
        code, _, _ = self.run_cli("check-examples")
        self.assertEqual(code, 3)
        code, _, _ = self.run_cli()
        self.assertEqual(code, 3)


class BlindTests(CalibrateTestCase):
    def blind(self, out: Path):
        return self.run_cli("blind", "--examples", str(self.examples), "--out", str(out))

    def test_blind_has_no_labels(self):
        rows = balanced(3, 3)
        rows[0]["accepted_by"] = "user"  # an unexpected field must not leak either
        self.write_jsonl(self.examples, rows)
        out = self.dir / "blind" / "blind.jsonl"
        code, report, _ = self.blind(out)
        self.assertEqual(code, 0)
        self.assertEqual(report["count"], 6)
        text = out.read_text()
        self.assertNotIn("accept", text)
        self.assertNotIn("reject", text)
        self.assertNotIn("liked", text)
        for line in text.splitlines():
            self.assertEqual(set(json.loads(line)), {"id", "input", "output"})

    def test_blind_order_is_stable_and_label_independent(self):
        rows = balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        out_a = self.dir / "a.jsonl"
        self.blind(out_a)
        shuffled = rows[:]
        random.Random(7).shuffle(shuffled)
        self.write_jsonl(self.examples, shuffled)
        out_b = self.dir / "b.jsonl"
        self.blind(out_b)
        self.assertEqual(out_a.read_bytes(), out_b.read_bytes())
        ids = [json.loads(line)["id"] for line in out_a.read_text().splitlines()]
        self.assertEqual(ids, sorted(ids, key=lambda i: cj.blind_order_key({"id": i})))
        labels = {e["id"]: e["label"] for e in rows}
        ordered_labels = [labels[i] for i in ids]
        self.assertNotEqual(ordered_labels, sorted(ordered_labels))
        self.assertNotEqual(ordered_labels, sorted(ordered_labels, reverse=True))

    def test_blind_rejects_invalid_examples(self):
        self.write_jsonl(self.examples, [example(1, "nope")])
        out = self.dir / "blind.jsonl"
        code, _, _ = self.blind(out)
        self.assertEqual(code, 3)
        self.assertFalse(out.exists())


class MajorityTests(unittest.TestCase):
    def test_majority_and_tie(self):
        self.assertEqual(cj.majority([{"verdict": "PASS"}])[0], "PASS")
        self.assertEqual(cj.majority([{"verdict": "PASS"}, {"verdict": "PASS"},
                                      {"verdict": "FAIL"}])[0], "PASS")
        self.assertEqual(cj.majority([{"verdict": "PASS"}, {"verdict": "FAIL"}])[0], "FAIL")
        self.assertEqual(cj.majority([{"verdict": "FAIL"}, {"verdict": "FAIL"},
                                      {"verdict": "PASS"}])[0], "FAIL")

    def test_reason_comes_from_a_winning_vote(self):
        votes = [{"verdict": "PASS", "reason": "good"}, {"verdict": "FAIL", "reason": ""},
                 {"verdict": "FAIL", "reason": "too long"}]
        self.assertEqual(cj.majority(votes), ("FAIL", "too long"))
        self.assertEqual(cj.majority([{"verdict": "FAIL"}]), ("FAIL", ""))


class ScoreTests(CalibrateTestCase):
    def test_trusted(self):
        rows = balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        self.write_jsonl(self.verdicts, ideal_verdicts(rows))
        code, result, _ = self.score()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "trusted")
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["metrics"], {"n": 20, "agreement": 1.0,
                                             "false_accept_rate": 0.0,
                                             "false_reject_rate": 0.0})
        self.assertEqual(result["thresholds"], {"min_agreement": 0.8, "max_false_accept": 0.1,
                                                "min_total": 20, "min_per_label": 5})
        self.assertEqual(result["disagreements"], [])
        self.assertEqual(set(result), {"status", "reasons", "metrics", "thresholds",
                                       "rubric_sha256", "examples_sha256", "created",
                                       "disagreements"})
        written = json.loads(self.calibration.read_text())
        self.assertEqual(written, result)
        self.assertEqual(written["rubric_sha256"], cj.file_sha256(self.rubric))

    def test_exactly_at_thresholds_is_trusted(self):
        rows = balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        verdicts = ideal_verdicts(rows)
        # 1 of 10 rejects passed (false accept 0.1) and 3 accepts failed: agreement 16/20.
        verdicts[10]["verdict"] = "PASS"
        for i in range(3):
            verdicts[i]["verdict"] = "FAIL"
        self.write_jsonl(self.verdicts, verdicts)
        code, result, _ = self.score()
        self.assertEqual(code, 0, result)
        self.assertEqual(result["metrics"]["agreement"], 0.8)
        self.assertEqual(result["metrics"]["false_accept_rate"], 0.1)
        self.assertEqual(result["metrics"]["false_reject_rate"], 0.3)
        self.assertEqual(len(result["disagreements"]), 4)
        d = next(d for d in result["disagreements"] if d["id"] == rows[10]["id"])
        self.assertEqual(d, {"id": rows[10]["id"], "label": "reject", "verdict": "PASS",
                             "reason": "fits rubric"})

    def test_majority_vote_and_tie_in_score(self):
        rows = balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        verdicts = ideal_verdicts(rows)
        accept_id, reject_id = rows[0]["id"], rows[10]["id"]
        # accept example: PASS, FAIL -> tie -> FAIL (a false reject)
        verdicts.append({"id": accept_id, "verdict": "FAIL"})
        # reject example: FAIL, PASS, PASS -> PASS (a false accept)
        verdicts += [{"id": reject_id, "verdict": "PASS"}, {"id": reject_id, "verdict": "PASS"}]
        self.write_jsonl(self.verdicts, verdicts)
        code, result, _ = self.score()
        self.assertEqual(code, 0)
        self.assertEqual({(d["id"], d["verdict"]) for d in result["disagreements"]},
                         {(accept_id, "FAIL"), (reject_id, "PASS")})
        self.assertEqual(result["metrics"]["agreement"], 0.9)

    def test_missing_and_unknown_ids(self):
        rows = balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        verdicts = ideal_verdicts(rows)[1:] + [{"id": "ghost", "verdict": "PASS"}]
        self.write_jsonl(self.verdicts, verdicts)
        code, result, err = self.score()
        self.assertEqual(code, 3)
        self.assertIsNone(result)
        self.assertIn(rows[0]["id"], err)
        self.assertIn("ghost", err)
        self.assertFalse(self.calibration.exists())

    def test_only_missing_ids(self):
        rows = balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        self.write_jsonl(self.verdicts, ideal_verdicts(rows)[:-1])
        code, _, err = self.score()
        self.assertEqual(code, 3)
        self.assertIn("no verdict for", err)
        self.assertNotIn("unknown", err)

    def test_invalid_verdicts(self):
        rows = balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        for bad in ([{"id": rows[0]["id"], "verdict": "pass"}], [{"verdict": "PASS"}], ["7"]):
            with self.subTest(bad=bad):
                self.write_jsonl(self.verdicts, bad)
                code, _, err = self.score()
                self.assertEqual(code, 3)
                self.assertIn("invalid verdicts", err)

    def test_missing_rubric(self):
        rows = balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        self.write_jsonl(self.verdicts, ideal_verdicts(rows))
        self.rubric.rename(self.dir / "moved.md")
        code, _, err = self.score()
        self.assertEqual(code, 3)
        self.assertIn("cannot read", err)
        self.assertFalse(self.calibration.exists())

    def test_advisory_too_few_examples(self):
        rows = balanced(10, 4)
        self.write_jsonl(self.examples, rows)
        self.write_jsonl(self.verdicts, ideal_verdicts(rows))
        code, result, _ = self.score()
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "advisory")
        self.assertEqual(result["reasons"], ["too-few-examples"])

    def test_advisory_low_agreement(self):
        rows = balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        verdicts = ideal_verdicts(rows)
        for i in range(5):  # 5 false rejects: agreement 0.75, false accept stays 0
            verdicts[i]["verdict"] = "FAIL"
        self.write_jsonl(self.verdicts, verdicts)
        code, result, _ = self.score()
        self.assertEqual(code, 1)
        self.assertEqual(result["reasons"], ["low-agreement"])
        self.assertEqual(result["metrics"]["false_reject_rate"], 0.5)

    def test_advisory_high_false_accept(self):
        rows = balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        verdicts = ideal_verdicts(rows)
        verdicts[10]["verdict"] = verdicts[11]["verdict"] = "PASS"  # 2/10 = 0.2
        self.write_jsonl(self.verdicts, verdicts)
        code, result, _ = self.score()
        self.assertEqual(code, 1)
        self.assertEqual(result["reasons"], ["high-false-accept"])
        self.assertEqual(result["metrics"]["agreement"], 0.9)

    def test_custom_thresholds(self):
        rows = balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        verdicts = ideal_verdicts(rows)
        verdicts[10]["verdict"] = verdicts[11]["verdict"] = "PASS"
        self.write_jsonl(self.verdicts, verdicts)
        code, result, _ = self.score("--max-false-accept", "0.2", "--min-agreement", "0.95")
        self.assertEqual(code, 1)
        self.assertEqual(result["reasons"], ["low-agreement"])

    def test_undefined_rates_never_trusted(self):
        rows = balanced(3, 0)
        self.write_jsonl(self.examples, rows)
        self.write_jsonl(self.verdicts, ideal_verdicts(rows))
        code, result, _ = self.score("--min-total", "1", "--min-per-label", "0")
        self.assertEqual(code, 1)
        self.assertIsNone(result["metrics"]["false_accept_rate"])
        self.assertEqual(result["reasons"], ["high-false-accept"])
        self.write_jsonl(self.examples, [])
        self.write_jsonl(self.verdicts, [])
        code, result, _ = self.score("--min-total", "0", "--min-per-label", "0")
        self.assertEqual(code, 1)
        self.assertEqual(result["metrics"]["n"], 0)
        self.assertEqual(result["reasons"], ["low-agreement", "high-false-accept"])


class StatusTests(CalibrateTestCase):
    def calibrate(self, rows=None, verdicts=None):
        rows = rows if rows is not None else balanced(10, 10)
        self.write_jsonl(self.examples, rows)
        self.write_jsonl(self.verdicts, verdicts if verdicts is not None else ideal_verdicts(rows))
        return self.score()

    def test_trusted(self):
        self.assertEqual(self.calibrate()[0], 0)
        code, report, _ = self.status()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "trusted")
        self.assertEqual(report["reasons"], [])

    def test_missing_calibration(self):
        self.write_jsonl(self.examples, balanced())
        code, report, _ = self.status()
        self.assertEqual(code, 1)
        self.assertEqual(report["reasons"], ["missing"])

    def test_stale_rubric(self):
        self.calibrate()
        self.rubric.write_text("PASS when the output is short.\n")
        code, report, _ = self.status()
        self.assertEqual(code, 1)
        self.assertEqual(report["reasons"], ["stale-rubric"])

    def test_stale_examples(self):
        self.calibrate()
        with self.examples.open("a") as fh:
            fh.write(json.dumps(example(99, "reject")) + "\n")
        code, report, _ = self.status()
        self.assertEqual(code, 1)
        self.assertEqual(report["reasons"], ["stale-examples"])

    def test_both_stale(self):
        self.calibrate()
        self.rubric.write_text("changed\n")
        self.examples.write_text("")
        code, report, _ = self.status()
        self.assertEqual(report["reasons"], ["stale-rubric", "stale-examples"])

    def test_recorded_advisory_reasons(self):
        rows = balanced(10, 10)
        verdicts = ideal_verdicts(rows)
        verdicts[10]["verdict"] = verdicts[11]["verdict"] = "PASS"
        self.assertEqual(self.calibrate(rows, verdicts)[0], 1)
        code, report, _ = self.status()
        self.assertEqual(code, 1)
        self.assertEqual(report["reasons"], ["high-false-accept"])

    def test_recorded_non_trusted_without_reasons(self):
        self.write_jsonl(self.examples, balanced())
        self.calibration.parent.mkdir(parents=True)
        self.calibration.write_text(json.dumps({
            "status": "weird", "rubric_sha256": cj.file_sha256(self.rubric),
            "examples_sha256": cj.file_sha256(self.examples)}))
        code, report, _ = self.status()
        self.assertEqual(code, 1)
        self.assertEqual(report["reasons"], ["recorded-status:weird"])

    def test_corrupt_calibration_exits_3(self):
        self.write_jsonl(self.examples, balanced())
        self.calibration.parent.mkdir(parents=True)
        self.calibration.write_text("{broken")
        self.assertEqual(self.status()[0], 3)
        self.calibration.write_text("[1]")
        code, _, err = self.status()
        self.assertEqual(code, 3)
        self.assertIn("not a JSON object", err)

    def test_missing_rubric_exits_3(self):
        self.calibrate()
        self.rubric.rename(self.dir / "gone.md")
        self.assertEqual(self.status()[0], 3)


class ScriptTests(unittest.TestCase):
    def test_runs_as_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "e.jsonl"
            path.write_text(json.dumps(example(1, "accept")) + "\n")
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "calibrate_judge.py"), "check-examples",
                 "--examples", str(path)], capture_output=True, text=True, env=env)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertFalse(json.loads(proc.stdout)["ready"])


if __name__ == "__main__":
    unittest.main()
