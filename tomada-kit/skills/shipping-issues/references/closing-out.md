# Closing out: cleanup and report

Read at step 9 (cleanup) and step 10 (report) — everything past the ordering
and safety rules the SKILL.md body already states inline.

## Table of Contents

- [Cleanup scope](#cleanup-scope)
- [Approval-gated commands](#approval-gated-commands)
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
by moving it out with `mv` into the holding area
([below](#approval-gated-commands)), never with `rm`. Say in the step 10
report where any leftover scratch directories are; the holding area is offered
for deletion in the final confirmation, a scratchpad left in place is the
user's to delete if they care. Every sub-agent prompt that has a sub-agent create a fixture must carry
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

## Approval-gated commands

The user's permission settings put some commands behind an approval prompt
(`permissions.ask` in `settings.json` — in practice the `rm -rf` family, and
sometimes `wget` or a publish command). This skill runs unattended, so every
such prompt raised mid-run parks the whole run until someone answers it, and
several of them turn an unattended run into one the user has to sit through.
The rule is not "never need approval" — it is **ask once, at the end, for
everything that could wait**. Check each such command against three questions,
in order:

1. **Is there an equivalent that raises no prompt?** Take it. Above all:
   **`mv` into the holding area instead of deleting.** A move needs no
   approval, is instant on the same filesystem, and doubles as a backup — the
   content is still there if the change turns out to be wrong. `curl` instead
   of `wget`; `git checkout -- <path>` instead of deleting a probe edit.
2. **Can it wait until the last merge?** Most can: clearing a scratch
   directory, a stale build output, a throwaway fixture, a leftover clone —
   nothing the issue's result depends on. Move it to the holding area, or, when
   moving is not the equivalent (a non-deletion command), append the exact
   command and why to `<runstate>/deferred.md`. Both are offered together in
   [the final confirmation](#the-final-confirmation).
3. **Does the issue's goal require it now?** Then it may run mid-run — an issue
   whose acceptance criterion *is* removing an existing directory, say. Even
   then, reach for step 1 first: moving the directory into the holding area
   achieves the same working-tree result with no prompt and a copy kept. For
   tracked content, `git rm -r <dir>` is equally prompt-free and the commit
   history is the backup; `mv` is for what git does not hold (untracked or
   gitignored content, generated trees, local data). Only a case neither covers
   — the content is too large to keep, or lives where a move cannot reach —
   takes the prompt mid-run, and the step 10 report says why.

**The holding area** is `<runstate>/holding/<n>/` — `<n>` the issue being
worked, `run` for anything not tied to one. It sits outside every checkout, so
a moved-out directory never reads as untracked content (the reason
`<runstate>` exists — [run-record.md](run-record.md)). Keep the original's
relative path under it (`holding/42/packages/legacy-cli/`) so the report can
name what came from where; on a name collision add a suffix rather than
overwrite. A move across filesystems is a copy-then-delete — fine for a
fixture, slow for `node_modules`; keep holding for what the run actually needs
out of the way. **Never move anything this run did not create or the issue did
not name** — the holding area is not a way to clear someone else's untracked
work out of a dirty tree; that is a [stop condition](../SKILL.md#stop-conditions).

Sub-agents follow the same rule and are handed the path as `{holding_dir}`
([delegation-templates.md](delegation-templates.md#standing-prohibitions-for-every-spawn));
their reports name what they moved there.

### The final confirmation

After `cleanup_run.sh` and after the step 10 report text, as the run's last
tool call: one command covering every holding directory this run filled plus
anything in `deferred.md` — e.g. `rm -rf <runstate>/holding/42
<runstate>/holding/57` — so the user answers one prompt, not one per issue.
List exactly what it covers in the report just above it (each held path with
its original location, each deferred command with its reason), so the user
approves something they can see. Delete only this run's holding directories,
never `<runstate>/holding/` wholesale — an earlier run's holdings are the user's
to decide on.

Declined, or the host refuses the call → leave everything where it is. The
report already names the paths; that is the complete outcome, not a failure to
retry. Nothing that has to happen for the PRs to count as shipped may be
deferred here — the merges and issue closures are already done by now.

## What the report must not omit

**There is no prescribed report format.** Shape, order and headings are yours —
write the report the run actually needs. What is fixed is the list below: each
line is a fact whose absence changes what the reader believes happened, so
omitting one is a defect, not a stylistic choice.

- **Any issue left open behind a merged PR.** This is the failure mode the skill
  exists to prevent; it can never be implied, only stated.
- **How each merged PR was reviewed** — the local `/code-review` pass (effort
  used, findings, what was fixed vs. rejected) or the fallback agent — and any
  `REJECTED` finding this session did not resolve. A run that shipped
  unreviewed must not read like one that passed. Never present re-reading your
  own diff as a review.
- **Acceptance criteria that shipped `not-met`, and why that was accepted.** If
  none did, say the criteria were met. If the issue carried none, say that —
  rather than implying it passed a check it never had.
- **Every `DEFERRED` design's open question**, phrased as the question. These
  are the only part of the report the user has to act on.
- **Follow-ups filed**, what was fixed *inline* instead of filed (an unexplained
  widened diff is indistinguishable from scope creep), and findings checked and
  deliberately *not* filed with what prevented each — a verified non-issue is a
  result, and silence reads as "nothing was noticed".
- **Everything held or deferred**, and any approval-gated command that had to
  run mid-run with why it could not wait — see
  [the final confirmation](#the-final-confirmation).
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
