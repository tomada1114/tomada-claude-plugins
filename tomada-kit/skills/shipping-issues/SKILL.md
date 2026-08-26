---
name: shipping-issues
description: "Rank the open GitHub Issues by their `priority: P0`-`P3` labels — backfilling a missing label from whether an issue unblocks others and how far its impact spreads — then implement the top one, open a PR that auto-closes the issue (Closes #N), watch CI until it is green, merge to main, and confirm the issue actually closed. With no argument it ships only the single highest-priority issue; pass \"all\" to work through every issue in dependency order (independent ones in parallel worktrees). Implementation, review, and CI fixes go to Codex runs; issue data and CI watching to scripts, so diffs and logs never enter the main context. Use when asked to ship the remaining issues, start from the highest-priority issue, implement an issue through to merge, take on the next issue, clear the ticket backlog, work through the open issues, or finish off every issue."
argument-hint: "[all | <issue number> | (empty = one issue)]"
metadata:
  platforms: claude-code, codex
---

# Shipping Issues

Take open GitHub issues from open to merged-and-closed: rank priority →
implement → linked PR → CI green → merge → confirm closed. Deterministic `gh`
work lives in `scripts/`, so raw JSON and CI logs never enter the main context.
**Done means all three:** the PR is merged to the default branch, the issue is
CLOSED, and nothing was deleted or weakened to get there.

## Modes

| Argument | Behavior |
|---|---|
| _(none)_ | Ship exactly one issue — the highest-priority shippable one. Stop after it merges and its issue closes. |
| `all` | Ship every shippable issue, in dependency-then-priority order. Independent issues run in parallel worktrees (cap 3). |
| a number, e.g. `42` | Ship that specific issue, after checking nothing it depends on is still open. |

Anything else in the argument is a filter hint (a label, a milestone) — apply
it as `issue_digest.py` flags.

