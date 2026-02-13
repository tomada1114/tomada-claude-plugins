---
name: claudecode-skill-creating
description: Guide for creating and improving Claude Code skills. Use PROACTIVELY when creating a new skill from scratch, updating or refactoring an existing skill, troubleshooting skill activation or YAML frontmatter issues, understanding skills vs slash commands, configuring Skill tool permissions (allowed-tools), integrating skills with CLAUDE.md for guaranteed activation, working with context fork or subagent orchestration, designing progressive disclosure with references/ and assets/, converting documentation into skill format.
---

# Skill Creator Guide

Skills are modular packages that extend Claude's capabilities with specialized knowledge, workflows, and tools. They transform Claude from a general-purpose agent into a domain specialist equipped with procedural knowledge no model fully possesses.

## Core Principles

### Concise is Key

The context window is a public good. Skills share it with system prompts, conversation history, other skills' metadata, and user requests.

**Default assumption: Claude is already very smart.** Only add context Claude does not already have. Challenge each piece of information: "Does Claude really need this?" Prefer concise examples over verbose explanations.

### Degrees of Freedom

Match instruction specificity to the task's fragility:

- **High freedom** (text instructions): Multiple valid approaches, context-dependent decisions. Use when heuristics guide the approach.
- **Medium freedom** (pseudocode/scripts with parameters): A preferred pattern exists but some variation is acceptable.
- **Low freedom** (specific scripts, few parameters): Operations are fragile, consistency is critical, a specific sequence must be followed.

Think of Claude exploring a path: a narrow bridge with cliffs needs specific guardrails (low freedom), while an open field allows many routes (high freedom).

## Anatomy of a Skill

### Canonical Directory Structure

```
skill-name/
├── SKILL.md              # Required. Instructions (<500 lines)
├── scripts/              # Executable code (Python/Bash)
├── references/           # Documentation loaded as needed
└── assets/               # Files used in output (templates, icons, fonts)
```

