#!/usr/bin/env python3
"""Ledger of evidence ("signals") that a skill fell short, and the rule for acting on it.

A signal is one observed shortfall of one skill: the user corrected or rejected its
output, its own self-check failed, a run hit friction, an instruction went unused, or
the user gave an explicit standing instruction. Signals are recorded as they happen;
this script then decides mechanically which ones have recurred enough to act on, so a
single incident never becomes a rule by itself and a rejected idea does not come back
without fresh evidence.

The ledger is append-only JSONL at <state>/signals.jsonl, where <state> defaults to
$AGENT_SKILL_STATE_DIR/evolving-skills (AGENT_SKILL_STATE_DIR defaults to
~/.local/state/agent-skills) and is replaced by --state-dir. Rows that share an `id`
merge field by field, later rows winning; a status change appends an update row that
carries `updated` instead of `ts`, so the creation time is kept.

Usage:
  signals.py add --skill S --kind K --key SLUG --summary TEXT [--evidence TEXT]
                 [--session ID] [--source self-check|user|gate|review] [--explicit]
  signals.py list [--skill S] [--status STATUS ...] [--key SLUG]
  signals.py promotable [--skill S] [--min-sessions 2]
  signals.py set --id ID [--id ID ...] --status STATUS [--commit SHA] [--run PATH]
                 [--note TEXT]
  signals.py stats [--skill S]

Every subcommand accepts --json (machine output) and --state-dir DIR.

Subcommands:
  add         Record one signal and print its id. Re-adding an identical
              (skill, key, session, summary) appends nothing and prints the existing id.
  list        Merged signals, oldest first, optionally filtered.
  promotable  Groups of open/deferred signals per (skill, key) that are ready to act
              on: any member is explicit, or members span --min-sessions distinct
              sessions. Signals in any other status never count.
  set         Append a status update for each id. `applied` requires --commit.
  stats       Counts per skill and status, and the number of promotable groups.

Kinds:    correction, self-check-fail, friction, unused-instruction, instruction
Statuses: open, deferred, applied, rejected, blocked, reverted

Exit codes:
  0  ok (including an empty result)
  3  bad invocation, invalid key, unknown id
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import secrets
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_BAD = 3

KINDS = ("correction", "self-check-fail", "friction", "unused-instruction", "instruction")
SOURCES = ("self-check", "user", "gate", "review")
STATUSES = ("open", "deferred", "applied", "rejected", "blocked", "reverted")
ACTIVE_STATUSES = ("open", "deferred")
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
LEDGER_NAME = "signals.jsonl"


class UsageError(Exception):
    """Bad invocation; reported on stderr with exit code 3."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: error: {message}\n")
        raise SystemExit(EXIT_BAD)


def default_state_dir() -> Path:
    base = os.environ.get("AGENT_SKILL_STATE_DIR", "~/.local/state/agent-skills")
    return Path(base).expanduser() / "evolving-skills"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ledger_path(state_dir: Path) -> Path:
    return state_dir / LEDGER_NAME


def parse_rows(text: str, source: str = "") -> list[dict]:
    """Parse ledger text. A line that is not a JSON object with an `id` is skipped
    with a warning on stderr (a torn write must not make the whole ledger unreadable)."""
    rows = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            row = None
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            sys.stderr.write(f"warning: skipping malformed ledger line {source}:{lineno}\n")
            continue
        rows.append(row)
    return rows


def merge(rows: list[dict]) -> list[dict]:
    """Merge rows by id, later rows winning per field; order is first appearance."""
    merged: "OrderedDict[str, dict]" = OrderedDict()
    for row in rows:
        merged.setdefault(row["id"], {}).update(row)
    return list(merged.values())


def read_ledger(state_dir: Path) -> list[dict]:
    path = ledger_path(state_dir)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_SH)
        try:
            text = fh.read()
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    return merge(parse_rows(text, str(path)))


def _session(signal: dict) -> str:
    value = signal.get("session") or ""
    return value.strip() if isinstance(value, str) else str(value).strip()


def new_id(existing: set) -> str:
    while True:
        candidate = "SIG-" + secrets.token_hex(4)
        if candidate not in existing:
            return candidate


