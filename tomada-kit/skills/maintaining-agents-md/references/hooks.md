# Shared hooks

One copy of each hook script under `.agents/hooks/`, wired from `.claude/settings.json` (Claude Code) and `.codex/hooks.json` (Codex CLI). `.claude/hooks/` is retired as a location.

## Table of contents

- [Why share hooks](#why-share-hooks)
- [Host facts](#host-facts)
- [The portable script pattern](#the-portable-script-pattern)
- [Wiring](#wiring)
- [Adapting an existing script](#adapting-an-existing-script)
- [Repo-wide references to update](#repo-wide-references-to-update)
- [Verification](#verification)
- [When hooks cannot run](#when-hooks-cannot-run)

## Why share hooks

A hook is enforcement: it runs whether or not the session read the rule. A rule in `AGENTS.md` is a reminder. A project that guards `.env` with a hook on one host and a sentence on the other is guarded on one host.

The scripts are already host-neutral in substance — a formatter run, a protected-path check, a lint gate. Only two things tie them to one host: the directory they sit in and the config that wires them. Both are fixable, and nothing is duplicated: one script, two wiring files.

## Host facts

Use the current host documentation for version-sensitive details. The stable project contract below is intentionally limited to the behavior this skill can verify and preserve.

| | Claude Code | Codex CLI |
|---|---|---|
| Project config | `.claude/settings.json` → `hooks` (`.claude/settings.local.json` is personal — never read, never written) | `<git root>/.codex/hooks.json` → `hooks`; also an inline `[hooks]` table in `.codex/config.toml`. Docs: https://learn.chatgpt.com/docs/hooks |
| Schema | `{"hooks": {"<Event>": [{"matcher": "…", "hooks": [{"type": "command", "command": "…", "timeout": N, "async": bool}]}]}}` | identical shape; `type` must be `command`; extra optional keys `statusMessage`, `additionalContextLimit`, `commandWindows` |
| Session started in a subdirectory | root hooks do **not** fire — project settings come from the launch directory | root `.codex/hooks.json` fires; verified with cwd `<root>/sub` |
| Hook command cwd | session cwd | session cwd |
| Project-root variable | `CLAUDE_PROJECT_DIR`, set to the launch directory | none — no `CODEX_*` equivalent |
| Events on both | SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse, SubagentStart, SubagentStop, Stop, PreCompact, PostCompact | same list |
| Claude-only events | Setup, UserPromptExpansion, PermissionDenied, PostToolUseFailure, PostToolBatch, Notification, MessageDisplay, TaskCreated, TaskCompleted, StopFailure, TeammateIdle, InstructionsLoaded, ConfigChange, CwdChanged, DirectoryAdded, FileChanged, WorktreeCreate, WorktreeRemove, Elicitation, ElicitationResult | — |
| Common payload fields | `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `permission_mode` | same names, plus `turn_id` and `model` |
| Shell tool payload | `tool_name: "Bash"`, `tool_input.command` | identical |
| File-edit payload | `tool_name: "Edit"`/`"Write"`, `tool_input.file_path` (`content` too, for `Write`) | `tool_name: "apply_patch"`, `tool_input.command` holds the patch text (`*** Add File:` / `*** Update File:` / `*** Delete File:` / `*** Move to:`, paths absolute or cwd-relative). **No `file_path`** |
| Matcher | regex over `tool_name`, e.g. `Edit\|Write\|Bash` | same, and `Edit`/`Write` are accepted as aliases of `apply_patch` |
| Read tool | `Read`, with `tool_input.file_path` | no such tool — reads go through the shell, so a `Read` matcher is a harmless no-op |
| Stop payload | `stop_hook_active` | `stop_hook_active`, plus `last_assistant_message` |
| Blocking | exit 2, stderr shown to the model; or JSON `{"decision": "block", "reason": "…"}` | identical: exit 2 produces `Command blocked by PreToolUse hook: <stderr>` |
| PostToolUse exit 2 | stderr goes back to the model; the tool has already run | same |
| Trust | governed by the workspace/project trust state; do not infer trust from the presence of a settings file | project-local hooks load only in a trusted project layer; non-managed command definitions require exact-definition review, and changing the command string requires review again. Use `/hooks` to inspect them; bypass flags are for deliberate automation only |

Two consequences worth stating in the project's own rules:

- **Start Claude Code sessions at the repo root.** A session launched inside a package silently runs without the root hooks. A monorepo package people work inside needs its own `.claude/settings.json`; `scripts/share_hooks.py` handles the root only.
- **A mis-resolved script path is a hard failure, not a skipped hook.** The interpreter exits 2 ("can't open file"), which reads to the host as a block, so every matching tool call is refused. This is why the command is wired through the git top level rather than a cwd-relative path.

## The portable script pattern

- **Root from the script's own location**, never from an environment variable: one host has no project-root variable, and a variable that looks host-specific may simply be inherited from whatever process started the session. `hook_payload.project_root()` walks up from the script to the directory holding `.agents/hooks`, then falls back to the git top level.
- **Host from the payload**, never from the environment: `tool_name == "apply_patch"` means parse the patch; a `file_path` means a single edited file. [assets/hooks/hook_payload.py](../assets/hooks/hook_payload.py) and [assets/hooks/hook_payload.mjs](../assets/hooks/hook_payload.mjs) do both and hand back one `Event` with `name`, `tool` (`shell` / `edit` / `other`), `command`, `files` (absolute), `cwd`, and `stop_hook_active`.
- **Exit codes:** 0 allows, 2 blocks and shows stderr to the model; any other non-zero code is a non-blocking error on Claude Code (Codex does not document it — unverified). An unreadable payload exits 0 — a hook that cannot parse its input must not become a wall.
- **Stop hooks honour `stop_hook_active`**, or the gate re-fires on its own output and the turn never ends.
- **Depth is preserved**: `.agents/hooks/x.py` sits as deep as `.claude/hooks/x.py` did, so a relative import such as `../../scripts/lib/…` keeps working.

Worked examples to copy and trim: [guard.py](../assets/hooks/examples/guard.py) (protected paths, `--no-verify`, plain force-push, admin merges), [format.py](../assets/hooks/examples/format.py) (format the edited file), [stop_check.py](../assets/hooks/examples/stop_check.py) (lint gate when the tree changed). Each keeps its project-specific settings in constants at the top.

## Wiring

The canonical command string, identical on both hosts:

```
<interpreter> "$(git rev-parse --show-toplevel)/.agents/hooks/<script>"
```

`<interpreter>` stays whatever the project already used — `uv run --script`, `node`, `python3`. Rewrite `${CLAUDE_PROJECT_DIR}/.claude/hooks/…` and bare `.claude/hooks/…` forms to it.

`.claude/settings.json` is the source of truth for the shared projection because it also carries Claude permissions and other settings. `.codex/hooks.json` is a second Codex source: update the matching shared entries, but preserve Codex-only events/commands and unrelated top-level keys. Inline `[hooks]` in `.codex/config.toml` is another Codex source and is outside this script's write scope. [assets/hooks/examples/settings-hooks.json](../assets/hooks/examples/settings-hooks.json) and [assets/hooks/examples/codex-hooks.json](../assets/hooks/examples/codex-hooks.json) show the common wiring shape.

`scripts/share_hooks.py <root>` is idempotent: relocate `.claude/hooks/**` to `.agents/hooks/` (with `git mv` for tracked files), rewrite the command strings in `.claude/settings.json`, and merge the shareable events into `.codex/hooks.json`. A matching event/matcher/command is refreshed; an unmatched existing Codex command is retained, including one in the same event. Add `--dry-run` for the plan, `--check` for a terse CI-shaped answer, `--json` for machine-readable output.

What it does not do: edit the scripts themselves, touch `.claude/settings.local.json`, rewrite `.codex/config.toml`, or handle a subdirectory's own settings file. Claude-only events are skipped and reported — they stay in `.claude/settings.json`, and the stub's free section is where a reader is told they exist. Codex-only JSON handlers are not treated as drift.

## Adapting an existing script

1. `tool_input.file_path` → `event.files` (a list; a patch can name several).
2. `CLAUDE_PROJECT_DIR` → `project_root()`.
3. Any environment-based host or root detection → payload fields.
4. A `Read` matcher stays; it is a no-op on the host without that tool.
5. Keep the interpreter the project already uses, and keep `../../scripts/lib/…` imports as they are — the new directory sits at the same depth.
6. Constants (protected paths, formatter commands, gate commands) move to the top of the file so the next project can re-tune them without reading the logic.
7. A script meant for one event gates on `event.name` (`if event.name != "Stop": return 0`) even when the original never did — the fixture run feeds it every event, and so may a future wiring change.
8. Adapt every script the inventory listed, not only the ones `share_hooks.py` tagged `adapt-script`; that tag is a substring heuristic and misses a stop gate that never read `tool_input`.
9. Passing `project_root()` or another runtime value into a subprocess argv can newly trigger a bandit-style lint rule (`S603`) that an all-literal argv did not; match the `# noqa` pattern the file already uses.
10. A project that already has its own stdin-JSON helper (`lib/payload.mjs`, `_payload.py`) retires it once every importer has moved to `hook_payload`; check nothing else imports it first.
11. `event.tool` is `read` for a Read call even though it carries `file_path`; a check that answers differently for reads and writes branches on `tool` or `tool_name`, never on "has a file".
12. Path checks port to the patch dialect for free through `event.files`. Content checks (refusing an edit that removes a quality gate, scanning new text for credentials) do not: the patch dialect has no before/after per file. Either parse the `+`/`-` lines of `tool_input.command` yourself or scope that check to the host that sends `file_path`, and say so in a comment.
13. The examples under `assets/hooks/examples/` are the reference shape and are Python; a `.mjs` hook is a port of the same shape onto `hook_payload.mjs` (`loadEvent`, `projectRoot(import.meta.url)`, `event.toolName`). The copied helper is written against a strict baseline, but a project's own lint and format conventions still apply to it — run them before calling the adaptation done.

## Repo-wide references to update

Search the repo for `.claude/hooks` and fix every hit — the path appears outside the settings file more often than expected. A literal search misses three shapes seen in real repos, so search for `hooks` near `.claude` as well: prefix checks such as `startsWith(".claude/")` in a generator, regex literals with escaped separators (`\.claude\/hooks\/`, often inside the guard's own gate-file list), and path segments split across arguments (`path.join(root, ".claude", "hooks", …)` in tests).

- tests that execute or assert on the hook scripts (`tests/hooks.test.ts` and friends);
- CI workflows that run them or list them as changed-path triggers;
- `README.md`, `CONTRIBUTING.md`, and onboarding docs — but not a released `CHANGELOG.md` entry, which records where the files lived at that release (an `Unreleased` section is fair game);
- the free section of `CLAUDE.md` describing what the hooks enforce — that description is no longer host-specific, so it moves into `AGENTS.md` as an "Agent hooks" section (template in `sections.md`). What stays in the free section: Claude-only events and `.claude/settings.json` policy.

## Verification

```bash
cat assets/hooks/fixtures/claude-edit.json | python3 <root>/.agents/hooks/guard.py; echo $?
python3 scripts/share_hooks.py <root> --check     # exit 0 = wiring is settled
python3 scripts/inventory.py <root> --json        # no H001–H006; review H009 separately
```

Then run the project's own lint, format, and type gate over `.agents/hooks/**` (the copied helper and the adapted scripts are now project code, and a stop gate that fails its own lint blocks every turn). Run every fixture in [assets/hooks/fixtures/](../assets/hooks/fixtures/) through every adapted script and check the exit codes: 0 for the ordinary payloads, 2 for the payloads the script is meant to refuse. Both dialects are covered — `claude-edit`, `claude-bash`, `claude-stop`, `codex-apply-patch`, `codex-bash`, `codex-stop`, plus `claude-bash-noverify` and `codex-apply-patch-env` as things a guard must block.

Tell the user two things in the report: hooks do not fire in a session started in a subdirectory of the repo on Claude Code, and Codex project hooks require a trusted project layer plus review of exact command definitions (use `/hooks`; a changed command hash needs review again).

## When hooks cannot run

No git (so no top-level resolution), a CI container, a host without hook support, or a teammate who declines the trust prompt. Hooks are enforcement; when they cannot run, the same intent has to be carried three other ways, in this order of strength:

1. A task-runner recipe (`just check`, `make lint`) that the CI job also calls — one command, same result everywhere.
2. A pre-commit hook or a CI job for the checks that must not be bypassable.
3. A line in `AGENTS.md` naming the rule and the command that enforces it.

Write the rule line regardless. A session that reads `AGENTS.md` and runs the command gets the same outcome as one that tripped the hook, and the rule survives the hook being removed.
