---
name: shipping-issues
description: "Rank open GitHub Issues by their `priority: P0`-`P3` labels — backfilling a missing label from how much an issue unblocks and how far its impact spreads — then implement the top one, review and fix it with `/code-review` before the PR, open a PR that auto-closes the issue (Closes #N), watch CI until it is green, merge to main automatically on green with no approval pause, confirm the issue closed, and return the checkout to the default branch. With no argument it ships the highest-priority issue and then whatever that run itself produced — the follow-ups it filed, the designs it unblocked; pass \"all\" to work through every issue in dependency order — independent ones implemented in parallel, each in its own worktree, with PR, CI and merge still serialized. Findings that fit the same change are fixed in the open diff rather than filed, and every `blocked: design` issue it files or finds gets a background `opus` sub-agent that decides the approach, records it on the issue, and clears the block. Implementation and CI repair go to a `sonnet` sub-agent — `opus` when the issue is foundational (architecture, an interface or schema, a skill or gate the rest of the backlog copies); the calling session judges each result and drives PR, CI watch, and merge. Use when asked to ship the remaining issues, start from the highest-priority issue, implement an issue through to merge, take on the next issue, clear the ticket backlog, or work through the open issues."
argument-hint: "[all | <issue number> | (empty = one issue)] [parallel N]"
metadata:
  platforms: claude-code
---

# Shipping Issues

Take open GitHub issues from open to merged-and-closed: plan → implement →
review and fix → linked PR → CI green → merge → confirm closed. Deterministic
GitHub work lives in `scripts/`, so raw JSON and CI logs never enter the main
context.
**Done means all three:** the PR is merged to the default branch, the issue is
CLOSED, and nothing was deleted or weakened to get there.

