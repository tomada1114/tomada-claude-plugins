# Core question bank (Rounds 1–3)

Question data for the app-wide UX rounds. The rules for asking (option count, trade-offs, one `(Recommended)`, batch size) are in SKILL.md § Asking questions. App-type questions for Round 4 are in `questions-app-type.md`.

Every JSON block is an AskUserQuestion question as-is. Translate `question`, `label`, and `description` into the user's language at runtime when the conversation is in another language; keep the meaning and the trade-off in each description. Move `(Recommended)` to a different option when the product's inputs point elsewhere, and drop it when nothing is clearly better.

## Contents

- [Round plan](#round-plan)
- [Round 1 — Structure](#round-1--structure)
- [Round 2 — States and feedback](#round-2--states-and-feedback)
- [Round 3 — Input, motion, language, accessibility](#round-3--input-motion-language-accessibility)

## Round plan

| Round | Questions | What it settles |
|---|---|---|
| 1 Structure | Navigation model / Platform conventions / Device priority / Signed-out states | The container every screen lives in |
| 2 States and feedback | Empty states / Loading / Errors, offline, permission denied / Action feedback | The places implementation sessions otherwise improvise |
| 3 Input, motion, language, a11y | Form validation / Motion amount / UI language / Accessibility target | Rules every form, transition, and string follows |
| 4 App type (when it applies) | From `questions-app-type.md` or built from the app-type pattern files | Type-specific behavior |

Drop any question whose answer is already in the inputs (requirements, UX flows, template constraints) or that does not apply — a round of two questions is fine. Why: an answer that changes no implementation value still lands in the document and reads as a decision.

## Round 1 — Structure

### Navigation model

```json
{
  "question": "What structure should primary navigation use?",
  "header": "Navigation",
  "options": [
    { "label": "Bottom tabs (3–5)", "description": "Mobile-first and strong for one-handed use. Past five top-level features it needs a 'More' tab that hides things." },
    { "label": "Left sidebar", "description": "Desktop or information-heavy apps. Hierarchy and filters stay visible, but it always costs width and must collapse on mobile." },
    { "label": "Hub and spoke (home first)", "description": "Sparse features where users return home between tasks. Moving between features takes two steps." },
    { "label": "Command palette first", "description": "Tools for practiced users: fast and keyboard-driven. If the GUI becomes secondary, first-time users cannot discover features." }
  ]
}
```

### Platform conventions

```json
{
  "question": "Which platforms does the app target? (multi-select)",
  "header": "Platforms",
  "options": [
    { "label": "Web (responsive)", "description": "Browser back and the URL carry state. Deeply nested modals stop matching history." },
    { "label": "iOS / iPadOS", "description": "Apple HIG: edge-swipe back, safe areas, and Dynamic Type become hard requirements." },
    { "label": "Android", "description": "Material conventions: predictive back, edge-to-edge drawing, many aspect ratios." },
    { "label": "macOS desktop", "description": "Apple HIG for Mac: menu bar with every command, keyboard shortcuts, multiple windows, Settings on Cmd+,. A web UI reused as-is feels slow here." }
  ],
  "multiSelect": true
}
```

Write the per-platform consequences into the document (back behavior, shortcut set, window model, safe areas, text scaling), not only the platform names.

### Device priority

```json
{
  "question": "Which width should design start from?",
  "header": "Device",
  "options": [
    { "label": "Mobile first", "description": "Design narrow, then expand. Forces prioritization, but desktop layouts tend to feel stretched." },
    { "label": "Desktop first", "description": "Start from the information-heavy view; suits work tools. Decisions about what to cut on mobile get postponed." },
    { "label": "Equal weight", "description": "Design the key screens at both widths in parallel. Highest quality, twice the specification work." }
  ]
}
```

Skip this for single-platform native apps.

### Signed-out states

The authentication method itself (providers, required or optional) belongs to requirements; ask only whether it adds screens.

```json
{
  "question": "Does what the user sees depend on being signed in?",
  "header": "Guest",
  "options": [
    { "label": "Guests can try core features", "description": "Every core screen works signed out. Lowest barrier, but each screen needs a prompt to save or sync and a story for carrying data over after sign-in." },
    { "label": "Browse as guest, sign in to write", "description": "Sign-in interrupts the first write action. The interrupted action must resume after sign-in." },
    { "label": "Everything after sign-in", "description": "Only a sign-in screen before login. Fewest screens, but first-time visitors need a separate surface that explains the value." }
  ]
}
```

Skip when the app has no accounts.

## Round 2 — States and feedback

Design these as separate states: first-run empty, no search results, filtered to zero, load failed, offline, and permission denied (OS permission and authorization). Why: each looks like "nothing here", but the next action differs in every case.

### Empty states

```json
{
  "question": "How should screens with no data look?",
  "header": "Empty",
  "options": [
    { "label": "Onboarding style (Recommended)", "description": "Explain what the screen is for plus one call to action. Doubles as first-run guidance, but feels repetitive if it shows every time." },
    { "label": "Minimal", "description": "One short sentence. Fast for users who know the app; a dead end for first-time users." },
    { "label": "Sample data", "description": "Faint placeholder rows show the shape of the result. Communicates the end state, but risks being mistaken for real data." }
  ]
}
```

### Loading

```json
{
  "question": "How should loading be shown?",
  "header": "Loading",
  "options": [
    { "label": "Skeletons (Recommended)", "description": "Placeholders in the final layout's shape; no layout jump on arrival. The skeleton must be kept in sync with the real layout." },
    { "label": "Spinner", "description": "Lightest to build. The layout tends to jump on completion and long waits show no progress." },
    { "label": "Progress bar", "description": "For work whose remaining time can be estimated. On work that cannot, it looks stalled and erodes trust." }
  ]
}
```

Whatever the choice, record the timing thresholds (defaults: show nothing for waits under 300 ms, show the indicator after 300 ms and keep it at least 500 ms once shown, add a text explanation or cancel after 10 s).

### Errors, offline, permission denied

```json
{
  "question": "How should errors, offline, and permission-denied states be communicated?",
  "header": "Errors",
  "options": [
    { "label": "By severity (Recommended)", "description": "Input errors inline, transient failures as a toast, blocking states full-screen. More patterns to design, fewest interruptions for the user." },
    { "label": "Toast for everything", "description": "Simple to build. Toasts disappear, so errors that need the user to act again get missed." },
    { "label": "Modal for everything", "description": "Never missed, but interrupts even for minor errors and is strongly disliked when frequent." }
  ]
}
```

### Action feedback

```json
{
  "question": "How should the app respond when the user changes or deletes something?",
  "header": "Feedback",
  "options": [
    { "label": "Optimistic + undo (Recommended)", "description": "Apply immediately, roll back with a message on failure; destructive actions show an undo toast instead of a confirm dialog. Fast, but every mutation needs a rollback path. Irreversible actions (payment, publish, permanent delete) still confirm." },
    { "label": "Wait for the server", "description": "Show a pending state until the server confirms. Simplest to reason about; feels slow on poor networks." },
    { "label": "Confirm dialogs", "description": "Ask before every destructive action. Easy to build, but users learn to click through and the dialog stops protecting them." }
  ]
}
```

## Round 3 — Input, motion, language, accessibility

### Form validation

```json
{
  "question": "When should form fields be validated?",
  "header": "Validation",
  "options": [
    { "label": "On blur, then live (Recommended)", "description": "Validate a field when the user leaves it; once it shows an error, re-validate on each keystroke so the error clears as soon as it is fixed. Submit validates everything. Balanced, slightly more state per field." },
    { "label": "On submit only", "description": "Nothing interrupts typing. Long forms return a batch of errors at the end." },
    { "label": "Live while typing", "description": "Immediate feedback, but shows errors before the user has finished (an email is 'invalid' until the @)." }
  ]
}
```

Whatever the choice, record: where errors appear (below the field, linked with `aria-describedby`), what happens on a failed submit (focus moves to the first invalid field or an error summary), how required and optional fields are marked, that the submit button stays enabled, and that input is never cleared on error.

### Motion amount

```json
{
  "question": "How much animation and micro-interaction should the app have?",
  "header": "Motion",
  "options": [
    { "label": "Restrained (Recommended)", "description": "Screen transitions and state changes only, within 100–200 ms. Never breaks on low-end devices; less memorable." },
    { "label": "Moderate", "description": "Adds press feedback, count-ups, list item enter/exit. More to build and to test." },
    { "label": "Expressive", "description": "Choreographed transitions and shared-element animation. Distinctive, but dropped frames make it worse than none." }
  ]
}
```

Whatever the choice, record the reduced-motion substitute (fade or instant change) for every animation. Why: for users with vestibular disorders, the motion itself triggers symptoms.

### UI language and i18n

```json
{
  "question": "Which UI languages should the app support?",
  "header": "Language",
  "options": [
    { "label": "One fixed language", "description": "Layouts can be tuned to measured text. Adding a language later means reworking button widths and line wrapping." },
    { "label": "Several languages, LTR only", "description": "Needs a language switcher and externalized strings. No fixed-width buttons: budget +35% (to German) and +50% (Japanese to English) text expansion." },
    { "label": "Several languages including RTL", "description": "Left and right flip: all layout in logical properties (margin-inline-start), and icons chosen per whether they mirror. Highest test cost." }
  ]
}
```

Whatever the choice, numbers, dates, and currency go through `Intl` (or the platform formatter), never hand-written formats. Why: the device locale changes formatting even in a single-language app. Also settle the UI copy register and the glossary (see the template's UI copy section).

### Accessibility target

```json
{
  "question": "Which accessibility target should the app commit to?",
  "header": "A11y target",
  "options": [
    { "label": "AA + focus ring (Recommended)", "description": "WCAG 2.2 AA — the legal floor (EAA, JIS X 8341-3) — plus the AAA focus-ring rule 2.4.13, which is cheap if decided now and inconsistent if added later." },
    { "label": "AA only", "description": "WCAG 2.2 AA. Meets audits. Focus rings may end up differing per component." },
    { "label": "AA + selected AAA", "description": "For public-sector, health, or education audiences. Adds 7:1 body-text contrast and stricter focus visibility; constrains the palette owner." }
  ]
}
```

After this answer, fill the accessibility targets table from `accessibility.md` with concrete values (focus ring width and offset, minimum target size, keyboard rules, live-region policy, color-vision rule).
