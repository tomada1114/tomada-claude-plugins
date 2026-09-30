# UX guidelines template

Scaffold for `docs/design/ux-guidelines.md` (or the path the caller names). It holds app-wide UX policy as values an implementing session can use directly. Screens and flows live in the UX flows document (`designing-wireframes`); colors, type, spacing, and tokens live in the design direction (`refero-design`, or the repository's `designing-ui`).

## How to use

- A scaffold, not a form. Keep only sections the conversation actually decided; delete the rest instead of filling defaults. Why: a leftover default reads as a decision to the implementing session. A section that ran deep may outgrow the scaffold.
- Every value gets a one-line reason: what it was chosen over and why. A value with no reason is not decided — drop it and ask.
- Values in `[brackets]` are examples; replace them.
- Undecided items: `Open: <what would settle it>`, in place, and collected under Open items.
- Match length to the substance; no filler, summaries, or restated principles.
- Copy from `# UX guidelines` down; leave this "How to use" section behind.

---

# UX guidelines

| | |
|---|---|
| Product | |
| Platforms | [macOS 15+, web] |
| App type | [section name in the app-type pattern references] |
| Related | Requirements: `<path>` · UX flows: `<path>` · Design direction: `<path>` |

## Principles

2–3 UX principles, each naming what it gives up. A sentence nobody would disagree with is a slogan; cut it.

- **[Principle]** — [one sentence]. Decides: [a concrete fork it settles]. Gives up: [what is lost].

## Navigation

- Model: [left sidebar, 2 levels max; command palette on Cmd+K] — why
- Back behavior: [browser back restores list scroll position and filters; filter state lives in the URL]
- Deep links: [every detail view has a URL]

## Platform conventions

One block per target platform.

- **[macOS]:** [every command in the menu bar with its shortcut; Settings on Cmd+,; windows remember size and position; toolbar items have labels in customization]
- **[Web]:** [URL reflects view and filters; no nested modals; min width 320 px]

## States

| State | Trigger | Shows | Primary action | Copy pattern |
|---|---|---|---|---|
| First-run empty | [no items ever] | [what the screen is for + one CTA] | [Create first X] | "No [X] yet. [Create your first X]." |
| No results | [search returns 0] | [query echoed, one suggestion] | [Clear search] | "Nothing matches “[query]”." |
| Filtered to zero | | | [Reset filters] | |
| Loading | | [skeleton in final layout] | — | — |
| Load failed | | [inline, keeps stale data if any] | [Retry] | "Couldn't load [X]. [Retry]." |
| Offline | | [banner; edits queue locally] | — | "You're offline. Changes will sync when you reconnect." |
| Permission denied (OS) | [camera/mic/notifications refused] | [why it's needed + how to enable] | [Open Settings] | |
| Not authorized | [role lacks access] | [who can grant access] | [Request access] | |

## Feedback and loading

| Rule | Value |
|---|---|
| Loading indicator delay | [none under 300 ms; show after 300 ms; once shown, keep at least 500 ms] |
| Long waits | [after 10 s: text explanation + Cancel] |
| Mutations | [optimistic; on failure roll back and show an error toast with Retry] |
| Destructive actions | [undo toast for 5 s instead of a confirm; confirm only for irreversible: payment, publish, permanent delete] |
| Toasts | [info 4 s auto-dismiss; errors that need action stay until dismissed; max 1 visible, newest replaces] |
| Error placement | [input → inline; transient → toast; blocking → full screen] |

## Forms and validation

- Timing: [validate on blur; after an error is shown, re-validate on input; submit validates all]
- Errors: [below the field, linked with `aria-describedby`, say what to fix]; on failed submit [focus moves to the first invalid field]
- Required/optional: [mark optional fields "(optional)"; required is the default]
- Submit button: [stays enabled; shows pending state and blocks double submit]
- Input is never cleared on error; `autocomplete` attributes on every personal-data field

## Motion

- Amount: [restrained — state changes and transitions only]
- Durations: [100 ms hover/opacity · 200 ms expand/collapse, popovers · 300 ms sheets, dialogs · page transitions none]
- Only `transform` and `opacity` animate
- Reduced motion: [movement, scale, parallax → fade of the same duration or instant; auto-play stops]
- If the repository's tokens name durations, cite the token names here instead of restating values.

## Language and copy

- UI languages: [English only] · RTL: [no] · Text expansion budget: [+35%, no fixed-width buttons]
- Formatting: numbers, dates, currency through [`Intl` / platform formatter]
- Register: [second person, sentence case, no exclamation marks]
- Buttons: verb + object ("Delete invoice", not "Delete" / "OK")
- Destructive confirm: states count and reversibility ("Permanently delete 3 files? This can't be undone.")

| Use | Don't use | For |
|---|---|---|
| | | |

## Signed-in and guest states

- [Browse as guest; sign-in interrupts the first write, then resumes that action]

## Accessibility targets

| Target | This product |
|---|---|
| Level | [WCAG 2.2 AA + 2.4.13 focus appearance] |
| Focus ring | [2 px outline, 2 px offset, on `:focus-visible`; color from the design direction, ≥3:1 measured] |
| Minimum target size | [44×44 pt/px primary; 24×24 px absolute floor] |
| Keyboard | [every function reachable; focus order = visual order; shortcut list in Help] |
| Focus not obscured | [`scroll-padding-top` = sticky header height + 8 px] |
| Live regions | [toasts polite; blocking errors assertive; streamed text per paragraph] |
| Color use | [never the only carrier: status = color + icon + text] |
| Text scaling | [200% without loss; reflow at 320 px] |
| Reduced motion / forced colors | [see Motion; outlines not shadows] |
| Contrast | [measured in the design direction's "Measured contrast" table — `<path>`] |

Verification for the implementing session: [simulate protanopia, deuteranopia, tritanopia, achromatopsia in DevTools; keyboard-only pass through every flow; VoiceOver pass on the primary flow].

## App-type rules

Rules adopted from the app-type references, each with its reason.

- [Streaming output: stop button always visible; auto-scroll stops when the user scrolls up]

## Reference products

| Product | Flow studied | Adopted | Rejected | Why |
|---|---|---|---|---|

## Non-goals

| Not doing | Why | Covered instead by |
|---|---|---|

## Open items

- Open: [what would settle it]

## Decision log

Append one row per question round. A resumed session reads this first.

| Date | Decided | Rejected options | Why |
|---|---|---|---|
| YYYY-MM-DD | | | |
