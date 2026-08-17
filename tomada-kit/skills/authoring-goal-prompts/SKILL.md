---
name: authoring-goal-prompts
description: "Author a self-contained prompt for Claude Code's /goal command, run unattended in a separate session — a lead-to-staff handoff where this (stronger) session researches, designs, and decides, and a (typically weaker) executor model implements. Drafts a goal with measurable done-criteria, transcript-verifiable checks, scope + anti-cheat constraints, and stop rules; packages design intent, code examples, research findings, checklists, and pre-answered decisions as support files in ~/.claude/goal-prompts/<slug>/ whenever the executor would otherwise re-derive them. Use PROACTIVELY when the user mentions /goal, a goal prompt, an unattended or self-driving run, deciding the done-criteria for a goal run, or setting up a long-running autonomous Claude session. Examples: <example>Context: User wants an unattended run user: 'Write the prompt I will hand to /goal' assistant: 'I will use authoring-goal-prompts skill' <commentary>goal-prompt authoring request</commentary></example>"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, Task, AskUserQuestion
argument-hint: "[task to draft a /goal prompt for]"
---

# Goal Prompt Author

Produce a ready-to-paste prompt for Claude Code's `/goal` command, which a person will run in a
**separate, unattended session**. Your output is the prompt itself plus its support files — you do
**not** run `/goal`.

This is a **lead-engineer → staff-engineer handoff**: this session (typically the stronger model)
does the investigating, designing, and deciding; the goal session (typically a weaker, cheaper
model with zero shared context) executes. Author everything with that asymmetry in mind.

**Don't use this skill for:** running or babysitting `/goal` yourself; one-turn tasks that finish
faster than setting up a goal; subjective goals with no measurable end state ("make the UX nicer").

## Four truths about `/goal` that drive every decision

1. **No human is reachable mid-run.** Every decision the goal session might otherwise ask about
   must be pre-decided and encoded as a fallback rule. You cannot rely on a follow-up question.
2. **A small evaluator model judges only the transcript** — it runs no commands and reads no files.
   "Done" must be provable by text the goal session prints (an exit code, a sentinel line, `git status`).
3. **Optimizing the transcript invites cheating.** A model graded on "looks done" may skip/`xfail`
   tests, weaken assertions, or stub implementations. Forbid this explicitly.
4. **The executor knows nothing you don't write down.** The goal session is fresh and often a
   smaller model. Your discovery findings, design decisions, and pattern knowledge exist only in
   this conversation — anything not written into the prompt or a support file is lost, and the
   executor will re-derive it, possibly differently. Never make the executor redo lead work.

**Concise wins — per file.** `goal.md` carries the contract and stays lean; support files carry the
knowledge and earn each line by preventing a wrong decision. Neither is padding.

**Hard length limit: the prompt you hand to `/goal` must be ≤ 4000 characters** — `/goal` rejects a
longer condition, so **measure the final prompt** (`wc -m`, character count, not `wc -c` bytes)
before emitting, every time. When bundled, only `goal.md` is passed to `/goal`, so **siblings don't
count** — if you're near or over the cap, move bulk into siblings until `goal.md` fits, never cram.

## Workflow

```
Phase 1: Discovery & design (autonomous)  →  Phase 2: Choose the handoff package
   →  Phase 3: Draft goal.md + support files
   →  Phase 4: Resolve residual ambiguity (ask only if needed)  →  Phase 5: Emit
```

## Phase 1: Discovery & design (autonomous — decide, don't ask)

Investigate the target project before drafting. Default target is the current working directory
unless the user names another. Gather, in order:

1. **Project rules** — read the target `CLAUDE.md` and any dev-rule/contribution docs. Scope limits
   (e.g. "don't rename/refactor unrelated code") become `CONSTRAINTS` verbatim.
2. **Baseline** — find the verify command (test/build/lint) and determine its **current** state
   (run it if cheap/safe, else infer from recent signals) so the goal is reachable — capture as
   `BASELINE`. If the goal will make commits, also capture `git status` and name any pre-existing
   dirty files in `BASELINE`, so the session doesn't misattribute or "clean up" them.
3. **Existing patterns** — locate concrete files/idioms to imitate; capture the actual snippet
   (`path:lines`) verbatim for `examples.md` — a pasted block leaves one way to comply, a pointer doesn't.
4. **Environment preflight** — for outward-facing endings (push, PR, publish, deploy), verify the
   prerequisite now (`gh auth status`, `git remote -v`, required tools) and record it in `BASELINE`.
   If it can't be guaranteed, encode a **degraded terminal state** (see the guide) instead of thrashing.