An issue labeled `blocked: design` (or a recognized equivalent — see
[dependency-triage.md](references/dependency-triage.md)) is never picked
automatically, even under `all`. Take it on only by naming its number
explicitly or passing `--include-design`, and only when deciding the design
is itself part of this run — [step 2b](#2b-decide-the-design-before-implementing).

## Inputs and outputs

Reads: the current repo's open issues and PRs via `gh`; the project's own
`CLAUDE.md` / `AGENTS.md` for conventions.
Writes: `priority: P0`…`P3` labels, `blocked: design` labels, branches, PRs,
merge commits, issue closures, follow-up issues (step 9), and a run record — layout, events, why
nothing lives inside a worktree: [references/run-record.md](references/run-record.md).
Call it right after each event happens, not batched at the end:

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

`verdict: BLOCKED` stops the run. A dirty tree is a warning — ask first.
`check`'s result decides steps 3/6/7's route once, here — fallback ladders:
[platform-notes.md](references/platform-notes.md). Open the run record:
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
  to an independent `sonnet` worker where delegation is available, else read
  it and run its steps inline. Returns the pick with evidence, parallel-safe
  groups, and blocked/unclear lists — never raw issue prose.

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

### The Codex pattern (steps 3, 6, 7)

Fill the matching generic template from
`{CODEX_SKILL_DIR}/references/delegation-templates.md` — per-step fill table:
[delegation-templates.md](references/delegation-templates.md) — write it to
`<runstate>/prompts/<n>-<step>.md`, and run `{CODEX_SKILL_DIR}/scripts/codex_run.sh
task [--write] --cwd <worktree> --prompt-file <path>` (`--write` for 3 and 7;
6 omits it — read-only, which is what makes it a genuine review). Codex
cannot ask a question back — leave nothing merge-gating unguessed.
`codex_touched:` is not the file list; `git -C <worktree> status --short` is.
No usable Codex → fallback ladders: [platform-notes.md](references/platform-notes.md).

### 3. Implement

One issue = one branch = one PR, under the worktree root step 10 cleans:

```bash
git -C <repo> worktree add <repo>/.claude/worktrees/<n> -b <type>/<n>-<slug> <default_branch>
```

Single mode: the main checkout may serve as `<worktree>`.

A fresh worktree is not a build environment: it has no `node_modules`, no
`vendor/`, no `.venv`, so the verification command the run is told to pass fails
before it reads a line of code. Install into each worktree from the parent
first, and run the project's own verification command there **once, unmodified,
before any prompt is issued** — a red baseline is the repository's problem, not
the issue's, and finding it here costs one command instead of three
implementation runs. What that smoke run turns up goes to step 9.

Fill/run:
[delegation-templates.md#implementation-step-3](references/delegation-templates.md#implementation-step-3)
— `--cwd` isolates each worktree, so a parallel batch (cap 3, see Modes) is
issued together; serialize everything else. `codex_status:` non-zero → don't
retry blindly: read `git status`/`git log` for what landed, resume naming
what's left, or record `--event blocked`.

A `VERIFY: ... -> fail` is not automatically the code's fault. The sandbox has
no network, so any step that reaches a registry, a proxy, or a remote fails
inside it and would pass outside — re-run that step yourself before treating it
as a defect, and say in the PR which of the two you saw.

### 4. Open the PR

`PUSHED: no` is read against `git -C <worktree> log <base>..HEAD`, never on its
own: a Codex sandbox has no network, so a run that did everything right still
returns `PUSHED: no` with its commits sitting in the worktree. Commits present
→ push them from the parent and carry on. No commits, or only `UNRESOLVED` →
no branch: record `--event blocked --field issue=<n>`, report `SKIPPED(<why>)`
in step 11, in `all` mode move on.

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

Decides whether this run actually closes anything. `--fix` appends a missing
`Closes #N`. `WRONG_BASE` → retarget (`gh pr edit <pr> --base <default>`)
before merging.

### 6. Review before CI

Fill/run:
[delegation-templates.md#review-step-6](references/delegation-templates.md#review-step-6),
against the worktree, after the PR and before CI. Heavy diff (schema, storage
layer, public contract, new/bumped dependency, cross-module rewire) → add the
adversarial pass from the same reference, issued alongside Review.

Apply findings, commit (`review: <what was fixed>`), push, re-run
verification so CI judges the reviewed code. Fix the cause, never the check —
then record (`--event review --field pr=<n> --field status=<...> --field
intent_match=<yes|no> --field unresolved=<count>`).

### 7. CI to green

```bash
# The checks API still serves the PREVIOUS commit's results for a minute or two
# after a push, so a watch started too early returns that run's verdict — a
# stale PASS is worse than a stale FAIL. Wait for the new head to appear first.
head=$(gh pr view <pr> --json headRefOid -q .headRefOid)
until gh run list --branch <branch> --limit 8 --json headSha -q '.[].headSha' | grep -q "${head:0:7}"; do sleep 15; done
{SKILL_DIR}/scripts/ci_watch.sh <pr> --timeout 1800 > <runstate>/ci/<pr>.log
grep -E '^(verdict|mergeable|merge_state|review_decision):' <runstate>/ci/<pr>.log
```

Redirected — raw output carries failing-run log tails that must stay out of
this context. One watch per PR; keep `failed_checks:` for repair. This is the
run's only wait primitive — never a hand-rolled sleep/poll loop. `all` mode:
watch several PRs concurrently. Record (`--event ci --field pr=<n> --field
verdict=<...>`).

On `FAIL`, fill/run:
[delegation-templates.md#ci-repair-step-7-only-on-fail](references/delegation-templates.md#ci-repair-step-7-only-on-fail)
— up to **3 attempts**. `PUSHED: no` ends the loop. A test deleted, skipped,
or weakened to pass, or a "flaky" re-run without diagnosis, is a failed
outcome. `NO_CHECKS` → run the project's own verification command locally and
merge on a local green (no such command → ask first). `verdict: ERROR` →
re-read with `gh`, not a green.

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
(`NO_WRITE_ACCESS`) means report the finding in step 11 instead. File as you
go, right after the PR that surfaced it lands; record (`--event followup`).

### 10. Clean up — once, at the end, script only

The main worktree's `HEAD` may still be on the last-implemented branch, and
cleanup refuses to delete a branch checked out there — switch back to the
default branch, fast-forwarded, **before** cleanup runs:

```bash
git switch <default> && git pull --ff-only
{SKILL_DIR}/scripts/cleanup_run.sh [--remote] [--dry-run] [--merged-only]
```

Scope, `--merged-only` semantics, and the worktree-cost argument:
[references/closing-out.md#cleanup-scope](references/closing-out.md#cleanup-scope)
— record the cleanup outcome (`--event cleanup ...`).

### 11. Report

Shape: [references/closing-out.md#report-shape](references/closing-out.md#report-shape)
— selection rationale, per-issue outcomes, follow-ups filed and checked but
not filed, then what was left undone. Flag any issue left open behind a
merged PR explicitly — that is the failure mode this skill exists to prevent.

## Cost discipline

What belongs in this context versus a delegated run, the per-issue Codex-run
budget, and why the model assignments are what they are:
[references/cost-discipline.md](references/cost-discipline.md).

## Stop conditions

Stop the whole run and report when: preflight is BLOCKED, a dependency cycle
needs a human to break it, a merge conflict needs a product decision, or the
same CI failure survives the retry ceiling on two different issues.

Also stop on **a change in the repository that this run did not make** — the
main checkout dirty with files no step here touched, a branch moved underneath
you, main ahead of what the last merge left. Someone else is working in the same
tree. Prove it is not yours before concluding it (compare the actual hunks
against what your own worktrees hold; "it edits a file my issue also edits" is
not proof either way), then leave it exactly as found — no stash, no restore, no
commit — and ask. Their uncommitted work is unrecoverable if you discard it, and
a gate failing on their half-finished edit is not yours to fix. Record it
before stopping (`--event blocked --field reason=<what stopped it>`).

In `all` mode, a single failed issue does not stop the run — mark it FAILED,
record it the same way, skip anything that depended on it, and continue.

## Platform notes

Codex-runtime constraints for this skill, the fallback ladders when no usable
Codex is present, and the best-effort degradations:
[references/platform-notes.md](references/platform-notes.md).
