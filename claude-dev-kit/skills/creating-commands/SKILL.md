---
name: creating-commands
description: "Create effective Claude Code custom commands for workflow automation. Use when creating new custom commands, understanding YAML frontmatter structure (description, allowed-tools, argument-hint, model, disable-model-invocation), designing argument patterns ($ARGUMENTS vs $1/$2/$3), integrating Bash execution (! prefix) and file references (@ prefix), or troubleshooting command issues."
---

# Custom Commands Creator

This skill provides comprehensive guidance for creating effective custom slash commands that automate workflows in Claude Code projects.

## When to Use This Skill

- Creating new custom commands from scratch
- Understanding YAML frontmatter structure and all available fields
- Designing argument patterns ($ARGUMENTS vs positional arguments)
- Integrating Bash command execution (`!` prefix)
- Using file references (`@` prefix) in commands
- Organizing commands with subdirectory structures
- Troubleshooting command invocation or argument issues
- Designing team-shareable commands for project workflows

## What Are Custom Commands?

Custom commands are user-defined slash commands (starting with `/`) that extend Claude Code's built-in functionality. They are defined as Markdown files with optional YAML frontmatter and enable workflow automation through:

- Direct invocation via `/command-name` syntax
- Dynamic argument handling
- Pre-execution Bash integration
- File content inclusion
- Tool access control

### Difference from Skills

| Feature | Skills | Custom Commands |
|---------|--------|-----------------|
| File format | SKILL.md (YAML frontmatter) | command-name.md (YAML frontmatter) |
| Location | `.claude/skills/` | `.claude/commands/` |
| Primary purpose | Knowledge & guidelines | Workflow automation & execution |
| Tool control | `allowed-tools` | `allowed-tools` |
| Invocation | Context matching | Explicit `/command-name` |

## File Placement and Priority

### Project-Level (Recommended)
```
your-project/.claude/commands/
├── fix-errors.md
├── deploy.md
└── kiro/
    ├── spec-init.md
    ├── spec-tasks.md
    └── steering.md
```

**Benefits**:
- Shared with entire team via git
- Project-specific workflow automation
- CI/CD pipeline compatible
- Consistent team workflows

### User-Level
```
~/.claude/commands/
├── personal-notes.md
└── template-generator.md
```

**Benefits**:
- Available across all projects
- Personal workflow optimization

**Priority**: Project-level > User-level (project commands override user commands with the same name)

## Complete YAML Frontmatter Reference

### Required Fields

#### description (Quasi-Required)
Command description shown in autocomplete and command listings.

**Rules**:
- Maximum 1024 characters
- Should clearly explain what the command does
- Shown when user types `/` to see available commands
- If omitted, first line of command body is used

**Example**:
```yaml
description: Fix errors found by npm run check:all (lint, format, typecheck, tests)
```

### Optional Fields

#### allowed-tools (Optional)
Restricts which tools the command can invoke.

**Specification**:
- カンマ区切りの1行形式で記述
- **重要**: 指定したツールはユーザー確認なしで自動的に許可される
- Bash コマンドはワイルドカードパターンで細かく制御可能
- If omitted, inherits all tools from conversation context

**Example**:
```yaml
# Read-only command
allowed-tools: Read, Grep, Glob

# Full project modification
allowed-tools: Read, Write, Edit, Bash, Glob, Grep

# Bash コマンドの細かい制御（ワイルドカード対応）
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Read
```

**Bash コマンドの自動実行について**:
- `allowed-tools` で Bash を指定すると、コマンド実行時にユーザー確認をスキップして自動実行される
- `Bash(git:*)` のようにワイルドカードを使用すると、`git` で始まるすべてのコマンドを許可
- `Bash(npm install:*)` のように特定のコマンドのみを許可することも可能
- これにより、スラッシュコマンド起動時に即座に Bash コマンドを実行できる

**Best Practices**:
- Grant minimum necessary tools for security
- Read-only tasks: `Read, Grep, Glob`
- File modification: Add `Write, Edit`
- System commands: Carefully add `Bash` with specific patterns (e.g., `Bash(git:*)`)

#### argument-hint (Optional)
Shows expected argument format during autocomplete.

**Format**: Plain text hint shown next to command name

**Example**:
```yaml
argument-hint: <feature-name>
argument-hint: <feature-name> [-y]
argument-hint: <file-path> [--force]
```

**Display**: User sees `/command-name <feature-name>` in autocomplete

#### model (Optional) - 基本的に指定しないことを推奨
Specifies which Claude model to use for this command.