5. **Design** — when the task involves choices (architecture, interfaces, naming, approach, library),
   make them now and record decision + rationale + rejected alternative. The lead designs; the executor executes.

For a broad/uncertain scope, dispatch an `Explore` agent for items 1 and 3 in parallel.

Resolve everything you can here by investigation — only genuine, goal-defining unknowns reach Phase 4.

## Phase 2: Choose the handoff package (autonomous)

**The knowledge-transfer test decides — not size.** Bundle to `~/.claude/goal-prompts/<slug>/`
whenever the run depends on knowledge that currently exists only in this session: design decisions,
patterns worth showing as code, research findings, a work inventory, predictable ambiguities you've
pre-answered. Test each piece: *"could a fresh, smaller-model session plausibly get this wrong if it
had to re-derive it?"* — any yes means that knowledge goes into a support file.

- **Chat-only** stays right for self-contained tasks where the repo plus a short prompt carry
  everything (a scoped test-fix, a mechanical rename): print one copyable fenced block.
- The 4000-character cap remains a *mechanical* trigger: exceeding it forces a bundle even when
  the knowledge test alone didn't.

Pick siblings from the standard menu — create only those that earn their place
(full guidance: [references/support-file-guide.md](references/support-file-guide.md)):

| File | Carries | Create when |
|---|---|---|
| `design.md` | target design: interfaces/schemas as code blocks, decisions + rationale + rejected alternatives | you made any design choice the executor could plausibly make differently |
| `examples.md` | patterns to imitate as fenced code blocks — verbatim repo snippets, Before/After pairs | "follow the style of X" is not enough; show, don't point |
| `research.md` | distilled findings: current behavior, root causes, repro commands, verified-vs-inferred | you learned non-obvious facts the executor would burn turns rediscovering |
| `checklist.yaml` (`.md` for short queues) | work queue with one acceptance criterion per item, machine-checkable statuses | multi-item work — migrations, audits, content production, coding or not |
| `decisions.md` | pre-answered questions + fallback rules ("if X, do Y") | any run long enough to hit an ambiguity you can predict |

`<slug>` is a deterministic kebab-case summary of the goal (~4–6 words); re-running the same goal
overwrites the same dir (idempotent). **Overwrite guard**: if the dir already holds a run in progress
(e.g. a checklist with done/skip items), don't clobber it — pick a new slug or confirm with the user.

## Phase 3: Draft goal.md + support files

Fill the scaffold in [assets/goal-prompt-template.md](assets/goal-prompt-template.md), including
only the sections that carry signal. Write support files from the scaffolds in
[assets/support-file-templates.md](assets/support-file-templates.md), following the quality rules
in [references/support-file-guide.md](references/support-file-guide.md). Read
[references/goal-authoring-guide.md](references/goal-authoring-guide.md) while drafting for the
mechanics, failure modes, and worked examples.

Always bake in:
- A single, unambiguous **success sentinel** the evaluator can read off the transcript (e.g.
  `GOAL_DONE: <command> exited 0`) — one objective line, not a compound condition a small model may misjudge.
- **Anti-cheat constraints**: do not skip / `xfail` / disable / delete tests; do not weaken
  assertions; do not stub or mock to pass. The build/tests must pass on the real implementation.
- **Process discipline (coding goals that add/change behavior)**: encode TDD — write the test first,
  paste the failing line, then implement to green, test+implementation in the same commit — and
  commit granularity: one commit per logical unit, at least one per work item, never one giant commit.
  Omit only when the repo has no test infrastructure, and record that omission in `decisions.md`.
- **Encoded fallbacks**: "if X is ambiguous, prefer Y; if blocked, stop and report" — the goal session
  cannot ask. For endings that can fail environmentally (push, PR, publish), define a **degraded
  terminal state** with its own `GOAL_DONE:`-prefixed sentinel so the run ends cleanly either way.
- A **stop ceiling** (`or stop after N turns`) and, for long runs, commit-per-unit + a one-line
  per-iteration progress log. Size from the work: roughly 2–3 turns per item plus ~10 for setup/finish
  — too low false-negatives the stop, too high burns tokens on thrash.
- **When bundled**: `CONTEXT` lists every sibling by **absolute path** with a read-first order, and
  `CONSTRAINTS` carries the **divergence rule** — if the repo contradicts a support-file *fact*, trust
  the repo and note the divergence; if a *design* element is impossible as specified, apply the
  fallback in `decisions.md` or stop and report. Point, never duplicate, across `goal.md`/siblings.

