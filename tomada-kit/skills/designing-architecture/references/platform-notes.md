<!-- platform-annex -->
# Platform notes

The body of this skill names capabilities, not tools. This file is the one place that
maps them to what each host offers.

## Tool mapping

| Neutral phrasing in the body | Claude Code | Codex CLI |
|---|---|---|
| "batched rounds — at most 4 questions per round, 2–4 options each … and wait for the answers" (step 2) | `AskUserQuestion` (≤4 questions per call), one call per round, the recommended option first and labelled "(Recommended)" | `request_user_input` where the session exposes it; otherwise one plain-text message in the format of `../ui-ux-designing/references/questions-core.md` § Presenting as plain text (`N. label — description`, `(Recommended: N)`), then wait. |
| "a library documentation lookup tool" (step 2, decision inventory) | the context7 MCP server (`mcp__context7__resolve-library-id`, then `mcp__context7__query-docs`) when connected | a context7 MCP server if configured under `[mcp_servers]`; otherwise the library's official docs |
| "vendor docs", "the official docs" | `WebFetch` for a known URL, `WebSearch` to find it | the host's web search tool when enabled, or fetching the page when network access is allowed |
| named skills (`recording-architecture-decisions`, `designing-ui`, `steering-the-roadmap`, `updating-docs`, `planning-tickets`, `kicking-off-apps`) | the repository's own skills are read by path from its skills directory; user skills: the `Skill` tool | read the repository's skills by path from `.claude/skills/` or `.agents/skills/`, whichever it ships; user skills: open the skill's SKILL.md from the skill catalog path and follow it; if it is not in the catalog (the catalog is truncated when many skills are installed), read `~/.claude/skills/<name>/SKILL.md` (`refero-design`: `~/.agents/skills/refero-design/SKILL.md`). Resolve the child's relative links against the child's own directory. |

## Codex constraints (best-effort degradation)

These are degradation paths for a runtime that does not expose a capability, not a feature list of either product.

- **Option prompt unavailable** → one plain-text message in the `questions-core.md` format → cost: no guarantee lost; restate each chosen option in the reply that follows, because an ADR is marked Accepted only on an explicit choice.
- **No library documentation tool** → the library's official docs, read directly → cost: more time per decision, and version details may lag the published package; record the docs URL and date checked as usual.
- **No web access** (search disabled or the sandbox blocks network) → options come from what is already in the repository and the model's knowledge, each unverified claim marked unchecked, and every ADR that rests on one left **Proposed** (the body's step 3 rule) → cost: the Sources guarantee (URL + date checked) is lost for those claims; name them in the report as what would settle the decision.
- **Git writes and the repository's checks under a filesystem sandbox** (the step 4 docs build or harness check, commit, and push) → `Operation not permitted` on `.git/index.lock`, a ref lock, or a tool cache under `~/.cache/<tool>` → rerun that exact operation through the host's approved escalation path, or point the tool's cache variable at a writable temp directory → cost: one approval round-trip or a cold cache. Never delete a lock file, skip a check, or bypass the pre-commit hook to get around it.
