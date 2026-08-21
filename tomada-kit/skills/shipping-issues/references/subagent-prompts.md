# Sub-agent Prompt Templates

## Table of Contents

- [Priority research and labeling](#priority-research-and-labeling-sonnet)
- [Implementation](#implementation-opus-isolation-worktree-for-parallel-batches)
- [Self-review by delegation](#self-review-by-delegation-opus-heavy-diff--sonnet-otherwise)
- [CI repair](#ci-repair-sonnet-spawned-only-on-fail)
- [Merge and issue closure](#merge-and-issue-closure-no-spawn)

Copy-and-fill templates for the spawns this skill makes. Each carries intent,
concrete paths, embedded context, and an output contract, so the parent never
receives raw `gh` JSON or full CI logs.

Model choices follow `orchestrating-models` §2: unresolved spec → `opus`,
fully specified pass/fail → `sonnet`. <!-- derived from orchestrating-models §2 -->

Placeholders in `{braces}` are filled by the parent before spawning.

## Priority research and labeling (`sonnet`)

Spawned only when more than ~3 open issues still lack a `priority:` label, or
when the top rows of a labeled backlog are close enough that the pick needs
evidence. On a fully labeled backlog, `issue_digest.py --select` is the answer
and no spawn is warranted.

The agent writes the labels itself — that is the point of the spawn. The parent
gets the pick and a summary line; the per-issue tier list never crosses back.

```
Intent: I am about to implement and ship GitHub issues in {owner}/{repo}. Priority
in this repo is stored as `priority: P0`…`P3` labels, and {unlabeled_count} open
issues have no label yet. I need those labels written, and the single
highest-priority shippable issue back, with the evidence behind it. I will act on
your ordering directly, so an unverified claim costs me a full implement/PR/CI
cycle — and a wrong label costs every later run too.

Read first, in this order:
  {SKILL_DIR}/references/priority-rubric.md
  {SKILL_DIR}/references/dependency-triage.md

Then run and read the full-body digest (do not paste its raw output back to me):
  python3 {SKILL_DIR}/scripts/issue_digest.py {filters}

`~Pn` in the priority column is a suggested tier the script computed but has not
written; `P2(~P0)` is a written label the signals now say is too low. Run the
research pass from priority-rubric.md on the top 3–5 rows only, and verify each
claim you repeat:
  gh issue view <n> --comments        (shortlisted issues only)
  grep for the symbols/paths the body names, to confirm ripple/leverage
  gh run list --branch {default_branch} --limit 5   (only if an issue claims CI/main is broken)

Then write the tiers — one call, both halves:
  python3 {SKILL_DIR}/scripts/apply_priority_labels.py \
      --backfill --set <n>=<tier> --set <m>=<tier> --quiet

`--backfill` takes the script's suggestion for every issue you did not examine;
each `--set` overrides one you did, including any `P2(~P0)` you confirmed. Do not
re-tier an issue you have no evidence about — the suggestion is better than a
guess. Exit code 2 means the token cannot write labels here: report that instead,
and rank from the suggestions.

Return exactly these sections, nothing else:

## Labels
- <the apply_priority_labels.py summary line, verbatim>
- overrides: #N P2->P0 <one-line reason>   (only the --set ones, one line each)

## Selected
- #N — <title> — <tier>
  - unblocks: <#M, #K and why each is genuinely blocked, or "none">
  - leverage: <what shared ground it touches, with the path you verified, or "none">
  - urgency: <damage being taken now, with evidence, or "none">
  - likely files: <paths> — est. size S/M/L

## Order after that
- #N <tier> — one-line reason it comes next — likely files — S/M/L

## Blocked
- #N — blocked by #M (explicit | inferred: <which rule from dependency-triage.md>)

## Needs clarification
- #N — the specific missing information

## Parallel-safe groups
- [#A, #B] — disjoint file sets
- serialize: #C (touches {lockfile/CI/schema})

If the top two are genuinely tied on every axis of the rubric, list both under
"Unresolved" with the trade-off rather than picking one.
```

## Implementation (`opus`, `isolation: "worktree"` for parallel batches)

Implementation carries unresolved spec by definition — always `opus`.

```
Intent: You are shipping GitHub issue #{n} in {owner}/{repo} end to end. Your
branch will be merged automatically once CI is green, and issue #{n} must close
when it merges — so the PR must be complete, correct, and correctly linked.

<issue>
{full issue body + relevant comments, pasted by the parent}
</issue>

<context>
Repo root: {path}
Base branch: {default_branch}   <- the PR MUST target this branch; GitHub only
                                   auto-closes issues on merges into the default branch
Likely files: {paths from triage}
Project conventions: read {repo}/CLAUDE.md and {repo}/AGENTS.md before writing code.
Related decisions already made: {anything the parent resolved}
</context>

Do:
1. Read the project's own instruction files and follow them, including its test
   and commit conventions. If the project ships its own skills for committing or
   opening PRs (check {repo}/.claude/skills/), use them instead of raw git/gh.
2. Create a branch named {type}/{n}-{slug} off {default_branch}. If the issue
   claims a performance improvement (runtime, throughput, memory, latency),
   measure the *before* state right here, on the unmodified code, using the
   exact command you will re-run after implementing — an existing number in
   the issue body is not a substitute, it was not measured under your
   conditions. Measuring later, after step 3 has already changed the code,
   leaves no clean baseline to measure.
3. Implement the issue's stated scope. Deliver what the issue asks, at the scope
   it asks. If a better approach exists, note it in the PR body in one sentence
   and implement as asked.
4. Add or update the tests that cover the change, and run the project's own
   verification command (check its CLAUDE.md/AGENTS.md/justfile/Makefile for it).
   Report the exact command — the parent needs it if this repo has no CI.
   For a performance issue, re-run step 2's baseline command now, under the
   same conditions, and state why the delta is a real improvement and not
   noise. Put both numbers and the command in the PR body's test plan, and
   report them under MEASURE below.
5. Commit in coherent increments, and push as soon as the first coherent commit
   exists — a stopped agent's worktree keeps only what was pushed. Then open
   the PR against {default_branch} with a body whose FIRST
   line after the summary is exactly:  Closes #{n}
   (not "see #{n}", not "related to #{n}" — those do not close anything), plus a
   summary and a test plan.
6. Confirm GitHub actually registered the link, and repair it if not:
     {SKILL_DIR}/scripts/link_check.sh <pr> --issue {n} --fix
   Report its verdict verbatim. Do not return until it says LINKED, or explain
   why it cannot.
7. Self-review the branch before it reaches CI, with the effort level chosen
   from the diff you just produced. Take the first rung that is actually
   available to you: (a) a built-in review pass; (b) no built-in one, but you
   can delegate — hand the branch to one independent reviewer using the
   Self-review template in this file and apply what it returns; (c) neither —
   report REVIEW: UNAVAILABLE and continue. Rung (b) is a real review because
   the reviewer reads the diff in a context that never wrote it; re-reading
   your own diff yourself is not, so do not report that as a review.
   With a built-in pass available:
   - Heavy diff (touches a schema, storage layer, or public contract; adds or
     bumps a dependency; or rewires behavior across several modules): one pass
     at high effort, applying its findings to the working tree.
   - Anything else: one pass at low effort, applying its findings, twice — the
     second pass reviews the code as the first pass changed it.
   Applying findings updates the working tree but does not commit them.
   So, per pass: read what it changed, commit it on its own
   (`review: <what was fixed>`), and push before any next pass, so it sees the
   fixed code. Re-run the step 4 verification command after the final pass and
   report that final result under VERIFY.
   The pass count is a ceiling: after the final pass there is no further
   review round. Findings still open at that point go under UNRESOLVED (in
   scope) or FOLLOW-UPS (out of scope) — the parent merges and files them
   rather than iterating.
   Fix the cause, never the check: clearing a finding by deleting a test,
   loosening an assertion, or silencing a warning is a failed outcome — say so
   under UNRESOLVED instead. A finding outside issue #{n}'s scope does not get
   fixed here; it goes under FOLLOW-UPS and the parent files it.
   With no built-in pass but delegation available, spawn one reviewer (the
   Self-review template below), fix the causes it names in your worktree,
   commit (`review: <what was fixed>`), push, re-run the step 4 verification
   command, and report REVIEW: DELEGATED with the finding and fix counts. One
   reviewer, one round — leftovers go to UNRESOLVED / FOLLOW-UPS as above.
   With neither, report REVIEW: UNAVAILABLE and continue — do not re-read your
   own diff and call it a review.
8. Do NOT clean up after yourself — no `rm`, no worktree removal, no branch
   deletion; the parent runs one batch cleanup at the end. If you produced
   gitignored artifacts (fixtures, bench outputs) in a worktree, copy them into
   the main checkout at {repo root} before returning or they will be lost.
   Do not watch CI or wait on anything after your final push either — the
   parent watches CI; return as soon as the review passes have landed.

Return exactly:
BRANCH: <name>
PR: <url or "none" + reason>
BASE: <branch the PR targets>
LINK: <link_check.sh verdict — LINKED | NOT_LINKED(<detail>) | WRONG_BASE>
CHANGED: <file list>
VERIFY: <exact command run> -> <pass/fail + the failing output if any>
MEASURE: <perf issue: command + before + after + why it counts as improved. Otherwise "n/a">
REVIEW: <effort level + per pass: N findings, M applied>
        <or "DELEGATED: N findings, M applied">
        <or "UNAVAILABLE" + why>
SCOPE-NOTES: <anything in the issue you did not implement, and why>
FOLLOW-UPS: <defects you saw that are NOT this issue, one per line as
             `file:line — what is wrong — what prevents it today`, or "none">
UNRESOLVED: <judgment calls you had to make, or "none">

Every value in that return must come from a command output in this session —
the parent re-verifies the PR, CI, and closure against GitHub, so a remembered
or assumed value is caught and costs a full re-check. If a step did not run,
say so instead of filling the field.

FOLLOW-UPS is how a real defect you must not fix here still survives the run —
the parent files it as its own issue (SKILL.md step 6.5). Report it there
rather than widening this PR, and rather than staying silent about it. Always
include what currently prevents it (a guard at another layer, a provider that
filters the input, a caller that cannot reach it) or "nothing": the parent tiers
the issue on exactly that, and "nothing" versus "an adapter drops it first" is
the difference between a live bug and a missing defense layer. Do not file the
issue yourself — you see only your own worktree.

If the issue cannot be implemented as written, stop before creating a branch and
return only UNRESOLVED with what is missing.
```

## Self-review by delegation (`opus` heavy diff / `sonnet` otherwise)

Used only when no built-in review pass is reachable but delegation is — rung
(b) of step 7 above. Spawn it from wherever the branch is held: the
implementation agent when it can delegate, otherwise the main context after
that agent returns `REVIEW: UNAVAILABLE` (SKILL.md step 4.5). The reviewer is
read-only and never touches the branch; the holder applies the fixes.

`opus` when the diff is heavy (schema, storage layer, public contract, new or
bumped dependency, behavior rewired across modules), `sonnet` otherwise.

```
Intent: PR #{pr} implements issue #{n} and merges as soon as CI is green. Lint,
types and tests already pass — CI will re-check them. What no one has done is
read the change as a change. That is your job, and you are reading it in a
context that did not write it.

The branch {branch} is checked out at {worktree_path}. Read the issue and the
diff against {base}:
  gh issue view {n}
  git -C {worktree_path} diff {base}...HEAD

Judge exactly what CI cannot:
- does the implementation match what issue #{n} actually asked for — nothing
  missing, nothing quietly widened beyond it;
- unnecessary complexity: indirection, options, or abstraction the issue did
  not need;
- maintainability: names that mislead, duplicated logic, a comment that is
  already wrong about the code beside it;
- the tests: do they pin the behavior the issue is about, or only the shape of
  the implementation? A test that would pass with the bug still present is a
  finding;
- anything the diff walked past — a sibling of the case it fixed, an error path
  it left silent.

Report the defect, never the patch: file, line, what is wrong, why it matters.
The holder of the branch re-derives the fix in the code it can see; a patch
written from your context is how a review fix causes the next regression.
Do not edit, commit, or push anything.

Rank findings by whether they should block this merge. A finding outside issue
#{n}'s scope is still worth reporting — mark it OUT-OF-SCOPE and it becomes a
follow-up issue rather than a change to this PR.

Return exactly:
FINDINGS: <one per line as `file:line — what is wrong — why it matters`, or
           "none">
OUT-OF-SCOPE: <same shape, or "none">
TESTS: <verdict on the test changes in one or two lines>
INTENT-MATCH: <does the diff implement issue #{n} as written — yes / no + what
               is missing or extra>
```

## CI repair (`sonnet`, spawned only on FAIL)

Fully specified pass/fail work — `sonnet`. The parent runs `ci_watch.sh` in its
own context first (a green first watch needs no agent) and spawns this only on
a `FAIL` verdict. Escalate to `opus` only if the same failure survives two
repair attempts.

```
Intent: PR #{pr} implements issue #{n} and will be merged as soon as CI is green.
Its CI just failed: {failing_check_names_from_parent_watch}. I need it green, or
a clear statement of why it cannot be.

Start by reading the failing logs:
  {SKILL_DIR}/scripts/ci_watch.sh {pr} --timeout 1800

If verdict is NO_CHECKS, this repo has no CI on this PR. Do not merge on that
alone: run the project's own verification command in the branch worktree at
{worktree_path} — {verify_command} — and report its result as LOCAL-VERIFY.

If verdict is FAIL: read the failing logs the script printed, fix the cause in
the branch worktree at {worktree_path}, commit, push, and re-run ci_watch.sh.
Repeat at most {max_retries} times total. ci_watch.sh is your only wait
primitive — it blocks until checks settle; never write a sleep/poll loop
around `gh` instead.

Fix the failure, not the check. Deleting, skipping, or weakening a test to make
CI pass is a failed outcome — if the test is genuinely wrong, say so in
UNRESOLVED and stop. Same for retrying a flaky job without diagnosing it: if you
believe a failure is flaky, say which job and why, do not just re-run until green.

Return exactly:
VERDICT: PASS | FAIL | TIMEOUT | NO_CHECKS
ATTEMPTS: <n>
LOCAL-VERIFY: <command -> pass/fail, or "n/a (CI present)">
FIXES: <one line per repair commit, or "none">
REMAINING-FAILURE: <check name + the 5 most relevant log lines, or "none">
MERGE-STATE: <mergeable / merge_state / review_decision from the script>
FOLLOW-UPS: <defects the failure exposed that are NOT this PR's to fix, one per
             line as `file:line — what is wrong — what prevents it today`, or
             "none">
UNRESOLVED: <anything needing a human, or "none">
```

A CI failure is a good detector of pre-existing problems — a flaky job with a
real race behind it, a check that only passes because of ordering, a fixture
that has been wrong for months. Put those under FOLLOW-UPS with what currently
prevents them, so the parent can file them (SKILL.md step 6.5); fix only what
makes *this* PR green.

## Merge and issue closure (no spawn)

Landing is one script call and a verdict read — run it in the main context:

```
{SKILL_DIR}/scripts/land_pr.sh {pr} --issue {n}
```

`--issue {n}` makes the script re-check the closing link before merging (and
repair a missing `Closes #{n}`), then confirm after the merge that issue #{n}
really closed — closing it explicitly if GitHub's auto-close did not fire.

Add `--auto` when `ci_watch.sh` reported `review_decision: REVIEW_REQUIRED` or
`merge_state: BLOCKED` for a reason other than failing checks.
