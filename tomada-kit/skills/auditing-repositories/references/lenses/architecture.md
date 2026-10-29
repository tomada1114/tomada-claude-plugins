# Lens: architecture and design (`AR`)

How the code is divided, which way dependencies run, and whether the patterns in use
earn their keep. The most valuable findings here are **drift**: the repository states a
design (AGENTS.md's Architecture section, a skill's "Owns" line and the design it
records) and the code does something else. Decide which side is wrong before proposing
anything. Sometimes the code is right and the skill is stale.

## Survey (facts to collect, no judgment)

- **S-AR1 Declared design.** Every layering or ownership rule the repository states,
  quoted with `path:line`: layer names, allowed import directions, where business rules
  live, what a route, screen or adapter may do.
- **S-AR2 Module map.** Each package or feature directory in scope with a one-line role
  taken from its docstring, README or declared design, plus its line count.
- **S-AR3 Cross-boundary imports.** Imports that run against a declared direction, such
  as the core importing an adapter, a framework or the UI. List each one with `path:line`
  and the import line. Where no direction is declared, list imports between top-level
  packages as a matrix (from → to, count).
- **S-AR4 Cross-cutting concerns.** For configuration loading, logging, error
  translation, validation, persistence access, time and randomness, and external calls,
  list every place that does the work, with `path:line`.
- **S-AR5 Duplicated concepts.** The same domain concept defined in more than one place:
  a type, enum, constant set or schema, including front end and back end copies.
- **S-AR6 Large units.** Source files over 400 lines and functions or classes over 80
  lines, each with its top-level symbols and the file's churn count from the inventory.

## Analysis (judge each item; "keep, because …" is a valid result)

- **AR1 Declared vs actual.** For each S-AR1 rule, say whether the code follows it. A
  violation needs one of two proposals: move the code, or fix the rule when it no
  longer serves. Say which, and why.
- **AR2 Dependency direction.** Domain decisions inside routes, screens, adapters or
  scripts. Framework types leaking into the core. Cycles.
- **AR3 Cohesion and boundaries.** Units with more than one reason to change. Size ×
  churn from S-AR6 points at them. Ask whether feature-first or layer-first
  organization fits how this code actually changes.
- **AR4 Abstraction level.** A missing seam: code that cannot be tested without a real
  clock, network or database. Speculative indirection: an interface with one
  implementation and no test double, or a wrapper that only forwards. Both are debt;
  name which.
- **AR5 Cross-cutting consistency.** A concern from S-AR4 done in more than one way.
  Propose the single home for it and the order to migrate call sites.
- **AR6 State and sources of truth.** Duplicated concepts from S-AR5. Hand-maintained
  copies of a schema that could be generated or shared. State owned by two places.
- **AR7 Pattern fit.** A pattern heavier than the problem, such as a factory for one
  product or an event bus with one subscriber. A known pattern that would remove
  repeated branching: a table, a strategy, a state machine.
- **AR8 Fitness for what comes next.** Read the open issues — tracking parents and the
  highest priority tiers — and the Product section. Say whether the current structure
  absorbs that planned work or will need the change anyway. Prefer findings that
  unblock it.

## What a good proposal looks like here

Name the target shape concretely: the modules and the functions that move, and the
interface that appears, with its name. Give the order of moves that keeps every step
green. A structural change that alters no behavior starts from characterization tests
that pin today's behavior. For a large redesign, propose a tracking issue with
independent steps rather than one big issue.
