# YAML Frontmatter Specification

This document provides the complete specification for YAML frontmatter fields in Claude Code skills.

## Complete Field Reference

```yaml
---
name: skill-identifier                    # Optional (defaults to directory name)
description: Full description...          # Recommended (first paragraph used if omitted)
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

## Field: `name`

**Type:** String
**Required:** No (defaults to directory name)
**Max Length:** 64 characters

**Validation Rules:**
```regex
^[a-z0-9][a-z0-9-]*[a-z0-9]$
```

**Rules:**
- Must start and end with lowercase letter or number
- Can contain lowercase letters (a-z)
- Can contain numbers (0-9)
- Can contain hyphens (-) as separators
- Cannot contain:
  - Uppercase letters
  - Spaces
  - Underscores (_)
  - Special characters (!@#$%^&* etc.)

**Prohibited Patterns:**
- XML-like tags (e.g., `<skill>`, `</name>`)
- Reserved words: `anthropic`, `claude`

**Recommended Naming Style - Gerund Form (-ing):**

The gerund form (ending in -ing) is **strongly recommended** because it clearly expresses what capability the skill provides:

```yaml
# ✅ BEST: Gerund form (strongly recommended)
name: processing-pdfs
name: analyzing-spreadsheets
name: managing-databases
name: testing-code
name: writing-documentation
name: reviewing-code
name: explaining-code
```

**Acceptable Alternatives:**
```yaml
# Noun phrases
name: pdf-processing
name: spreadsheet-analysis

# Action-oriented
name: process-pdfs
name: analyze-spreadsheets
```

**Invalid Examples:**
```yaml
name: API-Docs-Writer       # ✗ Uppercase letters
name: api_docs_writer       # ✗ Underscores
name: api docs writer       # ✗ Spaces
name: api-docs-writer!      # ✗ Special characters
name: ApiDocsWriter         # ✗ CamelCase
name: -api-docs            # ✗ Starts with hyphen
name: api-docs-            # ✗ Ends with hyphen
name: claude-helper        # ✗ Reserved word
name: anthropic-tools      # ✗ Reserved word
```

## Field: `description`

**Type:** String
**Required:** No (but strongly recommended)
**Max Length:** 1024 characters
**Default:** First paragraph of SKILL.md content if omitted

**Purpose:**
The description is crucial for skill activation. It must tell Claude:
1. **What** the skill does
2. **When** to use it
3. **Trigger keywords** that should activate it

**Recommended Structure:**
```
[Action verbs] + [specific technologies/frameworks] + [problem solved].
Use when [scenario 1], [scenario 2], or [working with keywords].
```

**Components:**

1. **Action Verbs** (choose relevant ones):
   - Generate, Create, Implement, Build
   - Analyze, Review, Inspect, Examine
   - Transform, Convert, Process, Parse
   - Validate, Check, Verify, Test
   - Document, Explain, Describe

2. **Technology Keywords**:
   - Framework names: React, Vue, Django, Express, FastAPI
   - Languages: TypeScript, Python, JavaScript, Go, Rust
   - Tools: Jest, Pytest, Docker, Git, npm
   - File types: .csv, .json, .yaml, .md, .pdf
   - Protocols: REST, GraphQL, WebSocket, gRPC

3. **Trigger Scenarios**:
   - Specific user actions: "creating components", "writing tests"
   - Problem domains: "API documentation", "database migration"
   - Workflows: "setting up projects", "deploying applications"

**Quality Checklist:**
- [ ] Includes specific action verbs
- [ ] Names technologies/frameworks explicitly
- [ ] Lists trigger scenarios with "Use when..."
- [ ] Contains keywords users would naturally say
- [ ] Under 1024 characters
- [ ] Differentiates from similar skills

**Example Analysis:**

```yaml
# ✅ EXCELLENT: Specific, trigger-rich, clear
description: Generate OpenAPI/Swagger documentation from Express routes, FastAPI endpoints, or GraphQL schemas. Analyzes code structure and creates comprehensive API specifications with request/response examples. Use when documenting APIs, creating API specs, or working with OpenAPI, Swagger, REST, GraphQL, API design.

# Why this works:
# - Action: "Generate", "Analyzes", "creates"
# - Technologies: Express, FastAPI, GraphQL, OpenAPI, Swagger
# - Problem: API documentation, specifications
# - Triggers: "documenting APIs", "creating API specs", "API design"
# - Keywords: OpenAPI, Swagger, REST, GraphQL (appears multiple times)
```

```yaml
# ✅ GOOD: Clear purpose with triggers
description: Implement comprehensive tests with test design tables, equivalence partitioning, boundary value analysis, and 100% branch coverage. Use when writing tests, adding test cases, or improving test coverage for React Native/Expo TypeScript code with Jest.

