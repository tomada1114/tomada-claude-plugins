---
name: claude-rules-organizer
description: Reorganize bloated CLAUDE.md files into modular .claude/rules/ structure with dynamic loading. Use PROACTIVELY when CLAUDE.md exceeds 200 lines, when organizing project rules, when splitting monolithic instructions, when optimizing context usage, or when user mentions CLAUDE.md refactoring, rules organization, context optimization. Examples: <example>Context: User has large CLAUDE.md user: 'My CLAUDE.md is getting too big' assistant: 'I will use claude-rules-organizer to split into modular rules' <commentary>Triggered by CLAUDE.md size concern</commentary></example>
---

# Claude Rules Organizer

Reorganize bloated CLAUDE.md files into a modular `.claude/rules/` structure for better maintainability and context efficiency.

## When to Use This Skill

- CLAUDE.md exceeds 200 lines
- Multiple unrelated topics in single CLAUDE.md
- Context optimization needed (large projects)
- Team wants topic-based rule organization
- Need dynamic loading for specific file types
- Migrating from monolithic to modular rules

## Core Concepts

### Three Rule Methods (Priority Order)

| Method | Location | Loading | Use Case |
|--------|----------|---------|----------|
| **CLAUDE.md** | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Always at startup | Core project overview, navigation |
| **.claude/rules/** | `.claude/rules/*.md` | Conditional (paths) | Topic-specific rules |
| **@import** | Within CLAUDE.md | At startup | External file references |

### Dynamic Loading with paths

Rules with `paths` frontmatter load **only when matching files are accessed**:

```markdown
---
paths: src/api/**/*.ts
---

# API Rules
- Input validation required
- Use standard error format
```

| paths | Loading | Context |
|-------|---------|---------|
| None | Startup | Always consumed |
| Specified | On file access | On-demand only |

## Reorganization Workflow

### Step 1: Analyze Current CLAUDE.md

Identify distinct topics:
- Project overview (keep in CLAUDE.md)
- Coding standards → `rules/code-style.md`
- Testing rules → `rules/testing.md`
- API conventions → `rules/api.md` (with paths)
- Frontend rules → `rules/frontend.md` (with paths)

### Step 2: Create Modular Structure

```
.claude/
├── CLAUDE.md              # Minimal: overview + navigation only
└── rules/
    ├── code-style.md      # No paths → always load
    ├── testing.md         # No paths → always load
    ├── api.md             # paths: src/api/**/* → dynamic
    ├── frontend/
    │   ├── react.md       # paths: **/*.tsx → dynamic
    │   └── styles.md      # paths: **/*.css → dynamic
    └── backend/
        └── database.md    # paths: src/db/**/* → dynamic
```

### Step 3: Determine paths Strategy

| Rule Type | paths Recommendation |
|-----------|---------------------|
| Universal (code style, git) | No paths (always load) |
| Language-specific | `**/*.{ext}` |
| Directory-specific | `src/api/**/*` |
| Test-specific | `**/*.test.ts, **/*.spec.ts` |

### Step 4: Migrate Content

For each topic:

1. Create new rule file with frontmatter
2. Move relevant content from CLAUDE.md
3. Add paths if file-type specific
4. Update CLAUDE.md to reference new location

## Output Templates

### Minimal CLAUDE.md Template

```markdown
# Project Name

Brief project description.

## Quick Reference

- Build: `npm run build`
- Test: `npm test`
- Lint: `npm run lint`

## Rule Files

Detailed rules in `.claude/rules/`:
- `code-style.md` - Coding standards
- `testing.md` - Test conventions
- `api.md` - API guidelines (loads for src/api/)
- `frontend/react.md` - React patterns (loads for *.tsx)

## Key Files

| Purpose | Path |
|---------|------|
| Entry | src/index.ts |
| Config | config/ |
```

### Rule File Template (No paths)

```markdown
# [Topic] Rules

## Overview
Brief description of what this rule file covers.

## Rules

### Rule Category 1
- Specific rule
- Another rule

### Rule Category 2
- Specific rule
```

### Rule File Template (With paths)

```markdown
---
paths: src/api/**/*.ts
---

# API Development Rules

## Overview
Rules for API endpoint development.

## Standards

### Request Handling
- Validate all inputs
- Use typed request/response

### Error Handling
- Use standard error format
- Include error codes
```

## Best Practices

### DO

1. **Keep CLAUDE.md minimal** - Overview and navigation only
2. **One topic per file** - `testing.md`, `api.md`, not `rules.md`
3. **Use paths sparingly** - Only for truly file-specific rules
4. **Descriptive filenames** - Content should be obvious from name
5. **Use subdirectories** - Group related rules (`frontend/`, `backend/`)

### DON'T

1. **Don't over-fragment** - 3-10 rule files is ideal
2. **Don't paths everything** - Universal rules need no paths
3. **Don't duplicate** - Reference shared rules, don't copy
4. **Don't nest too deep** - Max 2 levels of subdirectories

## Verification

After reorganization:

1. **Check startup load**: Run `claude` and use `/memory` to verify only intended rules load
2. **Test dynamic load**: Read a file matching a paths pattern, confirm rule loads
3. **Verify no duplicates**: Second read of same file type should not reload rules
4. **Check context**: Use `/context` before and after to measure improvement

## AI Assistant Instructions

When this skill is activated:

### Analysis Phase

1. **Read current CLAUDE.md** completely
2. **Identify topics**: List distinct sections/concerns
3. **Measure size**: Count lines, estimate tokens
4. **Check for @imports**: Note external references
5. **Present analysis** to user with recommendations

### Planning Phase

1. **Propose structure**: Show target file tree
2. **Categorize rules**:
   - Universal (no paths)
   - File-type specific (with paths)
   - Directory-specific (with paths)
3. **Estimate impact**: Context savings, maintainability gains
4. **Get user approval** before proceeding

### Execution Phase

1. **Create directories**: `.claude/rules/` and subdirs
2. **Create rule files**: One topic at a time
3. **Update CLAUDE.md**: Strip content, add navigation
4. **Preserve @imports**: Keep external references working
5. **Show diff summary**: What moved where

### Verification Phase

1. **List created files** with line counts
2. **Show new CLAUDE.md** content
3. **Provide test commands** for verification
4. **Suggest next steps** if further optimization possible

### Always

- Preserve all existing rules (no content loss)
- Maintain team compatibility (git-friendly)
- Use English for file contents
- Follow glob pattern standards
- Create backup recommendation before major changes

### Never

- Delete rules without user confirmation
- Change rule semantics during migration
- Create circular @imports
- Use paths for less than 50 lines of rules
- Over-fragment into too many small files

## Additional Resources

- [Detailed Reference](reference.md) - Glob patterns, edge cases, troubleshooting
- [Templates](templates/) - Ready-to-use rule file templates
