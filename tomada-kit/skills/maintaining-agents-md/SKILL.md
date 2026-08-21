---
name: maintaining-agents-md
description: "Keep a project's agent rule files and hooks in one shape both Claude Code and Codex CLI obey: AGENTS.md is the master, each CLAUDE.md beside it is a thin stub importing it with `@AGENTS.md`, and hook scripts live in .agents/hooks wired from both hosts. Modes: init (survey the project, draft AGENTS.md), audit (find and fix stale, bloated, missing, or host-specific rules), migrate (fold a legacy CLAUDE.md body, .claude/CLAUDE.md, and .claude/rules/*.md into AGENTS.md, then stub CLAUDE.md), sync (regenerate the stubs), hooks (move .claude/hooks scripts into .agents/hooks, wire .claude/settings.json and .codex/hooks.json). Use when creating or improving AGENTS.md or CLAUDE.md, converting CLAUDE.md to AGENTS.md, sharing Claude Code rules or hooks with Codex, cleaning up .claude/rules, folding a session's learnings into the project rules, or checking the rule files are in sync."
argument-hint: "[init | audit | migrate | sync | hooks] [project-root]"
metadata:
  platforms: claude-code, codex
---

# Maintaining AGENTS.md

Without this skill, rule files drift into one of three bad shapes: a CLAUDE.md that only Claude Code reads, an AGENTS.md that imports CLAUDE.md (meaningless to Codex), or two files that say overlapping things. This skill enforces one shape — **AGENTS.md is the master; CLAUDE.md is a stub that imports it** — and carries the host facts that make the shape necessary.

## Why the shape is what it is

- Claude Code does not read AGENTS.md. It reads CLAUDE.md and expands `@path` imports, relative to the importing file, in the root and in subdirectories (subdirectory CLAUDE.md loads when a file under it is read). Source: https://code.claude.com/docs/en/memory
- Codex reads the AGENTS.md chain from the git root down to its **launch directory** only, concatenated, under a shared 32 KiB budget. It has no import syntax and never opens CLAUDE.md. A subdirectory AGENTS.md reaches Codex only when Codex is started inside that directory. Source: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Therefore: everything tool-agnostic lives in AGENTS.md; the stub exists so Claude Code gets the same text; Claude-only mechanics (hooks, settings, `.claude/rules` listing) go in the stub's free section below the managed block. Full spec with edge cases: [references/file-contract.md](references/file-contract.md).

## Contract

**Input:** `$ARGUMENTS` = optional mode (`init` | `audit` | `migrate` | `sync` | `hooks`) and optional project root. No root → git toplevel of the working directory. No mode → run the inventory and follow its `suggested_mode`; say which mode was chosen and why before doing anything else. An explicit mode always wins over `suggested_mode`; when they disagree, say so in one line, proceed with the explicit mode, and report the findings the other mode would handle as fixes of the form "run `migrate`" rather than applying them.

**Reads:** every `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules/**/*.md` under the root (skipping dependency and build directories); for `init`/`audit`, the project's manifests, task runners, CI config, and README; for `hooks`, `.claude/settings.json`, `.codex/hooks.json`, and every script under `.claude/hooks/` and `.agents/hooks/`.

