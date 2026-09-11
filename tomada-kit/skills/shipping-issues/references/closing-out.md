# Closing out: cleanup and report

Read at step 9 (cleanup) and step 10 (report) — everything past the ordering
and safety rules the SKILL.md body already states inline.

## Table of Contents

- [Cleanup scope](#cleanup-scope)
- [What the report must not omit](#what-the-report-must-not-omit)

## Cleanup scope

```bash
${CLAUDE_SKILL_DIR}/scripts/cleanup_run.sh [--remote] [--dry-run] \
    [--worktree-root <runstate>/worktrees] [--merged-only] [--force]
```

All deletion goes through `cleanup_run.sh`, in **one batch after the last
merge** — not once per batch. Never run `rm`, `git worktree remove`, or
`git branch -D` ad hoc in the main context or in a sub-agent — raw `rm` is
flagged as dangerous and stalls the run on a permission prompt, and the single
entry point is what lets deletion be gated on merge status.

**That covers temporary files too, not just the repository.** A throwaway
fixture, a scratch clone, a probe directory under the session scratchpad or
`/tmp` is left exactly where it is: it costs nothing, it is disposable by
construction, and `rm -rf`-ing it buys a permission prompt that interrupts the
run for no gain. Revert a probe *inside* a checkout with `git checkout --` or
by moving it out with `mv`, never with `rm`. Say in the step 10 report where
any leftover scratch directories are, and let the user delete them if they
care. Every sub-agent prompt that has a sub-agent create a fixture must carry
this prohibition explicitly — three separate agents in one observed run
reached for `rm` on their own scratch directories despite the instruction
being implied rather than stated.

Deleting worktrees mid-run to stay under the concurrency cap is the one
tempting exception, and it is not worth it: each intermediate call is another
approval, and the disk a few worktrees hold is cheap next to interrupting a
long unattended run. Carry them to the end and clean once. If disk genuinely
is the constraint, that is a reason to shrink the batch, not to add cleanup
calls. The script touches only: worktrees under an
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

## What the report must not omit

**There is no prescribed report format.** Shape, order and headings are yours —
write the report the run actually needs. What is fixed is the list below: each
line is a fact whose absence changes what the reader believes happened, so
omitting one is a defect, not a stylistic choice.

- **Any issue left open behind a merged PR.** This is the failure mode the skill
  exists to prevent; it can never be implied, only stated.
- **Any issue that shipped without a clean `/code-review` pass** — reviewed by
  the fallback agent, or carrying a `REJECTED` finding this session did not
  resolve. A run that shipped unreviewed must not read like one that passed.
  Never present re-reading your own diff as a review. (A branch `/code-review`
  reviewed and a fix sub-agent repaired *did* pass the default review and needs
  no flag.)
- **Acceptance criteria that shipped `not-met`, and why that was accepted.** If
  none did, say the criteria were met. If the issue carried none, say that —
  rather than implying it passed a check it never had.
- **Every `DEFERRED` design's open question**, phrased as the question. These
  are the only part of the report the user has to act on.
- **Follow-ups filed**, what was fixed *inline* instead of filed (an unexplained
  widened diff is indistinguishable from scope creep), and findings checked and
  deliberately *not* filed with what prevented each — a verified non-issue is a
  result, and silence reads as "nothing was noticed".
- **Light issues left for the lighter runner** — every number on a
  `deferred-light:` line, the backlog's and this run's own filings alike, so
  the reader knows they were routed rather than overlooked.
- **Operator actions** the run surfaced — things resolved by running a command
  or changing a setting rather than by a PR. The backlog will never show them,
  so the report is their only record.
- **A serial fallback when parallel was expected**, and which gate failed.
  Otherwise a repository that could not support worktrees reads as a slow run.
- **The verification command actually used**, when the plan's suggestion was
  overridden.
- **Issues whose ship contract had to be guessed at** — the `PARTIAL` grouping's
  undeclared issues and anything `issue_digest.py --audit` flagged. This is what
  stops the next run paying the same judgement cost.
- **What was left undone, with the specific reason each** — blocked, needing
  clarification, hit the retry ceiling, still held for `blocked: design`, or a
  design agent still queued or in flight. An issue whose design this run decided
  but whose implementation it did not reach is **ready**, not blocked: it is the
  next run's first candidate, and that is a different thing from being stuck.
