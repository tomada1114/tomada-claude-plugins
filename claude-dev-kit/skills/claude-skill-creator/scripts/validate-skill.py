#!/usr/bin/env python3
"""
Validate SKILL.md files for Claude Code skills.

Usage:
    python validate-skill.py <path-to-SKILL.md>
    python validate-skill.py <path-to-skill-directory>

Validates:
    - YAML frontmatter presence and structure
    - name: lowercase, hyphens, max 64 chars
    - description: non-empty, max 1024 chars
    - SKILL.md body line count (warns if > 500)
    - Required sections presence
"""

import sys
import re
from pathlib import Path


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def log_pass(message: str) -> None:
    print(f"{Colors.GREEN}✓{Colors.END} {message}")


def log_fail(message: str) -> None:
    print(f"{Colors.RED}✗{Colors.END} {message}")


def log_warn(message: str) -> None:
    print(f"{Colors.YELLOW}⚠{Colors.END} {message}")


def log_info(message: str) -> None:
    print(f"{Colors.BLUE}ℹ{Colors.END} {message}")


def parse_frontmatter(content: str) -> tuple[dict | None, str, int]:
    """Parse YAML frontmatter from SKILL.md content.

    Returns: (frontmatter_dict, body, frontmatter_end_line)
    """
    lines = content.split('\n')

    if not lines or lines[0].strip() != '---':
        return None, content, 0

    end_index = -1
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            end_index = i
            break

    if end_index == -1:
        return None, content, 0

    frontmatter_lines = lines[1:end_index]
    body = '\n'.join(lines[end_index + 1:])

    frontmatter = {}
    current_key = None
    current_value = []

    for line in frontmatter_lines:
        if ':' in line and not line.startswith(' ') and not line.startswith('\t'):
            if current_key:
                frontmatter[current_key] = ' '.join(current_value).strip()
            key, _, value = line.partition(':')
            current_key = key.strip()
            current_value = [value.strip()]
        elif current_key:
            current_value.append(line.strip())

    if current_key:
        frontmatter[current_key] = ' '.join(current_value).strip()

    return frontmatter, body, end_index + 1


def validate_name(name: str) -> list[str]:
    """Validate the 'name' field."""
    errors = []

    if not name:
        errors.append("name is empty")
        return errors

    if len(name) > 64:
        errors.append(f"name exceeds 64 characters ({len(name)} chars)")

    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', name) and len(name) > 1:
        if name[0] == '-' or name[-1] == '-':
            errors.append("name cannot start or end with hyphen")
        if re.search(r'[A-Z]', name):
            errors.append("name cannot contain uppercase letters")
        if re.search(r'[_\s]', name):
            errors.append("name cannot contain underscores or spaces")
        if re.search(r'[^a-z0-9-]', name):
            errors.append("name can only contain lowercase letters, numbers, and hyphens")

    # Reserved words - warn instead of error for self-created skills
    # (This rule exists to prevent external malicious skills from impersonating official ones)
    # Return as separate list to handle differently
    reserved_warnings = []
    if 'anthropic' in name.lower() or 'claude' in name.lower():
        reserved_warnings.append("name contains reserved words ('anthropic', 'claude') - OK for your own skills")

    return errors, reserved_warnings


def validate_description(description: str) -> list[str]:
    """Validate the 'description' field."""
    errors = []
    warnings = []

    if not description:
        errors.append("description is empty")
        return errors, warnings

    if len(description) > 1024:
        errors.append(f"description exceeds 1024 characters ({len(description)} chars)")

    if '<' in description and '>' in description:
        if re.search(r'<(?!example|commentary)[a-zA-Z][^>]*>', description):
            warnings.append("description may contain XML tags (only <example> and <commentary> are recommended)")

    if 'use when' not in description.lower() and 'use proactively' not in description.lower():
        warnings.append("description should include 'Use when...' or 'Use PROACTIVELY when...'")

    return errors, warnings


def validate_body(body: str) -> tuple[list[str], list[str]]:
    """Validate the SKILL.md body content."""
    errors = []
    warnings = []

    lines = body.strip().split('\n')
    line_count = len(lines)

    if line_count > 500:
        warnings.append(f"body exceeds 500 lines ({line_count} lines) - consider using progressive disclosure")
    elif line_count > 400:
        log_info(f"Body is {line_count} lines (approaching 500 limit)")

    recommended_sections = [
        ('# ', 'title heading'),
        ('## When to Use', '"When to Use" section'),
    ]

    for pattern, name in recommended_sections:
        if pattern not in body:
            warnings.append(f"missing recommended {name}")

    return errors, warnings


def validate_skill(skill_path: Path) -> bool:
    """Validate a SKILL.md file."""
    print(f"\n{Colors.BOLD}Validating: {skill_path}{Colors.END}\n")

    if not skill_path.exists():
        log_fail(f"File not found: {skill_path}")
        return False

    content = skill_path.read_text(encoding='utf-8')

    frontmatter, body, fm_end_line = parse_frontmatter(content)

    if frontmatter is None:
        log_fail("No valid YAML frontmatter found (must start with ---)")
        return False

    log_pass("YAML frontmatter found")

    all_errors = []
    all_warnings = []

    # Validate name
    name = frontmatter.get('name', '')
    name_errors, name_warnings = validate_name(name)
    if name_errors:
        for err in name_errors:
            log_fail(f"name: {err}")
        all_errors.extend(name_errors)
    else:
        log_pass(f"name: '{name}' is valid")

    for warn in name_warnings:
        log_info(f"name: {warn}")  # Info level for reserved word notice

    # Validate description
    description = frontmatter.get('description', '')
    desc_errors, desc_warnings = validate_description(description)
    if desc_errors:
        for err in desc_errors:
            log_fail(f"description: {err}")
        all_errors.extend(desc_errors)
    else:
        log_pass(f"description: {len(description)} chars (valid)")

    for warn in desc_warnings:
        log_warn(f"description: {warn}")
    all_warnings.extend(desc_warnings)

    # Validate body
    body_errors, body_warnings = validate_body(body)
    for err in body_errors:
        log_fail(f"body: {err}")
    all_errors.extend(body_errors)

    for warn in body_warnings:
        log_warn(f"body: {warn}")
    all_warnings.extend(body_warnings)

    # Summary
    print()
    if all_errors:
        log_fail(f"Validation failed with {len(all_errors)} error(s)")
        return False
    elif all_warnings:
        log_warn(f"Validation passed with {len(all_warnings)} warning(s)")
        return True
    else:
        log_pass("Validation passed")
        return True


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python validate-skill.py <path-to-SKILL.md or skill-directory>")
        return 1

    path = Path(sys.argv[1])

    if path.is_dir():
        skill_path = path / 'SKILL.md'
    else:
        skill_path = path

    if not skill_path.name == 'SKILL.md':
        log_warn(f"Expected SKILL.md, got {skill_path.name}")

    success = validate_skill(skill_path)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
