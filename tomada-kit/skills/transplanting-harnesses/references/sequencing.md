# Sequencing the plan

The issues are worked through in one long run by a downstream shipping workflow, which
sorts by dependency level first and by priority label within a level. So the order lives
entirely in two fields — `priority` and `depends_on` — and getting them right is what
makes the difference between a backlog that flows and one that deadlocks on its third
issue.

## Table of Contents

- [The priority ladder](#the-priority-ladder)
- [A blocker is never lower than what it blocks](#a-blocker-is-never-lower-than-what-it-blocks)
- [The dependency chains that recur](#the-dependency-chains-that-recur)
- [No milestones, no phases](#no-milestones-no-phases)
- [The tracking issue](#the-tracking-issue)
- [Issue sizing](#issue-sizing)

---

## The priority ladder

The tiers mean what they mean to the downstream workflow — P0 ships now, P1 is the
ground later issues stand on, P2 is a real self-contained change, P3 is polish. Mapped
onto a harness transplant:

| Tier | What goes here |
|---|---|
| **P0** | The policy document settled (AGENTS.md first, since every later issue cites it). The `priority: P0`–`P3` labels themselves, when the target has no priority vocabulary. Anything else another issue is blocked on. |
| **P1** | The task runner. Hooks and CI rewired to call the same commands. Agnostic copies — workflows, labels file, issue forms, templates. Placeholders for adapt items, and the translation of each one: a placeholder still speaking the reference stack's commands misleads whoever reads it, so its translation ranks with it, not a tier below. |
| **P2** | Coverage floors and the tests that reach them. Architecture enforcement. |
| **P3** | Polish, community health files, and the final issue that removes `docs/harness-reference/` — which depends on every other issue in the plan. |

AGENTS.md is P0 rather than P1 because it is the file every other issue quotes: commands
that do not exist yet, a coverage floor that is not enforced yet, an architecture rule
that is about to be made mechanical. Writing it once, up front, with the intended end
state, is what lets the rest of the plan be written as deltas against it.

## A blocker is never lower than what it blocks

If issue B depends on issue A, then A's tier is at least as high as B's. The script
rejects a plan that breaks this, because the downstream workflow would otherwise hold a
P0 in BLOCKED while it works through P2s — the plan reads as a contradiction and the run
stalls at the top of its own queue.

In practice the fix is almost always to raise the blocker rather than to lower the
dependent. A task-runner command that three P1 issues call is not a P2 however small it
is; it is P1 by the company it keeps.

## The dependency chains that recur

These edges show up in nearly every transplant, and they are the ones the gap table does
not produce on its own:

- **Policy document → task-runner commands → hooks and CI.** The doc names the commands,
  the runner defines them, the hook and the workflow call them. Rewiring the hook before
  the command exists produces a hook that calls nothing.
- **Labels file → triage conventions and issue/PR templates.** Templates that apply
  labels need the labels to exist.
- **Skills source → sync mechanism → drift check.** The check has nothing to compare
  until the mirror is generated, and the mirror has nothing to generate from until the
  source layout is settled.
- **Base lint and type configuration → boundary enforcement.** Import restrictions are
  expressed inside the linter that has to be configured first.
- **Coverage tooling → per-area floors → tests that reach them.** A floor set before the
  measurement works fails for the wrong reason.
- **The seed pull request → every issue that cites `docs/harness-reference/` → the issue
  that removes it.** The removal issue depends on all of them, which is what keeps the
  snapshot from outliving its purpose.

## No milestones, no phases

The plan uses none. Milestones, phase labels and "part 1 of 3" titles are a second
ordering that nothing enforces and that goes stale the moment an issue is re-tiered.
Dependency edges and priority labels already carry the order, and the downstream workflow
reads exactly those two.

## The tracking issue

The final issue — the one removing `docs/harness-reference/` — ends with a step that
closes the tracking issue, so nothing is left for a shipping run to pick up.

One parent issue, every other issue attached to it as a sub-issue, with a task list of
them in its body — appended by the script, not written by hand.

It carries no priority label. An umbrella issue is not implementable, and a workflow
that ranks it will eventually try to ship it. Its body says what is being transplanted,
from which repository and commit, under which license, and what the end state is, so
that someone arriving at issue 14 of 20 can reconstruct the intent without this
conversation.

## Issue sizing

One issue is one pull request, independently verifiable. The usable test is whether the
body can name a command that fails before the change and passes after. If it cannot, the
issue is either too vague to hand over or is really several issues.

Two signals that a row should be split: the steps run past roughly eight, or the issue
touches more than one rubric area. Splitting along the rubric keeps the dependency edges
legible, since the recurring chains above are all cross-area.

Fill `touches` with the paths the change will actually land in. The downstream workflow
intersects those sets to decide what can be implemented in parallel worktrees, so `*` is
the honest answer when the paths are genuinely unknown and a narrow guess is not — it
will be trusted.
