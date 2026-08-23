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

Anything else in the argument is a filter hint (a label, a milestone, "only my
own issues") — apply it as `issue_digest.py` flags.

## Inputs and outputs

Reads: the current repo's open issues and PRs via `gh`; the project's own
`CLAUDE.md` / `AGENTS.md` for conventions.

Writes: `priority: P0`…`P3` labels on the repo's open issues (the persisted
ranking), branches, PRs, merge commits on the remote, issue closures, **new
follow-up issues for defects found along the way** (step 9), plus a run
record so a re-run knows what already landed.

### Run record

```bash
python3 {SKILL_DIR}/scripts/run_record.py --repo <owner>/<repo> --event <kind> \
    [--field k=v ...] [--body-file <path>]
```

Appends one line (or, for `run-start`, a heading plus a line) to `<runstate>/run.md`,
where **`<runstate>`** is
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/shipping-issues/<owner>__<repo>/`
— never rewritten or deleted, so a stopped run keeps what already landed.

Every other file this run generates lives there too, and **never inside a
worktree**: filled prompts at `<runstate>/prompts/<issue>-<step>.md`, issue
bodies for follow-ups beside them, CI logs at `<runstate>/ci/<pr>.log`. An
untracked file left in a worktree makes step 10's cleanup skip it as dirty, and
a commit convention that stages everything would land it in the PR. Call
it right after the event happens, not batched at the end; `--repo` can be
omitted when cwd is the repo being shipped. Events: `run-start`, `selection`
(the rubric-shaped block from
[references/priority-rubric.md](references/priority-rubric.md) via
`--body-file`), `labels`, `pr-created`, `review`, `ci`, `merged`, `followup`,
`cleanup`, `blocked`, `note`.

## Workflow

### 0. Preflight

`{SKILL_DIR}` below is the absolute path of this skill's own directory, which
the calling context substitutes before running anything. Markdown links to
bundled files stay relative.

**Requires:** `gh` (authenticated), `git`, `python3`. Optional: the Codex CLI —
plus Node for its companion entry point — for steps 3, 6 and 7; `coreutils` for
`gtimeout`, without which the CI watch has no enforced timeout.

```bash
{SKILL_DIR}/scripts/preflight.sh
{SKILL_DIR}/scripts/codex_run.sh check
```

`verdict: BLOCKED` stops the run — report the blocker and stop. A dirty working
tree is a warning: ask whether to stash, commit, or proceed before creating any
branch. Note the reported `default_branch` and `branch_protection` — both decide
how step 8 lands.

`codex_run.sh check` decides which route steps 3, 6 and 7 take. Exit 3 means no
usable Codex — absent, unauthenticated, or not ready; the `codex_auth` and
`codex_ready` lines say which — and every Codex step falls back. Do not read the
exit code alone at the step itself; settle it once, here.

Once preflight passes, open the run record (`{SKILL_DIR}/scripts/run_record.py
--event run-start --field mode=<single|all>`).

### 1. Rank — by label, not by re-reading the backlog

```bash
python3 {SKILL_DIR}/scripts/issue_digest.py --select [--label L] [--assignee A]
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
  python3 {SKILL_DIR}/scripts/apply_priority_labels.py --backfill --set N=P0 --quiet
  ```

- **more than that, tangled dependency edges, or a close top-two** — hand the
  Priority research template in
  [references/delegation-templates.md](references/delegation-templates.md) to an
  independent `sonnet` worker where delegation is available, otherwise read the
  same template here and run its read → rubric → `apply_priority_labels.py`
  steps inline before continuing. Either way what comes back is the pick with
  its evidence, the order behind it, the parallel-safe groups `all` mode batches
  from, and the blocked/unclear lists — never the issue prose or the raw digest
  table. Do not run the backfill yourself first;
  that one call covers both halves.

`--backfill` creates the four labels if the repo lacks them and writes the
suggested tier to every open issue that has none; each `--set` overrides one the
research pass judged differently. No issue body reaches this context either way,
and the output is one summary line. Run it without asking. Exit code 2
(`NO_WRITE_ACCESS`) means this token cannot write labels here — rank from the
`~Pn` suggestions for this run, say so in the report, and do not retry.

Priority means, in order: **unblocks other issues > leverage on shared ground >
must-be-first ordering > damage being taken right now.** A self-contained
nice-to-have never outranks those, however easy.
[references/priority-rubric.md](references/priority-rubric.md) defines each tier
and when a written label is worth overriding; the readiness gate that decides
what counts as shippable is in
[references/dependency-triage.md](references/dependency-triage.md).

Re-run `--select` after labeling, then record both halves ("Run record" above):
`--event labels` with the script's one-line summary, then `--event selection`
with the rubric-shaped block via `--body-file`. **Proceed on that pick without
asking.** Ask the user directly, and wait, only when the top two are genuinely
tied on every axis, or the top issue needs a product decision before it can be
implemented at all.

### 3. Implement — Codex writes the code, this context owns `gh`

One issue = one branch = one PR. Create the worktree first, under the root
step 10 cleans — anywhere else is never cleaned up:

```bash
git -C <repo> worktree add <repo>/.claude/worktrees/<n> -b <type>/<n>-<slug> <default_branch>
```

In single mode `<worktree>` may be the main checkout instead, in which case skip
the `worktree add` and let the run create the branch. Then write the filled
Implementation template from
[references/delegation-templates.md](references/delegation-templates.md) to
`<runstate>/prompts/<n>-impl.md` and run it:

```bash
{SKILL_DIR}/scripts/codex_run.sh task --write --cwd <worktree> --prompt-file <runstate>/prompts/<n>-impl.md
```

Codex carries the issue from branch to pushed commits: read the project's own
`CLAUDE.md`/`AGENTS.md`, implement the stated scope, add the tests, run the
verification command, commit in coherent increments, push. **It stops at the
push.** Opening the PR, `link_check.sh`, CI, and the merge are all this
context's work (steps 4 onward) — see
[references/cost-discipline.md](references/cost-discipline.md#why-the-split-is-where-it-is)
for why that boundary is load-bearing rather than a workaround.

Isolation comes from the work copy, not the runtime: `--cwd` scopes Codex to one
worktree, so a parallel batch (cap 3) is one worktree and one Codex run per
issue. Issue those runs in a single message so they execute concurrently, then
join. Serialize everything else.

**Returns**, per the template: `BRANCH` and `PUSHED`, `CHANGED`, `VERIFY`,
`MEASURE` for a performance claim, the three PR fields step 4 uses verbatim
(`PR-TITLE`, `PR-SUMMARY`, `TEST-PLAN`), plus `SCOPE-NOTES` and `FOLLOW-UPS`
(both fed to step 9) and `UNRESOLVED` — not the diff. `codex_touched:` lists
only what it edited through patches, so `git -C <worktree> status --short` is
the authority on what actually changed.

`codex_status:` non-zero means the turn did not complete. Do not retry blindly —
Codex pushes incrementally, so read `git -C <worktree> status --short` and
`git log` for what did land, then either resume that worktree with a prompt
naming what is left, or record `--event blocked`. Exit 4 is a usage error in the
call itself, not a Codex failure. With no usable Codex (step 0's `check`), fall
back to an `opus` worker per issue where this runtime exposes delegation,
otherwise inline, one at a time, using the same template at the same scope.

**Codex cannot ask a question back.** A spec hole returns as a decision it made
alone, under `UNRESOLVED` if you are lucky. Fill the template's `<context>`
block until nothing merge-gating is left to guess.

Push discipline is the run's insurance: Codex pushes as soon as its first
coherent commit exists, so a run stopped mid-way loses at most its uncommitted
tail. It never deletes anything — that happens once, in step 10 — and copies any
gitignored artifacts it produced into the main checkout before returning, since
worktrees are deleted at the end.

### 4. Open the PR

Read `PUSHED:` first. `no`, or a return that is only `UNRESOLVED`, means there
is no branch to open a PR from — record `--event blocked --field issue=<n>`,
report it as `SKIPPED(<why>)` in step 11, and in `all` mode move to the next
issue.

```bash
gh pr create --base <default_branch> --head <branch> --title <PR-TITLE> --body <...>
```

Two constraints exist so the issue closes itself on merge: the body carries
**`Closes #N`** as the first line after the summary (a bare `#N` mention closes
nothing), and the PR targets the **default branch** (auto-close only fires
there). Build the body from `PR-SUMMARY`, `Closes #N`, and `TEST-PLAN`, which
already carries the verification command and, for a performance issue, both
measurements. Record it as soon as it exists (`--event pr-created --field
issue=<n> --field pr=<url>`), before CI: a run that stops mid-watch must still
show what was opened.

