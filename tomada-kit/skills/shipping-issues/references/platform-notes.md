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
`{CODEX_SKILL_DIR}/scripts/codex_run.sh`, which belongs to the sibling
**`delegating-to-codex`** skill. That skill owns the runner's contract, the
generic prompt templates, and the full sandbox-limits list; read its
`references/sandbox-constraints.md` when a run fails for a reason the prompt
cannot explain. Four of its rules decide how *this* skill routes:

- **Entry point.** `codex_mode: companion` (the openai-codex plugin is
  installed) has job tracking, `--resume`, and structured review output;
  `codex_mode: exec` (bare `codex` CLI) loses `--resume` and returns
  `review_verdict: UNSTRUCTURED`; `codex_mode: NONE` (exit 3) means no *usable*
  Codex — absent, unauthenticated, or not ready — and every Codex step falls
  back to the legacy paths described in each SKILL.md step (`opus`/`sonnet`
  sub-agents, or sequential inline work). Step 0 settles this once.
- **`gh` cannot authenticate inside the Codex sandbox** (`git` still reaches
  github.com; `gh auth status` fails). So every task that touches the GitHub
  API — priority research, PR creation, `link_check.sh`, `ci_watch.sh`,
  `land_pr.sh` — stays in the parent. Codex only handles code inside the
  worktree.
- **Model and effort are never passed**, so each run inherits the Codex CLI's
  own configuration file.
- **Codex cannot ask a question back**, and **`codex_touched:` is not the file
  list** — `git -C <worktree> status --short` is the authority.

**`delegating-to-codex` is a Claude-Code-only skill and is not bridged to
Codex.** On a Codex host it may not resolve at all, in which case
`{CODEX_SKILL_DIR}` cannot be filled and steps 3, 6 and 7 take the
`codex_mode: NONE` ladder below. Treat that as the expected Codex-host path,
not as a broken install.

## Tool mapping

- Delegating priority research (step 2) → Claude Code: spawn one `sonnet`
  sub-agent and hand it the Priority research template from
  the skill's delegation-templates reference / Codex: the main
  context reads the same file skill-relatively and runs the read → rubric →
  `apply_priority_labels.py` steps inline. This is the one step never
  delegated to the Codex runtime — the whole thing is `gh` calls, and the
  sandbox cannot authenticate them.
- Implementation (step 3) → same on both platforms:
  `{CODEX_SKILL_DIR}/scripts/codex_run.sh task --write --cwd <worktree>`. Only when `codex_mode: NONE`
  does it fall to the legacy path (Claude Code: one `opus` sub-agent per
  issue, parallel groups at `isolation: "worktree"` capped at 3 / Codex: the
  main context processes worktrees one at a time). Scope is the same
  regardless of path: branch → implement → test → commit → push. PR creation
  always stays with the parent.
- Review (step 6) → same on both platforms:
  `{CODEX_SKILL_DIR}/scripts/codex_run.sh task --cwd <worktree>` (no `--write` = read-only). Being a
  **separate run** from the implementation is the requirement, and `--cwd`
  can point straight at the worktree, so there is no need to thread
  delegation into the worktree at all. Add `codex_run.sh review` only for a
  heavy diff. Only `codex_mode: NONE` falls back to the legacy ladder (one
  independent reviewer where delegation is available = `DELEGATED`,
  otherwise `UNAVAILABLE`).
- Parallelizing CI-watch (step 7) → Claude Code: with several PRs in flight
  in `all` mode, run watches in the background via `run_in_background` /
  Codex: run `ci_watch.sh` per PR sequentially. The watch itself always
  stays with the parent (it uses `gh`).
- CI repair (step 7, on FAIL only) → same on both platforms: the watch is
  already redirected to `<runstate>/ci/<pr>.log` — outside the worktree, so it
  cannot leave the worktree dirty or be swept into a commit — and that path is
  handed to `{CODEX_SKILL_DIR}/scripts/codex_run.sh task --write --cwd <worktree>`. The parent drives the
  re-watch and the loop of up to 3 attempts. Only `codex_mode: NONE` falls
  to the legacy path (Claude Code: one `sonnet` sub-agent per failing PR,
  re-spawned as `opus` if the same failure survives two attempts in a row /
  Codex: the main context works one PR at a time, up to 3 attempts, raising
  its own effort and continuing if the same failure survives two in a row).
- Presenting options / confirming (step 2's tie-break, preflight's
  dirty-tree check, etc.) → Claude Code: `AskUserQuestion` / Codex: ask the
  user directly in plain conversational text and wait for the reply.
- The citation of `orchestrating-models` §2 (the rationale for model
  assignment) → that is a Claude-Code-only skill, and it is not bridged
  from this skill, so Codex cannot resolve the reference. The sonnet/opus
  assignments themselves stay in SKILL.md's body as a conclusion valid on
  both platforms — only the citation target goes stale.
- The `gh` CLI (issue/PR/Actions operations, auth) → in the parent, plain
  `gh` works as-is on both platforms — no extra connector or plugin needed.
  The Codex sandbox is the only exception (above).

## Constraints under Codex (best-effort degradation)

- Spawning sub-agents (priority research, and each fallback under
  `codex_mode: NONE`) → on a runtime that does not expose spawn capability,
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
