# Argument Patterns and Bash Integration

This guide covers advanced argument handling patterns and comprehensive Bash integration techniques for custom commands.

## Argument Patterns Overview

### $ARGUMENTS vs Positional Arguments

| Feature | $ARGUMENTS | $1, $2, $3... |
|---------|------------|---------------|
| **Captures** | All arguments as single string | Individual space-separated arguments |
| **Preserves spaces** | Yes, completely | Only within quoted arguments |
| **Best for** | Free-form text, descriptions | Multiple distinct parameters |
| **Flag detection** | Difficult (string matching) | Easy ($2 == "-y") |
| **Optional params** | Not supported | Supported ($2, $3 can be empty) |
| **Argument count** | Always 1 (all or nothing) | Variable (check if empty) |

### Visual Comparison

**Input**: `/command create user authentication -y`

**With $ARGUMENTS**:
```markdown
$ARGUMENTS = "create user authentication -y"
```
- Entire input as one string
- Cannot distinguish between "create", "user", "authentication", "-y"

**With Positional**:
```markdown
$1 = "create"
$2 = "user"
$3 = "authentication"
$4 = "-y"
```
- Each space-separated word is individual argument
- Can process each independently

---

## Pattern 1: $ARGUMENTS (All Arguments as String)

### Use Cases

1. **Natural Language Input**
```yaml
---
argument-hint: <project-description>
---

Description: $ARGUMENTS
```
**Example**: `/spec-init Create a comprehensive authentication system with OAuth2 and JWT`

2. **Search Queries**
```yaml
---
argument-hint: <search-query>
---

Query: $ARGUMENTS
```
**Example**: `/search-docs how to implement push notifications`

3. **Commit Messages**
```yaml
---
argument-hint: <commit-message>
---

Commit message: $ARGUMENTS
```
**Example**: `/quick-commit fix: resolve memory leak in user session management`

### Benefits
- ✅ Preserves exact user input
- ✅ No need to worry about spaces
- ✅ Natural for free-form text
- ✅ Simpler mental model for users

### Limitations
- ❌ Cannot detect flags (-y, --force)
- ❌ Cannot have optional parameters
- ❌ Cannot process arguments individually
- ❌ Cannot provide defaults for missing parts

### Implementation Example

```yaml
---
description: Initialize new specification with project description
argument-hint: <project-description>
allowed-tools: Read, Write, Bash
---

# Spec Initialization

**Project Description**: $ARGUMENTS

## Processing

### Step 1: Generate Feature Name
Extract key concepts from: "$ARGUMENTS"
- Tokenize description
- Create kebab-case name
- Ensure uniqueness

### Step 2: Create Structure
Using project description: $ARGUMENTS
```

---

## Pattern 2: Positional Arguments ($1, $2, $3...)

### Use Cases

1. **Required + Optional Parameters**
```yaml
---
argument-hint: <feature-name> [environment]
---

Feature: $1 (required)
Environment: $2 (optional, defaults to "development")
```

2. **Flag Detection**
```yaml
---
argument-hint: <feature-name> [-y]
---

Feature: $1
Auto-approve: $2 == "-y"
```

3. **Multiple Distinct Inputs**
```yaml
---
argument-hint: <app-name> <environment> <version>
---

Application: $1
Environment: $2
Version: $3
```

### Benefits
- ✅ Individual argument access
- ✅ Easy flag detection
- ✅ Optional parameters supported
- ✅ Can provide defaults
- ✅ Argument validation per-field

### Limitations
- ❌ Spaces split arguments (unless quoted)
- ❌ More complex for free-form text
- ❌ Requires argument counting logic

### Implementation Example

```yaml
---
description: Generate implementation tasks for specification
argument-hint: <feature-name> [-y]
allowed-tools: Read, Write, Edit
---

# Implementation Tasks

Generate tasks for feature: **$1**

## Prerequisites Validation

**Argument Check**:
- Feature name ($1): Required
  - Stop if empty: "Error: Feature name required"
  - Validate format: kebab-case

- Auto-approve flag ($2): Optional
  - If $2 == "-y": Skip approval checks
  - If $2 == "": Require manual approval
  - Otherwise: Show warning "Unknown flag: $2"

## Context Loading

Load specification files for feature: $1
- Requirements: `.kiro/specs/$1/requirements.md`
- Design: `.kiro/specs/$1/design.md`
- Metadata: `.kiro/specs/$1/spec.json`
```

---

## Flag Detection Patterns

### Basic Flag Check

```markdown
## Auto-Approve Check

If invoked with `-y` flag:
- $2 == "-y": Skip confirmation, proceed automatically
- Otherwise: Prompt for approval

**Example**:
- `/command feature -y` → Auto-approve
- `/command feature` → Manual approval
```

