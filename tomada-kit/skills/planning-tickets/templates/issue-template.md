# Issue body template

The skeleton for `gh issue create --body-file`. A repository's own conventions
(`triaging-issues`, issue forms, a `shipping-issues` ship contract) are added to it and
win where they differ. Domain-specific requirement groups (UI, API, schema) extend
Functional Requirements as extra tables of the same shape — no separate template.

## Fallback title prefixes

Only when the repository has no title convention of its own.

| Prefix | Meaning |
|---|---|
| `[Foundation]` | Must land before the parallel work |
| `[Parallel]` | Independent; can run alongside others |
| `[Parallel/worktree:<name>]` | Independent, with a suggested worktree branch |
| `[Depends]` | Has open dependencies |
| `[Sequential]` | Must follow a specific order |

## Skeleton

````markdown
## User Story

**As a** [user type] **I want** [goal] **so that** [benefit].

## Background & Context

Where this sits in the whole, in 2–3 lines, and the document sections the implementer
reads (e.g. `docs/product/requirements.md §3.1`, ADR-0003).

| Item | Value | Source |
|------|-------|--------|
| [every concrete value the work needs] | [real value] | [doc §x.x] |

## Functional Requirements (EARS)

| ID | Requirement | Verification |
|----|-------------|--------------|
| REQ-001 | **When** [trigger], the system shall [action]. | [test or command] |
| REQ-002 | **While** [state], the system shall [behavior]. | [test or command] |
| REQ-003 | **If** [error condition], **then** the system shall [recovery]. | [test or command] |

## Boundary Conditions

| Condition | EARS requirement |
|-----------|------------------|
| Minimum / maximum / empty / over-limit / null | **When** [boundary], the system shall [behavior]. |

## Concrete Examples

At least three — happy path, boundary, error — all with real values.

```
Trigger:      [concrete input]
Pre-state:    [real values]
Post-state:   [real values]
Verification: [how to check]
```

## Acceptance Criteria

- [ ] REQ-001: [checkable condition with real values]
- [ ] Boundary: [boundary behavior verified]
- [ ] [the repository's check command] passes

## Not In Scope

- Not implementing: [excluded work] → #N owns it
- Not handling: [edge case] → [why it waits]

## Dependencies

One per line, exactly `Depends on #N` / `Blocks #N` / `Part of #N` (or the repository's
own spelling) — automation parses these. `None` when there are none.

- Depends on #N — [what it needs from it: a type, a function, a component]
- Blocks #N — [what waits on this]
````

## Variants

- **Foundation:** Functional Requirements become specification tables of the types,
  constants, or schema (name, fields, constraints, values with source); usage code may
  replace Concrete Examples. `Blocks #N` is backfilled after all issues exist.
- **Integration:** Background describes the flow being connected (A → transform → B);
  Depends on lists the merged stream issues; Not In Scope includes "no change to the
  internals of the connected components".
- **Tracking parent:** only a goal line, a "done when", and a checklist `- [ ] #N` of
  its sub-issues; the repository's `tracking` label (or the fallback one) and no tier.
