# Delegation Prompt Templates

## Table of Contents

- [Priority research and labeling](#priority-research-and-labeling-sonnet)
- [Implementation](#implementation-step-3)
- [Review](#review-step-6)
- [Adversarial focus file](#adversarial-focus-file-step-6-heavy-diffs-only)
- [CI repair](#ci-repair-step-7-only-on-fail)

Two kinds of handoff live here. **Priority research** is this skill's own
template, in full: it is `gh` calls end to end, `gh` cannot authenticate inside
the Codex sandbox, so it stays with whatever delegation the calling runtime
exposes — or runs inline when it exposes none. Why the boundary sits exactly
there is argued once, under "Why the split is where it is" in this skill's
cost-discipline reference.

**Implementation, review, and CI repair** go to Codex, and their prompt bodies
are not repeated here. The generic templates, the filling rules they share, the
runner's flags, and the sandbox limits all belong to the **`delegating-to-codex`**
skill — read `{CODEX_SKILL_DIR}/references/delegation-templates.md` and fill the
template named in each section below. What stays here is only this skill's
delta: how each `{brace}` is filled from an issue, and the extra return fields
step 4 needs.

Everything that governs a Codex run applies unchanged, and two points carry the
most weight for this skill: **the run cannot ask a question back**, so a hole in
the prompt returns as a decision made alone rather than as a question — leave
nothing merge-gating to guess; and **model and reasoning effort are never
passed**, so each run inherits the Codex CLI's own configuration.

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


## Implementation (step 3)

Fill the **Implementation (write)** template from
`{CODEX_SKILL_DIR}/references/delegation-templates.md`, write it to
`<runstate>/prompts/<n>-impl.md`, and run it against the issue's worktree:

```bash
{CODEX_SKILL_DIR}/scripts/codex_run.sh task --write --cwd {worktree_path} --prompt-file <runstate>/prompts/<n>-impl.md
```

Fill it like this:

| Placeholder | This skill's value |
|---|---|
| the one-line statement | `GitHub issue #{n} in {owner}/{repo}` |
| what happens after the run | "your branch is turned into a PR and merged automatically once CI is green, so it must be complete and correct by the time you push" |
| `<task>` | the full issue body plus the comments that change the spec, pasted by the parent |
| `{work_dir}` | the issue's worktree — `{repo}/.claude/worktrees/{n}`, or the main checkout in single mode |
| `{base_branch}` | the repo's default branch |
| the branch name | `{type}/{n}-{slug}` |
| the template's `Likely files` line | the paths from step 2's triage |
| who owns the forge API | "the parent opens the PR and watches CI" |
| `{durable_path}` (step 7 of the template) | `{repo_root}` — worktrees are deleted in step 10, so gitignored artifacts must be copied out |

Every brace the table does not name is filled the obvious way from the repo —
the project's own paths, the verification command if step 2 surfaced one, the
decisions step 2 already resolved. None may be left as a brace.

Append these three fields to the template's return block. Step 4 uses them
verbatim, so they are not optional:

```
PR-TITLE: <one line the parent can use verbatim>
PR-SUMMARY: <2-4 lines: what changed and why, for the PR body>
TEST-PLAN: <what the parent should put under the PR's test plan, including the
            verification command and, for a perf issue, both numbers>
```

`FOLLOW-UPS` is how a real defect the run must not fix here still survives:
step 9 files it as its own issue. `SCOPE-NOTES` and `UNRESOLVED` feed the same
step and the step 11 report.

Scope is **branch to pushed commits**; the PR, the link check, CI, and the merge
belong to the parent. With no usable Codex (`codex_run.sh check` exits 3), hand
the same filled template to an independent `opus` worker per issue where
delegation is available, otherwise work through it inline, one issue at a time.
The scope does not change in the fallback.

## Review (step 6)

Fill the **Review (read-only)** template from
`{CODEX_SKILL_DIR}/references/delegation-templates.md` into
`<runstate>/prompts/<n>-review.md` and run it from the parent, after the PR
exists and before CI:

```bash
{CODEX_SKILL_DIR}/scripts/codex_run.sh task --cwd {worktree_path} --prompt-file <runstate>/prompts/<n>-review.md
```

Fill it like this:

| Placeholder | This skill's value |
|---|---|
| the one-line statement | `PR #{pr} implements issue #{n}` |
| what happens next | "merges as soon as CI is green" |
| `<spec>` | the issue body, pasted — the run cannot reach `gh` |
| `{branch}`, `{work_dir}` | the issue's branch and worktree |
| `{base}` | the repo's default branch |

No extra return fields. What the parent does with them:

- **`INTENT-MATCH: no` is read before the findings.** It says the diff is not
  issue #{n}'s change — a scope defect, and it can arrive with an empty
  `FINDINGS:` list. Send the missing part back through a fix run, or re-run the
  Implementation template when most of the change is absent.
- A `TESTS:` verdict saying the tests pin the implementation rather than the
  behavior is treated as a finding.
- **One round is the ceiling.** Apply the findings, commit
  (`review: <what was fixed>`), push, and re-run the verification command so CI
  judges the reviewed code. What is still open after that round goes on the
  parent's `UNRESOLVED` list, or to step 9 as a follow-up when it is outside
  issue #{n}'s scope — it does not block the merge.
- Record which rung ran (`--event review --field status=<codex|codex+adversarial|DELEGATED|UNAVAILABLE>`).

## Adversarial focus file (step 6, heavy diffs only)

Fill the **Adversarial review** template from
`{CODEX_SKILL_DIR}/references/delegation-templates.md` into
`<runstate>/prompts/<n>-adversarial.md`, alongside the Review pass and never
instead of it, when the diff touches a schema, storage layer, or public
contract; adds or bumps a dependency; or rewires behavior across several
modules:

```bash
{CODEX_SKILL_DIR}/scripts/codex_run.sh review --cwd {worktree_path} --base {base} \
    --focus-file <runstate>/prompts/<n>-adversarial.md
```

Same fills as the Review section above; `<spec>` is again the pasted issue body.
Issue both passes in one message. When both ran, merge their findings by
`file:line` before applying, or a defect both saw is fixed twice. Record the
status as `codex+adversarial`, or `codex+adversarial(unstructured)` when the
verdict came back `UNSTRUCTURED`.

## CI repair (step 7, only on `FAIL`)

Only after the parent's own `ci_watch.sh` returns `FAIL`. Fill the **Failure
repair (write)** template from
`{CODEX_SKILL_DIR}/references/delegation-templates.md` into
`<runstate>/prompts/<n>-cifix.md`:

```bash
{CODEX_SKILL_DIR}/scripts/codex_run.sh task --write --cwd {worktree_path} --prompt-file <runstate>/prompts/<n>-cifix.md
```

Fill it like this:

| Placeholder | This skill's value |
|---|---|
| what is failing | "PR #{pr} implements issue #{n}; its CI just failed: ..." — the check names come from the parent's `failed_checks:` line |
| `{log_path}` | `<runstate>/ci/<pr>.log` — the watch output, already outside the worktree |
| `{work_dir}` | the issue's worktree |
| `{max_attempts}` | 3 |
| previous-attempt detail | empty on attempt 1; from attempt 3, the accumulated detail rather than the same instruction again |

The log reaches the run through that path, never through the prompt, so it never
lands in the parent's context. The run cannot call `ci_watch.sh` — it is a `gh`
wrapper — so the watch/repair loop lives in the parent: repair, push, re-watch,
up to 3 attempts. `PUSHED: no` ends the loop; read `UNRESOLVED` rather than
re-watching unchanged code.

With no usable Codex, hand the same filled template to an independent `sonnet`
worker per failing PR where delegation is available — escalating to `opus` after
two failed attempts — otherwise work through it inline, one PR at a time.
