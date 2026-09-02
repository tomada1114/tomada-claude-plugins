# Dependency and Readiness Triage

## Table of Contents

- [Readiness gate](#readiness-gate)
- [Dependency edges the regex misses](#dependency-edges-the-regex-misses)
- [Ordering rules](#ordering-rules)
- [Parallel vs sequential (`all` mode)](#parallel-vs-sequential-all-mode)
- [Single mode: which issue](#single-mode-which-issue)
- [Deciding a held design](#deciding-a-held-design)

Read after `issue_digest.py` output is in hand, before deciding what to ship.
The script annotates mechanical signals; this file covers the judgment the
script cannot make. Which of the ready issues is *worth* shipping first is a
separate question — see `priority-rubric.md`.

## Readiness gate

An issue is **shippable** only if all of these hold:

1. It states a concrete change — a behavior, a file, an acceptance condition.
   "Consider improving X" is a discussion, not a work item.
2. Nothing it depends on is still open (`BLOCKED-BY` flag empty).
3. No open PR already claims it (`HAS-OPEN-PR` flag absent), unless that PR is
   stale/draft and the user asked to take it over.
4. No `NOT-READY-LABEL` (blocked, question, discussion, wontfix…), and no
   `NEEDS-DESIGN` (`blocked: design` or a recognized equivalent) unless it was
   taken on deliberately — see
   [Deciding a held design](#deciding-a-held-design) below. The two are
   different failure modes: a hard label needs someone else to act first; a
   design block just needs a decision, which this run can make — and by default
   does, in the background, for every design-blocked issue it files or finds.
   An issue whose block was cleared that way is ordinary: it carries a decision
   recorded on the issue itself, and passes this gate like anything else.
5. Its scope is one coherent change. An issue that is really five issues gets
   reported back for splitting, not implemented as a mega-PR.

An issue that fails 1 or 5 is **not** implemented silently. Report it as
`NEEDS-CLARIFICATION` with the specific missing information, and move on to the
next candidate.

## Dependency edges the regex misses

`issue_digest.py` catches explicit `#N` references and common EN/JA dependency
phrasings. These edges only appear on reading:

- **Same-file collision** — two issues that both rewrite `foo.py` are not
  formally dependent, but they must not run in parallel worktrees, and the
  second one's branch must be cut *after* the first has merged, from the
  updated default branch — never from a branch point that predates it.
- **Schema-before-consumer** — an issue adding a column/field must land before
  any issue reading it, even with no cross-reference.
- **Interface-before-implementation** — a protocol/type issue precedes the
  issues that implement it.
- **Config-before-feature** — a settings/validation issue precedes features
  that read those settings.
- **Append-target collision** — a changelog, release-notes file, decision log,
  or generated index that every PR appends to conflicts both-added even when
  the code paths are disjoint. Find such files once, before grouping (what did
  the last few merged PRs all touch?); branches that both append to one are a
  same-file collision.
- **Shared-cause duplication** — two issues that are symptoms of one underlying
  defect (the same rename, the same missing guard) produce the same hunks
  independently. If two shortlisted issues name the same symbol or the same
  failure, ship one first and rebase the other on the result — or report them
  as one issue.
- **Umbrella issues** — an epic listing `- [ ] #12 #13 #14` is not itself
  implementable. Treat it as a container: ship the children, leave the epic.

When two issues could reasonably go either order, prefer the one that is
smaller and touches fewer files first — it shortens the window in which the
other's branch can drift.

## Ordering rules

1. Topologically sort by dependency edges (explicit + inferred above).
2. Within a level, order by `priority:` label tier, then by the digest's score
   within a tier (see `priority-rubric.md` for what each tier means); break
   remaining ties with "touches fewer files" and then "older".
3. Cycles are a data problem, not something to break arbitrarily. Report the
   cycle and ask which edge to drop.

The digest's `UNBLOCKS:#a,#b` flag is the reverse of `BLOCKED-BY` and is the
main input to step 2: an issue several others wait on belongs at the front of
its level even when it looks small.

## Parallel vs sequential (`all` mode)

Read at [step 2c](../SKILL.md#2c-group-for-parallelism--all-mode-only), after
the ordering above is settled. This decides which issues may be *implemented*
at the same time; the PR, CI watch and merge stay serialized regardless.

Two issues may share a batch only when **all** of these hold:

- Neither depends on the other, directly or transitively.
- Their likely file sets do not overlap. Estimate it before spawning by
  grepping for the symbols and paths each issue body names — a two-minute
  check that prevents a conflict pileup nobody wants to unpick later.
- Neither changes shared infrastructure — dependency manifests, lockfiles, CI
  config, migrations, schema — or a shared append-target file (changelog,
  decision log, generated index). Anything touching those is serialized,
  always, even when the code paths are disjoint.
- Neither is a `blocked: design` issue taken on deliberately. Step 2b's
  decision has to be settled and recorded before its implementation starts,
  and settling one while two other runs are in flight is how a design decision
  gets made in a hurry. An issue whose design was *already* decided and
  recorded — by step 2b earlier, or by a step 8b background agent — carries no
  block and is ordinary here; what this excludes is deciding a design while the
  batch runs, not implementing one that was decided.

Cap a batch at **3** concurrent worktrees. Beyond that the default branch
drifts faster than the batch's branches can rebase onto it, and the conflict
cost outgrows the wall-clock saving.

Fewer than 2 issues clear these checks → the batch is serial, and no worktree
is created. That is the common outcome on a small or tightly coupled backlog,
and it is not a failure — say so in one line and move on.

Whether the *repository* can support any of this is a separate gate:
[worktree-parallelism.md#viability-gate](worktree-parallelism.md#viability-gate).

After each merge inside a batch, the remaining branches are behind. Bring them
up to date in their own worktrees before their own PR is opened rather than
after a CI failure — a conflict there is evidence this grouping call was wrong
for that pair, and worth recording as such.

## Single mode: which issue

Among the shippable issues, pick by `priority-rubric.md` — unblocks-others
first, then leverage, then must-be-first ordering, then damage being taken
now. State the pick with its evidence lines before implementing.

## Deciding a held design

Two paths lead here, and they differ only in who decides and when:

- **inline — [step 2b](../SKILL.md#2b-decide-the-design-before-implementing)**,
  when the design blocks the very issue this run is about to implement (an
  explicit issue number or `--include-design`, never the default backlog scan).
  This session decides it, on the critical path, before step 3.
- **background — [step 8b](../SKILL.md#8b-unblock-held-designs-in-the-background)**,
  for every *other* design-blocked issue: the ones this run just filed and the
  ones already sitting in the backlog. An `opus` sub-agent decides each one
  while this session keeps shipping, and does 1–2 and 4 below itself.

Either way, the same four things happen in the same order:

1. Settle the approach — from the repo, its conventions, and the issue thread.
2. Record the decision as a comment on the issue itself — the next
   implementer must read this back, not re-derive it. The comment is the
   design of record; a decision that lives only in a run's transcript did not
   happen.
3. Record it in the run record (`--event design --field issue=<n> --field
   mode=<inline|background> --field verdict=<DECIDED|DEFERRED>`).
4. Clear the block: `python3 {SKILL_DIR}/scripts/apply_priority_labels.py
   --clear-design <n>` — after the comment posted, never before.

**Neither path invents a product or UX call** the repo and the issue thread do
not already answer. Inline, ask the user and do not implement past it; in the
background, the agent returns `DEFERRED` with the question, leaves the label
on, and the question reaches the user in the step 10 report.

Inline, continue at step 3 with the decided approach as part of the brief. In
the background, the cleared issue is simply ready — for this run at step 8c if
budget allows, otherwise for the next one. The tier label is untouched by any
of this — see priority-rubric.md's note that tier and design-readiness are
orthogonal.
