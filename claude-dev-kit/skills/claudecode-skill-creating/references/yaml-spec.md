# YAML Frontmatter Specification

Complete specification for YAML frontmatter fields in Claude Code skill files (SKILL.md).

## Two-Tier Field System

- **Tier 1 (Core):** Fields that define skill identity and discoverability. Every skill needs these.
- **Tier 2 (Claude Code Extension):** Fields that control Claude Code-specific execution behavior. Use only when needed.

## Complete Field Reference

```yaml
---
# Tier 1: Core
name: skill-identifier                    # Optional (defaults to directory name)
description: Full description...          # Recommended (primary trigger mechanism)
license: MIT                             # Optional (distribution license)
compatibility: ">=1.0.0"                 # Optional (Claude Code version constraint)

# Tier 2: Claude Code Extension
argument-hint: "[issue-number]"          # Optional
disable-model-invocation: false          # Optional (default: false)
user-invocable: true                     # Optional (default: true)
allowed-tools: Read, Grep, Glob          # Optional
model: claude-sonnet-4-20250514          # Optional
context: fork                            # Optional
agent: Explore                           # Optional (requires context: fork)
hooks: {}                                # Optional
---
```

---

## Tier 1 Fields

### Field: `name`

**Type:** String | **Required:** No (defaults to directory name) | **Max Length:** 64 characters

**Validation:**
```regex
^[a-z0-9][a-z0-9-]*[a-z0-9]$
```

**Rules:**
- Lowercase letters (a-z), numbers (0-9), hyphens (-) only
- Must start and end with letter or number
- No uppercase, spaces, underscores, or special characters
- Reserved words prohibited: `anthropic`, `claude`

**Naming Convention -- kebab-case with gerund form (-ing) strongly recommended:**

```yaml
# GOOD: Gerund form (recommended)
name: processing-pdfs
name: reviewing-code
name: managing-databases

# Acceptable alternatives
name: pdf-processing       # Noun phrase
name: process-pdfs         # Imperative

# INVALID
name: API-Docs-Writer      # Uppercase
name: api_docs_writer      # Underscores
name: api docs writer      # Spaces
name: -api-docs            # Starts with hyphen
name: claude-helper        # Reserved word
```

### Field: `description`

**Type:** String | **Required:** No (but strongly recommended) | **Max Length:** 1024 characters
**Default:** First paragraph of SKILL.md content if omitted

**CRITICAL: The description is the PRIMARY trigger mechanism.** Include ALL "when to use" information here -- NOT in the SKILL.md body. The body is only loaded AFTER the skill has already been triggered by matching the description. If trigger keywords are only in the body, they will never be seen during skill selection.

**Structure:**
```
[Action verbs] + [specific technologies/frameworks] + [problem solved].
Use when [scenario 1], [scenario 2], or [working with keywords].
```

**Good example:**
```yaml
description: >-
  Generate OpenAPI/Swagger documentation from Express routes, FastAPI endpoints,
  or GraphQL schemas. Analyzes code structure and creates comprehensive API
  specifications with request/response examples. Use when documenting APIs,
  creating API specs, or working with OpenAPI, Swagger, REST, GraphQL, API design.
```

**Bad example:**
```yaml
description: This skill handles database operations.
# No "Use when..." clause, no specific databases, no trigger keywords
```

### Field: `license`

**Type:** String | **Required:** No

Specifies the distribution license for the skill. Use SPDX identifiers.

```yaml
license: MIT
license: Apache-2.0
license: UNLICENSED
```

### Field: `compatibility`

**Type:** String | **Required:** No

Specifies the minimum Claude Code version required for this skill to function correctly. Uses semver range syntax.

```yaml
compatibility: ">=1.0.0"
compatibility: ">=1.2.0 <2.0.0"
```

If the running Claude Code version does not satisfy the constraint, the skill may be skipped or a warning displayed.

---

## Tier 2 Fields [Claude Code Extension]

### Field: `allowed-tools`

[Tier 2: Claude Code Extension]

**Type:** Comma-separated string | **Required:** No | **Default:** All tools available

Restricts Claude's tool access when the skill is active.

