# UX patterns by app type

For each app type, this file keeps only what is worth encoding as a design decision. Each section has three parts — "Reference products / Best practices / Patterns to avoid" — and patterns to avoid are a table of Pattern | Problem | Alternative. Why: a pattern only works as an instruction once the alternative is written down.

For types not covered here (AI assistant/agent UIs, productivity — notes/tasks, fintech, healthcare, developer tools, booking/marketplaces), see `app-type-ux-patterns-verticals.md`.

The "Caution" column in the reference-product tables says what not to copy from that product. Entries marked "Observe only (dark-pattern counterexample)" are examples to avoid, not models to follow.

## Contents

- [Conversational / voice apps](#conversational--voice-apps)
- [E-commerce / shopping](#e-commerce--shopping)
- [Dashboards / admin panels](#dashboards--admin-panels)
- [Social / community](#social--community)
- [Learning / education apps](#learning--education-apps)
- [Checklist for research](#checklist-for-research)

---

## Conversational / voice apps

### Reference products

| Product | What to study | Caution |
|---------|---------------|---------|
| **ChatGPT voice mode** | Voice input/output state transitions, handling interruptions (barge-in) | |
| **Speak** | Presenting role-play goals, ending a conversation naturally | |
| **ELSA Speak** | Granularity and timing of pronunciation scores | |
| **Duolingo (conversation practice)** | How short sessions are divided | Evaluate streak pressure separately |
| **Replika** | — | Observe only (dark-pattern counterexample). Do not learn from its emotional retention hooks or paywall funnels |

### Best practices

#### In-conversation screen

```
- Make one state indicator (waveform or level meter) the focus of the screen
- Hide the transcript by default; let a toggle show it. Why: once users start reading, they stop speaking
- At most two always-visible buttons: End and Mute
```

#### Visualizing voice state

```
Vary three things per state: color + shape + label. Why: color-only distinction fails for color-vision differences and outdoor visibility
- AI speaking:    active waveform / accent color / "Speaking"
- User speaking:  active waveform / info color   / "Listening"
- Processing:     indeterminate indicator / muted text color  / "Thinking"
- Idle:           still waveform / subtle text color / "Tap to start"
```

#### Feedback timing

```
- Do not correct during the conversation. Afterwards, show "what went well → 1-2 things to fix", in that order
- During the conversation, show only non-evaluative info (volume, speaking rate, time left).
  Why: visible scoring reduces how much people speak, which reduces practice itself
```

#### Interruption and ending

```
- Stop AI audio immediately when user speech is detected (barge-in)
- Before auto-ending after prolonged silence, ask once whether to continue
- Keep feedback up to that point even when a session ends early. Why: if quitting feels like a loss, users don't come back
```

### Patterns to avoid

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Ending every turn with a question | Feels like an interrogation | Mix in turns that close with an acknowledgment; ask a question roughly one turn in three |
| Instant scoring mid-conversation | Awareness of evaluation shrinks speech | Present it together after the session |
| Voice-only experience | Unusable in noise or for users with hearing constraints | Provide text input and transcripts as equal paths |
| Long setup before starting | Users drop off before using it | Start immediately with defaults; suggest settings after the first session |
| State shown by color alone | Indistinguishable in some environments | Triple-encode with color + shape + label |

### Reference links (conversational UI / VUI)

- [Google Design: Speaking the Same Language (VUI design principles)](https://design.google/library/speaking-the-same-language-vui) — primary source
- [WillowTree: 7 UX/UI Rules for Designing a Conversational AI Assistant](https://www.willowtreeapps.com/insights/willowtrees-7-ux-ui-rules-for-designing-a-conversational-ai-assistant)
- [Voice User Interface (VUI) Design Principles](https://www.parallelhq.com/blog/voice-user-interface-vui-design-principles) — secondary source; verify claims against primary sources

---

## E-commerce / shopping

### Reference products

| Product | What to study | Caution |
|---------|---------------|---------|
| **Amazon** | Search and filtering, review display, repurchase paths | Product-page information density tends to be excessive for Japanese-language markets |
| **Mercari** | Low friction from listing to purchase, instant-buy paths | |
| **ZOZOTOWN** | Size selection, stock and restock-notification display | |
| **Apple Store** | Step-by-step configurator | |
| **SHEIN / Temu** | — | Observe only (dark-pattern counterexample). Do not learn from countdowns, fake low-stock warnings, or roulette-style coupons |

For seller-facing admin screens (Shopify etc.), see the dashboards section.

### Best practices

#### Product list

```
- Fix card content to four elements: image / name (max 2 lines) / price / rating (score + count)
- Reserve image space with aspect-ratio so lazy loading never shifts the layout
- Default to "Load more" + pagination for loading more.
  Use infinite scroll only when the conditions in the social section are met.
  Why: returning to the same position via "Back" directly affects conversion
- Filters immediately return the resulting item count
```

#### Product detail

```
- Gallery supports swipe and zoom; the first image conveys size
- Progressive disclosure: basics → details → reviews; collapse detailed specs
- Keep the add-to-cart CTA fixed while scrolling, with price and selected variant alongside
- Show stock, delivery time, and return terms before the CTA. Why: revealing them late is a main cause of cart abandonment
```

#### Cart / checkout

```
- Show the final total, including shipping, fees, and tax, before the payment step
- Make guest checkout the default path; offer account creation after purchase
- Add autocomplete attributes to inputs; fill the address from the postal code
- One purpose per step; show current position and remaining steps
- Show errors directly below the field, as a sentence saying what to fix and how
```

### Patterns to avoid

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Hidden shipping/fees | Total jumps on the final screen, destroying trust | Show an estimated total already on list and detail pages |
| Forced registration | Higher first-purchase drop-off | Guest checkout + registration offer after completion |
| Countdowns and stock pressure | Illegal if false; breeds distrust even if true | Show only real stock, without decoration |
| Stacked pop-ups | Users leave before seeing products | First visit only, one unobtrusive banner at the bottom |
| Pre-checked add-ons | Unintended charges and refund costs | Off by default; add-ons require an explicit action |

---

## Dashboards / admin panels

### Reference products

| Product | What to study | Caution |
|---------|---------------|---------|
| **Linear** | Keyboard operation, fast state transitions, optimistic updates | |
| **Stripe Dashboard** | Moving between list and detail, persistent filters | |
| **Shopify admin** | Information architecture for seller operations, bulk actions | Not a reference for buyer-side e-commerce |
| **Vercel** | Deployment status badges, auto-following logs | |
| **Notion** | Switching hierarchy and views | Treat its permission/sharing UI as an upper bound on complexity |

### Best practices

#### Layout

```
- Left sidebar (level 1) + in-page tabs (level 2). Stop the hierarchy at two levels
- Limit the top of the screen to 3-5 "numbers to act on today"; put the rest behind drill-downs
- Absorb variable space in the sidebar; prioritize width for the data area
```

#### Data display

```
- Lists are sorted and paginated by default. Never show all records by default
- Reflect filter state in the URL. Why: if it can't be shared and reproduced, it won't be used in operations
- Open details from a row in a panel or page, not a modal (don't break Back)
- Empty states say "why it's empty" and "what to do next"
- Exports apply to the filtered results
```

#### Actions

```
- For destructive actions, prefer "do it + undo (toast for a few seconds)" over a confirmation dialog.
  Why: confirmations get skimmed and stop working. Require confirmation only for irreversible actions (billing, publishing, permanent deletion)
- Button labels are verb + object ("Delete invoice", not "Delete")
- Bulk actions state the target count, including the total when targets extend off-screen
```

### Patterns to avoid

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Home page that just lists metrics | The numbers that matter get buried | Narrow to the top 3-5 metrics; drill down for the rest |
| Deep hierarchy | Users lose track of where they are | Two levels + full-text search |
| Stacked modals | Breaks Back | Panels or page navigation |
| Confirmation dialogs everywhere | Skimming becomes habit | Make actions undoable; confirm only irreversible ones |
| Different expression per screen | Learning cost accumulates | Share components and state patterns |

---

## Social / community

### Reference products

| Product | What to study | Caution |
|---------|---------------|---------|
| **Bluesky / Threads** | Feed structure, compose UI, moderation display | |
| **Discord** | Channel structure, notification granularity settings | |
| **Instagram** | Feel of Stories/Reels interaction | Don't copy notification pressure or algorithmic nudging |
| **Reddit** | Collapsible threads, voting and sorting | |

X changes its UI too much to serve as a microblogging model. Use Bluesky / Threads as the reference for feeds and compose UI.

### Best practices

#### Feed

```
- Default to "Load more" + pagination. Use infinite scroll only when both hold:
  (1) the footer holds no important info (terms, help, settings links)
  (2) returning from a detail view restores scroll position and loaded items
  Why: missing either creates unreachable info and lost reading position
- Pull-to-refresh never skips the read position; announce new posts with a count badge
- Autoplay video muted by default, and off by default on mobile data
- Likes etc. use optimistic updates (reflect instantly; revert and notify on failure)
```

#### Profile

```
- Put display name / handle / bio / links on the first screen, with editing one tap away
- Collect only fields that are displayed. Why: asking for unused attributes causes sign-up drop-off
```

#### Notifications

```
- Separate on/off per type; default to opt-in (only mentions and DMs on)
- In-app notifications show read/unread clearly, with one "mark all as read" action
- Ask for push permission once, after the user has experienced value, with a reason
```

### Patterns to avoid

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Unconditional infinite scroll | Footer unreachable; return position lost | "Load more" + position restore; infinite scroll only when conditions are met |
| All notifications on by default | Notification fatigue leads to uninstalling | Opt-in + per-type settings |
| Autoplay with sound | Can't open it in public | Muted by default; tap for sound |
| Hidden account/data deletion | Loses trust and invites regulation | Put account deletion at the same level within settings |
| Designing to maximize time spent | Trades retention for short-term metrics | Measure achievement, not time spent |

---

## Learning / education apps

### Reference products

| Product | What to study | Caution |
|---------|---------------|---------|
| **Duolingo** | Short units, progress visualization | Evaluate streak pressure and upsell pushes separately |
| **Khan Academy** | Showing prerequisites, dependencies between units | |
| **Anki** | Spaced-repetition schedule display | Exposes too many settings for a general audience |
| **Coursera** | Moving between videos and assignments, restoring resume position | |

### Best practices

#### Progress display

```
- Present a single "today's goal" with a numeric completion condition
- Show progress at two levels: within the unit and across the course. Course-only feels too distant
- If you use streaks, provide grace (days off that don't break it).
  Why: a design where one missed day wipes everything becomes a reason to quit
```

#### Lesson structure

```
- One unit is 5-15 minutes; after interruption, users resume where they left off
- Mix new and review material in one session (e.g. 70% new, 30% review)
- Adjust difficulty by accuracy; step back to easier items after consecutive misses
```

#### Handling wrong answers

```
- Don't stop at showing the right answer; add 1-2 sentences on why
- Retry is one tap from the same screen
- Send wrong answers to a review queue; don't show them as accumulating penalties.
  Why: a running tally of losses raises the psychological cost of coming back
```

### Patterns to avoid

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Long sessions | Focus breaks, and stopping feels like failure | 5-15 minute units + saved resume position |
| Emphasizing failure | Users stop returning | Turn wrong answers into a review queue |
| Passive video watching | Doesn't stick | Insert check questions every few minutes |
| Excessive gamification | Rewards, not learning, become the goal | Limit rewards to progress visualization |
| Streaks that reset completely | One missed day leads to churn | Grace days and a way to recover |

---

## Checklist for research

When trying competitors, check the same items in the same order for every type. Use these as the observation items for Step 2 (cross-competitor flow comparison) in `research-methods.md`.

### All app types

- [ ] Number of steps from onboarding to the first meaningful result
- [ ] Layout of key screens and priority of information
- [ ] Navigation structure (hierarchy depth, how current location is shown)
- [ ] Error handling (are cause and recovery stated?)
- [ ] Loading display (skeleton, spinner, or with progress?)
- [ ] Empty states (is the next action stated?)
- [ ] Settings structure and defaults
- [ ] Accessibility (keyboard operation, dynamic text size, contrast)

### Type-specific

**Conversational / voice:** voice-state visualization / feedback timing / interruption and ending

**E-commerce:** search and filtering / when the total is shown / cart operations / number of checkout steps

**Dashboards:** information hierarchy / filter persistence / bulk actions / export

**Social:** feed loading method and position restore / notification defaults and granularity / moderation paths

**Learning / education:** unit length / built-in review / handling wrong answers / progress granularity
