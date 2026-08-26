# Dependency and Readiness Triage

## Table of Contents

- [Readiness gate](#readiness-gate)
- [Dependency edges the regex misses](#dependency-edges-the-regex-misses)
- [Ordering rules](#ordering-rules)
- [Parallel vs sequential (all mode)](#parallel-vs-sequential-all-mode)
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
   design block just needs a decision, which this run can make.
5. Its scope is one coherent change. An issue that is really five issues gets
   reported back for splitting, not implemented as a mega-PR.

An issue that fails 1 or 5 is **not** implemented silently. Report it as
`NEEDS-CLARIFICATION` with the specific missing information, and move on to the
next candidate.

## Dependency edges the regex misses

`issue_digest.py` catches explicit `#N` references and common EN/JA dependency
phrasings. These edges only appear on reading:

- **Same-file collision** — two issues that both rewrite `foo.py` are not
  formally dependent, but must not run in parallel worktrees. Serialize them.
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

## Parallel vs sequential (all mode)

Two issues may run in parallel worktrees only when **all** hold:

- Neither depends on the other, directly or transitively.
- Their likely file sets do not overlap. Estimate this before spawning by
  grepping for the symbols/paths named in each issue body — a two-minute check
  that prevents a merge conflict pileup.
- Neither changes shared infrastructure (dependency manifests, CI config,
  lockfiles, migrations, schema) or a shared append-target file (changelog,
  decision log). Anything touching those is serialized, always.

Cap parallelism at 3 concurrent worktrees. Beyond that, main drifts faster than
branches can rebase and the conflict cost exceeds the wall-clock saving.

After each merge in a parallel batch, the remaining in-flight branches are
behind. Rebase them onto the updated default branch before their CI run rather
than after a failure.

## Single mode: which issue

Among the shippable issues, pick by `priority-rubric.md` — unblocks-others
first, then leverage, then must-be-first ordering, then damage being taken
now. State the pick with its evidence lines before implementing.

## Deciding a held design

Read at step 2b, only when the picked issue carries `blocked: design` (or a
recognized equivalent) and was taken on deliberately — an explicit issue
number or `--include-design`, never the default backlog scan.

1. Settle the approach. A product/UX call you cannot make from the repo and
   its issue thread — ask the user; do not guess and implement anyway.
2. Record the decision as a comment on the issue itself — the next run must
   read this back, not re-derive it.
3. Record it in the run record (`--event design --field issue=<n>`).
4. Clear the block: `python3 {SKILL_DIR}/scripts/apply_priority_labels.py
   --clear-design <n>`.

Then continue at step 3 with the decided approach as part of the brief. The
tier label is untouched by any of this — see priority-rubric.md's note that
tier and design-readiness are orthogonal.
