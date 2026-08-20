---
name: shipping-issues
description: "Rank the open GitHub Issues by their `priority: P0`-`P3` labels — backfilling a label, from whether an issue unblocks others and how far its impact spreads, wherever one is missing — then implement the top one, open a PR that auto-closes the issue (Closes #N), watch CI until it is green, merge to main, and confirm the issue actually closed. With no argument it ships only the single highest-priority issue; pass \"all\" to work through every issue in dependency order (independent ones in parallel worktrees). Issue data collection, CI watching, and fix retries are delegated to scripts and sub-agents to save tokens. Use when asked to ship the remaining issues, start from the highest-priority issue, implement an issue through to merge, take on the next issue, clear the ticket backlog, work through the open issues, or finish off every issue."
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
| `all` / `全部` / `ぜんぶ` / `すべて` | Ship every shippable issue, in dependency-then-priority order. Independent issues run in parallel worktrees (cap 3). |
| a number, e.g. `42` | Ship that specific issue, after checking nothing it depends on is still open. |

Anything else in the argument is a filter hint (a label, a milestone, "自分の
Issue だけ") — apply it as `issue_digest.py` flags.

## Inputs and outputs

Reads: the current repo's open issues and PRs via `gh`; the project's own
`CLAUDE.md` / `AGENTS.md` for conventions.

Writes: `priority: P0`…`P3` labels on the repo's open issues (the persisted
ranking), branches, PRs, merge commits on the remote, issue closures, **new
follow-up issues for defects found along the way** (step 6.5), plus a run
record at
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/shipping-issues/<owner>__<repo>/run.md`
(appended, never deleted) so a re-run knows what already landed.

## Workflow

### 0. Preflight

Script paths below are skill-relative (`scripts/...`, `references/...`); the
main context resolves them from this skill's own directory on either
platform.

```bash
scripts/preflight.sh
```

`verdict: BLOCKED` stops the run — report the blocker and stop. A dirty working
tree is a warning: ask whether to stash, commit, or proceed before creating any
branch. Note the reported `default_branch` and `branch_protection` — both decide
how step 6 lands.

### 1. Rank — by label, not by re-reading the backlog

```bash
python3 scripts/issue_digest.py --select [--label L] [--assignee A]
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
  python3 scripts/apply_priority_labels.py --backfill --set N=P0 --quiet
  ```

- **more than that, tangled dependency edges, or a close top-two** — hand off
  the Priority research template in
  [references/subagent-prompts.md](references/subagent-prompts.md):

  Delegate this to an independent `sonnet` worker using that template where
  delegation is available; otherwise the main context reads the same template
  skill-relatively and performs the same read → rubric →
  `apply_priority_labels.py` steps inline, before continuing. Either way: only
  the selection with evidence comes back — not the prose, not the per-issue
  tier list.

  Do not run the backfill yourself first; that call covers both halves either
  way.

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
Ask the user directly, in plain conversation, and wait for their reply, only
when the top two are genuinely tied on every axis, or the top issue needs a
product decision before it can be implemented at all.

### 3. Implement, with the issue link built in

One issue = one branch = one PR, following the Implementation template in
[references/subagent-prompts.md](references/subagent-prompts.md).

Delegate this to an independent `opus` worker per issue using that template
where delegation is available — a parallel group uses an isolated work copy
per issue (cap 3), spawned together in one batch; serialize everything else —
otherwise the main context reads the same template skill-relatively and works
through issues one at a time in the checkout (or one worktree at a time),
following the same steps inline. Either way: phase order (rank → implement →
CI → merge) stays unchanged; when delegation is unavailable this collapses the
fan-out speed parallelism of `all` mode to serial — a time increase only.

Two constraints exist so the issue closes itself on merge:

- the PR body carries **`Closes #N`** — a bare `#N` mention closes nothing;
- the PR targets the **default branch** — GitHub's auto-close only fires there.

