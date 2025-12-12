---
name: claude-skill-creator
description: Guide for creating effective Claude Code skills with proper YAML frontmatter, directory structure, templates, scripts, and best practices. Use PROACTIVELY when creating new skills, updating existing skills, learning about skill development, troubleshooting skill activation issues, or working with Claude Code skills, skill structure, YAML frontmatter, Skill permission settings, CLAUDE.md integration.
---

# Claude Skill Creator Guide

This guide helps you create well-structured, effective skills for Claude Code. Skills extend Claude's capabilities through organized folders containing instructions, templates, scripts, and resources.

## When to Use This Skill

Use this skill when:
- Creating a new skill from scratch
- Updating an existing skill
- Learning about skill structure and best practices
- Troubleshooting why a skill isn't being activated
- Converting documentation into a skill format
- Understanding skills vs slash commands
- **Configuring Skill tool permissions**
- **Integrating skills with CLAUDE.md for guaranteed activation**

## Critical: Skill Tool Permissions

**Skills are NOT automatically available!** The Skill tool is denied by default. You must explicitly allow it.

### Enable Skill Tool

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
# For personal skills (available across all your projects)
mkdir -p ~/.claude/skills/my-skill-name

# For project skills (shared with team via git)
mkdir -p .claude/skills/my-skill-name
```

### 2. Create SKILL.md

Every skill requires a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: skill-identifier
description: What this skill does and when to use it. Use when [scenario 1], [scenario 2], or working with [keyword1], [keyword2].
---

# Skill Name

[Your skill content here]
```

### 3. Use Templates

Start with our templates:
- [Basic Skill Template](templates/basic-skill-template.md) - For simple skills
- [Advanced Skill Template](templates/advanced-skill-template.md) - For complex skills

## YAML Frontmatter Essentials

### Required Fields

**name:**
- Lowercase letters, numbers, hyphens only
- Maximum 64 characters
- Example: `api-docs-writer`, `test-strategy`, `code-review`

**description:**
- Must describe BOTH what the skill does AND when to use it
- Maximum 1024 characters
- Include trigger keywords users would naturally mention
- Be specific, not generic

**Good Description Example:**
```yaml
description: Generate OpenAPI/Swagger documentation from Express routes, FastAPI endpoints, or GraphQL schemas. Use when documenting APIs, creating API specs, or working with OpenAPI, Swagger, REST, GraphQL.
```

**Bad Description Example:**
```yaml
description: Helps with API documentation
```

### Optional Field: allowed-tools

Restrict Claude's capabilities when the skill is active:

```yaml
---
name: safe-analyzer
description: Analyze code without modifications...
allowed-tools: Read, Grep, Glob
---
```

Use for: read-only operations, security-critical workflows, preventing accidental modifications.

## Skills vs Slash Commands

| Aspect | Slash Commands | Skills |
|--------|---------------|--------|
| Activation | Manual (`/command`) | Automatic (model-invoked) |
| Complexity | Simple prompts | Complex capabilities |
| Files | Single .md file | Directory with resources |
| Supporting Files | No | Yes (templates, scripts, examples) |
| Tool Restrictions | No | Yes (`allowed-tools`) |

**Use Slash Commands for:**
- Frequently-used manual operations
- Simple instructions in one file
- When you want explicit control

**Use Skills for:**
- Complex workflows with multiple resources
- Capabilities Claude should discover automatically
- Team standards and workflows
- When tool restrictions needed

See [reference.md](reference.md) for detailed comparison.

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
├── scripts-guide.md      # Script documentation (if using scripts)
├── templates/            # Reusable templates
│   ├── basic-template.md
│   └── advanced-template.md
├── examples/             # Complete example skills
│   ├── 1-simple-skill/
│   ├── 2-skill-with-references/
│   ├── 3-skill-with-scripts/
│   ├── 4-skill-with-templates/
│   └── 5-tool-restricted-skill/
└── scripts/              # Utility scripts
    ├── validate.py
    └── setup.sh
```

**Progressive Disclosure:** Keep SKILL.md under 500 lines. Use reference files for detailed information that Claude loads on-demand.

## Content Structure Template

```markdown
---
name: skill-name
description: [What it does] and [when to use]. Use when [triggers].
---

# Skill Title

Brief introduction (2-3 sentences).

## When to Use This Skill

- Specific scenario 1
- Specific scenario 2
- Specific scenario 3

## Instructions

1. **Step 1**: First action
2. **Step 2**: Next action
3. **Step 3**: Final action

## Examples

### Example 1: Common Use Case

```language
// Code example
```

## Best Practices

- Practice 1
- Practice 2

## AI Assistant Instructions

When this skill is activated:

1. Always do X
2. Never do Y
3. If uncertain, ask user

## Additional Resources

