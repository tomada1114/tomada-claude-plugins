# Question bank

Rounds in order; skip a round the platform excludes or the inputs already answer.
Rounds marked **(UX stage)** are skipped when `ui-ux-designing` runs afterwards, as it
does in `kicking-off-apps`; rounds marked **(visual stage)** are skipped when a visual
design stage (`refero-design`) follows.

**Round 0 — Product and scope** (all; hearing mode starts here)
- Who uses it, in what situation, and what do they do today instead?
- The core interaction: the one thing done most often
- What would make the first version a success — an observable outcome
- Working title (it becomes the repository name)
- What is explicitly out for the first version (seed the non-goals)

**Round 1 — Features and behavior** (all)
- Per MVP feature: inputs, limits, defaults, what happens on save / delete / undo
- Recurring or time-based behavior: schedules, reminders, date boundaries
- Import / export, and what happens to data on uninstall or account deletion

**Round 2 — Desktop specifics** (desktop)
- Window model: single main window / multiple documents / menu-bar only
- Launch at login, background activity, notifications
- Keyboard-first operation: which actions need shortcuts
- OS integrations: files, clipboard, other apps, system permissions each implies

**Round 3 — Mobile specifics** (mobile)
- Primary action placement, gestures, haptics, offline use

**Round 4 — Error handling and validation** (all) **(UX stage)**
- Destructive actions: immediate / undo toast / confirmation
- Error display: inline / toast / alert; retry behavior
- Validation timing: as you type / on blur / on submit

**Round 5 — Accessibility** (all with UI) **(UX stage)**
- Target level (WCAG AA or platform equivalent), screen reader and keyboard coverage

**Round 6 — Visual** (all with UI) **(visual stage)**
- Light / dark / follow system; brand colors that already exist

**Round 7 — Business rules** (all)
- Free vs paid limits, quotas, pricing that changes behavior
- Calculations and their edge cases (overflow, rounding, time zones)

**Round 8 — Data and integration** (apps with data or a backend)
- Local-only vs synced; accounts and authentication
- Third-party services (APIs, LLMs, payments) and what happens when they fail
- For APIs: pagination, error format, versioning
