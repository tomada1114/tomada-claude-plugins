# Real-World Examples

This document presents four complete custom command examples from an active project, with detailed analysis of design decisions, patterns used, and lessons learned.

## Overview of Examples

| Command | Pattern | Key Features | Complexity |
|---------|---------|--------------|------------|
| fix-errors.md | Simple Execution | No args, workflow automation | ⭐ Simple |
| spec-init.md | $ARGUMENTS | Free-form input, file generation | ⭐⭐ Moderate |
| spec-tasks.md | Positional + Flags | Multiple args, flag detection | ⭐⭐⭐ Complex |
| steering.md | Full Integration | Bash `!`, File `@`, conditional | ⭐⭐⭐⭐ Advanced |

---

## Example 1: fix-errors.md (Simple Execution)

### Complete Source

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

## Success Criteria

- `npm run check:all` exits with code 0 (all green)
- OR all remaining issues are documented with proposed fixes
```

### Analysis

**Pattern Used**: Simple Execution (Pattern 1)

**Design Decisions**:
1. **No arguments**: Fixed workflow that doesn't need customization
2. **No allowed-tools specified**: Inherits all tools (needs Bash for npm commands)
3. **Clear success criteria**: Binary pass/fail with fallback

**Strengths**:
- ✅ Dead simple to use: `/fix-errors`
- ✅ Clear step-by-step workflow
- ✅ Well-defined success criteria
- ✅ Handles both auto-fix and manual intervention
- ✅ Includes verification loops

**Why This Pattern Works**:
- Quality checks are always the same
- No configuration needed
- Workflow is linear and predictable
- Users don't need to think about parameters

**Lessons Learned**:
1. Simple commands should stay simple (resist feature creep)
2. Clear workflow documentation helps AI follow steps
3. Success criteria prevent endless loops
4. Code blocks guide AI to use specific commands

**When to Use Similar Pattern**:
- Fixed workflows (deploy, build, test)
- Project-wide operations (update deps, clean cache)
- Standard maintenance tasks

---

## Example 2: spec-init.md (Single Argument)

### Complete Source (Simplified)

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
**Check existing `.kiro/specs/` directory to ensure the generated feature name is unique. If a conflict exists, append a number suffix (e.g., feature-name-2).**

### 2. Create Spec Directory
Create `.kiro/specs/[generated-feature-name]/` directory with:
- `spec.json` - Metadata and approval tracking
- `requirements.md` - Lightweight template with project description

**Note**: design.md and tasks.md will be created by their respective commands during the development process.

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
    },
    "design": {
      "generated": false,
      "approved": false
    },
    "tasks": {
      "generated": false,
      "approved": false
    }
  },
  "ready_for_implementation": false
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

### 5. Update CLAUDE.md Reference
Add the new spec to the active specifications list with the generated feature name and a brief description.

## Next Steps After Initialization

Follow the strict spec-driven development workflow:
1. **`/kiro:spec-requirements <feature-name>`** - Create and generate requirements.md
2. **`/kiro:spec-design <feature-name>`** - Create and generate design.md (requires approved requirements)
3. **`/kiro:spec-tasks <feature-name>`** - Create and generate tasks.md (requires approved design)

**Important**: Each phase creates its respective file and requires approval before proceeding to the next phase.

## Output Format

After initialization, provide:
1. Generated feature name and rationale
2. Brief project summary
3. Created spec.json path
4. **Clear next step**: `/kiro:spec-requirements <feature-name>`
5. Explanation that only spec.json was created, following stage-by-stage development principles
```

### Analysis

**Pattern Used**: $ARGUMENTS (Pattern 2)

**Design Decisions**:
1. **$ARGUMENTS for free-form input**: Users describe feature naturally
2. **allowed-tools explicit**: Only what's needed (Bash, Read, Write, Glob)
3. **argument-hint descriptive**: `<project-description>` signals natural language expected
4. **Reference $ARGUMENTS multiple times**: Used in template generation

**Strengths**:
- ✅ Natural input: "Create a user authentication system with OAuth2"
- ✅ Preserves exact description for documentation
- ✅ Clear tool restrictions for security
- ✅ Staged workflow prevents over-generation
- ✅ Next steps explicitly documented

**Why This Pattern Works**:
- Project descriptions are naturally multi-word
- No need for flags or options (single task)
- Description should be preserved verbatim
- Simplifies user mental model

**Lessons Learned**:
1. $ARGUMENTS perfect for natural language input
2. Reference input multiple times in templates
3. Stage-by-stage prevents overwhelming users
4. Explicit next steps guide workflow
5. Unique name generation prevents conflicts

**When to Use Similar Pattern**:
- Commit message generation
- Documentation from descriptions
- Search queries
- Any free-form text input

---

## Example 3: spec-tasks.md (Multiple Arguments + Flags)

