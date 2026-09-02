---
name: shipping-issues
description: "Rank open GitHub Issues by their `priority: P0`-`P3` labels — backfilling a missing label from how much an issue unblocks and how far its impact spreads — then implement the top one, review and fix it with `/code-review` before the PR, open a PR that auto-closes the issue (Closes #N), watch CI until it is green, merge to main automatically on green with no approval pause, confirm the issue closed, and return the checkout to the default branch. With no argument it ships the highest-priority issue and then whatever that run itself produced — the follow-ups it filed, the designs it unblocked; pass \"all\" to work through every issue in dependency order — independent ones implemented in parallel, each in its own worktree, with PR, CI and merge still serialized. Findings that fit the same change are fixed in the open diff rather than filed, and every `blocked: design` issue it files or finds gets a background `opus` sub-agent that decides the approach, records it on the issue, and clears the block. Implementation and CI repair go to a `sonnet` sub-agent; the calling session judges each result and drives PR, CI watch, and merge. Use when asked to ship the remaining issues, start from the highest-priority issue, implement an issue through to merge, take on the next issue, clear the ticket backlog, or work through the open issues."
argument-hint: "[all | <issue number> | (empty = one issue)]"
metadata:
  platforms: claude-code
---

# Shipping Issues

Take open GitHub issues from open to merged-and-closed: rank priority →
implement → review and fix → linked PR → CI green → merge → confirm closed.
Deterministic GitHub work lives in `scripts/`, so raw JSON and CI logs never
enter the main context.
**Done means all three:** the PR is merged to the default branch, the issue is
CLOSED, and nothing was deleted or weakened to get there.

