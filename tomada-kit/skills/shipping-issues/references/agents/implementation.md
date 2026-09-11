# Implementation (sub-agent prompt)

Spawned at [SKILL.md step 3](../../SKILL.md#3-implement), one issue at a time.
**`sonnet` is the default; `opus` when the issue is foundational** —
architecture or a skeleton, an interface/port/schema, or a skill, instruction
file, or gate whose shape the rest of the backlog copies. The test is blast
radius, not difficulty:
[cost-discipline.md#the-foundation-exception-opus-for-what-the-backlog-builds-on](../cost-discipline.md#the-foundation-exception-opus-for-what-the-backlog-builds-on).
A resume/patch run stays on the model its first run used.

```
Implement GitHub issue #{n} in {owner}/{repo}. Once you return, your branch is
turned into a PR and merged automatically once CI is green, so it must be
complete and correct by the time you push. You cannot ask me a question
mid-run — if something is genuinely undecidable, make the call, implement it,
and report it under UNRESOLVED.

Work only inside {workdir} — not any sibling checkout or worktree of the same
repository. {workdir_note}

<task>
{Issue #{n}: "{title}" (labels: {labels}{, UNBLOCKS/BLOCKED-BY if any}).

Read the full issue body and every comment yourself, read-only, with:
  gh issue view {n} --repo {owner}/{repo} --json title,body,labels,comments
That read is the ONLY GitHub command you are permitted to run.

Then a short paraphrase of what the issue asks — two or three sentences — so
the sub-agent can tell a bad read from a good one, ending with: "the body is
authoritative over this summary."}

{And, whenever the repository has moved under the issue since it was written —
a dependency of it merged in this same run, a file it cites was rewritten:
"IMPORTANT — the issue body describes the OLD state. On current `main`: <what
changed>. Read the current files before designing anything, and if the body's
premise no longer holds, say so under UNRESOLVED and implement what the issue
is actually trying to achieve rather than its literal description of a file
that has since changed."}
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
6. The only GitHub command you may run is
   `gh issue view {n} --repo {owner}/{repo} --json title,body,labels,comments` — every other GitHub
   call, including `gh pr`, `gh issue edit/comment/close`, any label change,
   or a non-GET `gh api` call, belongs to the parent (it opens the PR and
   watches CI). Never `rm`: undo a probe inside the checkout with
   `git checkout --`, or move it aside with `mv`, and name any scratch file —
   including a throwaway fixture or repository you created under a temp
   directory — you left behind in your report. `rm` triggers an approval
   prompt that stalls the run, and a disposable temp directory costs nothing
   to keep.
7. Run every verification in the **foreground**. Do not start a long command
   in the background and then poll it — a run that returns while waiting on
   its own background job returns without its report, and its work has to be
   recovered by hand.
8. {Parallel mode only:} If you produce a gitignored artifact worth keeping —
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
ACCEPTANCE: <the issue's Acceptance Criteria checklist, one line per item, as
             `met | not-met | not-applicable — <the command or output that
             shows it>`. "The issue has no acceptance criteria" is a valid
             answer; a criterion you cannot demonstrate is not-met, never met>
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

`ACCEPTANCE` is the one field green CI cannot substitute for. CI proves the
repository still works; it does not prove the issue was answered — a change can
pass every check and still miss a criterion the issue spelled out. An issue
written with a checklist has already done the hard part of saying what "done"
means, and reading that checklist back against real command output is what turns
a merge into a completed issue rather than a closed one. Any `not-met` line is a
step 3 result to send back, not a step 10 footnote.

**Name the verification CI cannot run.** CI runs one environment: a clean
checkout with no developer's variables exported. So a change whose behavior
turns on whether an environment variable is *set* — a credential, a feature
flag, a recording mode — has a whole half CI never exercises, and a green pipe
is not evidence about it. Whenever the diff makes anything conditional on the
environment, write the both-ways check into the prompt as an explicit command
pair with a throwaway value, and require both in `VERIFY`:

```
AND, because CI cannot catch this, run these explicitly and report both:
  {VAR}=dummy-not-a-real-value {verify_command}
  {VAR}=dummy-not-a-real-value {build_command}
Both must succeed. That value is a throwaway string, not a credential; do not
put a real one anywhere, and do not read any `.env` file to find one.
```

Seen in practice: a gate keyed off a provider credential's mere presence, which
refused to start the app, broke the build, and stopped a whole test file from
loading on any machine that exported that variable for an unrelated reason —
with CI green throughout, because CI does not set it. Nothing but running it
both ways would have found that before merge.

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
