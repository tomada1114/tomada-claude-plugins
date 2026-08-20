---
name: advanced-skill-name
description: What this skill produces, then the triggers — "Use when [concrete situation], [concrete situation], or working with [artifact or keyword]." Keep the key use case first; Claude Code truncates the listing entry at 1536 chars of description + when_to_use.
# allowed-tools: Read, Grep, Glob, Write, Edit   (omit unless pre-approving this skill's own scripts, or an unattended run — see references/yaml-spec.md#allowed-tools)
metadata:
  platforms: claude-code, codex   # or just `claude-code` if this skill is inherently Claude-only —
                                   # see references/agent-neutral-authoring.md before writing the body
# Claude Code extensions (not part of the portable Agent Skills standard):
# when_to_use: "Trigger phrases and example requests"
# disable-model-invocation: true   (user-only; NOT the same as user-invocable: false)
# user-invocable: false            (Claude-only)
# disallowed-tools: AskUserQuestion   <!-- neutrality-ignore: N1 -->
# argument-hint: "[arg1] [arg2]"
# arguments: [arg1, arg2]
# model: <alias>   (fable/opus/sonnet/haiku — never a dated full ID)
# effort: high
# context: fork   <!-- neutrality-ignore: N1 -->
# agent: Explore
# background: false
# paths: "src/**/*.ts"
---

# [Skill Name]

<!-- Delete any heading below you cannot fill with something Claude would not already do unprompted. -->

[One sentence naming the gap: what Claude does without this skill, and where that falls short.]

## Contract

**Input:** [what arrives in `$ARGUMENTS`, and what to do when it is missing]

**Output:** [artifact and its path — derive the path from the input so a re-run lands on top of the previous run, not beside it]

## Phase 1: [Name]

1. [Step.]
2. [Step.]

## Phase 2: [Name]

[Phases run in strict sequence; parallelism happens inside a phase. If this phase spawns sub-agents, name the model for each — `opus` where the sub-agent could come back asking what you meant, `sonnet` for fully specified pass/fail work, `haiku` for judgment-free enumeration. Give each spawn a self-contained prompt with an explicit output path; sub-agents never talk to each other.]

## Resources

- `references/[name].md` — [what it covers, and the condition under which to read it]
- `references/platform-notes.md` — only if `metadata.platforms` includes `codex`: starts with `<!-- platform-annex -->`, holds the Claude/Codex tool mapping and the "what's lost on Codex" list. This is the only place a Claude-specific tool name may appear in body text — see references/agent-neutral-authoring.md.
- `scripts/[name].py` — run as `python3 ${CLAUDE_SKILL_DIR}/scripts/[name].py <args>`; never a hardcoded `~/.claude/skills/...` path <!-- neutrality-ignore: N2 -->
- `assets/[name]` — [boilerplate copied into the output]

Markdown links to bundled files use relative paths (`references/foo.md`) so the validator can resolve them. Commands and sub-agent prompts use `${CLAUDE_SKILL_DIR}/...`, which expands to an absolute path before the model sees it. The two are not interchangeable.

## Critical rules

[Only for genuinely fragile operations — binary formats, irreversible writes, APIs that fail silently. State the exact constraint and what breaks when it is violated. Prescriptiveness outside this section costs quality; delete the section if nothing here is fragile.]
