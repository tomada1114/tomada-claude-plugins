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
record so a re-run knows what already landed.

### Run record

```bash
python3 scripts/run_record.py --repo <owner>/<repo> --event <kind> \
    [--field k=v ...] [--body-file <path>]
```

Appends one line (or, for `run-start`, a heading plus a line) to
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/shipping-issues/<owner>__<repo>/run.md`
— never rewritten or deleted, so a stopped run keeps what already landed. Call
it right after the event happens, not batched at the end; `--repo` can be
omitted when cwd is the repo being shipped. Events: `run-start`, `selection`
(the rubric-shaped block from
[references/priority-rubric.md](references/priority-rubric.md) via
`--body-file`), `labels`, `pr-created`, `review`, `ci`, `merged`, `followup`,
`cleanup`, `blocked`, `note`.

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
how step 6 lands. Once it passes, open the run record
(`scripts/run_record.py --event run-start --field mode=<single|all>`).

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

Re-run `--select` after labeling, then record both halves ("Run record"
above): `--event labels` with the script's one-line summary, then
`--event selection` with the rubric-shaped block via `--body-file`:
chosen issue, evidence lines, runner-up, deferred. **Proceed on that pick
without asking.**
Ask the user directly, in plain conversation, and wait for their reply, only
when the top two are genuinely tied on every axis, or the top issue needs a
product decision before it can be implemented at all.

### 3. Implement — Codex writes the code, this context owns `gh`

One issue = one branch = one PR. The implementation goes to a Codex run, per
issue, using the Implementation template in
[references/subagent-prompts.md](references/subagent-prompts.md):

```bash
scripts/codex_run.sh check                      # once per run, before the first issue
scripts/codex_run.sh task --write --cwd <worktree> --prompt-file <filled template>
```

Codex carries the issue from branch to pushed commits: read the project's own
`CLAUDE.md`/`AGENTS.md`, implement the stated scope, add the tests, run the
verification command, commit in coherent increments, push. **It stops at the
push.** The Codex sandbox reaches github.com over `git`, but `gh` cannot
authenticate inside it — so opening the PR, `link_check.sh`, CI, and the merge
are all this context's work (steps 3.5 onward). That boundary is not a
limitation to route around: it is what keeps every merge-gating fact established
here, from script output, rather than accepted on a worker's say-so.

Isolation still comes from the work copy, not the runtime: `--cwd` scopes Codex
to one worktree, so a parallel batch (cap 3) is one worktree and one Codex run
per issue, each with its own thread, job state, and review target. Serialize
everything else. `check` reporting `codex_mode: NONE` (exit 3) means this
machine has no Codex — fall back to an `opus` worker per issue where this
runtime exposes delegation, otherwise inline, one at a time, using the same
template at the same scope.

Codex returns branch, changed files, the verification command it ran, `MEASURE:`
for a performance claim, `FOLLOW-UPS` (fed to step 6.5), and `UNRESOLVED` — not
the diff. `codex_touched:` lists only what it edited through patches, so
`git -C <worktree> status --short` is the authority on what actually changed.

**Codex cannot ask a question back.** A spec hole returns as a decision it made
alone, under `UNRESOLVED` if you are lucky. Fill the template's `<context>`
block until nothing merge-gating is left to guess.

Push discipline is the run's insurance: Codex pushes as soon as its first
coherent commit exists, so a run stopped mid-way loses at most its uncommitted
tail. It never cleans up after itself (no `rm`, no worktree removal — that
happens once, in step 7) and copies any gitignored artifacts it produced into
the main checkout before returning, since worktrees are deleted at the end.

### 3.5 Open the PR

```bash
gh pr create --base <default_branch> --head <branch> --title <...> --body <...>
```

Two constraints exist so the issue closes itself on merge: the body carries
**`Closes #N`** as the first line after the summary (a bare `#N` mention closes
nothing), and the PR targets the **default branch** (auto-close only fires
there). Build the body from what Codex returned — summary, `Closes #N`, and a
test plan carrying the verification command and, for a performance issue, both
measurements. Record it as soon as it exists (`--event pr-created --field
issue=<n> --field pr=<url>`), before CI: a run that stops mid-watch must still
show what was opened.

### 4. Verify the auto-close link

```bash
scripts/link_check.sh <pr> --issue <n> --fix
```

Cheap, and it is the one check that decides whether this run actually closes
anything. `--fix` appends the missing `Closes #N` itself. `WRONG_BASE` means the
PR targets a non-default branch — retarget it (`gh pr edit <pr> --base
<default>`) before merging, or the issue stays open.

### 4.5 Review before CI — a context that did not write the diff

Between the PR existing and CI judging it there is one review pass that catches
what CI cannot: whether the change is what issue #N asked for, needless
complexity, maintainability, and tests that would still pass with the bug
present. Run it from here against the worktree, with the Self-review template in
[references/subagent-prompts.md](references/subagent-prompts.md) as the prompt:

