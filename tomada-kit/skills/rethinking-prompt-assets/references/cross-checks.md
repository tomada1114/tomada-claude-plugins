# Cross-asset checks

The checks no single-asset review can make, because each needs two or more assets (or
an asset and the evidence of its use) side by side. Run them in Phase 4, after the
blind design has returned. `evidence.json` field names refer to the collector's output.

A check that finds nothing is recorded under "Examined and kept" with what was looked
at. Every finding carries the two `path:line` locations that make it a finding, a
confidence, and the cost it causes today.

## Table of Contents

- [X1: Overlap](#x1-overlap)
- [X2: Contradiction](#x2-contradiction)
- [X3: Unclear boundary](#x3-unclear-boundary)
- [X4: Unused or unreachable](#x4-unused-or-unreachable)
- [X5: Tier drift](#x5-tier-drift)
- [X6: Flow waste](#x6-flow-waste)
- [X7: Leftovers](#x7-leftovers)
- [X8: Memory files against skills](#x8-memory-files-against-skills)
- [X9: Coordination fit](#x9-coordination-fit)

## X1: Overlap

Two assets instruct the same job, or state the same fact or rule.

- Start from: pairs linked in `mentions` / `mentioned_by`; the cards' `Restates` and
  `Claims to own` fields; descriptions that would both match one request.
- Finding when: a request exists for which the model could reasonably load either, or
  a rule is written out in both so that changing it means editing two places.
- A pointer ("criteria live in the X skill") is the cure, not an overlap.

## X2: Contradiction

Two assets, or an asset and a memory file, give instructions that cannot both be
followed.

- Start from: the same subject in two cards (delegation rules, approval rules, output
  paths, git and remote-write rules, language rules); memory-file rules against the
  skills they govern.
- Finding when: following one breaks the other. Quote both. Say which one the model
  is likely to obey (the more specific, the more recently loaded) and what that costs.

## X3: Unclear boundary

A reader cannot tell from the descriptions which asset owns a request.

- Start from: the blind design's units set against current assets. Where the design
  has one unit and the estate has several, or the reverse, the boundary is in question.
- Also: an asset whose `Explicitly not its job` names no neighbor although an adjacent
  asset exists; a pair that each defer to the other.
- Finding when: you can write one realistic request and name two assets that would
  each claim it, or none.

## X4: Unused or unreachable

An asset that costs listing space and maintenance and shows no sign of doing work.

- Start from: `listing-diff.md`, `signals.no_evidence_of_use`,
  `signals.no_description`, `non_skill_dirs` (a directory with no SKILL.md, or a
  symlink whose target is gone), `signals.never_model_invoked`,
  `listing.description_chars_total`, and `commands` with their usage.
- Check the live listing before anything else. A skill whose description Claude Code
  dropped cannot be selected by the model, so its zero usage says nothing about
  whether it is needed. That is a finding about the listing as a whole (too many
  descriptions for the budget), and the cure is fewer or shorter descriptions across
  the estate, or marking some skills as typed-only on purpose, not deleting the
  skill that happened to lose.
- Read `usage_window` first: absence of use is a claim about that window only. Read
  the usage numbers with these limits in mind:
  - an asset reached only when a parent reads it by name can show zero invocations
    (`signals.reached_only_through_other_assets`);
  - a typed command and a model-initiated load are counted apart, and an asset that is
    only ever typed has a description that never wins selection on its own;
  - `scratch` counts are experiments and say nothing about real use.
- Separate the three failures: **cannot fire** (absent from the live listing, or
  listed without a description), **never needed** (no job in the needs document maps
  to it: candidate for deletion), and **needed but not firing** (listed in full, a job
  maps to it, usage is nil, and `unknown_invocations` or the user's account shows the
  job being done some other way: a description or boundary problem).
- An asset with no evidence of use and no job in the needs document is still the
  user's call: ask in the proposal, do not assume.

## X5: Tier drift

What an asset does when it delegates differs from the estate's own source for model
assignment (the skill that owns tier selection, and the sub-agent definitions).

- Start from: each asset's `tier_mentions`, `model_mentions`, `signals.delegates`,
  `signals.names_models_but_no_tier`; `agents` for what each tier really is.
- Finding when any of these holds:
  - a hand-off names no tier, or names a raw model or effort instead of a tier;
  - the tier named does not fit the job by the source's own criteria (a judgment-free
    survey on the expensive tier; work with open questions on the cheap one);
  - an asset copies the assignment table instead of pointing at the source, and the
    copy has gone stale against `agents`;
  - a memory file's summary of the tiers disagrees with the definitions;
  - a tier exists that no asset uses, or assets need a kind of worker no tier covers.
- The tier set itself is in scope: compare it with the kinds of worker the blind
  design asked for under `Delegates`.

## X6: Flow waste

A job that spans assets takes more stages, hand-offs or user stops than it needs.

- Start from: the blind design's `Flows` set against the cards' `Steps`, `Inputs`,
  `Outputs` and `Asks the user` for the same job.
- Trace one realistic run end to end and list, per stage: what it reads, what it
  writes, what the next stage does with that output, where the user is stopped.
- Finding when:
  - a stage's output is not read by any later stage, or is re-derived by one;
  - two stages ask the user the same thing, or a later stage re-opens a decision an
    earlier one closed;
  - a stage exists only to call another asset and adds no decision of its own;
  - the order forces rework (a later stage routinely invalidates an earlier output);
  - a session boundary or hand-off falls where nothing needs a fresh context.
- Usage shows which stages are skipped in practice: a child that is never loaded
  while its parent is used often is a stage people route around.
- Whether the contexts in a stage exchange information in the right shape is X9.

## X7: Leftovers

Instructions whose reason is gone.

- Start from: the cards' `Cautions` and `Model-specific text`; `model_mentions`.
- Finding when:
  - a caution gives no reason, or its reason describes an incident, tool or model that
    is no longer present;
  - text addresses a model version that no tier runs, or works around a behavior the
    current guidance says has changed;
  - the same caution has been copied across assets since a single incident.
- The wording-level version of this check, and the list of phrasings that now hurt, is
  the `auditing-prompt-docs` linter and its rules file. Run the linter over the
  in-scope files for the mechanical hits and use its per-model references to decide
  whether a reason still holds. Structural leftovers (a whole section, phase or asset
  that exists for a departed model) are this check's own.

## X8: Memory files against skills

The always-loaded files carry what belongs in an on-demand asset, or the reverse.

- Finding when: a memory file holds a procedure used in a minority of sessions (it
  costs context in all of them); a rule every session needs lives only in a skill that
  may not load; a memory file restates a skill.

## X9: Coordination fit

A stage that uses more than one context moves information between them in a shape
that does not match the work: who hands what to whom, and whether anything is shared
before the final result. X6 asks whether a stage should exist; this check asks whether
the contexts inside a flow are wired the right way.

The criteria for choosing a shape (lead and sub-agents that only return results, a
checker loop, long-lived workers, workers that exchange findings mid-run, and what
each costs) live in the estate's model-assignment source; in the user-level estate
that is the coordination section of the `orchestrating-models` skill's delegation
patterns. Read it before judging and point at it in the move; do not restate it. Its
default is the simplest shape, a lead with sub-agents, so a move toward a heavier
shape needs evidence that the simple one is struggling, while a move toward a lighter
one needs only evidence that the extra channel is unused.

- Start from: the cards' `Coordination` and `Delegations` fields; the blind design's
  `Coordination` line per flow; `environment` in the needs document for which
  mechanisms exist and whether agent teams are enabled
  (`claude-code.md`, "Coordination mechanisms").
- For each multi-context stage, write down three facts before judging: what each
  worker must know from the others while it works (nothing, or which findings); what
  comes back to the lead (a summary, a file, pointers); and where the stage has to
  run (interactive only, or also unattended, scheduled, or on another runtime).
- Finding when the shape is too light for the work:
  - the lead carries one worker's findings into another worker's brief, round after
    round, or the instructions have one context play several roles and stage a debate
    between them, where the job is one of competing hypotheses, cross-examined
    review, or implementation and verification that go back and forth;
  - a later stage needs detail that the summary dropped, and the hand-off returns no
    pointer (file path and line, URL) for the lead to open;
  - a worker is re-spawned cold for each of a series of related tasks and re-reads
    the same material each time, where continuing the same worker would keep it.
- Finding when the shape is too heavy:
  - teammates, a shared task list or a shared document are prescribed, yet the
    workers are independent and only their results are combined at the end;
  - workers that can message each other are given the same file to edit, or work
    that is sequential;
  - several contexts are spawned for one decision with no dependency between them
    and nothing gained from running side by side.
- Finding when a shape is used without what makes it work:
  - a checker with no written criteria, a check-and-fix loop with no cap on rounds
    or no rule for what happens at the cap;
  - a shared file with two writers and no owner, or an exchange between workers with
    no end condition (time, agreement, a deciding role);
  - a stage that depends on agent teams inside an asset that also runs unattended,
    on a schedule, or on a runtime without them: teammates start only in an
    interactive Claude Code session with the feature enabled, so elsewhere the
    stage silently runs as something else;
  - teammates named without a sub-agent definition, or expected to run at a
    definition's effort in split panes, where that is not documented to apply; this
    is tier drift (X5) caused by the shape, so report it once, here.
- A stage with one context has no coordination to judge. Record "single context"
  and move on; do not propose a pattern for work that does not need dividing.
- The cure is a `reroute` move. When it adopts agent teams, the move names the
  setting it depends on and where that would be enabled, as a follow-up for the user
  (`claude-code.md`, "Follow-ups after applying moves").
