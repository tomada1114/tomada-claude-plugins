---
name: evolving-skills
description: >-
  Improve skills automatically from evidence, with no approval step: record what went
  wrong when a skill ran (the user corrected its output, its self-check failed, a
  standing instruction was given), act only on what has recurred, make one change in a
  staging copy, and commit it only when a mechanical gate shows the skill got no worse
  (path guard, size budget, validators, the skill's eval cases before and after).
  A failed change never reaches the real files. Also calibrates an LLM judge against
  the user's past accept and reject decisions before the judge is trusted. Use when
  skill-driven work has just ended with corrections or a failed self-check, or when
  asked to learn from feedback, tune or auto-improve a skill, see what the automatic
  runs did, revert an automatic change, or calibrate a judge. Also runs unattended
  from a session-end hook. Not for building or fully reviewing a skill
  (creating-agent-skills) or restructuring many assets (rethinking-prompt-assets).
argument-hint: "[harvest <digest.json> | improve [skill] | calibrate <skill> <judge> | status | revert <commit>]"
metadata:
  platforms: claude-code
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/signals.py:*), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/gate.py:*), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/calibrate_judge.py:*), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/session_digest.py:*), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/auto_run.py:*)
---

# Evolving skills

A skill's author finds out it is wrong when the user says "not like that". The usual
repair is a line added on the spot, which fits that one incident, is never tested
against the cases the skill already handled, and is never removed. This skill replaces
the on-the-spot edit with a loop that has a memory and a gate: evidence is recorded
first, a change is made only for what has recurred, and the change lands only when the
skill measurably got no worse.

The user has approved this loop to run without asking: an edit that passes the gate is
committed, and git history is the undo. Two things stay outside that approval, because
they are how the loop could quietly weaken itself or reach other people: a change that
rewrites or removes an existing check (the gate reports it as `blocked`), and anything
that leaves this machine (push, publishing a plugin, syncing tiers). Report those and
leave them to the user.

## Contract

**Input:** a mode, or nothing. With nothing, or after work in this session: `harvest`
this session, then `improve`.

| Mode | Does |
|---|---|
| `harvest [digest.json]` | Record signals from this session, or from a transcript digest when run headless |
| `improve [skill]` | Act on promotable signals: one change per signal group, gated, committed |
| `calibrate <skill> <judge>` | Measure a judge against labelled examples; write its calibration file |
| `status` | What the ledger holds, what is blocked and waiting for the user, what the automatic runs did |
| `revert <commit>` | Undo a landed change and mark its signals |

**Output:** rows in the ledger `${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/evolving-skills/signals.jsonl`;
a run directory under `runs/` per attempted change, holding the staging copy and
`verdict.json`; one git commit per landed change; a closing report.

**Scripts** (run them, do not read them; each prints JSON and documents itself with `--help`):
`scripts/signals.py` (ledger), `scripts/gate.py` (stage, check, land, revert),
`scripts/calibrate_judge.py`, `scripts/session_digest.py`, `scripts/auto_run.py`
(the session-end hook and its switch).

## Harvest

Record every place the session shows a skill falling short, as one signal each:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/signals.py add --skill <name> --kind <kind> --key <slug> \
  --summary "<what happened, one sentence>" --evidence "<the user's words, or the failed check>" \
  --session <session id> --source <user|self-check|gate|review> [--explicit]