def add_signal(state_dir: Path, *, skill: str, kind: str, key: str, summary: str,
               evidence: str = "", session: str = "", source: str = "",
               explicit: bool = False) -> tuple[str, bool]:
    """Append a signal unless an identical one exists. Returns (id, created)."""
    if not skill.strip():
        raise UsageError("--skill must not be empty")
    if kind not in KINDS:
        raise UsageError(f"--kind must be one of: {', '.join(KINDS)}")
    if not KEY_RE.match(key):
        raise UsageError(f"--key {key!r} must match {KEY_RE.pattern} (short kebab-case slug)")
    if not summary.strip():
        raise UsageError("--summary must not be empty")
    if source and source not in SOURCES:
        raise UsageError(f"--source must be one of: {', '.join(SOURCES)}")
    state_dir.mkdir(parents=True, exist_ok=True)
    path = ledger_path(state_dir)
    with path.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            fh.seek(0)
            signals = merge(parse_rows(fh.read(), str(path)))
            for sig in signals:
                if (sig.get("skill") == skill and sig.get("key") == key
                        and _session(sig) == session.strip()
                        and sig.get("summary") == summary):
                    return sig["id"], False
            sig_id = new_id({s["id"] for s in signals})
            row = {
                "id": sig_id,
                "ts": now_iso(),
                "skill": skill,
                "kind": kind,
                "key": key,
                "summary": summary,
                "evidence": evidence,
                "session": session,
                "source": source,
                "explicit": bool(explicit),
                "status": "open",
            }
            fh.seek(0, os.SEEK_END)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    return sig_id, True


def set_status(state_dir: Path, ids: list[str], status: str, *, commit: str | None = None,
               run: str | None = None, note: str | None = None) -> list[dict]:
    """Append one update row per id. Validates everything before writing anything."""
    if status not in STATUSES:
        raise UsageError(f"--status must be one of: {', '.join(STATUSES)}")
    if status == "applied" and not commit:
        raise UsageError("--status applied requires --commit")
    path = ledger_path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            fh.seek(0)
            known = {s["id"] for s in merge(parse_rows(fh.read(), str(path)))}
            unknown = [i for i in ids if i not in known]
            if unknown:
                raise UsageError(f"unknown id: {', '.join(unknown)}")
            stamp = now_iso()
            updates = []
            for sig_id in dict.fromkeys(ids):
                row = {"id": sig_id, "updated": stamp, "status": status}
                if commit:
                    row["commit"] = commit
                if run:
                    row["run"] = run
                if note:
                    row["note"] = note
                updates.append(row)
            fh.seek(0, os.SEEK_END)
            for row in updates:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    return updates


def filter_signals(signals: list[dict], *, skill: str | None = None,
                   statuses: list[str] | None = None, key: str | None = None) -> list[dict]:
    out = []
    for sig in signals:
        if skill and sig.get("skill") != skill:
            continue
        if statuses and sig.get("status") not in statuses:
            continue
        if key and sig.get("key") != key:
            continue
        out.append(sig)
    return out


def promotable_groups(signals: list[dict], *, skill: str | None = None,
                      min_sessions: int = 2) -> list[dict]:
    groups: "OrderedDict[tuple, list[dict]]" = OrderedDict()
    for sig in filter_signals(signals, skill=skill, statuses=list(ACTIVE_STATUSES)):
        groups.setdefault((sig.get("skill"), sig.get("key")), []).append(sig)
    result = []
    for (g_skill, g_key), members in groups.items():
        sessions = {_session(m) for m in members} - {""}
        explicit = any(m.get("explicit") is True for m in members)
        if not explicit and len(sessions) < min_sessions:
            continue
        result.append({
            "skill": g_skill,
            "key": g_key,
            "signals": [m["id"] for m in members],
            "sessions": len(sessions),
            "explicit": explicit,
            "kinds": sorted({m.get("kind") for m in members if m.get("kind")}),
            "summaries": [m.get("summary", "") for m in members],
        })
    result.sort(key=lambda g: (str(g["skill"]), str(g["key"])))
    return result