### 5. Verify the auto-close link

```bash
{SKILL_DIR}/scripts/link_check.sh <pr> --issue <n> --fix
```

Cheap, and it is the one check that decides whether this run actually closes
anything. `--fix` appends the missing `Closes #N` itself. `WRONG_BASE` means the
PR targets a non-default branch — retarget it (`gh pr edit <pr> --base
<default>`) before merging, or the issue stays open.

### 6. Review before CI — a context that did not write the diff

Between the PR existing and CI judging it there is one review pass that catches
what CI cannot: whether the change is what issue #N asked for, needless
complexity, maintainability, and tests that would still pass with the bug
present. Write the filled Review template from
[references/delegation-templates.md](references/delegation-templates.md) to
`<runstate>/prompts/<n>-review.md` and run it from here against the worktree:

```bash
{SKILL_DIR}/scripts/codex_run.sh task --cwd <worktree> --prompt-file <runstate>/prompts/<n>-review.md
```

No `--write`: the reviewer is read-only at the sandbox level, so it reports
defects and cannot quietly patch them. It is a **separate run** from the one
that implemented the change — that is the point — and `--cwd <worktree>` is what
makes it reachable from here.

For a **heavy diff** — one that touches a schema, storage layer, or public
contract; adds or bumps a dependency; or rewires behavior across several modules
— add the adversarial pass, whose template is in the same file and whose axis is
the one the Review template does not judge. Issue both in one message.

