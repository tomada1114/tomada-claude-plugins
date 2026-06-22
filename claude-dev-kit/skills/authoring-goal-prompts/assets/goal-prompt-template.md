# `/goal` prompt scaffold

This is a **scaffold to clone and fill**, not a form to complete in full. Include a section only
when it removes ambiguity or changes the goal session's behavior. Delete the rest. A short prompt
that nails GOAL / DONE WHEN / VERIFY / CONSTRAINTS / STOP RULES beats a long one padded with the
optional sections. The bracketed notes are guidance — remove them from the final prompt.

The final prompt is plain prose with labeled sections; it does not need to be Markdown-fenced inside
itself. Use `UPPERCASE` labels so the structure is scannable.

---

## Core sections (almost always include)

```
GOAL: [One sentence. The end state, not the activity. "Every call site of getUserV1 is migrated
       to getUserV2 and the build passes" — not "work on the migration".]

DONE WHEN: [Binary, measurable, transcript-observable. Prefer ONE objective check the small
       evaluator can read off the conversation. End with a sentinel the goal session must print:
       e.g. "the goal session has run `npm test` and printed a line `GOAL_DONE: npm test exited 0`".]

VERIFY: [The exact command(s) that prove DONE WHEN, and the instruction to PRINT their output each
       time. e.g. "Run `npm test` and paste the summary line + exit code into the conversation.
       Do not claim success without showing fresh output from the latest code."]

CONSTRAINTS:
  - Scope: [What must NOT change — pulled from the project's CLAUDE.md / dev rules. e.g. "do not
    rename, refactor, or touch files outside src/api/. No unrelated cleanup."]
  - Integrity (anti-cheat): Do NOT skip, xfail, disable, or delete tests; do not weaken assertions;
    do not stub or mock to make checks pass. The implementation must genuinely satisfy the checks.

STOP RULES:
  - Stop after [N] turns (or [duration]) even if not done, and report what remains.
  - Fallbacks (no human is reachable mid-run): if [likely ambiguity] then [decision];
    if blocked or a check stays red after [M] attempts, stop and summarize the blocker.
```

## Optional sections (include only if they add signal)

```
CONTEXT: [Project facts the goal session won't infer quickly. When bundled, point to absolute paths:
       "Background and the full item list are in /Users/.../.claude/goal-prompts/<slug>/inventory.md —
       read it first." Keep inline context to a few lines; externalize anything bulky.]

BASELINE: [The current, measured state so the terminal state is reachable. e.g. "As of now `npm test`
       fails only in test/auth (3 failures); everything else is green. Do not fix unrelated failures."]

PRIORITY: [Order of attack when there are many items — usually simplest/highest-confidence first.]

PLAN: [A light approach sketch to prevent aimless exploration. Name concrete patterns to imitate:
       "Mirror the structure of src/api/products.ts." Keep it a sketch, not step-by-step micromanagement.]

OUTPUT: [Artifacts/reviewability for long runs: "Commit after each migrated module with message
       `migrate: <file>`. After each iteration print one line: `progress: X/Y done, remaining: …`."]
```

---

## Filled example (concise, chat-only)

```
GOAL: All tests under test/auth pass and `npm run lint` is clean, with no changes outside src/auth/ and test/auth/.

BASELINE: Right now `npm test test/auth` has 3 failures (token refresh, expiry, logout); lint is already clean. The rest of the suite is green.

DONE WHEN: `npm test test/auth` exits 0 AND `npm run lint` exits 0, and you have printed a final line `GOAL_DONE: auth tests + lint green` after showing both commands' fresh output.

VERIFY: Run `npm test test/auth` and `npm run lint`, pasting each command's summary + exit code into the conversation every time. Never claim success without fresh output from the current code.

CONSTRAINTS:
  - Scope: change only files in src/auth/ and test/auth/. No unrelated refactors, renames, or cleanup.
  - Integrity: do not skip/xfail/delete tests, weaken assertions, or stub to pass. Fix the real code.

STOP RULES:
  - Stop after 25 turns even if red, and report remaining failures.
  - If a failure persists after 4 distinct attempts, stop and summarize the blocker rather than thrashing.
```
