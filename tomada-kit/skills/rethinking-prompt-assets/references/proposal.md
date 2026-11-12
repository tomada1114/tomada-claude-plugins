# The proposal, its approval, and applying it

## Table of Contents

- [Moves](#moves)
- [proposal.md](#proposalmd)
- [Asking for approval](#asking-for-approval)
- [The ledger](#the-ledger)
- [Applying approved moves](#applying-approved-moves)

## Moves

The unit of approval is the **move**: one structural change, together with every
edit needed to leave the estate consistent after it, that can be approved, declined
and reverted on its own. The user says yes or no to moves, never to individual line
edits and never to the proposal as a whole.

| Kind | What it is |
|---|---|
| `delete` | Remove an asset. Includes repointing or removing every reference to it. |
| `merge` | Fold two or more assets into one. Names the survivor. |
| `split` | Divide one asset along a boundary. Names both results. |
| `rebuild` | Replace an asset with one written from the blind design's unit, not edited from the old text. |
| `restructure` | Keep the asset, change its shape: move content between body, references and scripts, reorder or remove phases. |
| `reroute` | Change a flow: drop, reorder or combine stages across assets; change a hand-off artifact; change how the contexts in a stage coordinate (who returns what to whom, what is shared mid-run). |
| `retier` | Change which tier a hand-off uses, or change the tier set. |
| `relocate` | Move a rule between a memory file and a skill. |
| `reword` | Wording fixes within one document. One `reword` move per document, however many lines. |
| `new` | Add an asset for a job nothing covers. |

Sizing rules:

- Two changes that only make sense together are one move. Two changes either of which
  stands alone are two moves, with `Requires` when order matters.
- A move never mixes a structural change with unrelated wording fixes in the same
  document; the wording goes in that document's `reword` move, which then
  `Requires` the structural one.
- Keeping an asset is a verdict, not a move. It is recorded under "Examined and kept".

## proposal.md

```
# Rethink: <scope> (<date>)

Scope: <what was in scope and how it was resolved>
Evidence: usage window <first>..<last>, <n> transcripts; <n> assets read
Blind design: <blind | not blind: reason>
Working tree at start: <clean | the files that already had uncommitted changes>

## Summary
<A few sentences: the shape the blind design proposed, where the estate already
matches it, and the handful of moves that matter most.>

## Moves

| ID | Kind | Targets | One line | Effort | Requires |
|---|---|---|---|---|---|

### M01 <kind>: <targets>
- Change: <what will exist afterwards>
- Why: <the check ids (X1–X9) or the blind-design unit behind it>
- Evidence: <path:line for each claim; usage numbers with the window>
- Cost of leaving it: <what goes wrong or is paid today, and how often>
- Cost of moving: <files touched, what the user must relearn, what could break>
- Blast radius: <every asset, memory file or published copy that names a
  target, from the reference graph, with path:line>
- Revert: <what copying the snapshot back restores, and anything it cannot (a remote
  copy already synced, a follow-up already run)>
- Confidence: high | medium | low, and what would raise it
- Requires: <move ids, or none>

## Questions only the user can answer
<An asset with no evidence of use and no job in the needs document; a job the needs
document may have missed. One line each, phrased so a yes or no decides a move.>

## Design differences not acted on
<Where the blind design differs from the estate but no cost was found in the estate's
current form. One line each, so the difference is on record without a move.>

## Examined and kept
<Each in-scope asset or flow that was checked and left alone, with what was checked.>

## Declined before
<Moves in the ledger that this run found again, with the date and the reason given.
Listed, not re-proposed, unless the evidence has changed; then say what changed.>
```

Order the moves by what they unblock, then by cost of leaving it. Every in-scope
asset appears exactly once across Moves, Questions, and Examined and kept.

## Asking for approval

Show the Summary and the Moves table in the conversation, with the path to
`proposal.md`, then ask which moves to apply with `AskUserQuestion`. Offer a
recommended set (the moves with high confidence and evidence of a present cost) as
the first option, and put the Questions to the user in the same call. Wait for the
answer.

Approval covers exactly the named moves as written. A move whose `Requires` was not
approved is not applied; say so and ask about the pair. Declining needs no reason,
but record one if the user gives it.

## The ledger

`decisions.json`, one level above `runs/`, is a list of:

```json
{"date": "2026-11-10", "id": "M04", "kind": "merge", "targets": ["a", "b"],
 "one_line": "…", "decision": "approved | declined | deferred",
 "reason": "…", "applied": true}
```

Append after the approval round and update `applied` as moves land. Phase 0 reads it
so that a declined move is not raised again on the next run.

## Applying approved moves

1. Order the approved moves by `Requires`. Apply one move at a time, and finish all
   of its edits, including its blast radius, before starting the next, so that
   stopping between moves always leaves a consistent estate.
2. Before a move's first edit, copy every file and directory it will change or
   remove to `$RUN/snapshots/<move-id>/`, keeping paths relative to the configuration
   root. This is what makes a move revertable: git cannot be relied on, because
   files in the estate often carry uncommitted work, and a snapshot preserves that
   work exactly as it was. To revert a move, copy its snapshot back.
3. Do each move with the tool that owns that kind of work:
   - `rebuild`, `new`, `split`, `merge`: write the result with the
     `creating-agent-skills` skill's Building steps, from the blind design's unit and
     the facts worth keeping from the old text. Start from the unit, not from the old
     file. When the result keeps the name of an asset it replaces, build it under
     `$RUN/staging/<name>/` and validate it there; it is swapped in at step 5.
   - `restructure`: edit in place; validate with that skill's validators.
   - `reword`: apply with the `auditing-prompt-docs` rules, then re-run its linter on
     the document.
   - `retier`: change every place the estate's model-assignment source lists as
     needing to agree, in one move.
   - `delete`: repoint or remove the references first. Do not remove the asset yet.
4. A file that already had uncommitted changes at the start of the run holds the
   user's work in progress. Its snapshot keeps that work, so an edit can proceed.
   When a move would remove or wholly replace such a file, name it in the step 5
   confirmation so the user sees that uncommitted work is among what goes.
5. Removal and swap come last, once, for all `delete`, `merge` and `rebuild` moves
   together: list the paths to be removed and the staged replacements to be moved
   into place, confirm the list with the user through `AskUserQuestion`, then do it in one step. Until then the
   old assets stay in place and keep working.
6. After the last move, re-run the collector and each touched skill's validators.
   Report any name that still resolves to a removed asset as unfinished work, with
   its location.
7. Make no commit and no remote write unless the user asks. Close with what was
   applied, what was not and why, the validator results, and the follow-ups the moves
   created (see `claude-code.md`): copies of the changed assets held by a published
   plugin, or by repositories that receive synced tier
   definitions, and a setting an approved move depends on (agent teams).
