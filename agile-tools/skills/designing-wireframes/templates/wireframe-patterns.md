# Wireframe Patterns

Common UI patterns for ASCII wireframes.

## Thumb-Zone Design (Mobile UX Critical)

Primary actions should be placed in the "green zone" (bottom of screen) for easy thumb reach.

### Thumb Reach Zones

```
┌─────────────────────────────────┐
│                                 │  ← Hard to reach (Red)
│    Settings, destructive        │    Place: Settings, delete
│                                 │
├─────────────────────────────────┤
│                                 │  ← Stretch zone (Yellow)
│    Secondary content            │    Place: Secondary actions
│                                 │
├─────────────────────────────────┤
│                                 │  ← Natural zone (Green)
│    Primary actions              │    Place: Main CTA, nav
│                                 │
└─────────────────────────────────┘
         👍 Thumb position
```

### Recommended: Actions at Bottom

```
┌─────────────────────────────────┐
│  Title                    [⚙️]  │  ← Settings in hard zone (OK)
├─────────────────────────────────┤
│                                 │
│  Content Area                   │  ← Scrollable content
│  (scrollable)                   │
│                                 │
├─────────────────────────────────┤
│  [Action 1] [Action 2] [+]     │  ← Primary actions in green zone
├──────────┬──────────────────────┤
│  [Tab 1]  │     [Tab 2]        │  ← Tab bar in green zone
└──────────┴──────────────────────┘
```

### NOT Recommended: Actions in Middle

```
┌─────────────────────────────────┐
│  Title                    [⚙️]  │
├─────────────────────────────────┤
│  Progress bars                  │
├─────────────────────────────────┤
│  [Action 1] [Action 2] [+]     │  ← NG: Hard to reach with thumb
├─────────────────────────────────┤
│  Content List                   │
│  (scrollable)                   │
├──────────┬──────────────────────┤
│  [Tab 1]  │     [Tab 2]        │
└──────────┴──────────────────────┘
```

---

## Screen Structure

### Basic Screen with Header

```
┌─────────────────────────────────┐
│  Screen Title                   │
├─────────────────────────────────┤
│                                 │
│  Content Area                   │
│                                 │
└─────────────────────────────────┘
```

### Screen with Header Actions

```
┌─────────────────────────────────┐
│  ←  Title              [⚙️] [+] │
├─────────────────────────────────┤
│                                 │
│  Content Area                   │
│                                 │
└─────────────────────────────────┘
```

### Tab-based Navigation

```
┌─────────────────────────────────┐
│  Title                    [⚙️]  │
├─────────────────────────────────┤
│                                 │
│  Content Area                   │
│                                 │
├──────────┬──────────────────────┤
│  [Tab 1]  │     [Tab 2]        │
└──────────┴──────────────────────┘
```

## Components

### Progress Bar

```
💧 Water        1.2L / 2.0L
████████████░░░░░░  60%

☕ Caffeine     150mg / 300mg
██████████░░░░░░░░  50%
```

### Button Grid (Text Only)

```
┌─────────────────────────────────┐
│  [水]  [コーヒー] [紅茶] [緑茶] │
│  [ジュース]   [牛乳]   [+]     │
└─────────────────────────────────┘
```

### Button Grid (Icon + Text)

```
┌─────────────────────────────────┐
│  [💧水]  [☕コーヒー] [🍵紅茶]  │
│  [🍵緑茶] [🧃ジュース] [🥛牛乳]│
└─────────────────────────────────┘
```

### List with Section Headers

```
┌─────────────────────────────────┐
│  📅 12月27日（Today）           │
│  ├─ Coffee 250ml (90mg) 10:30  │
│  ├─ Water 350ml         09:15  │
│  └─ Green Tea 150ml     08:00  │
│                                 │
│  📅 12月26日                    │
│  ├─ Milk 250ml          20:00  │
│  └─ Coffee 350ml        14:00  │
│                                 │
│  🔒 12月20日 - Pro              │
│  （Tap to unlock）              │
└─────────────────────────────────┘
```

### Settings List

```
┌─────────────────────────────────┐
│  Goals                          │
│  ├─ Water Goal      2,000ml  > │
│  ├─ Caffeine Limit    300mg  > │
│  └─ Bedtime           22:00  > │
│                                 │
│  Display                        │
│  └─ Unit                 ml  > │
│                                 │
│  Account                        │
│  └─ Subscription            >  │
└─────────────────────────────────┘
```

