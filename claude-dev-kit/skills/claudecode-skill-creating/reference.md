# Claude Code Skills - Detailed Reference

This file provides comprehensive reference information for Claude Code skills. It's loaded on-demand when detailed specifications are needed.

## Table of Contents

- [YAML Frontmatter Specification](#yaml-frontmatter-specification)
- [Skills vs Slash Commands](#skills-vs-slash-commands)
- [Directory Structure Details](#directory-structure-details)
- [Progressive Disclosure Pattern](#progressive-disclosure-pattern)
- [Tool Restrictions](#tool-restrictions)
- [Common Patterns Library](#common-patterns-library)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Version Guidelines](#version-guidelines)

## YAML Frontmatter Specification

### Complete Field Reference

```yaml
---
name: skill-identifier              # Required
description: Full description...    # Required
allowed-tools: Read, Grep, Glob    # Optional
---
```

### Field: `name`

**Type:** String
**Required:** Yes
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

**Valid Examples:**
```yaml
name: api-docs-writer
name: test-strategy
name: code-review
name: db-migration-helper
name: security-analyzer
name: comprehensive-testing
name: openapi-generator
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
```

### Field: `description`

**Type:** String
**Required:** Yes
**Max Length:** 1024 characters

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

### Field: `allowed-tools`

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

## Skills vs Slash Commands

### Comprehensive Comparison

| Aspect | Slash Commands | Agent Skills |
|--------|---------------|--------------|
| **Activation** | Manual - user types `/command` | Automatic - model decides based on context |
| **Discovery** | User must know command exists | Claude discovers from description |
| **Structure** | Single markdown file | Directory with SKILL.md + resources |
| **Location** | `.claude/commands/` | `.claude/skills/` or `~/.claude/skills/` |
| **File Organization** | Monolithic (all in one file) | Modular (templates, scripts, docs, examples) |
| **Complexity** | Simple prompts and instructions | Complex multi-step capabilities |
| **Supporting Files** | Not supported | Templates, scripts, examples, reference docs |
| **Tool Restrictions** | Not supported | `allowed-tools` available |
| **Distribution** | Via git | Via git or npm plugins |
| **Context Cost** | Low (small file) | Variable (progressive disclosure) |
| **Use Case** | Frequently-used manual operations | Capabilities Claude should discover automatically |

### Decision Framework

```
Should this be a Slash Command or a Skill?

1. Does the user need explicit control over when it runs?
   YES → Slash Command
   NO → Continue to question 2

2. Is it a simple, single-purpose prompt?
   YES → Slash Command
   NO → Continue to question 3

3. Does it require supporting files (templates, scripts, examples)?
   NO → Could be either, prefer Slash Command for simplicity
   YES → Skill

4. Should Claude discover and use it automatically based on context?
   YES → Skill
   NO → Slash Command

5. Does it need tool restrictions for safety?
   YES → Skill (use allowed-tools)
   NO → Could be either
```

### Examples

**Slash Command Examples:**

```markdown
<!-- .claude/commands/review.md -->
# Code Review

Please review the current changes with focus on:
- Code quality and maintainability
- Potential bugs or edge cases
- Performance implications
- Security concerns

Provide specific, actionable feedback.
```

**When to use:** User wants to trigger a review manually at a specific time.

---

**Skill Examples:**

```yaml
---
name: comprehensive-testing
description: Implement tests with test design tables, equivalence partitioning, boundary value analysis, and 100% branch coverage. Use when writing tests, adding test cases, improving test coverage, or working with Jest, Pytest, TypeScript testing.
---
```

**When to use:** Claude should automatically suggest comprehensive testing when user mentions testing, test coverage, or test cases.

### Migration Guide

**Converting Slash Command → Skill:**

1. Create skill directory:
```bash
mkdir -p .claude/skills/skill-name
```

2. Convert command to SKILL.md:
```yaml
---
name: skill-name
description: [What the command does]. Use when [when user would type /command].
---

# Skill Name

[Content from slash command file]
```

3. Add supporting files if needed
4. Test activation with relevant prompts
5. Remove slash command if skill works well

**Converting Skill → Slash Command:**

1. Extract core prompt from SKILL.md
2. Create `.claude/commands/command-name.md`
3. Include essential instructions only
4. Remove YAML frontmatter
5. Test with `/command-name`

## Directory Structure Details

### Three Storage Locations

#### 1. Personal Skills (`~/.claude/skills/`)

**Location:**
```
~/.claude/skills/
├── my-personal-skill/
│   └── SKILL.md
├── another-skill/
│   └── SKILL.md
```

**Characteristics:**
- Available across ALL projects for the user
- Stored in user's home directory
- Not shared with team members
- Persists across projects

**Use Cases:**
- Personal coding preferences
- Custom workflows specific to you
- Experimental skills
- Skills with personal API keys

**Example:**
```yaml
---
name: my-commit-style
description: Generate git commits in my preferred style with detailed descriptions and emoji prefixes.
---
# Use when YOU want consistent commit style across all YOUR projects
```

#### 2. Project Skills (`.claude/skills/`)

**Location:**
```
project-root/
├── .claude/
│   └── skills/
│       ├── team-skill/
│       │   └── SKILL.md
│       └── project-specific/
│           └── SKILL.md
```

**Characteristics:**
- Specific to ONE project
- Committed to git
- Shared with entire team
- Automatically available after `git pull`

**Use Cases:**
- Team coding standards
- Project-specific workflows
- Company policies
- Shared conventions

**Example:**
```yaml
---
name: company-api-docs
description: Generate API documentation following our company's API documentation standards with specific sections, examples, and OpenAPI specs.
---
# Team members get this automatically when they clone/pull the repo
```

#### 3. Plugin Skills (via plugins)

**Location:**
```
node_modules/
└── @company/claude-plugin/
    └── .claude-plugin/
        └── skills/
            └── plugin-skill/
                └── SKILL.md
```

**Characteristics:**
- Distributed as npm packages
- Installed via package.json
- Can bundle multiple skills
- Versioned and published

**Use Cases:**
- Reusable skill packages
- Organization-wide standards
- Public skill libraries
- Commercial skill packages

**Distribution:**
```bash
npm install @company/claude-skills-package
```

### Recommended File Organization

#### Simple Skill (< 200 lines)
```
simple-skill/
└── SKILL.md
```

#### Medium Skill (200-500 lines)
```
medium-skill/
├── SKILL.md              # Core instructions
└── examples.md           # Extended examples
```

#### Complex Skill (> 500 lines)
```
complex-skill/
├── SKILL.md              # Core (< 500 lines)
├── reference.md          # Detailed reference
├── examples.md           # Extended examples
├── templates/            # Reusable templates
│   ├── template1.txt
│   └── template2.txt
├── scripts/              # Utility scripts
│   ├── validate.py
│   └── setup.sh
└── docs/                 # Additional documentation
    └── advanced.md
```

#### Skill with Everything
```
full-featured-skill/
├── SKILL.md              # Main entry point (< 500 lines)
├── reference.md          # Complete API/spec reference
├── examples.md           # Extended code examples
├── CHANGELOG.md          # Version history
├── templates/            # Reusable templates
│   ├── basic-template.txt
│   ├── advanced-template.txt
│   └── config-template.yaml
├── examples/             # Complete example projects
│   ├── simple-example/
│   │   ├── input.txt
│   │   └── output.txt
│   └── advanced-example/
│       ├── input.json
│       └── output.json
├── scripts/              # Utility scripts
│   ├── validate.py       # Validation script
│   ├── setup.sh          # Setup script
│   └── transform.py      # Data transformation
└── docs/                 # Additional documentation
    ├── architecture.md   # Architecture overview
    ├── api.md           # API details
    └── troubleshooting.md
```

## Progressive Disclosure Pattern

### Concept

Progressive disclosure allows you to create comprehensive skills without bloating SKILL.md. Claude only loads additional files when needed.

### How It Works

1. **SKILL.md** is always loaded (small context cost)
2. **Referenced files** are loaded on-demand (zero cost until needed)
3. **Claude decides** when to load based on need

### Implementation

#### In SKILL.md (loaded always):

```markdown
---
name: comprehensive-skill
description: [Your description]
---

# Comprehensive Skill

Brief overview and essential information.

## Quick Start

[Essential instructions that fit in < 500 lines]

## Detailed Reference

For complete API specification, see [reference.md](reference.md).

For extended examples, see [examples.md](examples.md).

## Templates

Use these templates as starting points:
- [Basic template](templates/basic.txt)
- [Advanced template](templates/advanced.txt)
```

#### In reference.md (loaded on-demand):

```markdown
# Complete API Reference

[Extensive details that would bloat SKILL.md]

## All Methods

### Method 1
[Complete specification]

### Method 2
[Complete specification]

[... continues for hundreds of lines ...]
```

### Benefits

1. **Smaller Context Cost**: SKILL.md stays small
2. **Comprehensive Documentation**: Full details available when needed
3. **Better Organization**: Logical separation of concerns
4. **Easier Maintenance**: Edit specific sections independently

### When to Use

**Use Progressive Disclosure When:**
- SKILL.md exceeds 500 lines
- You have extensive API reference
- Many detailed examples exist
- Supporting documentation is needed

**Keep Everything in SKILL.md When:**
- Skill is < 300 lines total
- All information is essential
- No extensive reference material

## Tool Restrictions

### Complete Tool Reference

**File Operations:**
- `Read` - Read file contents
- `Write` - Create new files
- `Edit` - Modify existing files
- `Glob` - Find files matching patterns
- `NotebookEdit` - Edit Jupyter notebooks

**Search:**
- `Grep` - Search file contents with regex

**Execution:**
- `Bash` - Execute bash commands
- `BashOutput` - Get output from running bash
- `KillShell` - Kill background bash process

**Web:**
- `WebFetch` - Fetch content from URLs
- `WebSearch` - Search the web

**Agent:**
- `Task` - Launch specialized sub-agents

**Utility:**
- `TodoWrite` - Manage todo lists
- `AskUserQuestion` - Ask user questions

### Common Restriction Patterns

#### Pattern 1: Read-Only Analysis
```yaml
allowed-tools: Read, Grep, Glob
```
**Use for:** Code analysis, security audits, complexity analysis

#### Pattern 2: Documentation Only
```yaml
allowed-tools: Read, Grep, Glob, Write
```
**Use for:** Generating new documentation without editing existing files

#### Pattern 3: Safe Exploration
```yaml
allowed-tools: Read, Grep, Glob, WebSearch
```
**Use for:** Learning unfamiliar codebases with online research

#### Pattern 4: Validation Only
```yaml
allowed-tools: Read, Bash
```
**Use for:** Running validation scripts without file modifications

### Benefits of Tool Restrictions

1. **Security**: Prevent unauthorized modifications
2. **Safety**: No accidental file changes
3. **Compliance**: Enforce organizational policies
4. **Focus**: Remove distracting capabilities
5. **Confidence**: Users trust read-only operations

## Common Patterns Library

### Pattern 1: Code Generation Skill

```yaml
---
name: component-generator
description: Generate React/Vue/Angular components with TypeScript, tests, and stories. Use when creating components, scaffolding UI, or working with React, Vue, Angular, TypeScript, Storybook.
---

## Workflow
1. Ask for framework (React/Vue/Angular)
2. Request component name and props
3. Generate:
   - Component file with TypeScript
   - Test file
   - Storybook story
4. Follow project conventions
```

### Pattern 2: Analysis and Reporting

```yaml
---
name: code-quality-analyzer
description: Analyze code quality, complexity, and maintainability with detailed reports. Use when reviewing code, measuring complexity, or improving code quality.
allowed-tools: Read, Grep, Glob
---

## Workflow
1. Scan provided files
2. Calculate metrics
3. Identify issues
4. Generate report with recommendations
```

### Pattern 3: Transformation

```yaml
---
name: data-transformer
description: Transform data between formats (CSV/JSON/YAML/XML). Use when converting data formats, processing files, or working with CSV, JSON, YAML, XML.
---

## Workflow
1. Read input file
2. Parse source format
3. Transform to target format
4. Validate output
5. Write result
```

### Pattern 4: Documentation Generation

```yaml
---
name: api-docs-generator
description: Generate API documentation from code with OpenAPI specs, examples, and descriptions. Use when documenting APIs, creating OpenAPI specs, or working with REST, GraphQL.
---

## Workflow
1. Analyze code structure
2. Extract routes/endpoints
3. Generate OpenAPI specification
4. Add examples and descriptions
5. Create markdown documentation
```

### Pattern 5: Testing

```yaml
---
name: test-generator
description: Generate comprehensive tests with edge cases, mocks, and 100% coverage. Use when writing tests, adding test cases, or working with Jest, Pytest, testing.
---

## Workflow
1. Analyze code to test
2. Identify edge cases
3. Generate test cases
4. Create mocks/fixtures
5. Ensure coverage
```

## Troubleshooting Guide

### Skill Not Activating

**Diagnosis Steps:**

1. **Check Description**:
   ```bash
   # Does description include keywords you're using?
   # Add more trigger keywords
   ```

2. **Verify Name Format**:
   ```bash
   # Ensure lowercase with hyphens only
   echo "my-skill-name" | grep -E '^[a-z0-9-]+$'
   ```

3. **Validate YAML**:
   ```yaml
   # Check for proper formatting
   ---
   name: skill-name   # Space after colon required
   description: Text  # Space after colon required
   ---
   ```

4. **Check File Location**:
   ```bash
   # Verify file exists
   ls -la ~/.claude/skills/skill-name/SKILL.md
   ls -la .claude/skills/skill-name/SKILL.md
   ```

5. **Test Manually**:
   ```
   Ask Claude: "What skills are available?"
   Ask Claude: "Should you use [skill-name] for this task?"
   ```

### Skill Activates at Wrong Times

**Solutions:**

1. **Make Description More Specific**:
   ```yaml
   # ✗ Too broad
   description: Helps with testing

   # ✅ Specific
   description: Generate Jest tests for React components with hooks and async testing. Use when testing React hooks, async components, or writing Jest tests.
   ```

2. **Add Negative Triggers**:
   ```markdown
   ## When NOT to Use This Skill

   Don't use for:
   - Python testing (use pytest-skill instead)
   - E2E testing (use e2e-skill instead)
   ```

3. **Narrow Scope**:
   ```yaml
   # ✗ Too general
   description: Code analysis and refactoring

   # ✅ Narrow scope
   description: Analyze TypeScript code complexity and suggest refactoring for functions > 50 lines. Use when reviewing TypeScript code or refactoring complex functions.
   ```

## Version Guidelines

### Semantic Versioning for Skills

Skills should follow semantic versioning principles:

```
MAJOR.MINOR.PATCH

Example: 2.1.3
         │ │ │
         │ │ └─ Patch: Bug fixes, minor improvements
         │ └─── Minor: New features (backward compatible)
         └───── Major: Breaking changes
```

### Version History Format

```markdown
## Version History

### 2.0.0 (2025-01-15)
**Breaking Changes:**
- Changed output format
- Removed deprecated options

**New Features:**
- Added support for Python 3.12
- New validation mode

**Fixes:**
- Fixed edge case in parser
- Improved error messages

### 1.2.0 (2024-12-01)
**New Features:**
- Added TypeScript support
- New templates for FastAPI

**Improvements:**
- Better error handling
- Performance improvements

### 1.1.1 (2024-11-15)
**Fixes:**
- Fixed validation bug
- Updated dependencies
```

### When to Bump Versions

**MAJOR (Breaking Changes):**
- Changed skill behavior significantly
- Removed features or options
- Changed output format incompatibly
- Renamed files or directories
- Changed AI instructions significantly

**MINOR (New Features):**
- Added new capabilities
- New templates or examples
- Enhanced existing features
- New optional parameters

**PATCH (Bug Fixes):**
- Fixed bugs or errors
- Improved documentation
- Performance improvements
- Minor wording changes

---

This reference document should be used when you need detailed specifications beyond what's in the main SKILL.md.