- **scripts/**: Token-efficient — code is NOT loaded into context, only execution output. Use for deterministic operations.
- **references/**: Loaded only when Claude determines it is needed. Keep files one level deep from SKILL.md. For files >100 lines, include a table of contents.
- **assets/**: Templates, images, boilerplate copied or adapted for output. Not loaded into context until needed.

### YAML Frontmatter

#### Tier 1: Standard Fields (portable skill format)

```yaml
---
name: kebab-case-name        # Required. Max 64 chars. Regex: ^[a-z0-9][a-z0-9-]*[a-z0-9]$
description: "..."           # Required. THE primary trigger mechanism. Max 1024 chars
license: "..."               # Optional. License terms or pointer to LICENSE.txt
compatibility: "..."         # Optional. Rarely needed. Environment requirements (max 500 chars)
---
```

Skills using only Tier 1 fields are portable and pass the official `package_skill.py` validation.

#### Tier 2: Claude Code Extension Fields

These fields are supported by Claude Code runtime but are NOT part of the portable skill format:

| Field | Type | Purpose |
|-------|------|---------|
| `allowed-tools` | String | Restrict tools (e.g., `Read, Grep, Glob`) |
| `argument-hint` | String | Hint in autocomplete (e.g., `[issue-number]`) |
| `disable-model-invocation` | Boolean | `true` = user-only invocation (deploy, commit) |
| `user-invocable` | Boolean | `false` = hidden from `/` menu (Claude-only) |
| `model` | String | Explicit model selection |
| `context` | String | `fork` for isolated subagent execution |
| `agent` | String | Agent type for fork (`Explore`, `Plan`, `general-purpose`) |
| `hooks` | Object | Lifecycle hooks |

See [references/yaml-spec.md](references/yaml-spec.md) for complete field reference.

### Progressive Disclosure (Three-Level System)

1. **Metadata** (name + description, ~100 words) — Always in context
2. **SKILL.md body** (<5k words) — Loaded when skill triggers
3. **Bundled resources** — Loaded as needed (unlimited; scripts can execute without loading)

Keep SKILL.md under 500 lines. When approaching this limit, split content into `references/` files. Reference them from SKILL.md with clear "when to read" guidance.

## Description: The Primary Trigger

The description field is the **sole mechanism** Claude uses to decide when to activate a skill. The SKILL.md body is only loaded AFTER triggering — so "When to Use This Skill" sections in the body are not helpful for activation.

**All trigger information must go in the description field:**
- What the skill does
- Specific scenarios and keywords that should trigger it
- Include "Use PROACTIVELY when..." for auto-activation
- Optionally include `<example>` tags for higher activation rate

```yaml
# Good: Comprehensive triggers in description
description: "Use this skill whenever the user wants to create, read, edit, or manipulate
Word documents (.docx files). Triggers include: any mention of 'Word doc', '.docx', or
requests to produce professional documents with formatting. Also use when extracting content
from .docx files or working with tracked changes."

# Bad: Vague, no triggers
description: "Helps with document processing"
```

## What NOT to Include

A skill should only contain files that directly support its functionality:

- NO `README.md`, `INSTALLATION_GUIDE.md`, `QUICK_REFERENCE.md`, `CHANGELOG.md`
- NO auxiliary context about the creation process, setup procedures, or user-facing docs
- NO explanations of concepts Claude already knows (programming basics, common libraries)
- Use git history instead of version tracking files

## Skill Creation Process

### Step 1: Understand with Concrete Examples

Ask the user for concrete usage examples. Clarify what functionality the skill supports and what triggers should activate it. Conclude when usage patterns are clear.

### Step 2: Plan Reusable Contents

Analyze each example: What scripts, references, or assets would be helpful when executing these workflows repeatedly?

- Code rewritten repeatedly → `scripts/`
- Documentation Claude should reference → `references/`
- Boilerplate/templates used in output → `assets/`

### Step 3: Initialize the Skill

Create the directory and SKILL.md with proper frontmatter:

```bash
mkdir -p ~/.claude/skills/my-skill-name  # personal
mkdir -p .claude/skills/my-skill-name    # project (shared via git)
```

### Step 4: Edit and Implement

1. Implement reusable resources first (scripts, references, assets)
2. Test scripts by actually running them
3. Write SKILL.md body in imperative/infinitive form
4. Delete unused example/placeholder files

### Step 5: Test and Validate

- Verify activation with various phrasings
- Confirm Claude follows instructions correctly
- Check all referenced files exist and paths are correct

### Step 6: Iterate

Use the skill on real tasks, notice struggles, update SKILL.md or resources, and test again.

## Skills vs Slash Commands

| Aspect | Slash Commands | Skills |
|--------|---------------|--------|
| Activation | Manual only | Auto or manual |
| Structure | Single .md file | Directory with resources |
| Tool restrictions | No | Yes (`allowed-tools`) |
| Invocation control | No | Yes |
| Fork context | No | Yes (`context: fork`) |

Use **slash commands** for simple, frequent manual operations. Use **skills** for complex workflows, auto-discovery, tool restrictions, or bundled resources.

## Critical: Skill Tool Permissions

The Skill tool is denied by default. Enable it in `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": ["Skill(*)"]
  }
}
```

Or use CLI flag: `--allowed-tools "Skill"`

## Guaranteed Activation: CLAUDE.md Integration

Skills rely on description matching (~25% activation rate for edge cases). For guaranteed activation, add rules to CLAUDE.md:

```markdown
## Skill Activation Rules

When the user asks about the following, ALWAYS use the Skill tool:

- **API documentation, OpenAPI, Swagger** → `api-docs-writer` skill
- **Test strategy, testing approach** → `test-strategy` skill
```

## Subagent Orchestration Pattern

For skills requiring multi-phase quality control, use dedicated subagents:

```
your-skill/
├── SKILL.md                  # Orchestrator
└── scripts/                  # Evaluation scripts (optional)

.claude/agents/your-skill/    # Dedicated subagents
├── evaluator-a.md            # haiku - lightweight evaluation
├── improver-a.md             # sonnet - quality improvements
```

**Principles:** Parallel evaluation (haiku, fast/cheap) → Targeted improvement (sonnet, high quality) → Re-evaluate until threshold met. Evaluators detect issues, improvers propose fixes.

## Production Patterns

### QA as Bug Hunting

From Anthropic's PPTX skill: "Assume there are problems. Your job is to find them. Your first render is almost never correct. Approach QA as a bug hunt, not a confirmation step."

### Sub-Agent Review

"USE SUBAGENTS — even for 2-3 items. You have been staring at the code and will see what you expect, not what is there. Subagents have fresh eyes."

### Critical Rules Section

For fragile operations (OOXML, complex formats), add prescriptive "Critical Rules" at the bottom of SKILL.md listing exact constraints that must never be violated.

## Best Practices

- One skill = one capability. Split monolithic skills into focused ones
- Write trigger-rich descriptions with specific keywords and "Use PROACTIVELY when..."
- Use kebab-case for names (e.g., `processing-pdfs`, `analyzing-spreadsheets`)
- Keep SKILL.md under 500 lines; use `references/` for details
- Prefer concise examples over verbose explanations — 2-3 examples suffice
- Always use imperative/infinitive form in SKILL.md body
- Test activation with realistic prompts before publishing
- Add CLAUDE.md activation rules for critical skills

## References

Load these as needed during skill development:

- [references/yaml-spec.md](references/yaml-spec.md) — Complete YAML field specification with Tier 1/Tier 2 details
- [references/patterns-and-structure.md](references/patterns-and-structure.md) — Directory patterns, token efficiency, content type classification
- [references/troubleshooting.md](references/troubleshooting.md) — Diagnosis and fixes for common issues
- [references/scripts-guide.md](references/scripts-guide.md) — When and how to use scripts in skills

## Assets

Start with these templates:

- [assets/basic-skill-template.md](assets/basic-skill-template.md) — For simple, single-file skills
- [assets/advanced-skill-template.md](assets/advanced-skill-template.md) — For complex skills with resources

## Examples

Explore [examples/](examples/) for 4 working skill examples:
1. **[Simple Skill](examples/1-simple-skill/)** — Basic structure
2. **[Skill with References](examples/2-skill-with-references/)** — Progressive disclosure
3. **[Skill with Scripts](examples/3-skill-with-scripts/)** — Python and shell scripts
4. **[Tool-Restricted Skill](examples/4-tool-restricted-skill/)** — Read-only with `allowed-tools`

## AI Assistant Instructions

When this skill is activated to help create or improve skills:

### For New Skills

Follow the 6-step Skill Creation Process above:

1. **Understand**: Ask for concrete usage examples and trigger scenarios. Do not overwhelm with questions — start with the most important ones.
2. **Plan**: Identify what goes in `scripts/`, `references/`, `assets/`. Determine skill vs slash command using the comparison table.
3. **Initialize**: Create directory and SKILL.md with proper frontmatter. Use Tier 1 fields by default; add Tier 2 only when needed.
4. **Edit**: Implement resources first, then write SKILL.md. Write trigger-rich description with ALL "when to use" information. Do NOT put "When to Use" sections in the body.
5. **Test**: Verify activation with various phrasings.
6. **Iterate**: Suggest improvements based on real usage.

Guide structure decisions:
- < 200 lines → Single SKILL.md
- 200-500 lines → SKILL.md + references/
- > 500 lines → Must split with progressive disclosure

### For Existing Skills

1. Read existing SKILL.md and check organization against canonical structure
2. Verify description contains ALL trigger information (not in body)
3. Check for "Concise is Key" violations — remove explanations Claude already knows
4. Suggest moving detailed content to `references/`
5. Add scripts for deterministic, repetitive operations
6. Consider subagent orchestration if multiple evaluation criteria exist

### Always

- Remind users about Skill tool permissions
- Put ALL trigger info in description, never in body
- Suggest CLAUDE.md activation rules for critical skills
- Reference templates from `assets/` directory
- Point to `references/` for detailed specs
- Keep SKILL.md under 500 lines

### Never

- Create skills without proper YAML frontmatter
- Put "When to Use" sections in SKILL.md body (triggers go in description)
- Include README.md, CHANGELOG.md, or auxiliary documentation
- Create monolithic files > 500 lines
- Use `context: fork` without explicit task instructions (guidelines alone fail)
- Confuse `disable-model-invocation` (user-only) with `user-invocable: false` (Claude-only)
- Skip testing activation with realistic prompts