```bash
{SKILL_DIR}/scripts/codex_run.sh review --cwd <worktree> --base <default_branch> \
    --focus-file <runstate>/prompts/<n>-adversarial.md
```

It returns `review_verdict: approve | needs-attention` plus one line per finding
with severity, file, line range, and confidence; exit 1 means
`needs-attention`. On the bare `codex exec` rung it returns
`review_verdict: UNSTRUCTURED` and free text instead, and the exit code reports
only whether the run completed — read the text, and record the status as
`codex+adversarial(unstructured)`. `UNPARSED` means the structured result did
not come back; treat it the same way. When both passes ran, merge their findings
by `file:line` before applying, or a defect both saw is fixed twice.

**Read `INTENT-MATCH` before the findings.** `no` says the diff is not issue
#N's change — a scope defect, not a review finding, and it can arrive with an
empty `FINDINGS:` list. Send the missing part back through the fix run below, or
re-run the Implementation template when most of the change is absent. A `TESTS:`
verdict saying the tests pin the implementation rather than the behavior is
treated as a finding.

Apply the findings in the worktree — a further `codex_run.sh task --write --cwd
<worktree>` run carrying them verbatim, or here when the fix is a line or two,
or an `opus` worker in the worktree with no usable Codex — then commit
(`review: <what was fixed>`), push, and re-run the verification command, so CI
judges the reviewed code rather than the pre-review commit. Fix the cause, never
the check: a finding cleared by deleting a test, loosening an assertion, or
silencing a warning is a failed outcome and goes on this context's own
`UNRESOLVED` list instead — the review run has no such field. One round is the
ceiling; what is still open after it stays on that list, or goes to step 9 as a
follow-up if it is outside issue #N's scope, rather than blocking the merge.

