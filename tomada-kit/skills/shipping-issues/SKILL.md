---
name: shipping-issues
description: "Rank the open GitHub Issues by their `priority: P0`-`P3` labels — backfilling a label, from whether an issue unblocks others and how far its impact spreads, wherever one is missing — then implement the top one, open a PR that auto-closes the issue (Closes #N), watch CI until it is green, merge to main, and confirm the issue actually closed. With no argument it ships only the single highest-priority issue; pass \"all\" to work through every issue in dependency order (independent ones in parallel worktrees). Issue data collection, CI watching, and fix retries are delegated to scripts and sub-agents to save tokens. Use when asked to ship the remaining issues, start from the highest-priority issue, implement an issue through to merge, take on the next issue, clear the ticket backlog, work through the open issues, or finish off every issue."
argument-hint: "[all | <issue number> | (empty = one issue)]"
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
| `all` / `全部` / `ぜんぶ` / `すべて` | Ship every shippable issue, in dependency-then-priority order. Independent issues run in parallel worktrees (cap 3). |
| a number, e.g. `42` | Ship that specific issue, after checking nothing it depends on is still open. |

Anything else in the argument is a filter hint (a label, a milestone, "自分の
Issue だけ") — apply it as `issue_digest.py` flags.

## Inputs and outputs

Reads: the current repo's open issues and PRs via `gh`; the project's own
`CLAUDE.md` / `AGENTS.md` for conventions.

Writes: `priority: P0`…`P3` labels on the repo's open issues (the persisted
ranking), branches, PRs, merge commits on the remote, issue closures, plus a run
record at `~/.claude/shipping-issues/<owner>__<repo>/run.md` (appended, never
deleted) so a re-run knows what already landed.

## Workflow

### 0. Preflight

```bash
"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/scripts/preflight.sh
```

`verdict: BLOCKED` stops the run — report the blocker and stop. A dirty working
tree is a warning: ask whether to stash, commit, or proceed before creating any
branch. Note the reported `default_branch` and `branch_protection` — both decide
how step 6 lands.

### 1. Rank — by label, not by re-reading the backlog

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/scripts/issue_digest.py --select [--label L] [--assignee A]
```

Priority lives on GitHub as a `priority: P0`…`P3` label, so a ranked backlog
costs one script call to re-read. `--select` prints three lines — label
coverage, the pick, and what is held back — and nothing else. The tier is the
primary sort key; the heuristic score only orders issues *within* a tier, and a
BLOCKED issue is never selected.

The coverage line decides what happens next:

- `labels: N/N COMPLETE`, no `(~Pn)` marker on the top rows — the backlog is
  already ranked. **Skip step 2**: ship the issue on the `select:` line.
- anything else — the `~Pn` cells are suggestions the script computed but never
  wrote. Go to step 2 once, and later runs get the cheap path.

`P2(~P0)` means a written label now sits below what the signals justify —
usually written before the issue started blocking something. Re-label it in
step 2 rather than ranking around it, even on an otherwise complete backlog.

For the whole picture — per-issue `BLOCKED-BY`, `UNBLOCKS`, `HAS-OPEN-PR` flags
— drop `--select` (add `--body-chars 0` to keep the prose out) or use
`--rank-only` for just the table.

### 2. Label the unlabeled — once, and not in this context

Labeling is a script pass, not a reading pass. Who runs it depends only on how
many issues need judgment — and it runs **once**, not once per caller:

- **≤3 unlabeled or mis-tiered issues** — do it here. Read just those
  (`issue_digest.py --issue N --issue M`) against the rubric, then one call:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/scripts/apply_priority_labels.py --backfill --set N=P0 --quiet
  ```

- **more than that, tangled dependency edges, or a close top-two** — spawn one
  `sonnet` sub-agent with the Priority research template in
  [references/subagent-prompts.md](references/subagent-prompts.md) and let it
  make that same call. It reads the bodies, applies the rubric, and returns the
  selection with evidence — not the prose, not the per-issue tier list. Do not
  run the backfill yourself first; the agent's call covers both halves.

`--backfill` creates the four labels if the repo lacks them and writes the
suggested tier to every open issue that has none; each `--set` overrides one the
research pass judged differently. No issue body reaches this context either way,
and the output is one summary line. Run it without asking. Exit code 2
(`NO_WRITE_ACCESS`) means this token cannot write labels here — rank from the
`~Pn` suggestions for this run, say so in the report, and do not retry.

[references/priority-rubric.md](references/priority-rubric.md) defines what each
tier means and when a label is worth overriding; the readiness gate and
dependency rules are in
[references/dependency-triage.md](references/dependency-triage.md). Priority
means, in order: **unblocks other issues > leverage on shared ground >
must-be-first ordering > damage being taken right now.** A self-contained
nice-to-have never outranks those, however easy.

Re-run `--select` after labeling, then create the run record directory if it
does not exist and record the selection in the rubric's shape — chosen issue,
evidence lines, runner-up, deferred. **Proceed on that pick without asking.**
Ask via `AskUserQuestion` only when the top two are genuinely tied on every
axis, or the top issue needs a product decision before it can be implemented at
all.

### 3. Implement, with the issue link built in

One issue = one branch = one PR. Spawn an `opus` sub-agent per issue with the
Implementation template. For a parallel group, spawn them in a single message
with `isolation: "worktree"`; serialize everything else.

Two constraints exist so the issue closes itself on merge:

- the PR body carries **`Closes #N`** — a bare `#N` mention closes nothing;
- the PR targets the **default branch** — GitHub's auto-close only fires there.