**Available tools:** `Read`, `Write`, `Edit`, `Grep`, `Glob`, `Bash`, `WebFetch`, `WebSearch`, `Task`

```yaml
# Read-only analysis
allowed-tools: Read, Grep, Glob

# Documentation generation (read code, write docs, no editing existing files)
allowed-tools: Read, Grep, Glob, Write

# Bash with command filter
allowed-tools: Bash(gh:*)
```

Use when: security-sensitive operations, read-only analysis, preventing accidental changes.
Skip when: skills that need full tool access.

### Field: `argument-hint`

[Tier 2: Claude Code Extension]

**Type:** String | **Required:** No

Hint displayed during `/` autocomplete in the CLI:

```yaml
argument-hint: "[issue-number]"
argument-hint: "[filename] [format]"
```

### Field: `disable-model-invocation`

[Tier 2: Claude Code Extension]

**Type:** Boolean | **Required:** No | **Default:** `false`

Controls whether Claude can automatically invoke the skill (without user's `/` command).

| Value | User Invoke | Claude Invoke | Use Case |
|-------|-------------|---------------|----------|
| `false` (default) | Yes | Yes | General skills |
| `true` | Yes | No | Deploy, commit, send (timing-sensitive) |

```yaml
disable-model-invocation: true  # Only invoked via /deploy
```

### Field: `user-invocable`

[Tier 2: Claude Code Extension]

**Type:** Boolean | **Required:** No | **Default:** `true`

Controls whether the skill appears in the `/` menu.

| Value | Menu Visible | Claude Can Load | Use Case |
|-------|--------------|-----------------|----------|
| `true` (default) | Yes | Yes | Normal skills |
| `false` | No | Yes | Background knowledge only |

```yaml
user-invocable: false  # Hidden from menu, loaded by Claude when description matches
```

### Field: `model`

[Tier 2: Claude Code Extension]

**Type:** String | **Required:** No

Explicitly specify which model to use when skill is active:

```yaml
model: claude-opus-4-5-20251101
model: claude-sonnet-4-20250514
```

### Field: `context`

[Tier 2: Claude Code Extension]

**Type:** String | **Required:** No | **Values:** `fork`

When set to `fork`, the skill executes in an isolated subagent context:

```yaml
context: fork
```

**Characteristics of fork context:**
- Main context is forked (not newly created)
- Skill content becomes the subagent's prompt
- Must include explicit task instructions (not just guidelines)
- Returns results back to main conversation

**Important: `context: fork` is designed for Task Contents (active skills), NOT Reference Contents (passive skills).** A forked agent expects SKILL.md to define **what to do**. Reference Contents only define **how to do things** (guidelines), leaving the forked agent with no clear objective.

**Correct usage (Task Contents):**
```yaml
---
name: pr-opener
context: fork
---

## Your Task
1. Get the current branch diff: `git diff main...HEAD`
2. Generate PR title based on commits
3. Create PR using: `gh pr create --title "..." --body "..."`
```

**Incorrect usage (Reference Contents):**
```yaml
---
name: coding-standards
context: fork
---

## Guidelines
- Use TypeScript strict mode
- Follow ESLint rules
# No explicit task -- forked agent won't know what to do
```

### Field: `agent`

[Tier 2: Claude Code Extension]

**Type:** String | **Required:** No (only used with `context: fork`)
**Values:** `Explore`, `Plan`, `general-purpose`, or custom agent name

Specifies the subagent type for forked execution:

| Agent Type | Purpose | Tools |
|------------|---------|-------|
| `Explore` | Read-only exploration | Read, Grep, Glob |
| `Plan` | Planning and design | All except Edit, Write |
| `general-purpose` | Full capabilities (default) | All tools |

**Dynamic context injection** -- use `!` prefix to inject command output into skill content:

```yaml
---
name: pr-summary
context: fork
agent: Explore
allowed-tools: Bash(gh:*)
---

## Context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`

## Task
Summarize this PR focusing on...
```

### Field: `hooks`

[Tier 2: Claude Code Extension]

**Type:** Object | **Required:** No

Lifecycle hooks for skill execution. See [Hooks documentation](https://docs.anthropic.com/en/docs/claude-code/hooks) for details.
