---
name: syncing-agent-tiers
description: >-
  Push the canonical sub-agent tier definitions (executor, architect, scout, worker)
  into every listed repository's .claude/agents/ and .codex/agents/, opening one
  auto-merging PR per repository. Use after changing a tier's model or effort, when
  adding a repository to the sync list, or as the last step of distributing-plugins.
metadata:
  platforms: claude-code
---

# syncing-agent-tiers

Repositories keep their own copies of the tier files because cloud sessions and Codex
read only what is in the repository. This skill makes those copies generated output:
the only place a tier's model or effort is written is `assets/tiers.json`.

## Rules for repositories that receive the tiers

- Repository prose (AGENTS.md, CLAUDE.md, skills) names tiers by agent name and role
  only — never a model name or an effort level. Workflow `agent()` stages that need a
  model name one in a single constant the skill defines once, not inline per stage.
- Tests check structure (the four tiers exist in both hosts, the Codex instructions
  equal the Claude body, Claude files set `model` and `effort`, Codex files omit
  `model`), never the model or effort values.
- Repository-specific agents (any other file in `.claude/agents/`) are not touched.

## Steps

1. Edit `assets/tiers.json` (models, efforts, descriptions, bodies). Keep it in step
   with `orchestrating-models`, which explains the choices.
2. Preview: `python3 scripts/sync_agent_tiers.py --dry-run`.
3. Run: `python3 scripts/sync_agent_tiers.py` (or name repos). Each repo gets a PR from
   a temporary worktree of `origin/main`, with auto-merge queued when the repository
   allows it; the local checkout is not touched. Report every PR URL and every repo
   that printed a failure or "merge it yourself".
4. To add a repository, add it to `assets/repos.json` after its one-time migration
   (prose and tests follow the rules above).

`--render <dir>` writes the files into a checkout without any git step, for a
migration branch.
