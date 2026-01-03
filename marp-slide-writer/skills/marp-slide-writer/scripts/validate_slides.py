#!/usr/bin/env python3
"""Marp slide layout constraint validator.

Validates Marp markdown files against layout constraints to ensure
slides display correctly during YouTube recording.

Usage:
    python validate_slides.py <slides.md>
    python validate_slides.py episodes/20260101_example/slides/slides.md
"""

import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Level(Enum):
    """Validation message level."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationResult:
    """Single validation result."""

    slide_num: int
    level: Level
    message: str
    detail: str = ""


@dataclass
class LayoutConstraints:
    """Layout constraints for different slide configurations."""

    # h1 + bullet list
    h1_bullet_max: int = 8
    h1_bullet_recommended: int = 6

    # h1 + code block
    h1_code_max: int = 12
    h1_code_recommended: int = 10

    # h1 + description + bullet
    h1_desc_bullet_max: int = 6
    h1_desc_bullet_recommended: int = 5

    # h1 + description + code
    h1_desc_code_max: int = 10
    h1_desc_code_recommended: int = 8

    # h1 + bullet + code (combined)
    h1_bullet_code_bullet_max: int = 3
    h1_bullet_code_code_max: int = 5

    # h1 + table
    h1_table_max: int = 8
    h1_table_recommended: int = 6

    # no-header + code
    noheader_code_max: int = 17
    noheader_code_recommended: int = 14

    # small-text + bullet
    smalltext_bullet_max: int = 10
    smalltext_bullet_recommended: int = 8

    # subtitle-safe + bullet
    subtitlesafe_bullet_max: int = 5
    subtitlesafe_bullet_recommended: int = 4

    # Text length (Japanese characters)
    h1_max_chars: int = 30
    h1_recommended_chars: int = 20
    bullet_max_chars: int = 45
    bullet_recommended_chars: int = 35
    code_max_chars: int = 60
    code_recommended_chars: int = 50

    # Nesting
    max_nest_level: int = 2


class SlideValidator:
    """Validates Marp slides against layout constraints."""

    def __init__(self, constraints: LayoutConstraints | None = None):
        self.constraints = constraints or LayoutConstraints()
        self.results: list[ValidationResult] = []

    def validate_file(self, filepath: Path) -> list[ValidationResult]:
        """Validate a Marp markdown file."""
        content = filepath.read_text(encoding="utf-8")
        return self.validate_content(content)

    def validate_content(self, content: str) -> list[ValidationResult]:
        """Validate Marp markdown content."""
        self.results = []
        slides = self._split_slides(content)

        for i, slide in enumerate(slides, 1):
            self._validate_slide(i, slide)

        return self.results

    def _split_slides(self, content: str) -> list[str]:
        """Split content into individual slides."""
        # Remove YAML frontmatter
        content = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL)
        # Split by slide separator
        slides = re.split(r"\n---\n", content)
        return [s.strip() for s in slides if s.strip()]

    def _validate_slide(self, num: int, slide: str) -> None:
        """Validate a single slide."""
        # Parse slide components
        classes = self._extract_classes(slide)
        has_h1 = bool(re.search(r"^# [^#]", slide, re.MULTILINE))
        has_h2 = bool(re.search(r"^## ", slide, re.MULTILINE))
        has_description = self._has_description(slide)
        bullet_count = self._count_bullets(slide)
        code_lines = self._count_code_lines(slide)
        table_rows = self._count_table_rows(slide)
        code_blocks = self._count_code_blocks(slide)

        # Skip title/section slides
        if "title" in classes or "section" in classes:
            return

        # Check multiple code blocks
        if code_blocks > 1:
            self._add_result(
                num,
                Level.WARNING,
                "複数コードブロック",
                f"{code_blocks}個のコードブロックがあります。1スライド1ブロック推奨",
            )

        # Determine constraints based on configuration
        c = self.constraints

        if "no-header" in classes and code_lines > 0:
            self._check_limit(
                num,
                code_lines,
                c.noheader_code_max,
                c.noheader_code_recommended,
                "コード行数(no-header)",
            )
        elif "small-text" in classes and bullet_count > 0:
            self._check_limit(
                num,
                bullet_count,
                c.smalltext_bullet_max,
                c.smalltext_bullet_recommended,
                "箇条書き行数(small-text)",
            )
        elif "subtitle-safe" in classes and bullet_count > 0:
            self._check_limit(
                num,
                bullet_count,
                c.subtitlesafe_bullet_max,
                c.subtitlesafe_bullet_recommended,
                "箇条書き行数(subtitle-safe)",
            )
        elif has_h1:
            if has_description and code_lines > 0:
                self._check_limit(
                    num,
                    code_lines,
                    c.h1_desc_code_max,
                    c.h1_desc_code_recommended,
                    "コード行数(h1+説明文+コード)",
                )
            elif has_description and bullet_count > 0:
                self._check_limit(
                    num,
                    bullet_count,
                    c.h1_desc_bullet_max,
                    c.h1_desc_bullet_recommended,
                    "箇条書き行数(h1+説明文+箇条書き)",
                )
            elif bullet_count > 0 and code_lines > 0:
                # Combined bullet + code
                if bullet_count > c.h1_bullet_code_bullet_max:
                    self._add_result(
                        num,
                        Level.WARNING,
                        "箇条書き過多(h1+箇条書き+コード)",
                        f"{bullet_count}行 > 推奨{c.h1_bullet_code_bullet_max}行",
                    )
                if code_lines > c.h1_bullet_code_code_max:
                    self._add_result(
                        num,
                        Level.WARNING,
                        "コード過多(h1+箇条書き+コード)",
                        f"{code_lines}行 > 推奨{c.h1_bullet_code_code_max}行",
                    )
            elif code_lines > 0:
                self._check_limit(
                    num,
                    code_lines,
                    c.h1_code_max,
                    c.h1_code_recommended,
                    "コード行数(h1+コード)",
                )
            elif bullet_count > 0:
                self._check_limit(
                    num,
                    bullet_count,
                    c.h1_bullet_max,
                    c.h1_bullet_recommended,
                    "箇条書き行数(h1+箇条書き)",
                )
            elif table_rows > 0:
                self._check_limit(
                    num,
                    table_rows,
                    c.h1_table_max,
                    c.h1_table_recommended,
                    "テーブル行数(h1+テーブル)",
                )

        # Check text length
        self._check_text_lengths(num, slide)

        # Check nesting level
        self._check_nesting(num, slide)

    def _extract_classes(self, slide: str) -> list[str]:
        """Extract CSS classes from slide."""
        matches = re.findall(r"<!-- _class: (.+?) -->", slide)
        classes = []
        for match in matches:
            classes.extend(match.split())
        return classes

    def _has_description(self, slide: str) -> bool:
        """Check if slide has description text (non-bullet, non-code paragraph)."""
        lines = slide.split("\n")
        in_code = False
        for line in lines:
            if line.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            # Skip headers, bullets, comments, empty lines
            if (
                line.startswith("#")
                or line.startswith("-")
                or line.startswith("*")
                or line.startswith("|")
                or line.startswith("<!--")
                or line.startswith(">")
                or not line.strip()
            ):
                continue
            # Found a regular paragraph
            if len(line.strip()) > 5:
                return True
        return False

    def _count_bullets(self, slide: str) -> int:
        """Count bullet list items."""
        lines = slide.split("\n")
        count = 0
        in_code = False
        for line in lines:
            if line.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if re.match(r"^\s*[-*]\s", line):
                count += 1
        return count

    def _count_code_lines(self, slide: str) -> int:
        """Count lines inside code blocks."""
        matches = re.findall(r"```\w*\n(.*?)```", slide, re.DOTALL)
        total = 0
        for match in matches:
            lines = [line for line in match.split("\n") if line.strip()]
            total += len(lines)
        return total

    def _count_table_rows(self, slide: str) -> int:
        """Count table rows (including header)."""
        lines = slide.split("\n")
        count = 0
        for line in lines:
            if line.startswith("|") and not re.match(r"^\|[-: |]+\|$", line):
                count += 1
        return count

    def _count_code_blocks(self, slide: str) -> int:
        """Count number of code blocks."""
        return len(re.findall(r"```\w*\n", slide))

    def _check_limit(
        self, num: int, value: int, max_val: int, recommended: int, label: str
    ) -> None:
        """Check value against limits and add appropriate result."""
        if value > max_val:
            self._add_result(
                num, Level.ERROR, f"{label}超過", f"{value}行 > 上限{max_val}行"
            )
        elif value > recommended:
            self._add_result(
                num, Level.INFO, f"{label}推奨超過", f"{value}行 > 推奨{recommended}行"
            )

    def _check_text_lengths(self, num: int, slide: str) -> None:
        """Check text lengths in slide."""
        c = self.constraints
        lines = slide.split("\n")
        in_code = False

        for line in lines:
            if line.startswith("```"):
                in_code = not in_code
                continue

            # Count Japanese/wide characters as 1.5
            char_count = self._count_chars(line)

            if line.startswith("# ") and not line.startswith("## "):
                text = line[2:]
                text_len = self._count_chars(text)
                if text_len > c.h1_max_chars:
                    self._add_result(
                        num,
                        Level.WARNING,
                        "h1タイトル長すぎ",
                        f"{text_len}文字 > 上限{c.h1_max_chars}文字",
                    )
                elif text_len > c.h1_recommended_chars:
                    self._add_result(
                        num,
                        Level.INFO,
                        "h1タイトル推奨超過",
                        f"{text_len}文字 > 推奨{c.h1_recommended_chars}文字",
                    )
            elif re.match(r"^\s*[-*]\s", line):
                text = re.sub(r"^\s*[-*]\s*", "", line)
                text_len = self._count_chars(text)
                if text_len > c.bullet_max_chars:
                    self._add_result(
                        num,
                        Level.WARNING,
                        "箇条書き1行長すぎ",
                        f"{text_len}文字 > 上限{c.bullet_max_chars}文字: {text[:20]}...",
                    )
            elif in_code:
                if char_count > c.code_max_chars:
                    self._add_result(
                        num,
                        Level.INFO,
                        "コード1行長い",
                        f"{char_count}文字 > 推奨{c.code_recommended_chars}文字",
                    )

    def _count_chars(self, text: str) -> int:
        """Count characters (wide chars count as 1.5)."""
        count = 0
        for char in text:
            if ord(char) > 127:  # Non-ASCII (Japanese, etc.)
                count += 1.5
            else:
                count += 1
        return int(count)

    def _check_nesting(self, num: int, slide: str) -> None:
        """Check for excessive nesting levels."""
        lines = slide.split("\n")
        in_code = False
        for line in lines:
            if line.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue

            # Count leading spaces for bullets
            match = re.match(r"^(\s*)[-*]", line)
            if match:
                indent = len(match.group(1))
                # 2 spaces per level typically
                level = indent // 2
                if level > self.constraints.max_nest_level:
                    self._add_result(
                        num,
                        Level.WARNING,
                        "ネスト深すぎ",
                        f"{level + 1}階層 > 推奨{self.constraints.max_nest_level + 1}階層",
                    )

    def _add_result(
        self, slide_num: int, level: Level, message: str, detail: str = ""
    ) -> None:
        """Add a validation result."""
        self.results.append(ValidationResult(slide_num, level, message, detail))


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_slides.py <slides.md>")
        print("Example: python validate_slides.py episodes/20260101/slides/slides.md")
        return 1

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        return 1

    validator = SlideValidator()
    results = validator.validate_file(filepath)

    if not results:
        print(f"✅ {filepath.name}: All slides pass validation!")
        return 0

    # Group by level
    errors = [r for r in results if r.level == Level.ERROR]
    warnings = [r for r in results if r.level == Level.WARNING]
    infos = [r for r in results if r.level == Level.INFO]

    print(f"\n📊 Validation Results for {filepath.name}")
    print("=" * 50)

    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for r in errors:
            print(f"  Slide {r.slide_num}: {r.message}")
            if r.detail:
                print(f"    → {r.detail}")

    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for r in warnings:
            print(f"  Slide {r.slide_num}: {r.message}")
            if r.detail:
                print(f"    → {r.detail}")

    if infos:
        print(f"\n💡 INFO ({len(infos)}):")
        for r in infos:
            print(f"  Slide {r.slide_num}: {r.message}")
            if r.detail:
                print(f"    → {r.detail}")

    print("\n" + "=" * 50)
    print(f"Summary: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} info")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
