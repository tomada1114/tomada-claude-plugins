---
name: shipping-issues
description: "Rank the open GitHub Issues by their `priority: P0`-`P3` labels — backfilling a missing label from whether an issue unblocks others and how far its impact spreads — then implement the top one, review and fix it with `/code-review` before the PR exists, open a PR that auto-closes the issue (Closes #N), watch CI until it is green, merge to main, and confirm the issue actually closed. With no argument it ships only the single highest-priority issue; pass \"all\" to work through every issue in dependency order, one at a time. Implementation and CI repair go to a `sonnet` sub-agent; the calling session judges each result and drives the PR, CI watch, and merge itself. Use when asked to ship the remaining issues, start from the highest-priority issue, implement an issue through to merge, take on the next issue, clear the ticket backlog, work through the open issues, or finish off every issue."
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

## Modes

| Argument | Behavior |
|---|---|
| _(none)_ | Ship exactly one issue — the highest-priority shippable one. Stop after it merges and its issue closes. |
| `all` | Ship every shippable issue, one at a time, in dependency-then-priority order. Each issue runs the full workflow (steps 1–8) to completion before the next one starts. |
| a number, e.g. `42` | Ship that specific issue, after checking nothing it depends on is still open. |

Anything else in the argument is a filter hint (a label, a milestone) — apply
it as `issue_digest.py` flags.