### Multiple Flag Support

```markdown
## Flag Processing

**Supported Flags**:
- $2: Primary flag (-y, --force, or empty)
- $3: Secondary flag (--verbose, --dry-run, or empty)

**Flag Logic**:
1. Check $2:
   - "-y": Enable auto-approve
   - "--force": Enable force mode
   - "": No primary flag

2. Check $3:
   - "--verbose": Enable verbose logging
   - "--dry-run": Enable dry-run mode
   - "": No secondary flag
```

### Flag with Value Pattern

**Note**: Direct flag values (e.g., `--mode=staging`) are **not easily supported** since each space creates a new argument. Workaround is to use separate arguments:

```markdown
## Flag Pattern with Value

**Recommended**:
- `/command feature --mode staging`
  - $1: "feature"
  - $2: "--mode"
  - $3: "staging"

**Processing**:
If $2 == "--mode":
  Mode value: $3
Else if $2 == "-y":
  Auto-approve: true
```

### Default Values for Optional Arguments

```markdown
## Argument Defaults

Feature name: $1 (required)
Environment: ${2:-"development"}  # Use $2 if provided, else "development"
Verbose: $3 (empty = false, "-v" = true)

**Processing**:
1. Feature: $1
   - Stop if empty

2. Environment: $2
   - If empty: Use "development"
   - If provided: Use $2
   - Validate: "development", "staging", "production"

3. Verbose flag: $3
   - If $3 == "-v": Enable verbose mode
   - Otherwise: Standard output
```

---

## Bash Integration: The `!` Prefix

### Purpose
Execute bash commands **before** the slash command runs, injecting output into the command prompt.

### Syntax
```markdown
Line content: !`bash command here`
```

**Important**:
- Must be on its own line or as inline text
- Surrounded by backticks: `` !`command` ``
- Output is captured and shown to Claude
- Requires `allowed-tools: Bash` in frontmatter

### Use Cases

#### 1. File Existence Checks

```yaml
---
allowed-tools: Bash, Read, Write
---

## File Status Check

- Product overview: !`[ -f ".kiro/steering/product.md" ] && echo "✅ EXISTS" || echo "📝 Not found"`
- Tech stack: !`[ -f ".kiro/steering/tech.md" ] && echo "✅ EXISTS" || echo "📝 Not found"`
```

**Output**:
```
- Product overview: ✅ EXISTS
- Tech stack: 📝 Not found
```

#### 2. Git Status and History

```yaml
---
allowed-tools: Bash, Read
---

## Project State Analysis

**Git Status**:
- Current branch: !`git branch --show-current`
- Uncommitted changes: !`git status --porcelain | wc -l | awk '{print $1 " files"}'`
- Recent commits: !`git log --oneline --max-count=5`
```

**Output**:
```
**Git Status**:
- Current branch: main
- Uncommitted changes: 3 files
- Recent commits:
  a1b2c3d feat: add new feature
  e4f5g6h fix: resolve bug
  ...
```

#### 3. Project File Discovery

```yaml
---
allowed-tools: Bash, Read
---

## Codebase Analysis

**Source Files**:
- TypeScript files: !`find src -name "*.ts" -type f | wc -l`
- Test files: !`find src -name "*.test.ts" -type f | wc -l`
- Components: !`find src/components -name "*.tsx" -type f 2>/dev/null | head -5`
```

#### 4. Conditional Logic with Variables

```yaml
---
allowed-tools: Bash, Read, Write
---

## Conditional Check

**Steering Update Status**:
- Last update: !`LAST_COMMIT=$(git log -1 --format=%H -- .kiro/steering/ 2>/dev/null); if [ -n "$LAST_COMMIT" ]; then git log -1 --format="%h %s" $LAST_COMMIT; else echo "No previous update"; fi`
- Commits since: !`LAST=$(git log -1 --format=%H -- .kiro/steering/ 2>/dev/null); if [ -n "$LAST" ]; then git log --oneline ${LAST}..HEAD --max-count=10; else echo "First time"; fi`
```

**Complex bash with variable capture and conditional logic is fully supported.**

#### 5. Environment Checks

```yaml
---
allowed-tools: Bash
---

## Environment Validation

**System Info**:
- Node version: !`node --version 2>/dev/null || echo "Not installed"`
- npm version: !`npm --version 2>/dev/null || echo "Not installed"`
- Package manager: !`[ -f "package-lock.json" ] && echo "npm" || [ -f "yarn.lock" ] && echo "yarn" || [ -f "pnpm-lock.yaml" ] && echo "pnpm" || echo "unknown"`
```

### Advanced Bash Patterns

#### Multi-Command Chaining