- [Detailed reference](reference.md)
- [Script guide](scripts-guide.md)
```

## Using Scripts in Skills

Scripts provide deterministic, reliable functionality. See [scripts-guide.md](scripts-guide.md) for complete details.

### When to Use Scripts

✅ **Use scripts for:**
- Validation and checking
- Setup and initialization
- Data transformation
- Complex logic hard for Claude to generate reliably

❌ **Don't use scripts for:**
- User-specific customization
- File content editing
- Analysis and decision-making

### Shell vs Python

**Shell scripts (.sh):** Simple operations, file handling, < 50 lines
**Python scripts (.py):** Complex logic, cross-platform, > 50 lines

**Example:**
```bash
# scripts/setup.sh - Quick environment setup
# scripts/validate.py - Complex validation with error handling
```

See [examples/3-skill-with-scripts/](examples/3-skill-with-scripts/) for complete examples.

## Best Practices

### 1. Keep Skills Focused

One skill = one capability

✅ `api-docs-writer`, `test-strategy`, `db-migration`
❌ `developer-helper`, `backend-tools`

### 2. Write Trigger-Rich Descriptions

Include specific keywords users would naturally mention:

```yaml
description: Generate OpenAPI/Swagger documentation from Express routes, FastAPI endpoints, or GraphQL schemas. Use when documenting APIs, creating API specs, or working with OpenAPI, Swagger, REST, GraphQL.
```

### 3. Use `<example>` Tags for Higher Activation Rate

Add concrete examples in the description to improve activation:

```yaml
description: Generate API documentation. Use PROACTIVELY when documenting APIs. Examples: <example>Context: User asks about API docs user: 'Create OpenAPI spec for my endpoints' assistant: 'I will use api-docs-writer skill' <commentary>Triggered by API documentation request</commentary></example>
```

### 4. Provide Concrete Examples

Show, don't just tell. Include real code examples.

### 5. Use Progressive Disclosure

- SKILL.md: Core instructions (< 500 lines)
- reference.md: Detailed specs (loaded when needed)
- examples.md: Extended examples (loaded when needed)

### 6. Test Your Skills

1. Does it activate with expected keywords?
2. Does Claude follow instructions correctly?
3. Are examples clear and helpful?
4. Does it handle edge cases?

### 7. Context Window Awareness

✅ **DO:**
- Assume Claude's base knowledge
- Include only task-specific context
- Keep SKILL.md under 500 lines
- Use reference files for details

❌ **DON'T:**
- Explain programming basics
- Create monolithic skill files
- Include unnecessary background

## Examples

This skill includes 5 complete example skills:

1. **[Simple Skill](examples/1-simple-skill/)** - Basic greeting generator
2. **[Skill with References](examples/2-skill-with-references/)** - HTTP status code guide with reference.md
3. **[Skill with Scripts](examples/3-skill-with-scripts/)** - Project validator with Python and shell scripts
4. **[Skill with Templates](examples/4-skill-with-templates/)** - Changelog generator with templates
5. **[Tool-Restricted Skill](examples/5-tool-restricted-skill/)** - Read-only code analyzer

Each example demonstrates different skill capabilities and organization patterns.

## Troubleshooting

### Skill Not Activating

**Quick Fixes:**
1. Add more trigger keywords to description
2. Verify name is lowercase with hyphens only
3. Check YAML syntax (space after colons)
4. Ensure file is named exactly `SKILL.md`
5. Verify file path is correct

**Test:**
```
Ask Claude: "What skills are available?"
```

### Skill Activates at Wrong Times

**Solutions:**
1. Make description more specific
2. Narrow the scope
3. Add unique trigger keywords
4. Differentiate from similar skills

See [reference.md](reference.md) for detailed troubleshooting.

## Guaranteed Activation: CLAUDE.md Integration

**Problem**: Skills rely on description matching, resulting in ~25% activation rate for edge cases.

**Solution**: Add activation rules directly to CLAUDE.md for 100% activation:

### Recommended Directory Structure

```
your-project/
├── CLAUDE.md                    # Global rules + activation conditions
├── .claude/
│   ├── settings.json            # Skill permissions
│   ├── agents/                  # Task-specific agents
│   │   └── code-reviewer.md
│   └── skills/                  # Shared knowledge
│       └── my-skill/
│           └── SKILL.md
```

### CLAUDE.md Activation Rules

Add to your project's `CLAUDE.md`:

```markdown
## Skill Activation Rules

When the user asks about the following, ALWAYS use the Skill tool to invoke the specified skill:

- **API documentation, OpenAPI, Swagger** → `api-docs-writer` skill
- **Test strategy, testing approach** → `test-strategy` skill
- **Database migration** → `db-migration` skill
```

This approach guarantees skill activation regardless of how the user phrases their request.

## Quick Reference Checklist

When creating a skill:

- [ ] **Skill tool enabled** in `.claude/settings.json` (`"allow": ["Skill(*)"]`)
- [ ] Directory created: `~/.claude/skills/skill-name/` or `.claude/skills/skill-name/`
- [ ] File named exactly `SKILL.md`
- [ ] YAML frontmatter with `---` delimiters
- [ ] `name`: lowercase, hyphens, <64 chars
- [ ] `description`: what + when, trigger keywords, <1024 chars
- [ ] **`Use PROACTIVELY`** included in description for auto-activation
- [ ] **`<example>` tags** in description for improved matching
- [ ] Clear "When to Use" section
- [ ] Step-by-step instructions
- [ ] Concrete examples
- [ ] AI Assistant Instructions
- [ ] Tested with realistic scenarios
- [ ] **CLAUDE.md activation rules** added (for guaranteed activation)

## Templates

Use these templates to get started quickly:

- **[Basic Skill Template](templates/basic-skill-template.md)** - For simple, straightforward skills
- **[Advanced Skill Template](templates/advanced-skill-template.md)** - For complex skills with multiple features

## Additional Resources

### Detailed Documentation
- **[reference.md](reference.md)** - Complete YAML spec, skills vs commands comparison, tool restrictions, common patterns
- **[scripts-guide.md](scripts-guide.md)** - Comprehensive guide to using scripts in skills

### Examples
Explore the [examples/](examples/) directory for 5 complete, working skill examples covering:
- Basic structure
- Reference files
- Scripts (Python and shell)
- Templates
- Tool restrictions

### Further Reading
- [Keep a Changelog](https://keepachangelog.com/) - For documenting skill versions
- [Semantic Versioning](https://semver.org/) - For versioning skills

## AI Assistant Instructions

When this skill is activated to help create or improve skills:

### For New Skills

1. **Understand Requirements**:
   - What capability does the user want?
   - Is this a skill or slash command? (Use decision framework)
   - What complexity level?

2. **Recommend Template**:
   - Simple task → Basic template
   - Complex workflow → Advanced template
   - Show template content from templates/ directory

3. **Help with YAML**:
   - Suggest descriptive, lowercase-hyphen name
   - Write trigger-rich description with keywords
   - Add `allowed-tools` if read-only or restricted

4. **Guide Structure**:
   - < 200 lines → Single SKILL.md
   - 200-500 lines → SKILL.md + examples.md
   - > 500 lines → Progressive disclosure with reference.md

5. **Add Supporting Files**:
   - Scripts if deterministic operations needed
   - Templates for reusable content
   - Examples for clarity

### For Existing Skills

1. **Analyze Current State**:
   - Read existing SKILL.md
   - Check file organization
   - Identify improvement areas

2. **Suggest Improvements**:
   - Enhance description with more triggers
   - Add missing sections (examples, best practices)
   - Break into multiple files if > 500 lines
   - Add scripts for repetitive tasks
   - Include templates for consistency

3. **Refactor if Needed**:
   - Move detailed content to reference.md
   - Extract examples to examples.md
   - Create script files for automation
   - Add templates directory

### Testing Skills

1. **Verify Activation**:
   - Test with various phrasings that should trigger
   - Confirm it doesn't activate for unrelated queries

2. **Check Instructions**:
   - Ensure AI follows the workflow
   - Validate examples are clear
   - Test edge cases

3. **Validate Files**:
   - All referenced files exist
   - Templates are usable
   - Scripts are executable
   - Examples work correctly

### Always

- Use the templates from templates/ directory
- Reference example skills from examples/ directory
- Point to reference.md for detailed specs
- Point to scripts-guide.md for script questions
- Keep SKILL.md under 500 lines
- Write trigger-rich descriptions
- Include concrete examples
- Test activation with expected keywords

### Never

- Create skills without proper YAML frontmatter
- Use uppercase letters, spaces, or underscores in name field
- Write vague descriptions without triggers
- Skip the "When to Use" section
- Forget AI Assistant Instructions
- Create monolithic files > 500 lines without progressive disclosure
- Use generic trigger keywords
- **Forget to remind users about Skill tool permissions**
- **Skip CLAUDE.md integration for critical skills**

### When Uncertain

- Ask user about intended use cases
- Show template options and let user choose
- Suggest simple approach first, then offer to enhance
- Point to relevant examples from examples/ directory

## Version

**Current Version:** 2.1.0

### Version History

- **2.1.0** (2025-11-29): Activation best practices
  - Added Critical: Skill Tool Permissions section
  - Added Guaranteed Activation: CLAUDE.md Integration section
  - Added `<example>` tag usage in descriptions
  - Added `Use PROACTIVELY` pattern guidance
  - Updated Quick Reference Checklist with activation items
  - Updated AI Assistant Instructions with permission reminders

- **2.0.0** (2025-01-21): Major enhancement
  - Added 5 complete example skills in examples/ directory
  - Created comprehensive scripts-guide.md
  - Created detailed reference.md
  - Added basic and advanced templates
  - Reorganized for progressive disclosure
  - Reduced main SKILL.md from 634 to ~400 lines

- **1.0.0** (Previous): Initial release
  - Basic skill creation guide
  - Essential YAML frontmatter documentation
  - Core best practices
