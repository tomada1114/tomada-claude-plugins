<!-- audit-ignore-file: A006 -->
<!-- prompt-lint-ignore-file: P001,P002,P003,P004,P005,P008,P012 -->
# General prompting practices

What holds across current Claude models. The anti-patterns and their rewrites
live in `rules.md`; this file is the positive side — what to write, and the
divergences that decide which model file to open next.

## Table of Contents

- [Where the three models diverge](#where-the-three-models-diverge)
- [Clarity](#clarity)
- [Examples](#examples)
- [Structure](#structure)
- [Output and formatting](#output-and-formatting)
- [Long context](#long-context)
- [Tool use](#tool-use)
- [Thinking and effort](#thinking-and-effort)
- [Agentic and long-horizon work](#agentic-and-long-horizon-work)
- [Scope control](#scope-control)

---

## Where the three models diverge

The single table worth consulting during an audit. Open the per-model file when
the document targets one model specifically.

| Behavior | Fable 5.1 | Opus 5 | Sonnet 5 |
|---|---|---|---|
| Conversational length | dense prose; asks for shorter sentences, not less structure | longer than prior Opus; needs an explicit conciseness instruction | calibrated to task complexity |
| Formatting in chat | under-formats; anti-formatting blocks must go | standard | standard |
| Progress updates during tool chains | fewer than expected; ask for them | narrates readily; tune down | well calibrated; remove scaffolding |
| Self-verification | standard | strong — remove verification instructions | standard |
| Subagent delegation | delegates readily; let the lead keep working | delegates readily; cap it | standard |
| Instruction literalism | standard | high on review-bar wording | high — state scope explicitly |
| Thinking | always on, adaptive only | on by default; disable only at ≤ `high` effort | on by default (change from 4.6) |
| Effort default | `high` | `high`; `low`/`medium` are the primary cost lever | `high`; `xhigh` for hardest work |

Detail: `model-fable-5-1.md`, `model-opus-5.md`, `model-sonnet-5.md`.

## Clarity

Treat the reader as a capable colleague with no context on your norms. Say what
the output should be and what constrains it. The check: hand the prompt to a
person with minimal context on the task — if they would be confused, so is the
model.

Give the reason behind an instruction, not only the instruction. A model that
knows *why* generalizes the rule to cases the rule did not enumerate. "Never use
ellipses" is weaker than "your response is read aloud by a text-to-speech
engine, which cannot pronounce ellipses."

Use sequential numbered steps where order or completeness actually matters, and
prose everywhere else.

Ask for what you want rather than hinting at it. "Can you suggest some changes"
gets suggestions; "Change this function to improve its performance" gets the
edit. Where a document should default to acting, say so once:

```text
By default, implement changes rather than only suggesting them. If the user's
intent is unclear, infer the most useful likely action and proceed, using tools
to discover missing details instead of guessing.
```

Where it should default to advising, invert it explicitly — the model will not
infer the preference.

## Examples

Examples are the most reliable steering lever for format, tone, and structure,
and they beat an equivalent paragraph of rules. Three to five, wrapped in
`<example>` tags inside an `<examples>` container.

Make them relevant (mirroring the real case), diverse (so the model does not
overfit one shape), and structurally marked so they read as examples rather than
instructions. A single complete example — request, correct response, and one
sentence on *why* it is correct — is the standard fix for a behavior that
resists description.

Positive examples outperform prohibitions in every measured case. Reach for a
prohibition only where the wrong action is irreversible.

## Structure

XML tags separate content types when a prompt mixes instructions, context,
examples, and variable input: `<instructions>`, `<context>`, `<input>`. Use
consistent tag names, and nest where the content has real hierarchy.

This matters most in prompts a parent constructs for a sub-agent, where slices
of a diff or a design doc are pasted in and would otherwise read as instructions.

A role sentence in the system prompt focuses tone and behavior measurably, even
at one sentence.

## Output and formatting

Say what the output should be, not what it should avoid. "Write in flowing prose
paragraphs" works; "do not use markdown" does not.

Match the style of the prompt to the style you want back — a prompt heavy with
markdown pulls markdown into the response.

Where formatting control has to be tight, an XML format indicator is the
strongest lever: "Write the prose sections in `<smoothly_flowing_prose>` tags."

Calibrate length explicitly for anything the model writes to disk. Files and
reports run long by default:

```text
Match the length of written documents to what the task needs: cover the
substance, but do not pad with filler sections, redundant summaries, or
boilerplate.
```

Mathematical output defaults to LaTeX. If the surface cannot render it, say so
and name the substitute notation.

## Long context

Put long documents and data at the **top** of the prompt, above the query,
instructions, and examples. Queries placed at the end measurably improve
response quality on complex multi-document inputs.

Wrap each document in `<document>` with `<source>` and `<document_content>`
subtags.

For long-document tasks, ask the model to pull the relevant quotes into
`<quotes>` tags before doing the work. It focuses the model on the passages that
matter and leaves the rest unattended.

## Tool use

Independent tool calls run in parallel by default. Where you want that at close
to 100%, or want to dial it back, say so explicitly:

```text
If you intend to call multiple tools and there are no dependencies between the
calls, make all of the independent calls in the same response. If some calls
depend on the results of others, run those sequentially. Never use placeholders
or guess missing parameters.
```

Tool definitions do the heavy lifting: a tool that is not triggering usually
needs a clearer description of when and why to use it, not a louder instruction
in the system prompt.

## Thinking and effort

Adaptive thinking is the current mode: the model decides how much to think based
on the `effort` setting and the complexity of the query. Manual budgets are
removed (see `rules.md` P010).

`effort` is the primary control for the intelligence / latency / cost tradeoff,
and it is the first lever to reach for before prompting around a behavior. Effort
level names do not correspond to the same amount of thinking across models, so
re-run a sweep on your own evals after a model change.

Thinking depth is also promptable in both directions. To reduce it:

```text
Thinking adds latency and should only be used when it will meaningfully improve
answer quality — typically for problems that require multistep reasoning. When
in doubt, respond directly.
```

To improve use of it after tool calls: "After receiving tool results, reflect on
their quality and determine the best next step before proceeding."

Prefer a general instruction ("think thoroughly about the tradeoffs") over a
hand-written step-by-step reasoning plan. Model reasoning routinely exceeds what
a human would prescribe, and the prescription caps it.

## Agentic and long-horizon work

State the context-window contract. Without it a model may wrap up early as it
senses the limit approaching:

```text
Your context window will be automatically compacted as it approaches its limit,
so you can continue working from where you left off. Do not stop early due to
token budget concerns. As you approach the limit, save your progress and state
before the context refreshes.
```

Structured state (test results, task status) belongs in JSON; progress notes
belong in freeform text; git is the checkpoint mechanism. Ask for incremental
progress rather than everything at once.

For research, define what a successful answer looks like, ask for competing
hypotheses with tracked confidence, and have the model persist notes to a file.

For risky actions, describe the reversibility test rather than enumerating
commands:

```text
Consider the reversibility and impact of your actions. Local reversible actions
— editing files, running tests — proceed. For actions that are hard to reverse,
affect shared systems, or could be destructive, ask first. Do not use
destructive actions as a shortcut around an obstacle.
```

## Scope control

Current models expand scope unprompted: extra files, unrequested refactors,
abstractions for hypothetical requirements. For narrow work, constrain it
explicitly:

```text
Deliver what was asked, at the scope intended. Make routine judgment calls
yourself, and check in only when different readings would lead to materially
different work. If the request seems mistaken or a better approach exists, say
so in a sentence and continue as asked rather than quietly narrowing, widening,
or transforming it. Finish the whole task, and stop short of actions clearly
beyond what was asked.
```

The same instinct shows up in code as over-engineering — extra error handling,
defensive validation for impossible states, helpers for one-time operations.
Name the specific dimensions (scope, documentation, defensive coding,
abstractions) rather than asking for "simple code".

For tasks with tests, say that tests verify the solution rather than define it,
and that hardcoding to the test cases is not a solution.

For grounded answers about a codebase: "Never speculate about code you have not
opened. If the user references a specific file, read it before answering."
