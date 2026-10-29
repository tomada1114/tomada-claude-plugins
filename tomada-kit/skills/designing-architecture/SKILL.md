---
name: designing-architecture
description: >-
  Decide a new app's hard-to-reverse design choices from its signed-off requirements and
  UX drafts before any issue is filed — design lock, app shape, sandbox and OS
  permissions, persistence, backend and sync, auth, key dependencies, locales,
  distribution — through researched option rounds with the user, and write each decision
  in the present tense, with its reasoning, into the repository skill that owns the
  subject (its SKILL.md or references/), or AGENTS.md's Architecture section for a layer
  rule. Creates no architecture overview, roadmap, decision record, or ADR; a subject
  with no owning skill gets a new skill for that subject. Use when designing the
  architecture of a new app, writing its design lock, settling decisions after a
  bootstrap, or as stage 7 of kicking-off-apps.
metadata:
  platforms: claude-code, codex
---

# Designing Architecture

Issues are cheap and change weekly; the reasoning they depend on should not. This skill
settles what the app will stay — its shape and each choice that is expensive to
reverse — so every issue can cite a skill instead of re-deciding it in a thread. Without
it, the first implementer settles persistence or app shape by accident.

**Design lives in the skills — the owner's standing rule.** A decision is written once,
in the skill an agent loads when it touches that subject: what the app does and why, in
the present tense. A document no skill points an agent at is never read when it
matters, and a second copy drifts. So this skill writes no architecture overview, no
roadmap, and no decision record (ADR): git holds what a decision used to say, and
changing a decision means rewriting its sentences in the owning skill, in the same
change as the code. Direction — what comes next — is the Product section and the open
issues, not a document.

## Contract

**Input:** a repository whose `docs/product/requirements.md` is signed off and whose
`AGENTS.md` Product section is written; `docs/product/ux-flows.md`,
`docs/design/ux-guidelines.md`, and `docs/design/design-direction.md` when they exist.

**Output:** each decision written into its home, found in this order:

1. The repository skill whose **Owns** line covers the subject (read every skill's
   frontmatter and Owns / Does-not-own lines first). A short rule goes in its body; a
   longer one — a schema, a flow, a dependency verdict — goes in a `references/*.md`
   the body links to. The design lock goes where the repository's `designing-ui` (or
   equivalent) says.
2. `AGENTS.md`'s Architecture section (or an area's `AGENTS.md`) for a rule about the
   layers themselves — what may import what — and its contract table, when it has one.
3. No owner: a new skill for that one subject (for example `persisting-data`), written
   to the repository's `authoring-skills` conventions and added to its Skills table.
   Never a general "architecture" skill or a standalone document.

A template that still ships an architecture document, a roadmap, or ADR machinery — a
`docs/architecture*` tree, a roadmap page or skill, a `recording-architecture-decisions`
skill, an ADR index — loses it in this stage's change: move each still-true reason to
its owning skill, delete the rest (skill, mirror, Skills-table row), and point every
reference at the skill. Keep the list of hard-to-reverse changes and every sign-off
rule; only where the reasoning is written changes.

## 1. Inventory the decisions

Read the inputs, the repository's skills, its `AGENTS.md`, and
[references/decision-inventory.md](references/decision-inventory.md). List every
decision the requirements force and the template has not already made, each with the
skill it will be written into. Show the list to the user before researching, so a
decision they consider settled is not re-opened.

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

- Write each decision into its home (Contract) as present-tense text: what the app
  does and why — what it protects and, where it matters, the alternative it rules out.
  Replace the template's sentences on that subject rather than adding beside them.
- Write one as settled only when the user chose it explicitly in this session. A choice
  they deferred, or one resting on a claim marked unchecked, is not written as settled:
  list it in the report with what would settle it, so it becomes an issue.
- Every external claim carries its URL and the date checked, or is marked unchecked.
- Match length to substance; no filler sections, no summary page that repeats the skills.

Work that changes code — applying tokens, removing the sample, flipping an entitlement —
is not done here. List it in the report; each becomes an issue in the next stage.

## 4. Verify and commit

Run the repository's skill and harness checks (the skills mirror sync, `just
check-harness`, or whatever its `AGENTS.md` / `CLAUDE.md` lists for skill and docs
changes). Commit as `docs(skills): record <App>'s design decisions` and push when
authorized.

## Report

The decisions made, each with the skill file it is written in; the ones deferred with
what would settle them; any skill created; any architecture document, roadmap, or ADR
machinery removed; and the follow-ups that must become issues.

## Platform notes

Host-specific tool mapping and degradations: [references/platform-notes.md](references/platform-notes.md).
