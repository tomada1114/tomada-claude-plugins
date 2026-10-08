<!-- platform-annex -->
# Platform notes

The body of this skill names capabilities, not tools. This file is the one place that
maps them to what each host offers. Whichever host runs the skill, its subjects are the
same two files: Claude Code's `.claude/settings.local.json` and Codex CLI's
`.codex/rules/local.rules` in the target repository, plus the user-level files beside
them. Rule strings such as `Bash(cargo *)` or `prefix_rule(...)` in the body are those
files' content, not calls the running host makes.

## Tool mapping

| Neutral phrasing in the body | Claude Code | Codex CLI |
|---|---|---|
| "one round of at most 4 questions, each with 2–4 options … " (step 3) | `AskUserQuestion` (≤4 questions per call), every question in one call, the loose option first and labelled "(Recommended)" | `request_user_input` where the session exposes it; otherwise one plain-text message in the format of `../ui-ux-designing/references/questions-core.md` § Presenting as plain text (`N. label — description`, `(Recommended: N)`), then wait. |
| `{SKILL_DIR}` in a command (steps 1 and 4) | the skill's base directory shown at load (`${CLAUDE_SKILL_DIR}`) | the directory of this SKILL.md; `<repo>` stays the target repository's path |
| "the next session … keeps the permissions it loaded" (Report) | a running Claude Code session keeps its loaded permissions; start a new session in the repository to see them | Codex reads rules at startup too; a new Codex session in the trusted repository picks up `local.rules` |

## Codex constraints (best-effort degradation)

These are degradation paths for a runtime that does not expose a capability, not a feature list of either product.

- **Option prompt unavailable** → one plain-text message in the `questions-core.md` format → cost: no guarantee lost; map each free-text answer back to the exact rule strings and show the final lists before writing, since nothing may be added silently after the table.
- **Reading or writing user-level files** (`~/.claude/settings.json`, `~/.codex/config.toml`, `~/.codex/rules/default.rules`) from a sandboxed session → refused or outside the writable roots → rerun that read or write through the host's approved escalation path, or ask the user to paste the relevant block → cost: one round-trip. Do not skip the read: without it a project rule that a user-level rule already covers or overrides looks effective when it is not. <!-- neutrality-ignore: N2 -->
- **`.codex/` is read-only inside Codex's workspace sandbox** → writing `.codex/rules/local.rules` from a Codex session is refused → write it through the approved escalation path → cost: one approval round-trip.
- **Git writes under a filesystem sandbox** (step 5's commit and push, a `.gitignore` line) → `Operation not permitted` on `.git/index.lock` or a ref lock, or a blocked network push → rerun that exact operation through the host's approved escalation path → cost: one approval round-trip; no guarantee lost. Never delete a lock file or bypass the pre-commit hook to get around it.
- **No effect observable in-session** → neither host reloads its permissions mid-session → cost: the "no more prompts" outcome is unverified until a new session starts in the repository; the merge report and the `execpolicy check` table are the checks; say so in the report.
- **Run as a kickoff stage** → the kickoff state directory and the new clone's sandbox and network limits are covered in `../kicking-off-apps/references/platform-notes.md` (Codex constraints).
