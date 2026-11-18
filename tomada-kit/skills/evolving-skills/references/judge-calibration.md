# Calibrating a judge

A judge is a rubric applied by a model. Before it is allowed to send work back or to
score an eval case, it has to show that it decides the way the user does. A rubric that
passes everything looks exactly like a good rubric until it is tried on work the user
rejected.

## Files

In the skill, under `evals/calibration/<judge>/`:

| File | Holds |
|---|---|
| `rubric.md` | The criteria, as concrete PASS and FAIL conditions. Names what the judge is shown (the request and the output) |
| `examples.jsonl` | One row per past decision: `{"id", "input", "output", "label": "accept" \| "reject", "source", "note"}` |
| `calibration.json` | Written by `calibrate_judge.py score`. Never edited by hand |

## Examples come from the user's decisions

The only valid labels are decisions the user made: output they accepted as it was
(`accept`), output they rewrote, rejected or sent back (`reject`, with the version
before their change as `output`). Sources worth mining: a skill's own feedback log,
the diff between what a skill handed off and what was published, signals of kind
`correction` in the ledger.

Do not write examples to fill a gap, and do not label by your own reading: a judge
calibrated on invented examples agrees with the inventor. With fewer than 20 examples
or fewer than 5 of either label the judge stays advisory, and that is the correct
state for a new skill.

## Procedure

```bash
D=<skill>/evals/calibration/<judge>
python3 ${CLAUDE_SKILL_DIR}/scripts/calibrate_judge.py check-examples --examples $D/examples.jsonl
python3 ${CLAUDE_SKILL_DIR}/scripts/calibrate_judge.py blind --examples $D/examples.jsonl --out <run>/blind.jsonl
# judge the blind file in batches (below), collecting <run>/verdicts.jsonl
python3 ${CLAUDE_SKILL_DIR}/scripts/calibrate_judge.py score --examples $D/examples.jsonl \
  --verdicts <run>/verdicts.jsonl --rubric $D/rubric.md --out $D/calibration.json
```

Judging: spawn `worker` sub-agents with the judge brief (`references/agents/judge.md`, linked from SKILL.md), one per batch of at
most 20 examples, each given the rubric and a slice of the blind file and nothing
else. The blind file has no labels and a shuffled order; the brief must not say which
skill version, which session, or what share is expected to pass. Save each reply's
JSON lines to `verdicts.jsonl`; a `worker` writes no files.

Sanity check from the other side when the skill has eval cases: an output produced
with the skill disabled, or by a deliberately weakened copy, should fail the rubric
more often than the skill's own output. A judge that cannot tell them apart is not
measuring the skill.

## Thresholds

`trusted` requires all of: at least 20 examples with at least 5 of each label;
agreement with the user at or above 0.8; false-accept rate at or below 0.1 (of the
outputs the user rejected, the share the judge passed). The false-accept rate is the
one that matters for a gate: a strict judge wastes a retry, a lenient one lets through
what the user would have sent back.

The calibration records the hash of the rubric and of the examples. Editing either
makes `calibrate_judge.py status` report `advisory` until `score` is run again, so a
rubric cannot be loosened and keep its standing.

## What each standing allows

| | `advisory` | `trusted` |
|---|---|---|
| In a skill's self-check | Its findings are listed for the main session, which decides | May send the output back for one fix round |
| As an `llm` grader in a `gate` case | `weight: 0.01` only | Normal weight |
| As the only grader of a case | No | No. Pair it with a `regex` or a route grader |

When calibration fails, read `disagreements` in the output. Rewrite the rubric where
its wording explains the misses, as general conditions and not as descriptions of the
missed examples, then run `blind` and `score` again. Two rounds; after that the judge
stays advisory and the disagreements are recorded as a `review` signal.