```bash
scripts/codex_run.sh task --cwd <worktree> --prompt-file <filled Self-review template>
```

No `--write`: the reviewer is read-only at the sandbox level, so it reports
defects and cannot quietly patch them. It is a **separate run** from the one
that implemented the change — a fresh run reads the diff in a context that never
wrote it, which is the only thing that makes it a review — and `--cwd
<worktree>` is what makes it reachable from here, so nothing has to be delegated
into the worktree to see the right branch.

For a **heavy diff** — one that touches a schema, storage layer, or public
contract; adds or bumps a dependency; or rewires behavior across several modules
— add the adversarial pass, which judges the axis the template does not: failure
modes, trust boundaries, data loss, rollback safety.

```bash
scripts/codex_run.sh review --cwd <worktree> --base <default_branch> --focus-file <issue context>
```

It returns `review_verdict: approve | needs-attention` plus one line per finding
with severity, file, line range, and confidence; exit 1 means
`needs-attention`. Neither pass replaces the other — the adversarial one is told
to skip style, naming, and cleanup, which is most of what the Self-review
template looks for.

Apply the findings in the worktree — a further `codex_run.sh task --write --cwd
<worktree>` run carrying them verbatim, or here when the fix is a line or two —
then commit (`review: <what was fixed>`), push, and re-run the verification
command, so CI judges the reviewed code rather than the pre-review commit. Fix
the cause, never the check: a finding cleared by deleting a test, loosening an
assertion, or silencing a warning is a failed outcome and goes under
`UNRESOLVED` instead. One round is the ceiling — what is still open after it
goes to `UNRESOLVED`, or to step 6.5 as a follow-up if it is outside issue #N's
scope, rather than blocking the merge.

Record which rung ran (`--event review --field pr=<n> --field
status=<codex|codex+adversarial|DELEGATED|UNAVAILABLE>`). With no Codex on the
machine, take the highest rung still reachable — one independent reviewer
spawned against the branch where delegation is available (`DELEGATED`),
otherwise `UNAVAILABLE`; do not re-read the diff here and call that a review.
`UNAVAILABLE` is a lowered assurance level, not a silent one — lint, types,
tests and CI still ran, but nothing judged the change for complexity, intent, or
maintainability — so it stays in the run record and is named again in the step 8
report.

### 5. CI to green

Run `scripts/ci_watch.sh <pr> --timeout 1800` in the main context first — its
output is a short verdict, and most PRs go green on the first watch, so a repair
run would buy nothing.

In `all` mode with several PRs in flight, run the watches concurrently where
that is available; otherwise run `ci_watch.sh` per PR sequentially, one wait at
a time. It is the run's only wait primitive — one blocking call per wait;
neither this context nor any worker hand-rolls a `sleep`/poll loop around `gh`.
Record each verdict (`--event ci --field pr=<n> --field verdict=<...>`),
including one that took repair attempts to reach.

Only on `FAIL`, hand the repair to Codex using the CI repair template in
[references/subagent-prompts.md](references/subagent-prompts.md). `ci_watch.sh`
prints the failing logs to stdout and Codex cannot run `gh` itself, so redirect
that output into the worktree and pass the path — the logs reach the repair
without landing in this context:

```bash
scripts/ci_watch.sh <pr> --timeout 1800 > <worktree>/.ci-failure.log
scripts/codex_run.sh task --write --cwd <worktree> --prompt-file <filled template>
```

Codex reads that log, fixes the cause, commits, and pushes; this context
re-watches and decides whether to go again — up to **3 attempts** total. The
loop lives here because only this context can watch. Delete the log before step
7 if the repo does not ignore it, or cleanup skips the worktree as dirty. If the
same failure survives two attempts, put the accumulated detail in the third
prompt rather than sending the same instruction again. With no Codex on the
machine, fall back to a `sonnet` worker per failing PR where delegation is
available — escalating to `opus` after two failed attempts — otherwise inline.

A green CI is the goal. A check that passes because a test was deleted, skipped,
or weakened is a failed outcome and gets reported as such — same for a "flaky"
job re-run until it happens to pass without a diagnosis.

`NO_CHECKS` — this repo has no CI on this PR. Do not merge on the absence of
evidence: run the project's own verification command (the one Codex reported)
in the branch worktree, and merge on a local green. If the project has no such
command either, say so explicitly in the report and ask before merging.

### 6. Merge and confirm the issue closed

```bash
scripts/land_pr.sh <pr> --issue <n>
```

`--issue` makes the script re-check the closing link before merging and confirm
the issue really closed after — closing it explicitly, with a back-reference
comment, if GitHub's auto-close did not fire. Read both lines it prints:
`result:` and `issue:`.

Merge automatically once step 5 reported a green `verdict: PASS`. Six outcomes
need different handling:

