# The proposal, what gets applied, and applying it

## Table of Contents

- [Moves](#moves)
- [proposal.md](#proposalmd)
- [Choosing what to apply](#choosing-what-to-apply)
- [The ledger](#the-ledger)
- [Applying moves](#applying-moves)

## Moves

The unit is the **move**: one structural change, together with every
edit needed to leave the estate consistent after it, that can be applied, left out
and reverted on its own. A move is applied or not as a whole, never line by line.

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
- Why: <the check ids (X1–X10) or the blind-design unit behind it>
- Evidence: <path:line for each claim; usage numbers with the window>
- Cost of leaving it: <what goes wrong or is paid today, and how often>
- Cost of moving: <files touched, what the user must relearn, what could break>
- Blast radius: <every asset, memory file or published copy that names a
  target, from the reference graph, with path:line>
- Revert: <what reverting the move's commit restores, and anything it cannot (a remote
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

## Choosing what to apply

The user has approved applying moves without asking first; what they asked for in
exchange is that each applied move is well evidenced, mechanically checked, and one
revertable commit. So the proposal is sorted, not voted on.

**This run applies** a move when all hold: confidence is high; the evidence shows a
cost paid today (not only a difference from the blind design); every move it
`Requires` is also being applied; and none of its targets has uncommitted changes.

**Left for the user**, listed in the conversation with the reason for each:

- a move with medium or low confidence, or resting on a "Questions only the user can
  answer" item;
- a move the ledger shows was declined before, unless the evidence changed;
- a move the gate reports as `blocked` (it rewrites or removes an existing check,
  test, eval case or hook) or as failing;
- a move whose target holds the user's uncommitted work;
- anything outside this machine: published plugin copies, repositories that receive
  synced tier definitions, a setting the move depends on. These are follow-ups
  (`claude-code.md`), never applied here.

Show the Summary, the Moves table marked with which list each move is on, and the path
to `proposal.md`. With `report-only`, stop here. Otherwise go on to apply without
waiting; put any question only the user can answer in the closing report, where a yes
or no decides a left-over move.

## The ledger

`decisions.json`, one level above `runs/`, is a list of:

```json
{"date": "2026-11-10", "id": "M04", "kind": "merge", "targets": ["a", "b"],
 "one_line": "…", "decision": "applied | left-for-user | gate-failed | blocked | declined",
 "reason": "…", "commit": "<sha or null>", "run": "<gate run directory or null>"}
```

Append one row per move as it is sorted or lands. `declined` is recorded when the
user says no to a left-over move, or reverts an applied one. Phase 0 reads the ledger
so that a declined move is not raised again on the next run.

## Applying moves

`GATE` is `scripts/gate.py` in the `evolving-skills` skill, a sibling of this skill's
directory; its steps and verdicts are described in that skill's
`references/gate-and-evals.md`. Read those files by path: the skill itself is invoked
only by the user.

1. Order the moves to apply by `Requires`. Apply one move at a time, and finish all of
   it, including its blast radius, before starting the next, so that stopping between
   moves always leaves a consistent estate.
2. Stage the move: `GATE stage --root <configuration root> --path <target> ...` with
   every file and directory the move changes or removes. Staging refuses a path with
   uncommitted changes; that move goes to the user's list. All edits are made in the
   `head/` copy the command prints, never in the estate.
3. Do each move in the staging copy with the tool that owns that kind of work:
   - `rebuild`, `new`, `split`, `merge`: write the result with the
     `creating-agent-skills` skill's Building steps, from the blind design's unit and
     the facts worth keeping from the old text. Start from the unit, not from the old
     file. A rebuilt or new skill that produces an artifact gets its self-check and
     eval cases there.
   - `restructure`: edit in place in the copy.
   - `reword`: apply with the `auditing-prompt-docs` rules, then run its linter on
     the staged document.
   - `retier`: change every place the estate's model-assignment source lists as
     needing to agree, in one move.
   - `delete`: repoint or remove the references, and remove the asset from the copy.
4. Check: `GATE check --run <run>`, and `--final` after a pass when a touched skill
   has eval cases. `pass` lands. `unmeasured` lands with `--allow-unmeasured` when
   no touched skill has a case the move could affect, which is the usual situation
   for moves between assets; say so in the commit subject. `fail`, `blocked` and
   `inconclusive` do not land: record the verdict in the ledger with the run
   directory and move the move to the user's list. A `delete` of a skill that carries
   tests, eval cases or hooks is `blocked` by design, since it removes checks.
5. Land: write the commit message (subject `rethink <move id> <kind>: <one line>`,
   body with the Why and Evidence lines from the proposal) to a file in the run
   directory, then `GATE land --run <run> --message-file <file>`.
6. After each landed move, re-run the collector and each touched skill's validators.
   A name that still resolves to a removed asset, or a validator error the move
   introduced, means the blast radius was wrong: `GATE revert --root <root> --commit
   <sha>`, record it, and put the move on the user's list with what was missed.
7. Close with: the commits landed (move id, sha), the moves left for the user and why,
   the validator results, and the follow-ups the applied moves created (see
   `claude-code.md`): copies of the changed assets held by a published plugin or by
   repositories that receive synced tier definitions, and a setting a move depends on
   (agent teams). Nothing is pushed.