```bash
!`cd src && find . -name "*.ts" | head -10`
```

#### Error Handling

```bash
!`command 2>/dev/null || echo "Command failed or not found"`
```

#### Complex Logic

```bash
!`for dir in src app lib; do [ -d "$dir" ] && echo "Found: $dir" || echo "Missing: $dir"; done`
```

#### Counting and Formatting

```bash
!`find . -name "*.md" | wc -l | awk '{print $1 " markdown files"}'`
```

### Bash Integration Best Practices

**✅ Good Examples**:
```yaml
# Simple, clear check
- File exists: !`[ -f "README.md" ] && echo "Yes" || echo "No"`

# Safe command with fallback
- Git status: !`git status --short 2>/dev/null || echo "Not a git repo"`

# Formatted output
- File count: !`find src -name "*.ts" | wc -l | awk '{print $1}'`
```

**❌ Bad Examples**:
```yaml
# Dangerous - no error handling
- Status: !`rm -rf /tmp/*`

# Overly complex - hard to debug
- Complex: !`cd $(find . -name src) && ls | grep -E ".*\.ts$" | sort | uniq | wc -l`

# Side effects - modifies system
- Build: !`npm install && npm run build`
```

**Security Considerations**:
- ⚠️ Bash commands run with user's permissions
- ⚠️ Avoid destructive operations (`rm`, `mv`, etc.)
- ⚠️ Use read-only commands when possible
- ⚠️ Always handle errors (2>/dev/null, || echo)
- ⚠️ Be cautious with commands that modify state

---

## File References: The `@` Prefix

### Purpose
Include file contents directly in the command prompt without explicit Read tool calls.

### Syntax
```markdown
- File name: @path/to/file.md
- Config: @package.json
```

**Important**:
- Relative paths from project root
- No `allowed-tools` requirement for `@` references
- File contents are automatically loaded
- If file doesn't exist, error is shown to Claude

### Use Cases

#### 1. Configuration Loading

```yaml
---
description: Update project documentation based on current config
---

## Configuration Context

**Current Configuration**:
- Package info: @package.json
- TypeScript config: @tsconfig.json
- Environment template: @.env.example
```

#### 2. Documentation Reference

```yaml
---
description: Update steering documents with latest project info
---

## Existing Documentation

**Current Docs**:
- README: @README.md
- Contributing: @CONTRIBUTING.md
- Changelog: @CHANGELOG.md
```

#### 3. Code Context Loading

```yaml
---
description: Analyze architecture consistency
---

## Architecture Context

**Existing Patterns**:
- Domain layer example: @src/domain/user/User.ts
- Use case example: @src/application/auth/LoginUseCase.ts
- Infrastructure example: @src/infrastructure/api/UserApi.ts
```

#### 4. Steering Documents

```yaml
---
description: Generate implementation tasks with full project context
---

## Project Guidelines

**Steering Documents**:
- Product vision: @.kiro/steering/product.md
- Tech stack: @.kiro/steering/tech.md
- Code structure: @.kiro/steering/structure.md
```

#### 5. Specification Files

```yaml
---
argument-hint: <feature-name>
---

## Specification Context for: $1

**Feature Documents**:
- Requirements: @.kiro/specs/$1/requirements.md
- Design: @.kiro/specs/$1/design.md
- Tasks: @.kiro/specs/$1/tasks.md
- Metadata: @.kiro/specs/$1/spec.json
```

**Note**: Using `$1` in file paths is supported!

### File Reference Best Practices

**✅ Good Examples**:
```yaml
# Clear file purpose
- Main config: @package.json
- Project README: @README.md

# Grouped by category
**Documentation**:
- README: @README.md
- API docs: @docs/api.md

**Configuration**:
- Package: @package.json
- TypeScript: @tsconfig.json
```

**❌ Bad Examples**:
```yaml
# Too many files (performance impact)
@src/**/*.ts  # This won't work, need specific paths

# No context about why
@file1.md
@file2.md
@file3.md

# Absolute paths (less portable)
@/Users/username/project/README.md
```

### Performance Considerations

**File Reference Limits**:
- Each `@` reference adds file content to prompt
- Large files increase token usage
- Recommend: Limit to 5-10 file references per command
- Consider file size when referencing

**Optimization**:
```yaml
# ✅ Good - specific files only
@src/domain/User.ts
@package.json

# ❌ Bad - would need many references
# Instead use Glob/Grep tools in command body
```

---

## Combining Patterns: Advanced Examples

### Example 1: Dynamic File Loading with Bash + File Reference

```yaml
---
description: Load specification based on latest commit
allowed-tools: Bash, Read
---

## Dynamic Spec Loading

