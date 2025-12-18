# Changelog

All notable changes to this skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this skill adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2025-12-18

### Added
- **Skill Development section** in SKILL.md with development process overview
- **skill-development.md** - Comprehensive guide covering:
  - Evaluation-driven development (create evaluations before documentation)
  - Iterative development with Claude A (designer) and Claude B (tester)
  - Workflow patterns (checklists, feedback loops)
  - Multi-model testing (Haiku, Sonnet, Opus)
- **Third-person rule** added to reference.md description section
- **CHANGELOG policy**: Don't create CHANGELOG.md by default (only for complex skills)

### Changed
- Updated AI Assistant Instructions with skill-development.md reference
- Updated AI Assistant Instructions: Never create CHANGELOG.md by default
- Removed CHANGELOG.md from directory structure examples in reference.md
- Enhanced Additional Resources with skill-development.md link

## [3.1.0] - 2025-12-18

### Added
- **Context Efficiency section** in SKILL.md with 3-level loading model
- **context-efficiency.md** - Comprehensive guide for token optimization
- Core principle: "Claude is already smart" - assume base knowledge
- Script efficiency explanation (code never enters context)
- Reference file rules (one level deep, ToC for long files)

### Changed
- Updated AI Assistant Instructions with context efficiency guidelines
- Enhanced Additional Resources with context-efficiency.md link

## [3.0.0] - 2025-12-18

### Changed
- **BREAKING**: Restructured SKILL.md for context efficiency (under 500 lines)
- Optimized description for better trigger matching
- Replaced duplicate content with links to reference files

### Added
- Table of Contents for quick navigation
- `scripts/validate-skill.py` for YAML frontmatter validation
- Separate CHANGELOG.md (this file)

### Removed
- Moved Version History from SKILL.md to CHANGELOG.md
- Removed duplicate content already in reference.md

## [2.1.0] - 2025-11-29

### Added
- Critical: Skill Tool Permissions section
- Guaranteed Activation: CLAUDE.md Integration section
- `<example>` tag usage in descriptions
- `Use PROACTIVELY` pattern guidance
- Updated Quick Reference Checklist with activation items
- Updated AI Assistant Instructions with permission reminders

## [2.0.0] - 2025-01-21

### Added
- 5 complete example skills in examples/ directory
- Comprehensive scripts-guide.md
- Detailed reference.md
- Basic and advanced templates

### Changed
- Reorganized for progressive disclosure
- Reduced main SKILL.md from 634 to ~400 lines

## [1.0.0] - Initial Release

### Added
- Basic skill creation guide
- Essential YAML frontmatter documentation
- Core best practices
