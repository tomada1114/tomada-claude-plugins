# YAML Frontmatter Fields: Complete Reference

This guide provides comprehensive coverage of all YAML frontmatter fields available for custom commands, their impact on behavior, and best practices for each.

## Field Overview

| Field | Required | Type | Default | Purpose |
|-------|----------|------|---------|---------|
| `description` | Quasi-required | string (max 1024 chars) | First line of body | Command description for autocomplete |
| `allowed-tools` | Optional | comma-separated list | Inherit all | Tool access restrictions |
| `argument-hint` | Optional | string | None | Argument format hint |
| `model` | Optional | enum | sonnet | Claude model selection |
| `disable-model-invocation` | Optional | boolean | false | Prevent AI auto-invocation |

---

## 1. description

### Purpose
Provides a human-readable description of what the command does. This is the primary way users discover and understand your command.

### Display Locations
- **Autocomplete menu**: Shown when user types `/`
- **Command listings**: Displayed in command help and documentation
- **Error messages**: Referenced when command fails

### Rules and Constraints

**Maximum Length**: 1024 characters
- Recommended: 60-150 characters for readability
- Longer descriptions are acceptable for complex commands

**Format**: Plain text
- No markdown formatting in the description itself
- Use clear, descriptive language
- Start with action verb when possible

**Default Behavior**: If omitted, the first line of the command body is used as description

### Writing Effective Descriptions

#### Pattern 1: Action + Context
```yaml
description: Fix errors found by npm run check:all (lint, format, typecheck, tests)
```
**Structure**: `[Action] + [What] + [Details in parentheses]`

#### Pattern 2: Purpose + Use Case
```yaml
description: Initialize a new specification with detailed project description and requirements
```
**Structure**: `[Purpose] + [Additional context]`

#### Pattern 3: Comprehensive with Scope
```yaml
description: Generate implementation tasks for a specification
```
**Structure**: `[Action] + [Target] + [Optional scope]`

#### Pattern 4: Detailed with Context
```yaml
description: Create or update Kiro steering documents intelligently based on project state
```
**Structure**: `[Action] + [Target] + [How/When]`

### Best Practices

**✅ Good Examples**:
```yaml
# Clear action and scope
description: Run full quality gate and auto-fix issues

# Specific use case
description: Initialize spec with project description and requirements

# Comprehensive but concise
description: Generate implementation tasks from approved design documents
```

**❌ Bad Examples**:
```yaml
# Too vague
description: Helper command

# Too verbose (over 200 chars, still understandable but less scannable)
description: This command is designed to provide comprehensive assistance with the initialization and setup of new specification documents by accepting detailed project descriptions as input parameters and then automatically generating the necessary directory structures along with initial configuration files

# Unclear action
description: Does stuff with specs
```

### Description Length Guidelines

**60-80 characters**: Ideal for quick scanning
```yaml
description: Fix errors from quality checks (lint, format, typecheck)
```

**80-120 characters**: Good for commands needing more context
```yaml
description: Initialize new specification with detailed project description and requirements document
```

**120-200 characters**: Acceptable for complex commands
```yaml
description: Generate implementation tasks for a specification, with optional auto-approval of requirements and design phases using -y flag
```

**200+ characters**: Use sparingly, consider splitting command or documenting in body
```yaml
# Acceptable if truly needed, but consider refactoring
description: Interactive technical design quality review and validation that analyzes architecture alignment, design consistency, extensibility, and type safety to provide GO/NO-GO decision with critical issues and recommendations
```

---

## 2. allowed-tools

### Purpose
Restricts which tools the command can invoke, implementing the principle of least privilege for security.

### Syntax
Comma-separated list of exact tool names:
```yaml
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
```

### Default Behavior
If omitted, the command **inherits all tools** available in the conversation context, including:
- All built-in tools
- All MCP server tools
- All user-configured tools

### Available Tools (Common)

**File Operations**:
- `Read`: Read file contents
- `Write`: Create new files or overwrite existing
- `Edit`: Modify existing files
- `Glob`: File pattern matching
- `Grep`: Content search

**Execution**:
- `Bash`: Execute shell commands
- `BashOutput`: Read output from background bash sessions

**Other**:
- `MultiEdit`: Edit multiple files at once
- `LS`: List directory contents (usually not needed explicitly)

**Note**: Unlike sub-agents, wildcard patterns (e.g., `mcp__*`) are **NOT supported** in custom commands. You must list each tool explicitly.

### Security Principles

#### Principle 1: Minimum Necessary Tools

Grant only the tools absolutely required for the command's function.

