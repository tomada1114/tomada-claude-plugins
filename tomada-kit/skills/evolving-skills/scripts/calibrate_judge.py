#!/usr/bin/env python3
"""Measure whether an LLM judge's PASS/FAIL verdicts agree with the user's own decisions.

A judge (a rubric applied by a model) may gate work only after it demonstrably agrees
with the user's past accept/reject decisions. This script never runs the judge: it
validates the labelled examples, writes a blind copy for the judge to read, scores the
verdicts that come back, and records a calibration file tied to the exact rubric and
examples by sha256, so editing either one invalidates the calibration. Pure and
deterministic apart from the `created` timestamp.

Files:
  examples.jsonl  {"id", "input", "output", "label": "accept"|"reject", "source"?, "note"?}
  verdicts.jsonl  {"id", "verdict": "PASS"|"FAIL", "reason"?}  (several votes per id allowed)

Usage:
  calibrate_judge.py check-examples --examples E [--min-total 20] [--min-per-label 5]
  calibrate_judge.py blind --examples E --out F
  calibrate_judge.py score --examples E --verdicts V --rubric R --out C
                     [--min-agreement 0.8] [--max-false-accept 0.1]
                     [--min-total 20] [--min-per-label 5]
  calibrate_judge.py status --rubric R --examples E --calibration C

Subcommands:
  check-examples  Validate every row and report whether the set is large enough.
  blind           Write only id, input and output, ordered by sha256 of the id.
  score           Majority vote per id (a tie is FAIL), agreement and error rates,
                  `trusted` or `advisory` with reasons; writes C and prints it.
  status          `trusted` only when C says trusted and both hashes still match.

All output is JSON on stdout; errors go to stderr.

Exit codes:
  0  ready (check-examples), written (blind), trusted (score, status)
  1  not ready (check-examples), advisory (score, status)
  3  bad invocation, unreadable or invalid file, missing or unknown verdict ids
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_NOT_READY = 1
EXIT_BAD = 3

LABELS = ("accept", "reject")
VERDICTS = ("PASS", "FAIL")
REQUIRED_FIELDS = ("id", "input", "output", "label")
BLIND_FIELDS = ("id", "input", "output")


class InputError(Exception):
    """Invalid invocation or file; reported on stderr with exit code 3."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: error: {message}\n")
        raise SystemExit(EXIT_BAD)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc.strerror or exc}") from exc