**Writes:** `AGENTS.md` and `CLAUDE.md` files inside the project (root and subdirectories); in `hooks` mode also `.agents/hooks/**`, the `hooks` key of `.claude/settings.json`, `.codex/hooks.json`, and the project files that reference `.claude/hooks` (tests, CI, docs). Never `.claude/settings.local.json`. Before any modification — a snapshot at
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/maintaining-agents-md/<repo-slug>/snapshots/<UTC-timestamp>/`
(`repo-slug` = `<root basename>__<8 hex of sha1(abs root)>`). Restore with
`python3 scripts/snapshot.py restore <root> <snapshot-id>`. Never writes `CLAUDE.local.md`, never deletes a file the snapshot does not hold.

Script paths below are skill-relative; resolve them from this skill's own directory on either host. All scripts take the project root as their first argument and support `--json`.

## Modes

| Mode | Picked automatically when | Does |
|---|---|---|
| `init` | no AGENTS.md and no CLAUDE.md with content | survey → draft AGENTS.md → sync |
| `audit` | the shape is already right | find what is stale, missing, bloated, or host-specific → propose → apply → sync |
| `migrate` | a CLAUDE.md with a body and no managed block (state `legacy`, or `orphan` when no AGENTS.md exists yet), an `@` import inside AGENTS.md, a populated `.claude/CLAUDE.md`, or any `.claude/rules/` | fold content into AGENTS.md → stub CLAUDE.md → sync |
| `sync` | never automatic — explicit only | `scripts/sync_stubs.py`, nothing else |
| `hooks` | H001–H006 present and nothing needs `migrate` | classify hooks → plan → relocate and wire both hosts (`scripts/share_hooks.py`) → adapt the scripts with the payload helper → update references → verify with the fixtures → sync |

Every mode starts with the inventory and ends with sync:

```bash
python3 scripts/inventory.py <root> --json
```

Exit 1 from `inventory.py` means findings exist, not that the script failed. Read `findings`, `suggested_mode`, and the per-file `state` values (`stub`, `stub+extras`, `legacy`, `legacy-import`, `missing`, `orphan`, `malformed`). Finding codes R001–R010 (rule files) and H001–H008 (hooks) are listed at the end of the script's `--help` and explained in [references/file-contract.md](references/file-contract.md).

### init

1. Survey the project. Delegate the survey where the environment supports fresh contexts — fill [references/agents/project-surveyor.md](references/agents/project-surveyor.md) with the absolute root and the inventory JSON and run it on `sonnet` (one spawn; it reads many files whose contents are not needed afterwards). Otherwise work through that file's checklist inline. The survey returns commands with their source `file:line`, an architecture map, environment variables, the test approach, gotchas found in CI and code comments, and candidate package boundaries.
2. Draft the root `AGENTS.md` from [references/sections.md](references/sections.md): only sections the survey filled with project-specific, verifiable content; commands copied from their source, not paraphrased; length matched to substance. A field the survey marked unknown is left out, not written as "unknown" — list the unknowns in your reply instead. Keep the existing language of any material you carry over (a Japanese README yields Japanese rules).
3. Subdirectory `AGENTS.md` only where the survey found a real boundary people work inside (a package with its own manifest and commands). A directory that merely has a different file type does not get one.
4. If the survey's "Host-specific mechanics" section is non-empty (hooks, `.claude/settings.json`, host-only skills or commands), draft the stub too: the managed block from [assets/claude-md-stub.md](assets/claude-md-stub.md) followed by a `# Claude Code specifics` free section describing them. Otherwise sync will create the bare stub.
5. Show the drafts, wait for the user's answer, snapshot (`python3 scripts/snapshot.py save <root> <files being overwritten> --label init --created <files being created>`), write the approved files, then run sync (step below). If the inventory reported H-findings, offer `hooks` next.

### audit

1. Read every AGENTS.md, stub free section, and rule file the inventory listed, and open the project files that let you check each claim (manifests, task runners, CI, the directories named).
2. Evaluate against [references/quality-criteria.md](references/quality-criteria.md): it is a list of pass/fail checks with the evidence to look at, not a score. Report every finding, including low-severity and uncertain ones, with a `must`/`should`/`could` tag — filtering happens when the user chooses what to apply.
3. Present findings in the reference's output format (`[criterion] path:line — issue → fix`), grouped by file, followed by the concrete diffs. Wait for the user's choice of which to apply.
4. Snapshot the files you will touch (`python3 scripts/snapshot.py save <root> <file>... --label audit`), apply the approved diffs, run sync. Sync's own writes (creating a missing stub, adopting a bare import, repairing a block) are the contract, not findings — they happen regardless of which findings were chosen; list them in the report. Findings whose fix is a fold or a deletion (R001, R003, R004, R007, R008) are out of audit's reach: report them with "run `migrate`" as the fix and offer to run it next. Same for H001–H006 with "run `hooks`".

When the user asks to fold *this session's* learnings into the rules, start from [references/session-learnings.md](references/session-learnings.md) instead of step 1 — the reflection questions there replace the full read, and steps 3–4 are the same.

### migrate

Follow [references/migration.md](references/migration.md). The order matters because deletion is last:

1. Classify every source the inventory found: legacy CLAUDE.md body, `.claude/CLAUDE.md`, each rule by `scope` (`global`, `directory`, `pattern`, `mixed`), and any `@` import line inside AGENTS.md.
2. Decide destinations with the table in the reference — global and pattern-only rules → a compact root AGENTS.md section whose heading carries the glob; directory-scoped rules → `<scope_dir>/AGENTS.md` plus its stub; Claude-only mechanics → the stub's free section. A directory-scoped rule has one trade-off to surface: in its own directory it loads lazily in Claude Code but reaches Codex only when Codex is launched there; at the root (heading carries the glob) it is guaranteed on both hosts but costs root lines. Present both with the directory as the recommendation and wait for the answer.
3. Show the full plan — source → destination per block, and the list of files that will be deleted afterwards — and wait for approval.
4. Snapshot every source and destination, write the destinations, then reread each destination and confirm every source block is present before deleting its source. Replace each CLAUDE.md with the stub (keep a free section only for content that is genuinely Claude-only).
5. Run sync. Report what moved where, what was deleted, and the snapshot id. If the inventory reported H-findings, offer `hooks` next.

### sync

```bash
python3 scripts/sync_stubs.py <root> --dry-run   # plan only; exit 1 means writes are pending, not failure
python3 scripts/sync_stubs.py <root>             # snapshot, then write
python3 scripts/sync_stubs.py <root> --check     # exit 1 on drift; for CI or a quick health check
```

