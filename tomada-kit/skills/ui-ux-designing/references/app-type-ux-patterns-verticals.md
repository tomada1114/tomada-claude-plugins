# UX patterns by app type (verticals and specialist domains)

Covers industry-leaning app types in the same "Reference products / Best practices / Patterns to avoid" format as `app-type-ux-patterns.md`. For the five general types (conversation/voice, e-commerce, dashboard, social, learning/education), see that file.

When several types apply, read all of them. Example: an AI code-review tool falls under both "AI assistant / agent UI" and "Developer tools".

## Table of contents

- [AI assistant / agent UI](#ai-assistant--agent-ui)
- [Productivity (notes / tasks)](#productivity-notes--tasks)
- [Fintech](#fintech)
- [Healthcare](#healthcare)
- [Developer tools](#developer-tools)
- [Booking / marketplace](#booking--marketplace)

---

## AI assistant / agent UI

### Reference products

| Product | What to study | Caveats |
|---------|---------------|---------|
| **Claude / ChatGPT** | Streaming output, stop and regenerate, attachment handling | |
| **Cursor** | Separating diff preview from apply; making context explicit | |
| **Perplexity** | Placement and granularity of citations | |
| **Linear's AI features** | Embedding AI in an existing GUI instead of funneling into chat | |

### Best practices

#### Streaming output and layout stability

```
- Render token by token, but hold code blocks until they close (never show a broken half-state)
- Reserve space so height does not jump during generation (min height, skeleton)
- Stop auto-scroll as soon as the user scrolls up, and switch to a "Jump to latest" button
- Announce incremental updates with aria-live="polite", but not per token (batch by paragraph)
```

#### Showing work and the plan layer

```
- Show tools used, search queries, and files read while they run, not after the result.
  Why: perceived wait time depends on whether the user can tell what is happening
- Each step has three states: running / done / failed; a failure keeps its reason
- Put details in a collapsible; show only a one-line summary by default
- For multi-step work, show the step list and current position, and mark where the user can intervene
```

#### Citations and trust cues

```
- Attach clickable source links to generated text, and map which sentence comes from which source
- Convey confidence secondarily through wording strength or color; never a bare numeric score.
  Why: numbers get trusted without basis and invite overconfidence
- When information is missing, say so instead of filling the gap with guesses
```

#### Control and apply

```
- Keep three controls always available: stop / retry / edit the last input and resend
- Present output as a proposal the user can edit or reject before adopting
- For anything that reaches outside (file writes, sending, publishing), require a diff preview and an explicit apply
```

### Patterns to avoid

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Only a spinner until completion | Perceived wait roughly doubles | Stream what is being worked on |
| Generation that cannot be interrupted | Users feel control was taken away | Always-available stop and retry |
| Assertions without sources | Unverifiable; erodes trust | Source links and explicit uncertainty |
| Pushing every feature into chat | Users cannot discover what is possible | Core actions in the GUI, chat as a helper |
| Applying output to production immediately | Irreversible | Diff preview + explicit apply |
| Height keeps shifting during generation | Unreadable; causes mis-taps | Reserved space and a stop condition for auto-scroll |

---

## Productivity (notes / tasks)

### Reference products

| Product | What to study | Caveats |
|---------|---------------|---------|
| **Linear** | Keyboard-first, optimistic updates, fast state transitions | |
| **Notion** | Block editing, switching views | Poor discoverability relative to feature count is a cautionary example |
| **Obsidian** | Local storage, link structure | The amount of exposed settings is excessive for general users |
| **Things** | Focused daily view, short add flow | |

### Best practices

#### Input and reflecting changes

```
- The add action opens with one key / one tap from any screen. Why: the effort of adding directly caps how much gets recorded
- Provide a command palette (every feature reachable by keyboard alone) and show each item's shortcut
- Apply edits instantly with optimistic updates; roll back and show the reason only on failure
- Limit save status to three states: saved / saving / offline (kept locally)
```

#### History, offline, and undo

```
- Make delete, move, and bulk changes undoable, with an undo action in the toast right after
- Queue offline edits instead of discarding them; on conflict at reconnect, keep both versions and let the user choose
- Show version history as "when, who, where", and let users view the diff before restoring
```

### Patterns to avoid

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Requiring a save button | Forgetting to save loses data | Autosave + save status |
| Delete guarded only by a confirm dialog | Users skim past it and delete | Undoable delete + trash |
| Undocumented shortcuts | Power users never get faster | List them on a reference screen and in menus |
| Unclear sync status | Users cannot tell "lost" from "not yet synced" | Explicit sync status and last-synced time |

---

## Fintech

### Reference products

| Product | What to study | Caveats |
|---------|---------------|---------|
| **Wise** | Showing fees and arrival time up front | |
| **Revolut / Monzo** | Readable transaction lists, instant card controls | Hierarchy design relative to feature count needs scrutiny |
| **Money Forward** | Aggregated view of multiple accounts, categorization | |

### Best practices

#### Displaying amounts

```
- Align digits with font-variant-numeric: tabular-nums.
  Why: misaligned digits force re-reading on every comparison
- Express sign with color + symbol + label, never color alone
- Always show the currency symbol or unit, and mark estimates with "approx." to distinguish them from final amounts
```

#### Transaction states and irreversible actions

```
- Show states as separate badges — pending / completed / failed / refunded — each with a next action
- The pre-transfer confirmation shows four items on one screen: amount, fee, expected arrival, recipient
- On failure, describe what the user can do next, not a reason code
- Transfers, account closure, and limit changes are irreversible, so require confirmation and re-show the recipient
- Mask balances and account numbers by default; reveal only on explicit action
```

### Patterns to avoid

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Hiding fees until the final screen | Loses trust; causes drop-off and complaints | Show the total from the input screen |
| Sign shown by color only | Indistinguishable for color-vision differences and in print | Add symbols and labels |
| Proportional digits that shift | Lists cannot be compared | Fix digits with tabular-nums |
| "Processing" with no explanation | Support inquiries increase | State expected duration and next action |
| Balance always shown large | Users cannot open the app in public | Masked by default + reveal toggle |

---

## Healthcare

### Reference products

| Product | What to study | Caveats |
|---------|---------------|---------|
| **Apple Health** | Aggregated metrics, period comparison, explicit data sources | |
| **Oura** | Showing the breakdown behind a score | Collapsing into one score can also take interpretation away from users |
| **Flo** | Controlling exposure of sensitive data, lightweight logging | |

### Best practices

#### Presenting numbers

```
- Pair numbers with interpretation (reference range, change since last time, measurement conditions).
  Why: a bare number cannot be judged good or bad, leading to either anxiety or indifference
- Use non-definitive wording ("tends to…", "consult a doctor for a diagnosis")
- Never show text that reads as diagnostic or treatment advice
```

#### Sensitive data and readability

```
- Hide health data by default; reveal on unlock or explicit action
- Keep specific values and symptom names out of notification previews
- Build on the assumption that dynamic text scaling (around 200%) must not break the layout
- Distinguish chart series by color + shape (marker shape, line style), with value labels alongside
```

### Patterns to avoid

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Showing only a large number | Users cannot tell good from bad | Add reference range and change since last time |
| Medical assertions | Leads to wrong self-diagnosis | Describe trends + guide to a doctor |
| Symptom names in notifications | Others can see them | Neutral wording + details in the app |
| Highlighting unlogged days in red | Guilt makes users stop logging | Neutral color + a path to resume logging |
| Presenting only a single score | Users do not know what to change | Let users open the breakdown and contributions |

---

## Developer tools

### Reference products

| Product | What to study | Caveats |
|---------|---------------|---------|
| **GitHub** | Diff display, review flow, expressing permissions | |
| **Sentry** | Error grouping and filtering, reproduction info | |
| **Vercel** | Build status badges, tailing logs | |
| **Linear** | Shortcut system, saved filters | |

### Best practices

#### Text, logs, and status

```
- Show logs, diffs, and identifiers in the monospace font, with line numbers and a wrap toggle
- Tail long-running logs by default; stop when the user scrolls up
- In diffs, add word-level changes within lines on top of line highlighting
- Show status badges (success / failed / running / skipped) three ways: color + icon + word
```

#### Filtering and copying

```
- Filters support combining and saving conditions, and reflect them in the URL
- Default list order is "needs attention"; chronological order is a toggle
- IDs, hashes, URLs, commands, and stack traces are copyable in one action.
  Why: developer tool output exists to be pasted elsewhere
- Put the shortcut list on one screen and also show shortcuts next to each menu item
```

### Patterns to avoid

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Identifiers that cannot be copied | Manual retyping causes errors | A copy action on every identifier |
| Non-monospace logs | Column alignment breaks; unreadable | Monospace font + line numbers |
| Status as color-only dots | Indistinguishable | Color + icon + word |
| Filters that cannot be saved | The same steps repeat every time | Saved conditions reflected in the URL |
| Errors shown only as internal codes | Users do not know how to respond | Cause + next action + collapsible details |

---

## Booking / marketplace

### Reference products

| Product | What to study | Caveats |
|---------|---------------|---------|
| **Airbnb** | Search → filter → compare → book flow, price breakdown | Do not adopt pressure copy like "only 1 room left" |
| **OpenTable** | Presenting availability, choosing time slots | |
| **Mercari** | Two-sided design for listing and buying, tracking transaction state | |

### Best practices

#### Search, filtering, and comparison

```
- Search criteria (dates, party size, location) stay visible on the results screen and editable in place
- Show the matching count before a filter is applied. Why: users can avoid actions that lead to zero results
- Show the total price (tax, fees, cleaning, etc.) already in the list, never the unit price alone
- Align comparison axes (price, rating, distance, cancellability) in the same place on every card
- Limit availability to three values — available / few left (with the actual number) / full — with no added theatrics
```

#### Booking and changes

```
- Before booking, restate five items on one screen: date/time, party size, location, total, cancellation terms
- Put change and cancel actions at the first level of the booking detail
- In two-sided marketplaces, describe the provider-side states (awaiting approval, confirmed) with the same vocabulary
```

### Patterns to avoid

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Unit price shown, total jumps at the end | Comparison becomes meaningless; trust is lost | Show the total in the list |
| Pressure copy like "N others are looking" | Unverifiable; may be subject to regulation | Quietly show only real inventory / availability |
| Cancellation terms visible only after booking | Generates complaints and refunds | Show them on the pre-booking screen |
| Zero filter results as a dead end | Users leave | Suggest results with one condition relaxed |
| Booking changes only via support | Operating costs and frustration pile up | Self-service from the booking detail |
