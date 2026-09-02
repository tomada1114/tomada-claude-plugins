# Worktree parallelism

Read at [step 2c](../SKILL.md#2c-group-for-parallelism--all-mode-only), before
deciding a batch runs in parallel, and again at step 9 before cleanup. Covers
what a worktree run needs that the main checkout already has, what it costs,
and the failure modes that look like something else.

Which *issues* may run together is a dependency question and lives in
[dependency-triage.md#parallel-vs-sequential-all-mode](dependency-triage.md#parallel-vs-sequential-all-mode).
This file is about whether the *repository* can support it at all, and how.

## Table of Contents

- [Why worktrees, and what they do not buy](#why-worktrees-and-what-they-do-not-buy)
- [Layout](#layout)
- [Viability gate](#viability-gate)
- [What a fresh worktree is missing](#what-a-fresh-worktree-is-missing)
- [Failure modes that look like the issue's fault](#failure-modes-that-look-like-the-issues-fault)
- [Teardown](#teardown)

## Why worktrees, and what they do not buy

The long pole in shipping an issue is the implementation run, and those runs
are independent when the issues are. Three of them in three worktrees finish
in roughly the time one takes. Everything after that — PR, CI, merge — is
either serialized by GitHub or serialized on purpose, and stays that way.

So the honest accounting is: parallel mode compresses the implementation wait
and nothing else. It buys that by paying, per issue, one dependency install
and one baseline run, plus the risk that two issues collide in ways the
grouping check missed. Under two issues in a group, that trade is a loss —
which is why single-issue mode never uses a worktree.

A second thing it buys, and the reason not to dismiss it on a small batch:
the main checkout is never switched off the default branch, so the user can
keep working in it while a run is in flight.

## Layout

```
<runstate>/worktrees/<issue-number>/     <- one worktree, branch <type>/<n>-<slug>
<runstate>/verify/<n>-baseline.log       <- its baseline, outside the worktree
<runstate>/ci/<pr>.log
```

`<runstate>` is
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/shipping-issues/<owner>__<repo>/`.

**Not** `<repo>/.claude/worktrees/`, which is where Claude Code's own
`EnterWorktree` puts them. A worktree nested inside the repo shows up as
`?? .claude/` in the main checkout's `git status` unless that repo happens to
ignore the path — and this skill reads an unexplained dirty main checkout as
someone else's work and stops. Keeping worktrees under `<runstate>` also
means one rule covers every file the run generates: none of it is ever inside
the checkout.

One consequence worth knowing: `ExitWorktree` only removes worktrees the same
session created through `EnterWorktree`. It will not touch these, and neither
will `Agent(isolation: "worktree")`'s auto-cleanup, which only fires when the
agent changed nothing. Teardown here is `cleanup_run.sh` and nothing else.

## Viability gate

`worktree_setup.sh` reconstructs what a fresh worktree lacks — it copies the
untracked local config, installs from the lockfile, and runs the project's own
verification command. Whether that is *enough* for a given repo is not worth
predicting; it is worth testing, once, cheaply.

Provision the group's **first** worktree and read its `verdict:` line:

- `verdict: READY` → the repo is worktree-viable. Provision the rest.
- `verdict: BLOCKED` → the worktree could not be created, or the dependency
  install failed. Not viable in this run.
- `verdict: READY_WITH_WARNINGS` with a red baseline → compare against the
  main checkout. **Red in both** is the repository's own broken state, which
  step 3 already knows how to report; parallel mode is still fine. **Green in
  the main checkout, red in the worktree** is the interesting case: something
  the verification needs is not reconstructible from tracked files plus a
  lockfile. Not viable.
- `deps: MANUAL(...)` → the script found a dependency manifest it will not
  guess a command for. Either supply the install command yourself and re-run,
  or treat the repo as not viable.

Not viable → remove that worktree, fall back to serial for the whole run, and
say which of these it was in the step 10 report. Do not retry per issue: the
answer is a property of the repository, not of the issue.

The usual causes of "green in main, red in the worktree", none of them worth
working around inside a run: a hand-built virtualenv or toolchain outside the
lockfile; a local database with data in it that fixtures assume; a service the
tests reach through a path relative to the developer's real checkout; a build
cache the suite treats as required rather than as an optimization.

## What a fresh worktree is missing

`git worktree add` checks out **tracked files only**. Everything below is
absent, and `worktree_setup.sh` handles the first two:

- **Untracked local config** — `.env`, `.env.local`, `*.local`, `.envrc`,
  `.claude/settings.local.json`. Copied from the main checkout. `.example` /
  `.sample` / `.template` variants are skipped, and so is anything actually
  tracked.
- **Dependencies** — `node_modules`, `vendor/`, `.venv` are all empty.
  Reinstalled from the lockfile. On macOS the script clones `node_modules`
  with `cp -Rc` first (APFS clonefile: near-instant, copy-on-write) except
  under `npm ci`, which wipes the directory anyway.
- **A virtualenv can never be copied.** `pyvenv.cfg` and the `bin/` shims
  hold absolute paths; a copied `.venv` is a broken one that fails in
  confusing ways. It is always re-created by the tool.
- **`.git` is a file, not a directory** in a linked worktree — it is a gitlink
  pointing into the main `.git/worktrees/<name>`. Any tool that assumes a
  `.git/` directory can misbehave; hook installers (husky, lefthook) are the
  common ones, and hooks themselves are shared repo-wide rather than
  per-worktree.
- **Build and type-check caches** (`.next`, `dist`, `__pycache__`, anything
  keyed by absolute path) start cold. First run in each worktree is slower.

## Failure modes that look like the issue's fault

- **Port collisions.** Two worktrees running a dev server or an integration
  suite bind the same default port; the second fails with something that reads
  like a test failure. This is why the setup calls are made one at a time, and
  why a repo whose verification binds fixed ports is not parallel-safe. The
  symptom to watch for: two or more concurrent runs report `VERIFY` failures
  that do not reproduce when the same command is re-run alone. That is the
  repo telling you it is not parallel-safe — finish the batch serially and
  record it.
- **One shared local database or fixture directory.** Same shape as ports:
  the failures land on whichever run lost the race, and look like flakes.
- **A branch cannot be checked out twice.** git refuses to add a worktree for
  a branch already checked out elsewhere. The `<type>/<n>-<slug>` naming makes
  this collision-free across issues, so hitting it means a stale worktree
  survived an earlier run — a [stop condition](../SKILL.md#stop-conditions),
  not something to force past.
- **Shared refs and object store.** Worktrees have their own index and working
  directory but one `.git`. Ordinary concurrent edits and commits are safe;
  what is not safe is running `git gc`/`prune` from one while another writes.
  Nothing in this skill does that — do not add it.
- **`gh` shares one token and one rate limit.** Parallel implementation runs
  do not touch the GitHub API at all (the implementation template forbids it),
  which is what keeps this from mattering. It starts mattering the moment
  someone lets a sub-agent call `gh`.

## Teardown

All of it goes through `cleanup_run.sh --worktree-root <runstate>/worktrees`,
in one batch at step 9, after the last merge. Never `git worktree remove` or
`rm` ad hoc — raw `rm` trips a permission prompt and stalls the run, and the
single entry point is what lets deletion be gated on merge status.

Two facts that decide how to call it:

- **Gitignored files inside a worktree do not block removal and are lost with
  it.** A fixture, a benchmark result, a generated artifact an implementation
  run produced but did not commit is gone. The implementation template tells
  sub-agents to copy anything like that into the main checkout before
  returning; when one reports having produced such a file, confirm it landed
  before cleanup runs.
- **The default removes every worktree under the root**, including one another
  session is mid-run in. That is correct at the end of a run this skill owns
  end to end. It is wrong when other sessions may be working in the same repo,
  and wrong when cleaning up outside a run just to reclaim disk — pass
  `--merged-only` there, which keeps any worktree whose branch has no merged
  PR. A dirty worktree is skipped and listed either way; `--force` overrides
  that, and only after salvaging what matters.

Leaving worktrees behind is not free: each carries its own installed
dependencies and caches, so a few stale ones reach gigabytes.
