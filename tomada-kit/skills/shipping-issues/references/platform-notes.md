<!-- platform-annex -->
# Platform notes (this skill's own Codex constraints and best-effort degradation)

- [Delegating to the Codex runtime (primary path for steps 3 / 6 / 7)](#delegating-to-the-codex-runtime-primary-path-for-steps-3--6--7)
- [Tool mapping](#tool-mapping)
- [Constraints under Codex (best-effort degradation)](#constraints-under-codex-best-effort-degradation)

**Premise: judge by whether the running runtime exposes it, not by whether the
product is Codex.** Codex the product may support parallel multi-agent
execution, but that does not mean the session that launched this skill can
call that spawn API (observed in practice: a runtime with no agent-launch API
exposed at all). The "Codex:" column below is the degraded path for *a
runtime that does not expose delegation* — not a feature list of the Codex
product. Where delegation is available, use the same path as Claude Code.

## Delegating to the Codex runtime (primary path for steps 3 / 6 / 7)

Implementation, review, and CI repair are handed to Codex through
`Skill(codex:rescue, ...)`, the **openai-codex** plugin's subagent — a thin
forwarder that runs one Codex turn and returns its output verbatim. Five
things about it decide how *this* skill routes:

- **Readiness.** `Skill(codex:setup)` reports whether Codex is installed and
  authenticated. Not ready → every Codex step falls back to the legacy paths
  described in each SKILL.md step (`opus`/`sonnet` sub-agents, or sequential
  inline work). Step 0 settles this once.
- **No `--cwd` of its own.** `codex:rescue` operates wherever the calling
  session's own working directory already is — there is no flag to scope one
  call to one worktree. The request's own opening sentence ("work only inside
  {worktree_path}") is the entire isolation boundary, which is why steps 3 and
  7 run one issue at a time even in `all` mode (see "Tool mapping" below).
- **The GitHub API is out of reach inside the Codex sandbox** (`git` still
  reaches github.com for clone/push; the sandbox otherwise has no network).
  So every task that touches it — priority research, PR creation,
  `link_check.sh`, `ci_watch.sh`, `land_pr.sh` — stays in the parent. Codex
  only handles code inside the worktree.
- **Model and effort are never passed**, so each run inherits the Codex CLI's
  own configuration file — also the only way to reach the top reasoning tier,
  since `codex:rescue`'s own `--effort` flag tops out at `xhigh`.
- **Codex cannot ask a question back**, and the return is free text, not a
  validated schema — `git -C <worktree> status --short` is the authority on
  what changed, never the run's own prose.

**The openai-codex plugin is a Claude-Code-only plugin and is not bridged to
Codex.** On a Codex host `codex:rescue`/`codex:setup` do not resolve at all,
in which case steps 3, 6 and 7 take the "no usable Codex" ladder below. Treat
that as the expected Codex-host path, not as a broken install.

## Tool mapping

- Delegating priority research (step 2) → Claude Code: spawn one `sonnet`
  sub-agent and hand it the Priority research template from
  the skill's delegation-templates reference / Codex: the main
  context reads the same file skill-relatively and runs the read → rubric →
  `apply_priority_labels.py` steps inline. This is the one step never
  delegated to the Codex runtime — the whole thing is GitHub API calls, and
  the sandbox has no network to make them.
- Implementation (step 3) → Claude Code:
  `Skill(codex:rescue, args="--wait <request telling it to work only inside
  <worktree>>")`, **one issue at a time** — `codex:rescue` has no `--cwd`, so
  there is no structural guarantee two concurrent calls stay in the two
  worktrees they were each told about, unlike a runner that scopes a run to a
  directory by flag. Not ready (`codex:setup`) or on a Codex host, falls to
  the legacy path (Claude Code: one `opus` sub-agent per issue, parallel
  groups at `isolation: "worktree"` capped at 3 — this path *does* have real
  per-agent isolation and may run in parallel / Codex: the main context
  processes worktrees one at a time). Scope is the same regardless of path:
  branch → implement → test → commit → push. PR creation always stays with
  the parent.
- Review (step 6) → Claude Code: `Skill(codex:rescue, args="--wait <read-only
  request>")` against the worktree. Being a **separate run** from the
  implementation is the requirement; explicitly asking for read-only behavior
  in the request is what keeps it from writing anything, since `codex:rescue`
  defaults to write-capable. Unlike steps 3/7, two of these against the same
  worktree may run in parallel (native review + adversarial), since neither
  writes. Not ready, or on a Codex host, falls back to the legacy ladder (one
  independent reviewer where delegation is available = `DELEGATED`, otherwise
  `UNAVAILABLE`).
- Parallelizing CI-watch (step 7) → Claude Code: with several PRs in flight
  in `all` mode, run watches in the background via `run_in_background` /
  Codex: run `ci_watch.sh` per PR sequentially. The watch itself always
  stays with the parent (it needs the GitHub API). This backgrounding applies only to a
  session that stays active to receive the completion — the interactive
  top-level session, or a call actively awaited in the same turn (e.g. via
  `Monitor`). **A delegated subagent running this skill on a caller's behalf
  (a fork, a spawned worker) must not background a wait and end its turn
  expecting a later wake-up** — a subagent's turn ending is how the harness
  learns it is done, so nothing resumes it just because a job it detached
  from later finishes. There, block on `ci_watch.sh` directly, one PR at a
  time, even under `all` mode.
- CI repair (step 7, on FAIL only) → Claude Code: the watch is already
  redirected to `<runstate>/ci/<pr>.log` — outside the worktree, so it cannot
  leave the worktree dirty or be swept into a commit — and that path is
  handed to `Skill(codex:rescue, args="--wait <request>")`, one PR at a time,
  same reasoning as step 3. The parent drives the re-watch and the loop of up
  to 3 attempts. Not ready, or on a Codex host, falls to the legacy path
  (Claude Code: one `sonnet` sub-agent per failing PR, re-spawned as `opus` if
  the same failure survives two attempts in a row / Codex: the main context
  works one PR at a time, up to 3 attempts, raising its own effort and
  continuing if the same failure survives two in a row).
- Presenting options / confirming (step 2's tie-break, preflight's
  dirty-tree check, etc.) → Claude Code: `AskUserQuestion` / Codex: ask the
  user directly in plain conversational text and wait for the reply.
- The citation of `orchestrating-models` §2 (the rationale for model
  assignment) → that is a Claude-Code-only skill, and it is not bridged
  from this skill, so Codex cannot resolve the reference. The sonnet/opus
  assignments themselves stay in SKILL.md's body as a conclusion valid on
  both platforms — only the citation target goes stale.
- Reaching the GitHub API (issue/PR/Actions operations) → the parent handles
  it as-is on both platforms; how it does so is not this skill's concern. The
  Codex sandbox having no network is the only exception (above).

## Constraints under Codex (best-effort degradation)

- Spawning sub-agents (priority research, and each fallback when there is no
  usable Codex) → on a runtime that does not expose spawn capability,
  everything becomes sequential inline execution in the main context. Judge
  the capability against the runtime, never guess it from the product name.
- Parallel implementation across issues and parallelized CI-watch in `all`
  mode → both become sequential, one issue/worktree and one PR at a time.
  The rank → implement → CI → merge phase order is preserved, but **the cost
  is not just wall-clock time**: the per-issue context isolation that
  delegation provided is also lost, so diffs, repo exploration, and CI logs
  for the whole run pile up in one context. Run the sequential path's `all`
  in small batches and report the rest as deferred.
- Step 6's review → with no usable Codex, take the highest rung of
  capability still reachable:
  1. Where the runtime exposes delegation, spawn ONE independent reviewer
     against the branch — assign it `opus`, since review and bug-finding is
     Opus-class work — and record `REVIEW: DELEGATED` (this counts as a
     review because a context that never wrote the diff is reading it).
  2. Otherwise, `REVIEW: UNAVAILABLE`.

  Never re-read your own diff and call that a review. `UNAVAILABLE` is an
  explicit lowered-assurance mode, not a silent skip: record it in the run
  record as `--event review --field status=UNAVAILABLE`, and name it again
  on that issue's line in the step 11 report. Lint, types, tests, and CI all
  passed, but nothing judged the change for unnecessary complexity, intent
  match, or maintainability — the user needs to be able to see that gap in
  assurance.
- Git sandbox restrictions → `git status`/`commit`/`push`/`switch` go
  through, but operations that write to `.git/index.lock` or `FETCH_HEAD`
  (`git fetch`, `git pull`, deleting a branch/ref, worktree operations,
  `cleanup_run.sh` as a whole) can fail with `Operation not permitted`. The
  skill adds no branch for this — just re-run that one Git operation with
  elevated permissions.
- Tool cache write restrictions → a package manager or test runner may be
  unable to write to its default user cache (`~/.cache/...`, etc.), so the
  first dependency resolution or test run can fail. Re-run it with that
  tool's cache environment variable pointed at a writable temp directory
  (`<TOOL>_CACHE_DIR=<writable tmp>`).