```

The session id is `${CLAUDE_SESSION_ID}` for this session, or the digest's `session_id`
when harvesting from a digest. What counts, how to choose the `key` so the same problem gets the same key next time,
and how to read a headless digest: [references/harvest.md](references/harvest.md). Record
all of them, including weak and uncertain ones; the promotion rule does the filtering,
and a signal left out can never recur. Harvest changes no skill.

## Improve

1. **Pick.** `signals.py promotable --json`. A group is promotable when the user
   stated it as a standing rule, or it appeared in two separate sessions. Everything
   else waits: one incident does not say whether the skill or the situation was
   unusual. Work the groups one at a time, each as its own change.
2. **Diagnose** against the skill's current text: missing rule, wrong rule, a rule
   that exists but is not followed, a step that belongs in a script, or nothing wrong
   with the skill. Decide where the fix belongs, and look for what to remove before
   what to add. The protocol and the placement table:
   [references/improve-protocol.md](references/improve-protocol.md).
3. **Stage.** `gate.py stage --root <git root> --path <skill dir>` copies the
   committed skill into a run directory and refuses when the path has uncommitted
   work, which belongs to the user: mark the signals `deferred` and move on. All
   edits from here go to the `head/` copy the command prints.
4. **Write the case first.** Add an eval case under `head/.../evals/` that reproduces
   the signal and fails on the unchanged skill; the gate checks that it did. A change
   with no case that needed it is a guess. Case format and what an isolated eval run
   cannot see: [references/gate-and-evals.md](references/gate-and-evals.md).
5. **Make the one change** in `head/`.
6. **Check.** `gate.py check --run <run>`, then once more with `--final` when it
   passes, which adds the holdout cases. Act on the verdict:

   | Verdict | Meaning | Do |
   |---|---|---|
   | `pass` | No check weakened, validators no worse, eval no worse, the new case went from failing to passing | `gate.py land`, mark signals `applied` with the commit |
   | `fail` | The skill got worse, or the case did not need the change | Read the reasons, try one different change in a fresh stage. After the second failure mark `rejected` and stop |
   | `blocked` | The change rewrites or removes an existing check, breaks the size budget, or copies wording from an eval prompt | Mark `blocked` with the run path. The run directory is the proposal; the user decides |
   | `unmeasured` | The skill has no eval case that exercises this | Go back to step 4. `land --allow-unmeasured` is only for changes no case can exercise, named in the protocol |
   | `inconclusive` | The eval could not finish (cost ceiling, rate limit, validators missing) | Mark `deferred`; retrying later is fine |

7. **Land.** Write the commit message to a file in the run directory in the protocol's
   format, with the signal ids in it, then `gate.py land --run <run> --message-file <file>`.
   It re-checks that nothing moved since staging, copies the change into the real
   tree, and commits only those files.

A change is never edited into the real skill directory directly, and never committed
around the gate: the staging copy is what makes a failed attempt cost nothing.

## Calibrate, status, revert

- **Calibrate.** A judge (a rubric applied by a model) may stop a skill's output or
  score an eval only after it agrees with the user's past decisions on labelled
  examples. Until then it is advisory. Procedure and thresholds:
  [references/judge-calibration.md](references/judge-calibration.md).
- **Status.** `signals.py stats --json`, `signals.py list --status blocked --json`, and
  `auto_run.py status`. Lead with what is blocked and waiting for the user.
- **Revert.** `gate.py revert --root <git root> --commit <sha>`, then
  `signals.py set --status reverted` on that commit's signals. A reverted group needs
  new signals before it is tried again.

## Delegation

Tiers are named by agent; what each one costs and when to use it is in the
`orchestrating-models` skill. The main session, or the headless `executor` run, does
the diagnosis and the edit, because they depend on having read the skill. Spawn only:

- one `worker` per batch of blind examples during `calibrate`, with
  [references/agents/judge.md](references/agents/judge.md);
- one `architect` when a group has failed the gate twice and the user asks for another
  attempt. It gets the two `verdict.json` files and the signals, and returns a diagnosis.

At most two spawns per run. The eval runs inside `gate.py check` are separate
processes, not spawns.

## Unattended runs

The session-end hook starts `harvest` on the cheapest tier and `improve` on the
`executor` tier, each with a daily cap and a budget; setup, the caps and the switch:
[references/auto-run.md](references/auto-run.md). In an unattended run, finish every
promotable group before ending: staging, checking and landing need no go-ahead. End
the turn early only for a `blocked` verdict (record it and continue with the next
group) or when the path has uncommitted work. Close with one line per group: signal
ids, verdict, commit or run path.

## Resources

- [references/harvest.md](references/harvest.md): signal kinds, choosing keys, reading a digest. Read at Harvest.
- [references/improve-protocol.md](references/improve-protocol.md): diagnosis categories, where a fix belongs, pruning, the commit message format, which changes may land unmeasured. Read at Improve step 2.
- [references/gate-and-evals.md](references/gate-and-evals.md): what each gate step checks, protected paths, eval case format, tags, isolation limits, cost. Read at Improve step 4 and when a verdict is unclear.
- [references/judge-calibration.md](references/judge-calibration.md): labelled examples, the blind run, thresholds, what an advisory judge may do. Read at Calibrate.
- [references/auto-run.md](references/auto-run.md): the session-end hook, tiers, caps, logs, switching it off. Read when setting up or debugging unattended runs.
- [references/agents/judge.md](references/agents/judge.md): the judge brief for `calibrate`.
