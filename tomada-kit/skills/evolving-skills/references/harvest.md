# Harvesting signals

A signal is one observed instance of a skill falling short. It is evidence, not a
verdict: whether it becomes a change is decided later, by recurrence.

## What counts

| Kind | Record when | `--source` |
|---|---|---|
| `correction` | The user changed, rejected or redid something the skill produced, or said it was wrong | `user` |
| `instruction` | The user stated how the skill should behave from now on. Add `--explicit` only when they said it as a rule ("always", "from now on", "never again"), not when they asked for one result to be different | `user` |
| `self-check-fail` | The skill's own self-check found a miss and the output had to be fixed before hand-off | `self-check` |
| `friction` | The skill's instructions caused a retry, a tool error, a wrong path, or a question the skill should have answered | `review` |
| `unused-instruction` | A step or a reference the skill prescribes was skipped with no loss | `review` |

Do not record: a correction to the content of the work that no skill instruction could
have prevented (a fact only the user knew), a change of mind about the task itself,
or anything about a skill that was not loaded in the session.

Attribute a signal to the skill whose instructions governed the step that went wrong.
When two skills were involved and the cause is unclear, record it against the one
that produced the artifact the user corrected.

## Choosing the key

Recurrence is counted per skill and key, so the key names the underlying problem, not
the incident. Two sessions that hit the same problem must end up with the same key.

- Before adding, list what exists: `signals.py list --skill <name> --json`. Reuse an
  existing key when the problem is the same, even if the wording of the incident differs.
- Name the behavior, in the skill's terms: `skips-lint-before-showing`,
  `summary-too-long`, `asks-for-already-known-path`.
- Avoid keys that describe the topic of the work (`kindle-article`) or the fix
  (`add-length-rule`). A key that names the fix prejudges the diagnosis.

<example>
The user said, in two sessions, "the report repeats the table in prose" and "again a
summary under the table". Both are `--key restates-table-in-prose`. The second makes
the group promotable.
</example>

## Evidence

`--evidence` carries what a later run needs to diagnose without the transcript: the
user's words (quoted, trimmed), or the check that failed and its output. `--summary` is
one sentence saying what the skill did and what was wanted instead.

## From a digest (headless harvest)

`harvest <digest.json>` runs without the conversation. The digest, written by
`scripts/session_digest.py`, lists the skills used and the person's messages after the
first skill use, truncated.

1. Read the digest and the SKILL.md of each skill in `skills_used`.
2. For each follow-up message, decide whether it is a signal by the table above. Most
   follow-ups are the next request, not a correction; record only what the text
   supports, and say so in the evidence when the cut-off text leaves it uncertain.
3. Add each signal with `--session` set to the digest's `session_id`.
4. Finish with one line: the number of signals added per skill. Edit nothing.
