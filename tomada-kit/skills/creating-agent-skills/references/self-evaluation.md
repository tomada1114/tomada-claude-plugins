# Self-Evaluation: Giving a Skill Its Own Criteria

A current model checks its own work without being told to. What it lacks is the
*user's* criteria: what this user sends back, which steps they consider mandatory. A
skill that writes those down as checks that can fail lets the model catch, during the
run, what the user would otherwise catch after it, and leaves a record that the
`evolving-skills` skill turns into improvements. This is not a "verify before
responding" step (`prompt-authoring.md`, PA2): it adds criteria, not a second pass.

Three loops share the same material:

| Loop | When | Runs | Weight |
|---|---|---|---|
| Self-check | During each run, before hand-off | The skill's own criteria against this one output | Light: a script and a short list |
| Gate | When the skill is changed | The skill's eval cases, committed version against changed version | Heavy, so only on change |
| Learning | After runs | Recorded misses and corrections become gated changes | Owned by `evolving-skills` |

## Table of Contents

- [The self-check contract](#the-self-check-contract)
- [Choosing the form of each criterion](#choosing-the-form-of-each-criterion)
- [When to add an independent judge](#when-to-add-an-independent-judge)
- [Hooks as enforcement](#hooks-as-enforcement)
- [Seeding eval cases](#seeding-eval-cases)
- [Review checklist](#review-checklist)

## The self-check contract

A skill that produces an artifact ends with a `## Self-check` section holding three
things, and nothing generic:

1. **Result criteria**: what makes this output acceptable to this user, each one
   observable in the output. A script where a program can decide it; otherwise at most
   five conditions written as PASS and FAIL.
2. **Route expectations**: the steps that must have happened, in order, stated as
   things visible in the session ("the linter ran after the last edit to the draft").
   Output can look right while a skipped step causes the next failure, so the two are
   checked separately.
3. **What to do with a miss**: fix and re-run the criteria, at most two rounds; then
   hand off, saying which criteria still fail. Record each miss as a signal.

```markdown
## Self-check

Before handing off:

1. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/check_output.py <artifact>`; fix what it reports.
2. Result — the summary states the decision in its first sentence; every figure has a
   source and a date; nothing in the table is repeated as prose under it.
3. Route — the source pages were opened in this session before they were cited.
4. On a miss, fix and repeat from step 1, twice at most. Report any criterion that
   still fails, and record each miss:
   `python3 ${CLAUDE_SKILL_DIR}/../evolving-skills/scripts/signals.py add --skill <name> --kind self-check-fail --key <slug> --summary "…" --source self-check --session ${CLAUDE_SESSION_ID}`
```

The `../evolving-skills` path holds for skills installed side by side in one skills
folder. A skill that ships alone (a plugin, another repository) writes the miss to a
log of its own instead and names that file in its Contract.

Rules for the section:

- A criterion comes from evidence: the gap list from Building step 2, a correction the
  user made, a failed eval case. A criterion nobody has ever needed is the model's
  default restated.
- The cap of two rounds and the report of what still fails are part of the contract.
  A loop with no cap and no exit rule is the defect checked by `OR` and by
  `rethinking-prompt-assets` X10.
- The signal line is what connects a run to later improvement.
- A skill with no artifact (a pure reference skill) has no self-check. Do not add one
  for symmetry.

## Choosing the form of each criterion

| The criterion | Form | Why |
|---|---|---|
| Can be decided by a program (format, length, required parts, forbidden strings, links resolve) | Script in `scripts/`, run in the self-check | Same answer every time, costs no judgment, and the same script can be an eval grader's target |
| Needs reading, but its conditions can be listed | PASS/FAIL list in the section, applied by the session that did the work | No extra context to pay for; enough when the criteria are concrete |
| Needs a reader who did not write the output (does it stand alone, does it sound like the user) | Independent judge, under the conditions below | The writer reads its own intent into the text |
| Must hold before an action that cannot be undone | Hook, under the conditions below | A self-check runs when the model reaches it; a hook runs regardless |

Move a criterion down this table only when the row above cannot express it. Prose
that restates a scripted check is deleted when the script lands.

## When to add an independent judge

A judge is a sub-agent that sees the request and the output, applies a rubric, and
returns findings; the main session decides and fixes. Add one only when all hold:

- the criterion needs a reader without the writer's context, and no script can decide it;
- the rubric has been calibrated against the user's own accept and reject decisions
  (`evolving-skills`, `references/judge-calibration.md`). An uncalibrated judge may
  run, but its findings are advisory: listed for the main session, never a reason to
  send work back automatically;
- a bad output is costly: it is published, sent, or expensive to redo.

Shape: one spawn, the tier named by agent (`worker` when the brief carries everything
and no tool is needed, `scout` when the judge has to open files; criteria in the
`orchestrating-models` skill), the brief in `references/agents/`, the rubric written as
PASS and FAIL conditions, the reply as findings with a location and the rubric item.
The judge gets the request as well as the output, and never the writer's notes about
what it meant to do. One fix round after the judge, not a loop.

## Hooks as enforcement

Skill text proposes; a hook enforces. Use a frontmatter hook for a rule that a program
can decide and that must not depend on the model reaching a step. The typical case is a
`PreToolUse` hook that denies a publishing or sending tool call until a marker shows the
checks passed, and returns the reason so the model can fix and retry.

Facts that shape the design (Claude Code; a skill with hooks is Claude Code only):

- A skill's hooks register when the skill is invoked and then run for the rest of the
  session, on later unrelated turns too. Match narrowly (a tool name, a path), and
  make the command exit immediately when the skill's artifact is not involved.
  `once: true` removes a hook after its first successful run.
- `${CLAUDE_SKILL_DIR}` is not expanded inside a hook `command`. Reference the script
  by `${CLAUDE_PROJECT_DIR}` in a project skill, or by a path the skill resolves and
  documents for a personal one.
- A `Stop` hook that blocks sends its `reason` to the model as the next instruction.
  Consecutive continuations are capped at eight, and the input carries
  `stop_hook_active`; check it so a condition that cannot be met does not burn the cap.
- `type: prompt` and `type: agent` hooks answer `{"ok": true}` or
  `{"ok": false, "reason": "..."}`, not the `decision` object command hooks print. A
  `prompt` hook on `Stop` costs a model call on every turn for the rest of the
  session, so it is the wrong tool for a per-run self-check; the section above does
  that job at no extra call.

## Seeding eval cases

The gate that protects automatic changes needs cases to run. Create them when the
skill is built, from the same gap list:

- Put cases in `evals/<case>/` in the `claude plugin eval` format (`prompt.md` plus
  `graders/`). Layout, grader choice and tags are in `evolving-skills`,
  `references/gate-and-evals.md`; the format and its limits in
  `evaluating-skills.md`, "claude plugin eval" (load via SKILL.md).
- Three cases minimum: tag two `gate` and one `holdout`. Each has one grader on the
  result and one on the route (the route expectations above translate directly to
  `tool_order` and `tool_used` graders).
- A self-check script and an eval grader should test the same thing by the same
  means: point a `regex` grader at what the script enforces, so the criterion is
  measured on change as well as applied at run time.
- Check that the suite measures the skill: run it once with the no-skill comparison
  and confirm the skill scores higher than no skill. A suite the baseline already
  passes will pass every change.

## Review checklist

Used by the Improving playbook's *self-evaluation* lens. Items that do not apply to
the skill (no judge, no hooks) are N-A.

### SE1: Criteria are the user's, and observable
Each self-check item names something visible in the output or the session. "Check
quality" and "make sure it is correct" are a FAIL.

### SE2: Result and route are separate
Required steps are stated as route expectations, not folded into result criteria.

### SE3: The loop is capped and has an exit
Two fix rounds at most, then hand off with what still fails.

### SE4: Misses are recorded
The self-check tells the model to record a signal. Without it nothing reaches the
learning loop.

### SE5: Mechanical criteria are scripts
A criterion a program could decide is not left as prose.

### SE6: A judge is calibrated or advisory
A judge that can send work back has a calibration file; otherwise the skill says its
findings are advisory.

### SE7: Hooks are narrow
A frontmatter hook matches only what it guards and exits at once elsewhere.

### SE8: The skill has cases the gate can run
`evals/` holds at least three cases with `gate` and `holdout` tags; missing cases are
reported as a proposal, with the gap list they would come from.
