# What breaks inside a Codex run

Read this when a run fails in a way the prompt cannot explain, or when deciding
whether a step can be delegated at all. Everything here is a property of the
sandbox, not of the prompt — no wording fixes any of it.

## Entry points, and what each one can do

`codex_run.sh` picks the entry point itself and reports it as `codex_mode:`.

| `codex_mode:` | When | What you lose |
|---|---|---|
| `companion` | the openai-codex plugin is installed alongside the `codex` CLI, and Node is present | nothing — job tracking, `--resume`, and structured review output all work |
| `exec` | the `codex` CLI is present without the plugin | `--resume` is unavailable, and `review` cannot return structured JSON (`review_verdict: UNSTRUCTURED` plus free text) |
| `NONE` (exit 3) | no `codex` CLI, or present but unauthenticated (`codex_auth: NOT_AUTHENTICATED`) or not ready (`codex_ready: no`) | everything — fall back |

The companion lives under a version-numbered path inside the plugin cache, so it
is discovered at run time rather than configured. <!-- neutrality-ignore: N2 -->

Settle the mode once, in a preflight `check`, and route every later step off
that one answer. Reading the exit code again at each step turns one question
into several.

## The forge API is out of reach

**`gh` cannot authenticate inside the sandbox.** `git` still reaches
github.com — clone, fetch, push all work — but `gh auth status` fails, so
anything that talks to the GitHub API stays with the caller: reading issues,
opening or editing PRs, watching Actions, merging, labeling, commenting.

This is the dividing line for splitting a workflow. Code inside the work
directory goes to the run; anything that needs the API stays outside it. That is
not a workaround being tolerated — it is what keeps every gating fact
established from your own command output rather than accepted on a run's report.

Treat any other credentialed CLI the same way until proven otherwise, and never
put a secret in a prompt to work around it.

## Git operations that fail

`git status`, `commit`, `push`, and `switch` go through. Operations that write
to `.git/index.lock` or `FETCH_HEAD` can fail with `Operation not permitted`:

- `git fetch`, `git pull`
- deleting a branch or ref
- worktree operations

Do those from the calling context. Create the worktree before the run and remove
it after; never ask a run to clean up after itself.

## Tool caches

A package manager or test runner may be unable to write its default user cache
(`~/.cache/...`), so the first dependency resolution or test run can fail for a
reason that has nothing to do with the code. Re-run it with that tool's cache
environment variable pointed at a writable temp directory
(`<TOOL>_CACHE_DIR=<writable tmp>`). Worth stating in the prompt when you
already know the project needs a network install.

## `--cwd` scoped too wide can fail silently

Pointing `--cwd` at a large parent repository, rather than the specific
directory the prompt actually reads and writes, can produce `codex_status`
non-zero with **completely empty output** — no error, no partial finding, no
clue in the return. This is not the same failure as an incomplete turn (see
below); there is nothing to resume, because nothing ran.

Scope `--cwd` to the narrowest directory that contains everything the prompt
references, and widen it only if a run then reports it cannot reach a file it
needs. A read-only investigation or review over one project's subtree is the
common case this bites — point `--cwd` at that subtree, not at the workspace
root it happens to live inside.

## `codex_touched:` is not the file list

It lists only edits made through patches. Files written by shell redirection do
not appear there. `git -C <work_dir> status --short` is the authority on what
actually changed — check it before believing either `codex_touched:` or the
run's own `CHANGED:` line.

## A stopped run keeps only what was pushed

There is no partial-result recovery beyond the repository itself. This is why
the implementation template pushes as soon as the first coherent commit exists,
and why `codex_status:` non-zero is never a reason to re-run the same prompt
blindly: read `git status --short` and `git log` for what landed, then resume
with a prompt naming what is left.

Gitignored artifacts a run produces — fixtures, benchmark output, generated
reports — die with the work directory. Have the run copy them somewhere durable
before it returns, or lose them.
