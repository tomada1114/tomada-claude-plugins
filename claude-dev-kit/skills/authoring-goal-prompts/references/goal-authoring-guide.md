# Goal authoring guide

Consult while drafting. The SKILL.md workflow is the procedure; this is the *why* plus the failure
modes and worked examples that make a goal robust.

## Contents

- [How `/goal` actually runs](#how-goal-actually-runs)
- [The two failure modes](#the-two-failure-modes)
- [Designing for the small evaluator](#designing-for-the-small-evaluator)
- [Anti-cheat: why and how](#anti-cheat-why-and-how)
- [No human mid-run: encode fallbacks](#no-human-mid-run-encode-fallbacks)
- [The externalization rule](#the-externalization-rule)
- [Section reference](#section-reference)
- [Worked examples](#worked-examples)
- [Good vs bad conditions](#good-vs-bad-conditions)

## How `/goal` actually runs

`/goal <condition>` sets a single goal for a session. After each turn the main model completes, a
**small evaluator model** (Haiku by default) reads the **conversation transcript** and answers
yes/no with a short reason. "no" feeds the reason back and the session takes another turn; "yes"
clears the goal and returns control. It can run unattended for hours. `/goal` shows status
(turns, tokens, elapsed, last reason); `/goal clear` (aliases: stop/off/reset/none/cancel) ends it.

Three consequences flow from this and shape every prompt you write:

1. The evaluator **only sees text in the transcript**. It runs no commands, opens no files, calls no
   APIs. If success isn't visible as printed text, it cannot be judged — and may be judged wrong.
2. There is **no human to ask** between turns. Clarifying questions don't happen; the session just
   keeps acting on whatever the goal said.
3. The main model is, in effect, **graded on the transcript**, which creates pressure to make the
   transcript *look* done. That pressure is the source of cheating (see below).

## The two failure modes

Every weak goal fails in one of two ways. Design against both:

- **Never stops (false negative / infinite loop).** The condition is unreachable, ambiguous, or
  depends on something the evaluator can't see. Burns tokens indefinitely. Mitigations: capture a
  `BASELINE` so the end state is reachable from the start; make `DONE WHEN` objective; always set a
  `STOP RULES` ceiling.
- **Stops too early (false positive).** The evaluator reads optimistic prose ("all tests pass now")
  without fresh evidence, or a compound condition is partly satisfied. Mitigations: require a
  **sentinel line tied to fresh command output**; keep the success check to one unambiguous clause;
  forbid claiming success without showing current output.

## Designing for the small evaluator

The judge is a small model. Make its job trivial and unambiguous:

- **One objective signal beats a five-clause AND.** "the latest `pytest` run printed `GOAL_DONE`"
  is easier and more reliable to judge than "tests pass and coverage is up and lint is clean and
  docs updated and no TODOs". If you truly need several conditions, fold them into one printed
  sentinel the main model emits only when all hold (e.g. instruct it to print `GOAL_DONE` only
  after all checks pass).
- **Demand fresh, objective evidence in the transcript**: exit codes, the test summary line,
  `git status` output, a file count from `ls | wc -l`. Prose assertions are not evidence.
- **Use a sentinel string** that wouldn't appear by accident (`GOAL_DONE: <what>`), and tie it to
  the check ("print it only immediately after `<cmd>` exits 0").

## Anti-cheat: why and how

Because the transcript is what's graded, the cheapest way to "succeed" is to make checks stop
failing rather than make the code correct: commenting out or `xfail`-ing failing tests, deleting
assertions, stubbing/mocking the unit under test, lowering a coverage threshold, catching and
swallowing the error. None of this is malice — it's the gradient. Counter it explicitly in
`CONSTRAINTS`:

> Do not skip, `xfail`, disable, or delete tests. Do not weaken or remove assertions. Do not stub
> or mock the code under test to make checks pass. Do not lower thresholds. The real implementation
> must satisfy the checks.

For coverage/threshold goals, also pin the threshold value so it can't be quietly lowered.

## No human mid-run: encode fallbacks

Whatever you would normally resolve with a follow-up question must be decided *now* and written into
the goal, because the unattended session can't ask. Patterns:

- **Pre-decide likely ambiguities**: "if the API returns both snake_case and camelCase, prefer
  camelCase"; "if a test is genuinely obsolete, leave it and note it — do not delete it."
- **Define give-up behavior**: "if a check stays red after N distinct attempts, stop and summarize
  the blocker" — prevents thrashing on an impossible step.
- **Bound the run**: `or stop after N turns` / a time budget. Always present for long goals.

## The externalization rule

Keep the `/goal` prompt short. When the task needs bulky supporting material, do **not** inline it —
put it in a bundle and reference it.

- **Chat-only (default):** the whole prompt fits comfortably (rule of thumb ≤ ~40–60 lines) and
  needs no external docs. Emit one fenced block.
- **Bundle** to `~/.claude/goal-prompts/<slug>/` when there's reusable bulk: a migration inventory
  (every call site), research findings, a design spec with many acceptance criteria, or a generated
  checklist. Write `goal.md` (still concise) plus sibling files (`inventory.md`, `research.md`,
  `checklist.md`, `context.md`). In `goal.md`'s `CONTEXT`, point to the siblings by **absolute path**
  and instruct the session to read them first. This mirrors progressive disclosure: the goal stays
  small; the bulk loads on demand. `<slug>` is a deterministic kebab-case summary (~4–6 words); the
  dir is auto git-ignored (under `~/.claude/`) and overwriting it on re-run is intended (idempotent).

A self-maintained **checklist artifact** is the cleanest way to make "queue empty" measurable for
backlog/migration goals: have the session maintain `checklist.md` and make `DONE WHEN` = "every item
in `<abs path>/checklist.md` is checked and `<build>` passes."

## Section reference

Core (almost always): `GOAL`, `DONE WHEN`, `VERIFY`, `CONSTRAINTS` (scope + integrity), `STOP RULES`.
Optional (only if they add signal): `CONTEXT`, `BASELINE`, `PRIORITY`, `PLAN`, `OUTPUT`.
See [../assets/goal-prompt-template.md](../assets/goal-prompt-template.md) for the fill-in scaffold.

## Worked examples

### A. Test-fix (chat-only)
See the filled example at the bottom of
[../assets/goal-prompt-template.md](../assets/goal-prompt-template.md): scoped to one directory,
single sentinel, anti-cheat clause, turn ceiling, anti-thrash fallback.

### B. API migration (bundled — inventory is bulky)
The goal references a generated inventory so the prompt stays short:

```
GOAL: Every call site of the deprecated getUserV1 is migrated to getUserV2 and the build passes.

CONTEXT: The complete list of call sites (file:line) is in
  /Users/me/.claude/goal-prompts/getuserv2-migration/inventory.md — read it first and treat it as the work queue.
  Mirror the call style already used in src/api/orders.ts.

BASELINE: `npm run build` currently passes; inventory.md lists 41 call sites across 18 files, none migrated yet.

DONE WHEN: Every item in inventory.md is checked off, `rg "getUserV1" src/` returns no matches, and
  `npm run build` exits 0 — after which print `GOAL_DONE: migration complete, build green`.

VERIFY: After each file, run `npm run build` and paste its result. At the end run `rg "getUserV1" src/`
  and paste the (empty) output. Update inventory.md checkboxes as you go and show the diff.

CONSTRAINTS:
  - Scope: only migrate call sites; do not change getUserV2's behavior or unrelated code.
  - Integrity: do not silence the deprecation by deleting call sites or stubbing; migrate them for real.

STOP RULES: Stop after 60 turns and report remaining items. If a call site can't be mechanically
  migrated (different return shape), leave it, note it in inventory.md, and continue.
```

`inventory.md` (the bulky sibling) holds the 41-line queue, keeping `goal.md` small.

### C. Backlog (self-maintained checklist)
`DONE WHEN: every item in /Users/me/.claude/goal-prompts/<slug>/checklist.md is checked and
`npm test` exits 0; then print GOAL_DONE.` The session maintains the checklist; "queue empty"
becomes a transcript-visible fact.

## Good vs bad conditions

| Bad | Why it fails | Better |
|---|---|---|
| "Improve the auth module" | Subjective, no end state → never stops | "All tests in test/auth pass and lint is clean" |
| "Make the app production-ready" | Not measurable | Enumerate concrete, checkable criteria |
| "All tests pass" (no evidence rule) | Evaluator trusts prose → stops early / cheating | "…and print `GOAL_DONE` after showing `npm test` exit 0" |
| "Migrate the API" (no inventory/scope) | Unbounded, unreachable | Bundle an inventory; scope to call sites; cap turns |
| Five-clause AND in one sentence | Small evaluator misjudges | One printed sentinel emitted only when all hold |
