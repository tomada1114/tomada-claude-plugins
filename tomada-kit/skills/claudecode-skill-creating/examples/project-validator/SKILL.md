---
name: project-validator
description: Check a Node project for the setup failures that surface later as confusing runtime errors — malformed package.json, uninstalled node_modules, missing .env, uninitialized git — and scaffold the missing pieces. Use when onboarding to an unfamiliar repo, bootstrapping a new project, or diagnosing "it works on my machine".
---

# Project Validator

Demonstrates bundling `scripts/`. The checks are deterministic, so they live in code: the source never enters the context window, only the output does.

## Validate an existing project

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/validate.py
```

Run it from the project root; every path it checks is relative to the working directory. It exits non-zero when a required check fails, and its report already names the fix for each failure — relay those, and run the commands the user asks for. Do not re-derive the checks by reading files yourself.

## Bootstrap a new project

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/setup.sh
```

Idempotent: it initializes git, writes a `.gitignore` and `README.md`, derives `.env.example` from an existing `.env`, and installs dependencies — each step skipped if already satisfied. Safe to re-run on a partially set-up repo.

## Path form

Scripts are invoked through `${CLAUDE_SKILL_DIR}`, which expands to an absolute path before the model sees it. A hardcoded `~/.claude/skills/...` breaks on plugin install and project checkout, and runs the wrong copy when both exist.
