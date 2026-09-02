# Closing out: cleanup and report

Read at step 9 (cleanup) and step 10 (report) — everything past the ordering
and safety rules the SKILL.md body already states inline.

## Table of Contents

- [Cleanup scope](#cleanup-scope)
- [Report shape](#report-shape)

## Cleanup scope

```bash
{SKILL_DIR}/scripts/cleanup_run.sh [--remote] [--dry-run] \
    [--worktree-root <runstate>/worktrees] [--merged-only] [--force]
```

All deletion goes through `cleanup_run.sh`, in one batch after the last merge.
Never run `rm`, `git worktree remove`, or `git branch -D` ad hoc in the main
context or in a sub-agent — raw `rm` is flagged as dangerous and stalls the
run on a permission prompt, and the single entry point is what lets deletion
be gated on merge status. The script touches only: worktrees under an
explicitly given `--worktree-root`; harness `worktree-agent-*` branches (a
leftover branch-naming convention from the Claude Code harness — a different
thing from this skill's own worktrees, which are never branch-named that way);
and branches whose PR is merged. `--remote` extends the last of those to the
same refs on origin. Nothing this run generated should be sitting uncommitted
in a checkout to begin with: prompts, issue bodies and CI logs all live under
`<runstate>/` (run-record.md).

**The worktree pass runs first, and only when `--worktree-root` is given.** A
branch checked out in a worktree cannot be deleted, so the worktrees have to
go before the branch pass can do its job; a serial run passes no root and the
pass is skipped, which is correct. Two things decide how to call it — the
default removes every worktree under the root including one another session
may be using, and gitignored files inside a worktree are lost with it —
both spelled out in
[worktree-parallelism.md#teardown](worktree-parallelism.md#teardown).

Record the cleanup outcome (`--event cleanup ...`) and report anything it left
`SKIPPED`.

## Report shape

Open with the selection rationale in one line — why this issue was first, by
tier — and, when step 2 wrote labels, one line for that (`labeled 9 issues: 2
P0, 3 P1, …`, straight from the script's summary). Then
per issue: `#N <title> → PR #M → MERGED, issue CLOSED | AUTO-ARMED | FAILED(<why>)
| SKIPPED(<why>)`, plus `REVIEW: DELEGATED` or `REVIEW: UNRESOLVED(<n>)`
whenever step 4 did not run clean on the `/code-review` path — a run that
shipped unreviewed, or reviewed by the fallback rather than `/code-review`
itself, must not read like one that passed the default review. A parallel-mode
branch reviewed by `/code-review` and repaired by the fix sub-agent did pass
the default review and needs no marker; what does need one is a finding that
sub-agent returned under `REJECTED` and this session did not resolve — that is
`REVIEW: UNRESOLVED(<n>)` like any other. Never re-read
your own diff and report that as a review. Flag any issue left open behind a
merged PR explicitly; that is the failure mode this skill exists to prevent.

Then, when step 8 filed anything, one line per follow-up: `filed #N <title>
[tier] — found while shipping #M`. A follow-up this run went on to ship (step
8c) gets its ordinary per-issue outcome line above as well — the filing line
says where it came from, the outcome line says it landed. Also state what the
run fixed *inline* rather than filing, in one line — a widened diff that
nobody mentions is indistinguishable from scope creep on review. And state the
findings you checked and did *not* file, with what prevented them — a verified
non-issue is a result, and silence reads as "nothing was noticed". Operator
actions the run surfaced (resolved by running a command or changing a setting,
not by a PR) get their own lines here — the backlog will never show them, so
the report is their only record.

Then the designs, when step 8b spawned anything: one line each, `design #N:
DECIDED — <approach in a clause>, block cleared` or `design #N: DEFERRED —
<the open question>`. The `DEFERRED` lines are the part of the report the user
actually has to act on, so they go last among these and are phrased as the
question, not as a status. A design still in flight when the run ended is its
own line: it will land on the issue after this report, which is fine, and
saying so is what keeps the label state readable.

When the run used parallel worktrees, one line for that too — which issues
shared a batch and why, or, when step 2c fell back, that it ran serially and
which gate it failed. A run that silently ran serially when the user expected
parallelism reads as a slow run rather than as a repository that could not
support it.

Then list what was left undone — blocked issues, ones needing clarification,
ones that hit the retry ceiling, and ones still held for `blocked: design`
(`needs-design:` from `issue_digest.py --select`, minus whatever step 8b just
cleared) — with the specific reason each. An issue whose design this run
decided but whose implementation it did not reach belongs here too, marked as
ready rather than blocked: it is the next run's first candidate, and that is a
different thing from being stuck.
