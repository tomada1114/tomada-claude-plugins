---
name: designing-architecture
description: >-
  Turn signed-off requirements and UX drafts into a new app's stable design documents
  before any issue is filed: an architecture overview (principles, how the app's domains
  map onto the template's layers, data, core flows, quality targets), one ADR per
  hard-to-reverse choice (design lock, app shape, sandbox and OS permissions,
  persistence, backend and sync, auth, key dependencies, locales, distribution) decided
  with the user through researched option rounds, and the Now/Next/Later roadmap —
  written into the homes the repository's own skills define
  (recording-architecture-decisions, designing-ui, steering-the-roadmap, updating-docs),
  with generic fallbacks. Use when designing the architecture of a new app, writing its
  first ADRs or design lock, filling the roadmap after a bootstrap, or as stage 7 of
  kicking-off-apps.
metadata:
  platforms: claude-code
---

# Designing Architecture

Issues are cheap and change weekly; the reasoning they depend on should not. This skill
writes down what the app will stay — its principles, its shape, and each choice that is
expensive to reverse — so every issue can cite a document instead of re-deciding it in
a thread. Without it, the first implementer settles persistence or app shape by
accident, and the template's ADR tree stays empty.

## Contract

**Input:** a repository whose `docs/product/requirements.md` is signed off and whose
`AGENTS.md` Product section is written; `docs/product/ux-flows.md`,
`docs/design/ux-guidelines.md`, and `docs/design/design-direction.md` when they exist.

**Output**, each in the home the repository's own skill names (read that skill first;
the fallback applies only when there is none):

| Document | Owner skill in the repository | Fallback |
|---|---|---|
| Architecture overview | `updating-docs` (which surface holds what) | `docs/architecture/overview.md` |
| ADRs + index row | `recording-architecture-decisions` | `docs/adr/NNNN-<title>.md` from [assets/adr-template.md](assets/adr-template.md) |
| Design lock | `designing-ui` (an ADR in some templates, the skill's own lock section in others) | an ADR |
| Roadmap | `steering-the-roadmap` | `docs/roadmap.md` with Now / Next / Later |

## 1. Inventory the decisions

Read the inputs, the template's `docs/architecture.md` and README "Design Philosophy",
and [references/decision-inventory.md](references/decision-inventory.md). List every
decision the requirements force and the template has not already made. Show the list to
the user before researching, so a decision they consider settled is not re-opened.

## 2. Decide, round by round

For each open decision, research the options from primary sources (context7 for
libraries; vendor docs for platforms) and present them through AskUserQuestion —
batched, at most 4 per call, 2–4 options each with what it costs, one marked
recommended when there is a real recommendation. The requirements and the non-goals are
the tie-breakers: say which line of them an option serves or violates. The design lock
is not re-decided here: transcribe `design-direction.md` into the lock format and ask
only about gaps the format has and the draft does not fill.

## 3. Write

- **ADRs**, one per decision, in the repository's template. Status **Accepted** with
  today's date when the user chose explicitly in this session — they are the owner the
  status legend means; **Proposed** for anything they deferred. Every external claim
  carries its URL and the date checked. Add each index row in the same change.
- **Overview**, using the skeleton in the reference: principles that each rule something
  out, the domain → layer map, data, core flows, measurable quality targets.
- **Roadmap**: Now = the MVP outcomes from the requirements, one to three, each with an
  observable "done when"; Next and Later from the deferred list. Leave the issue links
  empty — `planning-tickets` fills them when the issues exist.
- Match each document's length to its substance; no filler sections.

Work that changes code — applying tokens, removing the sample, flipping an entitlement —
is not done here. List it as follow-ups in the relevant ADR; it becomes an issue.

## 4. Verify and commit

Run the repository's documentation and harness checks (`just check-harness`, a docs
build, a link check — whatever its `AGENTS.md` lists for docs changes). Commit as
`docs: architecture overview, ADRs, and roadmap for <App>` and push when authorized.

## Report

The decisions made (ADR number, title, status), the ones deferred with what would settle
them, the documents written, and the follow-ups that must become issues.
