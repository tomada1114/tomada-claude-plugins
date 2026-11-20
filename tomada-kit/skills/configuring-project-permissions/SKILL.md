---
name: configuring-project-permissions
description: >-
  Set up a repository's personal, uncommitted Claude Code permissions so development
  runs without prompts, in its gitignored .claude/settings.local.json. Generic rules
  (git, gh, coreutils, hook-bypass and force-push denies) go to the user-level
  ~/.claude/settings.json; the project file keeps only what names the repository —
  recipes, scripts, dependency policy, protected files — allow by default, ask only for
  commands that open the app, write to GitHub, release, or change dependencies. Detects
  the toolchain, drops rules a global rule already covers, settles borderline rules in
  one question round, merges without dropping denies or hooks, and migrates a committed
  .claude/settings.json out. Use when setting up or tidying a project's permissions,
  when it keeps prompting for its own build/test commands, when moving permissions out
  of a committed settings file, or as stage 5 of kicking-off-apps.
metadata:
  platforms: claude-code
---

# Configuring Project Permissions

The goal is a repository where an agent runs every build, test, lint, format, codegen,
and cleanup command without a prompt, while the few commands that act on the
developer's machine, on GitHub, on a release, or on the dependency set still stop for a
human. The user prefers loose: when a development command could go either way, propose
allow.

Where Claude Code reads permissions:

| | Claude Code |
|---|---|
| User level (every repository) | `~/.claude/settings.json` `permissions` | <!-- neutrality-ignore: N2 -->
| This repository, personal | `.claude/settings.local.json` (gitignored) |
| Precedence | deny → ask → allow across all files |

The project file is not committed: which commands run without a prompt is each
person's choice, and a committed allow list is reviewed by nobody when it widens. A
committed `.claude/settings.json` may still carry team-wide, non-permission settings
(plugins, marketplaces, MCP servers), never `permissions` or personal hooks.

## Where a rule goes

- **User level** — anything safe and useful in every repository: git and gh reads and
  routine writes, coreutils, language toolchains installed user-wide (`cargo`, `pnpm`,
  `uv`, `mise`), hook-bypass and force-push denies, publish asks. Changing one of these
  is a change for every repository, so propose it and wait for a yes.
- **Project** — anything that names this repository: its task-runner recipes and
  scripts, the recipes its `AGENTS.md`/`CLAUDE.md` reserve for a human, its dependency
  policy, files it protects (an entitlements plist, a generated mirror), its
  format-on-edit hook.
- **Nowhere** — a project rule a user-level rule already covers. A project `allow` adds
  nothing under a user-level `allow`, and cannot beat a user-level `ask`/`deny`: if the
  user wants that loosened, the change belongs in the user-level file — say so.

Precedence makes the project file mostly a list of asks: when the user level already
allows `just *` or `cargo *`, the project file stops only the recipes and subcommands
that need a human, and an `ask` there wins over the global `allow`.

**Deletions.** A recursive `rm` stays at ask in the user level. When the work deletes
the same build output or temporary directory again and again, add a task-runner
recipe that deletes exactly that (`clean`, `prune-temp`) and let the recipe run under
the runner's allow — never a project allow for `rm -rf`.

## Contract

**Input:** a repository root (default: the current one). **Output:** its
`.claude/settings.local.json`, gitignored, plus any
user-level additions the user approved. Nothing is committed unless the repository
needs a `.gitignore` line or has a committed `.claude/settings.json` to migrate — then
that change goes through the repository's own branch, commit, and PR process.

## 1. Detect

```bash
python3 {SKILL_DIR}/scripts/detect_toolchain.py <repo> --json
```

`{SKILL_DIR}` is this skill's absolute directory. It reads marker files and the
user-level settings only, and returns: the tools with the file that proved each, recipes
and package scripts, `human_candidates` and `cleanup_recipes`, the proposed project
`allow`/`ask` with every rule a user-level rule already covers removed
(`covered_by_global`) or blocks (`blocked_by_global`), `global_candidates` for the
user level, the rules already in `.claude/settings.local.json` and in a committed
`.claude/settings.json` (`existing.local`, `existing.committed`, `committed_hooks`),
and whether the project file is ignored by git (`ignored`).

