<!-- platform-annex -->
# Platform notes

The body of this skill names capabilities, not tools. This file is the one place that
maps them to what each host offers.

## Tool mapping

| Neutral phrasing in the body | Claude Code | Codex CLI |
|---|---|---|
| "present the list once — approve as listed, or adjust — and wait for the answer" (Contract) | `AskUserQuestion` (≤4 questions per call), one question, "Approve as listed" first | `request_user_input` where the session exposes it; otherwise one plain-text message in the format of `../ui-ux-designing/references/questions-core.md` § Presenting as plain text (`N. label — description`, `(Recommended: N)`), then wait. |
| `{SKILL_DIR}` in a command (step 1) | the skill's base directory shown at load (`${CLAUDE_SKILL_DIR}`) | the directory of this SKILL.md |
| "the clone's skills directory (`.claude/skills/` or `.agents/skills/`)" (step 2) | read whichever copy exists; the procedure text is the same | same — reading a file by absolute path does not depend on which host discovers skills where |
| "where the runtime can run a command in the background" (step 3.2) | Bash with `run_in_background: true`, then continue with the labels sync | run the labels sync first, then the checks in the foreground |
| named skills (`starting-an-app`, `triaging-issues`, `designing-architecture`, `planning-tickets`, `kicking-off-apps`) | the `Skill` tool; the template's own skills are read by path | open the skill's SKILL.md from the skill catalog path and follow it; if it is not in the catalog (the catalog is truncated when many skills are installed), read `~/.claude/skills/<name>/SKILL.md` (`refero-design`: `~/.agents/skills/refero-design/SKILL.md`); the template's own skills are read by path. Resolve the child's relative links against the child's own directory. |
| arguments (`argument-hint`) | `argument-hint` | ignores it — pass the same arguments in the request text (e.g. `$bootstrapping-from-templates --template OWNER/NAME --repo OWNER/NAME`) |

## Codex constraints (best-effort degradation)

These are degradation paths for a runtime that does not expose a capability, not a feature list of either product.

- **Option prompt unavailable** → the approval question goes out as plain text and the reply is free text → cost: no guarantee lost, but restate the approved remote-write list verbatim before the first write so an ambiguous reply cannot widen it.
- **Background execution unavailable** → labels sync first, then the checks in the foreground → cost: wall-clock time only (a first build can take many minutes); no ordering the result depends on changes, because the commit still waits for green checks.
- **Git writes under a filesystem sandbox** (`git clone`, `git commit`, `git push`, and `gh repo create` through the script) → `Operation not permitted` on `.git/index.lock`, a ref lock, or `.git/FETCH_HEAD` → rerun that exact operation through the host's approved escalation path → cost: one approval round-trip; no guarantee lost. Never delete a lock file, skip the pre-commit hook, or re-clone to get around it.
- **Network blocked by the sandbox** (`gh repo create`, the copy-wait polling, clone, push, label sync) → the call fails or times out → rerun it through the approved escalation path → cost: one approval round-trip. The script is re-runnable and reuses what already exists, so a partial run resumes.
- **Package managers and the template's bootstrap script under a sandbox** (`mise trust`/`mise install`, `pnpm install`, `cargo`, `uv`, `just` recipes that install or build, the template's check command, the pre-commit hook) → a write to `~/.cache/<tool>`, `~/.local/share/<tool>`, or a global store fails with `Operation not permitted` → rerun with the tool's cache variable pointed at a writable temp directory (for example `XDG_CACHE_HOME`, `npm_config_cache`, `CARGO_HOME`, `UV_CACHE_DIR`), or rerun through the approved escalation path → cost: a cold cache, so the first build is slower. Do not weaken or skip a check to get past it.
- **Run as a kickoff stage** → the kickoff state directory and the new clone's sandbox and network limits are covered in `../kicking-off-apps/references/platform-notes.md` (Codex constraints).