### Complete Source (Key Sections)

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
   - **Core files (always load)**:
     - @.kiro/steering/product.md - Business context, product vision, user needs
     - @.kiro/steering/tech.md - Technology stack, frameworks, libraries
     - @.kiro/steering/structure.md - File organization, naming conventions, code patterns
   - **Custom steering files** (load all EXCEPT "Manual" mode in `AGENTS.md`):
     - Any additional `*.md` files in `.kiro/steering/` directory
     - Examples: `api.md`, `testing.md`, `security.md`, etc.
4. `.kiro/specs/$1/tasks.md` - Existing tasks (only if merge mode)

### CRITICAL Task Numbering Rules (MUST FOLLOW)

**⚠️ MANDATORY: Sequential major task numbering & hierarchy limits**
- Major tasks: 1, 2, 3, 4, 5... (MUST increment sequentially)
- Sub-tasks: 1.1, 1.2, 2.1, 2.2... (reset per major task)
- **Maximum 2 levels of hierarchy** (no 1.1.1 or deeper)

### Task Generation Rules

1. **Natural language descriptions**: Focus on capabilities and outcomes, not code structure
2. **Task integration & progression**: Each task must build on previous outputs
3. **Flexible task sizing**: As many sub-tasks as logically needed
4. **Requirements mapping**: End details with `_Requirements: X.X, Y.Y_`
5. **Code-only focus**: Include ONLY coding/testing tasks, exclude deployment/docs/user testing

### Requirements Coverage Check
- **MANDATORY**: Ensure ALL requirements from requirements.md are covered
- Cross-reference every requirement ID with task mappings
- If gaps found: Return to requirements or design phase

### Document Generation
- Generate `.kiro/specs/$1/tasks.md` using the exact numbering format above
- **Language**: Use language from `spec.json.language` field, default to English
- Update `.kiro/specs/$1/spec.json`:
  - Set `phase: "tasks-generated"`
  - Set approvals map exactly as:
    - `approvals.tasks = { "generated": true, "approved": false }`
  - Preserve existing metadata, do not remove unrelated fields
  - If invoked with `-y` flag: ensure the above approval booleans are applied
  - Set `updated_at` to current ISO8601 timestamp
```

### Analysis

**Pattern Used**: Positional Arguments + Flag Detection (Pattern 3)

**Design Decisions**:
1. **$1 for feature name**: Required, distinct parameter
2. **$2 for flag**: Optional `-y` for auto-approval
3. **allowed-tools carefully chosen**: Only file operations, no Bash (no need for execution)
4. **File references (@)**: Load steering documents without explicit Read calls
5. **Dynamic paths**: Use `$1` in file paths (`.kiro/specs/$1/...`)

**Strengths**:
- ✅ Clear required vs optional params
- ✅ Flag detection enables workflow variations
- ✅ File references simplify context loading
- ✅ Comprehensive validation rules
- ✅ Detailed output specifications
- ✅ Supports both new and merge modes

**Why This Pattern Works**:
- Feature name is distinct from flag
- Flag changes behavior (skip validation)
- Multiple context files needed
- Complex logic requires explicit tool control

**Lessons Learned**:
1. Positional args excellent for distinct parameters
2. Flag detection ($2 == "-y") is clean and intuitive
3. File references (@) reduce boilerplate
4. Dynamic paths with $1 are powerful
5. Detailed rules prevent ambiguous output
6. Comprehensive validation catches errors early

**When to Use Similar Pattern**:
- Commands with required + optional params
- Flag-based behavior modification
- Complex validation workflows
- Multi-file context loading

**Common Invocations**:
```bash
/kiro:spec-tasks auth-system          # Normal flow
/kiro:spec-tasks auth-system -y       # Skip approval checks
```

---

## Example 4: steering.md (Full Integration)

### Complete Source (Key Sections)

```yaml
---
description: Create or update Kiro steering documents intelligently based on project state
allowed-tools: Bash, Read, Write, Edit, MultiEdit, Glob, Grep, LS
---

# Kiro Steering Management

Intelligently create or update steering documents in `.kiro/steering/` to maintain accurate project knowledge for spec-driven development. This command detects existing documents and handles them appropriately.

## Existing Files Check

### Current steering documents status
- Product overview: !`[ -f ".kiro/steering/product.md" ] && echo "✅ EXISTS - Will be updated preserving custom content" || echo "📝 Not found - Will be created"`
- Technology stack: !`[ -f ".kiro/steering/tech.md" ] && echo "✅ EXISTS - Will be updated preserving custom content" || echo "📝 Not found - Will be created"`
- Project structure: !`[ -f ".kiro/steering/structure.md" ] && echo "✅ EXISTS - Will be updated preserving custom content" || echo "📝 Not found - Will be created"`
- Custom steering files: !`ls .kiro/steering/*.md 2>/dev/null | grep -v -E "(product|tech|structure)\.md$" | wc -l | awk '{if($1>0) print "🔧 " $1 " custom file(s) found - Will be preserved"; else print "📋 No custom files"}'`

