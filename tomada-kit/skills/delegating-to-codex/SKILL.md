---
name: delegating-to-codex
description: "Hand a coding task to the Codex CLI as a separate non-interactive run — an implementation whose diff and repo exploration should never enter this context, a review by a context that did not write the change, a repair driven by a log too large to read here, or a diagnosis or second opinion from a different model family. Provides a runner script (entry-point discovery, read-only vs write sandbox, structured returns), fill-in prompt templates with fixed return contracts, and the sandbox limits that decide what cannot be delegated at all — the forge API and every wait stay with the caller. Use when asked to delegate to Codex, run codex exec, get a second opinion from Codex or GPT, offload a diff or a build log to another agent, hand implementation to Codex, or when a task's reading would otherwise flood this context."
metadata:
  platforms: claude-code
---

# Delegating to Codex

Without this, a Codex handoff is an ad-hoc `codex exec` with an inline prompt:
no readiness check, a model and effort passed by reflex, no fixed return
contract, and a run that helpfully does the irreversible half of the job because
nobody told it not to. This skill owns the runner, the prompt contract, and the
boundary.

## When a run is worth it

Delegate for one of these, and say which:

- **Context isolation** — the reading is the cost, not the thinking. A diff, a
  repo you have never opened, a CI log. Worth it even when your own model is
  stronger than the run's: what you are buying is that none of it comes back.
- **An independent context** — a review is only a review if it is read by
  something that did not write it. Re-reading your own diff is not one.
- **A different model family** — a second opinion whose value is that it does
  not share your priors.
- **Parallel tracks** that touch disjoint files.

Do not delegate work you finish in a handful of tool calls, anything that needs
the forge API mid-way (see [references/sandbox-constraints.md](references/sandbox-constraints.md)),
or anything that would need a question answered — the run cannot ask one.

## Preflight, once per session

```bash
${CLAUDE_SKILL_DIR}/scripts/codex_run.sh check
```

`codex_ready: yes` means every route below is open. Exit 3 means no usable
Codex — absent, unauthenticated, or not ready; the `codex_auth` and
`codex_ready` lines say which — and everything falls back. Settle this once and
route later steps off the one answer; re-reading the exit code at each step
turns one question into several.

## Running

```bash
# implement, repair — write-capable
${CLAUDE_SKILL_DIR}/scripts/codex_run.sh task --write --cwd <dir> --prompt-file <file>

# review, investigate — read-only at the sandbox level
${CLAUDE_SKILL_DIR}/scripts/codex_run.sh task --cwd <dir> --prompt-file <file>

# structured adversarial review of a diff
${CLAUDE_SKILL_DIR}/scripts/codex_run.sh review --cwd <dir> --base <ref> --focus-file <file>

# continue the last run in that directory (companion entry point only)
${CLAUDE_SKILL_DIR}/scripts/codex_run.sh task --resume --cwd <dir>
```

`--write` is the permission. Its absence denies writes at the sandbox level, so
a review run cannot quietly patch what it finds — that is a property of the
call, not a promise in the prompt.

Fill the prompt from [references/delegation-templates.md](references/delegation-templates.md):
implementation, review, adversarial review, failure repair, investigation and
second opinion. Each carries a fixed return block; a calling workflow appends
its own fields to that block and keeps only the delta.

### The prompt is a file, and it lives outside `--cwd`