**✅ Good Example** (Read-only validation):
```yaml
---
description: Validate design document against project standards
allowed-tools: Read, Grep, Glob
---
```

**❌ Bad Example** (Unnecessary permissions):
```yaml
---
description: Validate design document against project standards
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, MultiEdit
# Validation should not need Write, Edit, or Bash
---
```

#### Principle 2: Progressive Permission Granting

Start with minimal tools and add only when needed.

**Evolution Example**:
```yaml
# Version 1: Analysis only
allowed-tools: Read, Grep

# Version 2: Add reporting
allowed-tools: Read, Grep, Write

# Version 3: Add automated fixes
allowed-tools: Read, Grep, Write, Edit
```

### Tool Permission Patterns

#### Pattern 1: Read-Only Commands
**Use Case**: Analysis, validation, reporting without modifications

```yaml
allowed-tools: Read, Grep, Glob
```

**Examples**:
- Code analysis
- Documentation validation
- Project structure inspection
- Statistics generation (read-only)

#### Pattern 2: File Creation Commands
**Use Case**: Generate new files without modifying existing ones

```yaml
allowed-tools: Read, Glob, Write
```

**Examples**:
- Template generation
- New file scaffolding
- Report generation
- Documentation creation

#### Pattern 3: File Modification Commands
**Use Case**: Update existing files

```yaml
allowed-tools: Read, Glob, Grep, Edit
```

**Examples**:
- Configuration updates
- Code refactoring
- Content updates
- Metadata changes

#### Pattern 4: Full Project Automation
**Use Case**: Complex workflows requiring execution

```yaml
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
```

**Examples**:
- Build and deploy workflows
- Multi-step automation
- Git operations
- Package management

**⚠️ Caution**: Use Bash permission carefully as it allows arbitrary command execution

#### Pattern 5: Bash-Integrated Context Gathering
**Use Case**: Commands using `!` prefix for pre-execution bash

```yaml
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
```

**Required for**:
- Commands with `!`git status``
- Commands with `!`[ -f file.md ]``
- Any pre-execution bash integration

**Important**: Even read-only bash commands (like `git log`, `ls`) require `allowed-tools: Bash`

### MCP Server Tools

**Limitation**: Custom commands cannot use wildcard patterns for MCP tools.

**❌ Not Supported**:
```yaml
allowed-tools: Read, Write, mcp__expo-mcp__*
```

**✅ Must List Explicitly**:
```yaml
allowed-tools: Read, Write, mcp__expo-mcp__search_docs, mcp__expo-mcp__install_library
```

**Recommendation**: For MCP-heavy commands, consider omitting `allowed-tools` to inherit all available tools, or use sub-agents instead of custom commands.

### Testing Tool Restrictions

**Test Method**: Intentionally try restricted operation

```markdown
## Test Tool Restrictions

Try to use Write (should fail if not in allowed-tools):
- Create test file at /tmp/test-restriction.txt
- If this succeeds, tool restriction is NOT working
- If this fails, tool restriction is working correctly
```

---

## 3. argument-hint

### Purpose
Provides a visual hint about expected argument format in autocomplete and command help.

### Syntax
Plain text string shown after command name:
```yaml
argument-hint: <required-arg> [optional-arg]
```

### Display Location
**Autocomplete**: User sees `/command-name <required-arg> [optional-arg]`

### Format Conventions

#### Convention 1: Angle Brackets for Required
```yaml
argument-hint: <feature-name>
argument-hint: <file-path>
argument-hint: <description>
```

#### Convention 2: Square Brackets for Optional
```yaml
argument-hint: <feature-name> [-y]
argument-hint: <command> [--force]
argument-hint: <file> [--verbose] [--dry-run]
```

#### Convention 3: Descriptive Names
```yaml
# ✅ Good - clear what's expected
argument-hint: <feature-name> [-y]
argument-hint: <app-name> <environment> <version>

# ❌ Bad - vague
argument-hint: <arg1> <arg2>
argument-hint: <input>
```

### Relationship with Argument Patterns

#### For $ARGUMENTS Commands
```yaml
---
argument-hint: <project-description>
---

Project Description: $ARGUMENTS
```
**Hint indicates**: Expects free-form text input

#### For Positional Arguments ($1, $2, $3...)
```yaml
---
argument-hint: <feature-name> [-y]
---

Feature: $1
Auto-approve: $2 == "-y"
```
**Hint indicates**: First argument required, second is optional flag

#### For No-Argument Commands
```yaml
---
# Omit argument-hint entirely
---
```
**No hint**: Command takes no arguments

