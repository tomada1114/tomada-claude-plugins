---
name: rethinking-prompt-assets
description: >-
  Rethink a set of prompt assets from zero — memory files (CLAUDE.md, AGENTS.md),
  skills, sub-agent definitions, and the flows they form — and propose large changes:
  delete, merge, split, rebuild, reroute. A sub-agent blind to the current
  assets designs the ideal set for the jobs they serve; the current set is then compared
  with it and with usage evidence from session transcripts. Finds what a
  one-file review cannot: overlap and contradiction between skills, unclear ownership,
  skills unused or never firing, delegation that drifted from the model-assignment
  source, wasted stages in multi-skill flows, cautions that outlived their reason.
  Applies the moves the user approves. Use when asked to rethink, consolidate, prune
  or overhaul all skills or the agent setup, to check a multi-skill flow's shape,
  or to find unused or redundant skills. Not for one document's wording
  (auditing-prompt-docs), one skill's structure (creating-agent-skills), or a
  repository's code (auditing-repositories).
argument-hint: "[scope: empty | asset names | flow <entry skill> | a job in words | repository path] [report-only]"
metadata:
  platforms: claude-code
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/collect_estate.py:*)
---

# Rethinking prompt assets

Asked to review a set of skills, a model reads them one at a time and proposes edits
to each. That review takes the current layout as given, so it never asks whether a
skill should exist, cannot see what two skills say between them, and has no evidence of
what is used. This skill reverses the order: jobs first, an independent design second,
the current assets third. Deleting, merging and rebuilding are ordinary outcomes, and so
is "the current shape is right": every asset gets a verdict, and a change has to show
the cost of leaving things as they are.