# Why this works:
# - Specific methodologies: equivalence partitioning, boundary value
# - Clear goal: 100% branch coverage
# - Technologies: React Native, Expo, TypeScript, Jest
# - Triggers: "writing tests", "test coverage"
```

```yaml
# ⚠️ MEDIOCRE: Too generic
description: Helps with API development and testing. Use when working on APIs.

# Problems:
# - Vague action: "Helps with"
# - No specific technologies
# - Generic trigger: "working on APIs"
# - Missing specific capabilities
```

```yaml
# ✗ BAD: No triggers, too vague
description: This skill handles database operations.

# Problems:
# - No "Use when..." clause
# - No specific databases mentioned
# - Unclear what "handles" means
# - No trigger keywords
```

## Field: `allowed-tools`

**Type:** Comma-separated string
**Required:** No
**Default:** All tools available

**Purpose:**
Restricts Claude's tool access when the skill is active. Use for:
- Security (prevent modifications)
- Compliance (enforce policies)
- Safety (read-only operations)
- Focus (limit distractions)

**Available Tools:**
- `Read` - Read file contents
- `Write` - Create new files
- `Edit` - Modify existing files
- `Grep` - Search for patterns
- `Glob` - Find files by pattern
- `Bash` - Execute bash commands
- `WebFetch` - Fetch web content
- `WebSearch` - Search the web
- `Task` - Launch sub-agents

**Syntax:**
```yaml
allowed-tools: Read, Grep, Glob
```

**Use Cases:**

1. **Read-Only Analysis:**
```yaml
---
name: code-analyzer
description: Analyze code without modifications...
allowed-tools: Read, Grep, Glob
---
```

2. **Documentation Only:**
```yaml
---
name: doc-generator
description: Generate documentation...
allowed-tools: Read, Grep, Glob, Write
---
# Can read code and write docs, but not edit existing code
```

3. **Safe Exploration:**
```yaml
---
name: codebase-explorer
description: Explore unfamiliar codebases...
allowed-tools: Read, Grep, Glob
---
# No modifications possible
```

**When to Use:**
- ✅ Security-sensitive operations
- ✅ Compliance requirements
- ✅ Read-only analysis
- ✅ Preventing accidental changes
- ✅ Learning/exploring codebases

**When NOT to Use:**
- ❌ Skills that need to modify code
- ❌ General-purpose skills
- ❌ When flexibility is needed

## Field: `argument-hint`

**Type:** String
**Required:** No

Hint displayed during `/` autocomplete:

```yaml
---
name: fix-issue
argument-hint: "[issue-number]"
---
```

Or for multiple arguments:
```yaml
argument-hint: "[filename] [format]"
```

## Field: `disable-model-invocation`

**Type:** Boolean
**Required:** No
**Default:** `false`

Controls whether Claude can automatically invoke the skill:

| Value | User Invoke | Claude Invoke | Use Case |
|-------|-------------|---------------|----------|
| `false` (default) | ✅ Yes | ✅ Yes | General skills |
| `true` | ✅ Yes | ❌ No | Deploy, commit, send (timing-sensitive) |

```yaml
---
name: deploy
description: Deploy to production
disable-model-invocation: true
---
```

## Field: `user-invocable`

**Type:** Boolean
**Required:** No
**Default:** `true`

Controls whether the skill appears in the `/` menu:

| Value | Menu Visible | Claude Can Load | Use Case |
|-------|--------------|-----------------|----------|
| `true` (default) | ✅ Yes | ✅ Yes | Normal skills |
| `false` | ❌ No | ✅ Yes | Background knowledge only |

```yaml
---
name: legacy-system-context
description: How the legacy auth system works
user-invocable: false
---
```

## Field: `model`

**Type:** String
**Required:** No

Explicitly specify which model to use when skill is active:

```yaml
---
name: complex-analysis
model: claude-opus-4-5-20251101
---
```

## Field: `context`

**Type:** String
**Required:** No
**Values:** `fork`

When set to `fork`, the skill executes in an isolated subagent context:

```yaml
---
name: deep-research
context: fork
agent: Explore
---
```

**Characteristics of fork context:**
- Conversation history is NOT accessible
- Skill content becomes the subagent's prompt
- Must include explicit task instructions (not just guidelines)
- Returns results back to main conversation

## Field: `agent`

**Type:** String
**Required:** No (only used with `context: fork`)
**Values:** `Explore`, `Plan`, `general-purpose`

Specifies the subagent type for forked execution:

| Agent Type | Purpose | Tools |
|------------|---------|-------|
| `Explore` | Read-only exploration | Read, Grep, Glob |
| `Plan` | Planning and design | All except Edit, Write |
| `general-purpose` | Full capabilities (default) | All tools |

**Dynamic context injection:**

Use `!` prefix to inject command output into skill content:

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

## Field: `hooks`

**Type:** Object
**Required:** No

Lifecycle hooks for skill execution. See [Hooks documentation](https://docs.anthropic.com/en/docs/claude-code/hooks) for details.
