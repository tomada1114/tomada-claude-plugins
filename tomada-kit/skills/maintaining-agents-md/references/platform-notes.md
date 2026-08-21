<!-- platform-annex -->
# Platform notes

The one file in this skill where host and tool names belong. Everything else is written in neutral phrasing; this is the mapping.

## Neutral phrasing → host mechanism

| The skill says | Claude Code | Codex CLI |
|---|---|---|
| "present the options and wait for the user's answer" | `AskUserQuestion` with 2–4 options and a recommendation | ask in plain text and stop for the reply |
| "delegate the project survey" | `Task` / Agent tool, `subagent_type: general-purpose`, `model: sonnet`, prompt = the **contents** of `references/agents/project-surveyor.md` with placeholders filled | read `references/agents/project-surveyor.md` and work through it inline in the main context |
| "run the inventory / sync script" | `Bash` | shell |

Sub-agent prompt handling on Claude Code: a spawned agent's working directory is the repo, not the skill directory, so never hand it the relative path `references/agents/project-surveyor.md`. Read the file, substitute `{{PROJECT_ROOT}}` and `{{INVENTORY_JSON}}`, and pass the resulting text. Any path inside that text must be absolute.

## Host facts this skill encodes

- Claude Code reads `CLAUDE.md` (and `CLAUDE.local.md`, and `./.claude/CLAUDE.md`), never `AGENTS.md`. Hence the stub. Reference: https://code.claude.com/docs/en/memory
- Codex CLI selects one non-empty file per directory in this order: `AGENTS.override.md`, `AGENTS.md`, then names configured by `project_doc_fallback_filenames`; lowercase `agents.md` is not automatic on case-sensitive filesystems (macOS may resolve it as the same path). It never opens `CLAUDE.md` and has no import syntax. Reference: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Host-level global instruction files under `~/.claude` and `CODEX_HOME` load outside the repo on their respective hosts. They carry the developer's personal, cross-project guidelines, which is why the project master should not repeat generic engineering advice. Neither is ever edited by this skill; inventory only reports the Codex budget/source metadata it can detect.
- `.claude/rules/*.md` is a Claude Code feature with no Codex equivalent, so migrate folds those rules into `AGENTS.md`. Hooks exist on both hosts: the scripts move to `.agents/hooks/` and are wired twice — see `hooks.md`.

## Hooks on each host

| | Claude Code | Codex CLI |
|---|---|---|
| Project wiring | `.claude/settings.json` → `hooks`; `.claude/settings.local.json` is personal and never touched | `<git root>/.codex/hooks.json`, or an inline `[hooks]` table in `.codex/config.toml`. A user-level `~/.codex/hooks.json` also exists and is out of this skill's scope; the skill preserves project Codex-only entries |
| Trusting a hook | governed by the workspace/project trust state | project-local hooks require a trusted project layer; non-managed command definitions are reviewed by exact definition (`/hooks`), and editing the command string requires review again |
| Project-root variable | `CLAUDE_PROJECT_DIR`, set to the launch directory | none; there is no `CODEX_*` equivalent |
| Session launched in a subdirectory | the root `.claude/settings.json` hooks do **not** load — project settings come from the launch directory | the root `.codex/hooks.json` still fires |

So: tell the user to start Claude Code at the repo root, and give a package that people work inside its own `.claude/settings.json`. Hook scripts resolve the project root from their own location and detect the host from the payload; `$(git rev-parse --show-toplevel)` in the command string works on both hosts.

## What is lost on Codex

Most modes are file inspection, file edits, and Python scripts from `scripts/`, all of which run identically on both hosts. Claude path-scoped rule triggers have no exact Codex equivalent, so migrate uses the LLM semantic conversion pass and reports the remaining scope trade-off. The other differences are ergonomic:

- The project survey runs inline instead of in a separate context, so the main context carries the manifest and CI file contents it reads. Summarize the survey into the same structured output the reference specifies before drafting, and drop the raw file dumps.
- Approval points are plain questions rather than a selection prompt. Still stop and wait — do not apply edits to rule files without the user's answer.

## State and scratch paths

- Snapshots and any other persistent state: `${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/maintaining-agents-md/<repo-slug>/`.
- Scratch that need not survive: `${TMPDIR:-/tmp}/agent-skills/maintaining-agents-md/`.
- Never write state under a host-namespaced directory such as `~/.claude/` or `~/.codex/` — both hosts must find the same snapshots.
