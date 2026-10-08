#!/usr/bin/env python3
"""Decide whether one Claude Code permission rule already covers another.

Used by detect_toolchain.py and merge_permissions.py to drop project rules that a
user-level rule already admits, and to spot project allow rules a user-level ask or
deny would stop anyway (Claude Code evaluates deny, then ask, then allow across every
settings file). Matching is textual: `*` matches any text, everything else is literal,
and a trailing ` *` also matches nothing, so `Bash(just *)` covers `Bash(just)`.

Library module; no command line and no exit codes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

KINDS = ("allow", "ask", "deny")
_RULE_RE = re.compile(r"^([^()]+)\((.*)\)$", re.DOTALL)


def split_rule(rule: str) -> tuple[str, str | None]:
    """`Bash(just *)` -> ("Bash", "just *"); bare `WebSearch` -> ("WebSearch", None)."""
    rule = rule.strip()
    m = _RULE_RE.match(rule)
    if not m:
        return rule, None
    spec = m.group(2)
    if spec.endswith(":*"):
        spec = spec[:-2] + " *"
    return m.group(1).strip(), spec


def rule_regex(spec: str) -> re.Pattern[str]:
    """Full-match pattern for a rule spec; a final ` *` may also match nothing."""
    tail = ""
    if spec.endswith(" *"):
        spec, tail = spec[:-2], "(?: .*)?"
    body = ".*".join(re.escape(part) for part in spec.split("*"))
    return re.compile(body + tail, re.DOTALL)


def covers(general: str, specific: str) -> bool:
    g_tool, g_spec = split_rule(general)
    s_tool, s_spec = split_rule(specific)
    if g_tool != s_tool:
        return False
    if g_spec is None:
        return True
    if s_spec is None:
        return g_spec == "*"
    return rule_regex(g_spec).fullmatch(s_spec) is not None


def first_cover(rule: str, rules: Iterable[str]) -> str | None:
    return next((r for r in rules if isinstance(r, str) and covers(r, rule)), None)


def load_permissions(path: Path | str) -> dict[str, list[str]]:
    """allow/ask/deny lists of a settings file; missing file or keys give empty lists."""
    path = Path(path)
    empty = {k: [] for k in KINDS}
    if not path.exists():
        return empty
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"{path}: {e}") from e
    perms = data.get("permissions") if isinstance(data, dict) else None
    if not isinstance(perms, dict):
        return empty
    return {k: [r for r in perms.get(k) or [] if isinstance(r, str)] for k in KINDS}
