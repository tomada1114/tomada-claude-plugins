---
name: shipping-issues
description: "Rank the open GitHub Issues by their `priority: P0`-`P3` labels — backfilling a missing label from whether an issue unblocks others and how far its impact spreads — then implement the top one, open a PR that auto-closes the issue (Closes #N), watch CI until it is green, merge to main, and confirm the issue actually closed. With no argument it ships only the single highest-priority issue; pass \"all\" to work through every issue in dependency order (independent ones in parallel worktrees). Implementation, review, and CI fixes go to Codex runs; issue data and CI watching to scripts, so diffs and logs never enter the main context. Use when asked to ship the remaining issues, start from the highest-priority issue, implement an issue through to merge, take on the next issue, clear the ticket backlog, work through the open issues, or finish off every issue."
argument-hint: "[all | <issue number> | (empty = one issue)]"
metadata:
  platforms: claude-code, codex
---

# Shipping Issues

Take open GitHub issues from "still open" to "merged into the default branch,
issue closed": research priority → implement → linked PR → CI green → merge →
confirm closed. Deterministic `gh` work lives in `scripts/`, so raw JSON and CI
logs never enter the main context.

**Done means all three:** the PR is merged into the default branch, the issue is
CLOSED, and nothing was deleted or weakened to get there. A merged PR that left
its issue open is not done.

## Modes

| Argument | Behavior |
|---|---|
| _(none)_ | Ship exactly one issue — the highest-priority shippable one. Stop after it merges and its issue closes. |
| `all` | Ship every shippable issue, in dependency-then-priority order. Independent issues run in parallel worktrees (cap 3). |
| a number, e.g. `42` | Ship that specific issue, after checking nothing it depends on is still open. |

