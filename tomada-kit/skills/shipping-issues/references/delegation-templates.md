# Delegation Prompt Templates

## Table of Contents

- [Priority research and labeling](#priority-research-and-labeling-sonnet)
- [Implementation](#implementation-step-3)
- [Review](#review-step-6)
- [Review fix](#review-fix-step-6)
- [Adversarial focus (step 6, opt-in)](#adversarial-focus-step-6-opt-in)
- [CI repair](#ci-repair-step-7-only-on-fail)

Two kinds of handoff live here. **Priority research** is this skill's own
template, in full: it is GitHub API calls end to end, and a Codex sandbox has
no network to make them, so it stays with whatever delegation the calling
runtime exposes — or runs inline when it exposes none. Why the boundary sits exactly
there is argued once, under "Why the split is where it is" in this skill's
cost-discipline reference.

**Implementation, review, and CI repair** go to Codex, on a Claude Code host,
through `Skill(codex:rescue, args="<request>")` — the **openai-codex** plugin's
subagent. It is a thin forwarder: one Codex turn, the request text forwarded
verbatim, the reply returned verbatim. Two things about it decide how every
template below is shaped:

- **It has no `--cwd` of its own.** Unlike a runner that scopes a run to a
  directory, `codex:rescue` operates wherever the session's own working
  directory already is — which this skill keeps pinned to the repo's main
  checkout throughout the run. The only thing that scopes a given request to
  the right branch is a sentence in the request itself — put it first, and
  treat it as load bearing, not decoration. This is also why every step runs
  **one issue at a time**: nothing here spawns a second concurrent
  `codex:rescue` call against the same checkout.
- **It defaults to write-capable.** Say "read-only, do not edit, create,
  delete, or run anything that writes to disk or git" explicitly in the
  request for step 6 — that sentence is the only thing keeping a review from
  patching what it finds. Leave it unsaid for steps 3 and 7, where write is the
  point.

Everything that governs a Codex run applies unchanged, and two points carry the
most weight for this skill: **the run cannot ask a question back**, so a hole in
the prompt returns as a decision made alone rather than as a question — leave
nothing merge-gating to guess; and **model and reasoning effort are never
passed**, so each run inherits the Codex CLI's own configuration (leaving
`--effort` unset is also the only way to reach the top reasoning tier — the
enum `codex:rescue` accepts stops at `xhigh`; the top tier is only reachable
through `~/.codex/config.toml`'s own setting, inherited when unset).

For the non-Codex fallbacks, follow `orchestrating-models` §2: unresolved spec →
`opus`, fully specified pass/fail → `sonnet`. <!-- derived from orchestrating-models §2 -->

## Priority research and labeling (`sonnet`)

Spawned only when more than ~3 open issues still lack a `priority:` label, or
when the top rows of a labeled backlog are close enough that the pick needs
evidence. On a fully labeled backlog, `issue_digest.py --select` is the answer
and no spawn is warranted.

The worker writes the labels itself — that is the point of the handoff. What
comes back is the pick with its evidence, the order behind it, and the
blocked/unclear lists; the issue prose and the raw digest table never cross
back.

Prompt body: `references/agents/priority-research.md`.
Fill its `{brace}` placeholders from the current repo and run count, then spawn
a `sonnet` worker with it where the runtime exposes delegation, otherwise read
the same file and run its read → rubric → `apply_priority_labels.py` steps
inline, in this context, before continuing.

## Implementation (step 3)

```bash
Skill(codex:rescue, args="--wait <filled request below>")
```

Fill and run, one issue at a time:

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
Likely files: {paths from step 2's triage}
Project conventions: read {repo_root}/CLAUDE.md and
{repo_root}/AGENTS.md before writing code.
Decisions already made: {anything step 2/2b resolved, so it is not re-opened}
Verification command: {verify_command, from step 3's smoke run, or "find it"}
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
step 9 files it as its own issue. `SCOPE-NOTES` and `UNRESOLVED` feed the same
step and the step 11 report.

Scope is **branch to pushed commits**; the PR, the link check, CI, and the
merge belong to the parent. With no usable Codex (`codex:setup` reports not
ready), hand the same filled request to an independent `opus` worker per issue
where delegation is available, otherwise work through it inline, one issue at
a time. The scope does not change in the fallback.

Push discipline is the run's insurance: it pushes as soon as its first
coherent commit exists, so a stopped run loses at most its uncommitted tail.
It never deletes anything — that happens once, in the parent's cleanup step
(step 10), and only after the branch is merged.

## Review (step 6)

```bash
Skill(codex:rescue, args="--wait <filled request below>")
```

Run from the parent, after the PR exists and before CI:

```
Read-only review only — do not edit, create, or delete any file, and do not
run any command that writes to disk or to git. PR #{pr} implements issue #{n}
in {owner}/{repo} and merges as soon as CI is green. Lint, types and tests
already pass. What no one has done is read the change as a change. That is
your job, and you are reading it in a context that did not write it.

The branch {branch} is checked out at {repo_root}. Read the specification
and the diff against {base}:

  GIT_OPTIONAL_LOCKS=0 git -C {repo_root} diff {base}...HEAD

<spec>
{the issue body, pasted — you cannot fetch it from here}
</spec>

{Where the implementation departed from the issue's own "Done means" — a
different mechanism, a call site the issue said to leave alone — name the
departure here and ask the run to judge it, rather than letting it infer the
spec from the diff.}

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
I re-derive the fix in the code I can see; a patch written from a context that
never ran the tests is how a review fix causes the next regression.

Attach a severity and a confidence to every finding and report all of them; I
decide what blocks. A finding outside this task's scope is still worth
reporting — mark it OUT-OF-SCOPE.

Return exactly:
FINDINGS: <one per line as `[sev] file:line (conf) — what is wrong — why it
           matters`, sev = high|medium|low and conf = high|medium|low, or
           "none">
OUT-OF-SCOPE: <same shape, or "none">
TESTS: <verdict on the test changes in one or two lines>
INTENT-MATCH: <does the diff implement the spec as written — yes / no + what
               is missing or extra>
```

No extra return fields. What the parent does with them:

- **`INTENT-MATCH: no` is read before the findings.** It says the diff is not
  issue #{n}'s change — a scope defect, and it can arrive with an empty
  `FINDINGS:` list. Send the missing part back through the Implementation
  request, or re-run it when most of the change is absent.
- A `TESTS:` verdict saying the tests pin the implementation rather than the
  behavior is treated as a finding.
- **Triage every finding in the parent before anything is fixed.** The review
  returns prose, never a patch, and the parent decides which findings are
  real. This is the whole reason the review is read-only: a reviewer that
  applies its own findings lands its misreadings too, and the parent never
  sees what it would have rejected.
- **One round is the ceiling.** The accepted findings go to one Review fix run
  (below). What triage rejected is noted in the PR with the reason; what is
  real but outside issue #{n}'s scope goes to step 9 as a follow-up; what is
  left undecided goes on the parent's `UNRESOLVED` list. None of those three
  block the merge.
- Record which rung ran (`--event review --field status=<codex|codex+adversarial|DELEGATED|UNAVAILABLE>`).

## Review fix (step 6)

Run only when triage accepted at least one finding — a clean review skips this
run entirely. Carry **only the accepted findings**: a rejected one handed back
here gets fixed anyway, which is the failure this split exists to prevent.

```bash
Skill(codex:rescue, args="--wait <filled request below>")
```

```
Work only inside {repo_root}, on branch {branch} — already checked out. Apply
the fixes below to PR #{pr}, which implements issue #{n} in {owner}/{repo} and
merges once CI is green. Do NOT touch the GitHub API, do NOT delete anything,
and do NOT push a new branch.

These findings came from a review of this diff and have already been triaged
and accepted. Fix exactly these, and nothing else — a finding not on this list
was considered and rejected, so re-fixing it would undo a decision:

{the accepted findings, one per line, verbatim, each with its file:line}

For each one, fix the cause rather than the symptom, and never the check
itself: no weakened assertion, no lowered threshold, no skipped or deleted
test, no suppression comment. If a finding turns out to be wrong on closer
reading, do NOT fix it — say so under DISPUTED and move on.

Read {repo_root}/CLAUDE.md and {repo_root}/AGENTS.md first; the fixes follow
the project's own conventions.

Then run {verify_command} and commit as `review: <what was fixed>`. Do not
push.

Return exactly:
FIXED: <one per line as `file:line — what you changed`, or "none">
DISPUTED: <findings you did not fix, with why, or "none">
VERIFY: <exact command run> -> <pass/fail + the failing output if any>
COMMITS: <sha + subject of each commit, or "none">
UNRESOLVED: <anything still open, or "none">
```

`DISPUTED` is the run's escape hatch and is read, not ignored: a finding the
fix run argues against is one the review and the triage both got wrong, and it
belongs in the PR body rather than silently dropped.

## Adversarial focus (step 6, opt-in)

Issued **in addition to** the Review pass above, never instead of it, and only
when the user asked for one or the change can lose or corrode data that
already exists — a migration, a storage-layer write, a released public
contract real consumers are on. Diff size and module count are not the
trigger; the Review pass already covers those. Both are read-only
reads of the same checkout, but this skill runs one `codex:rescue` call at a
time — issue this one after Review returns, never concurrently with it:

```bash
Skill(codex:rescue, args="--wait <filled request below>")
```

```
Read-only review only — do not edit, create, or delete any file, and do not
run any command that writes to disk or to git. This change implements
{one-line statement} in {owner}/{repo} and {what happens next — e.g. "merges
as soon as CI is green"}. A separate pass has already read this diff for
scope, complexity, and maintainability, and lint/types/tests pass. Your axis
is the one neither of those covers: how this change fails in production.

The branch is checked out at {repo_root}; the diff is against {base}:

  GIT_OPTIONAL_LOCKS=0 git -C {repo_root} diff {base}...HEAD

<spec>
{the issue body, pasted}
</spec>

Judge only these axes, and skip style, naming, and cleanup entirely — the
other pass owns those and duplicate findings cost me a triage round:
- failure modes: what input, ordering, or concurrent state makes this
  misbehave;
- trust boundaries: input that reaches a new place without being validated
  there;
- data loss and corruption: writes, migrations, deletions, cache
  invalidation;
- rollback safety: what happens if this is reverted after it has run once,
  and whether the change is backward-compatible with data written by the old
  code.

Report every finding you have, including the uncertain ones, with a severity
and a confidence. I filter; you do not.

Return exactly:
review_verdict: approve | needs-attention
FINDINGS: <one per line as `[sev] file:l1-l2 (conf) — what fails — under what
           conditions`, or "none">
```

When both passes ran, merge their findings by `file:line` before applying, or
a defect both saw is fixed twice. Record the status as `codex+adversarial`.
Unlike the dedicated review verb this skill used to call, `codex:rescue`
returns free text rather than a schema-validated JSON payload — read
`review_verdict:` off the returned text itself; there is no separate
`UNSTRUCTURED` state to detect, since it was never structured to begin with.

## CI repair (step 7, only on `FAIL`)

Only after the parent's own `ci_watch.sh` returns `FAIL`. Write the failing
log to a file **outside** the repo checkout first — a stray untracked file
inside it makes cleanup skip the directory as dirty, and a commit convention
that stages everything would land the log in the change:

```bash
Skill(codex:rescue, args="--wait <filled request below>")
```

```
PR #{pr} implements issue #{n} in {owner}/{repo}; its CI just failed:
{check names, from the parent's failed_checks: line}. I need the cause fixed
and pushed. I will re-check after you return — you cannot, and must not try
to.

Work only inside {repo_root} — this is the repo's main checkout.

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
never lands in the parent's context. The run cannot call `ci_watch.sh` — it
talks to the GitHub API — so the watch/repair loop lives in the parent:
repair, push, re-watch, up to 3 attempts. `PUSHED: no` ends the loop; read
`UNRESOLVED` rather than re-watching unchanged code.

With no usable Codex, hand the same filled request to an independent `sonnet`
worker per failing PR where delegation is available — escalating to `opus`
after two failed attempts — otherwise work through it inline, one PR at a
time.
