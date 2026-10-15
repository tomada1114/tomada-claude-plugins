---
name: designing-architecture
description: >-
  Turn signed-off requirements and UX drafts into a new app's stable design documents
  before any issue is filed: an architecture overview (principles, how the app's domains
  map onto the template's layers, data, core flows, quality targets) that states each
  hard-to-reverse choice (design lock, app shape, sandbox and OS permissions,
  persistence, backend and sync, auth, key dependencies, locales, distribution) in the
  present tense with its reasoning — decided with the user through researched option
  rounds, never written as ADRs — and the Now/Next/Later roadmap, written into the
  homes the repository's own skills define (designing-ui, steering-the-roadmap,
  updating-docs), with generic fallbacks; a template's leftover ADR machinery is
  removed. Use when designing the architecture of a new app, writing its design lock,
  filling the roadmap after a bootstrap, or as stage 7 of kicking-off-apps.
metadata:
  platforms: claude-code, codex
---

# Designing Architecture

Issues are cheap and change weekly; the reasoning they depend on should not. This skill
writes down what the app will stay — its principles, its shape, and each choice that is
expensive to reverse — so every issue can cite a document instead of re-deciding it in
a thread. Without it, the first implementer settles persistence or app shape by
accident.

**No ADRs** — the owner's standing rule. A decision is written as the present state of
the design documents: what the app does and why, in the present tense. Git holds what
it used to say; there are no numbered records, statuses, dates, or index. Changing a
decision means rewriting its sentences in place, in the same change as the code. Why: a
record per decision turns every later change of mind into a ceremony, and the owner
wants features easy to change.

## Contract

**Input:** a repository whose `docs/product/requirements.md` is signed off and whose
`AGENTS.md` Product section is written; `docs/product/ux-flows.md`,
`docs/design/ux-guidelines.md`, and `docs/design/design-direction.md` when they exist.

**Output**, each in the home the repository's own skill names (read that skill first;
the fallback applies only when there is none):

| Document | Owner skill in the repository | Fallback |
|---|---|---|
| Architecture overview, holding every decision | `updating-docs` (which surface holds what) | `docs/architecture/overview.md` |
| Design lock | `designing-ui` (the present-state lock section it names) | a "Design lock" section in the overview |
| Roadmap | `steering-the-roadmap` | `docs/roadmap.md` with Now / Next / Later |

A repository whose template still ships ADR machinery — a
`recording-architecture-decisions` skill, an ADR directory or index, `AGENTS.md` rules
that require an ADR, a design lock "written as an ADR" — loses it in this stage's
change: delete the skill (with its mirror and its Skills-table row), the ADR template
and index, and point every reference at the present-state documents, as
`tomada1114/rust-template#207` did. Keep the list of hard-to-reverse changes and every
sign-off rule; only where the reasoning is written changes.

## 1. Inventory the decisions

Read the inputs, the template's `docs/architecture.md` and README "Design Philosophy",
and [references/decision-inventory.md](references/decision-inventory.md). List every
decision the requirements force and the template has not already made. Show the list to
the user before researching, so a decision they consider settled is not re-opened.

## 2. Decide, round by round

For each open decision, research the options from primary sources (a library
documentation lookup tool where the runtime has one, otherwise the library's official
docs; vendor docs for platforms). If the runtime cannot reach the web, say so and mark
each claim you could not check as unchecked instead of dating it. Then present the
decisions in batched rounds — at most 4 questions per round, 2–4 options each with what
it costs, one marked recommended when there is a real recommendation — and wait for the
answers before the next round. The requirements and the non-goals are the
tie-breakers: say which line of them an option serves or violates. The design lock
is not re-decided here: transcribe `design-direction.md` into the lock format and ask
only about gaps the format has and the draft does not fill.

## 3. Write

- **Decisions**, each in the home the repository gives its subject — the overview's
  Decisions section, `AGENTS.md`'s Architecture section, or the owning skill — as
  present-tense text: what the app does and why (what it protects, and where it matters
  the alternative it rules out and why). Write one as settled only when the user chose
  it explicitly in this session; a choice they deferred, or one resting on a claim
  marked unchecked, goes to the overview's Open list with what would settle it. Every
  external claim carries its URL and the date checked, or is marked unchecked.
- **Overview**, using the skeleton in the reference: principles that each rule something
  out, the domain → layer map, data, core flows, measurable quality targets.
- **Roadmap**: Now = the MVP outcomes from the requirements, one to three, each with an
  observable "done when"; Next and Later from the deferred list. Leave the issue links
  empty — `planning-tickets` fills them when the issues exist.
- Match each document's length to its substance; no filler sections.

Work that changes code — applying tokens, removing the sample, flipping an entitlement —
is not done here. List it in the overview's Follow-ups; each becomes an issue.

## 4. Verify and commit

Run the repository's documentation and harness checks (`just check-harness`, a docs
build, a link check — whatever its `AGENTS.md` / `CLAUDE.md` lists for docs changes).
Commit as `docs: architecture overview and roadmap for <App>` and push when
authorized.

## Report

The decisions made (each with where it is written), the ones deferred with what would
settle them, the documents written, any ADR machinery removed, and the follow-ups that
must become issues.

## Platform notes

Host-specific tool mapping and degradations: [references/platform-notes.md](references/platform-notes.md).
