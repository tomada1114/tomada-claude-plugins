#!/usr/bin/env python3
"""Merge permission rules into a project's .claude/settings.local.json without dropping anything.

Rules are appended to `permissions.allow` / `ask` / `deny` in the given order, skipping
exact duplicates; every other key (hooks, env, plugins, existing rules) is kept as is.
Conflicts are reported, not resolved: an allow rule that is also denied or asked in the
file stays ineffective, because Claude Code evaluates deny, then ask, then allow.

With --global, an incoming allow rule a user-level allow already covers is skipped
(`redundant`), and one a user-level ask/deny covers is skipped too (`shadowed`): a
project allow never beats a global ask or deny. ask and deny rules always merge.

Rules file: JSON object {"allow": [...], "ask": [...], "deny": [...], "hooks": {...}}
(keys optional). Each hooks event's entries are appended unless an equal entry exists.
Exit codes: 0 merged (or nothing to change), 1 unreadable input, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

from rule_match import first_cover, load_permissions

KINDS = ("allow", "ask", "deny")


@dataclass
class MergeReport:
    settings: str
    added: dict[str, list[str]] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)
    redundant: list[dict[str, str]] = field(default_factory=list)
    shadowed: list[dict[str, str]] = field(default_factory=list)
    hooks_added: dict[str, int] = field(default_factory=dict)
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


def filter_global(rules: dict, glob: dict[str, list[str]]) -> tuple[dict, list[dict[str, str]], list[dict[str, str]]]:
    """Drop incoming allow rules a global rule covers; return (rules, redundant, shadowed)."""
    redundant, shadowed, keep = [], [], []
    for rule in rules.get("allow", []):
        if not isinstance(rule, str):
            continue
        if by := first_cover(rule, glob["deny"]) or first_cover(rule, glob["ask"]):
            shadowed.append({"rule": rule, "by": by, "kind": "deny" if by in glob["deny"] else "ask"})
        elif by := first_cover(rule, glob["allow"]):
            redundant.append({"rule": rule, "by": by})
        else:
            keep.append(rule)
    return {**rules, "allow": keep}, redundant, shadowed


def merge_hooks(settings: dict, hooks: dict) -> dict[str, int]:
    added: dict[str, int] = {}
    if not isinstance(hooks, dict):
        return added
    for event, entries in hooks.items():
        if not isinstance(entries, list) or not entries:
            continue
        current = settings.setdefault("hooks", {}).setdefault(event, [])
        seen = {json.dumps(e, sort_keys=True) for e in current}
        count = 0
        for entry in entries:
            key = json.dumps(entry, sort_keys=True)
            if key not in seen:
                seen.add(key)
                current.append(entry)
                count += 1
        if count:
            added[event] = count
    return added


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("settings", help="path to the project's .claude/settings.local.json (created if missing)")
    ap.add_argument("--rules", required=True, help="JSON file with allow/ask/deny lists")
    ap.add_argument("--global", dest="global_path",
                    help="user-level settings; allow rules it already covers or stops are skipped")
    ap.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args(argv)

    path = Path(args.settings)
    try:
        rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
        settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        glob = load_permissions(args.global_path) if args.global_path else None
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"error: cannot read input: {e}", file=sys.stderr)
        return 1
    if not isinstance(rules, dict) or not isinstance(settings, dict):
        print("error: both files must hold a JSON object", file=sys.stderr)
        return 2

    redundant: list[dict[str, str]] = []
    shadowed: list[dict[str, str]] = []
    if glob is not None:
        rules, redundant, shadowed = filter_global(rules, glob)
    merged, added, conflicts = merge(settings, rules)
    hooks_added = merge_hooks(merged, rules.get("hooks") or {})
    report = MergeReport(settings=str(path), added=added, conflicts=conflicts, redundant=redundant,
                         shadowed=shadowed, hooks_added=hooks_added,
                         created=not path.exists(), dry_run=args.dry_run)
    if (added or hooks_added) and not args.dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        for kind, items in added.items():
            print(f"+{len(items)} {kind}: " + ", ".join(items))
        for event, n in hooks_added.items():
            print(f"+{n} hooks.{event}")
        for r in redundant:
            print(f"redundant: {r['rule']} (global allow {r['by']})")
        for r in shadowed:
            print(f"shadowed: {r['rule']} (global {r['kind']} {r['by']})")
        for c in conflicts:
            print(f"conflict: {c}")
        if not added and not hooks_added:
            print("nothing to change")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
