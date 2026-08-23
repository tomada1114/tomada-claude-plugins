# Delegation Prompt Templates

## Table of Contents

- [Priority research and labeling](#priority-research-and-labeling-sonnet)
- [Implementation](#implementation-codex-write-capable-one-worktree-per-issue)
- [Review](#review-codex-read-only-run-from-the-parent)
- [CI repair](#ci-repair-codex-write-capable-only-on-fail)
- [Adversarial focus file](#adversarial-focus-file-codex-read-only-heavy-diffs-only)

Copy-and-fill templates for the handoffs this skill makes. Each carries intent,
concrete paths, embedded context, and an output contract, so the parent never
receives raw `gh` JSON or full CI logs.

Implementation, review, and CI repair go to Codex through
`{SKILL_DIR}/scripts/codex_run.sh`. Priority research does not: it is `gh` calls
end to end, and `gh` cannot authenticate inside the Codex sandbox, so it stays
with whatever delegation the calling runtime exposes — or runs inline when it
exposes none. Why the boundary sits there is argued once, under "Why the split is where it
is" in this skill's cost-discipline reference. Model and
reasoning effort are deliberately not passed on the Codex path — see the header
of `scripts/codex_run.sh`. For the non-Codex fallbacks, follow
`orchestrating-models` §2: unresolved spec → `opus`, fully specified pass/fail →
`sonnet`. <!-- derived from orchestrating-models §2 -->

**A Codex run cannot ask a question back.** It is non-interactive with approvals
off, so a hole in the prompt does not return as a clarifying question — it
returns as a decision made alone. Fill every `{brace}` before running, and leave
nothing merge-gating to guess.

Placeholders in `{braces}` are filled by the parent before the run.

## Priority research and labeling (`sonnet`)

Spawned only when more than ~3 open issues still lack a `priority:` label, or
when the top rows of a labeled backlog are close enough that the pick needs
evidence. On a fully labeled backlog, `issue_digest.py --select` is the answer
and no spawn is warranted.

The worker writes the labels itself — that is the point of the handoff. What
comes back is the pick with its evidence, the order behind it, and the
blocked/unclear lists; the issue prose and the raw digest table never cross
back.

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

## Unresolved
- #N vs #M — the trade-off, left unpicked   (omit this section when there is no tie)

If the top two are genuinely tied on every axis of the rubric, list both under
Unresolved with the trade-off rather than picking one.
```

## Implementation (Codex, write-capable, one worktree per issue)

Write the filled template to a file and run it against the issue's worktree:

```bash
{SKILL_DIR}/scripts/codex_run.sh task --write --cwd {worktree_path} --prompt-file {filled_template}
```

Scope is **branch to pushed commits**; the PR, the link check, CI, and the merge
belong to the parent.

With no usable Codex (`codex_run.sh check` exits 3), hand this same template to
an independent `opus` worker per issue where delegation is available, otherwise
work through it inline, one issue at a time. The scope does not change in the
fallback.

```
Intent: You are implementing GitHub issue #{n} in {owner}/{repo}. Your branch
will be turned into a PR and merged automatically once CI is green, so it must
be complete and correct by the time you push. You cannot ask me a question
mid-run — if something is genuinely undecidable, make the call, implement it,
and report it under UNRESOLVED.

<issue>
{full issue body + relevant comments, pasted by the parent}
</issue>

<context>
Worktree: {worktree_path}   <- work only here; this is the branch's checkout
Base branch: {default_branch}
Likely files: {paths from triage}
Project conventions: read {repo}/CLAUDE.md and {repo}/AGENTS.md before writing code.
Related decisions already made: {anything the parent resolved}
Verification command, if the parent already knows it: {verify_command or "find it"}
</context>

Do:
1. Read the project's own instruction files and follow them, including its test
   and commit conventions.
2. Create a branch named {type}/{n}-{slug} off {default_branch}. If the issue
   claims a performance improvement (runtime, throughput, memory, latency),
   measure the *before* state right here, on the unmodified code, using the
   exact command you will re-run after implementing — an existing number in
   the issue body is not a substitute, it was not measured under your
   conditions. Measuring later, after step 3 has already changed the code,
   leaves no clean baseline to measure.
3. Implement the issue's stated scope. Deliver what the issue asks, at the scope
   it asks. If a better approach exists, say so in one sentence under
   SCOPE-NOTES and implement as asked.
4. Add or update the tests that cover the change, and run the project's own
   verification command (check its CLAUDE.md/AGENTS.md/justfile/Makefile for it).
   Report the exact command — the parent needs it if this repo has no CI.
   For a performance issue, re-run step 2's baseline command now, under the
   same conditions, and state why the delta is a real improvement and not
   noise. Report both numbers and the command under MEASURE.
5. Commit in coherent increments, and push as soon as the first coherent commit
   exists — a run stopped mid-way keeps only what was pushed.
6. Two hard prohibitions, both irreversible from here: do NOT run `gh` at all
   (the parent opens the PR and watches CI), and do NOT delete anything — no
   `rm`, no worktree removal, no branch deletion; the parent runs one batch
   cleanup at the end.

<example>
A correct ending: your last coherent commit is pushed to the remote branch; any
gitignored artifacts you produced (fixtures, bench outputs) are copied into the
main checkout at {repo_root}, since this worktree is deleted later; you emit the
return block below and stop. No PR, no CI watch, no waiting, no cleanup.
</example>

Return exactly:
BRANCH: <name>
PUSHED: <yes + the remote ref, or "no" + why>
CHANGED: <file list>
VERIFY: <exact command run> -> <pass/fail + the failing output if any>
MEASURE: <perf issue: command + before + after + why it counts as improved. Otherwise "n/a">
PR-TITLE: <one line the parent can use verbatim>
PR-SUMMARY: <2-4 lines: what changed and why, for the PR body>
TEST-PLAN: <what the parent should put under the PR's test plan, including the
            verification command and, for a perf issue, both numbers>
SCOPE-NOTES: <anything in the issue you did not implement, and why>
FOLLOW-UPS: <defects you saw that are NOT this issue, one per line as
             `file:line — what is wrong — what prevents it today`, or "none">
UNRESOLVED: <judgment calls you had to make, or "none">

Every value in that return must come from a command output in this session —
the parent re-verifies the branch, the PR, CI, and closure against GitHub, so a
remembered or assumed value is caught and costs a full re-check. If a step did
not run, say so instead of filling the field.

FOLLOW-UPS is how a real defect you must not fix here still survives the run —
the parent files it as its own issue (SKILL.md step 9). Report it there
rather than widening this change, and rather than staying silent about it.
Always include what currently prevents it (a guard at another layer, a provider
that filters the input, a caller that cannot reach it) or "nothing": the parent
tiers the issue on exactly that, and "nothing" versus "an adapter drops it
first" is the difference between a live bug and a missing defense layer. Do not
file the issue yourself — you see only this worktree.

If the issue cannot be implemented as written, stop before creating a branch and
return only UNRESOLVED with what is missing.
```

## Review (Codex, read-only, run from the parent)

Run from the parent against the worktree, after the PR exists and before CI
(SKILL.md step 6):

```bash
{SKILL_DIR}/scripts/codex_run.sh task --cwd {worktree_path} --prompt-file {filled_template}
```

No `--write`, so the reviewer is read-only at the sandbox level and cannot
quietly patch what it finds. This is a **separate run** from the one that
implemented the change: a fresh run reads the diff in a context that never wrote
it, which is the only thing that makes it a review. Re-reading a diff in the
context that produced it is not one, and neither is the parent skimming it here.

For a heavy diff, add the [adversarial pass](#adversarial-focus-file-codex-read-only-heavy-diffs-only)
alongside this one. It judges failure modes, trust boundaries, and rollback
safety, and is explicitly told to skip style, naming, and cleanup — which is most
of what this template looks for. Neither pass replaces the other.

```
Intent: PR #{pr} implements issue #{n} and merges as soon as CI is green. Lint,
types and tests already pass — CI will re-check them. What no one has done is
read the change as a change. That is your job, and you are reading it in a
context that did not write it.

The branch {branch} is checked out at {worktree_path}. Read the issue and the
diff against {base}:

<issue>
{issue body, pasted by the parent — you cannot run `gh` from here}
</issue>

  GIT_OPTIONAL_LOCKS=0 git -C {worktree_path} diff {base}...HEAD

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
The context that holds the branch re-derives the fix in the code it can see; a
patch written from your context is how a review fix causes the next regression.

Attach a severity and a confidence to every finding and report all of them; the
parent decides what blocks this merge. A finding outside issue #{n}'s scope is
still worth reporting — mark it OUT-OF-SCOPE and it becomes a follow-up issue
rather than a change to this PR.

Return exactly:
FINDINGS: <one per line as `[sev] file:line (conf) — what is wrong — why it
           matters`, sev = high|medium|low and conf = high|medium|low, or
           "none">
OUT-OF-SCOPE: <same shape, or "none">
TESTS: <verdict on the test changes in one or two lines>
INTENT-MATCH: <does the diff implement issue #{n} as written — yes / no + what
               is missing or extra>
```

`INTENT-MATCH: no` is not a finding — it says the diff is not issue #{n}'s
change, and the parent handles it as a scope defect before CI. Applying the rest
is the parent's call: hand the findings verbatim to a further
`{SKILL_DIR}/scripts/codex_run.sh task --write --cwd {worktree_path}` run, or fix
them in the parent when it is a line or two. Either way, commit
(`review: <what was fixed>`), push, and re-run the verification command before
CI starts.

## CI repair (Codex, write-capable, only on `FAIL`)

The parent runs `ci_watch.sh` in its own context first — a green first watch
needs no repair run — and only on a `FAIL` verdict redirects the watch output
into the worktree and hands Codex the path:

```bash
{SKILL_DIR}/scripts/codex_run.sh task --write --cwd {worktree_path} --prompt-file {filled_template}
```

The failing log reaches the run through a file rather than the prompt, so it
never lands in the parent's context. That file lives in the run's own state
directory, **not inside the worktree** — a stray untracked file there makes the
final cleanup skip the worktree as dirty, and a commit convention that stages
everything would land the CI log in the PR. Codex cannot run `ci_watch.sh`
itself — it is a `gh` wrapper — so the watch/repair loop lives in the parent:
repair, push, the parent re-watches, up to **3 attempts** total.

With no usable Codex, hand this template to an independent `sonnet` worker per
failing PR where delegation is available (escalating to `opus` after two failed
attempts), otherwise work through it inline, one PR at a time.

```
Intent: PR #{pr} implements issue #{n} and will be merged as soon as CI is green.
Its CI just failed: {failing_check_names_from_parent_watch}. I need the cause
fixed and pushed. I will re-watch CI myself after you return — you cannot, and
must not try to.

The failing checks and the tail of each failing run's log are in:
  {ci_log_path}

Read that file first. It is outside your worktree; read it there and do not copy
it in. Then fix the cause in the branch worktree at
{worktree_path}, commit, and push. Do not run `gh`, do not watch CI, do not
sleep or poll — return as soon as your fix is pushed.

This is attempt {attempt} of {max_retries}. {accumulated_failure_detail_if_any}

Fix the failure, not the check. Deleting, skipping, or weakening a test to make
CI pass is a failed outcome — if the test is genuinely wrong, say so in
UNRESOLVED and stop without pushing. Same for a flaky job: if you believe a
failure is flaky, say which job and why under UNRESOLVED rather than pushing a
no-op commit to re-trigger it.

Return exactly:
CAUSE: <what actually failed, in one or two lines>
FIXES: <one line per repair commit, or "none">
PUSHED: <yes + the remote ref, or "no" + why — "no" ends the repair loop; the
         parent does not re-watch unchanged code>
FOLLOW-UPS: <defects the failure exposed that are NOT this PR's to fix, one per
             line as `file:line — what is wrong — what prevents it today`, or
             "none">
UNRESOLVED: <anything needing a human, or "none">
```

A CI failure is a good detector of pre-existing problems — a flaky job with a
real race behind it, a check that only passes because of ordering, a fixture
that has been wrong for months. Put those under FOLLOW-UPS with what currently
prevents them, so the parent can file them (SKILL.md step 9); fix only what
makes *this* PR green.

## Adversarial focus file (Codex, read-only, heavy diffs only)

Added alongside the Review pass — never instead of it — when the diff touches a
schema, storage layer, or public contract; adds or bumps a dependency; or
rewires behavior across several modules.

```bash
{SKILL_DIR}/scripts/codex_run.sh review --cwd {worktree_path} --base {base} \
    --focus-file {filled_template}
```

Both entry points consume this file, but differently, so it has to stand on its
own: the companion appends it as focus text to a built-in reviewer, while the
bare `codex exec` fallback pipes it in as the **entire prompt** with no reviewer
instructions of its own. Written as below it works on either.

```
Intent: PR #{pr} implements issue #{n} in {owner}/{repo} and merges as soon as
CI is green. A separate pass has already read this diff for scope, complexity,
and maintainability, and lint/types/tests pass. Your axis is the one neither of
those covers: how this change fails in production.

The branch is checked out at {worktree_path}; the diff is against {base}:

  GIT_OPTIONAL_LOCKS=0 git -C {worktree_path} diff {base}...HEAD

<issue>
{issue body, pasted by the parent — you cannot run `gh` from here}
</issue>

Judge only these axes, and skip style, naming, and cleanup entirely — the other
pass owns those and duplicate findings cost the parent a triage round:
- failure modes: what input, ordering, or concurrent state makes this misbehave;
- trust boundaries: input that reaches a new place without being validated there;
- data loss and corruption: writes, migrations, deletions, cache invalidation;
- rollback safety: what happens if this is reverted after it has run once, and
  whether the change is backward-compatible with data written by the old code.

Report every finding you have, including the uncertain ones, with a severity and
a confidence. The parent filters; you do not.

Return exactly:
review_verdict: approve | needs-attention
FINDINGS: <one per line as `[sev] file:l1-l2 (conf) — what fails — under what
           conditions`, or "none">
```

On the companion entry point this returns `review_verdict: approve |
needs-attention` in structured form, exit 1 meaning `needs-attention`. On the
bare `codex exec` fallback it returns `review_verdict: UNSTRUCTURED` followed by
free text, and the exit code reports only whether the run completed — read the
text rather than the code. `UNPARSED` means the structured result did not come
back; treat it the same way.