Creates missing stubs, adopts a bare `@AGENTS.md` first line by wrapping it in the managed block, repairs a drifted block, and leaves free sections byte-for-byte. It skips a `legacy` CLAUDE.md with a finding — that file needs `migrate`; `--force` overwrites it with a pure stub and is for use only after the content has been moved. Orphan CLAUDE.md files (no AGENTS.md beside them) are reported, never deleted. If the inventory reported H-findings, offer `hooks` next.

### hooks

Follow [references/hooks.md](references/hooks.md). Hook scripts move to `.agents/hooks/` and get wired from both hosts; the rewrite of the scripts themselves is the part no script can do.

1. Read the inventory's `hooks` block — state, events per host, script locations, and the `root_form` of every command — then read every script it listed and every local helper those scripts import (`./lib/*` — the inventory lists wired scripts only). If `suggested_mode` is `migrate`, say so first (contract above) and carry its findings into the report as "run `migrate`".
2. Plan: where each script moves, what changes inside it, which events each host will carry, and every repo file that mentions `.claude/hooks` (grep for it: tests, CI, README, CONTRIBUTING, the stub's free section). Show the plan and wait for the user's answer.
3. `python3 scripts/share_hooks.py <root> --dry-run`, then without the flag — it snapshots, relocates the scripts, rewrites the command strings to the git-toplevel form, and generates `.codex/hooks.json`. Claude-only events stay in `.claude/settings.json` and are reported, not an error.
4. Copy `assets/hooks/hook_payload.py` (or `.mjs`) into `.agents/hooks/` and adapt each script to it: edited files come from `event.files` on both hosts, the root from `project_root()`, the host from the payload. [assets/hooks/examples/](assets/hooks/examples/) hold the target shape for a guard, a formatter, and a stop gate.
5. Update every reference found in step 2, and move the description of what the hooks enforce from the stub's free section into an "Agent hooks" section in `AGENTS.md`.
6. Verify before reporting: every fixture in [assets/hooks/fixtures/](assets/hooks/fixtures/) through every adapted script (0 for ordinary payloads, 2 for what the script must refuse), then `share_hooks.py <root> --check` and the inventory clean of H001–H006.
7. Run sync. Report the snapshot id, the events each host now carries, the Claude-only events left behind, and two facts the user needs: start Claude Code sessions at the repo root, and the first Codex session asks to trust each hook definition.

## Resources

- [references/file-contract.md](references/file-contract.md) — the managed block, the state table, when a subdirectory earns its own AGENTS.md, the host-loading facts and their consequences, what belongs in the free section, snapshot and restore. Read before the first write in any mode.
- [references/quality-criteria.md](references/quality-criteria.md) — audit checks and the finding format. Read in `audit`.
- [references/sections.md](references/sections.md) — section templates for root, monorepo root, package, and pattern-scoped conventions; what to add and what to leave out. Read in `init` and when proposing additions.
- [references/hooks.md](references/hooks.md) — the two-config problem, the verified host facts, the portable script pattern, the canonical command form, the adaptation checklist, and what to do where hooks cannot run. Read in `hooks`.
- [references/migration.md](references/migration.md) — source classification, destination table, the verify-then-delete rule, fixing an inverted import. Read in `migrate`.
- [references/session-learnings.md](references/session-learnings.md) — end-of-session reflection that feeds `audit`.
- [references/agents/project-surveyor.md](references/agents/project-surveyor.md) — the delegated survey prompt for `init`; `{{PROJECT_ROOT}}` and `{{INVENTORY_JSON}}` are filled by the caller with absolute values.
- [references/platform-notes.md](references/platform-notes.md) — host-specific notes: how to wait for the user, how to delegate the survey, and how hooks are trusted on each host.
- `scripts/inventory.py` — enumerate and classify; never writes. `scripts/sync_stubs.py` — the `sync` mode. `scripts/share_hooks.py` — the relocate-and-wire step of `hooks`; `--dry-run`, `--check`, `--no-snapshot`. `scripts/snapshot.py` — `save` / `list` / `restore`. Tests: `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` from the skill directory.
- [assets/claude-md-stub.md](assets/claude-md-stub.md) — the managed block as the script emits it, with an example free section.
- [assets/hooks/](assets/hooks/) — the payload helper for both runtimes, the six payload fixtures plus two a guard must block, worked `guard` / `format` / `stop_check` examples, and both wiring files.

## Critical rules

- Import syntax in the stub is the bare line `@AGENTS.md` — never inside backticks or a code fence (those make it literal), never a path that resolves outside the repository (that triggers an approval dialog and may be declined).
- No `@` import line inside AGENTS.md. Codex reads it as text.
- A CLAUDE.md body is replaced only after its content is verifiably present elsewhere and a snapshot exists; a rule file is deleted under the same two conditions. `CLAUDE.local.md` is personal and is never read into the master or modified.
- Rules keep their original language. Do not translate a project's Japanese rules into English while moving them.
- A hook command is wired through `$(git rev-parse --show-toplevel)`, never through a host-only variable or a cwd-relative path; a mis-resolved script exits 2 and blocks every matching tool call.
- Hook scripts detect the host from the payload, never from environment variables.