## 2. Read the repository's own policy

The detector knows names, not intent. Before proposing, read:

- `AGENTS.md` / `CLAUDE.md` on human approval and on not taking over the developer's
  machine — they name the recipes reserved for a human (a run that opens the app, a
  labels or ruleset sync, a release, a bootstrap) and the dependency policy.
- a committed `.claude/settings.json`: its `deny` rules and hooks move, they are not
  dropped (step 5).
- `~/.claude/settings.json`, to see what the user level already allows, asks, and <!-- neutrality-ignore: N2 -->
  forbids.

Adjust the proposal: every recipe the policy reserves for a human goes to ask; every
cleanup recipe and every recipe the policy treats as routine stays allowed.

## 3. Decide the borderline rules with the user

Present one short table — tools detected; project allow / ask / deny counts; rules
dropped as covered by the user level; proposed user-level additions — then ask only what depends on how the user works, in one round of at most 4
questions, 2–4 options each with its cost, the loose option first and marked
recommended unless the repository's policy says otherwise. Typical questions:

- Recipes that launch or install the app on this machine (`run`, `dev`,
  `install-app`): ask each time (when the policy reserves them), or allow?
- The proposed user-level additions (`global_candidates`, plus any generic rule found
  in the old committed file): add them to the user-level file, keep them project-only,
  or drop them?
- Anything the policy reserves for a human that the user may want to own (labels,
  ruleset, release, bootstrap): keep at ask (recommended), or allow?

Skip a question the policy or an earlier answer already settles. A rule the user
rejects is dropped; nothing is added silently after the table.

## 4. Write the project file

Write the agreed project rules to a JSON file (`{"allow": [...], "ask": [...],
"deny": [...], "hooks": {...}}`, keys optional), preview, then merge:

```bash
python3 {SKILL_DIR}/scripts/merge_permissions.py <repo>/.claude/settings.local.json --rules <rules.json> --global ~/.claude/settings.json --dry-run
python3 {SKILL_DIR}/scripts/merge_permissions.py <repo>/.claude/settings.local.json --rules <rules.json> --global ~/.claude/settings.json
```

It appends without duplicating, keeps every other key, skips an allow a user-level
rule already covers (`redundant`) or overrides (`shadowed`), merges hook entries, and
reports an allow that an ask or deny in the same file shadows. Existing local rules
that turn out generic (`git grep`, `sleep`, `cd`) are moved to the user level with the
user's yes, then removed from the project file by hand. Apply approved user-level
additions to `~/.claude/settings.json` the same way (the script takes any settings
path), after backing the file up. <!-- neutrality-ignore: N2 -->

## 5. Migrate a committed `.claude/settings.json`

When `existing.committed` or `committed_hooks` is non-empty: move its project-specific
rules and hooks into the local file (step 4), move its generic rules to the user level
(step 3's answer), then remove `permissions` and `hooks` from the committed file —
delete the file if nothing else is left. Update every document and check in the
repository that describes the committed file (search for `settings.json`), add a
CHANGELOG entry if the repository keeps one, and ship it through the repository's own
commit and PR skills. A harness check that reads the committed file should treat it as
optional rather than be deleted.

## 6. Make sure the project file stays out of git

`.claude/settings.local.json` is usually ignored globally already. If `ignored` reports
`false` for it, add the exact path to the repository's `.gitignore` and include that
line in the repository's next commit.

## Report

Tools detected; rules added per file and list; rules dropped as covered by the user
level; user-level additions made; a migrated committed file and the PR that removed
it; questions asked and the answers; conflicts and how they were resolved. New rules
take effect in the next session started in the repository — the current session keeps
the permissions it loaded.
