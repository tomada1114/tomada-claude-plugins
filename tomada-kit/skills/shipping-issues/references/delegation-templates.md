# Delegation Prompt Templates

## Table of Contents

- [Priority research and labeling](#priority-research-and-labeling-sonnet)
- [Implementation](#implementation-step-3)
- [Review fallback](#review-fallback)
- [CI repair](#ci-repair-step-6-only-on-fail)

Every sub-agent this skill spawns is a fully self-contained prompt: it cannot
ask a question back, so a hole in it returns as a decision made alone rather
than as a question. Leave nothing merge-gating unguessed. The parent — this
session — owns everything that talks to the GitHub API (issue/PR data,
opening the PR, `link_check.sh`, `ci_watch.sh`, `land_pr.sh`) and every
merge-gating judgment; a sub-agent only touches code inside the checkout.
This is also why every step runs **one issue at a time**: two sub-agents never
share the same checkout concurrently.

## Priority research and labeling (`sonnet`)

Spawned only when more than ~3 open issues still lack a `priority:` label, or
when the top rows of a labeled backlog are close enough that the pick needs
evidence. On a fully labeled backlog, `issue_digest.py --select` is the answer
and no spawn is warranted.

The worker writes the labels itself — that is the point of the handoff. What
comes back is the pick with its evidence, the order behind it, and the
blocked/unclear lists; the issue prose and the raw digest table never cross
back.

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

Work only inside {repo_root} — this is the repo's main checkout, not a
worktree.

<task>
{the full issue body, plus the comments that change the spec, pasted}
</task>

<context>
Work directory: {repo_root}
Base branch: {base_branch}
Branch: {branch_name}             <- already created and checked out; do not
                                      create a new one
Likely files: {paths from step 2's triage, or — when step 2 was skipped on a
               labeled backlog — a short grep/glob the parent runs against
               the issue's own keywords right before spawning; never blank}
Project conventions: read {repo_root}/CLAUDE.md and
{repo_root}/AGENTS.md before writing code.
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
   delete anything — no `rm`, no branch deletion.

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
uncommitted tail. It never deletes anything — that happens once, in the
parent's cleanup step (step 9), and only after the branch is merged.

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

The branch {branch} is checked out at {repo_root}. Read the project's own
conventions first — {repo_root}/CLAUDE.md and {repo_root}/AGENTS.md — then
the specification and the diff against {base}:

  GIT_OPTIONAL_LOCKS=0 git -C {repo_root} diff {base}...HEAD

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
**outside** the repo checkout first — a stray untracked file inside it makes
cleanup skip the directory as dirty, and a commit convention that stages
everything would land the log in the change. Spawn a **`sonnet`** sub-agent
(escalate to **`opus`** once the same failure has survived two attempts in a
row), one PR at a time:

```
PR #{pr} implements issue #{n} in {owner}/{repo}; its CI just failed:
{check names, from the parent's failed_checks: line}. I need the cause fixed
and pushed. I will re-check after you return — you cannot, and must not try
to.

Work only inside {repo_root}, on branch {branch} — already checked out. This
is the repo's main checkout, not a worktree.

<spec>
{the issue body, pasted — so a fix that changes behavior can be judged
against what the issue actually asked for}
</spec>

Base branch: {base_branch}
Verification command: {verify_command, from step 3's smoke run}
Project conventions: read {repo_root}/CLAUDE.md and {repo_root}/AGENTS.md
before changing anything.

The failing output is in:
  {log_path}

Read that file first. It is outside your work directory; read it there and do
not copy it in. Then fix the cause at {repo_root}, commit, and push. Do
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
