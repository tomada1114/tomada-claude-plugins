# Judge brief (calibration)

Fill the two slots and send as the whole prompt to a `worker` sub-agent. Add nothing
about where the examples came from.

```text
You are applying a rubric to pieces of work so that the rubric itself can be measured
against a person's past decisions. Your verdicts are compared with theirs afterwards;
the comparison is only meaningful if each verdict follows the rubric as written, so
judge every example on its own and do not balance the number of passes and fails.

<rubric>
{{RUBRIC_MD}}
</rubric>

<examples>
{{BLIND_JSONL_SLICE}}
</examples>

Each example is one JSON object with "id", "input" (what was asked for) and "output"
(what was produced). For every example, decide PASS or FAIL by the rubric.

Reply with JSON Lines only, one object per example, in the order given:
{"id": "<id>", "verdict": "PASS" | "FAIL", "reason": "<the rubric condition that decided it, one sentence>"}

If an example cannot be judged because the rubric does not cover it, answer FAIL and
say so in the reason.
```
