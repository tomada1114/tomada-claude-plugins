# Closing out: cleanup and report

Read at step 10 (cleanup) and step 11 (report) — everything past the ordering
and safety rules the SKILL.md body already states inline.

## Table of Contents

- [Cleanup scope](#cleanup-scope)
- [Report shape](#report-shape)

## Cleanup scope

```bash
git switch <default> && git pull --ff-only
{SKILL_DIR}/scripts/cleanup_run.sh [--remote] [--dry-run] [--merged-only]
```

All deletion goes through `cleanup_run.sh`, in one batch after the last merge.
Never run `rm`, `git worktree remove`, or `git branch -D` ad hoc in the main
context or in a Codex run — raw `rm` is flagged as dangerous and stalls the run
on a permission prompt. The script only touches `<repo>/.claude/worktrees/*`,
harness `worktree-agent-*` branches, and branches whose PR is merged;
`--remote` extends that to the same refs on origin. A worktree with
uncommitted files is skipped and listed — salvage what matters, then rerun
with `--force`. Nothing this run generated should be sitting in a worktree to
begin with: prompts, issue bodies and CI logs all live under `<runstate>/`
([run-record.md](run-record.md)).

**The worktree pass is not merge-gated by default: it removes every worktree
under that root, including one another session is mid-run in.** That is
correct at the end of a run this skill owns end to end, and wrong everywhere
else. When other sessions may be working in the same repo — or when cleaning
up outside a run, purely to reclaim disk — pass `--merged-only`, which keeps
any worktree whose branch has no merged PR (or still has an open one).
Worktrees are expensive to leave lying around: each one carries its own
`.venv` and type-check caches, so a few stale ones can add up to gigabytes.
Prefer the repo's own cleanup recipe when it exposes one, so cleanup does not
depend on this skill's path.

Record the cleanup outcome (`--event cleanup ...`) and report anything it left
`SKIPPED`.

## Report shape

Open with the selection rationale in one line — why this issue was first, by
tier — and, when step 2 wrote labels, one line for that (`labeled 9 issues: 2
P0, 3 P1, …`, straight from the script's summary). Then
per issue: `#N <title> → PR #M → MERGED, issue CLOSED | AUTO-ARMED | FAILED(<why>)
| SKIPPED(<why>)`, plus `REVIEW: UNAVAILABLE` or `REVIEW: UNRESOLVED(<n>)`
whenever step 6 did not run clean — a run that shipped unreviewed must not
read like one that passed review. Flag any issue left open behind a merged PR
explicitly; that is the failure mode this skill exists to prevent.

Then, when step 9 filed anything, one line per follow-up: `filed #N <title>
[tier] — found while shipping #M`. Also state the findings you checked and did
*not* file, with what prevented them — a verified non-issue is a result, and
silence reads as "nothing was noticed". Operator actions the run surfaced
(resolved by running a command or changing a setting, not by a PR) get their
own lines here — the backlog will never show them, so the report is their only
record.

Then list what was left undone — blocked issues, ones needing clarification,
ones that hit the retry ceiling — with the specific reason each.