def compute_stats(signals: list[dict], *, skill: str | None = None) -> dict:
    per_skill: dict = {}
    for sig in filter_signals(signals, skill=skill):
        counts = per_skill.setdefault(sig.get("skill"), {})
        status = sig.get("status", "open")
        counts[status] = counts.get(status, 0) + 1
    return {
        "total": sum(sum(c.values()) for c in per_skill.values()),
        "skills": {k: dict(sorted(v.items())) for k, v in sorted(per_skill.items())},
        "promotable_groups": len(promotable_groups(signals, skill=skill)),
    }


def _emit(as_json: bool, payload, text: str) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text)


def _format_signal(sig: dict) -> str:
    flag = " explicit" if sig.get("explicit") else ""
    return (f"{sig['id']}  {sig.get('status', '')}  {sig.get('skill', '')}/{sig.get('key', '')}"
            f"  [{sig.get('kind', '')}{flag}]  session={sig.get('session') or '-'}  "
            f"{sig.get('summary', '')}")


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="Emit JSON")
    common.add_argument("--state-dir", type=Path, default=None,
                        help="State directory holding signals.jsonl")
    parser = _Parser(prog="signals.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", parser_class=_Parser)
    sub.required = True

    p = sub.add_parser("add", parents=[common], help="Record one signal")
    p.add_argument("--skill", required=True)
    p.add_argument("--kind", required=True, choices=KINDS)
    p.add_argument("--key", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--evidence", default="")
    p.add_argument("--session", default="")
    p.add_argument("--source", choices=SOURCES, default="")
    p.add_argument("--explicit", action="store_true")

    p = sub.add_parser("list", parents=[common], help="List merged signals")
    p.add_argument("--skill")
    p.add_argument("--status", nargs="+", choices=STATUSES, action="extend")
    p.add_argument("--key")

    p = sub.add_parser("promotable", parents=[common], help="Groups ready to act on")
    p.add_argument("--skill")
    p.add_argument("--min-sessions", type=int, default=2)

    p = sub.add_parser("set", parents=[common], help="Change the status of signals")
    p.add_argument("--id", dest="ids", action="append", required=True)
    p.add_argument("--status", required=True, choices=STATUSES)
    p.add_argument("--commit")
    p.add_argument("--run")
    p.add_argument("--note")

    p = sub.add_parser("stats", parents=[common], help="Counts per skill and status")
    p.add_argument("--skill")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state_dir = args.state_dir.expanduser() if args.state_dir else default_state_dir()
    try:
        if args.command == "add":
            sig_id, created = add_signal(
                state_dir, skill=args.skill, kind=args.kind, key=args.key,
                summary=args.summary, evidence=args.evidence, session=args.session,
                source=args.source, explicit=args.explicit)
            _emit(args.json, {"id": sig_id, "created": created}, sig_id)
        elif args.command == "list":
            signals = filter_signals(read_ledger(state_dir), skill=args.skill,
                                     statuses=args.status, key=args.key)
            _emit(args.json, signals,
                  "\n".join(_format_signal(s) for s in signals) or "(no signals)")
        elif args.command == "promotable":
            if args.min_sessions < 1:
                raise UsageError("--min-sessions must be at least 1")
            groups = promotable_groups(read_ledger(state_dir), skill=args.skill,
                                       min_sessions=args.min_sessions)
            lines = [f"{g['skill']}/{g['key']}  sessions={g['sessions']}"
                     f"{'  explicit' if g['explicit'] else ''}  {' '.join(g['signals'])}"
                     for g in groups]
            _emit(args.json, groups, "\n".join(lines) or "(nothing promotable)")
        elif args.command == "set":
            updates = set_status(state_dir, args.ids, args.status, commit=args.commit,
                                 run=args.run, note=args.note)
            _emit(args.json, updates,
                  "\n".join(f"{u['id']} -> {u['status']}" for u in updates))
        else:  # stats
            stats = compute_stats(read_ledger(state_dir), skill=args.skill)
            lines = [f"{skill}: " + ", ".join(f"{k}={v}" for k, v in counts.items())
                     for skill, counts in stats["skills"].items()]
            lines.append(f"total={stats['total']}  promotable_groups={stats['promotable_groups']}")
            _emit(args.json, stats, "\n".join(lines))
    except UsageError as exc:
        sys.stderr.write(f"signals.py: error: {exc}\n")
        return EXIT_BAD
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