**推奨**: モデルは基本的に指定せず、会話のモデル設定を継承させることを推奨します。これにより、ユーザーが選択したモデルで一貫した体験が得られます。

**Available Models**:
- (未指定): 会話のモデル設定を継承 ← **推奨**
- `sonnet`: Balanced performance
- `opus`: Highest quality, complex tasks
- `haiku`: Fastest, simple tasks

**Example**:
```yaml
# 推奨: model フィールドを省略（会話のモデルを継承）
---
description: Fix errors from quality checks
allowed-tools: Bash, Read, Write
---

# 特別な理由がある場合のみ指定
model: haiku     # 非常にシンプルなタスク限定
```

#### disable-model-invocation (Optional)
Prevents AI from automatically invoking this command.

**Use Cases**:
- Commands that should only be manually triggered
- Debugging or administrative commands
- Commands with destructive actions

**Example**:
```yaml
disable-model-invocation: true
```

## Argument Patterns

### Pattern 1: All Arguments ($ARGUMENTS)

Captures everything passed to the command as a single string.

**When to Use**:
- Free-form text input (descriptions, queries)
- Variable-length input
- Single conceptual input that may contain spaces

**Example**:
```yaml
---
description: Initialize a new specification with detailed project description
argument-hint: <project-description>
---

# Spec Initialization

Initialize a new specification based on the provided project description:

**Project Description**: $ARGUMENTS

## Task: Initialize Specification Structure
...
```

**Invocation**: `/kiro:spec-init Create a user authentication system with email/password login`
- `$ARGUMENTS` = `"Create a user authentication system with email/password login"`

### Pattern 2: Positional Arguments ($1, $2, $3...)

Shell-script style positional argument access.

**When to Use**:
- Multiple distinct parameters
- Optional parameters with defaults
- Flag detection (-y, --force, etc.)
- Need to process arguments individually

**Example**:
```yaml
---
description: Generate implementation tasks for a specification
argument-hint: <feature-name> [-y]
---

# Implementation Tasks

Generate detailed implementation tasks for feature: **$1**

## Prerequisites & Context Loading
- If invoked with `-y` flag ($2 == "-y"): Auto-approve requirements and design
- Otherwise: Stop if requirements/design missing
...
```

**Invocation**: `/kiro:spec-tasks auth-system -y`
- `$1` = `"auth-system"`
- `$2` = `"-y"`
- `$3` = `""` (empty)

### Pattern 3: No Arguments

Simple execution commands that don't require input.

**When to Use**:
- Fixed workflow execution
- Project-wide checks
- Automated fix commands

**Example**:
```yaml
---
description: Fix errors found by npm run check:all (lint, format, typecheck, tests)
---

## Workflow

1. **Run full quality check to identify all issues**
   ```bash
   npm run check:all
   ```
...
```

**Invocation**: `/fix-errors` (no arguments)

## Bash Integration

### Pre-Execution Bash (`!` prefix)

Execute bash commands **before** the slash command runs, injecting results into the prompt.

**Syntax**: Lines starting with exclamation mark followed by command in backticks

**Use Cases**:
- Gather context (git status, file existence checks)
- Dynamic condition evaluation
- Project state inspection

**Requirements**:
- Must specify `allowed-tools` including relevant bash commands
- Commands run in project directory
- Output captured and provided to Claude

**Example**:
```yaml
---
description: Create or update Kiro steering documents
allowed-tools: Bash, Read, Write, Edit
---

## Existing Files Check

### Current steering documents status
- Product overview: !`[ -f ".kiro/steering/product.md" ] && echo "✅ EXISTS" || echo "📝 Not found"`
- Technology stack: !`[ -f ".kiro/steering/tech.md" ] && echo "✅ EXISTS" || echo "📝 Not found"`

## Project Analysis

### Current Project State
- Recent changes: !`git log --oneline --max-count=20`
- Working tree: !`git status --porcelain`
```

**Advanced Pattern**: Multi-line bash with variable capture
```yaml
- Last update: !`LAST_COMMIT=$(git log -1 --format=%H -- .kiro/steering/); if [ -n "$LAST_COMMIT" ]; then git log --oneline ${LAST_COMMIT}..HEAD; else echo "No previous update"; fi`
```

### File References (`@` prefix)

Include file contents directly in the command prompt.

**Syntax**: `@` followed by file path (absolute or relative)

**Use Cases**:
- Load configuration files
- Reference documentation
- Include existing code for context

**Example**:
```yaml
---
description: Create or update steering documents
---

## Context Loading

### Existing Documentation
- Main README: @README.md
- Package configuration: @package.json
- TypeScript config: @tsconfig.json
- Core steering: @.kiro/steering/product.md
- Custom steering: @.kiro/steering/tech.md
```