### Advanced Hint Patterns

#### Multiple Required Arguments
```yaml
argument-hint: <app-name> <environment> <version>
```
Maps to: `$1`, `$2`, `$3`

#### Optional Arguments with Defaults
```yaml
argument-hint: <feature-name> [environment]
```
Indicates: Second argument is optional (command provides default)

#### Flags with Values
```yaml
argument-hint: <feature> [--mode=<mode>] [-y]
```
Indicates: Flag can take a value

### Best Practices

**✅ Good Examples**:
```yaml
# Clear required + optional distinction
argument-hint: <feature-name> [-y]

# Multiple clear parameters
argument-hint: <app-name> <environment>

# Optional with context
argument-hint: <spec-name> [--force]
```

**❌ Bad Examples**:
```yaml
# Too vague
argument-hint: <args>

# Unclear optionality
argument-hint: feature-name flag

# Inconsistent formatting
argument-hint: <feature> optional-arg
```

---

## 4. model

### Purpose
Specifies which Claude model to use for processing this command.

### Available Values

| Model | Characteristics | Best For |
|-------|----------------|----------|
| `sonnet` | Balanced performance/cost | General-purpose commands (default) |
| `opus` | Highest quality, slowest | Complex analysis, critical decisions |
| `haiku` | Fastest, cheapest | Simple tasks, quick checks |
| `inherit` | Use conversation's model | Consistent experience across session |

### Default Behavior
If omitted, defaults to `sonnet` (or the system default).

### Use Cases by Model

#### sonnet (Default)
**Best For**:
- General-purpose commands
- Standard workflow automation
- Balanced speed and quality needs

**Example Commands**:
```yaml
model: sonnet  # Or omit for default
```
- Code generation
- File operations
- Standard analysis

#### opus (Premium)
**Best For**:
- Complex architectural decisions
- Critical design reviews
- Multi-step reasoning
- High-stakes operations

**Example Commands**:
```yaml
model: opus
```
- Architecture validation
- Comprehensive code review
- Strategic planning
- Complex refactoring decisions

**⚠️ Consideration**: Higher cost and latency

#### haiku (Economy)
**Best For**:
- Simple validation checks
- Quick formatting tasks
- Straightforward operations
- High-frequency commands

**Example Commands**:
```yaml
model: haiku
```
- Syntax validation
- Simple file operations
- Quick status checks
- Format verification

**✅ Benefit**: Significantly faster and cheaper

#### inherit (Contextual)
**Best For**:
- Commands that should match user's current session model
- Maintaining consistent quality level across workflow
- When user has explicitly chosen a model for their session

**Example Commands**:
```yaml
model: inherit
```
- Commands that are part of larger workflow
- Commands where user's model preference should apply

### Selection Guidelines

**Decision Flow**:
```
Is this a critical decision or complex analysis?
├─ YES → opus
└─ NO ↓

Is this a simple, straightforward task?
├─ YES → haiku
└─ NO ↓

Should this match user's session model?
├─ YES → inherit
└─ NO → sonnet (default)
```

### Best Practices

**✅ Good Model Choices**:
```yaml
# Critical architecture review
---
description: Interactive technical design quality review and validation
model: opus
---

# Quick syntax check
---
description: Validate JSON syntax in configuration files
model: haiku
---

# General workflow
---
description: Generate implementation tasks from design
model: sonnet  # or omit
---
```

**❌ Poor Model Choices**:
```yaml
# Overkill - simple task using opus
---
description: Format code with prettier
model: opus  # haiku would be sufficient
---

# Underpowered - complex task using haiku
---
description: Comprehensive architecture refactoring analysis
model: haiku  # opus or sonnet recommended
---
```

---

## 5. disable-model-invocation

### Purpose
Prevents Claude from automatically invoking this command based on context. Command can only be manually triggered by user typing `/command-name`.

### Type and Default
- **Type**: boolean
- **Default**: `false` (command can be auto-invoked)
- **Values**: `true` | `false`

### When to Use

#### Use Case 1: Destructive Operations
Commands that modify production systems or delete data:
```yaml
---
description: Deploy to production environment with database migrations
disable-model-invocation: true
---
```

**Reason**: Prevents accidental deployment during casual conversation

#### Use Case 2: Administrative Commands
Commands meant for maintainers only:
```yaml
---
description: Reset all specification approvals (admin only)
disable-model-invocation: true
---
```

**Reason**: Should only run when explicitly requested

