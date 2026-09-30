#!/usr/bin/env python3
"""Merge permission rules into a Claude Code settings file without dropping anything.

Rules are appended to `permissions.allow` / `ask` / `deny` in the given order, skipping
exact duplicates; every other key (hooks, env, plugins, existing rules) is kept as is.
Conflicts are reported, not resolved: an allow rule that is also denied or asked in the
file stays ineffective, because Claude Code evaluates deny, then ask, then allow.

Rules file: JSON object {"allow": [...], "ask": [...], "deny": [...]} (keys optional).
Exit codes: 0 merged (or nothing to change), 1 unreadable input, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

KINDS = ("allow", "ask", "deny")


@dataclass
class MergeReport:
    settings: str
    added: dict[str, list[str]] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)
    created: bool = False
    dry_run: bool = False


def merge(settings: dict, rules: dict) -> tuple[dict, dict[str, list[str]], list[str]]:
    perms = settings.setdefault("permissions", {})
    added: dict[str, list[str]] = {}
    for kind in KINDS:
        incoming = [r for r in rules.get(kind, []) if isinstance(r, str) and r.strip()]
        if not incoming:
            continue
        current = perms.setdefault(kind, [])
        new = [r for r in dict.fromkeys(incoming) if r not in current]
        current.extend(new)
        if new:
            added[kind] = new
    conflicts = []
    for rule in perms.get("allow", []):
        for other in ("deny", "ask"):
            if rule in perms.get(other, []):
                conflicts.append(f"{rule} is in allow and {other}; {other} wins")
    return settings, added, conflicts


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("settings", help="path to .claude/settings.json (created if missing)")
    ap.add_argument("--rules", required=True, help="JSON file with allow/ask/deny lists")
    ap.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args(argv)

    path = Path(args.settings)
    try:
        rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
        settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: cannot read input: {e}", file=sys.stderr)
        return 1
    if not isinstance(rules, dict) or not isinstance(settings, dict):
        print("error: both files must hold a JSON object", file=sys.stderr)
        return 2

    merged, added, conflicts = merge(settings, rules)
    report = MergeReport(settings=str(path), added=added, conflicts=conflicts,
                         created=not path.exists(), dry_run=args.dry_run)
    if added and not args.dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        for kind, items in added.items():
            print(f"+{len(items)} {kind}: " + ", ".join(items))
        for c in conflicts:
            print(f"conflict: {c}")
        if not added:
            print("nothing to change")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