Record which rung ran (`--event review --field pr=<n> --field
status=<codex|codex+adversarial|DELEGATED|UNAVAILABLE> --field
intent_match=<yes|no> --field unresolved=<count>`). With no usable Codex, take
the highest rung still reachable — the ladder and its reporting duties are in
[references/platform-notes.md](references/platform-notes.md). Never re-read your
own diff and call that a review.

### 7. CI to green

Redirect the watch and read back only the verdict lines. On `FAIL` its raw
output carries up to five failing runs' log tails, which must not enter this
context:

```bash
{SKILL_DIR}/scripts/ci_watch.sh <pr> --timeout 1800 > <runstate>/ci/<pr>.log
grep -E '^(verdict|mergeable|merge_state|review_decision):' <runstate>/ci/<pr>.log
```

That one call is both the watch and the repair run's input — do not watch twice.
Keep the failing check names from `failed_checks:` in that file; the repair
template's intent line needs them. It is the run's only wait primitive: one
blocking call per wait, and neither this context nor any worker hand-rolls a
`sleep`/poll loop around `gh`. In `all` mode with several PRs in flight, run the
watches concurrently where that is available, issued in one message; otherwise
one at a time. Record each verdict (`--event ci --field pr=<n> --field
verdict=<...>`), including one that took repair attempts to reach.

Only on `FAIL`, hand the repair to Codex using the CI repair template in
[references/delegation-templates.md](references/delegation-templates.md), which
takes the log path as `{ci_log_path}`:

```bash
{SKILL_DIR}/scripts/codex_run.sh task --write --cwd <worktree> --prompt-file <runstate>/prompts/<n>-cifix.md
```

Codex reads that log, fixes the cause, commits, and pushes; this context
re-watches and decides whether to go again — up to **3 attempts** total. The
loop lives here because only this context can watch. `PUSHED: no` means the run
declined to push — a wrong-test or flaky-job claim, which is a human decision —
so read `UNRESOLVED` and stop the loop rather than re-watching unchanged code.
If the same failure survives two attempts, put the accumulated detail in the
third prompt rather than sending the same instruction again. With no usable
Codex, fall back to a `sonnet` worker per failing PR where delegation is
available — escalating to `opus` after two failed attempts — otherwise inline.

A green CI is the goal. A check that passes because a test was deleted, skipped,
or weakened is a failed outcome and gets reported as such — same for a "flaky"
job re-run until it happens to pass without a diagnosis.

`NO_CHECKS` — this repo has no CI on this PR. Do not merge on the absence of
evidence: run the project's own verification command (the one the implementing
run reported) in the branch worktree, and merge on a local green. If the project
has no such command either, say so explicitly in the report and ask before
merging. `verdict: ERROR` is not a green either — the check results could not be
read at all; re-read them with `gh` before going near a merge.

### 8. Merge and confirm the issue closed

```bash
{SKILL_DIR}/scripts/land_pr.sh <pr> --issue <n>
```

Merge automatically once step 7 reported a green `verdict: PASS`. The script
re-checks the closing link before merging and confirms the issue really closed
after; read both lines it prints, `result:` and `issue:`. Six results need
different handling and one of them must never be read as success —
[references/landing-outcomes.md](references/landing-outcomes.md) has the table.

Record the outcome (`--event merged ...`) as it happens, in both modes. In `all`
mode, also rebase every still-in-flight branch onto the updated default branch
after each merge, before its CI run — and re-rank the remaining issues with
`issue_digest.py --select`, since a merged blocker can move a dependent from
BLOCKED to top of the list. That re-rank is one script call now that priority is
labeled; do not re-run the research pass per merge.

