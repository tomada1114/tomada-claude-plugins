---
name: greeting-generator
description: Write a greeting in a target language at a specified register, with the usage constraints a dictionary entry omits — time-of-day window, seniority assumptions, regional variation. Use when drafting localized welcome copy, onboarding strings, or greetings for an international audience.
---

# Greeting Generator

Single-file skill: no `references/`, no `scripts/`, no `assets/`. Everything the model needs is here.

## Procedure

1. Settle language, register (formal / neutral / casual), and channel (spoken, written, UI string). Ask only for what the request left open.
2. Emit the greeting, plus romanization when the script is non-Latin.
3. State the constraint that makes it wrong elsewhere — the hour range it stops working, the seniority gap it assumes, the region that would hear it as odd.
4. Give one alternative at the adjacent register, and say what flips the choice.

Step 3 is the whole point. A translation is free; knowing that おはようございます stops being correct around 11am is not.

## Output shape

```
おはようございます (ohayō gozaimasu) — "good morning", formal
Constraint: workplace use ends ~11am; after that こんにちは.
Adjacent: おはよう — same word minus the honorific, peers only.
```