**Benefits**:
- No need for explicit Read tool calls
- Cleaner command structure
- Direct context inclusion

## Command Creation Step-by-Step

### Step 1: Define Purpose and Scope

**Questions**:
1. What does this command do? (single responsibility)
2. What arguments does it need?
3. Which tools are required? (minimum privilege)
4. Who uses it? (personal or team)

**Example**:
- **Purpose**: Automate error fixing workflow
- **Scope**: Run checks, auto-fix what's possible, report remaining issues
- **Arguments**: None (fixed workflow)
- **Tools**: `Bash` (for running npm scripts)
- **Target**: Team (project-level)

### Step 2: Create File

**Project-level**:
```bash
# In project directory
mkdir -p .claude/commands
touch .claude/commands/your-command.md
```

**For grouped commands**:
```bash
mkdir -p .claude/commands/group-name
touch .claude/commands/group-name/your-command.md
```

**User-level**:
```bash
mkdir -p ~/.claude/commands
touch ~/.claude/commands/your-command.md
```

**Note**: Command name is derived from filename without `.md` extension. Subdirectories are for organization only and don't affect the command name.

### Step 3: Write YAML Frontmatter

**Template**:
```yaml
---
description: [What it does in 1-2 sentences]
allowed-tools: [Tool1, Tool2, Tool3]
argument-hint: [<arg-format>]
model: sonnet
---
```

**Important**: Choose appropriate argument pattern based on your needs:
- No arguments: Omit argument-hint
- Single free-form input: Use $ARGUMENTS
- Multiple parameters or flags: Use $1, $2, $3...

### Step 4: Write Command Body

**Structure**:
```markdown
---
[YAML frontmatter]
---

# Command Title

Brief command overview.

## Context Loading (if using ! or @)
- File existence: !`[ -f "file.md" ] && echo "EXISTS" || echo "NOT FOUND"`
- Documentation: @README.md

## Task: [Primary Task Description]

### Workflow
1. Step 1
2. Step 2
3. Step 3

### Success Criteria
- Criterion 1
- Criterion 2
```

**Best Practices**:
- Use clear headers for organization
- Include code blocks for examples
- Specify success criteria
- Document expected behavior

### Step 5: Test

**Testing Methods**:
1. **Basic invocation**: `/your-command` (check if command appears)
2. **Argument passing**: `/your-command arg1 arg2` (verify argument capture)
3. **Expected behavior**: Verify Claude performs described tasks
4. **Tool restrictions**: Ensure only allowed tools are used

**Debugging**:
- Check if command appears in autocomplete (`/` to list all commands)
- Verify frontmatter YAML syntax (no tabs, proper indentation)
- Test argument patterns with simple echo commands first

## Best Practices

### 1. Single Responsibility Principle

**✅ Good Example**:
```yaml
---
description: Fix errors found by npm run check:all (lint, format, typecheck, tests)
---
```
Clear, focused purpose: error fixing workflow

**❌ Bad Example**:
```yaml
---
description: Fix errors, deploy app, update docs, and run tests
---
```
Too many responsibilities - split into multiple commands

### 2. Clear Argument Design

**✅ Good Example**:
```yaml
---
argument-hint: <feature-name> [-y]
---

Feature: **$1**
Auto-approve: $2 == "-y"
```

**❌ Bad Example**:
```yaml
---
argument-hint: <args>
---

Arguments: $ARGUMENTS
```
Unclear what arguments are expected

### 3. Minimum Tool Privilege

**✅ Good Example**:
```yaml
# Validation command (read-only)
allowed-tools: Read, Grep, Glob

# Fix command (modification needed)
allowed-tools: Read, Write, Edit, Bash
```

**❌ Bad Example**:
```yaml
# Everything granted unnecessarily
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, WebFetch, WebSearch
```

### 4. Documentation and Examples

**✅ Good Example**:
```markdown
## Usage Examples

**Basic invocation**:
```
/kiro:spec-init Create user authentication feature
```

**With auto-approve**:
```
/kiro:spec-tasks auth-feature -y
```
```

### 5. Subdirectory Organization

**Good Structure**:
```
.claude/commands/
├── fix-errors.md          # General utility
├── kiro/                  # Grouped by feature
│   ├── spec-init.md
│   ├── spec-design.md
│   ├── spec-tasks.md
│   └── spec-impl.md
└── deploy/                # Grouped by category
    ├── staging.md
    └── production.md
```

**Benefits**:
- Clear command categorization
- Easier to find related commands
- Prevents command name collisions
- Better team organization