The sub-agent returns branch, PR URL, base, link verdict, changed files, the
exact verification command it ran, the self-review result (`REVIEW:`, step 4.5),
and any out-of-scope defects it saw (`FOLLOW-UPS`, fed to step 6.5) — not the
diff. Sub-agents never clean up after themselves (no `rm`, no worktree removal
— that all happens once, in step 7), and must copy any gitignored artifacts
they produced (fixtures, bench outputs) into the main checkout before
returning, because worktrees are deleted at the end of the run.

That return is a claim, not a verified fact. Steps 4–6 re-establish every
merge-gating fact — the PR exists, CI's verdict, the issue's final state — from
script output in this context, so a report of "PR opened, CI green" changes
nothing about which steps run, and nothing is deleted or declared done on a
sub-agent's say-so. Push discipline is the other half of that insurance: the
template has the agent push as soon as its first coherent commit exists, so an
agent stopped mid-run loses at most its uncommitted tail, and step 7's script
skips dirty worktrees rather than deleting them.

### 4. Verify the auto-close link

```bash
scripts/link_check.sh <pr> --issue <n> --fix
```

Cheap, and it is the one check that decides whether this run actually closes
anything. `--fix` appends the missing `Closes #N` itself. `WRONG_BASE` means the
PR targets a non-default branch — retarget it (`gh pr edit <pr> --base
<default>`) before merging, or the issue stays open.

The implementation agent already runs this; re-running here is a one-line
confirmation, not duplicated work.

### 4.5 Self-review before CI — effort scaled to the diff

Between the PR existing and CI judging it there is one review pass that catches
what CI cannot: correctness bugs, dead reuse, needless complexity. A
self-review pass, run when one is available, does it and applies its own
fixes. The implementation agent picks the effort level from the diff it just
produced:

- **Heavy diff** — touches a schema, storage layer, or public contract; adds or
  bumps a dependency; or rewires behavior across several modules — one pass at
  high effort, applying its findings.

  `high` reaches in a single pass what `low` needs repetition for, and
  re-reviewing a large diff in full costs more than the second pass catches.

- **Anything else** — one pass at low effort, applying its findings, **twice**:
  the second pass reviews the code as the first pass changed it. `low` returns
  fewer, high-confidence findings — the right depth for a small, contained
  diff.

Applying findings hands them off to be written into the working tree; that
does not commit them, so each pass ends with a commit and a push.

**The implementation agent runs the review, inside its own worktree**, as the
last thing it does before returning. It is the only context whose working tree
*is* the PR branch: a self-review pass runs in the calling session's cwd and
applying its findings writes to that working tree, so run from here it
reviews the wrong checkout — a worktree's branch is invisible to it. That
holds for any extra pre-merge pass too: more review happens inside the
worktree (spawn an agent there), or not at all.

Every pass lands on the branch before step 5 starts, so CI is watched on the
reviewed code rather than on the pre-review commit.

Two rules keep the passes convergent. Each pass runs on a settled branch — the
previous pass's fixes are committed and pushed before the next starts, and
nothing pushes while a pass runs — so a finding that cites lines the head no
longer has is stale, not unresolved. And the pass count is a ceiling, not a
floor: when the final pass still returns findings, there is no further round —
in-scope leftovers go under `UNRESOLVED`, out-of-scope ones under `FOLLOW-UPS`,
the PR merges anyway, and step 6.5 files what survived. When a finding is
relayed to another context for fixing, pass the defect — file, line, what is
wrong — never the reviewer's proposed patch: the fixer re-derives the fix in
the code it can see, because a patch written without that context is how a
review fix causes the next regression.

Step 5's rule applies to review fixes too: a finding is cleared by fixing the
cause, never by deleting a test, loosening an assertion, or silencing a check. A
finding outside the shipped issue's scope is not fixed here either — it comes
back under `FOLLOW-UPS` and is filed in step 6.5.

The agent reports `REVIEW:` with the chosen effort level and per-pass finding
and fix counts. `UNAVAILABLE` — no self-review pass is reachable from a
sub-agent context, or none exists on this platform at all — is not a run
failure: when the branch is checked out in this context — single-issue mode,
no worktree — run the same passes here instead, committing and pushing each
one; otherwise note it in the report and go on to CI.

