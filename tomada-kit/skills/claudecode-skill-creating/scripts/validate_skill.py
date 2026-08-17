#!/usr/bin/env python3
"""validate_skill.py — Static validation for a Claude Code skill directory.

Usage:
    validate_skill.py <skill-path> [--json]

Checks:
    1. SKILL.md exists.
    2. YAML frontmatter present and parseable (without requiring PyYAML).
    3. Required fields: `name`, `description`.
    4. `name` matches ^[a-z0-9][a-z0-9-]*[a-z0-9]$, no `--`, and len <= 64.
    5. `description` length <= 1024 chars (Agent Skills limit), and
       `description` + `when_to_use` <= 1536 chars (Claude Code listing cap).
    6. SKILL.md body <= 500 lines (warning at 500, error at 800).
    7. Relative links to references/, assets/, scripts/, examples/ resolve.
    8. No single code block in SKILL.md exceeds 25 lines (warning; move logic to scripts/).

Output:
    Human-readable by default, machine-readable with --json.

Exit codes:
    0 = no errors (warnings allowed)
    1 = at least one error
    2 = bad invocation
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
CODE_BLOCK_RE = re.compile(r"^```[^\n]*\n(.*?)^```", re.DOTALL | re.MULTILINE)


@dataclass
class Finding:
    level: str  # "error" | "warning" | "info"
    code: str
    message: str
    location: str = ""


@dataclass
class Report:
    skill_path: str
    skill_name: str = ""
    description_length: int = 0
    body_lines: int = 0
    findings: list[Finding] = field(default_factory=list)

    def add(self, level: str, code: str, message: str, location: str = "") -> None:
        self.findings.append(Finding(level, code, message, location))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warning"]


def parse_frontmatter(text: str) -> tuple[dict[str, str], int]:
    """Parse a minimal YAML frontmatter block (top-level key: value only).

    Returns (fields, body_start_line). Multi-line values via leading-space
    continuation are joined with a single space. Quoted values are unquoted.
    Comments and blank lines are ignored.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fields: dict[str, str] = {}
    last_key: str | None = None
    end_idx = -1
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            end_idx = i
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Key: value at column 0 (no indent) → new key
        if not line.startswith(" ") and not line.startswith("\t") and ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            fields[key] = value
            last_key = key
        elif last_key is not None:
            # continuation line
            fields[last_key] = (fields[last_key] + " " + stripped).strip()
    if end_idx == -1:
        return fields, 0  # unterminated frontmatter handled by caller
    return fields, end_idx + 1


def collect_link_targets(body: str) -> list[str]:
    return [m.group(1).split("#", 1)[0] for m in LINK_RE.finditer(body)]


def validate(skill_path: Path) -> Report:
    report = Report(skill_path=str(skill_path))

    if not skill_path.exists() or not skill_path.is_dir():
        report.add("error", "E001", f"Skill path does not exist or is not a directory: {skill_path}")
        return report

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        report.add("error", "E002", "SKILL.md is missing", str(skill_md))
        return report

    text = skill_md.read_text(encoding="utf-8")
    fields, body_start = parse_frontmatter(text)
    if not fields:
        report.add("error", "E003", "YAML frontmatter is missing or unterminated", "SKILL.md")
        return report

    # Required fields
    name = fields.get("name", "")
    description = fields.get("description", "")
    report.skill_name = name
    report.description_length = len(description)

    if not name:
        report.add("error", "E010", "Required field 'name' is missing", "SKILL.md frontmatter")
    else:
        if not NAME_RE.match(name):
            report.add(
                "error",
                "E011",
                f"name '{name}' does not match ^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                "SKILL.md frontmatter",
            )
        if len(name) > 64:
            report.add("error", "E012", f"name length {len(name)} exceeds 64 chars", "SKILL.md frontmatter")
        if "--" in name:
            report.add(
                "error",
                "E014",
                f"name '{name}' contains consecutive hyphens (rejected by the Agent Skills spec)",
                "SKILL.md frontmatter",
            )
        if name != skill_path.name:
            report.add(
                "warning",
                "W013",
                f"frontmatter name '{name}' differs from directory name '{skill_path.name}'",
                "SKILL.md frontmatter",
            )

    if not description:
        report.add("error", "E020", "Required field 'description' is missing", "SKILL.md frontmatter")
    else:
        if len(description) > 1024:
            report.add(
                "error",
                "E021",
                f"description length {len(description)} exceeds 1024-char limit",
                "SKILL.md frontmatter",
            )
        elif len(description) > 900:
            report.add(
                "warning",
                "W022",
                f"description length {len(description)} approaches 1024-char limit",
                "SKILL.md frontmatter",
            )

    # Claude Code truncates description + when_to_use at 1536 chars in the
    # skill listing. Text past the cap never reaches the model at selection time.
    listing_len = len(description) + len(fields.get("when_to_use", ""))
    if listing_len > 1536:
        report.add(
            "warning",
            "W023",
            f"description + when_to_use is {listing_len} chars; Claude Code truncates the "
            f"listing entry at 1536, so the tail is dropped. Put the key use case first.",
            "SKILL.md frontmatter",
        )

    # Body line count (excluding frontmatter)
    body_lines = text.splitlines()[body_start:]
    report.body_lines = len(body_lines)
    if report.body_lines > 800:
        report.add("error", "E030", f"SKILL.md body has {report.body_lines} lines (>800)", "SKILL.md")
    elif report.body_lines > 500:
        report.add(
            "warning",
            "W031",
            f"SKILL.md body has {report.body_lines} lines (>500). Consider splitting into references/.",
            "SKILL.md",
        )

    # Code block size (logic directly in SKILL.md should live in scripts/ instead)
    for m in CODE_BLOCK_RE.finditer("\n".join(body_lines)):
        block_lines = m.group(1).count("\n") + (1 if m.group(1) else 0)
        if block_lines > 25:
            report.add(
                "warning",
                "W050",
                f"SKILL.md has a {block_lines}-line code block (>25). "
                "Move logic like this to scripts/ and call it as a one-liner.",
                "SKILL.md",
            )

    # Link integrity (relative links only)
    body_text = "\n".join(body_lines)
    for target in collect_link_targets(body_text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if target.startswith("/"):
            continue  # absolute path — out of scope
        target_path = (skill_path / target).resolve()
        try:
            target_path.relative_to(skill_path.resolve())
        except ValueError:
            report.add("warning", "W040", f"link escapes skill directory: {target}", "SKILL.md")
            continue
        if not target_path.exists():
            report.add("error", "E041", f"broken link: {target}", "SKILL.md")

    return report


def render_human(report: Report) -> str:
    lines = []
    lines.append(f"Skill: {report.skill_path}")
    lines.append(f"  name:        {report.skill_name or '(missing)'}")
    lines.append(f"  description: {report.description_length} chars")
    lines.append(f"  body:        {report.body_lines} lines")
    lines.append("")
    if not report.findings:
        lines.append("OK — no issues.")
        return "\n".join(lines)
    by_level = {"error": [], "warning": [], "info": []}
    for f in report.findings:
        by_level[f.level].append(f)
    for level in ("error", "warning", "info"):
        items = by_level[level]
        if not items:
            continue
        lines.append(f"{level.upper()}S ({len(items)}):")
        for f in items:
            loc = f" [{f.location}]" if f.location else ""
            lines.append(f"  {f.code}: {f.message}{loc}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__, file=sys.stderr)
        return 2
    as_json = "--json" in argv[2:]
    skill_path = Path(argv[1]).expanduser().resolve()
    report = validate(skill_path)
    if as_json:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    else:
        print(render_human(report))
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
