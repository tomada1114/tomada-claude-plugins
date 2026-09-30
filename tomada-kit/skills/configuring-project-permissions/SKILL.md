---
name: configuring-project-permissions
description: >-
  Loosen a repository's committed Claude Code permission file (.claude/settings.json) so
  development runs without permission prompts: detect the toolchain (just, make, mise,
  pnpm/npm/yarn/bun, cargo, uv/python, go, swift/xcodebuild/xcodegen, docker, lefthook,
  linters) with scripts/detect_toolchain.py, propose broad per-tool allow rules plus
  docs domains, settle the borderline ones with the user in short question rounds —
  recipes that launch the app, write to GitHub, or release — and merge the result with
  scripts/merge_permissions.py without dropping existing deny rules or hooks. Use when
  setting up permissions for a new or existing project, when a project keeps prompting
  for its own build/test commands, when asked to allow a tool like cargo, uv, just or
  pnpm project-wide, or as stage 5 of kicking-off-apps. Works from Claude Code or Codex;
  the target is always Claude Code's file.
metadata:
  platforms: claude-code, codex
---

# Configuring Project Permissions

The goal is a project where an agent runs every build, test, lint, format, and codegen
command, and every read-only GitHub query, without a prompt — while the few commands
that act on the developer's machine, on GitHub, or on a release still stop for a human.
The user prefers loose: when in doubt between allow and ask for a development command,
propose allow.

The file this skill writes is Claude Code's permission file, whichever host runs the
skill: detection and merging are plain Python over marker files and JSON, so the steps
are the same from a Codex session; see platform notes for sandbox reads. Codex's own sandbox and approval settings are a
different mechanism and are out of scope here.

Two facts shape every rule here (Claude Code permissions docs):

- Rules are evaluated deny → ask → allow across **all** settings files. A project
  `allow` can never override a user-level `ask` or `deny`, and an `allow` never carves
  an exception out of a broader `deny`. If the user wants something that their global
  settings ask about, that change belongs in `~/.claude/settings.json`, not here — say so. <!-- neutrality-ignore: N2 -->
- A rule matches the command after wrappers like `timeout` and `nice` are stripped, but
  environment runners (`mise exec`, `npx`, `docker exec`) are not stripped. Allow a
  runner only together with the inner tool (`Bash(mise exec -- cargo *)`), never bare.

## Contract

**Input:** a repository root (default: the current one). **Output:** its
`.claude/settings.json` with merged rules, committed. Personal preferences go to
`.claude/settings.local.json` only when the user asks for that.

## 1. Detect

```bash
python3 {SKILL_DIR}/scripts/detect_toolchain.py <repo> --json
```

`{SKILL_DIR}` is this skill's absolute directory; the command runs from any directory, since `<repo>` is passed as a path.

It returns the tools with the file that proved each, task-runner recipes and package
scripts, `human_candidates` (recipe names such as `run`, `dev`, `labels`, `ruleset`,
`release-prep`, `bootstrap`, `clean`), a proposed `allow` / `ask` list, and the rules
the file already has. It reads marker files only.

## 2. Read the repository's own policy

The detector knows names, not intent. Before proposing, read:

- `AGENTS.md` / `CLAUDE.md` sections on human approval and on not taking over the
  developer's machine — templates name the recipes reserved for a human there (for
  example a local test run that drives the GUI, or a labels or ruleset sync).
- the existing `.claude/settings.json`: its `deny` rules and hooks are kept verbatim.
- `~/.claude/settings.json` `ask` / `deny` (the user's global Claude Code settings): <!-- neutrality-ignore: N2 -->
  anything already covered there needs no project rule, and anything it blocks cannot
  be loosened here.

Adjust the proposal: move every recipe the policy reserves for a human to `ask`, and
every recipe the detector flagged but the policy treats as routine to `allow`.

## 3. Decide the borderline rules with the user

Present the proposal as a short table — tools detected, how many allow rules, what
stays at ask — then ask only about rules where the answer depends on how the user
works. Ask them in one round of at most 4 questions, each with 2–4 options and what
each costs, the loose option first and marked recommended unless the repository's
policy says otherwise, and wait for the answers. Typical questions:

- Recipes that launch or install the app on this machine (`run`, `dev`, `install-app`):
  allow, or ask each time?
- GitHub writes an unattended run needs (`gh issue create`, `gh pr create`,
  `gh pr merge`): allow, since the repository's `shipping-issues` merges on green CI,
  or ask?
- Web access: every domain (`WebFetch(domain:*)`) or only the stack's documentation
  domains the detector listed?
- Anything the policy reserves for a human that the user may want to own themselves
  (labels, ruleset, release, bootstrap): keep at ask (recommended), or allow?

Skip any question the repository's policy or the user's earlier answers already settle.
A rule the user rejects is dropped; nothing is added silently after the table.

## 4. Merge and commit

Write the agreed rules to a JSON file (`{"allow": [...], "ask": [...]}`), preview, then
merge:

```bash
python3 {SKILL_DIR}/scripts/merge_permissions.py <repo>/.claude/settings.json --rules <rules.json> --dry-run
python3 {SKILL_DIR}/scripts/merge_permissions.py <repo>/.claude/settings.json --rules <rules.json>
```

It appends without duplicating, keeps every other key, and reports an allow rule that
a deny or ask in the same file shadows — resolve each such conflict with the user
rather than deleting the deny. Commit as `chore: loosen Claude Code permissions for
<tools>` and push when the push is authorized (the kickoff gate covers it). The new
rules take effect in the next Claude Code session started in that repository — run from
a Codex session, the current session is unaffected, so the merge report is the check.

## Report

Tools detected, rules added per list, questions asked and the answers, conflicts and how
they were resolved, and anything the user wanted that only a global settings change
could grant.

## Platform notes

Host-specific tool mapping and sandbox recovery: [references/platform-notes.md](references/platform-notes.md).
