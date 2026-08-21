# Cost discipline

What this skill keeps out of the main context, why the sub-agent count is what
it is, and why the model assignments are fixed. Read it when deciding whether
to delegate a step, or before changing a spawn count.

The main context holds the selection and the verdicts, nothing else. Issue
bodies go to the triage agent, diffs stay in the implementation agent, CI logs
stay in the repair agent. If you find yourself about to read a full `gh` JSON
blob or a workflow log in the main context, that is the signal to delegate
instead.

Labeling is the cheap half of this by design: the backfill is a pure script pass
with a one-line summary, and re-deriving priority from issue prose happens once
per issue — ever — because the answer is written back to GitHub. On a labeled
backlog the whole ranking step is `--select`, three lines, no sub-agent. Never
re-read bodies to reconstruct a priority a label already carries; if a label
looks wrong, fix the label.

Sub-agent count scales with issue count, not with thoroughness: one triage
(optional), one implementation per issue, one CI-repair per PR. The self-review
passes (step 4.5) normally add no spawn from here — they run inside the
implementation agent, and only the effort level and finding counts come back.
The one exception is the reviewer rung: at most one reviewer per PR, and only
where no built-in review pass was reachable at all.
Filing a follow-up (step 6.5) never adds a spawn — the agent that found it already
returned the lead in `FOLLOW-UPS`, and confirming it costs a couple of targeted
reads in the main context, which is also what makes the tier trustworthy.

Model assignments (triage and CI watch on `sonnet`, implementation on `opus`,
escalation to `opus` after two failed repairs) are baked-in conclusions — the
dividing line is spec completeness — and apply as stated on both platforms.
Implementation stays delegated even when the main model is Opus: a deliberate
exception to the Opus-main "do it yourself" default, bought for context
isolation — the diff, the repo exploration, and the CI logs are never needed
in the main context again. (See `orchestrating-models` §2 for the reasoning
behind these assignments; `platform-notes.md`
notes where that citation resolves.)