## Project Analysis

### Current Project State
- Project files: !`find . -path ./node_modules -prune -o -path ./.git -prune -o -path ./dist -prune -o -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" -o -name "*.java" -o -name "*.go" -o -name "*.rs" \) -print 2>/dev/null || echo "No source files found"`
- Configuration files: !`find . -maxdepth 3 \( -name "package.json" -o -name "requirements.txt" -o -name "pom.xml" -o -name "Cargo.toml" -o -name "go.mod" -o -name "pyproject.toml" -o -name "tsconfig.json" \) 2>/dev/null || echo "No config files found"`
- Documentation: !`find . -maxdepth 3 -path ./node_modules -prune -o -path ./.git -prune -o -path ./.kiro -prune -o \( -name "README*" -o -name "CHANGELOG*" -o -name "LICENSE*" -o -name "*.md" \) -print 2>/dev/null || echo "No documentation files found"`

### Recent Changes (if updating)
- Last steering update: !`git log -1 --oneline -- .kiro/steering/ 2>/dev/null || echo "No previous steering commits"`
- Commits since last steering update: !`LAST_COMMIT=$(git log -1 --format=%H -- .kiro/steering/ 2>/dev/null); if [ -n "$LAST_COMMIT" ]; then git log --oneline ${LAST_COMMIT}..HEAD --max-count=20 2>/dev/null || echo "Not a git repository"; else echo "No previous steering update found"; fi`
- Working tree status: !`git status --porcelain 2>/dev/null || echo "Not a git repository"`

### Existing Documentation
- Main README: @README.md
- Package configuration: @package.json
- Python requirements: @requirements.txt
- TypeScript config: @tsconfig.json
- Project documentation: @docs/
- Coding Agent Project memory: @AGENTS.md

## Smart Update Strategy

Based on the existing files check above, this command will:

### For NEW files (showing "📝 Not found"):
Generate comprehensive initial content covering all aspects of the project.

### For EXISTING files (showing "✅ EXISTS"):
1. **Preserve user customizations** - Any manual edits or custom sections
2. **Update factual information** - Dependencies, file structures, commands
3. **Add new sections** - Only if significant new capabilities exist
4. **Mark deprecated content** - Rather than deleting
5. **Maintain formatting** - Keep consistent with existing style

## Task: Create or Update Steering Documents

### 1. Product Overview (`product.md`)

#### For NEW file:
Generate comprehensive product overview including:
- **Product Overview**: Brief description of what the product is
- **Core Features**: Bulleted list of main capabilities
- **Target Use Case**: Specific scenarios the product addresses
- **Key Value Proposition**: Unique benefits and differentiators

#### For EXISTING file:
Update only if there are:
- **New features** added to the product
- **Removed features** or deprecated functionality
- **Changed use cases** or target audience
- **Updated value propositions** or benefits

### 2. Technology Stack (`tech.md`)

#### For NEW file:
Document the complete technology landscape:
- **Architecture**: High-level system design
- **Frontend**: Frameworks, libraries, build tools (if applicable)
- **Backend**: Language, framework, server technology (if applicable)
- **Development Environment**: Required tools and setup
- **Common Commands**: Frequently used development commands
- **Environment Variables**: Key configuration variables
- **Port Configuration**: Standard ports used by services

#### For EXISTING file:
Check for changes in:
- **New dependencies** added via package managers
- **Removed libraries** or frameworks
- **Version upgrades** of major dependencies
- **New development tools** or build processes
- **Changed environment variables** or configuration
- **Modified port assignments** or service architecture

### 3. Project Structure (`structure.md`)

#### For NEW file:
Outline the codebase organization:
- **Root Directory Organization**: Top-level structure with descriptions
- **Subdirectory Structures**: Detailed breakdown of key directories
- **Code Organization Patterns**: How code is structured
- **File Naming Conventions**: Standards for naming files and directories
- **Import Organization**: How imports/dependencies are organized
- **Key Architectural Principles**: Core design decisions and patterns

#### For EXISTING file:
Look for changes in:
- **New directories** or major reorganization
- **Changed file organization** patterns
- **New or modified naming conventions**
- **Updated architectural patterns** or principles
- **Refactored code structure** or module boundaries

## Important Principles

### Security Guidelines
- **Never include sensitive data**: No API keys, passwords, database credentials
- **Review before commit**: Always review steering content
- **Team sharing consideration**: Files are shared with all project collaborators

### Content Quality Guidelines
- **Single domain focus**: Each file covers one specific area
- **Clear, descriptive content**: Provide concrete examples and rationale
- **Regular maintenance**: Review after major project changes
- **Actionable guidance**: Write specific, implementable guidelines

