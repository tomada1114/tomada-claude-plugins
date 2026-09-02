# Delegation Prompt Templates

## Table of Contents

- [Priority research and labeling](#priority-research-and-labeling-sonnet)
- [Implementation](#implementation-step-3)
- [Review fix, parallel mode](#review-fix-parallel-mode)
- [Review fallback](#review-fallback)
- [CI repair](#ci-repair-step-6-only-on-fail)
- [Design decision](#design-decision-step-8b)

Every sub-agent this skill spawns is a fully self-contained prompt: it cannot
ask a question back, so a hole in it returns as a decision made alone rather
than as a question. Leave nothing merge-gating unguessed. The parent — this
session — owns everything that talks to the GitHub API (issue/PR data,
opening the PR, `link_check.sh`, `ci_watch.sh`, `land_pr.sh`) and every
merge-gating judgment; a sub-agent only touches code inside the checkout.

`{workdir}` below is the one thing every template must get right: the repo's
main checkout in serial mode, that issue's worktree
(`<runstate>/worktrees/<n>`) in parallel mode. **Two sub-agents never share a
working directory** — that invariant is what makes parallel mode safe, and
filling `{workdir}` with the main checkout for two concurrent runs breaks it
silently rather than loudly. The read-only templates are the exception, and
only because they write nothing: the review fallback and the design agent read
a checkout others are working in without disturbing it. Everything downstream of implementation still
runs one PR at a time in the parent.

## Priority research and labeling (`sonnet`)

Spawned only when more than ~3 open issues still lack a `priority:` label, or
when the top rows of a labeled backlog are close enough that the pick needs
evidence. On a fully labeled backlog, `issue_digest.py --select` is the answer
and no spawn is warranted.

The worker writes the labels itself — that is the point of the handoff. What
comes back is the pick with its evidence, the order behind it, and the
blocked/unclear lists; the issue prose and the raw digest table never cross
back. In `all` mode it also returns proposed parallel-safe groups — a
proposal, not a decision: [step 2c](../SKILL.md#2c-group-for-parallelism--all-mode-only)
still has to clear the repository's own viability gate before any of it runs.

Prompt body: `references/agents/priority-research.md`. Fill its `{brace}`
placeholders from the current repo and run count, then spawn a `sonnet`
sub-agent with it.

## Implementation (step 3)

Spawn a **`sonnet`** sub-agent, one issue at a time, with:

```
Implement GitHub issue #{n} in {owner}/{repo}. Once you return, your branch is
turned into a PR and merged automatically once CI is green, so it must be
complete and correct by the time you push. You cannot ask me a question
mid-run — if something is genuinely undecidable, make the call, implement it,
and report it under UNRESOLVED.

Work only inside {workdir} — not any sibling checkout or worktree of the same
repository. {workdir_note}

<task>
{the full issue body, plus the comments that change the spec, pasted}
</task>

<context>
Work directory: {workdir}   {"<- already provisioned: dependencies installed,
                              local config copied, baseline verified" in
                              parallel mode; omit in serial mode}
Base branch: {base_branch}
Branch: {branch_name}             <- already created and checked out; do not
                                      create a new one
Likely files: {paths from step 2's triage, or — when step 2 was skipped on a
               labeled backlog — a short grep/glob the parent runs against
               the issue's own keywords right before spawning; never blank}
Project conventions: read {workdir}/CLAUDE.md and
{workdir}/AGENTS.md before writing code.
Decisions already made: {anything step 2/2b resolved, so it is not re-opened}
Verification command: {verify_command, from step 3's smoke run — if that
                        smoke run found none, say so explicitly here rather
                        than asking the sub-agent to locate one}
</context>

Do:
1. Read the project's own instruction files and follow them, including its
   test and commit conventions.
2. If the task claims a performance improvement (runtime, throughput, memory,
   latency), measure the *before* state here, on the unmodified code, with the
   exact command you will re-run afterwards.
3. Implement the stated scope. Deliver what the task asks, at the scope it
   asks. If a better approach exists, say so in one sentence under
   SCOPE-NOTES and implement as asked.
4. Add or update the tests that cover the change, and run the verification
   command above. Report the exact command. For a performance task, re-run
   step 2's baseline under the same conditions and report both numbers under
   MEASURE.
5. Commit in coherent increments, and push as soon as the first coherent
   commit exists — a run stopped mid-way keeps only what was pushed.
6. Two hard prohibitions, both irreversible from here: do NOT touch the
   GitHub API at all (the parent opens the PR and watches CI), and do NOT
   delete anything — no `rm`, no branch deletion, no worktree removal.
7. {Parallel mode only:} If you produce a gitignored artifact worth keeping —
   a fixture, a benchmark result, a generated file the change does not commit
   — copy it into {repo_root} before you return and name it under
   SCOPE-NOTES. Your working directory is a worktree and is deleted at the
   end of the run; anything gitignored inside it goes with it.

Return exactly:
BRANCH: <name>
PUSHED: <yes + the remote ref, or "no" + why>
CHANGED: <file list>
VERIFY: <exact command run> -> <pass/fail + the failing output if any>
MEASURE: <performance task: command + before + after + why it counts as
          improved. Otherwise "n/a">
SCOPE-NOTES: <anything in the task you did not implement, and why>
FOLLOW-UPS: <defects you saw that are NOT this task, one per line as
             `file:line — what is wrong — what prevents it today`, or "none">
UNRESOLVED: <judgment calls you had to make, or "none">
PR-TITLE: <one line the parent can use verbatim>
PR-SUMMARY: <2-4 lines: what changed and why, for the PR body>
TEST-PLAN: <what the parent should put under the PR's test plan, including the
            verification command and, for a perf issue, both numbers>

Every value in that return must come from a command output in this session.
If a step did not run, say so instead of filling the field.
```

`FOLLOW-UPS` is how a real defect the run must not fix here still survives:
step 8 files it as its own issue. `SCOPE-NOTES` and `UNRESOLVED` feed the same
step and the step 10 report.

Scope is **branch to pushed commits**; the PR, the review, CI, and the merge
belong to the parent. Push discipline is the run's insurance: it pushes as
soon as its first coherent commit exists, so a stopped run loses at most its
uncommitted tail — and in parallel mode the worktree itself is temporary, so
an unpushed commit is one cleanup away from gone. It never deletes anything —
that happens once, in the parent's cleanup step (step 9), and only after the
branch is merged.

In parallel mode, issue every implementation prompt in the batch **in one
message**. Spawned one after another they run one after another, which is the
whole thing this mode exists to avoid.

## Review fix, parallel mode

Only in parallel mode, and only for findings this session has already read and
accepted. `/code-review --fix` writes to the session's own working tree, which
in parallel mode is the main checkout sitting on the default branch — the
wrong tree — so the review runs read-only and the writing is delegated here
instead. See [SKILL.md step 4](../SKILL.md#4-review-and-fix--judge-the-result-before-the-pr-exists).

Zero accepted findings → no spawn. Spawn one **`sonnet`** sub-agent per branch
that has any:

```
Branch {branch} implements issue #{n} in {owner}/{repo} and is about to become
a PR. A review has already run against it and I have triaged the findings
myself; below are the ones I accepted. Apply exactly these and nothing else.

Work only inside {workdir} — not any sibling checkout or worktree of the same
repository. Branch {branch} is already checked out there; do not switch
branches, and do not create one.

<findings>
{one per line, as `file:line — what is wrong — why it matters`. Findings the
parent rejected are not listed here and must not be inferred.}
</findings>

Project conventions: read {workdir}/CLAUDE.md and {workdir}/AGENTS.md before
changing anything.
Verification command: {verify_command}

Do:
1. Fix each finding at its cause, not at its symptom.
2. If a finding is wrong on closer reading — the code already handles it, or
   the fix would change behavior the issue did not ask to change — do NOT
   apply it. Report it under REJECTED with the reason. A finding I accepted
   from a summary can still be wrong in front of the code, and you are the
   one in front of the code.
3. Do not fix anything that is not in the list. Real defects you notice go to
   FOLLOW-UPS, not into this diff.
4. Run the verification command, commit, and push.
5. Do NOT touch the GitHub API, and do NOT delete anything — no `rm`, no
   branch deletion, no worktree removal.

Return exactly:
APPLIED: <one line per finding fixed, `F<n> -> <what changed>`, or "none">
REJECTED: <one line per finding not applied, with why, or "none">
VERIFY: <exact command run> -> <pass/fail + the failing output if any>
PUSHED: <yes + the remote ref, or "no" + why>
FOLLOW-UPS: <defects you saw that are NOT in the list, one per line as
             `file:line — what is wrong — what prevents it today`, or "none">
```

`REJECTED` is read, not skimmed — it is the run's only signal that a finding
this session accepted did not survive contact with the code, and a rejection
that reads like a real defect goes back through the same loop with the reason
addressed. `FOLLOW-UPS` feeds step 8 like every other one.

## Review fallback

Only when this session's host will not let it launch `/code-review`
directly — see [SKILL.md step 4](../SKILL.md#4-review-and-fix--judge-the-result-before-the-pr-exists).
Spawn one independent, **read-only** `opus` sub-agent against the branch:

```
Read-only review only — do not edit, create, or delete any file, and do not
run any command that writes to disk or to git. Branch {branch} implements
issue #{n} in {owner}/{repo}. It becomes a PR and merges as soon as CI is
green, so a defect you miss here merges. Lint, types and tests already pass.
What no one has done is read the change as a change. That is your job, and
you are reading it in a context that did not write it.

The branch {branch} is checked out at {workdir}. Read the project's own
conventions first — {workdir}/CLAUDE.md and {workdir}/AGENTS.md — then
the specification and the diff against {base}:

  GIT_OPTIONAL_LOCKS=0 git -C {workdir} diff {base}...HEAD

<spec>
{the issue body, pasted}
</spec>

Judge exactly what the test suite cannot:
- does the implementation match what the spec actually asked for — nothing
  missing, nothing quietly widened beyond it;
- unnecessary complexity: indirection, options, or abstraction the task did
  not need;
- maintainability: names that mislead, duplicated logic, a comment that is
  already wrong about the code beside it;
- the tests: do they pin the behavior the task is about, or only the shape of
  the implementation? A test that would pass with the bug still present is a
  finding;
- anything the diff walked past — a sibling of the case it fixed, an error
  path it left silent.

Report the defect, never the patch: file, line, what is wrong, why it matters.
I re-derive the fix in the code I can see.

Attach a severity and a confidence to every finding and report all of them; I
decide what blocks. A finding outside this task's scope is still worth
reporting — mark it OUT-OF-SCOPE.

Return exactly:
FINDINGS: <one per line as `F<n> [sev] file:line (conf) — what is wrong — why
           it matters`, sev = high|medium|low and conf = high|medium|low, or
           "none">
OUT-OF-SCOPE: <same shape with `O<n>` instead of `F<n>`, or "none">
TESTS: <verdict on the test changes in one or two lines>
INTENT-MATCH: <does the diff implement the spec as written — yes / no + what
               is missing or extra>
```

`INTENT-MATCH: no` is read before the findings — it says the diff is not
issue #{n}'s change and can arrive with an empty `FINDINGS:` list; send the
missing part back through the Implementation request. Triage every finding in
this session before fixing anything, the same way `--fix`'s output is
triaged.

## CI repair (step 6, only on `FAIL`)

Only after `ci_watch.sh` returns `FAIL`. Write the failing log to a file
**outside** the working directory first (`<runstate>/ci/<pr>.log`) — a stray
untracked file inside it makes cleanup skip the directory as dirty, and a
commit convention that stages everything would land the log in the change. Spawn a **`sonnet`** sub-agent
(escalate to **`opus`** once the same failure has survived two attempts in a
row), one PR at a time:

```
PR #{pr} implements issue #{n} in {owner}/{repo}; its CI just failed:
{check names, from the parent's failed_checks: line}. I need the cause fixed
and pushed. I will re-check after you return — you cannot, and must not try
to.

Work only inside {workdir}, on branch {branch} — already checked out. Do not
touch any sibling checkout or worktree of the same repository.

<spec>
{the issue body, pasted — so a fix that changes behavior can be judged
against what the issue actually asked for}
</spec>

Base branch: {base_branch}
Verification command: {verify_command, from step 3's smoke run}
Project conventions: read {workdir}/CLAUDE.md and {workdir}/AGENTS.md
before changing anything.

The failing output is in:
  {log_path}

Read that file first. It is outside your work directory; read it there and do
not copy it in. Then fix the cause at {workdir}, commit, and push. Do
not touch the GitHub API, do not watch CI, do not sleep or poll — return as
soon as your fix is pushed.

This is attempt {attempt} of 3. {What the previous attempts tried and why it
did not work — leave empty on attempt 1, and never re-send the same
instruction twice; from attempt 3, the accumulated detail rather than the same
instruction again.}

Fix the failure, not the check. Deleting, skipping, or weakening a test to
make it pass is a failed outcome — if the test is genuinely wrong, say so in
UNRESOLVED and stop without pushing. Same for a flaky job: if you believe a
failure is flaky, say which job and why under UNRESOLVED rather than pushing a
no-op commit to re-trigger it.

Return exactly:
CAUSE: <what actually failed, in one or two lines>
FIXES: <one line per repair commit, or "none">
PUSHED: <yes + the remote ref, or "no" + why — "no" ends the repair loop; I do
         not re-check unchanged code>
FOLLOW-UPS: <defects the failure exposed that are NOT this change's to fix,
             one per line as `file:line — what is wrong — what prevents it
             today`, or "none">
UNRESOLVED: <anything needing a human, or "none">
```

The log reaches the run through that path, never through the prompt, so it
never lands in the parent's context. The watch/repair loop — repair, push,
re-watch, up to 3 attempts — lives in the parent. `PUSHED: no` ends the loop;
read `UNRESOLVED` rather than re-watching unchanged code.

## Design decision (step 8b)

Spawned at [SKILL.md step 8b](../SKILL.md#8b-unblock-held-designs-in-the-background),
one **`opus`** sub-agent per design-blocked issue, **in the background** — this
session spawns a round in one message and goes straight back to shipping.

This is the only sub-agent in this skill that writes to GitHub, and only two
writes: one comment on the issue and one label clear. It writes nothing in the
checkout, so `{workdir}` is the repo's main checkout even while a parallel batch
is running — it reads there, it never touches the tree.

```
Decide the design for GitHub issue #{n} in {owner}/{repo}, completely enough
that a later run can implement it without deciding anything. You are not
implementing it: write no code, create no branch, open no PR, and modify no
file in the repository.

Read, in this order:
  - the issue and its thread:
    gh issue view {n} --repo {owner}/{repo} --comments
  - the project's own conventions: {workdir}/CLAUDE.md, {workdir}/AGENTS.md
  - the code the issue names, and the nearest thing this repo already does that
    solves a similar problem — your design has to look like it, not like a
    greenfield design

<issue>
{the issue body, pasted}
</issue>

Decide, concretely enough that an implementer never guesses:
- the approach, and the alternatives you rejected with the reason each lost;
- the files and functions that change, and the new ones that appear;
- the data, schema, config and API surface it touches: exact names, shapes,
  defaults, and the migration or compatibility path;
- behavior at the edges — errors, empty, concurrent, already-migrated,
  backward compatibility with what is deployed;
- what the tests must pin, case by case;
- what is explicitly out of scope for this issue.

Two things you must not do:
- Do not decide a product or UX call the repo and the issue thread do not
  already answer: what a user is promised, a policy, a price, wording a user
  sees, a trade between two user-visible behaviors. Return DEFERRED with the
  exact question instead — one question, answerable in a sentence.
- Do not widen the issue. If your design only works by also changing something
  the issue does not mention, say so under RISKS rather than folding it in.

On DECIDED, write it back to GitHub yourself, in this order:
  1. post the design as a comment — it is the design of record and must stand
     alone, without this conversation, starting with `## Design decision`:
     gh issue comment {n} --repo {owner}/{repo} --body-file <file>
  2. only after that comment posted, clear the block:
     python3 {SKILL_DIR}/scripts/apply_priority_labels.py --clear-design {n}
On DEFERRED do neither — the issue must stay blocked.

Return exactly:
VERDICT: DECIDED | DEFERRED
APPROACH: <the decision itself, 2-4 lines>
SCOPE: <the files and surfaces that change, one line>
OPEN-QUESTION: <on DEFERRED, the one question a human must answer; else "none">
RISKS: <what this design assumes or could get wrong, or "none">
COMMENT: <url of the comment you posted, or "none">
LABEL: cleared | left-on
```

`VERDICT: DEFERRED` is a result, not a failure — it is the run declining to
invent a product decision, and its `OPEN-QUESTION` is what the step 10 report
puts in front of the user. `LABEL: left-on` with `VERDICT: DECIDED` means only
the label write failed: clear it from this session before treating the issue as
ready. `APPROACH` is the only part worth reading closely in this context — the
full design lives on the issue, where the implementer will read it.
