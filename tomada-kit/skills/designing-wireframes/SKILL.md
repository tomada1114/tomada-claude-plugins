---
name: designing-wireframes
description: >-
  Create ASCII wireframes for every screen and window, user flow diagrams, and
  per-screen states (empty, loading, error) from a requirements document, for desktop
  (macOS windows, menu-bar popovers, settings), web (responsive app shells), and mobile.
  Writes into the requirements document in place, or into a separate file the caller
  names. Use when asked for a wireframe, screen layout, screen design, window layout,
  or user flow, to visualize screens before implementation, or as the UX stage of
  kicking-off-apps.
argument-hint: "[requirements path] [--out path]"
metadata:
  platforms: claude-code
---

# Designing Wireframes

**Before:** `refining-requirements`. **Alongside:** `ui-ux-designing` owns app-wide UX
policy (navigation model, state rules, validation, motion, accessibility targets); this
skill owns what each screen looks like and how a user moves between them.
**After:** `planning-tickets`.

## Input and output

Input is a requirements document. Output goes to the path the caller names (the kickoff
passes a separate `ux-flows.md`); with no path, add the wireframes to the requirements
document in place, section by section.

## 1. Screen inventory

List every screen, window, sheet, and popover the MVP features need, with the feature
section each serves. Show the list to the user before drawing: a missing or extra
screen is cheaper to catch here than after twenty diagrams.

## 2. Wireframes

Draw each screen with ASCII or box-drawing characters, following the platform's
conventions:

- **Desktop / web:** [templates/desktop-web-patterns.md](templates/desktop-web-patterns.md) —
  minimum window size and what collapses first, the shortcut for every primary action,
  menu-bar placement of every command on macOS, breakpoints on the web.
- **Mobile:** [templates/mobile-patterns.md](templates/mobile-patterns.md) — primary
  actions in the reachable bottom zone, destructive and rare actions higher up.

Annotate with real values from the requirements (labels, limits, sizes), and draw the
empty, loading, and error variants of each screen that has them.

## 3. Flows

One flow per core task, as numbered steps and a diagram that includes the failure
branch:

```
[Start] -> [Screen A] -> [Action] -> [Screen B]
                |
                v
           [Error] -> [Retry]
```

## 4. Cross-cutting behavior

When a UX guidelines document exists (`docs/design/ux-guidelines.md`, or the one the
kickoff produced), cite its rules per screen rather than restating them. Without one,
add the four sections of [templates/cross-cutting-sections.md](templates/cross-cutting-sections.md) —
error handling, accessibility, loading and feedback, form validation — filled with the
app's real messages, timings, and field rules.

Where the requirements leave a layout decision open, default to the platform's
conventions and ask the user (AskUserQuestion, batched) only about decisions that
change the layout.
