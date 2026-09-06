---
name: designing-wireframes
description: "Create ASCII wireframes, user flow diagrams, and cross-cutting specifications for UI/UX visualization (ワイヤーフレーム、画面設計、UI/UXフロー). Use PROACTIVELY when user mentions wireframe, UI design, UX flow, screen layout, screen design, user flow, or asks to visualize screens. Examples: <example>Context: User needs screen design user: 'Create wireframes for this feature' assistant: 'I will use designing-wireframes skill' <commentary>Triggered by wireframe request</commentary></example> <example>Context: After requirements are detailed user: 'Let me design the screens' assistant: 'I will use designing-wireframes skill' <commentary>Triggered by screen design request</commentary></example>"
metadata:
  platforms: claude-code, codex
---

# Wireframe Designer

Create ASCII wireframes, user flow diagrams, and cross-cutting specifications for UI/UX visualization.

**Before this skill**: Use `refining-requirements` to clarify ambiguous requirements.
**After this skill**: Use `planning-tickets` for GitHub Issues creation.

## Workflow

```
Input: Detailed requirements document
    |
Step 1: Create wireframes for each screen
    |
Step 2: Document user flows
    |
Step 3: Add cross-cutting sections
    |
Output: Requirements with wireframes & specifications
```

## Step 1: Create ASCII Wireframes

Create text wireframes (ASCII or box-drawing characters) for each screen in the requirements.

Primary actions belong in the reachable bottom zone; put destructive/rare actions (settings) higher up. Zone diagram and bottom-actions layout: wireframe-patterns.md.

### Component Patterns

See [wireframe-patterns.md](templates/wireframe-patterns.md) for: screen structures (basic, header actions, tab-based), components (progress bars, button grids, lists, settings), modals & overlays (bottom sheet, center modal, alert), onboarding screens, feedback (toast), swipe actions, empty states.

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

Based on user decisions from `refining-requirements`, add all 4 sections below to the requirements document.

Copy the four section templates from templates/cross-cutting-sections.md, filling in the app's real messages, timings and field rules.

## Best Practices

- Annotate wireframes with arrows or comments where the flow isn't obvious from the layout.
- Cross-reference related sections, include default values, and document edge cases (including empty states).
- Edit the target requirements document directly, section by section — don't create a separate file.
- When uncertain, default to platform conventions (iOS/Android) and ask the user about specific UI decisions; refer to `wireframe-patterns.md` for component examples.

> Codex での両対応に関する補足は `references/platform-notes.md` を参照。
