# Accessibility

The targets a product's UX guidelines commit to, how to set each one to a concrete value, and how to measure contrast on a palette decided elsewhere. The palette itself is chosen by `refero-design` (and the repository's `designing-ui` skill when it has one); this file only checks it.

## Contents

- [Target level](#target-level)
- [Targets table](#targets-table)
- [Contrast requirements](#contrast-requirements)
- [Contrast pass](#contrast-pass)
- [Following user settings](#following-user-settings)
- [Color-vision checks](#color-vision-checks)
- [Keyboard and assistive technology](#keyboard-and-assistive-technology)

---

## Target level

WCAG 2.2 level AA is the floor. WCAG 2.2 is a W3C Recommendation and is standardized as ISO/IEC 40500.

Services offered in the EU fall under the European Accessibility Act, which applies through the harmonized standard EN 301 549. That standard references WCAG 2.1 AA; meeting 2.2 AA also meets 2.1 AA, so target 2.2. Japan's JIS X 8341-3 maps to WCAG as well, so one target covers all three.

Put the targets table below in the UX guidelines with the "This product" column filled. Why: an implementing session can act only on concrete values; "AA compliant" can be neither implemented nor verified.

---

## Targets table

Focuses on criteria added in 2.2 and on those that must be decided before implementation.

| Criterion | Requirement | Decide |
|---|---|---|
| 2.5.8 Target size (minimum) | Targets at least 24×24 CSS px, or spaced so a 24 px circle centered on each does not overlap another target | Minimum target size |
| Target size (design value) | 24 px is the conformance floor, not a design value; use iOS 44×44 pt / Android 48×48 dp / web 44×44 px for primary controls | Actual size of primary controls |
| 2.4.11 Focus not obscured (minimum) | A focused element is not entirely hidden by sticky headers, footers, or toolbars | Height of fixed regions and the `scroll-margin` / `scroll-padding` value |
| 2.4.13 Focus appearance (AAA) | Outline at least 2 px thick around the element, 3:1 between focused and unfocused states | Focus ring width, offset, and which token supplies its color |
| 2.5.7 Dragging movements | Every drag action has a single-pointer alternative | Alternatives for reordering, sliders, map panning |
| 3.3.7 Redundant entry | Information entered earlier in the same process is not requested again (auto-filled or selectable) | Reuse policy for address, name, etc. |
| 3.3.8 Accessible authentication (minimum) | No cognitive test (memorizing, puzzles, transcribing characters) is required | Password manager and paste allowed; alternative sign-in methods |
| 1.4.10 Reflow | No two-dimensional scrolling at 320 CSS px width (400% zoom) | Minimum supported width; exceptions (tables, diagrams) |
| 1.4.12 Text spacing | Content survives line height 1.5, paragraph spacing 2×, letter spacing 0.12em, word spacing 0.16em | Places that must not use fixed heights |
| 1.4.11 Non-text contrast | UI component boundaries, state indicators, icons, and chart marks at 3:1 against adjacent colors | Measured in the contrast pass |
| 1.4.3 Contrast (minimum) | 4.5:1 normal text, 3:1 large text | Measured in the contrast pass |

Settle 2.4.13 even when the target is AA. Why: added later, the focus ring ends up looking different per component and cannot be unified.

Defaults to propose when nothing in the inputs says otherwise: focus ring 2 px solid, 2 px offset, drawn with `outline` on `:focus-visible`; primary targets 44×44 pt/px (48×48 dp on Android); text scales to 200% without loss.

---

## Contrast requirements

| Target | AA | AAA |
|---|---|---|
| Normal text (under 24 px, or under 18.66 px bold) | 4.5:1 | 7:1 |
| Large text (24 px and up, or 18.66 px bold and up) | 3:1 | 4.5:1 |
| UI component boundaries, state indicators, icons, chart marks (1.4.11) | 3:1 | — |
| Focus indicator (2.4.13) | 3:1 | — |
| Decorative, disabled, logos | Exempt | — |

"Exempt" does not mean unmeasured: a disabled control must still be recognizable, so aim for about 2.5:1 against its background.

Placeholder text counts as body text (4.5:1). Why: when it is the only label before input, an unreadable placeholder hides what the field is for.

WCAG 2.x ratios are the floor that law and audits reference. APCA Lc may be used alongside as a readability signal (Lc 90 for body text, at least Lc 75 for anything meant to be read), but never write "compliant" on the strength of APCA alone: WCAG 3 is a Working Draft and its contrast method is not final, so APCA values are not audit evidence.

---

## Contrast pass

Run this on any palette decided elsewhere: the token values in a `design-direction.md` from `refero-design`, a template's `tokens.css` / `globals.css`, or a Tailwind `@theme` block.

1. **List the pairs**, in light and in dark separately:
   - body text / background, and on every surface it sits on (card, elevated, sidebar)
   - muted and subtle text / background (subtle text used for real content counts as `text`)
   - placeholder / input background
   - on-accent text / accent at base, hover, and pressed
   - link text / background
   - each status color used as text (danger, success, warning, info) / background, and on-status text / status fill
   - input border and control boundaries / background (`ui`)
   - focus ring / background, and focus ring / accent where the ring sits on filled buttons (`ui`)
   - icons that carry meaning / background (`ui`)
2. **Resolve every value to a literal color** the script accepts: `#RRGGBB`, `#RGB`, `rgb(r g b)`, `oklch(L C H)`. Follow `var()` chains and split `light-dark(a, b)` into the light and dark pair. The script rejects alpha: composite a translucent color onto its actual background first (per channel: `a·fg + (1−a)·bg` in sRGB), and name the pair so the reader knows it was composited. Convert `hsl()` to hex first.
3. **Write the pairs JSON** next to the document the table goes into (e.g. `<state-dir>/contrast-pairs.json`), so a re-run after a palette change is one command:

   ```json
   [
     {"name": "light/text on bg", "fg": "#18181B", "bg": "#FFFFFF", "kind": "text"},
     {"name": "light/on-accent on accent-hover", "fg": "#FFFFFF", "bg": "oklch(0.52 0.19 262)", "kind": "text"},
     {"name": "dark/focus on bg", "fg": "#7AA2FF", "bg": "#0A0A0B", "kind": "ui"}
   ]
   ```

   `kind` is `text` (body), `large` (large text), or `ui` (boundaries, icons, focus).
4. **Run** `python3 ${CLAUDE_SKILL_DIR}/scripts/check_contrast.py <pairs.json>` (add `--level AAA` for an AAA target, `--json` for machine-readable output; `--pair FG BG --kind ui` checks one pair ad hoc). Exit 0 = all pass, 1 = at least one FAIL, 2 = input error.
5. **Paste the table** the script prints, unedited, into the target document under a "Measured contrast" heading, with the pairs file path. Why: ratios written from memory or copied from elsewhere are often wrong (a common one: `#71717A` on `#0A0A0B` quoted as 4.6:1 measures 4.09:1), and a wrong ratio marked as passing ships an unreadable UI.
6. **On FAIL**, report each failing pair with the smallest change that passes (usually lowering or raising OKLCH L on one side, or switching to a dark on-color) and hand it to the palette owner — the `refero-design` direction or the user. Re-run after the palette changes until exit 0.

Known failures worth checking first: white text on Tailwind 500-level fills fails (amber 2.15, green 2.28, orange 2.80, blue 3.68, red 3.76, violet 4.23; blue-600 passes at 5.17), and light gray on white fails (`#9CA3AF` on `#FFFFFF` = 2.54).

---

## Following user settings

| Setting | Required behavior |
|---|---|
| `prefers-reduced-motion: reduce` | Stop translation, scaling, rotation, parallax; replace with a fade or color change rather than removing the state change. Stop auto-playing carousels. |
| `prefers-contrast: more` | Raise boundaries to the strong border color and move muted text toward body text. |
| `forced-colors: active` | `box-shadow` and `backdrop-filter` are dropped: boundaries and focus rings drawn with shadows must use `border` / `outline`. Check that no information lives only in background images. |
| OS text size (Dynamic Type / font scale) | No breakage up to 200%. Body text in `rem` (web), text styles (native). |

Draw focus rings with `outline`. Why: `border` shifts layout, and `box-shadow` disappears in forced-colors mode.

---

## Color-vision checks

Holding "consider color blindness" as a principle detects nothing; write these rules into the guidelines and hand the steps to the implementing session.

1. List every place information is carried by color: status, required fields, chart series, link vs text. Each gets a shape, icon, or text as well.
2. Success green and error red often have near-equal lightness; always pair status colors with an icon.
3. Distinguish chart series by lightness difference and pattern (solid/dashed lines, fill patterns), not hue alone.
4. Simulate in the browser: Chrome/Edge DevTools → Rendering → Emulate vision deficiencies (protanopia, deuteranopia, tritanopia, achromatopsia); Firefox Accessibility Inspector → Simulate.
5. Review every screen in achromatopsia (grayscale). A design that works there works for the other types.

---

## Keyboard and assistive technology

Decide each of these as a rule in the guidelines:

- Every function is reachable and operable by keyboard alone; nothing exists only on hover or drag.
- Focus order matches visual order; if CSS `order` or `grid-area` reorders content, the DOM order follows.
- Focus rings appear on `:focus-visible`. Why: rings shown on mouse click get removed as "ugly", and keyboard users lose them.
- Live-region policy: which async updates, streamed output, and toasts are announced, and how. Default `aria-live="polite"`; `assertive` only for errors that block the user. Streamed text is announced per paragraph, not per token.
- Heading levels and landmarks (`header` / `nav` / `main` / `aside` / `footer`) are part of every screen's structure.
- Modals trap focus and return it to the triggering element on close.
- Icon-only buttons carry an accessible name, plus a tooltip on pointer devices.