#### Use Case 3: Debug/Development Commands
Commands used for debugging or testing:
```yaml
---
description: Dump internal state for debugging purposes
disable-model-invocation: true
---
```

**Reason**: Not part of normal workflow, only manual invocation

#### Use Case 4: Infrequent Operations
Commands that are rarely needed:
```yaml
---
description: Archive old specifications and clean up directories
disable-model-invocation: true
---
```

**Reason**: User should consciously decide when to run

### When NOT to Use (Keep Default: false)

**Normal Workflow Commands**:
```yaml
# ✅ Good - allow auto-invocation for workflow commands
---
description: Fix errors found by quality checks
# disable-model-invocation: false (default, omit field)
---
```

**Convenience Commands**:
```yaml
# ✅ Good - user might want AI to suggest this
---
description: Generate implementation tasks for specification
# Allow auto-invocation
---
```

### Examples

**With Auto-Invocation Disabled**:
```yaml
---
description: Deploy application to production with zero-downtime rollout
allowed-tools: Bash, Read
disable-model-invocation: true
---

# Production Deployment

⚠️ **WARNING**: This command deploys to production.

Ensure:
- [ ] All tests pass
- [ ] Staging deployment successful
- [ ] Team notified
```

**User Experience**:
- User types: `/deploy-production`
- AI will NOT suggest: "Would you like me to deploy to production?"
- Prevents: Accidental deployment from casual conversation

**With Auto-Invocation Enabled** (Default):
```yaml
---
description: Run quality checks and auto-fix issues
allowed-tools: Bash, Read, Write, Edit
# disable-model-invocation: false (default)
---
```

**User Experience**:
- User says: "I've made some changes"
- AI might suggest: "Would you like me to run quality checks with `/fix-errors`?"
- Enables: Helpful automation suggestions

---

## Field Combination Strategies

### Strategy 1: Maximum Safety (Read-Only Validation)
```yaml
---
description: Validate design against project standards
allowed-tools: Read, Grep, Glob
argument-hint: <feature-name>
model: sonnet
disable-model-invocation: false
---
```

**Use For**: Analysis, validation, reporting

### Strategy 2: Workflow Automation (Moderate Risk)
```yaml
---
description: Fix errors from quality checks and auto-apply fixes
allowed-tools: Read, Write, Edit, Bash
model: sonnet
disable-model-invocation: false
---
```

**Use For**: Standard development workflows

### Strategy 3: Critical Operations (Manual Only)
```yaml
---
description: Deploy to production with database migrations
allowed-tools: Bash, Read
model: opus
disable-model-invocation: true
---
```

**Use For**: High-stakes operations, administrative tasks

### Strategy 4: Quick Checks (Fast & Safe)
```yaml
---
description: Validate JSON syntax in configuration files
allowed-tools: Read, Grep
model: haiku
disable-model-invocation: false
---
```

**Use For**: Frequent, simple validations

---

## Complete Examples by Use Case

### Use Case 1: Simple Workflow Automation
```yaml
---
description: Run test suite and generate coverage report
allowed-tools: Bash, Read, Write
model: sonnet
---
```

### Use Case 2: Complex Analysis
```yaml
---
description: Comprehensive code quality analysis with architectural review
allowed-tools: Read, Grep, Glob, Write
model: opus
---
```

### Use Case 3: Quick Utility
```yaml
---
description: Format code with prettier and eslint
allowed-tools: Bash, Read
model: haiku
---
```

### Use Case 4: Critical Manual Operation
```yaml
---
description: Deploy to production environment with rollback capability
allowed-tools: Bash, Read, Write
argument-hint: <version-tag>
model: opus
disable-model-invocation: true
---
```

### Use Case 5: Context-Rich Command
```yaml
---
description: Initialize specification with project description and requirements
allowed-tools: Bash, Read, Write, Glob
argument-hint: <project-description>
model: sonnet
---
```

---

## Validation Checklist

When defining frontmatter for your command, verify:

- [ ] **description**: Clear, concise (60-150 chars ideal), starts with action verb
- [ ] **allowed-tools**: Minimum necessary tools for the task
- [ ] **argument-hint**: Matches actual argument usage ($ARGUMENTS vs $1/$2/$3)
- [ ] **model**: Appropriate for task complexity (haiku/sonnet/opus)
- [ ] **disable-model-invocation**: `true` only for destructive/admin commands
- [ ] All field names spelled correctly (no typos)
- [ ] YAML syntax valid (spaces, not tabs)
- [ ] Combination makes sense for intended use case

---

Use this reference to make informed decisions about each frontmatter field for your custom commands!
