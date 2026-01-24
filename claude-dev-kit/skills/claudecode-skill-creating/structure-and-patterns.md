# Skills Structure and Patterns

This document covers directory structure, patterns, and best practices for Claude Code skills.

## Skills vs Slash Commands

### Comprehensive Comparison

| Aspect | Slash Commands | Skills |
|--------|---------------|--------|
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

## Token Efficiency Best Practices

### How Skill Loading Works

**Metadata-Only Loading (Always):**
- Only `name` and `description` are loaded initially
- Approximately **50-100 tokens per skill**
- Even with 50+ skills installed, metadata costs only a few thousand tokens
- This is the "progressive disclosure" foundation

**SKILL.md Loading (On-Demand):**
- Full SKILL.md content loads only when skill is activated
- Target: **< 5,000 tokens** (under 500 lines)
- Referenced files (reference.md, examples.md) load only when explicitly needed

### Skill Splitting Strategy

**"One Skill = One Capability"** is critical for token efficiency:

```
# ❌ BAD: Monolithic skill
coding-assistant/
└── SKILL.md  # 2000 lines covering testing, docs, debugging, etc.
              # Always loads everything even for simple tasks

# ✅ GOOD: Focused skills
testing-code/
└── SKILL.md  # 300 lines - testing only

writing-documentation/
└── SKILL.md  # 250 lines - docs only

debugging-errors/
└── SKILL.md  # 200 lines - debugging only

refactoring-modules/
└── SKILL.md  # 280 lines - refactoring only
```

**Benefits of splitting:**
- Only relevant context loads for each task
- Claude selects skills more accurately
- Easier to maintain and update
- Better activation precision

### Token-Efficient Directory Structure

```
your-skill-name/
├── SKILL.md              # Required: Keep < 500 lines (< 5k tokens)
├── scripts/              # Code NOT loaded into context!
│   ├── validate.py       # Only execution output costs tokens
│   └── helper.sh         # Ideal for deterministic operations
├── references/           # Loaded only when explicitly referenced
│   ├── guidelines.md     # Keep mutually exclusive content separate
│   └── examples.md
└── assets/               # Templates, images (loaded on-demand)
    └── template.xlsx
```

**Why scripts/ is token-efficient:**
- Script **code is NOT loaded** into context
- Only **execution output** consumes tokens
- Perfect for: validation, data processing, complex calculations
- Use scripts for deterministic operations Claude might struggle with

### What NOT to Include

**Never add these files to skills (wastes tokens):**

❌ **CHANGELOG.md / VERSION.md**
- Version history wastes tokens every time skill loads
- Use git history instead (`git log --oneline`)
- If you must track versions, keep in a separate repo wiki

❌ **Extensive inline documentation**
- Move to reference.md (loaded on-demand)
- Link to external docs instead of duplicating

❌ **Redundant examples**
- 2-3 examples are sufficient
- More examples = more tokens

### Practical Token Budgets

| Component | Target | Max |
|-----------|--------|-----|
| SKILL.md | < 300 lines | 500 lines |
| Metadata (name + description) | ~80 tokens | 100 tokens |
| reference.md | < 500 lines | 800 lines |
| Total skill (excluding scripts) | < 5k tokens | 10k tokens |

### Monitoring Token Usage

To estimate your skill's token cost:
```bash
# Rough estimate: ~4 characters per token
wc -c ~/.claude/skills/my-skill/SKILL.md
# Divide result by 4 for approximate tokens
```

**Rule of thumb:** If `wc -l SKILL.md` exceeds 500, refactor.

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

**Web:**
- `WebFetch` - Fetch content from URLs
- `WebSearch` - Search the web

**Agent & Skills:**
- `Task` - Launch specialized sub-agents
- `Skill` - Invoke skills

**Task Management:**
- `TaskCreate` - Create new tasks
- `TaskUpdate` - Update task status
- `TaskList` - List all tasks
- `TaskGet` - Get task details

**Utility:**
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
