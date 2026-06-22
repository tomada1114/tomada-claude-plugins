---
name: refining-requirements
description: "Clarify ambiguous requirements through structured questioning and produce detailed, implementation-ready specifications. Acts as PdM to identify unclear points and resolve them via AskUserQuestion. Use PROACTIVELY when user mentions requirements, specs, PRD, refine, detail, clarify requirements, or asks to detail/refine app ideas. Also trigger when the user is about to jump into implementation with a vague or incomplete spec — even if they haven't explicitly asked to \"refine\" anything. Examples: <example>Context: User has rough idea user: 'Help me refine this app spec' assistant: 'I will use refining-requirements skill' <commentary>Triggered by spec refinement request</commentary></example> <example>Context: User jumps to implementation with vague spec user: 'Let me start building this feature' assistant: 'I will use refining-requirements skill first to clarify the requirements' <commentary>Proactively triggered before ambiguous implementation</commentary></example> <example>Context: Planning phase user: 'Let me detail the requirements' assistant: 'I will use refining-requirements skill' <commentary>Triggered by requirements detailing</commentary></example>"
---

# Requirements Refiner

Clarify ambiguous requirements through structured questioning and produce detailed, implementation-ready specifications.

**After this skill**: Use `designing-wireframes` for UI/UX visualization, then `planning-tickets` for GitHub Issues.

## Workflow

```
Phase 0: Gather Input (if no document provided)
    |
Phase 1: Understand & Classify
    |
Phase 2: Question Rounds (AskUserQuestion)
    |
Output: Detailed requirements document
```

## Phase 0: Gather Input (only if no document provided)

If the user hasn't provided a requirements document, gather the basics first via AskUserQuestion before doing anything else:

- What is the product/feature? (one-line description)
- Who is the target user and what pain does it solve?
- What platform? → Mobile app / Web app / API/Backend / CLI / Other
- Any constraints? (tech stack, MVP scope, deadline)

Then proceed to Phase 1 using those answers as the input.

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

Use `AskUserQuestion` tool to clarify ambiguities. Group related questions (max 4 per round). Ask only what's unclear — skip any category where the document is already specific.

### Question Design Principles

1. **Provide concrete options** — don't ask open-ended questions
2. **Include trade-offs** — explain what each option means
3. **Use descriptive headers** — short, scannable labels (max 12 chars)
4. **Batch related questions** — group by topic area

### Recommended Question Order

Ask in this order, skipping sections that don't apply to the platform:

**Round 1 — Core UI/UX** (mobile & web)
- Navigation structure (tab bar / sidebar / header nav)
- Primary action placement
- List/content display format

**Round 2 — Mobile UX** (mobile only)
- Primary action button placement → Bottom (Thumb-Zone) / Center / Within content
- Loading display → Simple spinner / Skeleton Screen / Shimmer
- Haptic Feedback → Implement / Don't implement
- Animation style → Platform standard / Custom

**Round 3 — Error Handling & Validation** (all platforms)
- Delete/destructive action UX → Immediate / Toast with Undo / Confirmation dialog
- Error display format → Toast / Alert / Inline message
- Form validation timing → Inline real-time / On blur / On submit
- Retry logic → Auto-retry / Manual retry button / No retry

**Round 4 — Accessibility** (mobile & web)
- WCAG compliance level → AA / Basic support / Not in MVP
- Screen reader support → Full / Basic labels only / Not in MVP

**Round 5 — Visual Design** (mobile & web)
- Dark mode → Light only (MVP) / Auto-follow system / Manual toggle
- Empty states → Simple text / Icon + text / With CTA
- Color scheme → Platform standard / Custom brand colors

**Round 6 — Business Logic** (all platforms)
- Free vs Pro feature gates and limits
- Default values for settings
- Edge case calculations (overflow, boundaries)

**Round 7 — API/Data** (API/backend & web apps with data)
- Authentication method
- Pagination strategy
- Error response format and HTTP status conventions

### After Questions: Update the Document

After gathering all answers, produce or update the requirements document:

1. **Detailed specifications** for each feature
2. **Edge case handling** for every boundary condition
3. **Default values** for all settings
4. **Validation rules** where defined

Use the [requirements-section.md](templates/requirements-section.md) template for individual feature sections. The full document should have this top-level structure:

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

## Best Practices

- Ask questions in rounds of 3-4 related topics
- Skip entire rounds if the platform makes them irrelevant (e.g., no UI questions for a pure API)
- Skip individual questions if the document already answers them clearly
- Use TodoWrite to track which phases are complete
- Suggest `designing-wireframes` after completion if UI screens need to be designed