**Invoking this skill is the authorization for every write it makes, up to and
including the merge.** Green CI is the go-ahead: on `verdict: PASS` the merge
happens in the same turn, with no "shall I merge?" and no summary-then-wait.
The same holds for the labels, branches, pushes, PR, follow-up issues, the
design comments step 8b writes, and the cleanup this workflow prescribes — the
ambient "ask before external or hard-to-reverse writes" default is satisfied
here by the user having invoked the skill, and re-confirming per issue defeats
`all` mode entirely. The only pauses are the [Stop conditions](#stop-conditions)
and the two narrow asks named inline: a genuinely tied top two at step 2, and
`NO_CHECKS` in a repo with no verification command at step 6. Everything else
runs to completion, and the run ends with the main checkout back on the default
branch.

## Modes

| Argument | Behavior |
|---|---|
| _(none)_ | Ship the highest-priority shippable issue. After it merges, the run continues through **its own output only** — the follow-ups it filed and the designs it unblocked ([step 8c](#8c-take-the-runs-own-output-back-into-the-queue)) — and never reaches back into the wider backlog. |
| `all` | Ship every shippable issue, in dependency-then-priority order. Independent issues are implemented and reviewed in parallel, one git worktree each; the PR, CI watch and merge for each stay serialized in this session. Follow-ups this run files join the same queue. |
| a number, e.g. `42` | Ship that specific issue, after checking nothing it depends on is still open. |

A count or concurrency in the argument — "10個ぐらい", "3 at a time", "parallel
5" — is the user setting `--max-parallel`. Pass it to `plan.py`; the default is
3 and the *only* reason to raise it is that the user asked. Anything else in the
argument is a filter hint (a label, a milestone) — pass it as `plan.py` flags.

An issue labeled `blocked: design` — or carrying `design=open` in its ship
contract, or a recognized label equivalent — is never *implemented*
automatically, even under `all`. Take its implementation on only by naming its
number explicitly or passing `--include-design`, and only when deciding the
design is itself part of this run
([step 2b](#2b-decide-a-design-that-gates-the-pick)).

The label itself is not left alone, though: this run sends a background `opus`
sub-agent after every design-blocked issue it files or finds
([step 8b](#8b-unblock-held-designs-in-the-background)), which decides the
approach, records it on the issue, and clears the block. An issue whose design
was decided that way carries no block any more and is selected like any other —
including, budget permitting, by this same run.

## Working rules

- **One checkout, one writer.** Two runs never share a working tree. Step 1
  decides which arrangement is in force, once, and several steps below read that
  decision: **serial** puts everything in the main checkout, one issue start to
  finish; **parallel** gives each issue its own worktree under
  `<runstate>/worktrees/<n>` and leaves the main checkout on the default branch,
  clean and unused for implementation. Never re-decide mid-batch — a batch that
  starts parallel finishes parallel, and the next batch is planned from scratch.
- **Concurrency stops at the GitHub API.** Steps 3 and 4 — implement, then apply
  the review's accepted findings — run concurrently across a batch. Everything
  that talks to GitHub — the PR, `link_check.sh`, `ci_watch.sh`, `land_pr.sh`,
  the merge — stays in this session and stays serialized, one PR at a time, in
  both modes. Parallel worktrees buy back the implementation wait, which is the
  long part; they do not make merging concurrent, and merging concurrently is
  not a goal.
- Every issue starts from a clean, up-to-date default branch, and the run
  returns there after every merge (`git switch <default> && git pull --ff-only`).
- **A run finishes what it started.** What the run itself turns up — a follow-up
  it filed, a design its background agent unblocked — is this run's work, not the
  next run's, as long as it is shippable and there is budget
  ([step 8c](#8c-take-the-runs-own-output-back-into-the-queue)). What it never
  does is reach past that: depth 1 (a follow-up of a follow-up waits), and no
  fresh pass over the wider backlog in single mode.
- A dirty working tree that this run did not create is never touched silently —
  see [Stop conditions](#stop-conditions).

## Inputs and outputs

Reads: the current repo's open issues and PRs; the project's own `CLAUDE.md` /
`AGENTS.md` for conventions.
Writes: `priority: P0`…`P3` labels, `blocked: design` labels (set *and*
cleared), design-decision comments on issues, branches, PRs, merge commits,
issue closures, follow-up issues (step 8), and a run record.

Every file this run generates — the run record, the repo profile and digest
caches, verify/CI logs, filled prompts, and in parallel mode the worktrees
themselves — lives under `<runstate>`, short for
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/shipping-issues/<owner>__<repo>/`
and **never inside the repo checkout**, worktrees included: anything nested in
the repo shows up as an untracked path in the main checkout's `git status`,
which this skill treats as a hard stop. Layout and event list:
[references/run-record.md](references/run-record.md). Call the run record right
after each event, not batched at the end:

```bash
python3 {SKILL_DIR}/scripts/run_record.py --repo <owner>/<repo> --event <kind> \
    [--field k=v ...] [--body-file <path>]
```

`{SKILL_DIR}` is this skill's own absolute path, substituted by the caller.
**Requires:** `git`, `python3`, `gh`.

## The ship contract

An issue can state the facts this run would otherwise infer from its prose, in a
comment block anywhere in the body:

```
<!-- ship: tier=P1 area=test-infra blocked-by=none blocks=#98
     touches=tests/,vitest.config.ts design=settled -->
```

`tier=` is a **settled** tier, not a guess — it ranks like a written label and
prints without the `~`. `blocked-by=`/`blocks=` are stated edges rather than
scraped ones. `touches=` is the one that changes what this skill can do
mechanically: parallel grouping stops being a judgement about which issues might
collide and becomes a set intersection, which is why step 1 reports `MECHANICAL`
only when every issue in the batch declares it.

Nothing here is required and a repo with no contracts works exactly as before —
the heuristics stay. But every field an issue carries is one the run does not
re-derive, so `file_followup.py` writes a contract on everything this run files,
and `issue_digest.py --audit` names the existing issues missing one. Run the
audit when a plan comes back `PARTIAL`; report its list in step 10 rather than
backfilling issues by hand mid-run.

## Workflow

### 1. Plan — one call

```bash
python3 {SKILL_DIR}/scripts/plan.py --mode <all|single|N> [--max-parallel N] \
    [--label L] [--assignee A] [--milestone M] [--include-design] --record
```

This is preflight, ranking, selection, the repo profile and the parallel
grouping in a single block and a single `gh` fetch. Read the block; do not
re-derive any of it.

- `preflight:` — `BLOCKED` stops the run. `tree: DIRTY` is a question to ask
  **now**, before any baseline. `existing-worktrees:` with a `BLOCKED` verdict
  means worktrees already sit under this run's own root: an earlier run that did
  not clean up, or one happening right now. That is a
  [stop condition](#stop-conditions), not a leftover to reuse — the branches
  inside are stale, and provisioning over them would implement on top of a
  branch this run never created. Confirm nothing is running in them, remove
  them with `cleanup_run.sh --worktree-root <runstate>/worktrees`, and re-plan.
- `profile:` / `verify-check:` — the package and hook managers, and a
  **suggested** verification command. That suggestion is a guess from script
  names in `package.json` (or a Makefile, or the language's default), and step 3
  executes it, so **confirm it before using it**: is it the gate this repo
  actually runs before a PR, and does it terminate? A repo whose `test` is the
  unit tests while `lint` and `typecheck` are separate gives a baseline that
  passes while CI will fail; a script that starts a watcher never returns at
  all. Overriding it is a one-word decision — say which command you used, in
  the step 10 report.
- `github:` — `write=no` means the label and follow-up writes will exit 2: rank
  from `~Pn` suggestions and report findings instead of filing them.
- `labels:` — `COMPLETE` means every tier is settled, so **skip step 2**.
- `contract:` — how much of the backlog states its own facts. Informational
  during the run; it is what a `PARTIAL` grouping traces back to.
- `grouping:` — **always a proposal**, never a decision:
  [step 2c](#2c-confirm-the-proposed-batch) is where it is confirmed.
  `MECHANICAL` means every issue in it declared its paths, so the proposal rests
  on stated facts · `PARTIAL` means at least one did not, so part of it rests on
  dependency edges alone · `SERIAL` means one issue at a time, no worktrees.
- `select:` / `batch A:` / `branch:` — the pick, everything that can be worked
  beside it, and the branch name already derived for each. Use those names.
- `needs-design:` — the input to
  [step 8b](#8b-unblock-held-designs-in-the-background). On a run with more than
  one issue to ship, spawn that round of background agents **here**, before
  step 3: they cost this session nothing to wait on, and starting them now is
  what gets their issues unblocked while the run is still going.
- `next:` — the exact command step 3 starts with.

`--record` writes `run-start`, `selection` and (in parallel mode)
`parallel-group` to the run record, so those are not separate calls.

`plan.py` caches its `gh` fetch for 300 seconds so the startup's own calls do not
re-fetch. `issue_digest.py` does **not** cache unless asked (`--cache-ttl`), so an
ad-hoc call after a merge always reads the real backlog. Pass `--refresh` when
re-planning inside that 300-second window after this run changed something.

Need the issue bodies too? One more call, still one fetch:

```bash
python3 {SKILL_DIR}/scripts/issue_digest.py --select 3 --with-rank \
    --detail-top 3 --body-chars 700
```

`--detail-top K` reads the top K without narrowing the ranking. Never list the
numbers by hand in three separate calls — that is three `gh` round-trips over
data the plan already fetched.

### 2. Label the unlabeled — only when the plan says so

Skip entirely on `labels: … COMPLETE`.

- **≤3 without a settled tier** — read them
  (`issue_digest.py --detail N --detail M`) against the rubric, then:
  ```bash
  python3 {SKILL_DIR}/scripts/apply_priority_labels.py --backfill --set N=P0 --quiet
  ```
- **more, tangled edges, or a close top-two** — hand
  [references/agents/priority-research.md](references/agents/priority-research.md)
  to an independent `sonnet` sub-agent. Returns the pick with evidence, the
  order after it, and blocked/unclear lists — never raw issue prose.

`--backfill` writes suggested tiers to every unlabeled issue; `--set` overrides
ones judged differently. Run without asking. Exit 2 (`NO_WRITE_ACCESS`) → rank
from `~Pn` suggestions instead. Rank order and override rules:
[priority-rubric.md](references/priority-rubric.md). Readiness gate:
[dependency-triage.md](references/dependency-triage.md).

Re-plan with `plan.py --refresh --record`, then **proceed without asking**
unless the top two are genuinely tied on every axis, or the pick needs a product
decision first.

### 2b. Decide a design that gates the pick

Only when the picked issue is design-blocked and was taken on deliberately —
never from the default backlog scan. This is the *inline* path, where the design
gates the very issue about to be implemented: settle the approach, record it,
and clear the block before step 3, per
[dependency-triage.md#deciding-a-held-design](references/dependency-triage.md#deciding-a-held-design).

Every other design-blocked issue is handled the other way round, in the
background and off the critical path:
[step 8b](#8b-unblock-held-designs-in-the-background).

### 2c. Confirm the proposed batch

**Every parallel batch passes through here** — the plan proposes, this step
decides. A script can tell you that two issues declare no overlapping paths and
no dependency edge between them; it cannot tell you that both will end up
editing the same config file, that one is a refactor whose blast radius is
wider than its `touches=` admits, or that a repo's generated files make any two
concurrent branches conflict. That is what to check here, against
[dependency-triage.md#parallel-vs-sequential-all-mode](references/dependency-triage.md#parallel-vs-sequential-all-mode)
and [worktree-parallelism.md](references/worktree-parallelism.md).

How much to check scales with what the proposal rests on:

- `MECHANICAL` — every issue stated its paths. Read the issues' scope against
  their declared `touches=` and drop any pair whose real reach is wider than it
  declared. Usually quick.
- `PARTIAL` — some issue declared nothing, so its half of the grouping is a
  guess. Read those issues properly before keeping them in the batch.

Shrinking the batch is always allowed and never needs asking: two issues in
parallel is already most of the win, and a wrong pairing costs a merge conflict
mid-batch. Note any issue whose `touches=` had to be judged — that is the step
10 report line, and the next run over this backlog should not have to make the
same call.

### 3. Implement

One issue = one branch = one PR. Step 1's `next:` line is the command.

**Serial** — in the main checkout:

```bash
git switch <default_branch> && git pull --ff-only && git switch -c <branch>
```

Then run the project's own verification command (the plan's `verify=`) **once,
unmodified, on this branch**, redirected to
`<runstate>/verify/<n>-baseline.log`.

**Parallel** — the script creates each branch, copies the untracked local
config, installs dependencies, and runs the baseline (bounded; a command that
never returns comes back `TIMEOUT`). It **reports and does not decide** —
nothing is torn down, nothing is skipped, no verdict is drawn about the repo:

```bash
git switch <default_branch> && git pull --ff-only   # once, before the batch
{SKILL_DIR}/scripts/worktree_setup.sh --spec <n>:<branch> --spec <m>:<branch> \
    --base <default_branch> --root <runstate>/worktrees \
    --log-dir <runstate>/verify --verify "<confirmed verify command>"
```

**Provision the first worktree on its own, read its block, then ask for the
rest.** One extra call, and it is what stops a repo that cannot carry a worktree
from costing three dependency installs instead of one. Read each block's
`verdict:`/`baseline:` lines and the trailing `batch:` line, nothing else.

Then judge what the baseline means — this is yours, not the script's:

- **`baseline: PASS`** → provision the rest of the batch.
- **`baseline: FAIL` in the worktree while the main checkout is green** →
  usually this repo is not worktree-viable in this run, but read the log's tail
  before concluding it: an absolute path in a config, a service the tests expect
  running, a fixture that only exists in the main checkout are all things that
  fail this way and are fixable. Not fixable → remove that worktree yourself
  (`git worktree remove --force <path> && git worktree prune`), record the
  verdict so later runs skip the probe, fall back to serial, and say so in step
  10 ([recovery.md#a-red-baseline](references/recovery.md#a-red-baseline)).
- **`baseline: FAIL` in the main checkout too** → the repository is broken and
  this is not the issue's problem. That is a step 8 finding, and the run may
  still be shippable on top of it — decide, and say which.
- **`baseline: TIMEOUT`** → the verify command never finished, so nothing was
  proved either way. Almost always the wrong command was chosen at step 1 (a
  watcher, a dev server). Pick the right one and re-run the baseline; do not
  treat it as a red baseline.

Read the exit code and the log's tail, never the full output. What the smoke run
turns up goes to step 8.

Fill and spawn a sub-agent per issue with
[delegation-templates.md#implementation-step-3](references/delegation-templates.md#implementation-step-3).
**`sonnet` by default; `opus` when the issue is foundational** — architecture or
a skeleton, an interface/port/schema, or a skill, instruction file, or gate whose
shape the rest of the backlog copies. The test is blast radius, not difficulty:
[cost-discipline.md#the-foundation-exception-opus-for-what-the-backlog-builds-on](references/cost-discipline.md#the-foundation-exception-opus-for-what-the-backlog-builds-on).
A change small enough that the handoff costs more than the work — a few known
lines, nothing to explore, verified by a command this session reads anyway — is
implemented here instead of spawned at all:
[cost-discipline.md#the-floor-too-small-to-delegate](references/cost-discipline.md#the-floor-too-small-to-delegate).

In parallel mode, issue every sub-agent in the batch **in one message** so they
actually run concurrently, and fill each one's work directory with its own
worktree path, never the main checkout.

Then **judge each result in this context**, against the issue and step 2b's
decision. Read the returned `ACCEPTANCE` block first: any `not-met` line is
work still owed on this issue, and sending it back now costs one resume run
where letting it through costs a merge that closed an issue it did not answer.
Green CI does not cover this — it proves the repository still works, not that
the issue was answered. A run that came back without a report, stopped before pushing, or
missed or widened the spec: [recovery.md](references/recovery.md) — in
particular, never re-spawn an agent that returned without its report. Use the
returned `TEST-PLAN` verbatim later; don't re-derive it.

### 4. Review and fix — judge the result before the PR exists

Run before any PR exists, against the branch. In parallel mode step 4 covers the
whole batch: review each branch, triage all of them, then fix them
concurrently — no PR is opened until the batch's last review is triaged.

```
/code-review <effort> <branch> [--fix]
```

**Effort first, branch second** — an unrecognized first token makes the *entire*
string the target and silently falls back to the last effort used. **`low` is
the standing default** — the user set it for every review this skill runs;
escalate only for the narrow cases in
[cost-discipline.md#code-review-effort](references/cost-discipline.md#code-review-effort).
Never `ultra` — it runs in the cloud, is billed, and cannot be launched from
this session.

**One escalation is not optional**: `low` skips test and fixture hunks, so a
diff living entirely in a file under `tests/` that *is* a gate — a workflow
lint, a boundary assertion, a tree walk deciding what "green" means — comes back
`(none)` having read nothing. That is a false clean, not a pass. Check what the
review actually read before believing an empty findings list, and re-run at
`medium`:
[cost-discipline.md#the-escalation-that-is-not-optional-a-diff-low-cannot-see](references/cost-discipline.md#the-escalation-that-is-not-optional-a-diff-low-cannot-see).

**`--fix` is serial-mode only** — in parallel mode it would write one branch's
repairs into the main checkout. Parallel mode reviews without `--fix` and spawns
one `sonnet` fix run per branch instead, all in one message; a branch with zero
accepted findings gets no spawn. Both paths and the reason:
[recovery.md#--fix-and-why-it-is-serial-mode-only](references/recovery.md#--fix-and-why-it-is-serial-mode-only).
Host won't let this session launch `/code-review` at all →
[recovery.md#code-review-cannot-be-launched](references/recovery.md#code-review-cannot-be-launched).

Triage is the same either way, and in parallel mode you triage *before* anything
is written rather than after — read every finding against the issue's scope,
send what belongs in this diff, and route the rest to step 8. "Belongs in this
diff" is the same behavior change the issue is about, tests included — a sibling
case of the bug just fixed belongs here, not in a new issue; a schema change or
a new public surface does not, however small the patch looks
([filing-followups.md](references/filing-followups.md)).

Either path writes code this session did not write, which inverts the read-only
guarantee a delegated review would otherwise give. **This session reading what
the fix pass changed** is the safeguard against a misread finding landing
unseen:

- **Read the findings the fix pass would not apply** — `skipped` from `--fix`,
  `REJECTED` from the parallel-mode sub-agent. Neither is clean: it means out of
  scope, a behavior change, or a false positive. One that is real but outside
  this issue's scope goes to step 8, not back into this diff.
- **Read only `git -C <workdir> diff <impl-commit>..HEAD`**, not the whole branch
  again. Nothing found and nothing refused → confirm with `--stat` and move on.
- Revert anything the fix pass got wrong on closer reading.
- Re-run the verification command **in `<workdir>`** (redirected as in step 3)
  only if something was actually changed; otherwise step 3's verify still holds.
  Then push.

Record, per branch: `--event review --field issue=<n> --field
status=<code-review|code-review+agent-fix|DELEGATED> --field
effort=<low|medium|high> --field findings=<n> --field skipped=<n>` — `skipped`
counts refusals from either path.

### 5. Open the PR

From here to step 7 the run is serial in both modes: one PR at a time, in the
batch's dependency-then-priority order. Finish an issue's PR → CI → merge before
opening the next issue's PR, even though their implementations already ran side
by side.

Commits on the branch but nothing pushed → push them from this session
(`git -C <workdir> push -u origin <branch>`). No commits at all → no branch:
record `--event blocked --field issue=<n>`, report `SKIPPED(<why>)` in step 10,
and in `all` mode move on to the next issue in the batch.

Open a PR from `<branch>` against `<default_branch>`, titled `<PR-TITLE>`. Body
must start with **`Closes #N`** after the summary (a bare `#N` closes nothing),
and target the **default branch** (auto-close only fires there) — build the body
from `PR-SUMMARY`, `Closes #N`, `TEST-PLAN`. Record it (`--event pr-created
--field issue=<n> --field pr=<url>`), then verify the closing link:

```bash
{SKILL_DIR}/scripts/link_check.sh <pr> --issue <n> --fix
```

`--fix` appends a missing `Closes #N`. `WRONG_BASE` → retarget the PR's base to
`<default>` before merging.

### 6. CI to green

Wait for the PR's new head commit to appear among the branch's CI runs before
watching — the checks API serves the previous commit's results for a minute or
two after a push, and a stale PASS is worse than a stale FAIL. Then:

```bash
{SKILL_DIR}/scripts/ci_watch.sh <pr> --timeout 1800 > <runstate>/ci/<pr>.log
grep -E '^(verdict|mergeable|merge_state|review_decision):' <runstate>/ci/<pr>.log
```

Redirected — raw output carries failing-run log tails that must stay out of this
context. One watch per PR; keep `failed_checks:` for repair. This is the run's
only wait primitive — never a hand-rolled sleep/poll loop. Block on it directly,
one PR at a time, even in `all` mode. Record (`--event ci --field pr=<n> --field
verdict=<...>`).

`FAIL`, `NO_CHECKS`, or `ERROR` → [recovery.md#ci-fails](references/recovery.md#ci-fails).

### 7. Merge and confirm the issue closed

```bash
{SKILL_DIR}/scripts/land_pr.sh <pr> --issue <n>
```

Merge as soon as step 6 reports `verdict: PASS` — call `land_pr.sh` in that same
turn. Do not ask whether to merge, and do not report the green CI and wait:
green CI is the approval. Re-checks the closing link, confirms the issue
closed — read `result:` and `issue:`. Six results, one must never read as
success: [landing-outcomes.md](references/landing-outcomes.md). Record
(`--event merged ...`).

Then put the main checkout back on the default branch — after every merge, and
again as the run's last act before the step 10 report:

```bash
git switch <default_branch> && git pull --ff-only
```

This run never ends with the session parked on a feature branch. In parallel
mode the main checkout is already on the default branch; pull it anyway so it
carries the merge that just landed.

**Serial `all`:** re-plan from there — `plan.py --mode all --refresh
--allow-existing-worktrees` — and
start the next issue's step 3 from this same up-to-date branch, without pausing
for confirmation in between.

**Parallel `all`:** the batch's remaining branches are now behind the default
branch. Bring each up to date in its own worktree **before its own step 5**
rather than after a CI failure, and merge rather than rebase:
[recovery.md#bringing-the-rest-of-a-parallel-batch-up-to-date](references/recovery.md#bringing-the-rest-of-a-parallel-batch-up-to-date).
A conflict either way means the grouping call was wrong for that pair:
[recovery.md#a-merge-conflict](references/recovery.md#a-merge-conflict). Only
when the whole batch has merged does the run re-plan and group the next batch.

### 8. Close out the findings the run turned up

Every run surfaces defects outside the issue being shipped — returned under
`SCOPE-NOTES`, `OUT-OF-SCOPE`, or `FOLLOW-UPS`. Three outcomes, in this order of
preference:

1. **fix it in the diff already open** — when it is the same behavior change the
   issue is about and the issue's own tests (or one added beside them) cover it;
2. **file it and ship it in this same run**
   ([step 8c](#8c-take-the-runs-own-output-back-into-the-queue)) — when it is a
   separate change but nothing about it is undecided;
3. **file it and leave it** — only when it needs a product call, depends on
   something still open, is its own batch of work, or the run is out of budget.

"Out of scope for this diff" is not "out of scope for this run": most of what an
implementation run declines belongs in outcome 2, not 3.
[references/filing-followups.md](references/filing-followups.md) settles which —
**read it before filing anything**.

```bash
python3 {SKILL_DIR}/scripts/file_followup.py \
    --title "<repo's title convention>" --body-file <path> \
    --tier P2 --area <area> --touches <paths> --label <area label> \
    --found-while <n> [--needs-design]
```

`--tier` is required, per [priority-rubric.md](references/priority-rubric.md),
even with `--needs-design` — the moment the design is decided the issue must
already rank correctly. `--area` and `--touches` become the issue's ship
contract, which is what lets a later run group it without judgement; give
`--touches` the paths the fix will actually land in, or `*` if you genuinely
cannot say. Add `--needs-design` only when the finding is an open design
question rather than a verified fix.

Exit 2 (`NO_WRITE_ACCESS`) means report the finding in step 10 instead. File as
you go, right after the PR that surfaced it lands; record (`--event followup`),
and pass `--refresh` on the next plan so the new issue is in the ranking.

### 8b. Unblock held designs in the background

Everything filed `--needs-design` just now, plus the design-blocked issues
already in the backlog (step 1's `needs-design:` line), gets one **`opus`**
sub-agent each, filled from
[delegation-templates.md#design-decision-step-8b](references/delegation-templates.md#design-decision-step-8b).

**Spawn and move on — never block on one.** They run in the background while
this session keeps shipping, and the Agent tool notifies this session as each
returns. The rules:

- One agent per issue, always `opus`, all of a round issued **in one message**.
  Cap **3 in flight**; queue the rest behind them — this run's own filings
  first, then backlog issues highest tier first.
- Spawn this run's filings as soon as `file_followup.py` returns their numbers.
  Sweep the backlog's held designs **once per run**, right after step 1 rather
  than at step 8: the `needs-design:` line is in hand from the first call, so
  those agents get the whole run to finish in. Never sweep again after every
  issue shipped.
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

Before cleanup, re-plan (`plan.py --mode <same> --refresh
--allow-existing-worktrees`) and keep going
through **what this run produced**: the follow-ups filed at step 8 and the issues
step 8b unblocked. Each runs the same steps 3–8 as any other issue, one PR at a
time.

Take one on only when all three hold:

1. **Depth 1** — it came from *this* run's own work. A follow-up filed while
   shipping a follow-up is recorded and left for the next run; that is what stops
   a run from chasing its own tail.
2. **Shippable on the ordinary gate**
   ([dependency-triage.md#readiness-gate](references/dependency-triage.md#readiness-gate))
   — design settled, nothing open it depends on, one coherent scope. A `DEFERRED`
   design is not shippable.
3. **Budget left** ([cost-discipline.md#run-budget](references/cost-discipline.md#run-budget)).
   Out of budget, or a background design still in flight once everything else is
   done → stop and name it in the report rather than waiting on it.

In `all` mode these simply join the existing queue, ordered the same way, with no
privilege over the backlog's own issues. With no argument or an explicit issue
number, this step is the *only* thing that extends the run past its first merge.

### 9. Clean up — once, after the last merge, script only

**Once means once.** Every deletion this run makes happens here, in a single
`cleanup_run.sh` call, including when a batch finished long ago — an
intermediate call to free the worktree cap costs another approval prompt and
buys only disk, which is the cheaper resource. `rm` is never used anywhere in
the run, on repository content or on a throwaway fixture under the scratchpad;
[closing-out.md](references/closing-out.md#cleanup-scope) has the reasoning and
what to do instead.

Step 7 already leaves `HEAD` on the up-to-date default branch, which is a
precondition for the branch deletion below (it refuses to delete whatever is
currently checked out — in the main checkout *or* in a surviving worktree):

```bash
{SKILL_DIR}/scripts/cleanup_run.sh [--remote] [--dry-run] \
    [--worktree-root <runstate>/worktrees] [--merged-only] [--force]
```

Pass `--worktree-root` only when this run created worktrees; without it the
worktree pass is skipped, which is right for a serial run. Anything gitignored
inside a worktree is lost with it —
[recovery.md#a-worktree-that-will-not-go-away](references/recovery.md#a-worktree-that-will-not-go-away).

Scope: [references/closing-out.md#cleanup-scope](references/closing-out.md#cleanup-scope)
— record the cleanup outcome (`--event cleanup ...`).

If this run proved the repo worktree-viable (or proved it is not), persist that
so the next run's plan skips the probe:

```bash
{SKILL_DIR}/scripts/preflight.sh --profile-cache <runstate>/repo-profile.json \
    --set-worktree-viable <yes|no>
```

### 10. Report

Shape: [references/closing-out.md#report-shape](references/closing-out.md#report-shape)
— selection rationale, per-issue outcomes, follow-ups filed (and what was fixed
inline instead of filed) and checked but not filed, designs decided or `DEFERRED`
by step 8b, then what was left undone. A `DEFERRED` design's open question is the
one thing in the report the user has to answer. Flag any issue left open behind a
merged PR explicitly — that is the failure mode this skill exists to prevent.

Name any acceptance criterion that shipped `not-met` and why it was accepted —
if none did, say the criteria were met, and if the issue had none, say that
instead of implying it passed a check it never carried.

Add one line when it applies: **issues whose ship contract had to be guessed at**
— the `PARTIAL` grouping's undeclared issues from step 2c, and anything
`issue_digest.py --audit` flagged. That list is what stops the next run over this
backlog from paying the same judgement cost twice.

## Cost discipline

What belongs in this context versus a sub-agent's, the per-issue run budget, why
the model and effort assignments are what they are, and what parallel mode
actually costs versus what it saves:
[references/cost-discipline.md](references/cost-discipline.md).

## Recovery

Everything that can go sideways between step 3 and step 7 — a sub-agent that
returned without its report, a red baseline, a CI failure, a merge conflict, a
repo that will not survive a worktree:
[references/recovery.md](references/recovery.md).

## Stop conditions

Stop the whole run and report when: the plan is `BLOCKED`, a dependency cycle
needs a human to break it, a merge conflict needs a product decision, or the same
CI failure survives the retry ceiling on two different issues.

Also stop on **a change in the repository that this run did not make** — the main
checkout dirty with files no step here touched, a branch moved underneath you,
main ahead of what the last merge left, or a linked worktree under this run's
root that this run did not create. Someone else is working in the same tree.
Prove it is not yours before concluding it (compare the actual hunks against what
your own branches and worktrees hold; "it edits a file my issue also edits" is
not proof either way), then leave it exactly as found — no stash, no restore, no
commit — and ask. Their uncommitted work is unrecoverable if you discard it, and
a gate failing on their half-finished edit is not yours to fix. Record it before
stopping (`--event blocked --field reason=<what stopped it>`).

In `all` mode, a single failed issue does not stop the run — mark it FAILED,
record it the same way, skip anything that depended on it, and continue.

A background design agent returning `DEFERRED` (step 8b) is **not** a stop
either, in any mode: its issue stays blocked, its open question goes in the
report, and the run carries on with everything else. The only design that stops a
run is one blocking the issue currently being implemented, at step 2b.