### 9. File the findings the run turned up

Every run surfaces defects that are not the issue being shipped — returned under
`SCOPE-NOTES`, `OUT-OF-SCOPE`, or `FOLLOW-UPS` by the implementation, review, or
CI-repair runs. Fixing one inline silently widens a PR that is about to
auto-merge; saying it only in the final report loses it the moment the
conversation ends.

[references/filing-followups.md](references/filing-followups.md) settles what to
file, what to fix inline, what is an operator action rather than an issue, and
what a body must contain. **Read it before filing anything** — including the
rule that a returned observation is a lead to verify, not a fact, because that
check routinely changes the tier.

Write the body to a file under `<runstate>/`, then:

```bash
python3 {SKILL_DIR}/scripts/file_followup.py \
    --title "<repo's title convention>" --body-file <path> \
    --tier P2 --label <area label> --found-while <n>
```

`--tier` is required and follows
[references/priority-rubric.md](references/priority-rubric.md) — the same rubric
step 2 ranks by, so the finding enters the backlog already ordered against
everything else. The script resolves the tier label the repo *already* uses
(`p2` stays `p2`; a second `priority: P2` vocabulary would split the backlog in
two), drops `--label` values the repo lacks instead of failing, and echoes the
resolved repo. Exit 2 (`NO_WRITE_ACCESS`) means report the finding in step 11
instead. Add `--repo OWNER/NAME` whenever cwd may not be the repo being shipped.

File as you go, right after the PR that surfaced the finding lands — not batched
at the end, where an interrupted run loses them all. Record it (`--event
followup`) as it happens, same as any other outcome.

### 10. Clean up — once, at the end, script only

The main worktree's `HEAD` is still on whatever branch was last implemented,
and cleanup's branch pass refuses to delete a branch checked out there — so
switch back to the default branch, fast-forwarded, **before** cleanup runs,
not after (a stale checkout also hands the next run a stale base):

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
begin with: prompts, issue bodies and CI logs all live under `<runstate>/`.

**The worktree pass is not merge-gated by default: it removes every worktree
under that root, including one another session is mid-run in.** That is correct
at the end of a run this skill owns end to end, and wrong everywhere else. When
other sessions may be working in the same repo — or when cleaning up outside a
run, purely to reclaim disk — pass `--merged-only`, which keeps any worktree
whose branch has no merged PR (or still has an open one). Worktrees are
expensive to leave lying around: each one carries its own `.venv` and type-check
caches, so a few stale ones can add up to gigabytes. Prefer the repo's own
cleanup recipe when it exposes one, so cleanup does not depend on this skill's
path.

Record the cleanup outcome (`--event cleanup ...`) and report anything it left
`SKIPPED`.

### 11. Report

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
(resolved by running a command or changing a setting, not by a PR) get their own
lines here — the backlog will never show them, so the report is their only
record.

Then list what was left undone — blocked issues, ones needing clarification,
ones that hit the retry ceiling — with the specific reason each.

## Cost discipline

What belongs in this context versus a delegated run, the per-issue Codex-run
budget, and why the model assignments are what they are — read
[references/cost-discipline.md](references/cost-discipline.md) before delegating
a step or changing a run count.

## Stop conditions

Stop the whole run and report when: preflight is BLOCKED, a dependency cycle
needs a human to break it, a merge conflict requires a product decision, or the
same CI failure survives the retry ceiling on two different issues (the problem
is the base branch, not the change).

Record it before stopping (`--event blocked --field reason=<what stopped it>`).

In `all` mode, a single failed issue does not stop the run — mark it FAILED,
record it the same way, skip anything that depended on it, and continue.

## Platform notes

Codex-runtime constraints for this skill, the fallback ladders when no usable
Codex is present, and the best-effort degradations:
[references/platform-notes.md](references/platform-notes.md).
