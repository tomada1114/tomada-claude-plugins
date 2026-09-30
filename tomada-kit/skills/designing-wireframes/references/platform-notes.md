<!-- platform-annex -->
# Platform notes

## Tool mapping

- Batched layout-decision questions (section 4) → Claude Code: `AskUserQuestion` (≤4 questions per call) / Codex: `request_user_input` where the session exposes it; otherwise one plain-text message in the format of `../ui-ux-designing/references/questions-core.md` § Presenting as plain text (`N. label — description`, `(Recommended: N)`), then wait.
- Screen inventory confirmation (section 1) → a plain message on both hosts; wait for
  the user's reply before drawing.
- Neighbouring skills (`refining-requirements`, `ui-ux-designing`, `planning-tickets`,
  `kicking-off-apps`) → Claude Code: the `Skill` tool / Codex: open the skill's SKILL.md from the skill catalog path and follow it; if it is not in the catalog (the catalog is truncated when many skills are installed), read `~/.claude/skills/<name>/SKILL.md` (`refero-design`: `~/.agents/skills/refero-design/SKILL.md`). Resolve the child's relative links against the child's own directory.
- `argument-hint` (frontmatter) → Claude Code: `argument-hint` / Codex ignores it — pass the same arguments in the request text (e.g. `$designing-wireframes <requirements path> --out <path>`)

## Codex constraints (best-effort degradation)

These are degradation paths for runtimes that do not expose the capability, not a
product feature list.

- Structured option prompt → unavailable when the runtime exposes no user-input tool;
  degrades to the plain-message batch above. Cost: no selectable choices, so answers
  arrive as free text and an ambiguous one costs an extra round; the 4-question cap and
  the recommendation marker are self-enforced instead of tool-enforced.
- Skill-to-skill hand-off → unavailable when the neighbouring skill is not installed or
  bridged on the runtime; degrades to naming it as the next step for the user to start.
  Cost: time (a manual step between stages). Without a kickoff caller, no separate
  `ux-flows.md` path is passed, so the wireframes go into the requirements document in
  place (the documented default).
- Everything else — ASCII wireframes, flow diagrams, the skill-relative templates — is
  plain text and file edits, identical on both hosts.
