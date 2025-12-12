---
name: changelog-generator
description: Generate and maintain CHANGELOG.md files following Keep a Changelog format. Use when creating changelogs, documenting releases, or tracking project changes.
---

# Changelog Generator

This skill helps you create and maintain professional CHANGELOG.md files following the [Keep a Changelog](https://keepachangelog.com/) format. Demonstrates the use of templates for consistent output.

## When to Use This Skill

Use this skill when:
- Creating a new CHANGELOG.md for your project
- Adding entries for new releases
- Documenting breaking changes
- Following semantic versioning practices
- Maintaining release history

## Changelog Format

This skill follows the [Keep a Changelog](https://keepachangelog.com/) format:

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security fixes

## Instructions

### Creating a New Changelog

Use the [changelog template](templates/CHANGELOG-template.md) as a starting point:

```bash
cp templates/CHANGELOG-template.md CHANGELOG.md
```

Then customize:
1. Update project name
2. Add your first version entries
3. Update links at the bottom

### Adding a New Release

When adding a new release entry:

1. **Move Unreleased to Version**: Convert [Unreleased] section to a version number
2. **Add Date**: Use YYYY-MM-DD format
3. **Categorize Changes**: Group under Added/Changed/Fixed/etc.
4. **Update Links**: Add comparison link for the new version

Use the [release template](templates/release-template.md) for formatting.

## Examples

### Example 1: Initial Changelog

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup
- User authentication system
- Dashboard UI components

### Changed
- Improved database query performance

### Fixed
- Fixed login redirect issue
```

### Example 2: Adding a Release

```markdown
# Changelog

## [Unreleased]

## [1.0.0] - 2025-01-21

### Added
- User authentication with JWT tokens
- Role-based access control (RBAC)
- Dashboard with real-time analytics
- RESTful API endpoints for user management

### Changed
- Updated UI to Material Design 3
- Improved database schema for better performance

### Fixed
- Fixed memory leak in WebSocket connections
- Corrected timezone handling in date displays

### Security
- Updated dependencies to patch security vulnerabilities

## [0.9.0] - 2025-01-15

### Added
- Beta release with core features

[Unreleased]: https://github.com/user/repo/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/user/repo/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/user/repo/releases/tag/v0.9.0
```

### Example 3: Breaking Changes

```markdown
## [2.0.0] - 2025-02-01

### Changed
- **BREAKING**: Renamed `getUser()` to `fetchUser()` for consistency
- **BREAKING**: Changed API response format to include metadata envelope

### Removed
- **BREAKING**: Removed deprecated `oldAuthMethod()` function
- Removed legacy compatibility layer

### Migration Guide

**Renamed Methods:**
```javascript
// Old (v1.x)
const user = await getUser(id);

// New (v2.0)
const user = await fetchUser(id);
```

**API Response Format:**
```javascript
// Old (v1.x)
{ id: 1, name: "John" }

// New (v2.0)
{
  data: { id: 1, name: "John" },
  meta: { timestamp: "2025-02-01T10:00:00Z" }
}
```
```

## Best Practices

1. **Keep Unreleased Section**: Always maintain an [Unreleased] section at the top
2. **Use Semantic Versioning**: Follow [SemVer](https://semver.org/) (MAJOR.MINOR.PATCH)
3. **Date Format**: Always use YYYY-MM-DD (ISO 8601)
4. **Group Changes**: Use the six standard categories
5. **Be Specific**: Write clear, user-focused descriptions
6. **Link Versions**: Include comparison links at the bottom
7. **Breaking Changes**: Clearly mark with **BREAKING** prefix
8. **Migration Guides**: Include for major version changes

## Templates

This skill provides two templates:

1. **[CHANGELOG-template.md](templates/CHANGELOG-template.md)**: Complete changelog template for new projects
2. **[release-template.md](templates/release-template.md)**: Template for adding new releases

## AI Assistant Instructions

When this skill is activated:

1. **Determine Action**:
   - New changelog → Use CHANGELOG-template.md
   - Add release → Use release-template.md
   - Update existing → Read current CHANGELOG.md first

2. **For New Changelogs**:
   - Copy template content
   - Customize with project details
   - Help user add initial entries

3. **For New Releases**:
   - Read existing CHANGELOG.md
   - Move [Unreleased] items to new version
   - Add current date in YYYY-MM-DD format
   - Update version links
   - Create new empty [Unreleased] section

4. **Categorization**:
   - **Added**: New features, new capabilities
   - **Changed**: Modifications to existing features
   - **Deprecated**: Features marked for future removal
   - **Removed**: Deleted features or capabilities
   - **Fixed**: Bug fixes
   - **Security**: Security-related changes

5. **Version Number**:
   - Ask if unsure about version number
   - Follow semantic versioning
   - Mark breaking changes clearly

Always:
- Use YYYY-MM-DD date format
- Follow Keep a Changelog format exactly
- Include comparison links
- Write user-focused descriptions (not commit messages)
- Group related changes together

Never:
- Use commit messages as-is (rewrite for users)
- Forget to update version links
- Skip the [Unreleased] section
- Use inconsistent formatting
- Include internal/technical details users don't need

## Version Number Guidelines

### MAJOR version (1.0.0 → 2.0.0)
- Breaking changes
- Incompatible API changes
- Removed features

### MINOR version (1.0.0 → 1.1.0)
- New features (backwards compatible)
- New functionality
- Deprecations

### PATCH version (1.0.0 → 1.0.1)
- Bug fixes (backwards compatible)
- Security patches
- Performance improvements

## Additional Resources

- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
