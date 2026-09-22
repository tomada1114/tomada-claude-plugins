---
name: designing-wireframes
description: >-
  Create ASCII wireframes, user flow diagrams, and cross-cutting specifications for
  UI/UX visualization. Use when asked for a wireframe, screen layout, screen design, or
  user flow, or to visualize screens before implementation.
metadata:
  platforms: claude-code, codex
---

# Wireframe Designer

**Before this skill**: Use `refining-requirements` to clarify ambiguous requirements.
**After this skill**: Use `planning-tickets` for GitHub Issues creation.

Input is a detailed requirements document; output is that same document with wireframes, user flows, and cross-cutting sections added. Edit it in place, section by section, rather than creating a separate file.

## Step 1: Create ASCII Wireframes

Create text wireframes (ASCII or box-drawing characters) for each screen in the requirements. Primary actions belong in the reachable bottom zone; destructive or rare actions (settings) go higher up.

[templates/wireframe-patterns.md](templates/wireframe-patterns.md) holds the thumb-zone diagram and example layouts: screen structures, components (progress bars, button grids, lists, settings), modals and overlays, onboarding, toasts, swipe actions, empty states.

## Step 2: Document User Flows

Document user flows with numbered steps:

```
1. User taps button
2. Bottom Sheet appears with options
3. User selects option
4. Record saved -> Toast notification
5. UI updates with new data
```

### Flow Diagram Format

```
[Start] -> [Screen A] -> [Action] -> [Screen B]
                |
                v
           [Error] -> [Retry]
```

## Step 3: Add Cross-Cutting Sections (for mobile apps)

Add all four sections from [templates/cross-cutting-sections.md](templates/cross-cutting-sections.md) — error handling, accessibility, loading and feedback, form validation — filling in the app's real messages, timings, and field rules from the decisions made in `refining-requirements`.

## Notes

- Annotate wireframes with arrows or comments where the flow isn't obvious from the layout, and cover empty and error states, not only the happy path.
- Where the requirements leave a UI decision open, default to platform conventions (iOS/Android) and ask the user about decisions that change the layout.

> Codex での両対応に関する補足は [references/platform-notes.md](references/platform-notes.md) を参照。
