# Priority Research and Selection

## Table of Contents

- [The label is the answer, written down](#the-label-is-the-answer-written-down)
- [The research pass](#the-research-pass)
- [Overriding the suggested tier](#overriding-the-suggested-tier)
- [Deciding, and saying why](#deciding-and-saying-why)
- [`all` mode](#all-mode)

Read when the backlog has issues without a `priority:` label, or when a written
label looks wrong. On a fully labeled backlog the pick comes from
`issue_digest.py --select` and this file is not needed. Dependency mechanics
(what must land before what) live in `dependency-triage.md`.

**Priority here means impact on the rest of the backlog, not "the one I feel
like doing."** Concretely, in this order:

1. **Unblocks other work** — closing it makes other open issues implementable.
2. **Leverage / ripple effect** — it improves the ground every later issue
   stands on (CI, test harness, shared types, schema, config, security).
3. **Must-be-first ordering** — not a formal dependency, but doing it later
   means redoing work (schema before consumers, interface before
   implementations, lint/format rules before touching many files).
4. **Damage being taken right now** — broken build, crash, data loss,
   vulnerability, failing CI on main. These jump the queue regardless of score.

Everything else — nice-to-have features, docs polish, personal preference —
ranks below all four, however small it is.

## The label is the answer, written down

Those four axes get evaluated **once per issue** and the verdict is stored on
GitHub as a label, so the next run reads it instead of re-deriving it:

| Label | Means | Typical evidence |
|---|---|---|
| `priority: P0` | Ship now | Other open issues are blocked on it, or damage is being taken right now (red main, crash, data loss, vulnerability) |
| `priority: P1` | Do next | Leverage — CI, schema, shared types, test harness, config: the ground later issues stand on. Or a must-be-first ordering that causes rework if skipped |
| `priority: P2` | Normal | A real, self-contained change. Nothing waits on it |
| `priority: P3` | Defer | Nice-to-have, docs polish, cosmetics |

Existing vocabularies are read as equivalents, so a repo with its own convention
is never force-relabeled: `p0`/`critical`/`urgent`/`blocker` → P0,
`priority: high` → P1, `priority: medium` → P2, `priority: low`/`nice to have` →
P3. `apply_priority_labels.py` writes the canonical spelling and strips the
older one when it re-tiers an issue.

Tier and design-readiness are orthogonal: `blocked: design` says the approach
isn't settled, not how urgent the issue is once it is. Tier an issue even
while it carries `blocked: design`, so it ranks correctly the instant the
block is cleared — see `dependency-triage.md`'s "Deciding a held design".

Two rules keep the labels trustworthy:

- **A wrong label gets fixed, not worked around.** Ranking around a stale label
  in your head leaves the next run to make the same mistake. Re-tier it with
  `apply_priority_labels.py --set N=P1`.
- **Re-tier on new information, not on a hunch.** A merged blocker, a new
  dependency edge, or a `P2(~P0)` marker from the digest is new information;
  "this feels more urgent today" is not.

## The research pass

Run it on unlabeled issues, and on any issue whose label the digest flags as
too low (`P2(~P0)`). The script's suggested tier comes from labels,
cross-references, and keywords — enough to *rank*, not enough to *choose*.
Spend a short, bounded pass gathering evidence for the top 3–5 rows only:

| Question | How to check |
|---|---|
| Does it really unblock the issues the table claims? | read both ends' comments; a bare `#12` mention is not a dependency |
| Is the "damage" still real? | is the failure reproducible now — check whether CI on `<default>` is actually red, or run the project's test command |
| Does it touch shared ground? | grep the paths/symbols the body names; a change under `src/core`, `schema/`, `.github/workflows/` has ripple by construction |
| Is it actually specified? | Does the body state a behavior, a file, or an acceptance condition? |
| Has someone already started? | `HAS-OPEN-PR` flag, plus recent comments claiming the work |
| Is it stale for a reason? | An issue untouched for a year with no reaction may be dead; check comments before reviving it |

Stop the research when the top candidate is clearly ahead. Do not read every
open issue in full — that is what the score exists to avoid.

## Overriding the suggested tier

The heuristic is deliberately crude — it suggests a tier for the whole backlog
for free so that judgment only has to correct the few it gets wrong. Write the
correction with `apply_priority_labels.py --set N=<tier>`; the cases that
recur:

- **Keyword false positive** — the body says "security" in passing but the
  change is a docs tweak. Demote it, usually to P2/P3.
- **Unblock edge is fake** — `#12` was mentioned as context, not as a
  prerequisite. Demote from P0; the ranking usually changes.
- **Umbrella / epic** — an issue whose body is a checklist of other issues is
  not implementable. Its tier is not wrong, so leave it: never select it, ship
  its highest-priority child instead. Same for an issue that is really five
  issues — report it as `NEEDS-CLARIFICATION`, do not demote it to hide it.
  Tiers answer "how much does this matter", not "can I ship it"; readiness is
  the other axis, and it lives in the dependency-triage reference.
- **Cheap unblock beats expensive damage** — when the top two are close, prefer
  the one that is smaller and touches fewer files. It lands sooner and shortens
  the window in which other branches drift.

## Deciding, and saying why

State the pick in this shape before implementing anything — the evidence lines
are what make the choice auditable, and they are cheap once the research pass
is done:

```
Selected: #12 "CI fails intermittently on macOS runners"  (P0, READY)
Why first:
  - unblocks #14, #15 — both add tests that cannot be trusted while CI is flaky
  - leverage: touches .github/workflows/ci.yml, every future PR benefits
  - damage now: main has been red 3 of the last 5 runs
Runner-up: #9 (P1) — real, but self-contained; nothing waits on it
Deferred: #7 umbrella (ship its children), #21 NEEDS-CLARIFICATION (no acceptance condition)
Labels written: #12 P0, #9 P1, #21 P2 (+6 backfilled by score)
```

Proceed on that pick without asking. Ask the user directly, in plain
conversation, and wait for their reply, only when the top two are genuinely
tied on all four axes and cost a full implement/PR/CI cycle to get wrong, or
when the highest-priority issue needs a product decision before it can be
implemented. A wrong-but-clearly-argued pick is recoverable; a stalled run is
not.

## `all` mode

The same rubric produces the *order*, not just the winner. Sort by dependency
level first (an issue cannot precede what it depends on), then by tier within a
level, then by score within a tier — which is exactly what
`issue_digest.py --select N` prints. Re-rank after each merge with that same
call: merging a blocker moves its dependents from BLOCKED to READY, and a
freshly READY P0 may outrank whatever was next in the original plan. Because the
tiers are labels, the re-rank costs one script call, not another research pass.