The sub-agent returns branch, PR URL, base, link verdict, changed files, and the
exact verification command it ran — not the diff. Sub-agents never clean up
after themselves (no `rm`, no worktree removal — that all happens once, in
step 7), and must copy any gitignored artifacts they produced (fixtures, bench
outputs) into the main checkout before returning, because worktrees are deleted
at the end of the run.

### 4. Verify the auto-close link

```bash
"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/scripts/link_check.sh <pr> --issue <n> --fix
```

Cheap, and it is the one check that decides whether this run actually closes
anything. `--fix` appends the missing `Closes #N` itself. `WRONG_BASE` means the
PR targets a non-default branch — retarget it (`gh pr edit <pr> --base
<default>`) before merging, or the issue stays open.

The implementation agent already runs this; re-running here is a one-line
confirmation, not duplicated work.

### 5. CI to green

Spawn a `sonnet` sub-agent per PR with the CI watch template. It runs
`ci_watch.sh`, and on failure reads the logs, fixes the branch, pushes, and
re-watches — up to **3 attempts**. If the same failure survives two attempts,
re-spawn on `opus` with the accumulated failure detail.

A green CI is the goal. A check that passes because a test was deleted, skipped,
or weakened is a failed outcome and gets reported as such — same for a "flaky"
job re-run until it happens to pass without a diagnosis.

`NO_CHECKS` — this repo has no CI on this PR. Do not merge on the absence of
evidence: run the project's own verification command (the one the implementation
agent reported) in the branch worktree, and merge on a local green. If the
project has no such command either, say so explicitly in the report and ask
before merging.

### 6. Merge and confirm the issue closed

```bash
"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/scripts/land_pr.sh <pr> --issue <n>
```

`--issue` makes the script re-check the closing link before merging and confirm
the issue really closed after — closing it explicitly, with a back-reference
comment, if GitHub's auto-close did not fire. Read both lines it prints:
`result:` and `issue:`.

Merge automatically on `verdict: PASS`. Three cases need different handling:

- `NOT_LINKED` / `WRONG_BASE` — the script refused to merge because the issue
  would be orphaned. Repair it (step 4: `--fix` for a missing keyword,
  `gh pr edit <pr> --base <default>` for a wrong base) and retry; only pass
  `--no-link-check` if the user asked for a PR that deliberately does not close
  its issue.
- `review_decision: REVIEW_REQUIRED` or `merge_state: BLOCKED` — re-run with
  `--auto` to arm auto-merge, report that it is armed (and that the issue closes
  when it lands), and move on to the next issue.
- `MERGE_REFUSED` / conflicts — report the reason; for conflicts, rebase in the
  branch's worktree and return to step 5.

Append every outcome to the run record as it happens, in both modes. In `all`
mode, also rebase every still-in-flight branch onto the updated default branch
after each merge, before its CI run — and re-rank the remaining issues with
`issue_digest.py --select`, since a merged blocker can move a dependent from
BLOCKED to top of the list. That re-rank is one script call now that priority is
labeled; do not re-run the research pass per merge.

### 7. Clean up — once, at the end, script only

```bash
"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/scripts/cleanup_run.sh [--remote] [--dry-run]
```

All deletion goes through this one script, in one batch after the last merge.
Never run `rm`, `git worktree remove`, or `git branch -D` ad hoc in the main
context or in sub-agents — raw `rm` is flagged as dangerous and stalls the run
on a permission prompt. The script only touches `<repo>/.claude/worktrees/*`,
harness `worktree-agent-*` branches, and branches whose PR is merged;
`--remote` extends that to the same refs on origin. A worktree with
uncommitted files is skipped and listed — salvage what matters, then rerun
with `--force`.

### 8. Report

Open with the selection rationale in one line — why this issue was first, by
tier — and, when step 2 wrote labels, one line for that (`labeled 9 issues: 2
P0, 3 P1, …`, straight from the script's summary). Then
per issue: `#N <title> → PR #M → MERGED, issue CLOSED | AUTO-ARMED | FAILED(<why>)
| SKIPPED(<why>)`. Flag any issue left open behind a merged PR explicitly; that
is the failure mode this skill exists to prevent.

Then list what was left undone — blocked issues, ones needing clarification,
ones that hit the retry ceiling — with the specific reason each.

## Cost discipline

The main context holds the selection and the verdicts, nothing else. Issue
bodies go to the triage agent, diffs stay in the implementation agent, CI logs
stay in the repair agent. If you find yourself about to read a full `gh` JSON
blob or a workflow log in the main context, that is the signal to delegate
instead.

Labeling is the cheap half of this by design: the backfill is a pure script pass
with a one-line summary, and re-deriving priority from issue prose happens once
per issue — ever — because the answer is written back to GitHub. On a labeled
backlog the whole ranking step is `--select`, three lines, no sub-agent. Never
re-read bodies to reconstruct a priority a label already carries; if a label
looks wrong, fix the label.

Sub-agent count scales with issue count, not with thoroughness: one triage
(optional), one implementation per issue, one CI-repair per PR.

Model assignments (triage and CI watch on `sonnet`, implementation on `opus`,
escalation to `opus` after two failed repairs) are baked-in conclusions from
`orchestrating-models` §2 — the dividing line is spec completeness. Implementation
stays delegated even when the main model is Opus: a deliberate exception to that
skill's Opus-main "do it yourself" default, bought for context isolation — the
diff, the repo exploration, and the CI logs are never needed in the main context
again. <!-- derived from orchestrating-models §2 -->

## Stop conditions

Stop the whole run and report when: preflight is BLOCKED, a dependency cycle
needs a human to break it, a merge conflict requires a product decision, or the
same CI failure survives the retry ceiling on two different issues (the problem
is the base branch, not the change).

In `all` mode, a single failed issue does not stop the run — mark it FAILED,
skip anything that depended on it, and continue.
