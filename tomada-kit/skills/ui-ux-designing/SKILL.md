---
name: ui-ux-designing
description: "Produces one app-wide UX guidelines document (docs/design/ux-guidelines.md or a caller-named path) fixing navigation, platform conventions, empty/loading/error/offline/permission states, feedback, form validation, motion and reduced-motion, UI language and i18n, and accessibility targets as concrete values, settled through batched AskUserQuestion rounds; also runs a measured WCAG contrast pass on a palette decided elsewhere. Use when settling app-wide behavior, deciding state handling, validation timing, motion policy, or accessibility targets, when a kickoff needs UX guidelines, or when a palette or tokens file needs its contrast measured. Not for visual direction — palette, typography, tokens (refero-design, plus the repository's designing-ui skill); not for wireframes, screen layouts, or user flows (designing-wireframes); not for product requirements (refining-requirements)."
argument-hint: "[output-path] | contrast <palette-source> [into <doc>]"
metadata:
  platforms: claude-code
---

# UI/UX Designing

Settles app-wide UX policy and writes it to one document. The reader is a later session implementing UI, so the document holds values it can use directly — durations in ms, sizes in pt/px, exact copy patterns, which state shows what — not adjectives. Why: "friendly errors" or "AA compliant" cannot be implemented, so the implementing session would decide on the spot anyway.

Visual direction (references, palette, typography, spacing, tokens, the design lock) belongs to `refero-design` and, when the repository has one, its own `designing-ui` skill. This skill only measures a palette's contrast.

## Contract

**Arguments** (free-form, any combination):
- an output path ending in `.md` — default `docs/design/ux-guidelines.md` in the target repository. Callers without a repository yet pass a path such as `<state-dir>/ux-guidelines.md`.
- paths of sibling documents — requirements, UX flows, design direction — to read and link, never restate.
- `contrast <palette-source> [into <doc>]` — run only the [contrast pass](#contrast-pass) on a pairs JSON, a tokens file, or a design-direction document, and paste the table into `<doc>`.

**Output:** the one document, from [templates/ux-guidelines-template.md](templates/ux-guidelines-template.md). If the repository already has a UX home — an existing `ux-guidelines.md`, or UX sections in an older `docs/design/design-concept.md` / `design-system.md` — update that file in place instead of creating a second one. Why: two sources split the implementing session's reference, and the stale one gets read. When it is unclear which file is canonical, ask once with AskUserQuestion.

**Boundaries:** screen layouts, wireframes, and user flows → `designing-wireframes`; product requirements → `refining-requirements`; visual direction → `refero-design`. When one of those documents exists, link to it and write only policy it does not already fix.

## Workflow

A single, local question ("how should this list behave when empty?") gets one recommendation and its trade-off, then stop — the steps below are for a product without settled UX policy.

1. **Read inputs.** Requirements, UX flows, the template or repository constraints (platform, stack, sample app), existing `docs/design/*`, README. Anything they answer is settled and not asked again. Why: users asked something they already answered start answering the rest carelessly. Identify the platforms and the app type (a section in [references/app-type-ux-patterns.md](references/app-type-ux-patterns.md) or [references/app-type-ux-patterns-verticals.md](references/app-type-ux-patterns-verticals.md)).

2. **Research competitor UX — when it would change an option.** Skip it when the caller says research is done, the inputs already name reference products with their flows, or the app has no real competitors. Otherwise pick at least three products, fill [references/agents/research-competitors.md](references/agents/research-competitors.md), and hand it to one `executor` sub-agent (cap: one; tier criteria in `orchestrating-models`). Why `executor`: the products, flows, rubric, and output shape are all fixed here, so what remains is collection without judgment. Share the summary with the user before the first question round; the options are built on it.

3. **Ask the question rounds** from [references/questions-core.md](references/questions-core.md) (Rounds 1–3), then Round 4 only when the app type matches a section of [references/questions-app-type.md](references/questions-app-type.md). For an app type not listed there, build 2–3 equivalent questions from the matching pattern section, choosing only points whose answer changes an implementation value. Follow [Asking questions](#asking-questions).

4. **Write the document after each round**, not once at the end. Round 1 creates it from the template; every round appends a row to its Decision log — decided, rejected options, why. A resumed session reads the Decision log before composing questions. Why: without it, settled questions get asked again, and without the reasons, a later objection cannot be weighed.

5. **Fill the accessibility targets** with concrete values from [references/accessibility.md](references/accessibility.md): focus ring width and offset, minimum target size, keyboard rules, live-region policy, the color-vision rule, text scaling. Colors are not decided here; the contrast row points at the measured table.

6. **Finish the document.** Keep only decided sections and delete the rest — a leftover default reads as a decision. Mark each gap `Open: <what would settle it>` where it belongs and collect them under Open items. Match length to the substance. Report the path, the decisions, and the open items.

## Contrast pass

Runs on any palette decided elsewhere — the token values in a `refero-design` direction, a template's `tokens.css` / `globals.css`, a Tailwind `@theme` block. Follow the pair checklist and value-resolution rules in [references/accessibility.md § Contrast pass](references/accessibility.md#contrast-pass): list light and dark pairs, resolve `var()` / `light-dark()` to literal colors, composite any alpha onto its background, write a pairs JSON next to the target document, then run:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/check_contrast.py <pairs.json>            # AA; add --level AAA, --json
python3 ${CLAUDE_SKILL_DIR}/scripts/check_contrast.py --pair "#FFFFFF" "#2563EB" --kind text
```

The JSON is an array of `{"name", "fg", "bg", "kind"}`; `kind` is `text`, `large`, or `ui`. Accepted colors: `#RRGGBB`, `#RGB`, `rgb()`, `oklch()`, no alpha. Exit 0 = all pass, 1 = a pair fails, 2 = bad input.

Paste the printed table unedited under "Measured contrast" in the document the caller named (default: the Accessibility targets section of the UX guidelines), with the pairs file path. Why: ratios from memory are often wrong, and a wrong ratio marked PASS ships unreadable UI. On FAIL, report each failing pair with the smallest passing change and hand it to the palette owner — `refero-design`'s direction or the user — then re-run until exit 0. This skill does not change the palette itself.

## Asking questions

Every question goes through AskUserQuestion, using the JSON in the question files as-is (translated into the user's language when the conversation is in another one).

- 2–4 options, each with its concrete content and what it gives up. Why: an open question ("how should errors work?") hands the design to the user, and the answer does not map to a value.
- At most one option marked `(Recommended)`, and only when one really is better for this product. Why: several recommendations equal none, and an unfounded one skews the choice.
- Up to 4 questions per call, one call per round. Why: later questions in a long batch get careless answers, and careless answers ship as values.

## Resources

- [references/questions-core.md](references/questions-core.md) — Rounds 1–3 and the round plan
- [references/questions-app-type.md](references/questions-app-type.md) — Round 4 for conversation/voice, e-commerce, dashboards, AI assistants
- [references/app-type-ux-patterns.md](references/app-type-ux-patterns.md) — conversation/voice, e-commerce, dashboards, social, learning
- [references/app-type-ux-patterns-verticals.md](references/app-type-ux-patterns-verticals.md) — AI assistants, productivity, fintech, healthcare, developer tools, booking/marketplace
- [references/accessibility.md](references/accessibility.md) — targets table, contrast requirements and pass, user settings, color-vision and keyboard rules
- [references/research-methods.md](references/research-methods.md) — research procedure and summary format, when researching without delegating
- [references/agents/research-competitors.md](references/agents/research-competitors.md) — the delegation prompt
- [templates/ux-guidelines-template.md](templates/ux-guidelines-template.md) — the output document
