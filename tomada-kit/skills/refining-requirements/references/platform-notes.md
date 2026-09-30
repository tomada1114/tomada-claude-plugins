<!-- platform-annex -->
# Platform notes

## Tool mapping

- Batched option questions (The loop, step 1; the continue-or-sign-off question in
  step 4) → Claude Code: `AskUserQuestion` (≤4 questions per call) / Codex: `request_user_input` where the session exposes it; otherwise one plain-text message in the format of `../ui-ux-designing/references/questions-core.md` § Presenting as plain text (`N. label — description`, `(Recommended: N)`), then wait.
- Hand-offs named in **Next:** (`designing-wireframes`, `ui-ux-designing`,
  `planning-tickets`, `kicking-off-apps`) → Claude Code: the `Skill` tool / Codex: open the skill's SKILL.md from the skill catalog path and follow it; if it is not in the catalog (the catalog is truncated when many skills are installed), read `~/.claude/skills/<name>/SKILL.md` (`refero-design`: `~/.agents/skills/refero-design/SKILL.md`). Resolve the child's relative links against the child's own directory.
- Constraint files read before the first question → both hosts read `AGENTS.md`,
  `CLAUDE.md`, and `README.md` from the file system; do not rely on the host having
  auto-loaded only its own instruction file.
- `argument-hint` (frontmatter) → Claude Code: `argument-hint` / Codex ignores it — pass the same arguments in the request text (e.g. `$refining-requirements <idea or spec path> --out <path>`)

## Codex constraints (best-effort degradation)

These are degradation paths for runtimes that do not expose the capability, not a
product feature list.

- Structured option prompt → unavailable when the runtime exposes no user-input tool;
  degrades to the plain-message batch above. Cost: no selectable choices, so answers
  arrive as free text and an ambiguous one costs an extra round; the 4-question cap and
  the recommendation marker are self-enforced instead of tool-enforced. Batching,
  concrete options, trade-offs, and the explicit sign-off are unchanged.
- Skill-to-skill hand-off → unavailable when the next skill is not installed or bridged
  on the runtime; degrades to reporting the **Next:** line as a recommendation the user
  starts themselves. Cost: time (a manual step between stages), and the output path a
  kickoff would have passed must be restated, or the default
  `docs/product/requirements.md` is used.
- Invoked outside `kicking-off-apps` → no caller passes `--out` or the "a UX stage
  follows" signal; the skill runs standalone, writes to the default path, and follows the
  body as written. Cost: none beyond the default.
