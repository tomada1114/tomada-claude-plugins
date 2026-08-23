# Cost discipline

What this skill keeps out of the main context, why the run count is what it is,
and why the work is split the way it is between Codex and the parent. Read it
when deciding whether to delegate a step, or before changing a run count.

The main context holds the selection and the verdicts, nothing else. Issue
bodies go to the triage agent, diffs stay in the Codex run that produced them,
CI logs reach the repair run through a file rather than through the prompt. If
you find yourself about to read a full `gh` JSON blob or a workflow log in the
main context, that is the signal to delegate instead.

Labeling is the cheap half of this by design: the backfill is a pure script pass
with a one-line summary, and re-deriving priority from issue prose happens once
per issue — ever — because the answer is written back to GitHub. On a labeled
backlog the whole ranking step is `--select`, three lines, no spawn at all.
Never re-read bodies to reconstruct a priority a label already carries; if a
label looks wrong, fix the label.

Run count scales with issue count, not with thoroughness: one triage spawn
(optional), one implementation run per issue, one review run per PR, one repair
run per failing CI attempt. The adversarial pass is the only conditional extra
and only for a heavy diff — a schema, storage layer, or public contract; a new
or bumped dependency; behavior rewired across modules. Filing a follow-up
(step 9) never adds a run — whatever found it already returned the lead under
`FOLLOW-UPS`, and confirming it costs a couple of targeted reads in the main
context, which is also what makes the tier trustworthy.

## Why the split is where it is

The dividing line is **`gh`**. It cannot authenticate inside the Codex sandbox,
so anything that talks to the GitHub API — priority research, opening the PR,
`link_check.sh`, `ci_watch.sh`, `land_pr.sh` — stays with the parent, and
everything that is code in a worktree goes to Codex. That is not a workaround
being tolerated; it is what keeps every merge-gating fact established here from
script output rather than accepted on a worker's report.

Implementation stays delegated even when the main model is Opus — a deliberate
exception to the Opus-main "do it yourself" default, bought for context
isolation: the diff, the repo exploration, and the CI logs are never needed in
the main context again. Review is a **separate** Codex run from implementation,
which costs one extra run per PR and buys the only thing that makes it a review:
a context that did not write the diff.

Model and reasoning effort are not passed on the Codex path at all. Leaving them
unset makes each run inherit the Codex CLI's own configuration file, so the
model is changed in one place when a newer one ships, and the strongest effort
setting stays reachable — one of the two entry points rejects the top effort
level outright while that file accepts it. The header of
`scripts/codex_run.sh` carries the exact path, the reasoning, and the one-off
override; `platform-notes.md` repeats it per platform.

The Claude-side model assignments that remain (triage on `sonnet`; the
no-Codex fallbacks — implementation on `opus`, CI repair on `sonnet` escalating
to `opus` after two failed attempts) are baked-in conclusions on spec
completeness, and apply as stated on both platforms. (See `orchestrating-models`
§2 for the reasoning; `platform-notes.md` notes where that citation resolves.)
