# Cost discipline

What this skill keeps out of the main context, why the run count is what it
is, and why each spawn gets the model it gets. Read it when deciding whether
to delegate a step, before changing a run count, or before picking a
`/code-review` effort.

## Table of Contents

- [Code review effort](#code-review-effort)
- [Run budget](#run-budget)
- [Model and effort assignment](#model-and-effort-assignment)
- [What parallel mode costs](#what-parallel-mode-costs)

The main context holds the selection and the verdicts, nothing else. Issue
bodies go to the triage agent, diffs stay in the sub-agent run that produced
them, CI logs and verify output reach the parent through a file rather than
through the prompt. If you find yourself about to read a full GitHub API JSON
blob, a workflow log, or an unrelated part of a diff in the main context,
that is the signal to delegate or scope the read instead.

Labeling is the cheap half of this by design: the backfill is a pure script
pass with a one-line summary, and re-deriving priority from issue prose
happens once per issue — ever — because the answer is written back to GitHub.
On a labeled backlog the whole ranking step is `--select`, three lines, no
spawn at all. Never re-read bodies to reconstruct a priority a label already
carries; if a label looks wrong, fix the label.

## Code review effort

`/code-review <effort> <branch> --fix` forks and runs entirely outside this
session's context — the finders' reads never reach here, only the findings
do. Effort controls how much of that runs:

**`low` is this repository's default effort.** The user set it as the standing
choice for every review this skill runs; use it unless the row below genuinely
calls for more, and do not silently drift back to `medium` because a diff looks
large.

| effort | pipeline | when |
|---|---|---|
| `low` | one pass, no verify sub-pass, ≤4 findings, skips test/fixture hunks | **the default** — use it unless a row below applies |
| `medium` | 8 finder angles × 6 candidates, 1-vote verify, ≤8 findings (precision-biased) | reach for it only deliberately: a change whose blast radius is hard to see from the diff alone, or one the run has already had to repair once |
| `high` | same 8 angles, 1-vote verify biased toward recall, ≤10 findings | the change can lose or corrode data that already exists — a migration, a storage-layer write, a released public contract real consumers are on — or the user asked for one |

Diff size or file count alone is not a reason to escalate — `low` already reads
the whole diff for scope and correctness, and a big mechanical rename is
exactly the shape it handles well. Never `ultra`: it runs in the cloud, is
billed per use, and the prompt that defines it says explicitly that a model
cannot launch it itself.

## Run budget

Run count scales with issue count, not with thoroughness: one triage spawn
(optional), one implementation sub-agent per issue plus up to 2 resume/patch
runs when this session's judgment finds the first incomplete, one
`/code-review` per branch, in parallel mode one fix sub-agent per branch that
had accepted findings (none when a review came back clean), one repair
sub-agent per failing CI attempt (capped at 3). This session's own
judgment calls — reading the implementation diff, reading `--fix`'s diff,
deciding what CI failure means — cost targeted reads in this context, never a
spawn. Filing a follow-up (step 8) never adds a run either: whatever found it
already returned the lead under `FOLLOW-UPS`, and confirming it costs a
couple of targeted reads.

Two things scale that count beyond the issue list itself, both deliberately
bounded:

- **Background design agents (step 8b)** — one `opus` run per design-blocked
  issue, capped at 3 in flight. They cost nothing in wall-clock on the shipping
  path (nothing ever waits on one) and almost nothing in this context: what
  comes back is a verdict and a two-line approach, while the design itself goes
  to the issue. What they buy is a backlog that stops accumulating undecided
  work — the single most expensive thing a backlog can hold, because every
  future ranking pass re-reads it and skips it again.
- **Shipping the run's own follow-ups (step 8c)** — a full steps 3–8 cycle per
  follow-up, the same cost as any issue. This is why depth is capped at 1: a
  run that shipped what it filed, and then what *that* filed, has no
  termination condition and no budget the user agreed to. Depth 1, then stop
  and report.

## Model and effort assignment

Implementation and priority research run on `sonnet` — fully specified work
with a clear pass/fail. CI repair starts on `sonnet` and escalates to `opus`
once the same failure survives two attempts in a row — persistent failure is
a sign the spec (or the fix) needs more judgment, not more mechanical retries.
The `/code-review` fallback runs on `opus`, since review and bug-finding is
Opus-class work with genuinely unresolved spec. Design decisions (step 8b) run
on `opus` for the same reason and more so — deciding an approach nobody has
decided is the least mechanical work this skill delegates, and a bad decision
recorded on an issue outlives the run that made it. It is also the only
sub-agent here that writes to GitHub (one comment, one label) and the only one
that writes no code at all.

The Agent tool used for these spawns takes a `model` but not a per-spawn
`effort` — a sub-agent's reasoning effort follows this session's own
configuration, there is no separate dial to set here.

Implementation stays delegated even when the main model is Opus — a
deliberate exception to the Opus-main "do it yourself" default, bought for
context isolation: the diff and the repo exploration are never needed in the
main context again once this session has judged the result.

## What parallel mode costs

Parallel mode does not reduce the number of runs — the same issues need the
same implementations. What it changes is when they happen, and what has to be
set up first.

**Added, per issue in a parallel batch:** one dependency install and one
baseline verify (`worktree_setup.sh`), both outside this context — the parent
reads one `verdict:` line each. Plus, per branch with accepted review
findings, one `sonnet` fix run that serial mode gets for free from
`/code-review --fix`.

**Saved:** the implementations overlap instead of queueing, which is the
longest stretch of a run, and nothing in this context grows to pay for it —
each sub-agent's exploration and diff still stay inside its own run.

The break-even is group size. One issue in a group means paying the setup for
no overlap at all, which is why step 2c refuses to parallelize a group smaller
than 2. The cap at 3 comes from somewhere else entirely — rebase churn as the
default branch moves under the batch — not from cost.

A repo that fails the viability gate costs one worktree's setup to discover,
once per run. The answer is a property of the repository, not of any issue:
never re-test it per issue.