def read_jsonl(path: Path) -> list[tuple[int, object]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    rows = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append((lineno, json.loads(line)))
        except json.JSONDecodeError as exc:
            raise InputError(f"{path}:{lineno}: invalid JSON ({exc.msg})") from exc
    return rows


def load_examples(path: Path) -> list[dict]:
    """Read and validate examples; raise InputError listing every problem."""
    problems = []
    examples = []
    seen: set = set()
    for lineno, row in read_jsonl(path):
        where = f"{path}:{lineno}"
        if not isinstance(row, dict):
            problems.append(f"{where}: row is not a JSON object")
            continue
        missing = [f for f in REQUIRED_FIELDS if f not in row or row[f] is None]
        if missing:
            problems.append(f"{where}: missing {', '.join(missing)}")
            continue
        if not isinstance(row["id"], str) or not row["id"].strip():
            problems.append(f"{where}: id must be a non-empty string")
            continue
        if row["label"] not in LABELS:
            problems.append(f"{where}: label must be one of {', '.join(LABELS)}, "
                            f"got {row['label']!r}")
            continue
        if row["id"] in seen:
            problems.append(f"{where}: duplicate id {row['id']!r}")
            continue
        seen.add(row["id"])
        examples.append(row)
    if problems:
        raise InputError("invalid examples:\n  " + "\n  ".join(problems))
    return examples


def load_verdicts(path: Path) -> list[dict]:
    problems = []
    verdicts = []
    for lineno, row in read_jsonl(path):
        where = f"{path}:{lineno}"
        if not isinstance(row, dict):
            problems.append(f"{where}: row is not a JSON object")
        elif not isinstance(row.get("id"), str) or not row["id"].strip():
            problems.append(f"{where}: id must be a non-empty string")
        elif row.get("verdict") not in VERDICTS:
            problems.append(f"{where}: verdict must be PASS or FAIL, got {row.get('verdict')!r}")
        else:
            verdicts.append(row)
    if problems:
        raise InputError("invalid verdicts:\n  " + "\n  ".join(problems))
    return verdicts


def readiness(examples: list[dict], min_total: int, min_per_label: int) -> dict:
    counts = {label: sum(1 for e in examples if e["label"] == label) for label in LABELS}
    shortfall = {}
    if len(examples) < min_total:
        shortfall["total"] = min_total - len(examples)
    for label in LABELS:
        if counts[label] < min_per_label:
            shortfall[label] = min_per_label - counts[label]
    return {"total": len(examples), "counts": counts, "ready": not shortfall,
            "shortfall": shortfall}


def blind_order_key(example: dict) -> str:
    return hashlib.sha256(example["id"].encode("utf-8")).hexdigest()


def blind_rows(examples: list[dict]) -> list[dict]:
    """Only id, input and output survive, so no label-bearing field can leak."""
    return [{f: e[f] for f in BLIND_FIELDS} for e in sorted(examples, key=blind_order_key)]


def majority(votes: list[dict]) -> tuple[str, str]:
    """Return (verdict, reason); a tie counts as FAIL. The reason is the first
    non-empty reason among the votes that agree with the outcome."""
    passes = sum(1 for v in votes if v["verdict"] == "PASS")
    verdict = "PASS" if passes > len(votes) - passes else "FAIL"
    reason = next((str(v["reason"]) for v in votes
                   if v["verdict"] == verdict and v.get("reason")), "")
    return verdict, reason


def _rate(count: int, denominator: int) -> float | None:
    return round(count / denominator, 6) if denominator else None


def score(examples: list[dict], verdicts: list[dict], *, min_agreement: float,
          max_false_accept: float, min_total: int, min_per_label: int) -> dict:
    known = {e["id"] for e in examples}
    votes: dict = {}
    for v in verdicts:
        votes.setdefault(v["id"], []).append(v)
    missing = sorted(known - votes.keys())
    unknown = sorted(votes.keys() - known)
    if missing or unknown:
        parts = []
        if missing:
            parts.append("no verdict for: " + ", ".join(missing))
        if unknown:
            parts.append("verdict for unknown id: " + ", ".join(unknown))
        raise InputError("; ".join(parts))

    agree = false_accept = false_reject = 0
    n_accept = n_reject = 0
    disagreements = []
    for e in examples:
        verdict, reason = majority(votes[e["id"]])
        if e["label"] == "accept":
            n_accept += 1
            ok = verdict == "PASS"
            false_reject += 0 if ok else 1
        else:
            n_reject += 1
            ok = verdict == "FAIL"
            false_accept += 0 if ok else 1
        if ok:
            agree += 1
        else:
            disagreements.append({"id": e["id"], "label": e["label"], "verdict": verdict,
                                  "reason": reason})

    metrics = {
        "n": len(examples),
        "agreement": _rate(agree, len(examples)),
        "false_accept_rate": _rate(false_accept, n_reject),
        "false_reject_rate": _rate(false_reject, n_accept),
    }
    reasons = []
    if not readiness(examples, min_total, min_per_label)["ready"]:
        reasons.append("too-few-examples")
    # An undefined rate cannot show the judge is good enough, so it fails the bar.
    if metrics["agreement"] is None or metrics["agreement"] < min_agreement:
        reasons.append("low-agreement")
    if metrics["false_accept_rate"] is None or metrics["false_accept_rate"] > max_false_accept:
        reasons.append("high-false-accept")
    return {
        "status": "advisory" if reasons else "trusted",
        "reasons": reasons,
        "metrics": metrics,
        "disagreements": disagreements,
    }


def status_of(rubric: Path, examples: Path, calibration: Path) -> dict:
    if not calibration.exists():
        return {"status": "advisory", "reasons": ["missing"], "calibration": str(calibration)}
    try:
        recorded = json.loads(calibration.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"cannot read calibration {calibration}: {exc}") from exc
    if not isinstance(recorded, dict):
        raise InputError(f"calibration {calibration} is not a JSON object")
    reasons = []
    if recorded.get("rubric_sha256") != file_sha256(rubric):
        reasons.append("stale-rubric")
    if recorded.get("examples_sha256") != file_sha256(examples):
        reasons.append("stale-examples")
    if recorded.get("status") != "trusted":
        recorded_reasons = recorded.get("reasons") or []
        if not isinstance(recorded_reasons, list) or not recorded_reasons:
            recorded_reasons = [f"recorded-status:{recorded.get('status')}"]
        reasons.extend(str(r) for r in recorded_reasons if str(r) not in reasons)
    return {"status": "advisory" if reasons else "trusted", "reasons": reasons,
            "calibration": str(calibration)}


def _print(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _add_thresholds(p: argparse.ArgumentParser) -> None:
    p.add_argument("--min-total", type=int, default=20)
    p.add_argument("--min-per-label", type=int, default=5)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="calibrate_judge.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", parser_class=_Parser)
    sub.required = True

    p = sub.add_parser("check-examples", help="Validate examples and report readiness")
    p.add_argument("--examples", type=Path, required=True)
    _add_thresholds(p)

    p = sub.add_parser("blind", help="Write examples without labels for the judge")
    p.add_argument("--examples", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)

    p = sub.add_parser("score", help="Score verdicts against labels")
    p.add_argument("--examples", type=Path, required=True)
    p.add_argument("--verdicts", type=Path, required=True)
    p.add_argument("--rubric", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--min-agreement", type=float, default=0.8)
    p.add_argument("--max-false-accept", type=float, default=0.1)
    _add_thresholds(p)

    p = sub.add_parser("status", help="Is the recorded calibration still valid?")
    p.add_argument("--rubric", type=Path, required=True)
    p.add_argument("--examples", type=Path, required=True)
    p.add_argument("--calibration", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "check-examples":
            report = readiness(load_examples(args.examples), args.min_total, args.min_per_label)
            _print(report)
            return EXIT_OK if report["ready"] else EXIT_NOT_READY

        if args.command == "blind":
            rows = blind_rows(load_examples(args.examples))
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            _print({"out": str(args.out), "count": len(rows)})
            return EXIT_OK

        if args.command == "score":
            examples = load_examples(args.examples)
            verdicts = load_verdicts(args.verdicts)
            rubric_sha = file_sha256(args.rubric)
            result = score(examples, verdicts, min_agreement=args.min_agreement,
                           max_false_accept=args.max_false_accept,
                           min_total=args.min_total, min_per_label=args.min_per_label)
            calibration = {
                "status": result["status"],
                "reasons": result["reasons"],
                "metrics": result["metrics"],
                "thresholds": {
                    "min_agreement": args.min_agreement,
                    "max_false_accept": args.max_false_accept,
                    "min_total": args.min_total,
                    "min_per_label": args.min_per_label,
                },
                "rubric_sha256": rubric_sha,
                "examples_sha256": file_sha256(args.examples),
                "created": now_iso(),
                "disagreements": result["disagreements"],
            }
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(calibration, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
            _print(calibration)
            return EXIT_OK if result["status"] == "trusted" else EXIT_NOT_READY

        report = status_of(args.rubric, args.examples, args.calibration)
        _print(report)
        return EXIT_OK if report["status"] == "trusted" else EXIT_NOT_READY
    except InputError as exc:
        sys.stderr.write(f"calibrate_judge.py: error: {exc}\n")
        return EXIT_BAD


if __name__ == "__main__":
    sys.exit(main())
