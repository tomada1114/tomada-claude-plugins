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

Prompt body: `references/agents/priority-research.md`.
Fill its `{brace}` placeholders from the current repo and run count, then spawn
a `sonnet` worker with it where the runtime exposes delegation, otherwise read
the same file and run its read → rubric → `apply_priority_labels.py` steps
inline, in this context, before continuing.


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

State in `<context>` that the worktree's dependencies are already installed, so
the run does not spend a turn deciding whether to install them, and tell it the
branch is already created and checked out — the template's step 2 otherwise has
it create a second one.

Every brace the table does not name is filled the obvious way from the repo —
the project's own paths, the verification command if step 2 surfaced one, the
decisions step 2 already resolved. None may be left as a brace.

Two things the run cannot infer from the diff, and CI will fail the PR for
either: **a merge gate that lives outside the code** — release intent
(Changesets, a version bump), a regenerated API report, generated docs — must be
named in `<context>` with the exact command that satisfies it; and **an issue
that offers a choice** ("either anchor every path, or keep the bare form and
document it") must arrive already decided, because a run that cannot ask picks
one alone and half the file ends up in each style. Say which option, and say it
in `Decisions already made`.

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

Push discipline is the run's insurance: Codex pushes as soon as its first
coherent commit exists, so a stopped run loses at most its uncommitted tail. It
never deletes anything — that happens once, in the parent's cleanup step — and
copies any gitignored artifacts it produced into the main checkout before
returning, since worktrees are deleted at the end.

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

Where the implementation **departed from the issue's own "Done means"** — a
different mechanism, a call site the issue said to leave alone — name the
departure in the prompt and ask the run to judge it, rather than letting it
infer the spec from the diff. A reviewer told only "this implements the issue"
reads a deviation as the intent; a reviewer told "the issue said X, this does Y,
decide whether Y is safe on the production path" is where the expensive finding
actually comes from.

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
