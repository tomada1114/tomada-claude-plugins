# Priority Research and Selection

Read before choosing what to ship. `issue_digest.py` prints a heuristic
`## Priority ranking` table; this file is how that table becomes a defensible
pick. Dependency mechanics (what may run in parallel, what must be serialized)
live in [dependency-triage.md](dependency-triage.md).

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

## The research pass

The score comes from labels, cross-references, and keywords. That is enough to
*rank*, not enough to *choose*. Before committing to a candidate, spend a short,
bounded pass gathering evidence for the top 3–5 rows only:

| Question | How to check |
|---|---|
| Does it really unblock the issues the table claims? | `gh issue view <n> --comments` on both ends; a bare `#12` mention is not a dependency |
| Is the "damage" still real? | Is the failure reproducible now — `gh run list --branch <default> --limit 5` for red CI, or run the project's test command |
| Does it touch shared ground? | grep the paths/symbols the body names; a change under `src/core`, `schema/`, `.github/workflows/` has ripple by construction |
| Is it actually specified? | Does the body state a behavior, a file, or an acceptance condition? |
| Has someone already started? | `HAS-OPEN-PR` flag, plus recent comments claiming the work |
| Is it stale for a reason? | An issue untouched for a year with no reaction may be dead; check comments before reviving it |

Stop the research when the top candidate is clearly ahead. Do not read every
open issue in full — that is what the score exists to avoid.

## Adjusting the score by hand

The heuristic is deliberately crude. Override it when:

- **Keyword false positive** — the body says "security" in passing but the
  change is a docs tweak. Drop the leverage points.
- **Unblock edge is fake** — `#12` was mentioned as context, not as a
  prerequisite. Drop the unblock points; the ranking usually changes.
- **Umbrella / epic** — an issue whose body is a checklist of other issues
  scores high (it references many) but is not implementable. Never select it;
  select its highest-priority child instead.
- **Huge unspecified scope** — a high-score issue that is really five issues is
  reported as `NEEDS-CLARIFICATION`, not shipped as a mega-PR.
- **Cheap unblock beats expensive damage** — when the top two are close, prefer
  the one that is smaller and touches fewer files. It lands sooner and shortens
  the window in which other branches drift.

## Deciding, and saying why

State the pick in this shape before implementing anything — the evidence lines
are what make the choice auditable, and they are cheap once the research pass
is done:

```
Selected: #12 "CI fails intermittently on macOS runners"  (score 17, READY)
Why first:
  - unblocks #14, #15 — both add tests that cannot be trusted while CI is flaky
  - leverage: touches .github/workflows/ci.yml, every future PR benefits
  - damage now: main has been red 3 of the last 5 runs
Runner-up: #9 (score 11) — real, but self-contained; nothing waits on it
Deferred: #7 umbrella (ship its children), #21 NEEDS-CLARIFICATION (no acceptance condition)
```

Proceed on that pick without asking. Ask via `AskUserQuestion` only when the
top two are genuinely tied on all four axes and cost a full implement/PR/CI
cycle to get wrong, or when the highest-priority issue needs a product decision
before it can be implemented. A wrong-but-clearly-argued pick is recoverable;
a stalled run is not.

## `all` mode

The same rubric produces the *order*, not just the winner. Sort by dependency
level first (an issue cannot precede what it depends on), then by priority
score within a level. Re-rank after each merge: merging a blocker moves its
dependents from BLOCKED to READY, and a freshly READY high-score issue may
outrank whatever was next in the original plan.