An untracked file left in the work directory makes a later cleanup skip it as
dirty, and a commit convention that stages everything lands the prompt in the
change. Put prompts, pasted specs, and logs in the calling workflow's own state
directory — or, absent one,
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/delegating-to-codex/`.

### Model and effort are not passed

Leaving them unset makes each run inherit `~/.codex/config.toml`'s `model` and
`model_reasoning_effort`, so a newer model is adopted by editing one file. It is
also the only path that can use effort `max` — the companion entry point rejects
that value outright while the config file accepts it. Export `CODEX_RUN_MODEL` /
`CODEX_RUN_EFFORT` for a genuine one-off override; do not pin them anywhere.

## Reading the return

Every subcommand prints `codex_mode:`. `task` adds `codex_status:` (0 = the turn
completed), `codex_thread:` on the companion entry point, `codex_touched:`, and
the run's final message after `---- codex output ----`.

- **`codex_status:` non-zero** — the turn did not complete. Do not retry blindly:
  a run pushes incrementally, so read `git -C <dir> status --short` and
  `git log` for what landed, then resume with a prompt naming what is left.
  Exit 4 is a usage error in your own call, not a run failure.
- **`codex_touched:` is not the file list.** It covers patch-based edits only.
  `git -C <dir> status --short` is the authority.
- **`review` returns** `review_verdict: approve | needs-attention`, a summary,
  and one line per finding with severity, file, line range, and confidence;
  exit 1 means `needs-attention`. On the `codex exec` entry point it returns
  `review_verdict: UNSTRUCTURED` and free text instead, and the exit code reports
  only whether the run completed — read the text, not the code. `UNPARSED` means
  the structured result did not come back; treat it the same way.

The return is a report from a context you cannot inspect. Where a claim in it
gates something irreversible — a merge, a deploy, a deletion — establish that
claim from your own command output instead.

## What never leaves this context

- **The forge API.** `gh` cannot authenticate inside the sandbox. Reading
  issues, opening or editing PRs, watching CI, merging, labeling — all yours.
- **Every wait.** One blocking call per wait, made here. No run hand-rolls a
  `sleep`/poll loop, and a repair loop is driven from here: repair → push → you
  re-check, under a stated attempt cap. Blocking means blocking: never fire a
  wait (a Codex call, a CI watch) via a backgrounded shell job and then end
  your turn assuming something will wake you up later — that only works for a
  session that stays active to receive it. A delegated subagent (a fork, a
  spawned worker) whose turn ends is, as far as the harness is concerned,
  done; a job it merely detached from and stopped watching will not resume it.
- **Deletions and worktree lifecycle.** Create the work copy before the run,
  remove it after. A run that deletes has no undo.
- **Asking the user.** Present the options here and wait for the answer; the run
  is non-interactive with approvals off.

## Parallel runs

Isolation comes from the work copy, not the runtime: one worktree per run,
`--cwd` scoping each to its own. Issue the runs in a single message so they
execute concurrently, then join. Serialize anything that shares a file.

## When there is no usable Codex

Take the highest rung still reachable, and name which one ran:

1. Hand the same filled template, at the same scope, to an independent worker —
   `opus` where the spec could still come back with a question (implementation,
   review, investigation), `sonnet` for fully specified pass/fail work
   (repairing a named failing check), escalating to `opus` if the same failure
   survives two attempts.
2. Otherwise work through the template inline, one task at a time.

For a review specifically, rung 2 does not exist: a context that wrote the diff
cannot review it. Record `REVIEW: UNAVAILABLE` and say so in the final report —
an explicit lowered-assurance mode, never a silent skip.

## Resources

- [references/delegation-templates.md](references/delegation-templates.md) — the
  five prompt templates and the filling rules they share. Read before writing any
  prompt for a run.
- [references/sandbox-constraints.md](references/sandbox-constraints.md) — entry
  points and what each loses, the forge-API boundary, git operations that fail,
  tool-cache failures. Read when a run fails for a reason the prompt cannot
  explain, or when deciding whether a step can be delegated at all.
- `scripts/codex_run.sh` — the runner. `--help` prints its full contract.

## Critical rules

Each of these fails silently or irreversibly, and no wording in the prompt
substitutes for it:

- **Never pass `--write` to a review or investigation run.** Read-only is the
  sandbox flag; a prompt asking the run not to change anything is unenforced.
- **Never let a run touch the forge API or wait on it.** It cannot authenticate,
  and a poll loop inside a run burns the turn without progress.
- **Never accept a pass that was bought by deleting, skipping, or weakening a
  test**, or by re-running a "flaky" job until it happened to succeed. That is a
  failed outcome and gets reported as one.
- **Never treat a run's own report as evidence** for a merge, a deploy, or any
  other irreversible step. Re-derive it here.