## Phase 4: Resolve residual ambiguity (ask only if needed)

Ask **only** if a goal-defining axis cannot be settled by investigation — and only
for these: the **done-state**, the **scope boundary**, the **verify method**, the **stop ceiling**,
or a **design fork** whose options are genuinely equal after investigation (record the answer in
`decisions.md` as "user answer"). Use `AskUserQuestion` — one round, ≤4 questions, concrete options.

If discovery answered it, do not ask. No question is the expected outcome for well-specified tasks.

Timing: Phase 4 may be pulled **before** Phase 2/3 when the answer changes what you would draft —
e.g. whether optional items are in scope, or whether the run ends at local commits vs an open PR.
Asking first beats redrafting a bundle.

## Phase 5: Emit

- **Measure first.** Count the prompt's characters with `wc -m` before printing (write the draft to
  the scratchpad first if it isn't on disk). It MUST be ≤ 4000 — if over, move bulk into a bundle
  (only `goal.md` counts) and re-measure. Never emit an over-limit prompt.
- Print the concise prompt in one fenced block, ready to paste after `/goal`.
- If bundled: write the files, then print the directory path, the sibling list (one line each on
  what it carries), and a one-line note — "In a fresh session run `/goal` with the contents of
  `~/.claude/goal-prompts/<slug>/goal.md` (it references the sibling docs by absolute path)."
- Briefly state which sections you included/omitted and why, plus the baseline you found.

## Self-QA bar (run before emitting — assume a problem exists)

- [ ] `DONE WHEN` is binary and measurable; not subjective.
- [ ] A success **sentinel / objective evidence** is required in the transcript (evaluator can see it).
- [ ] `VERIFY` names the exact command(s); the goal is **reachable** from the captured `BASELINE`.
- [ ] Everything `VERIFY` requires can actually run in the goal session's environment; artifacts
      that can't be exercised locally (CI workflows, deploys) have an explicit **proxy verification**
      chain with fallbacks, not silence.
- [ ] Scope **and anti-cheat** constraints are present (no skip/stub/weaken).
- [ ] A **stop ceiling** and **fallback decisions** are encoded (no human mid-run).
- [ ] **Staff-engineer test**: a fresh, weaker-model session reading only `goal.md` + siblings could
      reproduce your intended design — no decision, finding, or pattern lives only in this
      conversation. Every design choice you made is written down with its rationale.
- [ ] Support files **show, not tell**: patterns are fenced code blocks (verbatim from the repo
      where possible), findings carry evidence (`file:line`, pasted output), every checklist item
      has its own acceptance criterion.
- [ ] `goal.md` names every sibling by absolute path with a read-first instruction; no content is
      duplicated between `goal.md` and siblings; the divergence rule is in `CONSTRAINTS`.
- [ ] If the goal commits: pre-existing working-tree state is named in `BASELINE`, and commit rules
      (branch, message conventions, never `--no-verify`) are in `CONSTRAINTS`.
- [ ] For coding goals that add/change behavior: **TDD** (test-first, failing output pasted before
      implementing) and **logical-unit commit granularity** are encoded — or their omission is
      deliberate and recorded in `decisions.md`.
- [ ] If bundled with a checklist: ticking is anchored to pasted command output, skip semantics are
      defined (`skip_rule`), and `DONE WHEN` also requires a final whole-run verification
      (`verify_all`) — statuses alone are self-graded and cheatable.
- [ ] No bloat: every section earns its place; bulk is externalized, not inlined.
- [ ] The prompt is **≤ 4000 characters**, measured with `wc -m` (not estimated). When bundled, `goal.md` alone is under the cap.

## Supporting files

- [assets/goal-prompt-template.md](assets/goal-prompt-template.md) — the adaptive section scaffold for `goal.md` (clone and fill).
- [assets/support-file-templates.md](assets/support-file-templates.md) — scaffolds for `design.md`, `examples.md`, `research.md`, `checklist.yaml`, `decisions.md` (clone and fill).
- [references/goal-authoring-guide.md](references/goal-authoring-guide.md) — evaluator mechanics, failure modes, externalization rule, worked examples (consult while drafting).
- [references/support-file-guide.md](references/support-file-guide.md) — when to create each support file and the quality rules that make the lead→staff handoff lossless (consult when bundling).

All supporting files are referenced by skill-relative paths, so they resolve identically on Claude Code and (via the `~/.codex/skills/` symlink) on Codex.

> Codex で実行する場合の制約と代替手順は `references/codex-notes.md` を参照。
