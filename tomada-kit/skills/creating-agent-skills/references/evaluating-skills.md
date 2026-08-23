# Evaluating a Skill

Seeing a skill trigger tells you Claude found it — not that it did what you intended. Two things fail independently and need to be measured separately:

- **Selection**: does the skill activate on the prompts it should, and stay quiet on the ones it shouldn't? Owned by `description` / `when_to_use`.
- **Output**: when it does activate, does the result match what you wanted? Owned by the body and bundled resources.

## Table of Contents

- [Evaluation-driven authoring](#evaluation-driven-authoring)
- [The baseline comparison](#the-baseline-comparison)
- [Eval case format](#eval-case-format)
- [Running evals with skill-creator](#running-evals-with-skill-creator)
- [The A/B iteration loop](#the-ab-iteration-loop)
- [Reading how Claude navigates the skill](#reading-how-claude-navigates-the-skill)
- [Testing across models](#testing-across-models)

---

## Evaluation-driven authoring

Write the evals **before** the documentation. A skill written first and evaluated later documents the problems you imagined; a skill written against evals documents the problems that actually occurred.

1. **Find the gap.** Run the task with no skill. Record the specific failures — what context was missing, what convention was violated, what step got skipped.
2. **Write three cases** that reproduce those failures.
3. **Establish the baseline.** Measure the no-skill result against each case's expected behavior.
4. **Write the minimum instructions** that close the gap. Not the complete guide you could write — the part the baseline actually failed.
5. **Re-run and compare.** Anything that passed at baseline needs no instruction; delete the text covering it.

Step 5 is the one that keeps skills small. Most bloat is instructions for behavior the model already had.

## The baseline comparison

The check for both selection and output is the same shape: run each prompt in a **fresh session** with the skill available, then again with it disabled, and compare.

- A fresh session matters. Leftover context from authoring the skill masks gaps in the written instructions — you'll watch it succeed for reasons that won't exist for anyone else.
- Disable a skill for the without-skill arm via the `skillOverrides` setting (`"off"`), not by deleting it.
- Compare cost too, not just pass/fail. A skill that lifts the pass rate from 80% to 90% while tripling tokens may still be the wrong trade.

## Eval case format

Store cases in `evals/evals.json` inside the skill directory. Each case is a prompt plus assertions about the observable result:

```json
{
  "skills": ["processing-pdfs"],
  "query": "Extract all text from this PDF file and save it to output.txt",
  "files": ["test-files/document.pdf"],
  "expected_behavior": [
    "Reads the PDF using an appropriate PDF library or CLI tool",
    "Extracts text from every page without skipping any",
    "Writes the result to output.txt in readable form"
  ]
}
```

Write `expected_behavior` entries as things a grader can check from the transcript and the artifacts — files written, commands run, content present. "Handles the task well" is not gradable.

For **selection** cases, pair should-trigger prompts with should-not-trigger prompts. The should-not set is what catches an over-broad description, and it is the half people forget.

## Running evals with skill-creator

The official `skill-creator` plugin automates the loop inside Claude Code:

```text
/plugin install skill-creator@claude-plugins-official
```

If the marketplace is missing: `/plugin marketplace add anthropics/claude-plugins-official`. If the plugin is missing from a marketplace you already have: `/plugin marketplace update claude-plugins-official`. Then `/reload-plugins` to expose it in the current session.

Ask for it by name — e.g. `evaluate my summarize-changes skill with skill-creator`. What it does:

| Stage | Output |
|---|---|
| Test cases | prompts, input files, expected behavior → `evals/evals.json` |
| Isolated runs | one subagent per case (clean context), token count and duration recorded |
| Grading | each assertion checked against the output → `grading.json` with evidence |
| Benchmark | with-skill vs without-skill pass rate, time, tokens → `benchmark.json` |
| Version comparison | blind A/B between two versions of the skill |
| Description tuning | generates should-trigger / should-not-trigger prompts, measures hit rate, proposes description edits |
| Review viewer | HTML report for qualitative feedback that the next iteration reads |

Full format and workflow: [Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills).

## The A/B iteration loop

Skill development works best with two Claude instances in different roles:

- **Claude A** — the author. Has the conversation history, your domain context, and this skill.
- **Claude B** — the user. A fresh session with only the skill loaded, doing real work.

The loop: give Claude B a real task → watch where it struggles → bring the specific observation back to Claude A → revise → test again.

The observation must be specific. "It didn't work well" produces a rewrite; "it wrote the query but never filtered test accounts, even though the skill says to" produces a fix — usually prominence, ordering, or wording strength rather than more content.

Run this on real tasks rather than test scenarios. Test scenarios are written by someone who already knows the answer.

## Reading how Claude navigates the skill

Behavioral signals worth more than any checklist:

| Observation | What it means |
|---|---|
| Reads files in an order you didn't anticipate | The structure isn't as intuitive as it looked |
| Never follows a link to a reference | The pointer is too weak, or buried below the point where it decided it had enough |
| Re-reads the same reference every run | That content belongs in SKILL.md |
| Never opens a bundled file at all | It's unnecessary, or unsignposted |
| Activates on the wrong requests | Description too broad — tune with should-not-trigger cases |
| Never activates unprompted | Trigger keywords are in the body instead of the description, or `paths` is gating it |

## Testing across models

A skill is an addition to a model, not a standalone spec — its effectiveness depends on what the underlying model already needs spelled out. If a skill runs on more than one model, run the same eval cases on each one before calling it done:

- **Haiku** (fast, economical): does the skill provide enough guidance, or does it need a step spelled out that a stronger model would infer?
- **Sonnet** (balanced): is the skill clear and efficient with no ambiguity left for judgment calls that matter?
- **Opus** (strongest reasoning): does the skill avoid over-explaining what this model already does correctly unprompted?

A prescriptive block written for Haiku's failure mode is exactly the kind of instruction Opus doesn't need — and, per `prompt-authoring.md`'s "Prescriptiveness budget" section (load via SKILL.md), costs it quality. When a skill must serve models of different strength, prefer the version that clears the weakest model with the least prescription, rather than writing to the strongest model and hoping the weakest infers the gap.