- `NOT_LINKED` / `WRONG_BASE` — the script refused to merge because the issue
  would be orphaned. Repair it (step 4: `--fix` for a missing keyword,
  `gh pr edit <pr> --base <default>` for a wrong base) and retry; only pass
  `--no-link-check` if the user asked for a PR that deliberately does not close
  its issue.
- `DRAFT` — the PR is still a draft and the script could not (or was told not
  to) mark it ready. Run `gh pr ready <pr>` and retry.
- `reviewDecision: REVIEW_REQUIRED` or `mergeStateStatus: BLOCKED` in the JSON
  `land_pr.sh` echoes (the same two facts `ci_watch.sh` prints as
  `review_decision` / `merge_state`) — re-run with
  `--auto` to arm auto-merge, report that it is armed (and that the issue closes
  when it lands), and move on to the next issue.
- `MERGE_REFUSED` / conflicts — report the reason; for conflicts, rebase in the
  branch's worktree and return to step 5.
- `ALREADY_MERGED` / `NOT_OPEN` — the PR left the open set before this call;
  take the issue's state from the `issue:` line and move on without retrying.
- `MERGE_UNCONFIRMED` / `ERROR` — the outcome is unestablished. Re-read PR and
  issue state with `gh`; never report a merge on this result alone.

Record the outcome (`scripts/run_record.py --event merged ...`, see "Run
record" below) as it happens, in both modes. In `all` mode, also rebase every
still-in-flight branch onto the updated default branch after each merge,
before its CI run — and re-rank the remaining issues with `issue_digest.py
--select`, since a merged blocker can move a dependent from BLOCKED to top of
the list. That re-rank is one script call now that priority is labeled; do not
re-run the research pass per merge.

### 6.5 File the findings the run turned up

Shipping an issue surfaces defects that are not that issue: a sibling of the
bug just fixed, a latent gap the diff walked past, a scope the implementation
agent deliberately declined. Each one is a finding the run paid for. Fixing it
inline silently widens a PR that is about to auto-merge; saying it only in the
final report loses it the moment the conversation ends. File it.

**File — do not fix inline — when any of these hold:**

- it needs its own tests, schema change, or design decision;
- it changes behavior outside the shipped issue's stated scope;
- the implementing run already returned it under `SCOPE-NOTES` or
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

**Verify before filing.** A worker's out-of-scope observation is a lead, not
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
at the end, where an interrupted run loses them all. Record it (`--event
followup`) as it happens, same as any other outcome.

### 7. Clean up — once, at the end, script only

The main worktree's `HEAD` is still on whatever branch was last implemented,
and cleanup's branch pass refuses to delete a branch checked out there — so
switch back to the default branch, fast-forwarded, **before** cleanup runs,
not after (a stale checkout also hands the next run a stale base):

```bash
git switch <default> && git pull --ff-only
scripts/cleanup_run.sh [--remote] [--dry-run] [--merged-only]
```

All deletion goes through `cleanup_run.sh`, in one batch after the last merge.
Never run `rm`, `git worktree remove`, or `git branch -D` ad hoc in the main
context or in a Codex run — raw `rm` is flagged as dangerous and stalls the run
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

Record the cleanup outcome (`scripts/run_record.py --event cleanup ...`) and
confirm the final status: the local default branch matches origin and no
worktree or branch cleanup_run.sh reported was left `SKIPPED` for a reason
that still applies.

### 8. Report

Open with the selection rationale in one line — why this issue was first, by
tier — and, when step 2 wrote labels, one line for that (`labeled 9 issues: 2
P0, 3 P1, …`, straight from the script's summary). Then
per issue: `#N <title> → PR #M → MERGED, issue CLOSED | AUTO-ARMED | FAILED(<why>)
| SKIPPED(<why>)`, plus `REVIEW: UNAVAILABLE` or `REVIEW: UNRESOLVED(<n>)`
whenever step 4.5 did not run clean — a run that shipped unreviewed must not
read like one that passed review. Flag any issue left open behind a merged PR
explicitly; that is the failure mode this skill exists to prevent.

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

The main context holds the selection and the verdicts, nothing else — issue
bodies, diffs, and CI logs each stay with the run that needs them. What belongs
where, the per-issue Codex-run budget, and why the model assignments are what
they are: [references/cost-discipline.md](references/cost-discipline.md).

## Stop conditions

Stop the whole run and report when: preflight is BLOCKED, a dependency cycle
needs a human to break it, a merge conflict requires a product decision, or the
same CI failure survives the retry ceiling on two different issues (the problem
is the base branch, not the change).

Record it before stopping (`--event blocked --field reason=<what stopped it>`).

In `all` mode, a single failed issue does not stop the run — mark it FAILED,
record it the same way, skip anything that depended on it, and continue.

## Platform notes

詳細は [references/platform-notes.md](references/platform-notes.md) を参照。
