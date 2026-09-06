---
name: refining-requirements
description: "Clarify ambiguous requirements through structured questioning and produce detailed, implementation-ready specifications. Acts as PdM to identify unclear points and resolve them through structured questioning. Use PROACTIVELY when user mentions requirements, specs, PRD, refine, detail, clarify requirements, or asks to detail/refine app ideas. Also trigger when the user is about to jump into implementation with a vague or incomplete spec — even if they haven't explicitly asked to \"refine\" anything. Examples: <example>Context: User has rough idea user: 'Help me refine this app spec' assistant: 'I will use refining-requirements skill' <commentary>spec refinement</commentary></example> <example>Context: User jumps to implementation with vague spec user: 'Let me start building this feature' assistant: 'I will use refining-requirements first' <commentary>pre-implementation</commentary></example>"
metadata:
  platforms: claude-code, codex
---

# Requirements Refiner

Clarify ambiguous requirements through structured questioning and produce detailed, implementation-ready specifications.

**After this skill**: Use `designing-wireframes` for UI/UX visualization, then `planning-tickets` for GitHub Issues. See [references/platform-notes.md](references/platform-notes.md).

## Phase 0: Gather Input (only if no document provided)

If the user hasn't provided a requirements document, gather the basics first — present 2-4 options with tradeoffs and a recommendation, wait for the reply — then proceed to Phase 1 using the answers as input:

- What is the product/feature? (one-line description)
- Who is the target user and what pain does it solve?
- What platform? → Mobile app / Web app / API/Backend / CLI / Other
- Any constraints? (tech stack, MVP scope, deadline)

## Phase 1: Understand & Classify

1. Read the requirements document (or answers from Phase 0)
2. Identify the core value proposition and target user
3. **Determine the platform type** — this controls which checks are required in Phase 2:
   - **Mobile app** → all sections apply
   - **Web app** → skip Mobile UX (Thumb-Zone, Haptic), adapt Accessibility to keyboard/focus
   - **API/Backend** → skip UI sections entirely; focus on Business Logic, Error Handling, Data Contracts
   - **CLI** → skip UI sections; focus on command interface, error output, exit codes
4. Note what's already clear — don't ask about things the document already answers

## Phase 2: Question Rounds

Clarify ambiguities through batched questions — using the same options-with-recommendation format as Phase 0 (max 4 questions per round). Ask only what's unclear — skip any category where the document is already specific.

### Question Design Principles

1. **Use descriptive headers** — short, scannable labels (max 12 chars)
2. **Batch related questions** — group by topic area

### Recommended Question Order

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

Save the document as `requirements.md` in the project root, or update the existing file if one already exists.

## Platform notes

See [references/platform-notes.md](references/platform-notes.md) for details.
