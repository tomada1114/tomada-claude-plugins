---
name: authoring-goal-prompts
description: Author a concise, self-contained prompt to hand to Claude Code's /goal command in a separate, unattended session. Researches the target project (CLAUDE.md, dev rules, baseline build/test state, existing patterns) and drafts a goal with measurable done-criteria, transcript-verifiable checks, scope + anti-cheat constraints, and stop rules. Outputs to chat by default; externalizes bulky context to ~/.claude/goal-prompts/<slug>/ only when inlining would bloat it. Decides autonomously, asking only when a goal-defining axis is genuinely ambiguous. Use PROACTIVELY when the user mentions /goal, goal prompt, ゴールプロンプト, /goal に渡す, 自走/無人実行させたい, unattended run, 完了条件を決めて goal を回す, or setting up a long-running autonomous Claude session. Examples: <example>Context: User wants an unattended run user: '/goal に渡すプロンプトを作って' assistant: 'I will use authoring-goal-prompts skill' <commentary>goal-prompt authoring request</commentary></example>
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, Task, AskUserQuestion
argument-hint: "[task to draft a /goal prompt for]"
---

# Goal Prompt Author

Produce a ready-to-paste prompt for Claude Code's `/goal` command, which a person will run in a
**separate, unattended session**. Your output is the prompt itself — you do **not** run `/goal`.

**Don't use this skill for:** running or babysitting `/goal` yourself; one-turn tasks that finish
faster than setting up a goal; subjective goals with no measurable end state ("make the UX nicer").

## Three truths about `/goal` that drive every decision

1. **No human is reachable mid-run.** Every decision the goal session might otherwise ask about
   must be pre-decided and encoded as a fallback rule. You cannot rely on a follow-up question.
2. **A small evaluator model judges only the transcript** — it runs no commands and reads no files.
   "Done" must be provable by text the goal session prints (an exit code, a sentinel line, `git status`).
3. **Optimizing the transcript invites cheating.** A model graded on "looks done" may skip/`xfail`
   tests, weaken assertions, or stub implementations. Forbid this explicitly.

**Concise wins.** A longer prompt is not a better prompt. Include a section only when it removes
ambiguity or changes behavior. Cut empty ceremony.

## Workflow

```
Phase 1: Discovery (autonomous)  →  Phase 2: Draft  →  Phase 3: Decide output mode
   →  Phase 4: Resolve residual ambiguity (ask only if needed)  →  Phase 5: Emit
```

## Phase 1: Discovery (autonomous — decide, don't ask)

Investigate the target project before drafting. Default target is the current working directory
unless the user names another. Gather, in order:

1. **Project rules** — read the target `CLAUDE.md` and any dev-rule/contribution docs. Scope limits
   (e.g. "don't rename/refactor unrelated code") become `CONSTRAINTS` verbatim.
2. **Baseline** — find the verify command (test/build/lint) and determine its **current** state.
   Run it if it's cheap and safe; otherwise confirm it exists and infer state from recent signals.
   A terminal state you cannot reach from the current state is a goal that never ends. Capture this
   as the `BASELINE` section so the goal is reachable.
3. **Existing patterns** — locate concrete files/idioms the work should imitate, to name in `PLAN`
   or `CONTEXT` ("follow the pagination in `src/api/products.ts`").

For a broad/uncertain scope, dispatch an `Explore` agent for items 1 and 3 in parallel. Resolve
everything you can here by investigation — only genuine, goal-defining unknowns reach Phase 4.

## Phase 2: Draft

Fill the scaffold in [assets/goal-prompt-template.md](assets/goal-prompt-template.md), including
only the sections that carry signal. Read [references/goal-authoring-guide.md](references/goal-authoring-guide.md)
while drafting for the mechanics, failure modes, and worked examples.

Always bake in:
- A single, unambiguous **success sentinel** the evaluator can read off the transcript (e.g. require
  the goal session to print `GOAL_DONE: <command> exited 0`). Prefer one objective line over a
  compound multi-clause condition a small model may misjudge.
- **Anti-cheat constraints**: do not skip / `xfail` / disable / delete tests; do not weaken
  assertions; do not stub or mock to pass. The build/tests must pass on the real implementation.
- **Encoded fallbacks**: "if X is ambiguous, prefer Y; if blocked, stop and report" — because the
  goal session cannot ask.
- A **stop ceiling** (`or stop after N turns`) and, for long runs, commit-per-unit + a one-line
  per-iteration progress log so the run is reviewable afterward.

## Phase 3: Decide output mode (autonomous)

- **Default: chat-only.** Print the prompt as one copyable fenced block.
- **Bundle** to `~/.claude/goal-prompts/<slug>/` when supporting material would bloat the prompt —
  rule of thumb: the prompt would exceed ~40–60 lines, or there is reusable reference material
  (a migration inventory, research findings, a design spec, a generated checklist). Keep `goal.md`
  itself short; move the bulk into sibling files and have `CONTEXT` point to them by **absolute path**
  so the goal session reads them on demand. `<slug>` is a deterministic kebab-case summary of the
  goal (~4–6 words); re-running the same goal overwrites the same dir (idempotent).

## Phase 4: Resolve residual ambiguity (ask only if needed)

Use `AskUserQuestion` **only** if a goal-defining axis cannot be settled by investigation — and only
for these: the **done-state**, the **scope boundary**, the **verify method**, the **stop ceiling**.
One round, ≤4 questions, concrete options. If discovery answered it, do not ask. No question is the
expected outcome for well-specified tasks.

## Phase 5: Emit

- Print the concise prompt in one fenced block, ready to paste after `/goal`.
- If bundled: write the files, then print the directory path and a one-line note —
  "In a fresh session run `/goal` with the contents of `~/.claude/goal-prompts/<slug>/goal.md`
  (it references the sibling docs by absolute path)."
- Briefly state which sections you included/omitted and why, plus the baseline you found.

## Self-QA bar (run before emitting — assume a problem exists)

- [ ] `DONE WHEN` is binary and measurable; not subjective.
- [ ] A success **sentinel / objective evidence** is required in the transcript (evaluator can see it).
- [ ] `VERIFY` names the exact command(s); the goal is **reachable** from the captured `BASELINE`.
- [ ] Scope **and anti-cheat** constraints are present (no skip/stub/weaken).
- [ ] A **stop ceiling** and **fallback decisions** are encoded (no human mid-run).
- [ ] No bloat: every section earns its place; bulk is externalized, not inlined.

## Critical rules

- **Never** write a goal you cannot prove from the transcript, or one unreachable from the baseline.
- **Never** pad the prompt. Brevity over completeness.
- **Never** rely on asking mid-run — encode the fallback instead.
- **Always** include the anti-cheat clause for test/build goals.
- **Always** keep `goal.md` short and push bulk to sibling files (absolute paths) when bundling.

## Supporting files

- [assets/goal-prompt-template.md](assets/goal-prompt-template.md) — the adaptive section scaffold (clone and fill).
- [references/goal-authoring-guide.md](references/goal-authoring-guide.md) — evaluator mechanics, failure modes, externalization rule, worked examples (consult while drafting).