## Modals & Overlays

### Bottom Sheet

```
┌─────────────────────────────────┐
│                                 │
│  （Semi-transparent overlay）   │
│                                 │
├─────────────────────────────────┤
│  Add Coffee                     │
│                                 │
│  ┌─────────────────────────────┐│
│  │          150ml              ││
│  └─────────────────────────────┘│
│  ┌─────────────────────────────┐│
│  │          250ml              ││
│  └─────────────────────────────┘│
│  ┌─────────────────────────────┐│
│  │          350ml              ││
│  └─────────────────────────────┘│
│                                 │
│         [Cancel]                │
└─────────────────────────────────┘
```

### Center Modal

```
┌─────────────────────────────────┐
│                                 │
│  ┌─────────────────────────────┐│
│  │   Modal Title               ││
│  │                             ││
│  │   Content here              ││
│  │                             ││
│  │   [Cancel]    [Confirm]     ││
│  └─────────────────────────────┘│
│                                 │
└─────────────────────────────────┘
```

### Alert Dialog (iOS Style)

```
┌─────────────────────────────────┐
│                                 │
│  ┌─────────────────────────────┐│
│  │         Warning             ││
│  │                             ││
│  │  This may affect your       ││
│  │  sleep quality.             ││
│  │                             ││
│  ├─────────────────────────────┤│
│  │ [Cancel]  │  [Record]       ││
│  └─────────────────────────────┘│
│                                 │
└─────────────────────────────────┘
```

## Onboarding

### Welcome Screen

```
┌─────────────────────────────────┐
│                                 │
│         App Name                │
│                                 │
│    "Tagline goes here"          │
│                                 │
│  ✓ Feature point 1              │
│  ✓ Feature point 2              │
│  ✓ Feature point 3              │
│                                 │
│                                 │
│  ┌──────────────────────────────┐
│  │           Next               │
│  └──────────────────────────────┘
│           Skip                  │
└─────────────────────────────────┘
```

### Input Screen with Slider

```
┌─────────────────────────────────┐
│                                 │
│     Set your daily goal         │
│                                 │
│        💧 2,000 ml              │
│     ◀─────────○─────────▶       │
│                                 │
│  Recommended: 2L per day        │
│                                 │
│  ┌──────────────────────────────┐
│  │           Next               │
│  └──────────────────────────────┘
│           Skip                  │
└─────────────────────────────────┘
```

### Time Picker Screen

```
┌─────────────────────────────────┐
│                                 │
│     What's your bedtime?        │
│                                 │
│        ⏰ 22:00                 │
│     ┌──────────────────┐        │
│     │   Time Picker    │        │
│     └──────────────────┘        │
│                                 │
│  We'll remind you about         │
│  caffeine 6 hours before        │
│                                 │
│  ┌──────────────────────────────┐
│  │         Start                │
│  └──────────────────────────────┘
│           Skip                  │
└─────────────────────────────────┘
```

## Feedback

### Toast Notification (Top)

```
┌─────────────────────────────────┐
│  ┌─────────────────────────────┐│
│  │ ☕ +90mg recorded           ││ ← Toast
│  └─────────────────────────────┘│
├─────────────────────────────────┤
│                                 │
│  Regular screen content         │
│                                 │
└─────────────────────────────────┘
```

### Toast Notification (Bottom)

```
┌─────────────────────────────────┐
│                                 │
│  Regular screen content         │
│                                 │
├─────────────────────────────────┤
│  ┌─────────────────────────────┐│
│  │ ✓ Saved successfully        ││ ← Toast
│  └─────────────────────────────┘│
│  [Tab 1]  │     [Tab 2]        │
└──────────┴──────────────────────┘
```

## Swipe Actions

### Swipe to Delete

```
Normal state:
│  Coffee 250ml (90mg) 10:30    │

Swiped left:
│  Coffee 250ml (9... [Delete]  │
                     ↑ Red button
```

## Empty States

### Simple Text

```
┌─────────────────────────────────┐
│                                 │
│                                 │
│      No records yet             │
│                                 │
│                                 │
└─────────────────────────────────┘
```

### With Illustration

```
┌─────────────────────────────────┐
│                                 │
│           💧                    │
│                                 │
│   Start tracking your drinks!   │
│                                 │
│   Tap a button below to add     │
│   your first record.            │
│                                 │
└─────────────────────────────────┘
```