### Preservation Strategy
- **User sections**: Non-standard sections preserved
- **Custom examples**: User-added examples maintained
- **Comments**: Inline comments or notes kept
- **Formatting preferences**: Respect existing markdown style
```

### Analysis

**Pattern Used**: Full Integration (Bash `!` + File `@` + Complex Logic)

**Design Decisions**:
1. **No arguments**: Operates on entire project state
2. **allowed-tools extensive**: Needs all file and execution tools
3. **Bash pre-execution** (`!`): Gathers dynamic project state
4. **File references** (`@`): Loads existing documentation
5. **Conditional logic**: Different behavior for new vs existing files
6. **Complex validation**: Multi-step existence checks

**Strengths**:
- ✅ Fully automated context gathering
- ✅ Intelligent update vs create logic
- ✅ Comprehensive project analysis
- ✅ Preserves user customizations
- ✅ Rich error handling (2>/dev/null || echo)
- ✅ Clear update philosophy documented
- ✅ Security guidelines prominent

**Why This Pattern Works**:
- Project state is dynamic (git, files, configs)
- Needs to detect what already exists
- Different behavior for new vs existing
- Requires comprehensive context
- Bash is perfect for dynamic checks

**Lessons Learned**:
1. Bash `!` prefix ideal for dynamic checks
2. Complex bash (variables, conditionals) fully supported
3. File references `@` simplify documentation loading
4. Conditional logic in command body guides AI behavior
5. Clear "For NEW" vs "For EXISTING" sections prevent confusion
6. Security guidelines prevent sensitive data leaks
7. Preservation strategy builds user trust

**Advanced Patterns Demonstrated**:
- **Multi-line bash with variables**:
  ```bash
  !`LAST=$(git log -1 --format=%H -- .kiro/steering/); if [ -n "$LAST" ]; then git log --oneline ${LAST}..HEAD; fi`
  ```
- **Error handling**: `2>/dev/null || echo "fallback"`
- **Complex find commands**: Exclude paths with `-prune`
- **Pipe chains**: `ls | grep | wc | awk`
- **Conditional output**: `[ condition ] && echo "yes" || echo "no"`

**When to Use Similar Pattern**:
- Dynamic project analysis
- Update vs create decisions
- Context-rich operations
- State-dependent workflows
- Complex validation requirements

**Common Invocation**:
```bash
/kiro:steering    # No arguments, fully automated
```

---

## Comparative Analysis

### Complexity Progression

| Feature | fix-errors | spec-init | spec-tasks | steering |
|---------|------------|-----------|------------|----------|
| Arguments | None | $ARGUMENTS | $1, $2 flags | None |
| Bash integration | Implicit | None | None | Extensive |
| File references | None | None | Yes (@) | Yes (@) |
| Tool restrictions | None (inherit) | Explicit | Explicit | Explicit |
| Conditional logic | Simple | Moderate | Complex | Very complex |
| Context loading | None | Low | High | Very high |

### Pattern Selection Guide

**Choose Simple Execution** (fix-errors) when:
- Workflow is always the same
- No customization needed
- Clear linear steps
- Project-wide operation

**Choose $ARGUMENTS** (spec-init) when:
- Free-form text input
- Natural language description
- Single conceptual input
- Spaces should be preserved

**Choose Positional + Flags** (spec-tasks) when:
- Multiple distinct parameters
- Optional behavior flags
- Required + optional params
- Complex validation needed

**Choose Full Integration** (steering) when:
- Dynamic project analysis required
- State-dependent behavior
- Extensive context needed
- Create vs update logic
- Complex validation checks

---

## Key Takeaways

### Design Principles

1. **Start Simple**: Begin with simplest pattern that works
2. **Add Complexity When Needed**: Only add features when required
3. **Be Explicit**: Clear frontmatter, clear workflow, clear success criteria
4. **Guide the AI**: Detailed instructions prevent ambiguity
5. **Validate Early**: Check prerequisites before main logic
6. **Document Next Steps**: Help users understand workflow

### Technical Patterns

1. **$ARGUMENTS**: Perfect for natural language, preserve input exactly
2. **Positional Args**: Best for distinct parameters and flags
3. **Bash `!` Prefix**: Excellent for dynamic checks and context gathering
4. **File `@` References**: Simplify documentation and context loading
5. **Dynamic Paths**: Use arguments in paths (`.kiro/specs/$1/file.md`)

### Security and Maintenance

1. **Least Privilege**: Only grant necessary tools
2. **Error Handling**: Always handle bash failures gracefully
3. **Sensitive Data**: Never include secrets or credentials
4. **User Trust**: Preserve customizations, document changes
5. **Clear Documentation**: Users should understand what command does

---

Use these real-world examples as templates and inspiration for your own custom commands!
