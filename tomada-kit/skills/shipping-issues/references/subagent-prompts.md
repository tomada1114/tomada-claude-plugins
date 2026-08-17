# Sub-agent Prompt Templates

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
  "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/references/priority-rubric.md
  "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/references/dependency-triage.md

Then run and read the full-body digest (do not paste its raw output back to me):
  python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/scripts/issue_digest.py {filters}

`~Pn` in the priority column is a suggested tier the script computed but has not
written; `P2(~P0)` is a written label the signals now say is too low. Run the
research pass from priority-rubric.md on the top 3–5 rows only, and verify each
claim you repeat:
  gh issue view <n> --comments        (shortlisted issues only)
  grep for the symbols/paths the body names, to confirm ripple/leverage
  gh run list --branch {default_branch} --limit 5   (only if an issue claims CI/main is broken)

Then write the tiers — one call, both halves:
  python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/scripts/apply_priority_labels.py \
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
2. Create a branch named {type}/{n}-{slug} off {default_branch}.
3. Implement the issue's stated scope. Deliver what the issue asks, at the scope
   it asks. If a better approach exists, note it in the PR body in one sentence
   and implement as asked.
4. Add or update the tests that cover the change, and run the project's own
   verification command (check its CLAUDE.md/AGENTS.md/justfile/Makefile for it).
   Report the exact command — the parent needs it if this repo has no CI.
5. Commit and push. Open the PR against {default_branch} with a body whose FIRST
   line after the summary is exactly:  Closes #{n}
   (not "see #{n}", not "related to #{n}" — those do not close anything), plus a
   summary and a test plan.
6. Confirm GitHub actually registered the link, and repair it if not:
     "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/scripts/link_check.sh <pr> --issue {n} --fix
   Report its verdict verbatim. Do not return until it says LINKED, or explain
   why it cannot.
7. Do NOT clean up after yourself — no `rm`, no worktree removal, no branch
   deletion; the parent runs one batch cleanup at the end. If you produced
   gitignored artifacts (fixtures, bench outputs) in a worktree, copy them into
   the main checkout at {repo root} before returning or they will be lost.

Return exactly:
BRANCH: <name>
PR: <url or "none" + reason>
BASE: <branch the PR targets>
LINK: <link_check.sh verdict — LINKED | NOT_LINKED(<detail>) | WRONG_BASE>
CHANGED: <file list>
VERIFY: <exact command run> -> <pass/fail + the failing output if any>
SCOPE-NOTES: <anything in the issue you did not implement, and why>
UNRESOLVED: <judgment calls you had to make, or "none">

If the issue cannot be implemented as written, stop before creating a branch and
return only UNRESOLVED with what is missing.
```

## CI watch and repair (`sonnet`)

Fully specified pass/fail work — `sonnet`. Escalate to `opus` only if the same
failure survives two repair attempts.

```
Intent: PR #{pr} implements issue #{n} and will be merged as soon as CI is green.
I need it green, or a clear statement of why it cannot be.

Run:
  "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/scripts/ci_watch.sh {pr} --timeout 1800

If verdict is PASS, return immediately.

If verdict is NO_CHECKS, this repo has no CI on this PR. Do not merge on that
alone: run the project's own verification command in the branch worktree at
{worktree_path} — {verify_command} — and report its result as LOCAL-VERIFY.

If verdict is FAIL: read the failing logs the script printed, fix the cause in
the branch worktree at {worktree_path}, commit, push, and re-run ci_watch.sh.
Repeat at most {max_retries} times total.

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
UNRESOLVED: <anything needing a human, or "none">
```

## Merge and issue closure (no spawn)

Landing is one script call and a verdict read — run it in the main context:

```
"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/shipping-issues/scripts/land_pr.sh {pr} --issue {n}
```

`--issue {n}` makes the script re-check the closing link before merging (and
repair a missing `Closes #{n}`), then confirm after the merge that issue #{n}
really closed — closing it explicitly if GitHub's auto-close did not fire.

Add `--auto` when `ci_watch.sh` reported `review_decision: REVIEW_REQUIRED` or
`merge_state: BLOCKED` for a reason other than failing checks.
