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
  A006  Legacy prompt phrasings that current models handle badly: forced
        re-verification, severity self-filtering in review steps, requests to
        echo reasoning, and fixed progress-update scaffolding. Scans SKILL.md
        and references/*.md. See references/prompt-authoring.md.
        Suppress with `<!-- audit-ignore: A006 -->` on the line, or
        `<!-- audit-ignore-file: A006 -->` in the file's first 5 lines.
  A007  references/*.md files that link to another references/*.md file.
        References are one hop from SKILL.md only; Claude previews nested
        references with `head` rather than reading them whole, so a
        reference-to-reference link risks acting on a half-read file.
        Links from SKILL.md itself, external URLs, anchor-only links, and
        links outside references/ (e.g. scripts/, assets/) are not flagged.
        Same opt-out mechanism as A006 (see below), code `A007`.
  A008  references/*.md files over 100 lines with no detectable Table of
        Contents in their first 40 lines (neither a "Table of
        Contents"/"Contents"/"ToC" heading nor 3+ same-file anchor links).
        Same opt-out mechanism as A006 (see below), code `A008`.
  A009  SKILL.md frontmatter containing Japanese text. Frontmatter is
        English-only: `description` is what Claude reads to pick a skill,
        and `argument-hint` is shown in the CLI. Skill *content* is exempt —
        the body, references/, scripts/ and templates/ may hold Japanese
        freely, since some skills exist to produce Japanese text. There is
        no opt-out: a skill whose subject is Japanese still describes
        itself in English.

  N1-N4 Dual-platform neutrality — inherited automatically, not a separate
        check here. `validate_skill.validate()` (this script's base `report`)
        already runs dual-platform-skills/scripts/neutrality_lint.py and folds
        its N1-N4 findings in, so they appear in every audit report without
        duplicate logic. See validate_skill.py's own docstring (check 9).

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

IGNORE_LINE_RE = re.compile(r"<!--\s*audit-ignore:\s*([^>]+?)\s*-->", re.IGNORECASE)
IGNORE_FILE_RE = re.compile(r"<!--\s*audit-ignore-file:\s*([^>]+?)\s*-->", re.IGNORECASE)
# The file-level opt-out must sit in the file header, not anywhere in the body.
IGNORE_FILE_HEADER_LINES = 5


def _ignored_codes(pattern: re.Pattern[str], text: str) -> set[str]:
    """Collect check codes named in `<!-- audit-ignore[-file]: CODE[, CODE...] -->`."""
    codes: set[str] = set()
    for m in pattern.finditer(text):
        for code in re.split(r"[,\s]+", m.group(1).strip()):
            if code:
                codes.add(code.upper())
    return codes


def is_line_ignored(line: str, code: str) -> bool:
    """True if `line` carries an `audit-ignore: <code>` (or comma-list) directive."""
    return code.upper() in _ignored_codes(IGNORE_LINE_RE, line)


def is_file_ignored(lines: list[str], code: str) -> bool:
    """True if an `audit-ignore-file: <code>` directive appears in the file header."""
    header = "\n".join(lines[:IGNORE_FILE_HEADER_LINES])
    return code.upper() in _ignored_codes(IGNORE_FILE_RE, header)

# A006: phrasings that current models handle badly. Each entry is
# (regex, short reason). Kept deliberately narrow to limit false positives.
LEGACY_PHRASINGS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"double[- ]?check|re-?verify|verification step|"
            r"ダブルチェック|再確認し|検証ステップ",
            re.IGNORECASE,
        ),
        "forced re-verification — current models self-verify; this causes over-verification",
    ),
    (
        re.compile(
            r"only report (?:high|critical|important|significant|major)|"
            r"be conservative|do(?:n't| not) nitpick|skip (?:the )?nits|"
            r"重大な(?:もの|問題|指摘)だけ|重要なものだけ|保守的に",
            re.IGNORECASE,
        ),
        "severity self-filtering — models follow this literally and recall drops; filter in a separate phase",
    ),
    (
        re.compile(
            r"show your (?:reasoning|thinking|work)|"
            r"explain your (?:reasoning|thought process)|"
            r"write out your (?:thought process|reasoning)|"
            r"思考(?:過程|プロセス)を|推論過程を",
            re.IGNORECASE,
        ),
        "asks the model to echo its reasoning — can trigger the reasoning_extraction refusal on Fable",
    ),
    (
        re.compile(
            r"(?:after |every )\d+ tool calls|"
            r"\d+\s*回(?:ごと|おき)に.{0,10}(?:進捗|要約)",
            re.IGNORECASE,
        ),
        "fixed progress-update scaffolding — current models already pace updates well",
    ),
]


# A009: hiragana, katakana, or CJK ideographs. Punctuation-only ranges are
# deliberately excluded — an English description *about* Japanese may quote
# 「」 or 、 without itself being Japanese.
JAPANESE_RE = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")


def find_japanese_frontmatter(
    fields: dict[str, str],
) -> list[validate_skill.Finding]:
    """A009: flag Japanese text in SKILL.md frontmatter.

    Frontmatter is English-only: `description` is the text Claude reads when
    choosing a skill, and `argument-hint` is surfaced in the CLI. The skill's
    own content is out of scope by design — a skill that writes Japanese
    articles or SNS copy legitimately carries Japanese in its body,
    references, templates and scripts.
    """
    findings: list[validate_skill.Finding] = []
    for key, value in fields.items():
        match = JAPANESE_RE.search(value)
        if not match:
            continue
        findings.append(
            validate_skill.Finding(
                "warning",
                "A009",
                f"frontmatter field '{key}' contains Japanese text "
                f"(first at '{match.group(0)}') — frontmatter is English-only; "
                f"skill content (body, references/, scripts/) is exempt",
                "SKILL.md frontmatter",
            )
        )
    return findings


TOC_HEADING_RE = re.compile(
    r"^#{1,6}\s*.*\b(table of contents|contents|toc)\b", re.IGNORECASE
)
ANCHOR_LINK_RE = re.compile(r"\]\(#[^)]+\)")
TOC_HEAD_LINES = 100  # only files longer than this are required to have a ToC
TOC_SCAN_LINES = 40  # ToC must be detectable within this many leading lines
TOC_MIN_ANCHOR_LINKS = 3


def find_ref_to_ref_links(skill_path: Path, refs_dir: Path) -> list[validate_skill.Finding]:
    """A007: flag references/*.md files that link to another references/*.md file.

    References are meant to be exactly one hop from SKILL.md; Claude previews
    nested references with `head` rather than reading them whole, so a
    reference that links deeper risks the model acting on a half-read file.
    Only links that resolve to an existing .md file inside references/ (and
    not the linking file itself) are flagged — external URLs, anchor-only
    links, and links to scripts/assets/nonexistent paths are left alone.
    """
    findings: list[validate_skill.Finding] = []
    refs_dir_resolved = refs_dir.resolve()
    skill_path_resolved = skill_path.resolve()
    for md in sorted(refs_dir.glob("*.md")):
        rel = md.relative_to(skill_path).as_posix()
        text = md.read_text(encoding="utf-8")
        lines = text.splitlines()
        if is_file_ignored(lines, "A007"):
            continue
        md_resolved = md.resolve()
        for lineno, line in enumerate(lines, start=1):
            if is_line_ignored(line, "A007"):
                continue
            for m in validate_skill.LINK_RE.finditer(line):
                raw_target = m.group(1).strip()
                if not raw_target or raw_target.startswith("#"):
                    continue
                if raw_target.startswith(("http://", "https://", "mailto:")):
                    continue
                target_path_part = raw_target.split("#", 1)[0].strip()
                if not target_path_part:
                    continue
                try:
                    resolved = (md.parent / target_path_part).resolve()
                except OSError:
                    continue
                try:
                    resolved.relative_to(skill_path_resolved)
                    resolved.relative_to(refs_dir_resolved)
                except ValueError:
                    continue  # not inside this skill's references/ — out of scope
                if resolved.suffix.lower() != ".md":
                    continue
                if resolved == md_resolved:
                    continue
                if not resolved.exists():
                    continue  # dangling/illustrative path — E041 covers real broken links
                findings.append(
                    validate_skill.Finding(
                        "warning",
                        "A007",
                        f"reference-to-reference link to '{target_path_part}' — references "
                        f"are one hop from SKILL.md only; a head-preview of this file may "
                        f"stop before Claude ever reads the link",
                        f"{rel}:{lineno}",
                    )
                )
    return findings


def find_missing_toc(skill_path: Path, refs_dir: Path) -> list[validate_skill.Finding]:
    """A008: flag long references/*.md files with no detectable Table of Contents.

    Detection is lenient by design: a heading naming "Table of Contents" /
    "Contents" / "ToC" within the first TOC_SCAN_LINES lines counts, and so
    does a cluster of 3+ same-file anchor links up there (a hand-rolled ToC
    without a literal heading).
    """
    findings: list[validate_skill.Finding] = []
    for md in sorted(refs_dir.glob("*.md")):
        rel = md.relative_to(skill_path).as_posix()
        text = md.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) <= TOC_HEAD_LINES:
            continue
        if is_file_ignored(lines, "A008"):
            continue
        head = lines[:TOC_SCAN_LINES]
        has_heading = any(TOC_HEADING_RE.match(l) for l in head)
        anchor_count = sum(len(ANCHOR_LINK_RE.findall(l)) for l in head)
        if has_heading or anchor_count >= TOC_MIN_ANCHOR_LINKS:
            continue
        findings.append(
            validate_skill.Finding(
                "warning",
                "A008",
                f"{len(lines)}-line reference has no detectable Table of Contents in the "
                f"first {min(TOC_SCAN_LINES, len(lines))} lines — consider adding one",
                rel,
            )
        )
    return findings


def scan_legacy_phrasings(text: str, location: str) -> list[validate_skill.Finding]:
    """Flag legacy prompt phrasings, honoring audit-ignore directives.

    The file-level opt-out is only honored in the first few lines, so that prose
    merely *documenting* the directive (as this skill's own SKILL.md does) does
    not silently disable the check for the whole file.
    """
    lines = text.splitlines()
    if is_file_ignored(lines, "A006"):
        return []
    findings: list[validate_skill.Finding] = []
    for lineno, line in enumerate(lines, start=1):
        if is_line_ignored(line, "A006"):
            continue
        for pattern, reason in LEGACY_PHRASINGS:
            match = pattern.search(line)
            if match:
                findings.append(
                    validate_skill.Finding(
                        "info",
                        "A006",
                        f"legacy phrasing '{match.group(0).strip()}': {reason}",
                        f"{location}:{lineno}",
                    )
                )
                break
    return findings


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

    # A006: legacy prompt phrasings in SKILL.md and every reference file
    extras.extend(scan_legacy_phrasings(text, "SKILL.md"))
    if refs_dir.exists():
        for md in sorted(refs_dir.glob("*.md")):
            rel = md.relative_to(skill_path).as_posix()
            extras.extend(
                scan_legacy_phrasings(md.read_text(encoding="utf-8"), rel)
            )

    # A009: Japanese in frontmatter (content is deliberately not scanned)
    extras.extend(find_japanese_frontmatter(fields))

    # A007 / A008: reference-to-reference links and missing ToCs
    if refs_dir.exists():
        extras.extend(find_ref_to_ref_links(skill_path, refs_dir))
        extras.extend(find_missing_toc(skill_path, refs_dir))

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