## Troubleshooting

### Problem: Command Not Appearing

**Cause 1: Invalid filename**
```yaml
# ❌ Bad - uppercase, special characters
Fix_Errors.md
fix errors.md

# ✅ Good - lowercase, hyphens
fix-errors.md
```

**Cause 2: Invalid YAML syntax**
```yaml
# ❌ Bad - tabs used
---
description:	Fix errors
---

# ✅ Good - spaces used
---
description: Fix errors
---
```

**Cause 3: Wrong directory**
- Ensure file is in `.claude/commands/` (project) or `~/.claude/commands/` (user)
- Check file has `.md` extension

### Problem: Arguments Not Passing Correctly

**Cause 1: Using $ARGUMENTS when $1 intended**
```markdown
# ❌ Bad - will capture "feature-name -y" as single string
Feature: $ARGUMENTS

# ✅ Good - separate parameters
Feature: $1
Flag: $2
```

**Cause 2: Missing space after $**
```markdown
# ❌ Bad - not recognized
Feature: $1Description: $2

# ✅ Good - proper spacing
Feature: $1
Description: $2
```

### Problem: Bash Commands Not Executing

**Cause 1: Missing allowed-tools**
```yaml
# ❌ Bad - Bash not allowed
---
description: Check git status
---

Status: !`git status`

# ✅ Good - Bash explicitly allowed
---
description: Check git status
allowed-tools: Bash, Read
---

Status: !`git status`
```

**Cause 2: Invalid bash syntax**
```yaml
# ❌ Bad - unbalanced quotes
!`echo "test`

# ✅ Good - balanced quotes
!`echo "test"`
```

### Problem: File References Not Working

**Cause: Incorrect path**
```markdown
# ❌ Bad - absolute path when file doesn't exist
@/Users/username/project/README.md

# ✅ Good - relative path from project root
@README.md
@.kiro/steering/tech.md
```

## Reference Documentation

### Deep Dive Guides

1. **command-structure-guide.md**:
   - 3 basic command patterns
   - Pattern selection flowchart
   - Complete templates

2. **frontmatter-fields-guide.md**:
   - Detailed field explanations
   - Impact on command behavior
   - Field combination strategies

3. **argument-patterns.md**:
   - $ARGUMENTS vs positional comparison
   - Flag detection techniques
   - Bash integration best practices
   - Conditional logic patterns

4. **real-world-examples.md**:
   - 4 complete examples from real projects
   - Pattern analysis and rationale
   - Lessons learned from each

## Team Collaboration

### Sharing Project-Level Commands

```bash
# 1. Create command file
.claude/commands/your-command.md

# 2. Commit to git
git add .claude/commands/your-command.md
git commit -m "feat: add /your-command for [purpose]"
git push

# 3. Team members pull
git pull
# → Automatically available to entire team
```

### Documentation

```markdown
# Add to project README.md

## Claude Code Custom Commands

This project provides the following custom commands:

- **/fix-errors**: Run quality checks and auto-fix issues
- **/kiro:spec-init <description>**: Initialize new specification
- **/kiro:spec-tasks <feature> [-y]**: Generate implementation tasks
```

### Naming Conventions

Establish consistent naming within teams:
- `[category]-[action]`: `git-commit`, `test-run`
- `[feature]:[action]`: `kiro:spec-init`, `deploy:staging`
- `[action]-[target]`: `fix-errors`, `update-deps`

### Review Process

Review custom commands like code:
- Clear description and argument hints
- Appropriate tool restrictions
- Well-documented workflow
- Tested invocation patterns

## Quick Reference

### Minimal Command
```yaml
---
description: Does X when Y.
---

Brief command overview.

1. Do A
2. Do B
3. Do C
```

### Recommended Command
```yaml
---
description: Expert in X for Y and Z. Use when working with A, B, or C scenarios.
allowed-tools: Read, Write, Edit, Bash
argument-hint: <required-arg> [optional-flag]
model: sonnet
---

# Command Title

## Context Loading
- File check: !`[ -f "file.md" ] && echo "EXISTS" || echo "NOT FOUND"`
- Documentation: @README.md

## Task: Primary Task

### Workflow
1. Step 1
2. Step 2

### Success Criteria
- Criterion 1
- Criterion 2
```

### Complete Command
```yaml
---
description: Comprehensive description with clear use cases and expected behavior.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: <feature-name> [-y] [--force]
model: sonnet
disable-model-invocation: false
---

[Detailed command body - see real-world-examples.md for steering.md example]
```

---

Use this skill to create effective custom commands that automate your project workflows!
