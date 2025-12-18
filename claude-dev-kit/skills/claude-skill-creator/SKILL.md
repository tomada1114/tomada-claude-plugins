---
name: claude-skill-creator
description: Creates effective Claude Code skills with proper YAML frontmatter, directory structure, and best practices. Use PROACTIVELY when creating skills, updating skills, troubleshooting skill activation, configuring CLAUDE.md integration, or working with skill structure, allowed-tools, Skill permissions.
---

# Claude Skill Creator Guide

This guide helps you create well-structured skills for Claude Code. Skills extend Claude's capabilities through organized folders containing instructions, templates, scripts, and resources.

## Contents

- [When to Use This Skill](#when-to-use-this-skill)
- [Critical: Skill Tool Permissions](#critical-skill-tool-permissions)
- [Quick Start](#quick-start)
- [YAML Frontmatter](#yaml-frontmatter-essentials)
- [Directory Structure](#directory-structure)
- [Context Efficiency](#context-efficiency)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [CLAUDE.md Integration](#guaranteed-activation-claudemd-integration)
- [Quick Reference Checklist](#quick-reference-checklist)
- [AI Assistant Instructions](#ai-assistant-instructions)
- [Additional Resources](#additional-resources)

## When to Use This Skill

Use this skill when:
- Creating a new skill from scratch
- Updating an existing skill
- Troubleshooting why a skill isn't being activated
- Converting documentation into a skill format
- Configuring Skill tool permissions
- Integrating skills with CLAUDE.md for guaranteed activation

## Critical: Skill Tool Permissions

**Skills are NOT automatically available!** The Skill tool is denied by default.

Add to `.claude/settings.json` (project) or `~/.claude/settings.json` (user):

```json
{
  "permissions": {
    "allow": ["Skill(*)"]
  }
}
```

Or use CLI flag: `--allowed-tools "Skill"`

**Without this setting, Claude cannot invoke any skills.**

## Quick Start

### 1. Create Directory

```bash
# Personal skills (available across all your projects)
mkdir -p ~/.claude/skills/my-skill-name

# Project skills (shared with team via git)
mkdir -p .claude/skills/my-skill-name
```

### 2. Create SKILL.md

Every skill requires a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: skill-identifier
description: What this skill does. Use when [scenario], or working with [keywords].
---

# Skill Name

[Your skill content here]
```

### 3. Use Templates

- [Basic Skill Template](templates/basic-skill-template.md) - For simple skills
- [Advanced Skill Template](templates/advanced-skill-template.md) - For complex skills

### 4. Validate

Run the validation script to check your skill:

```bash
python scripts/validate-skill.py path/to/SKILL.md
```

## YAML Frontmatter Essentials

### Required Fields

**name:**
- Lowercase letters, numbers, hyphens only
- Maximum 64 characters
- Example: `api-docs-writer`, `test-strategy`

**description:**
- Must describe BOTH what the skill does AND when to use it
- Maximum 1024 characters
- Include trigger keywords users would naturally mention

**Good Example:**
```yaml
description: Generate OpenAPI documentation from Express or FastAPI endpoints. Use when documenting APIs, creating API specs, or working with OpenAPI, Swagger, REST.
```

**Bad Example:**
```yaml
description: Helps with API documentation
```

### Optional: allowed-tools

Restrict Claude's capabilities when the skill is active:

```yaml
---
name: safe-analyzer
description: Analyze code without modifications...
allowed-tools: Read, Grep, Glob
---
```

For complete YAML specification, see [reference.md](reference.md#yaml-frontmatter-specification).

## Directory Structure

### Simple Skill
```
simple-skill/
└── SKILL.md
```

### Complete Skill
```
comprehensive-skill/
├── SKILL.md              # Main file (< 500 lines)
├── reference.md          # Detailed reference (loaded on-demand)
├── templates/            # Reusable templates
├── examples/             # Complete examples
└── scripts/              # Utility scripts
```

**Progressive Disclosure:** Keep SKILL.md under 500 lines. Use reference files for detailed information that Claude loads on-demand.

For detailed structure patterns, see [reference.md](reference.md#directory-structure-details).

## Context Efficiency

Understanding how skills use context is essential for creating effective skills.

### The Three-Level Loading Model

Skills load content in three levels with different timing and token costs:

| Level | Content | When Loaded | Token Cost |
|-------|---------|-------------|------------|
| **1. Metadata** | YAML frontmatter | Always (startup) | ~100 tokens/skill |
| **2. Instructions** | SKILL.md body | When triggered | < 5k tokens |
| **3. Resources** | Reference files, scripts | When needed | 0 until accessed |

**Key insight**: You can install many skills without context penalty. Only metadata is pre-loaded.

### Core Principle: Claude is Already Smart

**Default assumption**: Claude has extensive base knowledge.

Challenge each piece of information:
- "Does Claude really need this explanation?"
- "Can I assume Claude knows this?"
- "Does this paragraph justify its token cost?"

**Good (concise):**
```markdown
Use pdfplumber:
\`\`\`python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
\`\`\`
```

**Bad (verbose):**
```markdown
PDF (Portable Document Format) files are a common file format...
To extract text from a PDF, you'll need to use a library...
```

### Script Efficiency: Code Never Enters Context

**When Claude executes a script, the script code does NOT enter the context window. Only the output consumes tokens.**

- 200-line `validate.py` script: 0 tokens (not loaded)
- Script output "✓ Valid": ~10 tokens

This makes scripts extremely token-efficient for deterministic operations.

### Reference File Rules

1. **Keep references one level deep** - SKILL.md → reference.md ✓, not SKILL.md → a.md → b.md
2. **Add ToC to files > 100 lines** - Helps Claude navigate large references
3. **Link to specific sections** - `[reference.md#section-a](reference.md#section-a)`

For complete context efficiency guide, see [context-efficiency.md](context-efficiency.md).

## Best Practices

### 1. Keep Skills Focused

One skill = one capability

- ✅ `api-docs-writer`, `test-strategy`, `db-migration`
- ❌ `developer-helper`, `backend-tools`

### 2. Write Trigger-Rich Descriptions

Include specific keywords users would naturally mention:

```yaml
description: Generate OpenAPI/Swagger documentation from Express routes or FastAPI endpoints. Use when documenting APIs, creating API specs, or working with OpenAPI, Swagger, REST, GraphQL.
```

### 3. Use `<example>` Tags for Higher Activation

```yaml
description: Generate API documentation. Use PROACTIVELY when documenting APIs. Examples: <example>Context: User asks about API docs user: 'Create OpenAPI spec' assistant: 'I will use api-docs-writer skill'</example>
```

### 4. Use Progressive Disclosure

- SKILL.md: Core instructions (< 500 lines)
- reference.md: Detailed specs (loaded when needed)
- examples/: Extended examples (loaded when needed)

### 5. Context Window Awareness

**DO:**
- Assume Claude's base knowledge
- Include only task-specific context
- Keep SKILL.md under 500 lines

**DON'T:**
- Explain programming basics
- Create monolithic files > 500 lines
- Include unnecessary background

### 6. Use Scripts for Deterministic Operations

Scripts provide reliable, token-efficient functionality. See [scripts-guide.md](scripts-guide.md) for details.

**Use scripts for:** Validation, setup, data transformation
**Don't use scripts for:** User-specific logic, content editing, analysis

## Troubleshooting

### Skill Not Activating

**Quick Fixes:**
1. Add more trigger keywords to description
2. Verify name is lowercase with hyphens only
3. Check YAML syntax (space after colons)
4. Ensure file is named exactly `SKILL.md`
5. Verify Skill tool is enabled in settings.json

**Test:**
```
Ask Claude: "What skills are available?"
```

### Skill Activates at Wrong Times

1. Make description more specific
2. Narrow the scope
3. Add unique trigger keywords

For detailed troubleshooting, see [reference.md](reference.md#troubleshooting-guide).

## Guaranteed Activation: CLAUDE.md Integration

**Problem**: Skills rely on description matching, resulting in ~25% activation rate for edge cases.

**Solution**: Add activation rules directly to CLAUDE.md:

```markdown
## Skill Activation Rules

When the user asks about the following, ALWAYS use the Skill tool:

- **API documentation, OpenAPI** → `api-docs-writer` skill
- **Test strategy, testing approach** → `test-strategy` skill
```

This guarantees skill activation regardless of how the user phrases their request.

## Quick Reference Checklist

When creating a skill:

- [ ] Skill tool enabled in `.claude/settings.json`
- [ ] Directory: `~/.claude/skills/name/` or `.claude/skills/name/`
- [ ] File named exactly `SKILL.md`
- [ ] YAML frontmatter with `---` delimiters
- [ ] `name`: lowercase, hyphens, <64 chars
- [ ] `description`: what + when, trigger keywords, <1024 chars
- [ ] `Use PROACTIVELY` in description for auto-activation
- [ ] Clear "When to Use" section
- [ ] Concrete examples
- [ ] AI Assistant Instructions
- [ ] CLAUDE.md activation rules (for guaranteed activation)

## Examples

This skill includes 5 complete example skills in `examples/`:

1. **[Simple Skill](examples/1-simple-skill/)** - Basic greeting generator
2. **[Skill with References](examples/2-skill-with-references/)** - HTTP status code guide
3. **[Skill with Scripts](examples/3-skill-with-scripts/)** - Project validator
4. **[Skill with Templates](examples/4-skill-with-templates/)** - Changelog generator
5. **[Tool-Restricted Skill](examples/5-tool-restricted-skill/)** - Read-only analyzer

## AI Assistant Instructions

When this skill is activated to help create or improve skills:

### For New Skills

1. **Understand Requirements**:
   - What capability does the user want?
   - Is this a skill or slash command?
   - What complexity level?

2. **Recommend Template**:
   - Simple task → Basic template
   - Complex workflow → Advanced template

3. **Help with YAML**:
   - Suggest descriptive, lowercase-hyphen name
   - Write trigger-rich description
   - Add `allowed-tools` if read-only

4. **Guide Structure**:
   - < 200 lines → Single SKILL.md
   - 200-500 lines → SKILL.md + examples.md
   - > 500 lines → Progressive disclosure with reference.md

### For Existing Skills

1. **Analyze**: Read SKILL.md, check organization
2. **Improve**: Enhance description, add missing sections
3. **Refactor**: Move detailed content to reference.md if > 500 lines

### Testing

1. Verify activation with expected keywords
2. Confirm it doesn't activate for unrelated queries
3. Validate all referenced files exist

### Always

- Use templates from templates/ directory
- Reference examples from examples/ directory
- Point to reference.md for detailed specs
- Point to scripts-guide.md for script questions
- Point to context-efficiency.md for context optimization
- Keep SKILL.md under 500 lines
- Write trigger-rich descriptions
- Remind users about Skill tool permissions
- **Apply 3-level loading model**: metadata (always) → SKILL.md (trigger) → resources (on-demand)
- **Assume Claude is smart**: Don't explain what Claude already knows

### Never

- Create skills without proper YAML frontmatter
- Use uppercase/spaces/underscores in name
- Write vague descriptions without triggers
- Skip "When to Use" section
- Create files > 500 lines without progressive disclosure
- Forget CLAUDE.md integration for critical skills

### When Uncertain

- Ask user about intended use cases
- Show template options
- Suggest simple approach first

## Additional Resources

### Documentation
- **[reference.md](reference.md)** - Complete YAML spec, skills vs commands, tool restrictions, patterns
- **[context-efficiency.md](context-efficiency.md)** - 3-level loading, token optimization, progressive disclosure
- **[scripts-guide.md](scripts-guide.md)** - Guide to using scripts in skills
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

### Examples
Explore `examples/` for 5 complete, working skill examples.

### Scripts
- **[scripts/validate-skill.py](scripts/validate-skill.py)** - Validate SKILL.md files

---

**Current Version:** 3.1.0 | See [CHANGELOG.md](CHANGELOG.md) for history.
