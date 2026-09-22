---
name: refining-requirements
description: >-
  Clarify ambiguous requirements through structured questioning and produce detailed,
  implementation-ready specifications. Acts as PdM to identify unclear points and
  resolve them through structured questioning. Use when asked to refine or detail a
  spec, PRD, or app idea. Also trigger when the user is about to start implementing from
  a vague or incomplete spec, even without an explicit request to refine.
metadata:
  platforms: claude-code, codex
---

# Requirements Refiner

**After this skill**: Use `designing-wireframes` for UI/UX visualization, then `planning-tickets` for GitHub Issues. Codex differences: [references/platform-notes.md](references/platform-notes.md).

## Phase 0: Gather Input (only if no document provided)

If the user hasn't provided a requirements document, gather the basics first — present 2-4 options with tradeoffs and a recommendation, wait for the reply — then proceed to Phase 1 using the answers as input:

- What is the product/feature? (one-line description)
- Who is the target user and what pain does it solve?
- What platform? → Mobile app / Web app / API/Backend / CLI / Other
- Any constraints? (tech stack, MVP scope, deadline)

## Phase 1: Classify the platform

The platform type controls which question rounds apply in Phase 2:

- **Mobile app** → all rounds apply
- **Web app** → skip Mobile UX (Thumb-Zone, Haptic); adapt Accessibility to keyboard/focus
- **API/Backend** → skip UI rounds entirely; focus on Business Logic, Error Handling, Data Contracts
- **CLI** → skip UI rounds; focus on command interface, error output, exit codes

## Phase 2: Question Rounds

Clarify ambiguities in batched rounds of at most 4 questions, grouped by topic, in the same options-with-recommendation format as Phase 0. Ask only what the document leaves unclear — skip any category where it is already specific.

Ask in this order, skipping rounds that don't apply: Core UI/UX, Mobile UX, Error Handling & Validation, Accessibility, Visual Design, Business Logic, API/Data. Question bank: [references/question-bank.md](references/question-bank.md)

### After Questions: Update the Document

Produce or update the requirements document with detailed specs, edge-case handling, default values, and validation rules for each feature, using the [requirements-section.md](templates/requirements-section.md) template. The full document uses this top-level structure:

```markdown
# [Product/Feature Name] — Requirements

## 1. Overview
- Product summary
- Target user and pain point
- Platform and tech stack

## 2. Features
(one section per feature, using requirements-section.md template)

## 3. Cross-Cutting Concerns
- Error handling strategy
- Accessibility requirements
- Loading & feedback patterns
- Form validation rules

## 4. Out of Scope (MVP)
- Deferred features with rationale
```

Section 3 records the decisions from the Error Handling, Accessibility, and Visual Design rounds; `designing-wireframes` later expands them into full specification sections.

Save the document as `requirements.md` in the project root, or update the existing file if one already exists.
