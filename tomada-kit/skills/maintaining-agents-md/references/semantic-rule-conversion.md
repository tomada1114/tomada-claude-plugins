# Semantic rule conversion

Use this reference when a Claude Code rule cannot be copied to Codex without changing when or how it applies. The goal is behavioral parity with an explicit, reviewable approximation—not a mechanically identical file.

## When the LLM pass is mandatory

Use the pass for every `.claude/rules/*.md` file with `paths:` frontmatter, especially `pattern` and `mixed` scopes, and for text that relies on Claude-only loading, imports, tools, matchers, or hook events. A rule with no host-specific behavior and no path scope may be copied mechanically after the normal verification.

Codex loads one selected instruction file per directory at session start and does not re-evaluate a glob when a later file is touched. That is why a Claude `paths:` trigger cannot be represented exactly in `AGENTS.md`.

## Conversion worksheet

For each source block, fill this out before editing a destination:

1. **Intent:** what behavior must change, for whom, and under what condition?
2. **Scope:** the original `paths:` patterns, the directory prefix found by inventory, file types, exclusions, and whether the rule is global.
3. **Mechanics:** commands, tools, hook events, imports, examples, exceptions, and enforcement strength (`must`, `should`, or explanatory context).
4. **Destination:** root section, directory `AGENTS.md`, or Claude stub free section; record why this location is the closest Codex behavior.
5. **Rewrite:** express the behavior as direct, tool-agnostic instructions. Keep the original language. Put the preserved scope in the heading or an explicit `対象` / `Applies to` line.
6. **Uncertainty:** state what Codex cannot enforce exactly, what broader or narrower behavior results, and any user decision still needed.
7. **Verification:** name concrete files and commands that exercise the rewritten rule. Do not invent a command or claim a test passed without evidence.

The output shown to the user must include a source → destination mapping, the rewritten draft, the scope trade-off, uncertainties, and the verification plan. Wait for approval before writing or deleting anything.

## Rewrite rules

- Preserve intent, priority, exceptions, examples, and language. Do not silently weaken a `must` into a suggestion.
- Convert a path trigger into an explicit scope statement. Example: `paths: ["src/**/*.jsx"]` becomes a `src/AGENTS.md` rule with `対象: *.jsx`, or a root heading such as `## JSX conventions — src/**/*.jsx`.
- If the original condition is a negation or a mixed glob, write both the inclusion and exclusion explicitly. If that would be ambiguous in a directory master, prefer a root section with the complete glob and explain the cost.
- Do not invent a Codex tool, matcher, hook event, or automatic trigger. Replace host mechanics with the observable project behavior, or keep the mechanic in the Claude stub free section when it is genuinely Claude-only.
- Keep one destination section per original scope unless the LLM can show that merging preserves every condition. Deduplication must not erase a narrower exception.
- A fallback filename or `AGENTS.override.md` is not a normal migration destination. Inventory reports it; preserve it and ask the user whether the host-specific divergence is intentional.

## Verify, then delete

After writing, reread each destination and compare it against the worksheet, not only against the source text. Check the target paths exist, run the named tests or commands, and run inventory again from the root and from each directory whose scoped rule matters. Do not delete the source rule until the user approves the mapping and the read-back confirms the behavior is represented. If exact parity is impossible, leave the source in place and report the remaining two-host difference.
