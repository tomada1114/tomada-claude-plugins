#!/usr/bin/env python3
"""audit_skill.py — Deeper review for an existing Claude Code skill.

Wraps validate_skill.py and adds editorial / structural checks:

  A001  "When to use" / "trigger" sections leaked into SKILL.md body
        (triggers belong in the description field, not the body).
  A002  Duplicate top-level (## / ###) headings.
  A003  references/*.md files that exist on disk but are NOT linked from
        SKILL.md (orphaned references).
  A004  references/*.md files referenced from SKILL.md but missing on disk
        (already covered by validate's E041, surfaced here as a hint).
  A005  Frontmatter description still uses pure auto-trigger framing
        ("Use PROACTIVELY when ...") despite being command-invoked.
        This is a hint, not an error — the user may legitimately want both.

Usage:
    audit_skill.py <skill-path> [--json] [--report <path>]

If --report is given, a human-readable Markdown report is written to that
path in addition to stdout. Otherwise only stdout is produced.

Exit codes:
    0 = no errors (warnings/hints allowed)
    1 = at least one error
    2 = bad invocation
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

# Reuse validate_skill in-process so we don't depend on subprocess wiring.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import validate_skill  # type: ignore  # noqa: E402

HEADING_RE = re.compile(r"^(#{2,6})\s+(.+?)\s*$", re.MULTILINE)
WHEN_TO_USE_RE = re.compile(
    r"^#{2,6}\s+.*\b(when to use|when this skill (?:triggers|activates)|trigger(?:s)?)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
PROACTIVE_RE = re.compile(r"\bUse PROACTIVELY\b", re.IGNORECASE)


def audit(skill_path: Path) -> tuple[validate_skill.Report, list[validate_skill.Finding]]:
    report = validate_skill.validate(skill_path)
    extras: list[validate_skill.Finding] = []

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return report, extras

    text = skill_md.read_text(encoding="utf-8")
    fields, body_start = validate_skill.parse_frontmatter(text)
    body_lines = text.splitlines()[body_start:]
    body = "\n".join(body_lines)

    # A001: trigger sections leaked into body
    for match in WHEN_TO_USE_RE.finditer(body):
        extras.append(
            validate_skill.Finding(
                "warning",
                "A001",
                f"trigger-style heading found in body: '{match.group(0).strip()}' "
                f"— move to description field",
                "SKILL.md body",
            )
        )

    # A002: duplicate headings
    seen: dict[str, int] = {}
    for m in HEADING_RE.finditer(body):
        key = m.group(2).strip().lower()
        seen[key] = seen.get(key, 0) + 1
    for heading, count in seen.items():
        if count > 1:
            extras.append(
                validate_skill.Finding(
                    "warning",
                    "A002",
                    f"duplicate heading '{heading}' appears {count} times",
                    "SKILL.md body",
                )
            )

    # A003 / A004: references/ orphan and missing detection
    refs_dir = skill_path / "references"
    linked_targets = {
        Path(t).as_posix()
        for t in validate_skill.collect_link_targets(body)
        if not t.startswith(("http://", "https://", "mailto:", "/"))
    }
    if refs_dir.exists():
        for md in sorted(refs_dir.glob("*.md")):
            rel = md.relative_to(skill_path).as_posix()
            if rel not in linked_targets:
                extras.append(
                    validate_skill.Finding(
                        "warning",
                        "A003",
                        f"orphan reference file (exists but not linked from SKILL.md): {rel}",
                        rel,
                    )
                )

    # A005: still pure auto-trigger framing
    description = fields.get("description", "")
    if PROACTIVE_RE.search(description):
        extras.append(
            validate_skill.Finding(
                "info",
                "A005",
                "description uses 'Use PROACTIVELY' framing — review whether trigger keywords "
                "are still needed under command-based invocation",
                "SKILL.md frontmatter",
            )
        )

    return report, extras


def render_markdown(skill_path: Path, report: validate_skill.Report, extras: list[validate_skill.Finding]) -> str:
    lines = [f"# Audit Report: {skill_path.name}", ""]
    lines.append(f"- **Path:** `{report.skill_path}`")
    lines.append(f"- **name:** `{report.skill_name or '(missing)'}`")
    lines.append(f"- **description length:** {report.description_length} chars")
    lines.append(f"- **body lines:** {report.body_lines}")
    lines.append("")

    all_findings = list(report.findings) + extras
    errors = [f for f in all_findings if f.level == "error"]
    warnings = [f for f in all_findings if f.level == "warning"]
    infos = [f for f in all_findings if f.level == "info"]

    summary = (
        f"- Errors: **{len(errors)}**  "
        f"- Warnings: **{len(warnings)}**  "
        f"- Hints: **{len(infos)}**"
    )
    lines.append("## Summary")
    lines.append(summary)
    lines.append("")

    if not all_findings:
        lines.append("**No issues detected.**")
        return "\n".join(lines)

    for level, items, header in (
        ("error", errors, "## Errors"),
        ("warning", warnings, "## Warnings"),
        ("info", infos, "## Hints"),
    ):
        if not items:
            continue
        lines.append(header)
        lines.append("")
        for f in items:
            loc = f" — `{f.location}`" if f.location else ""
            lines.append(f"- **{f.code}**: {f.message}{loc}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Audit a Claude Code skill.")
    parser.add_argument("skill_path", type=Path, help="Path to the skill directory")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--report", type=Path, help="Also write a Markdown report to this file")
    args = parser.parse_args(argv[1:])

    skill_path = args.skill_path.expanduser().resolve()
    report, extras = audit(skill_path)

    if args.json:
        payload = {
            "validate": asdict(report),
            "audit": [asdict(f) for f in extras],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(skill_path, report, extras))

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_markdown(skill_path, report, extras), encoding="utf-8")
        print(f"\nReport written to: {args.report}", file=sys.stderr)

    has_errors = any(f.level == "error" for f in report.findings + extras)
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
