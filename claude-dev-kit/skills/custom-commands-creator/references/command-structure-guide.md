# Command Structure Guide

This guide explains the three fundamental command structure patterns and helps you choose the right one for your use case.

## The Three Basic Patterns

### Pattern 1: Simple Execution (No Arguments)

**Characteristics**:
- No user input required
- Fixed workflow execution
- Self-contained task automation

**When to Use**:
- Automated checks or fixes
- Project-wide operations
- Consistent workflows that don't need customization

**Template**:
```yaml
---
description: Clear description of what this command does
allowed-tools: Bash, Read, Write, Edit
---

# Command Title

Brief overview of command purpose.

## Workflow

1. **Step 1**: First action
   ```bash
   npm run check:all
   ```

2. **Step 2**: Second action
   - Do something
   - Do something else

3. **Step 3**: Final action
   ```bash
   npm run verify
   ```

## Success Criteria

- All checks pass
- No errors reported
```

**Real-World Example**: `fix-errors.md`
```yaml
---
description: Fix errors found by npm run check:all (lint, format, typecheck, tests)
---

## Workflow

1. **Run full quality check to identify all issues**
   ```bash
   npm run check:all
   ```
   - Collect and analyze all errors from: lint, format, typecheck, i18n, tests

2. **Auto-fix what can be fixed automatically**
   - Run `npm run lint:fix` for ESLint auto-fixes
   - Run `npm run format` for Prettier formatting
   - Re-run `npm run check:all` to verify fixes

3. **Manually fix remaining issues**
   - Prioritize by impact: typecheck errors → test failures → i18n inconsistencies
   - For each error:
     - Identify root cause
     - Propose fix with file:line reference
     - Apply fix and verify

4. **Final verification**
   ```bash
   npm run check:all
   ```
   - Confirm all checks pass
```

**Invocation**: `/fix-errors` (no arguments)

---

### Pattern 2: Single Argument ($ARGUMENTS)

**Characteristics**:
- Captures all user input as single string
- Free-form text input
- Variable-length input with spaces

**When to Use**:
- Descriptions or natural language input
- Project names or feature descriptions
- Any input that should be treated as one cohesive unit
- When exact input preservation is needed (including spaces)

**Template**:
```yaml
---
description: Command that processes user-provided text input
allowed-tools: Read, Write, Bash
argument-hint: <description>
---

# Command Title

Process the following input: **$ARGUMENTS**

## Task: Main Task Description

### Step 1: Parse Input
Extract information from: $ARGUMENTS

### Step 2: Process
Do something with the parsed input.

### Step 3: Generate Output
Create result based on input.
```

**Real-World Example**: `spec-init.md`
```yaml
---
description: Initialize a new specification with detailed project description and requirements
allowed-tools: Bash, Read, Write, Glob
argument-hint: <project-description>
---

# Spec Initialization

Initialize a new specification based on the provided project description:

**Project Description**: $ARGUMENTS

## Task: Initialize Specification Structure

**SCOPE**: This command initializes the directory structure and metadata based on the detailed project description provided.

### 1. Generate Feature Name
Create a concise, descriptive feature name from the project description ($ARGUMENTS).
**Check existing `.kiro/specs/` directory to ensure the generated feature name is unique.**

### 2. Create Spec Directory
Create `.kiro/specs/[generated-feature-name]/` directory with:
- `spec.json` - Metadata and approval tracking
- `requirements.md` - Lightweight template with project description

### 3. Initialize spec.json Metadata
Create initial metadata with approval tracking:
```json
{
  "feature_name": "[generated-feature-name]",
  "created_at": "current_timestamp",
  "updated_at": "current_timestamp",
  "language": "ja",
  "phase": "initialized",
  "approvals": {
    "requirements": {
      "generated": false,
      "approved": false
    }
  }
}
```

### 4. Create Requirements Template
Create requirements.md with project description:
```markdown
# Requirements Document

## Project Description (Input)
$ARGUMENTS

## Requirements
<!-- Will be generated in /kiro:spec-requirements phase -->
```
```

**Invocation**: `/kiro:spec-init Create a comprehensive user authentication system with email/password, OAuth, and 2FA support`
- **$ARGUMENTS** = `"Create a comprehensive user authentication system with email/password, OAuth, and 2FA support"`
- Entire sentence is preserved as single input