**Latest Spec**:
- Most recent: !`ls -t .kiro/specs/*/spec.json | head -1 | cut -d'/' -f3`
- Spec file: @.kiro/specs/!`ls -t .kiro/specs/ | head -1`/spec.json
```

**Note**: Nested `!` in `@` path is **not supported**. Use separate steps instead:

```yaml
## Dynamic Spec Loading (Corrected)

**Step 1: Find Latest**:
- Latest feature: !`ls -t .kiro/specs/ | head -1`

**Step 2: Reference in Command**
Now load `.kiro/specs/[feature-from-step-1]/spec.json`
```

### Example 2: Conditional File Loading

```yaml
---
allowed-tools: Bash, Read
---

## Conditional Loading

**Configuration**:
- Has custom config: !`[ -f "config.custom.json" ] && echo "Yes" || echo "No"`

**Load Config**:
If custom config exists:
  - Custom: @config.custom.json
Otherwise:
  - Default: @config.json
```

### Example 3: Argument + Bash + File Reference

```yaml
---
argument-hint: <feature-name> [-y]
allowed-tools: Bash, Read, Write
---

# Combined Pattern for: $1

## Validation

**Feature Check**:
- Exists: !`[ -d ".kiro/specs/$1" ] && echo "✅ Found" || echo "❌ Not found"`
- Has requirements: !`[ -f ".kiro/specs/$1/requirements.md" ] && echo "✅ Yes" || echo "❌ No"`

## Auto-Approve Check

If $2 == "-y":
  - Skip validation, proceed
Else:
  - Require manual approval

## Context Loading

**Feature Context**:
- Requirements: @.kiro/specs/$1/requirements.md
- Design: @.kiro/specs/$1/design.md
- Metadata: @.kiro/specs/$1/spec.json

**Project Context**:
- Tech stack: @.kiro/steering/tech.md
- Structure: @.kiro/steering/structure.md
```

**This combines**:
- Positional arguments ($1, $2)
- Flag detection ($2 == "-y")
- Bash validation checks (!`[ -f ... ]`)
- File references (@path/to/file)
- Dynamic paths (@.kiro/specs/$1/...)

---

## Troubleshooting Argument Patterns

### Problem: $ARGUMENTS Not Capturing Full Input

**Symptom**: Only first word captured

**Cause**: Using $1 instead of $ARGUMENTS

```yaml
# ❌ Wrong
argument-hint: <description>
Description: $1  # Only gets "Create"

# ✅ Correct
argument-hint: <description>
Description: $ARGUMENTS  # Gets "Create user authentication system"
```

### Problem: Flag Not Detected

**Symptom**: Flag check always false

**Cause**: Using $ARGUMENTS when should use positional

```yaml
# ❌ Wrong
Feature: $ARGUMENTS
Auto-approve: $ARGUMENTS == "-y"  # Will never match

# ✅ Correct
Feature: $1
Auto-approve: $2 == "-y"  # Correctly checks second argument
```

### Problem: Bash Command Not Executing

**Symptom**: Literal `!`command`` shown in prompt

**Causes**:
1. Missing `allowed-tools: Bash`
2. Incorrect backtick formatting
3. Invalid bash syntax

```yaml
# ❌ Wrong - no Bash tool
---
description: Check status
---
Status: !`git status`  # Won't execute

# ✅ Correct
---
description: Check status
allowed-tools: Bash, Read
---
Status: !`git status`  # Will execute
```

### Problem: File Reference Not Loading

**Symptom**: File contents not shown

**Causes**:
1. File doesn't exist
2. Path incorrect (must be relative from project root)
3. Missing `@` prefix

```yaml
# ❌ Wrong - absolute path
@/Users/username/project/README.md

# ❌ Wrong - no @ prefix
README.md

# ✅ Correct - relative path with @
@README.md
@.kiro/steering/tech.md
```

---

## Best Practices Summary

### Argument Pattern Selection
- **$ARGUMENTS**: Free-form text, descriptions, natural language input
- **$1, $2, $3...**: Multiple parameters, flags, optional arguments

### Bash Integration
- ✅ Use for context gathering and validation
- ✅ Always handle errors (2>/dev/null || echo "fallback")
- ✅ Keep commands simple and readable
- ❌ Avoid destructive operations
- ❌ Don't use for core command logic (use in context only)

### File References
- ✅ Load configuration and documentation
- ✅ Provide architectural context
- ✅ Use relative paths from project root
- ❌ Limit to essential files (5-10 max)
- ❌ Avoid large files (performance impact)

### Combining Patterns
- ✅ Use arguments for user input
- ✅ Use bash for dynamic checks
- ✅ Use file refs for context
- ✅ Keep logic clear and debuggable

---

Use these patterns to create powerful, flexible custom commands that integrate seamlessly with your project workflow!
