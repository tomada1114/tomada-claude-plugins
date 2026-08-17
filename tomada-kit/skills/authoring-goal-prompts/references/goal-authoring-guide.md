# Goal authoring guide

Consult while drafting. The SKILL.md workflow is the procedure; this is the *why* plus the failure
modes and worked examples that make a goal robust.

## Contents

- [How `/goal` actually runs](#how-goal-actually-runs)
- [The two failure modes](#the-two-failure-modes)
- [Designing for the small evaluator](#designing-for-the-small-evaluator)
- [Anti-cheat: why and how](#anti-cheat-why-and-how)
- [No human mid-run: encode fallbacks](#no-human-mid-run-encode-fallbacks)
- [Degraded terminal states](#degraded-terminal-states)
- [The externalization rule](#the-externalization-rule)
- [Checklist bundles: evidence-anchored, skip-aware](#checklist-bundles-evidence-anchored-skip-aware)
- [Proxy verification for artifacts you can't run](#proxy-verification-for-artifacts-you-cant-run)
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
- **Guard against premature sentinel echoes.** The sentinel is quoted inside the goal text itself,
  and the session may restate the goal or read bundle files aloud. Word the requirement as
  "print exactly `GOAL_DONE: …` only immediately after the final verification output, never when
  quoting or discussing the goal" — a small evaluator can mistake an echoed sentinel for the real one.

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
  Size the ceiling from the work, not from vibes: roughly 2–3 turns per work item plus ~10 for
  setup/finish. A ceiling far below that guarantees a false-negative stop on a legitimate run;
  far above it just funds thrashing.

## Degraded terminal states

Some goals end in a step whose success depends on the environment, not the model: `git push`
(auth, network), `gh pr create` (token scopes), publishing, deploying. If the goal's only terminal
state requires that step, an environmental failure turns the run into a thrash loop — the session
retries something it cannot fix until the turn ceiling kills it, and the salvageable work
(local commits) is left unreported.

Fix: define a **second, explicitly-permitted terminal state** that salvages the work and ends the
run cleanly:

> If `git push` or `gh pr create` fails (e.g. auth), keep all local commits and print exactly:
> `GOAL_DONE: fixes committed locally, PR blocked — <reason>`. This also counts as reaching the goal.

Both sentinels share the `GOAL_DONE:` prefix so the small evaluator accepts either; the human
triages the degraded case afterwards. Two rules keep this honest:

- The degraded state must still require the **work itself to be complete and verified** — it only
  waives the environmental step, never the checks. Otherwise it becomes an escape hatch.
- Reserve it for failures the session genuinely cannot fix (auth, network, missing external
  service). "Tests still failing" is never a degraded terminal — that's what STOP RULES' report-
  and-stop is for, and it should read as *not* reaching the goal.

Best paired with authoring-time preflight (SKILL.md Phase 1): check `gh auth status` / remotes
while authoring, record the result in `BASELINE`, and only include the degraded terminal when the
prerequisite is genuinely uncertain at run time.

## The externalization rule

Keep the `/goal` prompt short. Two independent triggers push material into a bundle:

1. **Knowledge transfer (primary).** The goal session is a fresh, often weaker-model session; it
   sees none of your discovery or design reasoning. Design decisions, code patterns worth showing,
   research findings, and pre-answered ambiguities go into support files so the executor never
   re-derives them — see [support-file-guide.md](support-file-guide.md) for the standard menu
   (`design.md`, `examples.md`, `research.md`, `checklist.yaml`, `decisions.md`) and quality rules.
2. **Size (mechanical).** The prompt physically must fit the `/goal` cap.

**The hard cap is 4000 characters** — `/goal` rejects a longer condition. This is mechanical, not a
style call, so *measure* the final prompt (`wc -m`, character count, not `wc -c` bytes) before you
emit — every time, not by eyeball. Crucially, **bundling resets the budget**: only `goal.md` is
passed to `/goal`, so siblings (`inventory.md`, `research.md`, …) don't count against the cap. If
you're near or over 4000, the fix is always to move bulk into siblings until `goal.md` fits, never to
trim load-bearing sections (GOAL / DONE WHEN / VERIFY / CONSTRAINTS / STOP RULES) to squeeze under.

- **Chat-only (default):** the whole prompt fits comfortably (rule of thumb ≤ ~40–60 lines) and
  needs no external docs. Emit one fenced block.
- **Bundle** to `~/.claude/goal-prompts/<slug>/` when either trigger fires: knowledge only this
  session holds (a design, patterns, findings, pre-answered decisions), or reusable bulk (a
  migration inventory, a design spec with many acceptance criteria, a generated checklist). Write
  `goal.md` (still concise) plus siblings from the standard menu in
  [support-file-guide.md](support-file-guide.md). In `goal.md`'s `CONTEXT`, point to the siblings by
  **absolute path** and instruct the session to read them first, and put the divergence rule
  (repo beats stale support-file facts; impossible design → fallback or stop, never improvise) in
  `CONSTRAINTS`. This mirrors progressive disclosure: the goal stays small; the bulk loads on
  demand. `<slug>` is a deterministic kebab-case summary (~4–6 words); the dir is auto git-ignored
  (under `~/.claude/`) and overwriting it on re-run is intended (idempotent).

A self-maintained **checklist artifact** is the cleanest way to make "queue empty" measurable for
backlog/migration goals: have the session maintain `checklist.md` and make `DONE WHEN` = "every item
in `<abs path>/checklist.md` is checked and `<build>` passes." See the next section for how to keep
that honest.

## Checklist bundles: evidence-anchored, skip-aware

A checklist the session maintains is **also a self-graded artifact** — the same gradient that
produces transcript cheating produces boxes ticked without the work behind them. Three rules make
a checklist bundle robust:

1. **Anchor every tick to evidence.** Give each item its own acceptance criterion — the exact
   command and expected result — and require the session to paste that command's fresh output
   *before* ticking. Where a finding was verified at authoring time, say so in the item
   ("verified: X fails with Y") and include the reproduce command, so the session confirms the
   fix against the same signal instead of re-litigating whether the item is real.
2. **Never let boxes alone satisfy `DONE WHEN`.** Pair "every item checked" with a final
   whole-run verification item (full test/build/lint suite, `git status` clean) whose fresh output
   must appear in the transcript. Boxes prove queue progress; commands prove correctness.
3. **Define `[skip]` semantics.** One genuinely blocked item must not hold the run hostage (the
   never-stops failure mode). Rule: an item still red after N distinct attempts is marked
   `[skip] <one-line reason>` and the session moves on; `DONE WHEN` treats checked-or-skipped as
   terminal, but requires all skips listed in the final report/PR body so a human triages them.
   Cap total skips if the checklist is short — a run that skips half its items shouldn't read
   as success.

Two smaller habits that pay off: state in the checklist header whether **ordering matters**
(later items often depend on earlier ones — e.g. run a workflow linter only after the hardening
items that would fix its findings), and put shared how-to (validation command chains, style
requirements) in the header once instead of repeating it per item.

## Proxy verification for artifacts you can't run

Some deliverables cannot be exercised in the goal session's environment: CI workflow files, deploy
configs, cron definitions, IaC, anything that only runs on a remote platform. The failure mode is
silent: the session edits the YAML, nothing locally can fail, the transcript looks clean, and the
bug ships to the first real CI run — unverifiable steps default to unverified.

Counter it by naming an explicit **proxy verification chain** in `VERIFY` (or the checklist
header), best-first with fallbacks:

1. A domain linter/analyzer (`zizmor` or `actionlint` for GitHub Actions, `terraform validate`,
   a schema validator) — with an install path (`uvx`, `brew`) and what to do if install fails.
2. A syntax/schema parse as the floor (e.g. `python -c 'import yaml, sys; ...'`) — cheap and
   always available.
3. A dry-run mode where one exists (`--dry-run`, `--check`, plan-only).

Then require the **residual risk to be reported, not hidden**: what could still only fail on the
real platform goes in the final report/PR body ("workflows validated with zizmor + YAML parse;
not executed — verify on first CI run"). The evaluator can check that the proxy commands ran;
the human knows exactly what remains unproven.

## Section reference

Core (almost always): `GOAL`, `DONE WHEN`, `VERIFY`, `CONSTRAINTS` (scope + integrity), `STOP RULES`.
Optional (only if they add signal): `CONTEXT`, `BASELINE`, `PRIORITY`, `PLAN`, `OUTPUT`.
See [../assets/goal-prompt-template.md](../assets/goal-prompt-template.md) for the fill-in scaffold,
and [../assets/support-file-templates.md](../assets/support-file-templates.md) for the sibling scaffolds.

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

### D. Design-heavy feature (bundled — the design is the payload)
When this session made real design choices, the bundle exists to transfer them, not to save
characters: `goal.md` (contract) + `design.md` (interfaces as code, decisions with rationale and
rejected alternatives) + `examples.md` (verbatim repo patterns, wrong-way block) + `checklist.yaml`
(per-item acceptance) + `decisions.md` (pre-answered questions, fallbacks). Full walkthrough:
[support-file-guide.md](support-file-guide.md), "Worked example: a design-heavy bundle".

## Good vs bad conditions

| Bad | Why it fails | Better |
|---|---|---|
| "Improve the auth module" | Subjective, no end state → never stops | "All tests in test/auth pass and lint is clean" |
| "Make the app production-ready" | Not measurable | Enumerate concrete, checkable criteria |
| "All tests pass" (no evidence rule) | Evaluator trusts prose → stops early / cheating | "…and print `GOAL_DONE` after showing `npm test` exit 0" |
| "Migrate the API" (no inventory/scope) | Unbounded, unreachable | Bundle an inventory; scope to call sites; cap turns |
| Five-clause AND in one sentence | Small evaluator misjudges | One printed sentinel emitted only when all hold |
| "DONE WHEN: all checklist boxes ticked" | Checklist is self-graded → tickable without the work | Boxes ticked AND final verification commands' fresh output pasted |
| Goal ends at `git push` / `gh pr create`, no fallback | Environmental failure → thrash until the ceiling | Degraded terminal sentinel that keeps local commits and reports the blocker |
| "Follow the existing patterns" (bare pointer) | Executor must find, read, and interpret — three divergence points | `examples.md` with the verbatim snippet + source path |
| "Choose a sensible architecture for X" | Delegates design to a weaker model under anti-thrash pressure | Decide now; ship `design.md` with decisions, rationale, rejected alternatives |