### 5. CI to green

Run `scripts/ci_watch.sh <pr> --timeout 1800` in the main context first — its
output is a short verdict, and most PRs go green on the first watch, so a
sub-agent spawn would buy nothing.

In `all` mode with several PRs in flight, run the watches concurrently where
that is available instead of serializing them; otherwise run `ci_watch.sh` per
PR sequentially, one wait at a time.

`ci_watch.sh` is the run's only wait primitive — one blocking call per wait;
neither this context nor any sub-agent hand-rolls a `sleep`/poll loop around
`gh`.

Only on `FAIL`, hand off the CI repair template in
[references/subagent-prompts.md](references/subagent-prompts.md):

Delegate this to an independent `sonnet` worker per failing PR using that
template where delegation is available; otherwise the main context reads the
same template skill-relatively and performs the same repair steps inline, one
PR at a time. Either way: it reads the failing logs the script printed, fixes
the branch in its worktree, pushes, and re-watches — up to **3 attempts**
total. If the same failure survives two attempts, escalate to `opus` with the
accumulated failure detail (re-spawning on `opus` where delegation is
available, or raising its own effort inline otherwise). CI logs stay with the
worker doing the repair; the main context gets its verdict lines only.

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
scripts/land_pr.sh <pr> --issue <n>
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

### 6.5 File the findings the run turned up

Shipping an issue surfaces defects that are not that issue: a sibling of the
bug just fixed, a latent gap the diff walked past, a scope the implementation
agent deliberately declined. Each one is a finding the run paid for. Fixing it
inline silently widens a PR that is about to auto-merge; saying it only in the
final report loses it the moment the conversation ends. File it.

**File — do not fix inline — when any of these hold:**

- it needs its own tests, schema change, or design decision;
- it changes behavior outside the shipped issue's stated scope;
- the implementation agent already returned it under `SCOPE-NOTES` or
  `FOLLOW-UPS` as something it declined on purpose;
- the fix would push a green PR back through CI for a reason unrelated to its
  own issue.

**Do not file** what a one-line edit inside the current diff covers and the
issue's own tests already exercise, nor a restatement of the issue being
shipped, nor a speculative "we could someday" with no observed defect behind it.
An issue nobody will act on costs the next run's ranking pass real attention.

An operational action is not an issue either: something resolved by running an
existing command or skill, or by changing a machine or account setting, changes
nothing in the repository, so no PR can ever close it. Report it in step 8 as an
operator action instead. The same test applies to the backlog itself — an
existing open issue that turns out to be purely operational is not shippable;
close it with a comment naming the action that resolves it, and record the
closure in the report.

**Verify before filing.** A sub-agent's out-of-scope observation is a lead, not
a fact — it saw the code while working on something else. Read the lines it
names and confirm the defect is real, and confirm what actually prevents it
today. That check routinely changes the tier: a gap that sounds severe but is
already blocked at an adapter boundary is a missing defense layer (P3), not a
live bug (P1). File what you verified, including the mitigation, never the
agent's summary taken on faith. If it does not survive the check, say so in the
report and file nothing.

Write the body to a file, then:

```bash
python3 scripts/file_followup.py \
    --title "<repo's title convention>" --body-file <path> \
    --tier P2 --label <area label> --found-while <n>
```

`--tier` is required and follows
[references/priority-rubric.md](references/priority-rubric.md) — the same rubric
step 2 ranks by, so the finding enters the backlog already ordered against
everything else. The script resolves the tier label the repo *already* uses
(`p2` stays `p2`; a second `priority: P2` vocabulary would split the backlog in
two), drops `--label` values the repo lacks instead of failing, and echoes the
resolved repo. Exit 2 (`NO_WRITE_ACCESS`) means report the finding in step 8
instead. Add `--repo OWNER/NAME` whenever cwd may not be the repo being shipped.

Give the body what the next session needs and cannot cheaply re-derive: the
observed defect with `file:line`, why it matters in this codebase's terms, **what
currently prevents it and why that is not enough**, the invariants a fix must not
break (quote the canonical doc), and a completion checklist. Name the open design
questions and leave them open rather than deciding them here.