---

### Pattern 3: Multiple Arguments + Flags ($1, $2, $3...)

**Characteristics**:
- Multiple distinct parameters
- Positional argument access
- Flag detection (-y, --force, etc.)
- Optional parameters with defaults

**When to Use**:
- Commands with required + optional parameters
- Flag-based behavior modification
- Multiple distinct inputs that need separate processing
- When you need to detect presence/absence of specific flags

**Template**:
```yaml
---
description: Command with multiple parameters and optional flags
allowed-tools: Read, Write, Edit, Bash
argument-hint: <required-arg> [optional-flag]
---

# Command Title

Process feature: **$1**

## Prerequisites & Context Loading
- If invoked with flag ($2 == "-y"): Auto-approve and skip confirmation
- Otherwise: Perform validation checks

## Task: Main Task

### Step 1: Validate Required Argument
Feature name: $1
- Check if valid
- Check if exists

### Step 2: Process Optional Flag
If $2 == "-y":
  - Skip confirmation
  - Auto-proceed
Else:
  - Prompt for confirmation
  - Validate prerequisites

### Step 3: Execute Task
Perform main task with validated inputs.
```

**Real-World Example**: `spec-tasks.md`
```yaml
---
description: Generate implementation tasks for a specification
allowed-tools: Read, Write, Edit, MultiEdit, Glob, Grep
argument-hint: <feature-name> [-y]
---

# Implementation Tasks

Generate detailed implementation tasks for feature: **$1**

## Task: Generate Implementation Tasks

### Prerequisites & Context Loading
- If invoked with `-y` flag ($2 == "-y"): Auto-approve requirements and design in `spec.json`
- Otherwise: Stop if requirements/design missing or unapproved with message:
  "Run `/kiro:spec-requirements` and `/kiro:spec-design` first, or use `-y` flag to auto-approve"
- If tasks.md exists: Prompt [o]verwrite/[m]erge/[c]ancel

**Context Loading (Full Paths)**:
1. `.kiro/specs/$1/requirements.md` - Feature requirements (EARS format)
2. `.kiro/specs/$1/design.md` - Technical design document
3. `.kiro/steering/` - Project-wide guidelines and constraints:
   - @.kiro/steering/product.md - Business context, product vision, user needs
   - @.kiro/steering/tech.md - Technology stack, frameworks, libraries
   - @.kiro/steering/structure.md - File organization, naming conventions, code patterns
4. `.kiro/specs/$1/tasks.md` - Existing tasks (only if merge mode)

### Task Generation Rules

1. **Natural language descriptions**: Focus on capabilities and outcomes, not code structure
2. **Task integration & progression**: Each task must build on previous outputs
3. **Flexible task sizing**: As many sub-tasks as logically needed
4. **Requirements mapping**: End details with `_Requirements: X.X, Y.Y_`
5. **Code-only focus**: Include ONLY coding/testing tasks
```

**Invocation Examples**:
- `/kiro:spec-tasks auth-system` → $1="auth-system", $2="" (empty)
- `/kiro:spec-tasks auth-system -y` → $1="auth-system", $2="-y"

**Flag Detection Pattern**:
```markdown
### Prerequisites & Context Loading
- If invoked with `-y` flag ($2 == "-y"): Auto-approve requirements and design
- Otherwise: Stop if requirements/design missing or unapproved
```

---

## Pattern Selection Flowchart

```
Start: What kind of input does your command need?

┌─────────────────────────────────────┐
│ Does command need ANY user input?   │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
       NO                  YES
        │                   │
        ▼                   ▼
┌───────────────┐  ┌─────────────────────────────┐
│ Pattern 1:    │  │ How many distinct inputs?   │
│ Simple        │  └─────────────┬───────────────┘
│ Execution     │                │
└───────────────┘      ┌─────────┴─────────┐
                       │                   │
                    ONE                 MULTIPLE
                  (or free-form)         (or flags)
                       │                   │
                       ▼                   ▼
              ┌────────────────┐  ┌────────────────┐
              │ Pattern 2:     │  │ Pattern 3:     │
              │ $ARGUMENTS     │  │ $1, $2, $3...  │
              └────────────────┘  └────────────────┘
```

