# Scrutiny checklist

Run over the whole draft after every round — every feature section, not only the ones
the round touched. Each hit becomes a question or an Open question entry.

| ID | Look for | Example finding |
|---|---|---|
| S1 | Two statements that cannot both hold | "works offline" and "shared lists update live" |
| S2 | An object with an incomplete lifecycle — created but never edited, deleted, archived, exported | habits can be added, nothing says how one is removed or what happens to its history |
| S3 | A state with no behavior — first run, empty, limit reached, error, offline, permission denied | the dashboard with zero entries |
| S4 | A value left vague — "fast", "some", "a few", "large" — where an implementer needs a number | "reminders a few minutes before" |
| S5 | A feature that does not trace to the core interaction | social sharing in a single-user tracker |
| S6 | A non-goal nobody wrote down that an implementer would plausibly build | sync across devices, accounts, notifications |
| S7 | A requirement the template or platform cannot meet as-is, or can only meet by a hard-to-reverse choice (a server, a sandbox exception, a paid API) | global hotkeys in a sandboxed Mac app |
| S8 | Data questions: where it lives, how long, who can see it, what happens on uninstall or account deletion, migration when the format changes | |
| S9 | Scale and time: behavior at 10× the expected volume, across time zones and date boundaries, with long text or many items | streak counting across midnight and DST |
| S10 | An acceptance condition nobody could check — "intuitive", "works correctly" | |
| S11 | Money, legal, or safety exposure: payments, personal data, health claims, third-party terms | |

When the draft passes every row with nothing that would change scope or behavior, say
so and offer sign-off.