File as you go, right after the PR that surfaced the finding lands — not batched
at the end, where an interrupted run loses them all.

### 7. Clean up — once, at the end, script only

```bash
scripts/cleanup_run.sh [--remote] [--dry-run] [--merged-only]
```

All deletion goes through this one script, in one batch after the last merge.
Never run `rm`, `git worktree remove`, or `git branch -D` ad hoc in the main
context or in sub-agents — raw `rm` is flagged as dangerous and stalls the run
on a permission prompt. The script only touches `<repo>/.claude/worktrees/*`,
harness `worktree-agent-*` branches, and branches whose PR is merged;
`--remote` extends that to the same refs on origin. A worktree with
uncommitted files is skipped and listed — salvage what matters, then rerun
with `--force`.

**The worktree pass is not merge-gated by default: it removes every worktree
under that root, including one another session is mid-run in.** That is correct
at the end of a run this skill owns end to end, and wrong everywhere else. When
other sessions may be working in the same repo — or when cleaning up outside a
run, purely to reclaim disk — pass `--merged-only`, which keeps any worktree
whose branch has no merged PR (or still has an open one). Worktrees are
expensive to leave lying around: each one carries its own `.venv` and type-check
caches, so a few stale ones can add up to gigabytes.

A repo can wrap that safe mode in its own task runner, so cleanup does not
depend on this skill's path — `swing-copilot` exposes it as
`just worktree-clean [--dry-run]`. Prefer such a recipe when the repo has one.

End the run with the local default branch fast-forwarded
(`git checkout <default> && git pull --ff-only`). The merges landed on the
remote; a checkout still sitting on pre-merge code hands a stale base to the
next run — and to anything else that executes from this working copy on a
schedule.

### 8. Report

Open with the selection rationale in one line — why this issue was first, by
tier — and, when step 2 wrote labels, one line for that (`labeled 9 issues: 2
P0, 3 P1, …`, straight from the script's summary). Then
per issue: `#N <title> → PR #M → MERGED, issue CLOSED | AUTO-ARMED | FAILED(<why>)
| SKIPPED(<why>)`. Flag any issue left open behind a merged PR explicitly; that
is the failure mode this skill exists to prevent.

Then, when step 6.5 filed anything, one line per follow-up: `filed #N <title>
[tier] — found while shipping #M`. Also state the findings you checked and did
*not* file, with what prevented them — a verified non-issue is a result, and
silence reads as "nothing was noticed". Operator actions the run surfaced
(resolved by running a command or changing a setting, not by a PR) get their own
lines here — the backlog will never show them, so the report is their only
record.

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
(optional), one implementation per issue, one CI-repair per PR. The self-review
passes (step 4.5) add no spawn from here either — they run inside the
implementation agent, and only the effort level and finding counts come back.
Filing a follow-up (step 6.5) never adds a spawn — the agent that found it already
returned the lead in `FOLLOW-UPS`, and confirming it costs a couple of targeted
reads in the main context, which is also what makes the tier trustworthy.

Model assignments (triage and CI watch on `sonnet`, implementation on `opus`,
escalation to `opus` after two failed repairs) are baked-in conclusions — the
dividing line is spec completeness — and apply as stated on both platforms.
Implementation stays delegated even when the main model is Opus: a deliberate
exception to the Opus-main "do it yourself" default, bought for context
isolation — the diff, the repo exploration, and the CI logs are never needed
in the main context again. (See `orchestrating-models` §2 for the reasoning
behind these assignments; [references/platform-notes.md](references/platform-notes.md)
notes where that citation resolves.)

## Stop conditions

Stop the whole run and report when: preflight is BLOCKED, a dependency cycle
needs a human to break it, a merge conflict requires a product decision, or the
same CI failure survives the retry ceiling on two different issues (the problem
is the base branch, not the change).

In `all` mode, a single failed issue does not stop the run — mark it FAILED,
skip anything that depended on it, and continue.

## Platform notes

詳細は [references/platform-notes.md](references/platform-notes.md) を参照。