Anything else in the argument is a filter hint (a label, a milestone, "only my
own issues") — apply it as `issue_digest.py` flags.

## Inputs and outputs

Reads: the current repo's open issues and PRs via `gh`; the project's own
`CLAUDE.md` / `AGENTS.md` for conventions.

Writes: `priority: P0`…`P3` labels, branches, PRs, merge commits, issue
closures, follow-up issues for defects found along the way (step 9), and a
run record — layout, events, why nothing lives inside a worktree:
[references/run-record.md](references/run-record.md). Call it right after each
event happens, not batched at the end:

```bash
python3 {SKILL_DIR}/scripts/run_record.py --repo <owner>/<repo> --event <kind> \
    [--field k=v ...] [--body-file <path>]
```

## Workflow

### 0. Preflight

`{SKILL_DIR}` is this skill's own absolute path, substituted by the caller;
`{CODEX_SKILL_DIR}` is the sibling **`delegating-to-codex`** skill's directory.

**Requires:** `gh` (authenticated), `git`, `python3`, `delegating-to-codex`.
Optional: Codex CLI (+ Node) for steps 3/6/7; `coreutils` for `gtimeout`.

```bash
{SKILL_DIR}/scripts/preflight.sh
{CODEX_SKILL_DIR}/scripts/codex_run.sh check
```

`verdict: BLOCKED` stops the run. A dirty tree is a warning — ask before
creating any branch. Note `default_branch` and `branch_protection` (step 8
needs both). `codex_run.sh check` decides steps 3/6/7's route — settle it
once, here; fallback ladders: [platform-notes.md](references/platform-notes.md).

Open the run record: `{SKILL_DIR}/scripts/run_record.py --event run-start
--field mode=<single|all>`.

### 1. Rank — by label, not by re-reading the backlog

```bash
python3 {SKILL_DIR}/scripts/issue_digest.py --select [--label L] [--assignee A]
```

Priority is a `priority: P0`…`P3` GitHub label; `--select` prints coverage,
the pick, and what's held back. Tier is the primary sort key; the heuristic
score only orders *within* a tier; a BLOCKED issue is never selected.

- `labels: N/N COMPLETE`, no `(~Pn)` on top rows — already ranked. **Skip step 2.**
- anything else, or a `P2(~P0)` marker — go to step 2 once; later runs get the
  cheap path.

Full picture (`BLOCKED-BY`/`UNBLOCKS`/`HAS-OPEN-PR`): drop `--select` (add
`--body-chars 0`) or use `--rank-only`.

### 2. Label the unlabeled — once, not per caller

- **≤3 unlabeled/mis-tiered** — read them (`issue_digest.py --issue N --issue
  M`) against the rubric, then:
  ```bash
  python3 {SKILL_DIR}/scripts/apply_priority_labels.py --backfill --set N=P0 --quiet
  ```
- **more, tangled edges, or a close top-two** — hand
  [references/agents/priority-research.md](references/agents/priority-research.md)
  to an independent `sonnet` worker where delegation is available, else read
  it and run its steps inline. Returns the pick with evidence, parallel-safe
  groups, and blocked/unclear lists — never issue prose or the raw digest.

`--backfill` writes suggested tiers to every unlabeled issue; `--set`
overrides ones judged differently. Run without asking. Exit 2
(`NO_WRITE_ACCESS`) → rank from `~Pn` suggestions instead.

Rank order and override rules: [priority-rubric.md](references/priority-rubric.md).
Readiness gate: [dependency-triage.md](references/dependency-triage.md).

Re-run `--select`, record `--event labels` then `--event selection` (rubric
block via `--body-file`). **Proceed without asking** unless the top two are
genuinely tied on every axis, or the pick needs a product decision first.

### The Codex pattern (steps 3, 6, 7)

Fill the matching generic template from
`{CODEX_SKILL_DIR}/references/delegation-templates.md` with this skill's
delta — fill table per step:
[delegation-templates.md](references/delegation-templates.md) — write it to
`<runstate>/prompts/<n>-<step>.md`, and run:

```bash
{CODEX_SKILL_DIR}/scripts/codex_run.sh task [--write] --cwd <worktree> --prompt-file <path>
```

`--write` for 3 and 7; 6 omits it (read-only = a genuine review). Codex
cannot ask a question back — leave nothing merge-gating to guess.
`codex_touched:` is not the file list; `git -C <worktree> status --short` is.
No usable Codex → fallback ladders: [platform-notes.md](references/platform-notes.md).

### 3. Implement

One issue = one branch = one PR, under the worktree root step 10 cleans:

```bash
git -C <repo> worktree add <repo>/.claude/worktrees/<n> -b <type>/<n>-<slug> <default_branch>
```

Single mode: the main checkout may serve as `<worktree>`. Fill/run the
Implementation template:
[delegation-templates.md](references/delegation-templates.md#implementation-step-3).
Scope is **branch to pushed commits** — PR, link check, CI, merge stay here
(why: [cost-discipline.md](references/cost-discipline.md#why-the-split-is-where-it-is)).
`--cwd` isolates each worktree, so a parallel batch (cap 3) is one worktree +
one Codex run per issue, issued together; serialize everything else.

`codex_status:` non-zero → don't retry blindly: read `git status`/`git log`
for what landed, resume naming what's left, or record `--event blocked`.

### 4. Open the PR

`PUSHED: no` (or only `UNRESOLVED`) → no branch: record `--event blocked
--field issue=<n>`, report `SKIPPED(<why>)` in step 11, in `all` mode move on.

```bash
gh pr create --base <default_branch> --head <branch> --title <PR-TITLE> --body <...>
```

Body must start with **`Closes #N`** after the summary (a bare `#N` closes
nothing), and target the **default branch** (auto-close only fires there) —
build from `PR-SUMMARY`, `Closes #N`, `TEST-PLAN`. Record it (`--event
pr-created --field issue=<n> --field pr=<url>`) before CI.

### 5. Verify the auto-close link

```bash
{SKILL_DIR}/scripts/link_check.sh <pr> --issue <n> --fix
```

The one check deciding whether this run actually closes anything. `--fix`
appends a missing `Closes #N`. `WRONG_BASE` → retarget (`gh pr edit <pr>
--base <default>`) before merging.

### 6. Review before CI

Fill/run the Review template:
[delegation-templates.md](references/delegation-templates.md#review-step-6),
against the worktree, after the PR and before CI. Heavy diff (schema, storage
layer, public contract, new/bumped dependency, cross-module rewire) → add the
adversarial pass from the same reference, issued alongside Review.

Apply findings in the worktree, commit (`review: <what was fixed>`), push,
re-run verification so CI judges the reviewed code. Fix the cause, never the
check. Record (`--event review --field pr=<n> --field status=<...> --field
intent_match=<yes|no> --field unresolved=<count>`).

### 7. CI to green

```bash
{SKILL_DIR}/scripts/ci_watch.sh <pr> --timeout 1800 > <runstate>/ci/<pr>.log
grep -E '^(verdict|mergeable|merge_state|review_decision):' <runstate>/ci/<pr>.log
```

Redirected — raw output carries failing-run log tails that must not enter
this context. One watch per PR; keep `failed_checks:` for repair. This is the
run's only wait primitive — never a hand-rolled sleep/poll loop. `all` mode:
watch several PRs concurrently. Record (`--event ci --field pr=<n> --field
verdict=<...>`).

On `FAIL`, fill/run the CI repair template:
[delegation-templates.md](references/delegation-templates.md#ci-repair-step-7-only-on-fail)
— up to **3 attempts**. `PUSHED: no` ends the loop. A test deleted, skipped,
or weakened to pass, or a "flaky" re-run without diagnosis, is a failed
outcome.

`NO_CHECKS` → run the project's own verification command locally and merge on
a local green (no such command → ask first). `verdict: ERROR` → re-read with
`gh`, not a green.

### 8. Merge and confirm the issue closed

```bash
{SKILL_DIR}/scripts/land_pr.sh <pr> --issue <n>
```

Merge once step 7 reports `verdict: PASS`. Re-checks the closing link,
confirms the issue closed — read `result:` and `issue:`. Six results, one
must never read as success: [landing-outcomes.md](references/landing-outcomes.md).

Record (`--event merged ...`). `all` mode: rebase in-flight branches onto the
updated default branch after each merge, and re-rank with `issue_digest.py
--select` — one script call, not another research pass.

### 9. File the findings the run turned up

Every run surfaces defects that are not the issue being shipped — returned
under `SCOPE-NOTES`, `OUT-OF-SCOPE`, or `FOLLOW-UPS`. Fixing one inline
silently widens a PR about to auto-merge; saying it only in the final report
loses it when the conversation ends.
[references/filing-followups.md](references/filing-followups.md) settles what
to file, fix inline, or skip — **read it before filing anything**.

```bash
python3 {SKILL_DIR}/scripts/file_followup.py \
    --title "<repo's title convention>" --body-file <path> \
    --tier P2 --label <area label> --found-while <n>
```

`--tier` is required, per
[priority-rubric.md](references/priority-rubric.md). Exit 2
(`NO_WRITE_ACCESS`) means report the finding in step 11 instead. File as you
go, right after the PR that surfaced it lands; record it (`--event followup`)
as it happens.

### 10. Clean up — once, at the end, script only

The main worktree's `HEAD` is still on whatever branch was last implemented,
and cleanup refuses to delete a branch checked out there — switch back to the
default branch, fast-forwarded, **before** cleanup runs:

```bash
git switch <default> && git pull --ff-only
{SKILL_DIR}/scripts/cleanup_run.sh [--remote] [--dry-run] [--merged-only]
```

Scope, `--merged-only` semantics, and the worktree-cost argument:
[references/closing-out.md](references/closing-out.md#cleanup-scope). Record
the cleanup outcome (`--event cleanup ...`).

### 11. Report

Report shape: [references/closing-out.md](references/closing-out.md#report-shape).
Open with the selection rationale, then per-issue outcomes, then follow-ups
filed and findings checked but not filed, then what was left undone. Flag any
issue left open behind a merged PR explicitly — that is the failure mode this
skill exists to prevent.

## Cost discipline

What belongs in this context versus a delegated run, the per-issue Codex-run
budget, and why the model assignments are what they are:
[references/cost-discipline.md](references/cost-discipline.md).

## Stop conditions

Stop the whole run and report when: preflight is BLOCKED, a dependency cycle
needs a human to break it, a merge conflict requires a product decision, or the
same CI failure survives the retry ceiling on two different issues (the problem
is the base branch, not the change). Record it before stopping (`--event
blocked --field reason=<what stopped it>`).

In `all` mode, a single failed issue does not stop the run — mark it FAILED,
record it the same way, skip anything that depended on it, and continue.

## Platform notes

Codex-runtime constraints for this skill, the fallback ladders when no usable
Codex is present, and the best-effort degradations:
[references/platform-notes.md](references/platform-notes.md).
