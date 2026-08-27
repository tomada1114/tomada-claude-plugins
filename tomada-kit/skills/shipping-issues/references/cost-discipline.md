# Cost discipline

What this skill keeps out of the main context, why the run count is what it
is, and why each spawn gets the model it gets. Read it when deciding whether
to delegate a step, before changing a run count, or before picking a
`/code-review` effort.

## Table of Contents

- [Code review effort](#code-review-effort)
- [Run budget](#run-budget)
- [Model and effort assignment](#model-and-effort-assignment)

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

| effort | pipeline | when |
|---|---|---|
| `low` | one pass, no verify sub-pass, ≤4 findings, skips test/fixture hunks | a few files, no new public surface or data path — docs, config, copy, a small bug fix with its own test |
| `medium` | 8 finder angles × 6 candidates, 1-vote verify, ≤8 findings (precision-biased) | the default — anything not covered by the other two rows |
| `high` | same 8 angles, 1-vote verify biased toward recall, ≤10 findings | the change can lose or corrode data that already exists — a migration, a storage-layer write, a released public contract real consumers are on — or the user asked for one |

Diff size or file count alone is not a reason for `high` — `medium` already
reads for scope and correctness across the whole diff. Never `ultra`: it runs
in the cloud, is billed per use, and the prompt that defines it says
explicitly that a model cannot launch it itself.

## Run budget

Run count scales with issue count, not with thoroughness: one triage spawn
(optional), one implementation sub-agent per issue plus up to 2 resume/patch
runs when this session's judgment finds the first incomplete, one
`/code-review` per branch, one repair sub-agent per failing CI attempt (capped
at 3). This session's own
judgment calls — reading the implementation diff, reading `--fix`'s diff,
deciding what CI failure means — cost targeted reads in this context, never a
spawn. Filing a follow-up (step 8) never adds a run either: whatever found it
already returned the lead under `FOLLOW-UPS`, and confirming it costs a
couple of targeted reads.

## Model and effort assignment

Implementation and priority research run on `sonnet` — fully specified work
with a clear pass/fail. CI repair starts on `sonnet` and escalates to `opus`
once the same failure survives two attempts in a row — persistent failure is
a sign the spec (or the fix) needs more judgment, not more mechanical retries.
The `/code-review` fallback runs on `opus`, since review and bug-finding is
Opus-class work with genuinely unresolved spec.

The Agent tool used for these spawns takes a `model` but not a per-spawn
`effort` — a sub-agent's reasoning effort follows this session's own
configuration, there is no separate dial to set here.

Implementation stays delegated even when the main model is Opus — a
deliberate exception to the Opus-main "do it yourself" default, bought for
context isolation: the diff and the repo exploration are never needed in the
main context again once this session has judged the result.
