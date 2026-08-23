# Delegation prompt templates

## Table of Contents

- [Filling rules](#filling-rules) — apply to every template below
- [Implementation](#implementation-write)
- [Review](#review-read-only)
- [Adversarial review](#adversarial-review-focus-file-read-only)
- [Failure repair](#failure-repair-write)
- [Investigation and second opinion](#investigation-and-second-opinion-read-only)

Copy a template, fill every `{brace}`, write it to a file outside the work
directory, and run it with the command shown above each one. The templates are
deliberately generic: the last line of each return block is where a calling
skill appends the fields it needs, and that delta is the only thing a
task-specific skill has to carry.

## Filling rules

**The run cannot ask a question back.** It is non-interactive with approvals
off, so a hole in the prompt does not come back as a clarifying question — it
comes back as a decision made alone, under `UNRESOLVED` if you are lucky. Fill
every `{brace}` before running, and leave nothing that gates your next step to
guess.

**Paste, do not cite.** The run reaches only the files under `--cwd`. It cannot
fetch an issue, a ticket, a design doc, or a PR description — `gh` cannot
authenticate inside the sandbox and network access is not guaranteed. Anything
it must know goes into the prompt as text, or into a file whose absolute path
the prompt names. Large inputs (a failing log, a spec) belong in a file: the
path costs the caller nothing, the pasted body costs it the whole log.

**The sandbox flag is the permission, not the prose.** `--write` grants writes;
its absence denies them at the sandbox level. Telling a read-only run not to
modify anything is redundant, and telling a write-capable run to "only look" is
unenforced.

**Name the other half of the work.** State what you will do after the run
returns, and forbid the run from doing it — opening a PR, watching CI, merging,
deleting, waiting. A capable run left without that boundary does the helpful
thing, and the helpful thing is often irreversible.

**Fix the cause, never the check.** In every template that writes code: a test
deleted, skipped, or weakened to make something pass is a failed outcome, and
saying so is what makes the return trustworthy.

**Demand evidence, not confidence.** Close every return block with the line
below, because the claims that matter get checked against your own output
anyway, and a remembered value costs a full round trip to catch:

> Every value in that return must come from a command output in this session.
> If a step did not run, say so instead of filling the field.

## Implementation (write)

```bash
${CLAUDE_SKILL_DIR}/scripts/codex_run.sh task --write --cwd {work_dir} --prompt-file {filled_template}
```

Scope ends at **pushed commits** (or at a clean working tree, when there is no
branch in play). Anything that talks to a forge API belongs to the caller.

```
Intent: You are implementing {one-line statement of the change} in
{repo_or_project}. {What happens to your work after you return — e.g. "your
branch is turned into a PR and merged as soon as CI is green", or "I review
your diff and land it myself".} It must be complete and correct by the time you
{push / stop}. You cannot ask me a question mid-run — if something is genuinely
undecidable, make the call, implement it, and report it under UNRESOLVED.

<task>
{the full specification, pasted — issue body, ticket, spec excerpt, bug report}
</task>

<context>
Work directory: {work_dir}   <- work only here
Base branch: {base_branch}          (omit this block's git lines if no branch is involved)
Likely files: {paths you already know}
Project conventions: read {project}/CLAUDE.md and {project}/AGENTS.md before writing code.
Decisions already made: {anything you resolved so the run does not re-open it}
Verification command: {verify_command or "find it"}
</context>

Do:
1. Read the project's own instruction files and follow them, including its test
   and commit conventions.
2. {Create a branch named {branch_name} off {base_branch}. | Work on the current
   branch.} If the task claims a performance improvement (runtime, throughput,
   memory, latency), measure the *before* state here, on the unmodified code,
   with the exact command you will re-run afterwards — a number quoted in the
   spec was not measured under your conditions, and after step 3 there is no
   clean baseline left to measure.
3. Implement the stated scope. Deliver what the task asks, at the scope it asks.
   If a better approach exists, say so in one sentence under SCOPE-NOTES and
   implement as asked.
4. Add or update the tests that cover the change, and run the project's own
   verification command (check its CLAUDE.md/AGENTS.md/justfile/Makefile for
   it). Report the exact command. For a performance task, re-run step 2's
   baseline command under the same conditions and state why the delta is a real
   improvement and not noise; report both numbers under MEASURE.
5. Commit in coherent increments{, and push as soon as the first coherent commit
   exists — a run stopped mid-way keeps only what was pushed}.
6. Two hard prohibitions, both irreversible from here: do NOT run `gh` at all
   ({who owns the forge API — e.g. "I open the PR and watch CI"}), and do NOT
   delete anything — no `rm`, no worktree removal, no branch deletion.
{7. Copy any gitignored artifacts you produce (fixtures, benchmark output) into
   {durable_path}, since {work_dir} is deleted after this run.}

Return exactly:
BRANCH: <name, or "n/a">
PUSHED: <yes + the remote ref, or "no" + why, or "n/a">
CHANGED: <file list>
VERIFY: <exact command run> -> <pass/fail + the failing output if any>
MEASURE: <performance task: command + before + after + why it counts as improved.
          Otherwise "n/a">
SCOPE-NOTES: <anything in the task you did not implement, and why>
FOLLOW-UPS: <defects you saw that are NOT this task, one per line as
             `file:line — what is wrong — what prevents it today`, or "none">
UNRESOLVED: <judgment calls you had to make, or "none">
{task-specific fields the caller appends}

Every value in that return must come from a command output in this session. If a
step did not run, say so instead of filling the field.

FOLLOW-UPS is how a real defect you must not fix here still survives the run.
Report it there rather than widening this change, and rather than staying silent
about it. Always include what currently prevents it (a guard at another layer, a
caller that cannot reach it) or "nothing": "nothing" versus "an adapter drops it
first" is the difference between a live bug and a missing defense layer.

If the task cannot be implemented as written, stop before changing anything and
return only UNRESOLVED with what is missing.
```

## Review (read-only)

```bash
${CLAUDE_SKILL_DIR}/scripts/codex_run.sh task --cwd {work_dir} --prompt-file {filled_template}
```

A **separate run** from the one that implemented the change. A fresh run reads
the diff in a context that never wrote it, which is the only thing that makes it
a review; re-reading a diff in the context that produced it is not one.

For a heavy diff, run the [adversarial pass](#adversarial-review-focus-file-read-only)
alongside this one — it judges failure modes and rollback safety and is told to
skip style and naming, which is most of what this template looks for. Neither
replaces the other.

```
Intent: This change implements {one-line statement of what it was supposed to
do} and {what happens next — e.g. "merges as soon as CI is green"}. Lint, types
and tests already pass. What no one has done is read the change as a change.
That is your job, and you are reading it in a context that did not write it.

The branch {branch} is checked out at {work_dir}. Read the specification and the
diff against {base}:

<spec>
{the task specification, pasted — you cannot fetch it from here}
</spec>

  GIT_OPTIONAL_LOCKS=0 git -C {work_dir} diff {base}...HEAD

Judge exactly what the test suite cannot:
- does the implementation match what the spec actually asked for — nothing
  missing, nothing quietly widened beyond it;
- unnecessary complexity: indirection, options, or abstraction the task did not
  need;
- maintainability: names that mislead, duplicated logic, a comment that is
  already wrong about the code beside it;
- the tests: do they pin the behavior the task is about, or only the shape of
  the implementation? A test that would pass with the bug still present is a
  finding;
- anything the diff walked past — a sibling of the case it fixed, an error path
  it left silent.

Report the defect, never the patch: file, line, what is wrong, why it matters.
The context that holds the branch re-derives the fix in the code it can see; a
patch written from your context is how a review fix causes the next regression.

Attach a severity and a confidence to every finding and report all of them; I
decide what blocks. A finding outside this task's scope is still worth
reporting — mark it OUT-OF-SCOPE.

Return exactly:
FINDINGS: <one per line as `[sev] file:line (conf) — what is wrong — why it
           matters`, sev = high|medium|low and conf = high|medium|low, or "none">
OUT-OF-SCOPE: <same shape, or "none">
TESTS: <verdict on the test changes in one or two lines>
INTENT-MATCH: <does the diff implement the spec as written — yes / no + what is
               missing or extra>
```

`INTENT-MATCH: no` is not a finding — it says the diff is not the change that
was asked for, and it can arrive with an empty `FINDINGS:` list. Handle it as a
scope defect before anything else.

Applying the findings is the caller's call: hand them verbatim to a further
`codex_run.sh task --write --cwd {work_dir}` run, or fix them yourself when it
is a line or two. Either way, commit, push, and re-run the verification command
before the next gate. A finding cleared by deleting a test or loosening an
assertion is a failed outcome; the review template has no `UNRESOLVED` field, so
that goes on the caller's own list.

## Adversarial review (focus file, read-only)

```bash
${CLAUDE_SKILL_DIR}/scripts/codex_run.sh review --cwd {work_dir} --base {base} \
    --focus-file {filled_template}
```

Added **alongside** the Review pass, never instead of it, when the diff touches
a schema, storage layer, or public contract; adds or bumps a dependency; or
rewires behavior across several modules.

Both entry points consume this file, but differently, so it has to stand on its
own: the companion appends it as focus text to a built-in reviewer, while the
`codex exec` fallback pipes it in as the **entire prompt** with no reviewer
instructions of its own. Written as below it works on either.

```
Intent: This change implements {one-line statement} in {repo_or_project} and
{what happens next}. A separate pass has already read this diff for scope,
complexity, and maintainability, and lint/types/tests pass. Your axis is the one
neither of those covers: how this change fails in production.

The branch is checked out at {work_dir}; the diff is against {base}:

  GIT_OPTIONAL_LOCKS=0 git -C {work_dir} diff {base}...HEAD

<spec>
{the task specification, pasted}
</spec>

Judge only these axes, and skip style, naming, and cleanup entirely — the other
pass owns those and duplicate findings cost me a triage round:
- failure modes: what input, ordering, or concurrent state makes this misbehave;
- trust boundaries: input that reaches a new place without being validated there;
- data loss and corruption: writes, migrations, deletions, cache invalidation;
- rollback safety: what happens if this is reverted after it has run once, and
  whether the change is backward-compatible with data written by the old code.

Report every finding you have, including the uncertain ones, with a severity and
a confidence. I filter; you do not.

Return exactly:
review_verdict: approve | needs-attention
FINDINGS: <one per line as `[sev] file:l1-l2 (conf) — what fails — under what
           conditions`, or "none">
```

When both review passes ran, merge their findings by `file:line` before applying
anything, or a defect both saw is fixed twice.

## Failure repair (write)

For a failing build, test suite, or CI run whose log is too large to read in the
calling context. Write the log to a file **outside** the work directory first —
a stray untracked file inside it makes cleanup skip the directory as dirty, and
a commit convention that stages everything would land the log in the change.

```bash
${CLAUDE_SKILL_DIR}/scripts/codex_run.sh task --write --cwd {work_dir} --prompt-file {filled_template}
```

The run cannot re-check the failure if checking it needs a forge API, so the
watch/repair loop stays with the caller: repair, push, caller re-checks, up to a
stated attempt cap.

```
Intent: {what is failing and where — e.g. "PR #{pr} fails CI on {check_names}"}.
I need the cause fixed and pushed. I will re-check after you return — you
cannot, and must not try to.

The failing output is in:
  {log_path}

Read that file first. It is outside your work directory; read it there and do
not copy it in. Then fix the cause at {work_dir}, commit, and push. Do not run
`gh`, do not watch CI, do not sleep or poll — return as soon as your fix is
pushed.

This is attempt {attempt} of {max_attempts}. {What the previous attempts tried
and why it did not work — leave empty on attempt 1, and never re-send the same
instruction twice.}

Fix the failure, not the check. Deleting, skipping, or weakening a test to make
it pass is a failed outcome — if the test is genuinely wrong, say so in
UNRESOLVED and stop without pushing. Same for a flaky job: if you believe a
failure is flaky, say which job and why under UNRESOLVED rather than pushing a
no-op commit to re-trigger it.

Return exactly:
CAUSE: <what actually failed, in one or two lines>
FIXES: <one line per repair commit, or "none">
PUSHED: <yes + the remote ref, or "no" + why — "no" ends the repair loop; I do
         not re-check unchanged code>
FOLLOW-UPS: <defects the failure exposed that are NOT this change's to fix, one
             per line as `file:line — what is wrong — what prevents it today`,
             or "none">
UNRESOLVED: <anything needing a human, or "none">
```

A failure is a good detector of pre-existing problems — a flaky job with a real
race behind it, a check that only passes because of ordering, a fixture that has
been wrong for months. Those go under FOLLOW-UPS with what currently prevents
them; fix only what makes *this* change pass.

## Investigation and second opinion (read-only)

For a diagnosis, a design critique, or a survey of unfamiliar code where the
value is the conclusion and the reading is what you want kept out of your
context. No `--write`, so it cannot start fixing what it finds.

```bash
${CLAUDE_SKILL_DIR}/scripts/codex_run.sh task --cwd {work_dir} --prompt-file {filled_template}
```

```
Intent: {the question, stated as a question}. I want your answer and the
evidence behind it, not a fix — you are read-only and I will act on what you
return. {Why you are being asked: "a second pass from a context that did not
write this code" / "I have a hypothesis and want it attacked" / "I need the
three files that actually matter out of a directory I have not read".}

Work directory: {work_dir}
{What I already know and have ruled out, so you do not re-derive it:}
{known_facts}
{My current hypothesis, which you should try to refute rather than confirm:}
{hypothesis, or "none — I have no theory yet"}

Ground every claim in something you read or ran in this session. A plausible
explanation with no file behind it costs me more than "I could not determine
this", so say the latter when it is true.

Return exactly:
ANSWER: <the conclusion, in a few lines>
EVIDENCE: <one per line as `file:line — what it shows`, or the command you ran
           and its relevant output>
{HYPOTHESIS-VERDICT: <supported | refuted | undetermined> + why  (only when you
                      gave one)}
ALTERNATIVES: <other explanations you could not rule out, or "none">
UNKNOWNS: <what you would need to look at that you could not reach from here,
           or "none">
```

Two shapes are worth separating. A **diagnosis** asks what is broken and gets
the block above as-is. A **second opinion** asks whether a decision already made
is right — for that, name the decision and the constraints it was made under,
and ask explicitly for the case against it; a run given only the design will
review it, and reviewing is not the same as opposing.
