<!-- platform-annex -->
# Platform notes

## Tool mapping

- Question rounds (every stage, the stage 4 gate) → Claude Code: `AskUserQuestion` (≤4 questions per call) / Codex: `request_user_input` where the session exposes it; otherwise one plain-text message in the format of `../ui-ux-designing/references/questions-core.md` § Presenting as plain text (`N. label — description`, `(Recommended: N)`), then wait.
- Child skills by name → Claude Code: the `Skill` tool / Codex: open the skill's SKILL.md from the skill catalog path and follow it; if it is not in the catalog (the catalog is truncated when many skills are installed), read `~/.claude/skills/<name>/SKILL.md` (`refero-design`: `~/.agents/skills/refero-design/SKILL.md`). Resolve the child's relative links against the child's own directory. (The seven other children are bridged there; `refero-design` lives in `~/.agents/skills/`, which Codex reads directly.)
- Template's own skills (`starting-an-app`, `designing-ui`, …) → Claude Code loads `.claude/skills/` of the repository once a session starts there / Codex loads `.agents/skills/`; a template that only ships `.claude/skills/` is read as files (open its `SKILL.md` and follow it).
- Arguments (`[app idea, free-form | resume]`) → Claude Code: `argument-hint` / Codex ignores it — pass the same arguments in the request text (e.g. `$kicking-off-apps resume`).
- Delegation (stages 4 and 8) → Claude Code: `Agent` with `subagent_type: executor` (stage 4 verification) and `worker` (stage 8 issue bodies); tiers per the `orchestrating-models` skill / Codex: a spawned sub-agent if the session exposes one, otherwise inline.
- Handoff (stage 6) → Claude Code: `cd <repo_path> && claude` then `/kicking-off-apps resume` / Codex: `cd <repo_path> && codex` then `$kicking-off-apps resume`.

## Codex constraints (best-effort degradation)

These are degradation paths for a runtime that does not expose the capability, not a feature list of either product.

- Option prompts → plain-text numbered options. Costs nothing in the decisions; answers arrive as free text, so restate what was chosen before writing it to `state.md`.
- Delegation → stage 4 verification and stage 8 body drafting run in the main session. Costs time and context isolation: long check logs and many issue drafts accumulate in this session. Mitigation: draft issue bodies into `$STATE/issues/` one file at a time and keep only the plan table in view.
- `orchestrating-models` is Claude Code only → on Codex, pick the model/effort for sub-agents with Codex's own configuration; the delegation boundaries above still hold. Cost: sub-agent tiering is chosen ad hoc.
- Stage 5 writes `.claude/settings.json`, which only Claude Code reads. On a Codex-only project the stage still runs (the file is harmless), but it does not loosen Codex's sandbox or approvals — those live in Codex's `config.toml` / Rules (`codex-cli-config` skill). Record in `state.md` which host the permissions were set up for. Cost: the loose-permission outcome can't be checked in this session.
- Sandbox: `gh repo create`, `git clone`/`push`, and template bootstrap scripts can fail with `Operation not permitted` under a filesystem sandbox. Re-run that one operation through the host's approved escalation path; do not delete lock files or skip the step. Cost: one approval round-trip per blocked operation.
- `$STATE` (`~/.local/state/agent-skills/…`) and the new clone under `$(ghq root)` are outside a workspace-write sandbox's writable roots: add both as writable roots or approve each write via escalation; never move the state into the template repo. Cost: approval round-trips.
- No network in the default sandbox: `gh repo view/list` before stage 1 and every later `gh`/`git push` fail with a connection error (not `Operation not permitted`); enable network or approve escalation. Cost: one approval round-trip per blocked operation.
- No Refero server → `refero-design` runs from its bundled knowledge plus web search; cost: the direction is not grounded in live Refero references; record it under Open in `state.md`.
