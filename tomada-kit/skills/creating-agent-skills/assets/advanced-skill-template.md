---
name: advanced-skill-name
description: What this skill produces, then the triggers — "Use when [concrete situation], [concrete situation], or working with [artifact or keyword]." Keep the key use case first; Claude Code truncates the listing entry at 1536 chars of description + when_to_use.
# allowed-tools: Read, Grep, Glob, Write, Edit   (omit unless pre-approving this skill's own scripts, or an unattended run — see references/yaml-spec.md#allowed-tools)
# Claude Code extensions (not part of the portable Agent Skills standard):
# when_to_use: "Trigger phrases and example requests"
# disable-model-invocation: true   (user-only; NOT the same as user-invocable: false)
# user-invocable: false            (Claude-only)
# disallowed-tools: AskUserQuestion
# argument-hint: "[arg1] [arg2]"
# arguments: [arg1, arg2]
# model: <alias>   (usually omit to inherit the session model; never a dated full ID)
# effort: high
# context: fork
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

[Phases run in strict sequence; parallelism happens inside a phase. If this phase spawns sub-agents, name the tier for each — `architect` where the sub-agent could come back asking what you meant, `executor` for fully specified pass/fail work and judgment-free enumeration (criteria: the `orchestrating-models` skill). Give each spawn a self-contained prompt with an explicit output path; sub-agents never talk to each other.]

## Self-check

[Only for a skill that produces an artifact; delete otherwise. Before hand-off: (1) run the check script if there is one; (2) result criteria — at most five conditions observable in the output, taken from what the user has actually sent back; (3) route expectations — the steps that must have happened, in order; (4) on a miss, fix and repeat, twice at most, then hand off naming what still fails and record the miss as a signal. Contract and example: references/self-evaluation.md in creating-agent-skills.]

## Resources

- `references/[name].md` — [what it covers, and the condition under which to read it]
- `scripts/[name].py` — run as `python3 ${CLAUDE_SKILL_DIR}/scripts/[name].py <args>`; never a hardcoded `~/.claude/skills/...` path
- `scripts/tests/test_[name].py` — stdlib `unittest`, discovered with `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` from the skill directory; coverage ≥ 90% (see `references/scripts-guide.md#conventions` for the authoritative rules, checked by `scripts/check_scripts.py`). Generated files (`__pycache__/`, `.pytest_cache/`, `.coverage*`) belong in the enclosing repository's `.gitignore`.
- `assets/[name]` — [boilerplate copied into the output]
- `evals/<case>/prompt.md` + `graders/` — the cases a change to this skill is measured against (two tagged `gate`, one `holdout`); see references/self-evaluation.md in creating-agent-skills

Markdown links to bundled files use relative paths (`references/foo.md`) so the validator can resolve them. Commands and sub-agent prompts use `${CLAUDE_SKILL_DIR}/...`, which expands to an absolute path before the model sees it. The two are not interchangeable.

## Critical rules

[Only for genuinely fragile operations — binary formats, irreversible writes, APIs that fail silently. State the exact constraint and what breaks when it is violated. Prescriptiveness outside this section costs quality; delete the section if nothing here is fragile.]
