# File contract

The layout every mode converges on, the exact bytes of the managed block, and the host behavior that forces this shape.

## Table of contents

- [Shape](#shape)
- [Managed block](#managed-block)
- [CLAUDE.md states](#claudemd-states)
- [Finding codes](#finding-codes)
- [Host loading facts](#host-loading-facts)
- [When a subdirectory AGENTS.md is warranted](#when-a-subdirectory-agentsmd-is-warranted)
- [What goes where](#what-goes-where)
- [Adjacent files](#adjacent-files)
- [Snapshots](#snapshots)

## Shape

- `AGENTS.md` is the **master**: all tool-agnostic project instructions, in one file per directory that needs one.
- `CLAUDE.md` sitting next to an `AGENTS.md` is a **stub**: a managed block importing the master, optionally followed by a **free section** of Claude-only content.
- Invariant: every directory containing `AGENTS.md` contains a `CLAUDE.md` stub. The reverse never holds — a `CLAUDE.md` with content and no sibling `AGENTS.md` is an orphan and must be migrated, not left.
- The stub is mandatory, not a convenience: Claude Code does not read `AGENTS.md` natively. Without the stub the master is invisible to it.

## Managed block

A compliant stub begins with exactly these three lines (UTF-8, LF), as the first content in the file:

```
<!-- agents-md-sync:begin -->
@AGENTS.md
<!-- agents-md-sync:end -->
```

- The HTML comment markers do not break the import (verified).
- The import is always the bare `AGENTS.md` — relative to the stub's own directory, so a subdirectory stub imports its own sibling master, never the root one.
- Leading blank lines are tolerated when parsing and normalized away when writing.
- Whole blank lines *inside* the block (between a marker and the import line) are not drift: a markdown formatter inserts them, and sync leaves them alone. A padded or indented import line is drift — indented, it is a code block and stops importing.
- Everything after the `end` marker is the free section: hand-maintained, preserved byte-for-byte, never rewritten by sync. Conventional heading `# Claude Code specifics`.
- Writing `` `@AGENTS.md` `` inside backticks makes it literal — that is how prose about the import avoids becoming an import.

Real example (neonify, `CLAUDE.md`) — a pre-marker stub plus a free section that lists hooks, `.claude/rules/`, local skills, and `.claude/settings.json` policy. Its bare `@AGENTS.md` first line is the `legacy-import` state below: sync wraps that line in markers and keeps the rest untouched.

## CLAUDE.md states

| state | meaning | sync action |
|---|---|---|
| `stub` | managed block well-formed, nothing but whitespace after it | verify; rewrite block only if drifted |
| `stub+extras` | managed block plus a free section | same; free section preserved byte-for-byte |
| `legacy` | no managed block, has an old-style body | skip with finding — run migrate first; `--force` only after the body has been moved |
| `legacy-import` | no markers, but a bare `@AGENTS.md` line exists | adopt: wrap that line in markers, keep the remainder as the free section, original order |
| `missing` | `AGENTS.md` here, no `CLAUDE.md` | create the stub |
| `orphan` | `CLAUDE.md` here, no `AGENTS.md` | never touched, always reported; migrate decides |
| `malformed` | markers broken — begin without end, foreign content between them, block not at top | repair if the remainder is recoverable, otherwise report and skip |

Adoption of `legacy-import` is safe and therefore default, not a flag. `--force` on a `legacy` file writes the pure stub and relies on the snapshot for the old body; it is for cleanup after migrate, not a migration shortcut.

## Finding codes

Emitted by inventory and quoted in audit output.

| code | meaning |
|---|---|
| R001 | legacy `CLAUDE.md` — needs migrate |
| R002 | missing stub next to an `AGENTS.md` |
| R003 | orphan `CLAUDE.md` |
| R004 | inverted import (`^@...`) inside an `AGENTS.md` |
| R005 | effective chain over Codex's configured document budget |
| R006 | malformed managed block |
| R007 | `.claude/CLAUDE.md` alternative location has content |
| R008 | `.claude/rules/` present — invisible to Codex |
| R009 | adoptable `legacy-import` stub |
| R010 | `CLAUDE.local.md` present (info only) |
| R011 | active `AGENTS.override.md` shadows the canonical source |
| R012 | active configured fallback filename is not the canonical source |
| R013 | Codex config could not be read completely |

## Host loading facts

Claude Code — source: https://code.claude.com/docs/en/memory

- `@path` imports are resolved relative to the importing file, up to 4 hops deep.
- Import parsing skips code spans and fences.
- A subdirectory `CLAUDE.md` loads lazily, when a file under that directory is read (verified empirically). The root one loads at launch.
- An import that resolves **outside** the working directory triggers a one-time approval dialog — keep every import inside the repo, which the bare `@AGENTS.md` form guarantees.
- `CLAUDE.local.md` is appended after `CLAUDE.md` in the same directory.
- `./.claude/CLAUDE.md` is an alternative project location for the root file.
- `.claude/rules/*.md` are Claude-only. With `paths:` frontmatter they load when a matching file is read; without it, at launch.

Codex CLI — source: https://learn.chatgpt.com/docs/agent-configuration/agents-md (implementation: `codex-rs/core/src/agents_md.rs`)

- At launch it finds the project root by walking up to `.git`, then selects at most one non-empty file per directory from root down to cwd (`AGENTS.override.md`, then `AGENTS.md`, then names in `project_doc_fallback_filenames`), concatenated root-first. An empty candidate is skipped.
- `AGENTS.md` is the canonical lookup name. On a case-sensitive filesystem, names such as lowercase `agents.md` are ignored unless explicitly listed in `project_doc_fallback_filenames`; on macOS's usual case-insensitive filesystem, that spelling may resolve to the same file.
- It **does not descend below cwd**: `packages/api/AGENTS.md` is read only when Codex is launched inside `packages/api`.
- The project and global instruction chain shares `project_doc_max_bytes` (32768 bytes by default). Codex stops adding project documents when the cap is reached; the effective value may come from the global `CODEX_HOME/config.toml` or the project's `.codex/config.toml`. Inventory reports both the configured budget and the global source it could detect.
- No import syntax exists. `@anything` in an `AGENTS.md` is literal text, and `CLAUDE.md` is never opened.
- A host-level global `AGENTS.override.md` or `AGENTS.md` under `CODEX_HOME` is prepended to the project chain. This skill never edits that global file.

Consequences that drive every decision in this skill:

- Anything the whole team needs on both hosts belongs in `AGENTS.md`, because that is the only file both read.
- Deep subdirectory masters are opt-in knowledge for Codex users. Root content is what is guaranteed to load.
- The document cap is a hard ceiling, not a guideline; a deeper file can be absent from the effective context even though it exists on disk.
- An active override or configured fallback is a deliberate source choice that the Claude stub does not reproduce. Inventory reports it instead of silently replacing it.
- An `@./CLAUDE.md` line inside an `AGENTS.md` (seen in `youtube-management/AGENTS.md:1`) is junk text for Codex and an inverted dependency for Claude Code: the master ends up importing the stub. Migrate removes the line and reverses the direction.

## When a subdirectory AGENTS.md is warranted

Two routes lead to one, and they differ on purpose:

- **init** creates one only where a real boundary exists — a package, app, or service directory people `cd` into and work inside (`packages/api`, `apps/web`, `services/worker`). Signals: its own manifest, its own test/build command, its own deploy target. New content for a mere folder of source files goes in the root master.
- **migrate** creates one for every directory-scoped rule (`paths:` with a literal directory prefix that exists, such as `src/**` or `src/**/*.jsx`) — the rule already named that directory as its scope, and folding it into the root is what bloats the root. Pattern-only globs (`**/*.test.ts`) have no directory and go to a compact root section.

Either way the trade-off is the same and is stated in the plan: Claude Code loads a subdirectory master lazily; Codex sees it only when launched inside that directory. Root content is what is guaranteed on both hosts.

Every subdirectory master gets its own `CLAUDE.md` stub in the same directory.

## What goes where

| content | destination |
|---|---|
| commands, architecture, conventions, gotchas, env, test approach | `AGENTS.md` (root, or the owning subdirectory) |
| anything scoped to one package boundary | that package's `AGENTS.md` |
| hooks and what they enforce, `.claude/settings.json` policy, `.claude/rules/` listing, Claude-only skills, host-specific wording | stub free section |
| personal, machine-local, uncommitted preferences | `CLAUDE.local.md` (gitignored) |

Host names and tool names ("Claude", "Claude Code", tool identifiers) in `AGENTS.md` are a defect: the master is read by both hosts and must stay tool-agnostic. Move that wording to the free section.

## Adjacent files

- `CLAUDE.local.md` — personal and gitignored. Reported by inventory, never read into a shared file, never modified, never deleted.
- `.claude/CLAUDE.md` — alternative root location. If it has content, fold it into the root `AGENTS.md` during migrate and remove it; two active root files mean duplicated context and ambiguous ordering.
- `.claude/rules/*.md` — Claude-only. Migrate routes them by glob scope (see `migration.md`).
- `.claude/settings.json` — hook wiring plus permissions and other settings, read only; the skill never writes it. `.claude/settings.local.json` is personal: never read, never written.
- `.codex/config.toml` — may contain Codex's inline `[hooks]` source and instruction settings; inventory reports relevant metadata but never writes it.
- `AGENTS.override.md` — Codex reads it before `AGENTS.md` in the same directory. This skill neither creates nor manages it; report it when it is active so the user knows it wins.

## Snapshots

Every rule-file edit — by script or by hand — is preceded by a snapshot, so any mistake is one command away from reversal.

- Location: `${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/maintaining-agents-md/<repo-slug>/snapshots/<id>/`
- `<repo-slug>` = project directory basename + `__` + first 8 hex of the SHA-1 of its absolute path.
- `<id>` = UTC `YYYYMMDDTHHMMSSZ`, plus `-<label>` when a label is given.
- `manifest.json` records each file's relative path, status (`copied` / `created` / `absent`), and SHA-1.

Commands (run from the skill's `scripts/` directory, project root as the first argument):

```
python3 scripts/snapshot.py save <root> CLAUDE.md AGENTS.md --label pre-migrate
python3 scripts/snapshot.py list <root>
python3 scripts/snapshot.py restore <root> <snapshot-id> --dry-run
```

`restore` refuses a target that is dirty in git and differs from the snapshot unless forced, and leaves files recorded as `created` in place unless `--delete-created` is passed. Give the user the snapshot id in the completion report — it is the undo handle.
