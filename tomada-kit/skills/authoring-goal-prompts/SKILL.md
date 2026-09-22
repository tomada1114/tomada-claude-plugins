---
name: authoring-goal-prompts
description: >-
  Author a self-contained prompt for Claude Code's /goal command, run unattended in a
  separate session — a lead-to-staff handoff where this session researches, designs, and
  decides with full context, and a fresh executor session (typically Opus 5.5 at a lower
  effort, with none of that context) implements. Drafts a
  goal with measurable done-criteria, transcript-verifiable checks, scope + anti-cheat
  constraints, and stop rules; packages design intent, code examples, research findings,
  checklists, and pre-answered decisions as support files in a per-goal state directory
  whenever the executor would otherwise re-derive them. Use when setting up a /goal run
  or a long-running autonomous session, or when deciding its done-criteria.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, Agent, AskUserQuestion
argument-hint: "[task to draft a /goal prompt for]"
metadata:
  platforms: claude-code, codex
---

# Goal Prompt Author

Produce a ready-to-paste prompt for Claude Code's `/goal` command, which a person will run in a
**separate, unattended session**. Your output is the prompt itself plus its support files — you do
**not** run `/goal`.

**Don't use this skill for:** running or babysitting `/goal` yourself; one-turn tasks that finish
faster than setting up a goal; subjective goals with no measurable end state ("make the UX nicer").

## Five truths about `/goal` that drive every decision

1. **No human is reachable mid-run.** Every decision the goal session might otherwise ask about
   must be pre-decided and encoded as a fallback rule.
2. **A small evaluator model judges only the transcript** — it runs no commands and reads no files.
   "Done" must be provable by text the goal session prints (an exit code, a sentinel line, `git status`).
3. **Optimizing the transcript invites cheating.** A model graded on "looks done" may skip/`xfail`
   tests, weaken assertions, or stub implementations. Forbid this explicitly.
4. **The executor knows nothing you don't write down.** This is a lead-engineer → staff-engineer
   handoff: this session investigates, designs, and decides; the goal session — fresh, with zero
   shared context, typically Opus 5.5 at a lower effort than this one — executes. It is capable,
   but it spends its effort on execution under a turn ceiling; whatever it has to re-derive costs
   turns and may come out differently. Never make the executor redo lead work.
5. **Opus 5.5 ends some long-run turns early** with a text-only progress report. Under `/goal` each
   one costs an evaluator round and a turn from the ceiling. The goal names the unwanted stops and
   the wanted ones (template: `TURN ENDINGS`).

## Workflow

```
Phase 1: Discovery & design (autonomous)  →  Phase 2: Choose the handoff package
   →  Phase 3: Draft goal.md + support files
   →  Phase 4: Resolve residual ambiguity (ask only if needed)  →  Phase 5: Emit
```

## Phase 1: Discovery & design (autonomous — decide, don't ask)

Investigate the target project before drafting. Default target is the current working directory
unless the user names another. Gather, in order:

1. **Project rules** — read the target `AGENTS.md`/`CLAUDE.md` and any dev-rule/contribution docs.
   Scope limits (e.g. "don't rename/refactor unrelated code") become `CONSTRAINTS` verbatim.
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

For a broad/uncertain scope, run items 1 and 3 in parallel as `executor` sub-agents (tier choice:
the `orchestrating-models` skill); where that isn't available, read them sequentially in
the main context — same result, more time (see [references/platform-notes.md](references/platform-notes.md)).

Resolve everything you can here by investigation — only genuine, goal-defining unknowns reach Phase 4.

## Phase 2: Choose the handoff package (autonomous)

**The knowledge-transfer test decides — not size.** Bundle to
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/goal-prompts/<slug>/`
whenever the run depends on knowledge that currently exists only in this session: design decisions,
patterns worth showing as code, research findings, a work inventory, predictable ambiguities you've
pre-answered. Test each piece: *"could a fresh session without this conversation plausibly get this
wrong, or burn turns rediscovering it?"* — any yes means that knowledge goes into a support file.

**Chat-only** stays right for self-contained tasks where the repo plus a short prompt carry
everything (a scoped test-fix, a mechanical rename): print one copyable fenced block.

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

Write `goal.md` and the siblings yourself. Hand the write-out to an `executor` sub-agent only when
every decision (design, observations, pre-answered questions) is already settled and the files are
long enough that the brief is shorter than the write-out; take back only a summary. When to delegate
and to which tier: the `orchestrating-models` skill.

Always bake in — the template carries the wording:
- **Success sentinel**, readable off the transcript by the evaluator.
- **Anti-cheat constraints**.
- **TDD + commit granularity** for coding goals that add or change behavior; omit only when the repo
  has no test infrastructure, and record that omission in `decisions.md`.
- **Encoded fallbacks**, plus a **degraded terminal state** for endings that can fail environmentally.
- **Turn-ending rule** naming the early stops to avoid and the stops that are wanted.
- **Stop ceiling**: roughly 2–3 turns per work item plus ~10 for setup/finish.
- **When bundled**: `CONTEXT` lists every sibling by absolute path; `CONSTRAINTS` carries the
  divergence rule.

## Phase 4: Resolve residual ambiguity (ask only if needed)

Ask only if a goal-defining axis cannot be settled by investigation, and only for these: the
done-state, the scope boundary, the verify method, the stop ceiling, or a design fork whose options
are genuinely equal after investigation (record the answer in `decisions.md` as "user answer").
If discovery answered it, do not ask — no question is the expected outcome for well-specified tasks.

Timing: Phase 4 may be pulled before Phase 2/3 when the answer changes what you would draft — e.g.
whether optional items are in scope, or whether the run ends at local commits vs an open PR.

## Phase 5: Emit

- **Measure first.** `/goal` rejects a condition over 4000 characters, so count with `wc -m` before
  printing (write the draft to the scratchpad first if it isn't on disk). If over, move bulk into a
  bundle (only `goal.md` counts) and re-measure.
- Print the concise prompt in one fenced block, ready to paste after `/goal`.
- If bundled: write the files, then print the directory path, the sibling list (one line each on
  what it carries), and a one-line note — "In a fresh session run `/goal` with the contents of
  `${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/goal-prompts/<slug>/goal.md` (it
  references the sibling docs by absolute path)."
- Briefly state which sections you included/omitted and why, plus the baseline you found.

## Emit bar

- The goal is reachable from the captured `BASELINE`.
- Everything `VERIFY` requires can run in the goal session's environment; artifacts that can't be
  exercised locally (CI workflows, deploys) have an explicit proxy verification chain.
- Staff-engineer test: a fresh session reading only `goal.md` + siblings would reproduce your
  intended design — no decision, finding, or pattern lives only in this conversation.

## Platform notes
詳細は [references/platform-notes.md](references/platform-notes.md) を参照。
