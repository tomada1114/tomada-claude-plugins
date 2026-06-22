# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Claude Code plugin marketplace repository containing 4 plugins for extending Claude Code capabilities. The repository is published as a GitHub-hosted marketplace that users install via `/plugin marketplace add tomada1114/tomada-claude-plugins`.

## Repository Structure

```
tomada-claude-plugins/
├── .claude-plugin/
│   └── marketplace.json      # Marketplace definition (required)
├── claude-dev-kit/           # Plugin: Claude Code extension development
│   └── skills/               # 7 skills (skill creation, bootstrap, capture, tmux orchestration, team discussion, harness audit, goal prompt authoring)
├── git-workflow/             # Plugin: Git workflow automation
│   └── commands/             # smart-commit
├── agile-tools/              # Plugin: Agile development tools
│   └── skills/               # planning-tickets, refining-requirements, designing-wireframes, ui-ux-designing
└── content-tools/            # Plugin: Content creation tools
    └── skills/               # tomada-writing, converting-to-wordpress-swell
```

## Plugin Architecture

Each plugin directory follows Claude Code's plugin structure:
- `skills/` - Contains skill directories with `SKILL.md` files
- `commands/` - Contains `.md` files for slash commands
- `agents/` - Contains `.md` files for sub-agents

### marketplace.json Format

```json
{
  "name": "marketplace-name",
  "owner": { "name": "owner-name" },
  "plugins": [
    {
      "name": "plugin-name",
      "source": "./plugin-directory",  // Must start with ./
      "description": "Description"
    }
  ]
}
```

**Critical**: The `source` field must start with `./` (e.g., `"./claude-dev-kit"`, not `"claude-dev-kit"`).

## File Conventions

### SKILL.md Structure
```yaml
---
name: skill-name          # lowercase, hyphens, <64 chars
description: What it does and when to use. Use PROACTIVELY when [triggers].
allowed-tools: Read, Grep, Glob  # Optional: restrict available tools
---

# Skill Content
```

### Sub-Agent Structure
```yaml
---
name: agent-name
description: When to activate with PROACTIVELY keyword and trigger phrases.
tools: Read, Grep, Glob   # Available tools
model: sonnet             # Model selection
color: green              # Terminal color
---

# Agent Instructions
```

### Command Structure
Commands are single `.md` files with YAML frontmatter:
```yaml
---
description: What the command does
allowed-tools: Read, Edit, Write  # Optional
---

# Command Instructions
```

## Working with This Repository

### Adding a New Plugin
1. Create a new directory at repository root (e.g., `my-plugin/`)
2. Add `skills/`, `commands/`, or `agents/` subdirectories as needed
3. Add the plugin to `.claude-plugin/marketplace.json`

### Adding a New Skill
1. Create directory: `<plugin>/skills/<skill-name>/`
2. Create `SKILL.md` with proper YAML frontmatter
3. Optional: Add `reference.md`, `templates/`, `scripts/` for complex skills

### Adding a New Command
1. Create file: `<plugin>/commands/<command-name>.md`
2. Include YAML frontmatter with description

### Adding a New Sub-Agent
1. Create file: `<plugin>/agents/<agent-name>.md`
2. Include YAML frontmatter with name, description, tools, model, color

## Testing Plugins Locally

```bash
# Add local directory as marketplace
/plugin marketplace add ./

# Install specific plugin
/plugin install plugin-name@tomada-claude-plugins
```

