---
name: shipping-issues
description: "Rank open GitHub Issues by their `priority: P0`-`P3` labels — backfilling a missing label from how much an issue unblocks and how far its impact spreads — then implement the top one, open a PR that auto-closes the issue (Closes #N), watch CI to green, work its CI review through severity-ordered fix rounds, merge with no approval pause, confirm the issue closed, and return the checkout to the default branch. With no argument it ships the highest-priority issue and then what that run itself produced — the follow-ups it filed, the designs it unblocked. Pass \"all\" to work through every issue in dependency order, independent ones implemented in parallel git worktrees, with PR, CI and merge still serialized; pass \"light\" to do the same for only the issues labeled `model: light` (design settled, small, low-judgment). Design-blocked issues get a background sub-agent that decides the approach and clears the block. Use when asked to ship the remaining issues, start from the highest-priority issue, implement an issue through to merge, take on the next issue, clear the ticket backlog, or work through the open issues."
argument-hint: "[all | light | <issue number> | (empty = one issue)] [parallel N]"
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*.py:*), Bash(${CLAUDE_SKILL_DIR}/scripts/*.sh:*)
metadata:
  platforms: claude-code
---

# Shipping Issues

**Done means all three:** the PR is merged to the default branch, the issue is
CLOSED, and nothing was deleted or weakened to get there.

**Invoking this skill is the authorization for every write it makes, up to and
including the merge** — labels, branches, pushes, the PR, review-response
comments, follow-up issues, step 8b's design comments, cleanup. Green CI with a
cleared review is the go-ahead: once [step 6b](#6b-review-rounds) clears, the
merge happens in the same turn, with no "shall I merge?" and no
summary-then-wait. Re-confirming per issue defeats `all` mode entirely. The only
pauses are the [Stop conditions](#stop-conditions) and two narrow asks named
inline: a genuinely tied top two at step 2, and `NO_CHECKS` at step 6.

## Table of Contents

- [Modes](#modes) · [Deferring light issues](#deferring-light-issues) · [Working rules](#working-rules) · [Inputs and outputs](#inputs-and-outputs)
- [1. Plan](#1-plan--one-call) · [2. Label](#2-label-the-unlabeled--only-when-the-plan-says-so) · [2b. Gating design](#2b-decide-a-design-that-gates-the-pick) · [2c. Confirm the batch](#2c-confirm-the-proposed-batch)
- [3. Implement](#3-implement) · [4. Local review](#4-local-review--only-where-ci-does-not-review) · [5. Open the PR](#5-open-the-pr) · [6. CI to green](#6-ci-to-green) · [6b. Review rounds](#6b-review-rounds) · [7. Merge](#7-merge-and-confirm-the-issue-closed)
- [8. Close out findings](#8-close-out-the-findings-the-run-turned-up) · [8b. Unblock designs](#8b-unblock-held-designs-in-the-background) · [8c. Re-queue this run's output](#8c-take-the-runs-own-output-back-into-the-queue) · [9. Clean up](#9-clean-up) · [10. Report](#10-report)
- [Stop conditions](#stop-conditions) · [Further reading](#further-reading)

## Modes

| Argument | Behavior |
|---|---|
| _(none)_ | Ship the highest-priority shippable issue — [deferred `model: light` issues](#deferring-light-issues) aside — then continue through **its own output only** — the follow-ups it filed, the designs it unblocked ([step 8c](#8c-take-the-runs-own-output-back-into-the-queue)). Never reaches back into the wider backlog. |
| `all` | Ship every shippable issue except the [deferred `model: light` ones](#deferring-light-issues), in dependency-then-priority order. Independent issues are implemented and reviewed in parallel, one git worktree each; PR, CI watch and merge stay serialized. Follow-ups this run files join the same queue. |
| `light` | `all`, narrowed to open issues labeled `model: light` ([what the label means](references/dependency-triage.md#the-model-light-label)). A follow-up this run files joins the queue only if it carries the label too. The label chooses *which* issues, not *how*: implementation keeps the [model assignment](references/cost-discipline.md#model-and-effort-assignment) it would get anyway. |
| a number, e.g. `42` | Ship that specific issue, after checking nothing it depends on is still open. |

A count or concurrency in the argument — "10個ぐらい", "3 at a time", "parallel
5" — is the user setting `--max-parallel`. Pass it to `plan.py`; the default is 3
and the *only* reason to raise it is that the user asked. Anything else is a
filter hint (a label, a milestone) — pass it as `plan.py` flags.

An issue labeled `blocked: design`, or carrying `design=open` in its
[ship contract](references/ship-contract.md), is never *implemented*
automatically, even under `all` — take it on only by naming its number or passing
`--include-design` ([step 2b](#2b-decide-a-design-that-gates-the-pick)). The
label itself is not left alone:
[step 8b](#8b-unblock-held-designs-in-the-background) sends a background agent
after every design-blocked issue this run files or finds.

### Deferring light issues

Under `all` and with no argument, an issue labeled `model: light` is **left for
a lighter runner** (the Codex-side skill) rather than shipped here — its thinking
is done, so spending this runner on it buys nothing a cheaper one would not.
The exception is an issue something heavier is waiting on: when an issue that
is *not* deferred depends on it, directly or through a chain of light issues,
it ships in this run like any other, because leaving it would stall the work
behind it. `plan.py` makes the call and prints what it left on
`deferred-light:`; step 10 names them. `--include-light` takes them anyway, and
`light` mode and an explicit issue number are unaffected. A follow-up this run
files with the label is deferred by the same rule at
[step 8c](#8c-take-the-runs-own-output-back-into-the-queue).

## Working rules

- **One checkout, one writer.** Step 1 decides the arrangement once and it holds
  for the whole batch: **serial** puts everything in the main checkout, one issue
  start to finish; **parallel** gives each issue its own worktree under
  `<runstate>/worktrees/<n>` and leaves the main checkout clean on the default
  branch. Never re-decide mid-batch.
- **Concurrency stops at the GitHub API.** Steps 3 and 4 run concurrently across
  a batch; everything that talks to GitHub stays in this session, serialized, one
  PR at a time, in both modes. Parallel worktrees buy back the implementation
  wait — making merges concurrent is not a goal.
- Every issue starts from a clean, up-to-date default branch, and the run returns
  there after every merge (`git switch <default> && git pull --ff-only`).
- **A run finishes what it started**, to depth 1
  ([step 8c](#8c-take-the-runs-own-output-back-into-the-queue)): a follow-up of a
  follow-up waits, and single mode never re-scans the wider backlog.
- A dirty working tree this run did not create is never touched silently — see
  [Stop conditions](#stop-conditions).

## Inputs and outputs

Reads the repo's open issues and PRs, plus the project's own `CLAUDE.md` /
`AGENTS.md`. Writes `priority: P0`…`P3` labels, `blocked: design` labels (set
*and* cleared), design-decision comments, branches, PRs, merge commits, issue
closures, follow-up issues, and a run record.

Everything generated lives under `<runstate>` —
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/shipping-issues/<owner>__<repo>/`
— and **never inside the repo checkout**, worktrees included: anything nested in
the repo becomes an untracked path in `git status`, which this skill treats as a
hard stop. Layout: [run-record.md](references/run-record.md). Record each event
as it happens, not batched at the end:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/run_record.py --repo <owner>/<repo> \
    --event <kind> [--field k=v ...] [--body-file <path>]
```

**Requires:** `git`, `python3`, `gh`.

## Workflow

### 1. Plan — one call

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/plan.py --mode <all|light|single|N> \
    [--max-parallel N] [--label L] [--assignee A] [--milestone M] \
    [--include-design] --record
```

Preflight, ranking, selection, the repo profile and the parallel grouping in one
block from a single `gh` fetch. Read the block; do not re-derive any of it.
Field-by-field legend, caching rules, and the one-call way to pull issue bodies:
[plan-output.md](references/plan-output.md). Three fields carry a duty here:

- `preflight: BLOCKED` stops the run. `tree: DIRTY` is a question to ask **now**,
  before any baseline. `existing-worktrees: BLOCKED` is a
  [stop condition](#stop-conditions), not a leftover to reuse.
- `verify-check:` is a **guess** from script names, and step 3 executes it.
  **Confirm it before using it**: is it the gate this repo actually runs before a
  PR, and does it terminate? A repo whose `test` is the unit tests while `lint`
  and `typecheck` are separate gates gives a green baseline against a CI that
  will fail; a watcher never returns at all.
- `needs-design:` is the input to
  [step 8b](#8b-unblock-held-designs-in-the-background). Spawn that round **here,
  before step 3** — it costs this session nothing to wait on, and starting now is
  what gets those issues unblocked while the run is still going.
- `stale-labels:` names issues still labeled `blocked: dependency` although
  every dependency is closed. Readiness already ignores that label, but a human
  reading the backlog does not — run the `--clear-dependency` command the line
  prints, without asking. The same line after a merge (the re-plan at step 8c)
  is how the issues that merge just unblocked get cleared.

`labels: COMPLETE` → **skip step 2**. `github: write=no` → label and follow-up
writes exit 2, so rank from `~Pn` suggestions and report findings instead.

### 2. Label the unlabeled — only when the plan says so

- **≤3 without a settled tier** — read them
  (`issue_digest.py --detail N --detail M`) against
  [priority-rubric.md](references/priority-rubric.md), then:
  ```bash
  python3 ${CLAUDE_SKILL_DIR}/scripts/apply_priority_labels.py \
      --backfill --set N=P0 --quiet
  ```
- **more, tangled edges, or a close top-two** — hand
  [agents/priority-research.md](references/agents/priority-research.md) to an
  independent `sonnet` sub-agent, filled per
  [delegation-templates.md](references/delegation-templates.md). Returns the pick
  with evidence, the order after it, and blocked/unclear lists — never raw issue
  prose.

`--backfill` writes suggested tiers to every unlabeled issue; `--set` overrides
ones judged differently. Run without asking. Readiness gate:
[dependency-triage.md](references/dependency-triage.md). Then re-plan
(`plan.py --refresh --record`) and **proceed without asking**, unless the top two
are genuinely tied on every axis or the pick needs a product decision first.

### 2b. Decide a design that gates the pick

Only when the picked issue is design-blocked and was taken on deliberately —
never from the default backlog scan. Settle the approach, record it, and clear
the block before step 3, per
[dependency-triage.md#deciding-a-held-design](references/dependency-triage.md#deciding-a-held-design).
Every *other* design-blocked issue goes the other way round, off the critical
path: [step 8b](#8b-unblock-held-designs-in-the-background).

### 2c. Confirm the proposed batch

**Every parallel batch passes through here** — the plan proposes, this step
decides. A script can tell you two issues declare no overlapping paths and no
dependency edge; it cannot tell you both will end up editing the same config
file, that one is a refactor whose blast radius is wider than its `touches=`
admits, or that a repo's generated files make any two concurrent branches
conflict. That is what to check, against
[dependency-triage.md#parallel-vs-sequential-all-mode](references/dependency-triage.md#parallel-vs-sequential-all-mode)
— thoroughness scaling with the grouping verdict: `MECHANICAL` means read each
issue's real reach against its declared `touches=`; `PARTIAL` means read the
undeclared issues properly before keeping them.

When step 2's research agent ran, it returned its own parallel-safe groups from
paths it actually grepped. That is a second opinion, not a tie-break: where it
and `plan.py` disagree, take the narrower grouping.

Shrinking the batch is always allowed and never needs asking: two issues in
parallel is already most of the win, and a wrong pairing costs a merge conflict
mid-batch. Note any issue whose `touches=` had to be judged — a step 10 line.

### 3. Implement

One issue = one branch = one PR. Step 1's `next:` line is the command.

**Serial** — `git switch <default_branch> && git pull --ff-only && git switch -c
<branch>`, then run the confirmed verification command **once, unmodified, on
this branch**, redirected to `<runstate>/verify/<n>-baseline.log`.

**Parallel** — the script creates each branch, copies untracked local config,
installs dependencies, and runs the baseline (bounded). It **reports and does not
decide**:

```bash
git switch <default_branch> && git pull --ff-only   # once, before the batch
${CLAUDE_SKILL_DIR}/scripts/worktree_setup.sh --spec <n>:<branch> \
    --spec <m>:<branch> --base <default_branch> --root <runstate>/worktrees \
    --log-dir <runstate>/verify --verify "<confirmed verify command>"
```

**Provision the first worktree on its own, read its block, then ask for the
rest** — that one extra call is what stops a repo that cannot carry a worktree
from costing three dependency installs instead of one. Judging the four
`baseline:` outcomes is yours, not the script's
([all four](references/recovery.md#a-red-baseline); `verdict:` semantics
[here](references/worktree-parallelism.md#viability-gate)). Read exit codes and
log tails, never full output; what the smoke run turns up goes to step 8.

Fill and spawn a sub-agent per issue with
[agents/implementation.md](references/agents/implementation.md). **`sonnet` by
default; `opus` when the issue is foundational** — blast radius, not difficulty
([the foundation exception](references/cost-discipline.md#the-foundation-exception-opus-for-what-the-backlog-builds-on));
a change small enough that the handoff costs more than the work is implemented
here rather than spawned
([the floor](references/cost-discipline.md#the-floor-too-small-to-delegate)). In
parallel mode issue every sub-agent in the batch **in one message**, each with
its own worktree path, never the main checkout.

Then **judge each result in this context**, against the issue and step 2b's
decision. What each returned field is for:

| Returned field | Consumed |
|---|---|
| `ACCEPTANCE` | **Here, first.** A `not-met` line is work still owed. Sending it back costs one resume run; letting it through merges a PR that closed an issue it did not answer. Green CI does not cover this — it proves the repository still works, not that the issue was answered. |
| `UNRESOLVED` | **Here.** Judgment calls the agent made alone: each is accepted (and stated at step 10) or sent back, never silently inherited. |
| `PR-SUMMARY` / `TEST-PLAN` | [Step 5](#5-open-the-pr), verbatim. |
| `MEASURE` | [Step 6b](#6b-review-rounds), or step 4 — what review findings are checked against. |
| `SCOPE-NOTES` / `FOLLOW-UPS` | [Step 8](#8-close-out-the-findings-the-run-turned-up). |

At most **2 resume runs** on top of the first, same model; a third miss is
`NEEDS-CLARIFICATION`, not another spawn. A run that returned without a report,
stopped before pushing, or missed or widened the spec:
[recovery.md](references/recovery.md) — never re-spawn an agent that returned
without its report.

### 4. Local review — only where CI does not review

**Skip this step when the repository reviews in CI** — a workflow on the
default branch carries the [CI review contract](references/ci-review.md)'s
marker (`grep -l 'claude-review v1' .github/workflows/*`). That review runs on
every push of the PR and [step 6b](#6b-review-rounds) works it; a local pass
first would pay for the same review twice. What follows is for a repository
without one, and for a PR step 6b finds `NOT_REVIEWED`.

Run against the branch, before any PR exists. In parallel mode step 4 covers the
whole batch: review each branch, triage all of them, then fix them concurrently —
no PR opens until the batch's last review is triaged. This local pass is one
round: triage it as step 6b's round 1 — fix every accepted finding, defer the
rest the way step 6b does — and do not re-review after the fix.

```
/code-review <effort> <branch> [--fix]
```

**Effort first, branch second** — an unrecognized first token makes the *entire*
string the target and silently falls back to the last effort used. **`low` is the
standing default**; never `ultra`. One escalation is not optional: `low` skips
test and fixture hunks, so a diff living entirely under `tests/` that *is* a gate
comes back `(none)` having read nothing — a false clean, not a pass. Check what
the review actually read before believing an empty findings list. When to
escalate:
[cost-discipline.md#code-review-effort](references/cost-discipline.md#code-review-effort).

**`--fix` is serial-mode only** — in parallel mode it would write one branch's
repairs into the main checkout. Parallel mode reviews without `--fix` and spawns
one `sonnet` fix run per branch from
[agents/review-fix.md](references/agents/review-fix.md), all in one message; a
branch with zero accepted findings gets no spawn
([why](references/recovery.md#--fix-and-why-it-is-serial-mode-only)). Host won't
launch `/code-review` at all →
[agents/review-fallback.md](references/agents/review-fallback.md).

**Number the findings `F1`, `F2`, … before handing them over** — the fix agent
returns `APPLIED`/`REJECTED` against those same numbers, and without
caller-assigned IDs the returned lines cannot be matched back to what was sent.

Triage is the same either way, and in parallel mode you triage *before* anything
is written: read every finding against the issue's scope, send what belongs in
this diff, route the rest to step 8. "Belongs in this diff" is the same behavior
change the issue is about, tests included — a sibling case of the bug just fixed
belongs here; a schema change or a new public surface does not, however small the
patch looks ([filing-followups.md](references/filing-followups.md)).

Either path writes code this session did not write, so **reading what the fix
pass changed is the safeguard**: `git -C <workdir> diff <impl-commit>..HEAD`,
not the whole branch. Revert what it got wrong. Read the findings it would *not*
apply (`skipped` from `--fix`, `REJECTED` from the sub-agent) — neither is clean;
real-but-out-of-scope goes to step 8. Re-run the verification command **in
`<workdir>`** only if something actually changed, then push.

Record, per branch: `--event review --field issue=<n> --field
status=<code-review|code-review+agent-fix|DELEGATED> --field
effort=<low|medium|high> --field findings=<n> --field skipped=<n>` — `skipped`
counts refusals from either path.

### 5. Open the PR

From here to step 7 the run is serial in both modes: one PR at a time, in the
batch's dependency-then-priority order. Finish an issue's PR → CI → merge before
opening the next.

Commits but nothing pushed → push from this session (`git -C <workdir> push -u
origin <branch>`). No commits at all → no branch: record `--event blocked --field
issue=<n>`, report `SKIPPED(<why>)`, and in `all` mode move on.

Open a PR from `<branch>` against `<default_branch>`, titled `<PR-TITLE>`. The
body must start with **`Closes #N`** after the summary (a bare `#N` closes
nothing) and target the **default branch** (auto-close only fires there) — build
it from `PR-SUMMARY`, `Closes #N`, `TEST-PLAN`. Record (`--event pr-created
--field issue=<n> --field pr=<url>`), then:

```bash
${CLAUDE_SKILL_DIR}/scripts/link_check.sh <pr> --issue <n> --fix
```

`land_pr.sh` re-checks the link at step 7 too; this earlier call is not redundant
because it catches `WRONG_BASE` before CI spends thirty minutes on the wrong
base. `--fix` appends a missing `Closes #N`; `WRONG_BASE` → retarget before
merging.

### 6. CI to green

Wait for the PR's new head commit to appear among the branch's CI runs before
watching — the checks API serves the previous commit's results for a minute or
two after a push, and a stale PASS is worse than a stale FAIL. Then:

```bash
${CLAUDE_SKILL_DIR}/scripts/ci_watch.sh <pr> --timeout 1800 > <runstate>/ci/<pr>.log
grep -E '^(verdict|mergeable|merge_state|review_decision):' <runstate>/ci/<pr>.log
```

Redirected — raw output carries failing-run log tails that must stay out of this
context. One watch per PR; keep `failed_checks:` for repair. This is the run's
only wait primitive: never a hand-rolled sleep/poll loop. Block on it directly,
one PR at a time, even in `all` mode. Record (`--event ci ...`).

`FAIL` → [recovery.md#ci-fails](references/recovery.md#ci-fails) and
[agents/ci-repair.md](references/agents/ci-repair.md), at most 3 attempts.
`NO_CHECKS` or `ERROR` →
[recovery.md#no_checks-error-and-other-non-verdicts](references/recovery.md#no_checks-error-and-other-non-verdicts).
`PASS` → [step 6b](#6b-review-rounds) before any merge when the repository
reviews in CI: the review check succeeds whether or not it found anything. A
`FAIL` confined to the review check itself — its token expired, the action
errored — is not a code failure: do not send it to ci-repair; step 6b reads it
as `NOT_REVIEWED`.

### 6b. Review rounds

Only when the repository reviews in CI (step 4 was skipped). Every push to the
PR re-runs that review, so each pass through step 6 is one round.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/review_digest.py <pr> \
    > <runstate>/review/<pr>-<round>.log
```

Exit 3, `NOT_REVIEWED`: no review for this head — a fork or Dependabot PR, a PR
that edits the review workflow itself, a review job that errored. Run
[step 4](#4-local-review--only-where-ci-does-not-review) against the branch now
and finish this PR on that path. Exit 2 → treat as `verdict: ERROR`. The format,
and why a marker from anyone but the reviewer bot is ignored:
[ci-review.md](references/ci-review.md).

**You read the findings; the script does not.** The digest hands over the
reviewer's summary and inline comments verbatim, because a model wrote them and
a parser would drop whatever it failed to match. List each finding with the
severity and `R<n>` the reviewer gave it. Where the reviewer slipped — no
number, no tag — number it by position, take its severity from
[the table](references/ci-review.md#severity), and say so in the response.
`declared:` is the reviewer's own tally: a tally that disagrees with the list
is a slip to mention at step 10, never a reason to read fewer findings.

**The CI review is a lead, not a verdict.** It reads the change from a context
that did not write it, and it can be wrong about it — severity tags included.
Read every finding against the code before acting on it, the same way step 4's
findings are triaged. Each one ends as exactly one of:

- **fixed** — accepted, and in this PR's scope;
- **rejected** — wrong in front of the code; the reason is a fact about the
  code, never "out of scope" or "not worth it";
- **deferred** — real, but held back by the table below or out of this PR's
  scope.

| `round:` | Fix | Defer |
|---|---|---|
| 1 | every accepted finding, `nit` included | out-of-scope and `pre-existing` |
| 2 | accepted `must-fix` and `should-fix` | `nit` |
| 3 and later | accepted `must-fix` only | `should-fix`, `nit` |

This table governs the PR even where the host brings its own PR-handling
defaults — a PR-activity subscription's "optional findings never start a
push" or "no round limit" among them. The user invoked this skill, and its
round rules are what they chose.

Then, in this order:

1. **Defer.** A `pre-existing` finding verified real is an ordinary
   [step 8](#8-close-out-the-findings-the-run-turned-up) follow-up. Everything
   else deferred goes into **one** issue per PR, `Review leftovers from #<pr>` —
   a checklist of `file:line — what — why`, filed with `file_followup.py --tier
   P3 --found-while <n>` at the first deferral (`--label "model: light"` when
   every item meets [its conditions](references/dependency-triage.md#the-model-light-label)).
   Later rounds add their items to it as a comment.
2. **Respond**, before pushing, so the next round reads it:
   `review_digest.py <pr> --respond <file> --sha <reviewed sha>`, one line per
   finding.
3. **Fix** in `<workdir>` — here, or through
   [agents/review-fix.md](references/agents/review-fix.md) when the fixes are
   more than this session should write itself. Read what changed, re-run the
   verification command, push, and go back to [step 6](#6-ci-to-green).

**Cleared** — go to step 7 — when a round leaves nothing to fix. **FAILED** when
round 4 or later still has an accepted `must-fix`: the loop is not converging.
Leave the PR open, record `--event blocked --field reason=review-rounds`, and in
`all` mode move on.

Record each round: `--event review --field issue=<n> --field pr=<pr> --field
round=<k> --field source=<ci|local> --field must=<n> --field fixed=<n> --field
rejected=<n> --field deferred=<n>`.

### 7. Merge and confirm the issue closed

```bash
${CLAUDE_SKILL_DIR}/scripts/land_pr.sh <pr> --issue <n>
```

Merge as soon as step 6 reports `verdict: PASS` and step 6b has cleared — call
`land_pr.sh` in that same turn. Do not ask whether to merge, and do not report
the green CI and wait: green CI with a cleared review is the approval. Read `result:` and `issue:`. Six results, one of which must
never read as success: [landing-outcomes.md](references/landing-outcomes.md).
Record (`--event merged ...`). Then:

```bash
git switch <default_branch> && git pull --ff-only
```

after every merge, and again as the run's last act — this run never ends parked
on a feature branch. In parallel mode the main checkout is already there; pull it
anyway so it carries the merge that just landed.

**Serial `all`:** re-plan (`plan.py --mode all --refresh
--allow-existing-worktrees`) and start the next issue's step 3 from this
up-to-date branch, without pausing. **Parallel `all`:** the batch's remaining
branches are now behind; bring each up to date in its own worktree **before its
own step 5** rather than after a CI failure, and merge rather than rebase
([how](references/recovery.md#bringing-the-rest-of-a-parallel-batch-up-to-date)).
A conflict either way means the grouping call was wrong for that pair
([recovery.md#a-merge-conflict](references/recovery.md#a-merge-conflict)). Only
when the whole batch has merged does the run group the next batch.

### 8. Close out the findings the run turned up

Every run surfaces defects outside the issue being shipped. Three outcomes, in
order of preference: **fix it in the diff already open** · **file it and ship it
in this same run** ([step 8c](#8c-take-the-runs-own-output-back-into-the-queue))
· **file it and leave it**. "Out of scope for this diff" is not "out of scope for
this run": most of what an implementation run declines belongs in the second, not
the third. Which is which:
[filing-followups.md](references/filing-followups.md) — **read it before filing
anything**.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/file_followup.py \
    --title "<repo's title convention>" --body-file <path> \
    --tier P2 --area <area> --touches <paths> --label <area label> \
    --found-while <n> [--needs-design]
```

`--tier` is required even with `--needs-design` — the moment the design is
decided the issue must already rank correctly. `--area` and `--touches` become
the issue's [ship contract](references/ship-contract.md). `--needs-design` is for
an open design question, not a verified fix. Add `--label "model: light"` when the
follow-up meets [its three conditions](references/dependency-triage.md#the-model-light-label). Exit 2 (`NO_WRITE_ACCESS`) → report
the finding at step 10 instead. File as you go, right after the PR that surfaced
it lands; record (`--event followup`), and pass `--refresh` on the next plan.

### 8b. Unblock held designs in the background

Everything filed `--needs-design`, plus the design-blocked issues already in the
backlog (step 1's `needs-design:`), gets one **`opus`** sub-agent each, from
[agents/design-decision.md](references/agents/design-decision.md).

**Spawn and move on — never block on one.** They run while this session keeps
shipping, and the Agent tool notifies this session as each returns.

- One agent per issue, always `opus`, all of a round issued **in one message**.
  Cap **3 in flight**; queue the rest — this run's own filings first, then
  backlog issues highest tier first.
- **The queue drains on notification, not at a step.** When one returns, record
  it and spawn the next queued agent in the same turn, whatever step the shipping
  path is on. Anything still queued or in flight when the run ends is a step 10
  line.
- Sweep the backlog's held designs **once per run, right after step 1** — in
  every mode, single included — and never again per issue shipped. Spawn this
  run's own filings as soon as `file_followup.py` returns their numbers.
- The agent writes no code, no branch, no PR: it decides the approach, posts it
  as a comment (the design of record the next implementer reads), and clears the
  block itself. A design turning on a product/UX call the repo and the issue
  thread do not already answer comes back `DEFERRED` — the label stays on, the
  `OPEN-QUESTION` goes to the user at step 10, and that is a correct outcome.
- Record each return (`--event design --field issue=<n> --field mode=background
  --field verdict=<DECIDED|DEFERRED>`). `LABEL: left-on` alongside `VERDICT:
  DECIDED` means only the label write failed — clear it from this session before
  treating the issue as ready.

An issue returned `DECIDED` is ordinary backlog from that moment: ready for the
next run, or for this one at step 8c.

### 8c. Take the run's own output back into the queue

Before cleanup, re-plan (`plan.py --mode <same> --refresh
--allow-existing-worktrees`) and keep going through **what this run produced**:
the follow-ups filed at step 8 and the issues step 8b unblocked. Each runs the
same steps 3–8, one PR at a time. With an explicit issue number, the re-plan
only ever looks at that number and prints `select: none` — so re-plan each
candidate by its own number instead (`plan.py --mode <m> --refresh`), and
apply condition 4 from its labels yourself. Take one on only when all four
hold:

1. **Depth 1** — it came from *this* run's own work. A follow-up filed while
   shipping a follow-up is recorded and left for the next run.
2. **Shippable on the ordinary
   [readiness gate](references/dependency-triage.md#readiness-gate)**; a
   `DEFERRED` design is not.
3. **[Budget left](references/cost-discipline.md#run-budget).** Out of budget, or
   a background design still in flight once everything else is done → stop and
   name it at step 10 rather than waiting.
4. **Not deferred-light** — a `model: light` follow-up that nothing heavier
   waits on stays filed for the lighter runner
   ([why](#deferring-light-issues)); the re-plan's `deferred-light:` line names
   it.

In `all` mode these join the existing queue with no privilege over the backlog's
own issues. With no argument or an explicit number, this step is the *only* thing
that extends the run past its first merge.

### 9. Clean up

**Once, after the last merge, script only.** Every deletion this run makes
happens in a single `cleanup_run.sh` call, including when a batch finished long
ago. `rm` is never used anywhere in the run — not on repository content, not on a
throwaway fixture under the scratchpad. Reasoning, scope, and what to do instead:
[closing-out.md#cleanup-scope](references/closing-out.md#cleanup-scope).

Step 7 already left `HEAD` on the up-to-date default branch, which the branch
deletion below requires — it refuses to delete whatever is currently checked out,
in the main checkout *or* in a surviving worktree.

Pass every branch this run created as `--branch <name>`. Without it the
script deletes every merged-PR branch in the repository — other people's
included — which is not this run's to decide.

```bash
${CLAUDE_SKILL_DIR}/scripts/cleanup_run.sh --branch <name> [--branch <name> ...] \
    [--remote] [--dry-run] [--worktree-root <runstate>/worktrees] [--merged-only] [--force]
${CLAUDE_SKILL_DIR}/scripts/preflight.sh \
    --profile-cache <runstate>/repo-profile.json --set-worktree-viable <yes|no>
```

Pass `--worktree-root` only when this run created worktrees; anything gitignored
inside one is lost with it
([recovery.md](references/recovery.md#a-worktree-that-will-not-go-away)). The
second call runs only when this run actually probed worktree viability; it
persists the answer so the next run's plan skips the probe. Record the outcome
(`--event cleanup ...`).

### 10. Report

**No prescribed format** — shape the report to the run. What is fixed is the list
of facts whose absence would mislead the reader:
[closing-out.md#what-the-report-must-not-omit](references/closing-out.md#what-the-report-must-not-omit).
Chief among them: any issue left open behind a merged PR, any acceptance
criterion that shipped `not-met`, and every `DEFERRED` design's open question —
that last one is what the user actually has to answer.

## Stop conditions

Stop the whole run and report when: the plan is `BLOCKED`, a dependency cycle
needs a human to break it, a merge conflict needs a product decision, or the same
CI failure survives the retry ceiling on two different issues.

Also stop on **a change in the repository that this run did not make** — the main
checkout dirty with files no step here touched, a branch moved underneath you,
the default branch ahead of what the last merge left, or a linked worktree under
this run's root that this run did not create. Someone else is working in the same
tree. Prove it is not yours first — compare the actual hunks against what your
own branches and worktrees hold; "it edits a file my issue also edits" is not
proof either way — then leave it exactly as found (no stash, no restore, no
commit) and ask. Their uncommitted work is unrecoverable if you discard it, and a
gate failing on their half-finished edit is not yours to fix. Record before
stopping (`--event blocked --field reason=<...>`).

In `all` mode, a single failed issue does not stop the run — mark it FAILED,
record it, skip anything that depended on it, and continue.

A background design agent returning `DEFERRED` is **not** a stop either, in any
mode. The only design that stops a run is one blocking the issue currently being
implemented, at [step 2b](#2b-decide-a-design-that-gates-the-pick).

## Further reading

[cost-discipline.md](references/cost-discipline.md) — context budget, per-issue
run budget, model and effort assignment, what parallel mode costs against what it
saves · [recovery.md](references/recovery.md) — everything that can go sideways
between step 3 and step 7 ·
[delegation-templates.md](references/delegation-templates.md) — the six sub-agent
prompts and the rules every spawn shares.
