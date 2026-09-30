# Desktop and web wireframe patterns

Desktop windows are resizable and keyboard-driven: state the minimum window size, what
collapses first when it shrinks, and the shortcut for every primary action. On macOS
the menu bar carries every command, so a toolbar button is a shortcut to a menu item,
never the only way in.

## macOS: sidebar + content (+ inspector)

```
┌──────────────────────────────────────────────────────────────┐
│ ● ● ●   [≡]  Library                     [＋] [⌕ Search    ] │ ← toolbar: primary action ⌘N
├──────────────┬───────────────────────────────┬───────────────┤
│ ▾ Sources    │ Item title             Date   │ Inspector     │
│   All    12  │ ───────────────────────────── │ Name  [     ] │
│   Today   3  │ ▸ Morning run          09:12  │ Tags  [     ] │
│ ▾ Tags       │   Reading              08:40  │               │
│   Work       │   …                           │ [Delete ⌫]    │
│              │                               │               │
│ min 180pt    │ min 320pt, flexible           │ 260pt, ⌥⌘I    │
└──────────────┴───────────────────────────────┴───────────────┘
Shrinking: inspector hides first, then the sidebar collapses (⌃⌘S restores).
```

## macOS: menu-bar app popover

```
        ◉ ← status item (template image, 18pt)
 ┌──────────────────────────────┐
 │ Today            3 / 5  [⚙]  │
 │ ──────────────────────────── │
 │ ☑ Stretch                    │
 │ ☐ Water           [Log]      │
 │ ──────────────────────────── │
 │ Open Main Window…   ⌘O       │
 │ Quit                ⌘Q       │
 └──────────────────────────────┘
 Width 300pt fixed; closes on focus loss; Esc closes.
```

## macOS: settings window

```
┌───────────────────────────────────────────┐
│ ● ● ●        General   Shortcuts   Account │ ← toolbar tabs, ⌘, opens
├───────────────────────────────────────────┤
│  Launch at login        [✓]               │
│  Reminder time          [ 21:00 ▾ ]       │
│  Appearance             (•) System ( ) … │
└───────────────────────────────────────────┘
Changes apply immediately; no Save button.
```

## Web: app shell with responsive breakpoints

```
≥1024px                                   <768px
┌──────┬──────────────────────────┐       ┌──────────────────┐
│ Logo │ Page title     [Primary] │       │ ≡  Title   [＋]  │
│ Nav  ├──────────────────────────┤       ├──────────────────┤
│ ▸ A  │ Filters  [____] [▾]      │       │ Card             │
│   B  │ ┌──────┬──────┬──────┐   │       │ Card             │
│   C  │ │ Card │ Card │ Card │   │       │ Card             │
│      │ └──────┴──────┴──────┘   │       │                  │
└──────┴──────────────────────────┘       └──────────────────┘
Nav becomes a drawer below 768px; the primary action stays in the header.
```

## States every screen shows

Draw each screen's empty, loading, and error states next to the populated one — as small
variants, not full copies:

```
Empty:   [ illustration ]  "No habits yet"  [Add your first habit ⌘N]
Loading: skeleton rows ×3 after 300ms; nothing before that
Error:   inline banner "Couldn't save — Retry"  (content stays visible)
```