### Decision Questions

1. **No User Input Needed**:
   - Is this a fixed workflow?
   - Does it always do the same thing?
   - Are all parameters hard-coded?
   → **Use Pattern 1: Simple Execution**

2. **Single Free-Form Input**:
   - Is it a description or natural language?
   - Should spaces be preserved?
   - Is it treated as one cohesive unit?
   → **Use Pattern 2: $ARGUMENTS**

3. **Multiple Parameters or Flags**:
   - Are there multiple distinct inputs?
   - Do you need optional flags (-y, --force)?
   - Do parameters need separate processing?
   - Do you need to detect flag presence?
   → **Use Pattern 3: $1, $2, $3...**

## Combining Patterns

### Pattern 2 → Pattern 3 Evolution

As commands evolve, you might start with Pattern 2 and later need Pattern 3:

**Initial Version** (Pattern 2):
```yaml
argument-hint: <feature-name>
---
Feature: $ARGUMENTS
```

**Evolved Version** (Pattern 3):
```yaml
argument-hint: <feature-name> [-y]
---
Feature: $1
Auto-approve: $2 == "-y"
```

### Hybrid Approach: Last Argument as Free-Form

```yaml
---
argument-hint: <command> <target> <description>
---

Command: $1
Target: $2
Description: $3 (and all remaining arguments)
```

**Limitation**: This doesn't work well because each argument is space-separated. Better to use $ARGUMENTS if you need free-form text.

## Common Mistakes

### Mistake 1: Using $ARGUMENTS When $1 Intended

```yaml
# ❌ Bad - will capture "feature-name -y" as single string
---
argument-hint: <feature-name> [-y]
---
Feature: $ARGUMENTS
Flag check: $ARGUMENTS == "-y"  # Will never match!

# ✅ Good - separate parameters
---
argument-hint: <feature-name> [-y]
---
Feature: $1
Flag check: $2 == "-y"  # Correct flag detection
```

### Mistake 2: Using $1 for Free-Form Text

```yaml
# ❌ Bad - will only capture first word
---
argument-hint: <description>
---
Description: $1  # Only gets "Create" from "Create user authentication"

# ✅ Good - captures entire description
---
argument-hint: <description>
---
Description: $ARGUMENTS  # Gets "Create user authentication"
```

### Mistake 3: Complex Flag Logic Without Proper Structure

```yaml
# ❌ Bad - unclear flag handling
---
argument-hint: <feature> [-y] [--force] [--verbose]
---
Feature: $ARGUMENTS  # Will capture everything including flags

# ✅ Good - structured flag detection
---
argument-hint: <feature> [-y] [--force]
---
Feature: $1
Auto-approve: $2 == "-y"
Force mode: $3 == "--force"
```

## Advanced: Multi-Argument Commands

For commands with 3+ arguments, explicitly document the positional mapping:

```yaml
---
description: Deploy application to environment with specific version
argument-hint: <app-name> <environment> <version>
---

# Deployment Command

**Argument Mapping**:
- $1: Application name (required)
- $2: Environment (staging/production)
- $3: Version tag (e.g., v1.2.3)

## Validation

Application: $1
- Check if $1 is not empty
- Verify application exists

Environment: $2
- Check if $2 is "staging" or "production"
- Reject if invalid

Version: $3
- Validate version format
- Check if version exists in registry
```

## Testing Your Pattern Choice

After choosing a pattern, test with these invocations:

**Pattern 1 (No Arguments)**:
```
/your-command
/your-command extra args  # Should work but ignore args
```

**Pattern 2 ($ARGUMENTS)**:
```
/your-command single-word
/your-command Multiple words with spaces
/your-command "Quoted string with spaces"
```

**Pattern 3 ($1, $2, $3...)**:
```
/your-command arg1
/your-command arg1 arg2
/your-command arg1 -y
/your-command arg1 --force arg3
```

Verify that arguments are captured as expected by including debug output in early command versions:
```markdown
**Debug: Argument Capture**
- $1: "$1"
- $2: "$2"
- $ARGUMENTS: "$ARGUMENTS"
```

---

Use this guide to select the most appropriate pattern for your custom command's needs!