An issue labeled `blocked: design` (or a recognized equivalent — see
[dependency-triage.md](references/dependency-triage.md)) is never picked
automatically, even under `all`. Take it on only by naming its number
explicitly or passing `--include-design`, and only when deciding the design
is itself part of this run — [step 2b](#2b-decide-the-design-before-implementing).

## Working rules

- All work happens in the repo's **main checkout** — this skill never creates
  a git worktree. Sub-agents share that same checkout, so running one issue
  at a time, start to finish, is what keeps two runs from ever touching the
  tree together.
- One issue runs start to finish — branch, implement, review and fix, PR,
  CI, merge, issue closed — before the next one begins. `all` mode is this
  same sequence repeated, never run concurrently.
- Every issue starts from a clean, up-to-date default branch:
  `git switch <default> && git pull --ff-only && git switch -c <type>/<n>-<slug>`.
- After a merge, return to that state before ranking the next issue:
  `git switch <default> && git pull --ff-only`.
- A dirty working tree that this run did not create is never touched
  silently — see [Stop conditions](#stop-conditions).

## Inputs and outputs

Reads: the current repo's open issues and PRs; the project's own
`CLAUDE.md` / `AGENTS.md` for conventions.
Writes: `priority: P0`…`P3` labels, `blocked: design` labels, branches, PRs,
merge commits, issue closures, follow-up issues (step 8), and a run record.
Every file this run generates — the run record, verify/CI logs, filled
prompts — lives under `<runstate>` (used through the rest of this document),
short for
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/shipping-issues/<owner>__<repo>/`,
**never inside the repo checkout**. Full layout and event list:
[references/run-record.md](references/run-record.md). Call the run record
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

`verdict: BLOCKED` stops the run. A dirty tree is a warning — ask first, and
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
`--include-design` only to take one on deliberately.

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

### 2b. Decide the design before implementing

Only when the picked issue carries `blocked: design` (or an equivalent) and
was taken on deliberately, never from the default backlog scan. Settling the
approach, recording it, and clearing the block before step 3:
[dependency-triage.md#deciding-a-held-design](references/dependency-triage.md#deciding-a-held-design).

### 3. Implement

One issue = one branch = one PR, in the main checkout:

```bash
git switch <default_branch> && git pull --ff-only && git switch -c <type>/<n>-<slug>
```

Before spawning the implementation sub-agent, run the project's own
verification command **once, unmodified, on this branch**, redirected to
`<runstate>/verify/<n>-baseline.log` — a red baseline is the repository's
problem, not the issue's, and finding it here costs one command instead of a
wasted implementation run. Read the exit code and the log's tail, never the
full output. What that smoke run turns up goes to step 8.

Fill and spawn a **`sonnet`** sub-agent with
[delegation-templates.md#implementation-step-3](references/delegation-templates.md#implementation-step-3)
— a run that stops before pushing anything → don't retry blindly: read
`git status`/`git log` for what landed, resume naming what's left, or record
`--event blocked`.

**Judge the result in this context, against the issue and step 2b's
decision.** Start from `git diff --stat <base>...HEAD` plus the sub-agent's
own `CHANGED` / `SCOPE-NOTES` / `UNRESOLVED` — open the hunks only in the
files the spec actually touches, not the whole diff by default. If the
implementation is missing part of the spec or quietly widened it, send a new
`sonnet` run naming only what's left; don't re-run the whole task. Up to
**2** resume/patch runs on top of the first — a third miss means the issue
itself is underspecified: record `--event blocked` and report
`NEEDS-CLARIFICATION` in step 10 instead of spawning again. Use the
returned `TEST-PLAN` verbatim later — don't re-derive it.

### 4. Review and fix — judge the result before the PR exists

Run before any PR exists, against the branch:

```
/code-review <effort> <branch> --fix
```

**Effort first, branch second** — an unrecognized first token makes the
*entire* string the target and silently falls back to the last effort used.
Picking `<effort>` from what the diff is: [cost-discipline.md#code-review-effort](references/cost-discipline.md#code-review-effort).
Never `ultra` — it runs in the cloud, is billed, and cannot be launched from
this session.

`--fix` applies its own findings and reports each one `fixed`,
`no_change_needed`, or `skipped`. That inverts the read-only guarantee a
delegated review would otherwise give — **this session reading what `--fix`
changed** is now the safeguard against a misread finding landing unseen:

- **Read `skipped` findings** — a skip is not clean, it means out-of-scope, a
  behavior change, or a false positive. One real but outside this issue's
  scope goes to step 8, not back into this diff.
- **Read only `git diff <impl-commit>..HEAD`**, not the whole branch again.
  Zero findings and zero skips → confirm with `--stat` and move on.
- Revert anything `--fix` got wrong on closer reading.
- Re-run the verification command (redirected as in step 3) only if `--fix`
  changed something; otherwise step 3's verify still holds. Then push.

Host won't let this session launch `/code-review` directly → one independent,
**read-only** `opus` sub-agent against the branch, using
[delegation-templates.md#review-fallback](references/delegation-templates.md#review-fallback),
triaged the same way. Never re-read your own diff and call that a review.

Record: `--event review --field status=<code-review|DELEGATED> --field effort=<low|medium|high> --field findings=<n> --field skipped=<n>`.

### 5. Open the PR

Commits on the branch but nothing pushed → push them from this session.
No commits at all → no branch: record `--event blocked --field issue=<n>`,
report `SKIPPED(<why>)` in step 10, in `all` mode move on.

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
[delegation-templates.md#ci-repair-step-6](references/delegation-templates.md#ci-repair-step-6)
— up to **3 attempts**. `PUSHED: no` ends the loop. A test deleted, skipped,
or weakened to pass, or a "flaky" re-run without diagnosis, is a failed
outcome. `NO_CHECKS` → run the project's own verification command locally and
merge on a local green (no such command → ask first). `verdict: ERROR` →
re-read the actual PR/CI state before treating it as a green.

### 7. Merge and confirm the issue closed

```bash
{SKILL_DIR}/scripts/land_pr.sh <pr> --issue <n>
```

Merge once step 6 reports `verdict: PASS`. Re-checks the closing link,
confirms the issue closed — read `result:` and `issue:`. Six results, one
must never read as success: [landing-outcomes.md](references/landing-outcomes.md).
Record (`--event merged ...`).

Then return to the starting point for the next issue:
`git switch <default_branch> && git pull --ff-only`. `all` mode: re-rank with
`issue_digest.py --select` from there — one script call, not another research
pass — and start the next issue's step 3 from this same up-to-date branch,
without pausing for confirmation in between.

### 8. File the findings the run turned up

Every run surfaces defects outside the issue being shipped — returned under
`SCOPE-NOTES`, `OUT-OF-SCOPE`, or `FOLLOW-UPS`.
[references/filing-followups.md](references/filing-followups.md) settles what
to file, fix inline, or skip — **read it before filing anything**.

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

### 9. Clean up — once, at the end, script only

Step 7 already leaves `HEAD` on the up-to-date default branch, which is a
precondition for the branch deletion below (it refuses to delete whatever is
currently checked out):

```bash
{SKILL_DIR}/scripts/cleanup_run.sh [--remote] [--dry-run]
```

Scope: [references/closing-out.md#cleanup-scope](references/closing-out.md#cleanup-scope)
— record the cleanup outcome (`--event cleanup ...`).

### 10. Report

Shape: [references/closing-out.md#report-shape](references/closing-out.md#report-shape)
— selection rationale, per-issue outcomes, follow-ups filed and checked but
not filed, then what was left undone. Flag any issue left open behind a
merged PR explicitly — that is the failure mode this skill exists to prevent.

## Cost discipline

What belongs in this context versus a sub-agent's, the per-issue run budget,
and why the model and effort assignments are what they are:
[references/cost-discipline.md](references/cost-discipline.md).

## Stop conditions

Stop the whole run and report when: preflight is BLOCKED, a dependency cycle
needs a human to break it, a merge conflict needs a product decision, or the
same CI failure survives the retry ceiling on two different issues.

Also stop on **a change in the repository that this run did not make** — the
main checkout dirty with files no step here touched, a branch moved underneath
you, main ahead of what the last merge left. Someone else is working in the same
tree. Prove it is not yours before concluding it (compare the actual hunks
against what your own branch holds; "it edits a file my issue also edits" is
not proof either way), then leave it exactly as found — no stash, no restore, no
commit — and ask. Their uncommitted work is unrecoverable if you discard it, and
a gate failing on their half-finished edit is not yours to fix. Record it
before stopping (`--event blocked --field reason=<what stopped it>`).

In `all` mode, a single failed issue does not stop the run — mark it FAILED,
record it the same way, skip anything that depended on it, and continue.
