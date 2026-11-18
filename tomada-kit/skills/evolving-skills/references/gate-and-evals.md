# The gate and the eval cases

`scripts/gate.py check` decides whether a staged change may land. Its thresholds are
constants in the script, fixed before any run, so a result cannot be argued into a pass.

## Table of Contents

- [What each step checks](#what-each-step-checks)
- [Protected paths](#protected-paths)
- [Eval cases](#eval-cases)
- [What an eval run cannot see](#what-an-eval-run-cannot-see)
- [Scoring rules](#scoring-rules)
- [Cost](#cost)

## What each step checks

| Step | Fails or blocks when |
|---|---|
| diff | Nothing changed |
| guard | A protected file was rewritten or removed; a SKILL.md body or a reference grew past its budget; an added line shares wording with an eval prompt; a file was written outside the staged paths |
| validators | `validate_skill.py` or `audit_skill.py` report an error the committed version did not have, or more warnings; `check_scripts.py` reports an error after a script change |
| eval | The scoring rules below |

The steps run in that order and stop at the first that does not pass, so a blocked
change costs no eval run. Before them, `check` and `land` compare the run's `base/` copy
with the commit it was staged from and refuse on any difference (`base-tampered`):
every comparison rests on that copy, so it is read-only.

A path that does not exist yet (a new skill) is staged with `--new-path`. It has no
base: validators fail it on errors only, and every eval case has to pass on its own.

## Protected paths

The gate is only worth something if the change being judged cannot loosen it. These
may be added to freely, and a pure addition of lines is allowed; rewriting or removing
existing lines gives `blocked`:

- anything under `evals/` or `hooks/`, and `scripts/tests/`;
- files named `test_*.py`, `validate*.py`, `audit*.py`, `check*.py`, `guard*.py`,
  `gate.py`, `*lint*`, `lint-config*`, `*.calibration.json`;
- the `hooks:` block of a SKILL.md frontmatter, and its `## Self-check` section: the
  skill's own acceptance criteria may gain items, never lose or loosen them.

A `blocked` change is not discarded. Its run directory holds the staged files and the
verdict, and `signals.py list --status blocked` is the queue the user reads.

## Eval cases

Cases live in the skill at `evals/<case>/`, in the format `claude plugin eval` reads:

```text
evals/
├── <case>/
│   ├── prompt.md      # frontmatter: tags, max_turns, allowed_tools; body: what a user would type
│   └── graders/
│       ├── <name>.md  # frontmatter: type + options; body: rubric or pattern
│       └── ...
└── calibration/       # judge rubrics, labelled examples, calibration files; not a case
```

- **Prompt**: phrased the way the user types the request, not naming the skill. Each
  run starts in an empty directory, so the prompt carries everything the task needs.
  Grant `Skill` in `allowed_tools`, plus the read-only tools the skill uses.
- **Tags**: `gate` for cases the gate runs on every change; `holdout` for cases held
  back until `--final`. Keep roughly one case in three as holdout and never look at a
  holdout case while writing a change, or it stops measuring anything.
- **Graders**: give each case one grader on the result and one on the route.
  - Result: `regex` over the final message or over a produced file
    (`target: { source: file, path: ... }`). Prefer this to a judge whenever the
    criterion can be written as a pattern, including `match: not_contains`.
  - Route: `tool_order` (`before`, `after`) and `tool_used` (`min`, `max`) for steps
    the skill requires in order, such as running its linter before presenting.
  - `llm` graders (a judge, two votes of three) only for short outputs, with the
    rubric written as concrete PASS and FAIL conditions, and only once the judge is
    calibrated (`judge-calibration.md`, load via SKILL.md). An uncalibrated judge
    may sit in a case with `weight: 0.01` to collect verdicts without moving the score.
- **A case for a signal** reproduces the situation, not the incident: same kind of
  request, different subject matter. It has to fail on the committed skill.
- **Freeze**: once a case has been used by a gate run, changing it is a protected
  edit. Add a new case instead.

The first cases for a skill come from its gap list
(the `creating-agent-skills` skill, `references/self-evaluation.md`).

## What an eval run cannot see

Each run is an isolated headless session with only the skill under test loaded. The
gate builds a temporary plugin around the staged skill for this; the skill directory
itself never gets a plugin manifest. Inside a run there are no user settings, no
memory files, no other skills, no sub-agent definitions, no connectors, and no Artifact
tool. So:

- a step that spawns a named tier fails in the run. Write cases for the single-context
  path, and grade the brief the skill would send (a file it writes) where that matters;
- a skill that hands off to another skill can be graded only up to the hand-off;
- tools beyond the read-only set need `--allow-tools` on the eval command, which the
  gate does not pass. A case that needs to write files or run commands is graded on
  the final message and on files the session created with the tools it has.

## Scoring rules

A case's score is the mean over its runs (three by default) of the share of graders
that passed. Both the committed skill (base) and the staged skill (head) run the same
cases, taken from the staged copy.

| Rule | Requires |
|---|---|
| R1 | Mean over existing cases: head ≥ base |
| R2 | No existing case drops by more than 0.34 |
| R3 | Every `gate` case added by this change scores higher on head than on base, and at least 0.66 on head (two runs of three). A base score already at 0.66 or more means the case did not need the change (`baseline-already-passes`). An added case tagged neither `gate` nor `holdout` fails the check (`new-case-untagged`) |
| R4 | With `--final`: mean over `holdout` cases, head ≥ base |

When R1 or R2 fails, the gate reruns the failing cases once on both sides and pools
the runs, because three runs of a non-deterministic agent can differ by one flip. It
does this once. A second failure stands.

`unmeasured` means no case matched; `inconclusive` means a run did not finish. Neither
is a pass.

## Cost

A gate check runs cases × runs × 2 sessions, plus three short judge calls per `llm`
grader per run. `gate.py check` passes a cost ceiling to each eval (`--max-cost-usd`,
default 5; unattended runs pass 1); hitting it gives `inconclusive`. The ceiling applies
per eval invocation, and one check makes two (base and head), plus two more with
`--final` and one pair per retaken case. Keep the `gate` set small, three to six
cases, and put breadth in `holdout`. A full run of every case with the no-skill
comparison belongs to a deliberate review of the skill, not to this loop.
