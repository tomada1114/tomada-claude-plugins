---
name: refining-requirements
description: >-
  Turn a vague app idea or an incomplete spec into a signed-off, implementation-ready
  requirements document through repeated rounds of structured questioning, acting as
  the PdM while the user plays the client. Each round also scrutinizes the draft —
  contradictions, missing flows, unstated edge cases, MVP bloat, conflicts with the
  template or stack — and turns what it finds into the next questions, until the user
  signs off. Produces features with concrete values, an explicit MVP / Later /
  Non-goals split, and cross-cutting rules. Use when asked to refine or detail a spec,
  PRD, or app idea, when someone describes an app they want built, when implementation
  is about to start from a vague or incomplete spec, or as stage 1 of kicking-off-apps.
argument-hint: "[idea or path to spec] [--out path]"
metadata:
  platforms: claude-code, codex
---

# Refining Requirements

**Next:** `designing-wireframes` for screens and flows, `ui-ux-designing` for app-wide UX
policy, then `planning-tickets` for issues — or all of it through `kicking-off-apps`.

## Modes and output

- **Hearing** — the input is an idea in the user's words ("an app that…"). Build the
  document from nothing; the user answers as a client who knows the problem but not
  the spec.
- **Refinement** — the input is an existing document. Ask only what it leaves unclear.

Write to the path the caller names (`--out`, or the path `kicking-off-apps` passes);
otherwise update an existing requirements document in place; otherwise create
`docs/product/requirements.md`. Structure: [templates/requirements-document.md](templates/requirements-document.md),
one section per feature from [templates/requirements-section.md](templates/requirements-section.md).

## Before the first question

Read what already constrains the answer: the repository's or template's `AGENTS.md` /
`CLAUDE.md` and `README.md`. A template fixes the platform and stack, and its sample
shows what the app is built from — do not ask about anything they settle, and keep the
constraints in mind as scrutiny material ("this feature needs a server; the template is
local-only").

Classify the platform — desktop (macOS), web, mobile, API/backend, CLI — because it
decides which question rounds apply ([references/question-bank.md](references/question-bank.md)).

## The loop

Repeat until the user signs off:

1. **Ask** one batch — at most 4 questions, grouped by topic, 2–4 options each with its
   trade-off, one marked recommended when there is a real recommendation — and wait
   for the user's answers before updating the document. Hearing mode starts with the
   Product and scope round; open questions are fine there when options would put
   words in the client's mouth.
2. **Update the document** with the answers: concrete values, defaults, limits,
   validation rules, edge cases. Record each decision in the Decision log with the
   rejected alternative.
3. **Scrutinize the draft** against [references/scrutiny-checklist.md](references/scrutiny-checklist.md).
   Every finding becomes either a question for the next batch or an explicit entry
   under Open questions — never a silent assumption.
4. **Show the delta**: what changed, what the scrutiny found, what the next batch will
   ask. Ask the user whether to continue or sign off once the checklist finds nothing
   that changes scope or behavior.

Scope is part of every round, not the last one. Each MVP feature must trace to the core
interaction; anything that does not is proposed for Later. Non-goals are written as
deliberately as goals — what the app will not do even where it would be easy — because
the next reader will treat an unlisted non-goal as a feature.

When a UX or visual stage follows (the kickoff runs one), skip the question rounds the
question bank marks as belonging to it; this document records product behavior, not
styling.

## Sign-off

Sign-off is the user saying so, not the loop running out of questions. Set the
document's status line to `Signed off YYYY-MM-DD`, and leave any remaining Open
questions with what would settle them.

## Platform notes

Host tool mapping and degradation paths: [references/platform-notes.md](references/platform-notes.md).
