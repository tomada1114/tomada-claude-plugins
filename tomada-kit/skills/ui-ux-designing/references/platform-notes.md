<!-- platform-annex -->
# Platform notes

Maps the capabilities SKILL.md uses to each host's tools. The body names no tools; it states each capability with its fallback at the point of use. This file is the only place tool names appear.

## Tool mapping

- **Option questions** (Contract "which file is canonical", Workflow step 3, § Asking questions)
  Claude Code: `AskUserQuestion` (≤4 questions per call) / Codex: `request_user_input` where the session exposes it; otherwise one plain-text message in the format of `references/questions-core.md` § Presenting as plain text (`N. label — description`, `(Recommended: N)`), then wait. Pass the JSON blocks of `questions-core.md` / `questions-app-type.md` as-is, one call or message per round.
  On both, the rules in SKILL.md § Asking questions (2–4 options with trade-offs, at most one `(Recommended)`, at most 4 questions per round) do not change.

- **Delegating competitor research** (Workflow step 2)
  Claude Code: `Agent` with `subagent_type: executor` (the low-effort execution tier; criteria in `orchestrating-models`), one spawn, prompt = the filled text of `references/agents/research-competitors.md` with `{SKILL_DIR}` replaced by the skill's absolute path and `{{USER_MATERIAL}}` filled (see SKILL.md step 2).
  Codex: if the session exposes a sub-agent spawn capability, the same filled prompt goes to one sub-agent; otherwise the main session runs the same prompt itself, reading `references/research-methods.md` skill-relative.

- **Web search** (Workflow step 2, `research-methods.md`)
  Claude Code: `WebSearch` for queries, `WebFetch` for reading a found page.
  Codex: its built-in web search, when the session has it enabled.

- **Refero flows** (`research-methods.md` § Sources)
  Claude Code: `mcp__refero__refero_search_flows`, `mcp__refero__refero_get_flow` when the Refero MCP server is connected.
  Codex: the same server's tools when it is configured under `[mcp_servers]` in the Codex config.

- **Skill directory for the contrast script** (§ Contrast pass, `accessibility.md` step 4)
  `{SKILL_DIR}` → Claude Code: the skill's base directory shown at load (`${CLAUDE_SKILL_DIR}`) / Codex: the directory of this SKILL.md. For a symlinked skill, either the link or its target resolves the same files.
  Both: `python3 {SKILL_DIR}/scripts/check_contrast.py <pairs.json>` run from the target repository root; the script is stdlib-only Python 3.

- **Named skills** (`refero-design`, `designing-wireframes`, `refining-requirements`, `orchestrating-models`, a repository's `designing-ui`)
  When one has to be consulted: Claude Code: the `Skill` tool / Codex: open the skill's SKILL.md from the skill catalog path and follow it; if it is not in the catalog (the catalog is truncated when many skills are installed), read `~/.claude/skills/<name>/SKILL.md` (`refero-design`: `~/.agents/skills/refero-design/SKILL.md`). Resolve the child's relative links against the child's own directory. This skill only names them as boundaries or owners; it never runs their workflow.

- **Arguments** (`[output-path]`, `contrast <palette-source> [into <doc>]`)
  Claude Code: `argument-hint` / Codex ignores it — pass the same arguments in the request text (e.g. `$ui-ux-designing contrast <src> into <doc>`).

## Codex constraints (best-effort degradation)

These are degradation paths for a runtime that lacks the capability, not a feature list of either product. A Codex session that exposes a capability uses it as described in Tool mapping.

- No option-prompt tool → numbered plain-text options in one message per round → costs: answers come back as free text, so the main session maps them to options and may spend an extra turn confirming an ambiguous mapping; the 2–4 option limit is kept by convention rather than enforced by the tool.
- No sub-agent delegation → the main session runs the `research-competitors` prompt itself → costs: time (the question rounds wait for the research in the same session) and context isolation — search results and article reads for 3+ products accumulate in the main context before the question rounds. Mitigation: read only what the summary needs, keep only the summary format, and drop raw results from further consideration. Nothing is lost in parallelism, since the delegated path is a single spawn.
- No named low-effort tier (`executor`) → whatever sub-agent the runtime offers, or the main session → costs: effort is not tuned to the fixed-spec collection work; output contract is unchanged.
- No web search → the user supplies product names, URLs, or screenshots, and rows are marked "user-supplied" (passed to the research prompt as `{{USER_MATERIAL}}`); a sub-agent without search marks unconfirmed cells "Unverified" → costs: evidence limited to what the user provides; hands-on and dated-article checks cannot be done by the agent. If the user supplies nothing, skip research and record it as an Open item.
- No Refero server → Mobbin and hands-on walkthroughs from `research-methods.md` § Sources → costs: fewer ready-made multi-step flow examples for Step 2.
- No `${CLAUDE_SKILL_DIR}` expansion → the main session resolves `{SKILL_DIR}` to the loaded skill's absolute path before running the script or filling the prompt → cost: none beyond the resolution step.
- Named skill not installed on the host (`refero-design`, `orchestrating-models`, and the others above) → the boundary still holds: link the existing document if there is one, otherwise hand the palette and visual direction to the user and record the gap as an Open item → costs: no automatic hand-off to the owning skill; `orchestrating-models` tier criteria are unavailable, so the low-effort tier is taken from the rationale in SKILL.md step 2.
