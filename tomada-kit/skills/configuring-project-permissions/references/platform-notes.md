<!-- platform-annex -->
# Platform notes

The body of this skill names capabilities, not tools. This file is the one place that
maps them to what each host offers. Whichever host runs the skill, its subject is the
same: Claude Code's `.claude/settings.json` in the target repository. Rule strings such
as `Bash(cargo *)` or `WebFetch(domain:*)` in the body are that file's content, not
calls the running host makes.

## Tool mapping

| Neutral phrasing in the body | Claude Code | Codex CLI |
|---|---|---|
| "one round of at most 4 questions, each with 2–4 options … and wait for the answers" (step 3) | `AskUserQuestion` (≤4 questions per call), every question in one call, the loose option first and labelled "(Recommended)" | `request_user_input` where the session exposes it; otherwise one plain-text message in the format of `../ui-ux-designing/references/questions-core.md` § Presenting as plain text (`N. label — description`, `(Recommended: N)`), then wait. |
| `{SKILL_DIR}` in a command (steps 1 and 4) | the skill's base directory shown at load (`${CLAUDE_SKILL_DIR}`) | the directory of this SKILL.md; `<repo>` stays the target repository's path |
| "the next Claude Code session … is the check" (step 4) | the current session keeps its loaded permissions too; start a new session in the repository to see them | the current Codex session never reads the file; the merge script's report (added, kept, shadowed) is the only check available |

## Codex constraints (best-effort degradation)

These are degradation paths for a runtime that does not expose a capability, not a feature list of either product.

- **Option prompt unavailable** → one plain-text message in the `questions-core.md` format → cost: no guarantee lost; map each free-text answer back to the exact rule strings and show the final allow / ask lists before merging, since nothing may be added silently after the table.
- **Reading the user's global Claude Code settings** (`~/.claude/settings.json`, step 2) from a sandboxed session → the read is refused or the file is outside the readable roots → rerun the read through the host's approved escalation path, or ask the user to paste its `permissions` block → cost: one round-trip. Do not skip the check: without it a project rule that a global `ask` or `deny` overrides looks effective when it is not.
- **Git writes under a filesystem sandbox** (the step 4 commit and push) → `Operation not permitted` on `.git/index.lock` or a ref lock, or a blocked network push → rerun that exact operation through the host's approved escalation path → cost: one approval round-trip; no guarantee lost. Never delete a lock file or bypass the pre-commit hook to get around it.
- **No effect observable in-session** → the Codex session cannot exercise the new rules → cost: the "no more prompts" outcome is unverified until the user opens a Claude Code session in the repository; say so in the report.
- **Run as a kickoff stage** → the kickoff state directory and the new clone's sandbox and network limits are covered in `../kicking-off-apps/references/platform-notes.md` (Codex constraints).