**Invoking this skill is the authorization for every write it makes, up to and
including the merge.** Green CI is the go-ahead: on `verdict: PASS` the merge
happens in the same turn, with no "shall I merge?" and no summary-then-wait.
The same holds for the labels, branches, pushes, PR, follow-up issues, the
design comments step 8b writes, and the cleanup this workflow prescribes — the
ambient "ask before external or
hard-to-reverse writes" default is satisfied here by the user having invoked
the skill, and re-confirming per issue defeats `all` mode entirely. The only
pauses are the [Stop conditions](#stop-conditions) and the two narrow asks
named inline: a genuinely tied top two at step 2, and `NO_CHECKS` in a repo
with no verification command at step 6. Everything else runs to completion,
and the run ends with the main checkout back on the default branch.

## Modes

| Argument | Behavior |
|---|---|
| _(none)_ | Ship the highest-priority shippable issue. After it merges, the run continues through **its own output only** — the follow-ups it filed and the designs it unblocked ([step 8c](#8c-take-the-runs-own-output-back-into-the-queue)) — and never reaches back into the wider backlog. |
| `all` | Ship every shippable issue, in dependency-then-priority order. Independent issues are implemented and reviewed in parallel, one git worktree each (cap 3); the PR, CI watch and merge for each stay serialized in this session. Follow-ups this run files join the same queue. |
| a number, e.g. `42` | Ship that specific issue, after checking nothing it depends on is still open. |

Anything else in the argument is a filter hint (a label, a milestone) — apply
it as `issue_digest.py` flags.

An issue labeled `blocked: design` (or a recognized equivalent — see
[dependency-triage.md](references/dependency-triage.md)) is never *implemented*
automatically, even under `all`. Take its implementation on only by naming its
number explicitly or passing `--include-design`, and only when deciding the
design is itself part of this run —
[step 2b](#2b-decide-the-design-before-implementing).

The label itself is not left alone, though: this run sends a background `opus`
sub-agent after every design-blocked issue it files or finds
([step 8b](#8b-unblock-held-designs-in-the-background)), which decides the
approach, records it on the issue, and clears the block. An issue whose design
was decided that way carries no block any more and is selected like any other —
including, budget permitting, by this same run.

## Working rules

- **One checkout, one writer.** Two runs never share a working tree. That is
  satisfied one of two ways, and which one is in force decides how several
  steps below behave:
  - **Serial (the default)** — no argument, an explicit issue number, or an
    `all` run whose issues are not parallel-safe. Everything happens in the
    repo's main checkout, one issue start to finish before the next begins.
  - **Parallel (`all` only, and only when it earns it)** — two or more
    independent issues get one `git worktree` each, under
    `<runstate>/worktrees/<n>`, capped at 3. Their step 3 implementations run
    concurrently; the main checkout is not used for implementation at all and
    stays on the default branch, clean.
  Which one applies is decided once, at [step 2c](#2c-group-for-parallelism--all-mode-only)
  — never re-decided mid-batch.
- **Concurrency stops at the GitHub API.** Steps 3 and 4 — implement, then
  apply the review's accepted findings — run concurrently across a batch.
  Everything that talks to GitHub — the PR, `link_check.sh`, `ci_watch.sh`,
  `land_pr.sh`, the merge — stays in this session and stays serialized, one PR
  at a time, in both modes. Parallel worktrees buy back the implementation
  wait, which is the long part; they do not make merging concurrent, and
  merging concurrently is not a goal.
- Every issue starts from a clean, up-to-date default branch. Serial:
  `git switch <default> && git pull --ff-only && git switch -c <type>/<n>-<slug>`.
  Parallel: `worktree_setup.sh` branches from the freshly pulled default for
  each issue — see [step 3](#3-implement).
- After a merge, return to that state before ranking the next issue:
  `git switch <default> && git pull --ff-only`. In parallel mode, each merge
  also leaves the batch's remaining branches behind the default — rebase them
  in their own worktrees before their CI run, not after a failure.
- **A run finishes what it started.** What the run itself turns up — a
  follow-up it filed, a design its background agent unblocked — is this run's
  work, not the next run's, as long as it is shippable and there is budget
  ([step 8c](#8c-take-the-runs-own-output-back-into-the-queue)). What it never
  does is reach past that: depth 1 (a follow-up of a follow-up waits), and no
  fresh pass over the wider backlog in single mode.
- A dirty working tree that this run did not create is never touched
  silently — see [Stop conditions](#stop-conditions).

## Inputs and outputs

Reads: the current repo's open issues and PRs; the project's own
`CLAUDE.md` / `AGENTS.md` for conventions.
Writes: `priority: P0`…`P3` labels, `blocked: design` labels (set *and*
cleared), design-decision comments on issues, branches, PRs, merge commits,
issue closures, follow-up issues (step 8), and a run record.
Every file this run generates — the run record, verify/CI logs, filled
prompts, and in parallel mode the worktrees themselves — lives under
`<runstate>` (used through the rest of this document), short for
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/shipping-issues/<owner>__<repo>/`,
**never inside the repo checkout** — including the worktrees, which is why
they are not under `<repo>/.claude/worktrees/`: a worktree nested inside the
repo shows up as `?? .claude/` in the main checkout's `git status`, and this
skill treats an unexplained dirty main checkout as a hard stop. Full layout
and event list: [references/run-record.md](references/run-record.md). Call the run record
right after each event happens, not batched at the end:

```bash
python3 {SKILL_DIR}/scripts/run_record.py --repo <owner>/<repo> --event <kind> \
    [--field k=v ...] [--body-file <path>]
```

## Workflow

### 0. Preflight

`{SKILL_DIR}` is this skill's own absolute path, substituted by the caller.

**Requires:** `git`, `python3`.

```bash
{SKILL_DIR}/scripts/preflight.sh
```

`verdict: BLOCKED` stops the run. `in_worktree: yes` means this session is
already sitting inside a linked worktree — finish there or move to the main
checkout, but do not nest a run's worktrees under one. `existing_worktrees:`
listing anything under this run's own root before the run starts is a
[stop condition](#stop-conditions), not a leftover to reuse.
A dirty tree is a warning — ask first, and
ask *before* the step 3 baseline rather than after: an untracked build or
package-manager cache in the repo root can fail the baseline on its own (seen
in practice: a `.pnpm-store/` holding a unix socket, which a test helper that
copies untracked files hit with a bare `ENOTSUP`). Read a red baseline against
what is in the tree before treating it as the repository's defect.
Open the run record:
`{SKILL_DIR}/scripts/run_record.py --event run-start --field mode=<single|all>`.

### 1. Rank — by label, not by re-reading the backlog

```bash
python3 {SKILL_DIR}/scripts/issue_digest.py --select [--label L] [--assignee A]
```

`priority: P0`…`P3` labels drive rank; `--select` prints coverage, the pick,
and what's held back. Tier sorts first, score only orders *within* a tier;
BLOCKED issues are never selected. A `needs-design:` line lists issues
excluded for having no settled design — expected, not an error; add
`--include-design` only to implement one deliberately. Keep that list: it is
the input to [step 8b](#8b-unblock-held-designs-in-the-background), which
sends a background agent after each of them.

- `N/N COMPLETE`, no `(~Pn)` on top rows — already ranked. **Skip step 2.**
- otherwise, or a `P2(~P0)` marker — go to step 2 once; later runs get the
  cheap path.
- full picture (`BLOCKED-BY`/`UNBLOCKS`/`HAS-OPEN-PR`) — drop `--select` (add
  `--body-chars 0`) or use `--rank-only`.

### 2. Label the unlabeled — once, not per caller

- **≤3 unlabeled/mis-tiered** — read them (`issue_digest.py --issue N --issue
  M`) against the rubric, then:
  ```bash
  python3 {SKILL_DIR}/scripts/apply_priority_labels.py --backfill --set N=P0 --quiet
  ```
- **more, tangled edges, or a close top-two** — hand
  [references/agents/priority-research.md](references/agents/priority-research.md)
  to an independent `sonnet` sub-agent. Returns the pick with evidence, the
  order after it, and blocked/unclear lists — never raw issue prose.

`--backfill` writes suggested tiers to every unlabeled issue; `--set`
overrides ones judged differently. Run without asking. Exit 2
(`NO_WRITE_ACCESS`) → rank from `~Pn` suggestions instead. Rank order and
override rules: [priority-rubric.md](references/priority-rubric.md).
Readiness gate: [dependency-triage.md](references/dependency-triage.md).

Re-run `--select`, record `--event labels` then `--event selection` (rubric
block via `--body-file`). **Proceed without asking** unless the top two are
genuinely tied on every axis, or the pick needs a product decision first.

The `needs-design:` list from this same `--select` is the backlog half of
[step 8b](#8b-unblock-held-designs-in-the-background). On a run with more than
one issue to ship, spawn that round of background design agents here, before
step 3 — they cost this session nothing to wait on, and starting them now is
what gets their issues unblocked while the run is still going.

### 2b. Decide the design before implementing

Only when the picked issue carries `blocked: design` (or an equivalent) and
was taken on deliberately, never from the default backlog scan — this is the
*inline* path, the one where the design gates the very issue about to be
implemented. Settling the approach, recording it, and clearing the block
before step 3:
[dependency-triage.md#deciding-a-held-design](references/dependency-triage.md#deciding-a-held-design).

Every other design-blocked issue — the ones this run is not about to
implement — is handled the other way round, in the background and off the
critical path: [step 8b](#8b-unblock-held-designs-in-the-background).

### 2c. Group for parallelism — `all` mode only

Skip this step entirely with no argument or an explicit issue number: a
worktree for a single issue costs a dependency install and buys nothing.

In `all` mode, decide **once** whether this run is serial or parallel. Two
gates, and both must pass:

1. **Are the issues independent?** Group the shippable issues per
   [dependency-triage.md#parallel-vs-sequential-all-mode](references/dependency-triage.md#parallel-vs-sequential-all-mode).
   Fewer than 2 issues in the leading group → serial.
2. **Is the repo worktree-viable?** A fresh worktree holds tracked files and
   nothing else. `worktree_setup.sh` reconstructs the usual missing pieces;
   what it cannot reconstruct fails loudly rather than silently, and the
   cheapest test is to run it. Provision the group's **first** worktree and
   read its baseline before provisioning the rest —
   [worktree-parallelism.md#viability-gate](references/worktree-parallelism.md#viability-gate).
   `BLOCKED`, or a baseline that is red in the worktree while the main
   checkout is green → this repo is not worktree-viable in this run. Remove
   that worktree, fall back to serial, and say so in the step 10 report.

Both gates pass → parallel, capped at 3 concurrent worktrees. Record
`--event parallel-group --field issues=<n,m,...> --field mode=<parallel|serial>
--field reason=<why>`. Do not revisit the decision mid-batch: a batch that
starts parallel finishes parallel, and the next batch decides again from
scratch.

### 3. Implement

One issue = one branch = one PR. Where that branch lives depends on the mode
[step 2c](#2c-group-for-parallelism--all-mode-only) settled.

**Serial** — in the main checkout:

```bash
git switch <default_branch> && git pull --ff-only && git switch -c <type>/<n>-<slug>
```

Then run the project's own verification command **once, unmodified, on this
branch**, redirected to `<runstate>/verify/<n>-baseline.log`.

**Parallel** — one worktree per issue, provisioned by the script, which
creates the branch, copies the untracked local config, installs dependencies,
and takes the baseline in one call:

```bash
git switch <default_branch> && git pull --ff-only   # once, before the batch
{SKILL_DIR}/scripts/worktree_setup.sh --issue <n> --branch <type>/<n>-<slug> \
    --base <default_branch> --root <runstate>/worktrees \
    --verify "<verify_command>" --log <runstate>/verify/<n>-baseline.log
```

Provision the worktrees **one at a time**, not concurrently — the installs
contend for the same package-manager cache, and a repo whose verify command
binds a fixed port or writes one local DB will fail in ways that look like
the issue's fault. Read each call's `verdict:` line and nothing else.

Either way, **a red baseline is the repository's problem, not the issue's**,
and finding it here costs one command instead of a wasted implementation run.
Read the exit code and the log's tail, never the full output. What the smoke
run turns up goes to step 8.

Fill and spawn a **`sonnet`** sub-agent per issue with
[delegation-templates.md#implementation-step-3](references/delegation-templates.md#implementation-step-3)
— in parallel mode, issue every sub-agent in the batch **in one message** so
they actually run concurrently, and fill each one's work directory with its
own worktree path, never the main checkout. A run that stops before pushing
anything → don't retry blindly: read `git status`/`git log` **in that issue's
own working directory** for what landed, resume naming what's left, or record
`--event blocked`.

**Judge the result in this context, against the issue and step 2b's
decision.** Start from `git -C <workdir> diff --stat <base>...HEAD` — where
`<workdir>` is the main checkout in serial mode and that issue's worktree in
parallel mode; running it in the wrong directory reports on the wrong
branch — plus the sub-agent's
own `CHANGED` / `SCOPE-NOTES` / `UNRESOLVED` — open the hunks only in the
files the spec actually touches, not the whole diff by default. If the
implementation is missing part of the spec or quietly widened it, send a new
`sonnet` run naming only what's left; don't re-run the whole task. Up to
**2** resume/patch runs on top of the first — a third miss means the issue
itself is underspecified: record `--event blocked` and report
`NEEDS-CLARIFICATION` in step 10 instead of spawning again. Use the
returned `TEST-PLAN` verbatim later — don't re-derive it.

### 4. Review and fix — judge the result before the PR exists

Run before any PR exists, against the branch. In parallel mode, step 4 covers
the whole batch: review each branch, triage all of them, then fix them
concurrently — no PR is opened until the batch's last review is triaged.

```
/code-review <effort> <branch> [--fix]
```

**Effort first, branch second** — an unrecognized first token makes the
*entire* string the target and silently falls back to the last effort used.
**`low` is the standing default** — the user set it for every review this skill
runs; escalate only for the narrow cases in
[cost-discipline.md#code-review-effort](references/cost-discipline.md#code-review-effort).
Never `ultra` — it runs in the cloud, is billed, and cannot be launched from
this session.

**`--fix` is serial-mode only.** It applies findings to *this session's*
working tree — the main checkout. In serial mode that is the branch under
review, which is the point. In parallel mode the branch is checked out in a
worktree and the main checkout is sitting on the default branch, so `--fix`
would write another branch's repairs into the main checkout and leave it
dirty — the exact state [Stop conditions](#stop-conditions) treats as someone
else's work. The review itself reads `<base>...<branch>` from the shared
object store and is safe from anywhere; only the writing half is not. So:

| mode | step 4 |
|---|---|
| serial | `/code-review <effort> <branch> --fix`, triaged as below |
| parallel | `/code-review <effort> <branch>` (no `--fix`) per branch, back to back — a slash command runs one at a time, and each one forks, so this costs wall-clock but almost no context. Triage the whole batch, then spawn the fix runs for every branch **in one message**: one `sonnet` sub-agent per branch that has accepted findings, scoped to that issue's worktree, using [delegation-templates.md#review-fix-parallel-mode](references/delegation-templates.md#review-fix-parallel-mode). A branch with zero accepted findings gets no spawn. |

Triage is the same either way, and in parallel mode you triage *before*
anything is written rather than after — read every finding against the issue's
scope, send what belongs in this diff, and route the rest to step 8. "Belongs
in this diff" is the same behavior change the issue is about, tests included —
a sibling case of the bug just fixed belongs here, not in a new issue; a schema
change or a new public surface does not, however small the patch looks
([filing-followups.md](references/filing-followups.md)).

Either path writes code without this session having written it, which inverts
the read-only guarantee a delegated review would otherwise give — **this
session reading what the fix pass changed** is the safeguard against a misread
finding landing unseen:

- **Read the findings the fix pass would not apply** — `skipped` from
  `--fix`, `REJECTED` from the parallel-mode sub-agent. Neither is clean: it
  means out of scope, a behavior change, or a false positive. One that is real
  but outside this issue's scope goes to step 8, not back into this diff.
- **Read only `git -C <workdir> diff <impl-commit>..HEAD`**, not the whole
  branch again. Nothing found and nothing refused → confirm with `--stat` and
  move on.
- Revert anything the fix pass got wrong on closer reading.
- Re-run the verification command **in `<workdir>`** (redirected as in step 3)
  only if something was actually changed; otherwise step 3's verify still
  holds. Then push.

Host won't let this session launch `/code-review` directly → one independent,
**read-only** `opus` sub-agent against the branch, using
[delegation-templates.md#review-fallback](references/delegation-templates.md#review-fallback),
triaged the same way. Never re-read your own diff and call that a review.

Record, per branch: `--event review --field issue=<n> --field
status=<code-review|code-review+agent-fix|DELEGATED> --field
effort=<low|medium|high> --field findings=<n> --field skipped=<n>` —
`skipped` counts refusals from either path.

### 5. Open the PR

From here to step 7 the run is serial in both modes: one PR at a time, in
the batch's dependency-then-priority order. Finish an issue's PR → CI → merge
before opening the next issue's PR, even though their implementations already
ran side by side.

Commits on the branch but nothing pushed → push them from this session
(`git -C <workdir> push -u origin <branch>`). No commits at all → no branch:
record `--event blocked --field issue=<n>`, report `SKIPPED(<why>)` in step
10, in `all` mode move on to the next issue in the batch.

Open a PR from `<branch>` against `<default_branch>`, titled `<PR-TITLE>`.
Body must start with **`Closes #N`** after the summary (a bare `#N` closes
nothing), and target the **default branch** (auto-close only fires there) —
build the body from `PR-SUMMARY`, `Closes #N`, `TEST-PLAN`. Record it
(`--event pr-created --field issue=<n> --field pr=<url>`), then verify the
closing link:

```bash
{SKILL_DIR}/scripts/link_check.sh <pr> --issue <n> --fix
```

`--fix` appends a missing `Closes #N`. `WRONG_BASE` → retarget the PR's base
to `<default>` before merging.

### 6. CI to green

The checks API still serves the PREVIOUS commit's results for a minute or two
after a push, so a watch started too early returns that run's verdict — a
stale PASS is worse than a stale FAIL. Wait for the PR's new head commit to
actually appear among the branch's CI runs before watching, then:

```bash
{SKILL_DIR}/scripts/ci_watch.sh <pr> --timeout 1800 > <runstate>/ci/<pr>.log
grep -E '^(verdict|mergeable|merge_state|review_decision):' <runstate>/ci/<pr>.log
```

Redirected — raw output carries failing-run log tails that must stay out of
this context. One watch per PR; keep `failed_checks:` for repair. This is the
run's only wait primitive — never a hand-rolled sleep/poll loop. Block on it
directly, one PR at a time, even in `all` mode. Record (`--event ci --field
pr=<n> --field verdict=<...>`).

On `FAIL`, fill and spawn a **`sonnet`** sub-agent (escalate to `opus` after
the same failure survives two attempts in a row) with
[delegation-templates.md#ci-repair-step-6](references/delegation-templates.md#ci-repair-step-6-only-on-fail),
its work directory set to whichever checkout holds the branch — the main
checkout in serial mode, that issue's worktree in parallel mode — up to
**3 attempts**. `PUSHED: no` ends the loop. A test deleted, skipped,
or weakened to pass, or a "flaky" re-run without diagnosis, is a failed
outcome. `NO_CHECKS` → run the project's own verification command locally and
merge on a local green (no such command → ask first). `verdict: ERROR` →
re-read the actual PR/CI state before treating it as a green.

### 7. Merge and confirm the issue closed

```bash
{SKILL_DIR}/scripts/land_pr.sh <pr> --issue <n>
```

Merge as soon as step 6 reports `verdict: PASS` — call `land_pr.sh` in that
same turn. Do not ask whether to merge, and do not report the green CI and
wait: green CI is the approval. Re-checks the closing link, confirms the issue
closed — read `result:` and `issue:`. Six results, one must never read as
success: [landing-outcomes.md](references/landing-outcomes.md).
Record (`--event merged ...`).

Then put the main checkout back on the default branch — after every merge, and
again as the run's last act before the step 10 report:

```bash
git switch <default_branch> && git pull --ff-only
```

This run never ends with the session parked on a feature branch. In parallel
mode the main checkout is already on the default branch; pull it anyway so it
carries the merge that just landed.

**Serial `all`:** re-rank with `issue_digest.py --select` from there — one
script call, not another research pass — and start the next issue's step 3
from this same up-to-date branch, without pausing for confirmation in between.

**Parallel `all`:** the batch's remaining branches are now behind the default
branch. Bring each one up to date **in its own worktree, before its own step 5**
rather than after a CI failure:

```bash
git -C <runstate>/worktrees/<m> fetch origin <default_branch> --quiet
git -C <runstate>/worktrees/<m> merge origin/<default_branch>
git -C <runstate>/worktrees/<m> push
```

**Merge, not rebase** — step 3 already pushed these branches, so a rebase
would need a force-push, and this run does not force-push. A repo that
requires linear history is the one exception: there, rebase and push with
`--force-with-lease`, and only ever on a branch this run created and no PR is
open on yet.

A conflict either way means the parallel-safety call in step 2c was wrong for
that pair — resolve it in that worktree only if the conflict is mechanical;
otherwise record `--event blocked --field reason=merge-conflict`, report it,
and move on. Only when the whole batch has merged does the run re-rank with
`issue_digest.py --select` and group the next batch at step 2c.

### 8. Close out the findings the run turned up

Every run surfaces defects outside the issue being shipped — returned under
`SCOPE-NOTES`, `OUT-OF-SCOPE`, or `FOLLOW-UPS`. Three outcomes, in this order
of preference:

1. **fix it in the diff already open** — when it is the same behavior change
   the issue is about and the issue's own tests (or one added beside them)
   cover it;
2. **file it and ship it in this same run** ([step 8c](#8c-take-the-runs-own-output-back-into-the-queue))
   — when it is a separate change but nothing about it is undecided;
3. **file it and leave it** — only when it needs a product call, depends on
   something still open, is its own batch of work, or the run is out of budget.

"Out of scope for this diff" is not "out of scope for this run": most of what
an implementation run declines belongs in outcome 2, not 3.
[references/filing-followups.md](references/filing-followups.md) settles which
— **read it before filing anything**.

```bash
python3 {SKILL_DIR}/scripts/file_followup.py \
    --title "<repo's title convention>" --body-file <path> \
    --tier P2 --label <area label> --found-while <n> [--needs-design]
```

`--tier` is required, per [priority-rubric.md](references/priority-rubric.md),
even with `--needs-design` — the moment the design is decided the issue must
already rank correctly. Add `--needs-design` only when the finding is an open
design question rather than a verified fix —
[filing-followups.md](references/filing-followups.md) settles which. Exit 2
(`NO_WRITE_ACCESS`) means report the finding in step 10 instead. File as you
go, right after the PR that surfaced it lands; record (`--event followup`).

### 8b. Unblock held designs in the background

Everything filed `--needs-design` just now, plus the `blocked: design` issues
already in the backlog (the `needs-design:` list from step 1), gets one
**`opus`** sub-agent each, filled from
[delegation-templates.md#design-decision-step-8b](references/delegation-templates.md#design-decision-step-8b).

**Spawn and move on — never block on one.** They run in the background while
this session keeps shipping, and the Agent tool notifies this session as each
returns. The rules:

- One agent per issue, always `opus`, all of a round issued **in one message**.
  Cap **3 in flight**; queue the rest behind them — this run's own filings
  first, then backlog issues highest tier first.
- Spawn this run's filings as soon as `file_followup.py` returns their numbers.
  Sweep the backlog's held designs **once per run** — and that sweep does not
  have to wait for step 8: the `needs-design:` list is already in hand at step
  1, so a run with more than one issue to ship spawns it right after the step 2
  selection, giving those agents the whole run to finish in. Never sweep again
  after every issue shipped.
- The agent writes no code, no branch, no PR. It decides the approach, posts it
  as a comment on the issue — that comment is the design of record the next
  implementer reads — and clears the block itself with
  `apply_priority_labels.py --clear-design <n>`.
- A design that turns on a product/UX call the repo and the issue thread do not
  already answer comes back `DEFERRED`: the label stays on, and the agent's
  `OPEN-QUESTION` goes to the user in the step 10 report. That is a correct
  outcome, not a failure — see [Stop conditions](#stop-conditions): it is the
  one design question this run does not decide alone.
- Record each return: `--event design --field issue=<n> --field mode=background
  --field verdict=<DECIDED|DEFERRED>`. `LABEL: left-on` alongside
  `VERDICT: DECIDED` means only the label write failed — clear it from this
  session before treating the issue as ready.

An issue returned `DECIDED` is ordinary backlog from that moment: ready for the
next run, or for this one at step 8c.

### 8c. Take the run's own output back into the queue

Before cleanup, re-rank with `issue_digest.py --select` — one script call, no
research pass — and keep going through **what this run produced**: the
follow-ups filed at step 8 and the issues step 8b unblocked. Each runs the same
steps 3–8 as any other issue, one PR at a time.

Take one on only when all three hold:

1. **Depth 1** — it came from *this* run's own work. A follow-up filed while
   shipping a follow-up is recorded and left for the next run; that is what
   stops a run from chasing its own tail.
2. **Shippable on the ordinary gate**
   ([dependency-triage.md#readiness-gate](references/dependency-triage.md#readiness-gate))
   — design settled, nothing open it depends on, one coherent scope. A
   `DEFERRED` design is not shippable.
3. **Budget left** ([cost-discipline.md#run-budget](references/cost-discipline.md#run-budget)).
   Out of budget, or a background design still in flight once everything else
   is done → stop and name it in the report rather than waiting on it.

In `all` mode these simply join the existing queue, ordered the same way, with
no privilege over the backlog's own issues. With no argument or an explicit
issue number, this step is the *only* thing that extends the run past its first
merge.

### 9. Clean up — once, after the last merge, script only

Step 7 already leaves `HEAD` on the up-to-date default branch, which is a
precondition for the branch deletion below (it refuses to delete whatever is
currently checked out — in the main checkout *or* in a surviving worktree):

```bash
{SKILL_DIR}/scripts/cleanup_run.sh [--remote] [--dry-run] \
    [--worktree-root <runstate>/worktrees] [--merged-only] [--force]
```

Pass `--worktree-root` only when this run created worktrees; without it the
worktree pass is skipped, which is right for a serial run. The worktree pass
runs first — a branch checked out in a worktree cannot be deleted, so the
worktrees have to go before the branches can. **Anything gitignored inside a
worktree is lost with it** — a fixture or benchmark output an implementation
run produced and did not commit has to be copied into the main checkout
before this step, which is why the implementation template tells sub-agents
to do exactly that.

Scope: [references/closing-out.md#cleanup-scope](references/closing-out.md#cleanup-scope)
— record the cleanup outcome (`--event cleanup ...`).

### 10. Report

Shape: [references/closing-out.md#report-shape](references/closing-out.md#report-shape)
— selection rationale, per-issue outcomes, follow-ups filed (and what was fixed
inline instead of filed) and checked but not filed, designs decided or
`DEFERRED` by step 8b, then what was left undone. A `DEFERRED` design's open
question is the one thing in the report the user has to answer. Flag any issue left open behind a
merged PR explicitly — that is the failure mode this skill exists to prevent.

## Cost discipline

What belongs in this context versus a sub-agent's, the per-issue run budget,
why the model and effort assignments are what they are, and what parallel mode
actually costs versus what it saves:
[references/cost-discipline.md](references/cost-discipline.md).

## Stop conditions

Stop the whole run and report when: preflight is BLOCKED, a dependency cycle
needs a human to break it, a merge conflict needs a product decision, or the
same CI failure survives the retry ceiling on two different issues.

Also stop on **a change in the repository that this run did not make** — the
main checkout dirty with files no step here touched, a branch moved underneath
you, main ahead of what the last merge left, or a linked worktree under this
run's root that this run did not create. Someone else is working in the same
tree. Prove it is not yours before concluding it (compare the actual hunks
against what your own branches and worktrees hold; "it edits a file my issue
also edits" is not proof either way), then leave it exactly as found — no stash, no restore, no
commit — and ask. Their uncommitted work is unrecoverable if you discard it, and
a gate failing on their half-finished edit is not yours to fix. Record it
before stopping (`--event blocked --field reason=<what stopped it>`).

In `all` mode, a single failed issue does not stop the run — mark it FAILED,
record it the same way, skip anything that depended on it, and continue.

A background design agent returning `DEFERRED` (step 8b) is **not** a stop
either, in any mode: its issue stays blocked, its open question goes in the
report, and the run carries on with everything else. The only design that stops
a run is one blocking the issue currently being implemented, at step 2b.