The existing single-purpose reviewers are parts, called where a step needs them:
`auditing-prompt-docs` (wording and its linter), `creating-agent-skills` (one skill's
structure; building a replacement), `auditing-repositories` (a repository's harness).
Their own procedures, approval stops and remote writes do not run here; this skill's
proposal is the only approval. Load one with the `Skill` tool; how to call each: [references/claude-code.md](references/claude-code.md#parts-and-their-own-side-effects).

## Contract

**Input:** free-form. The scope is one of:

| Given | Scope |
|---|---|
| nothing | The whole user-level estate: memory files, every skill and command, every sub-agent definition |
| asset names | Those assets. Assets they name, or that name them, are context |
| `flow <entry skill>` | The entry skill and the assets it names directly (its stages), reviewed as one flow. Anything further out is context |
| a job in words ("how work gets delegated") | The assets whose descriptions claim that job. State the pick at the top of the proposal |
| a repository path | That repository's instruction files and skills. Its harness is covered by `auditing-repositories` as a part |

Context assets are read where a check needs them and changed only as part of a
move's blast radius. Scope stops at one step because the reference graph does not: a
few hubs (the model-assignment source above all) are named by a third of the estate,
and following links transitively turns any scope into the whole estate.

`report-only` stops after the proposal is written.

**Output:** `$RUN = ${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/rethinking-prompt-assets/<scope-slug>/runs/<YYYY-MM-DD>/`
holding `evidence.json`, `listing-diff.md`, `needs.md`, `blind-design.md`, `cards/`,
`proposal.md`, and, once moves are applied, `snapshots/` and `staging/`.
`<scope-slug>` is `estate` for the whole estate, otherwise the entry skill, the
repository name, or a 2–4 word slug of the job. The ledger `decisions.json` sits one
level above `runs/`. Edits to the assets come only after approval, in Phase 6.

**The order of the phases is the method.** Until the blind design has returned
(end of Phase 2), read no asset body in scope: only the collector's output, and the
frontmatter descriptions it summarizes. Whatever the session already has in context
(the always-loaded memory files) cannot be unread; do not add to it.

## Phase 0: Orient

1. Resolve the scope and the configuration root: `~/.claude` unless the scope is a
   repository ([references/claude-code.md](references/claude-code.md#where-the-estate-lives)).
2. Record the root's `git status --porcelain`. Files already modified are the user's
   work in progress; Phase 6 treats them differently.
3. Read `decisions.json` if it exists, so declined moves are not raised again.
4. Run the collector and save its output. Run it; do not read it.
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/collect_estate.py <root> --transcripts ~/.claude/projects --json > "$RUN/evidence.json"
   ```
   It reports each skill's size, description length and listing flags, the reference
   graph, every line that names a tier or a model, invocation counts from transcripts
   (typed, model-initiated, inside sub-agents, scratch sessions apart) with the window
   they cover, invocations of skills outside the root, and
   `signals` naming where each cross-check should look first. Signals are hints: zero
   use means no evidence inside the window, nothing more.
5. Compare the collector's skill list with the skill listing this session was
   actually given, and save the differences to `$RUN/listing-diff.md`: skills on disk
   that are absent from the listing, and skills listed by name with no description.
   The collector reads files and cannot see this. The listing has a budget, and over
   it the descriptions of the least-used skills are dropped first; those skills then
   cannot be selected, which keeps them least-used
   ([references/claude-code.md](references/claude-code.md#the-live-listing)).

## Phase 1: Needs

Write `$RUN/needs.md`: the jobs this estate exists to do, as someone would list them
who had never seen it.

- Derive jobs from the evidence: what the descriptions claim, what is invoked and how
  often, and `unknown_invocations`, which shows jobs the user does with assets outside
  the scope. Group by what the user is trying to get done, so that two assets serving
  one job become one job.
- For each job: an id (`J1`…), what prompts it, what done looks like, how often it
  happens (with the window), and any hard fact about the environment it depends on.
- Add environment facts separately: the tools the session has, what kinds of model and effort
  can be bought and their relative cost, standing preferences the user has stated.
- Leave out every asset name, stage count, file layout and tier name. Check the result
  with one question: could a reader reconstruct today's list of skills from this
  document? If so, the jobs are still shaped like the assets; regroup.

Then show the job list and ask, in one `AskUserQuestion` call: which jobs are missing, which are
retired, and what annoys them most about the current setup. Only the user knows the
jobs no asset covers yet and the ones they have stopped doing. Fold the answers in.

## Phase 2: Blind design

Spawn one `architect` sub-agent (`Agent` with `subagent_type: architect`) with
[references/agents/blind-designer.md](references/agents/blind-designer.md), filled with the needs document, and save the
reply verbatim as `$RUN/blind-design.md`. One spawn; the comparison stays in this
session.

Check the returned design for leakage: units named after existing assets, or
boundaries that match the current ones one for one, suggest the designer saw the
estate. Note it in the proposal; do not discard the design.

## Phase 3: Read the current state

Now read the assets in scope. With about a dozen assets or fewer, read them here.
With more, split them into disjoint slices and spawn one `scout` sub-agent per slice
with [references/agents/card-writer.md](references/agents/card-writer.md), all in one message, at most 4. Save each
reply under `$RUN/cards/`; a `scout` cannot write files. Cards extract what each asset
says and judge nothing. Afterwards open the full text of any asset a check implicates:
a move is never proposed from a card alone.

Tier criteria live in the `orchestrating-models` skill.

## Phase 4: Compare

1. **Design against estate.** Map each unit of the blind design to current assets:
   same shape; one unit spread over several assets; several units inside one asset; a
   unit with no asset; an asset with no unit. Do the same for flows, stage by stage.
2. **Cross-checks.** Run X1–X8 in [references/cross-checks.md](references/cross-checks.md): overlap,
   contradiction, unclear boundary, unused or unreachable, tier drift, flow waste,
   leftovers, memory files against skills. Call a part where a check says to.
3. **Verdict per asset:** keep, or one of the move kinds in
   [references/proposal.md](references/proposal.md#moves). A difference from the blind design is a reason to
   look, not a finding. A move needs evidence of a present cost and an honest cost of
   moving; where the design differs and no cost can be shown, the verdict is keep and
   the difference is recorded as not acted on. Report every finding with its
   confidence; low-confidence ones go in the proposal marked as such.

## Phase 5: Propose

Write `$RUN/proposal.md` in the format of [references/proposal.md](references/proposal.md#proposalmd) and ask for
approval as described there. The unit of approval is the move: one structural change
with everything needed to leave the estate consistent, approvable and revertable on
its own. **Change no asset before the user names the moves to apply.**

## Phase 6: Apply

Follow [references/proposal.md](references/proposal.md#applying-approved-moves): one move at a time including its
blast radius, its targets snapshotted first, each done with the part that owns that
kind of work, replacements staged and swapped in with the removals in a single
confirmed step at the end, the collector and validators re-run, the ledger updated,
no commit or remote write unless asked.

## Resources

- [references/cross-checks.md](references/cross-checks.md): the eight cross-asset checks, the evidence each
  starts from, and what makes a finding. Read at Phase 4.
- [references/proposal.md](references/proposal.md): move kinds and sizing, the proposal format, the approval
  round, the ledger, and the rules for applying moves. Read at Phase 4.3 and after.
- [references/agents/blind-designer.md](references/agents/blind-designer.md), [references/agents/card-writer.md](references/agents/card-writer.md): the two
  sub-agent briefs.
- [references/claude-code.md](references/claude-code.md): configuration roots and the transcript location,
  the tool for each step, the listing budget, the limits of blindness, how each part
  is called, and the follow-ups a move creates in published copies.
- `scripts/collect_estate.py`: run it, do not read it. Standard library only; tests
  in `scripts/tests/`.
