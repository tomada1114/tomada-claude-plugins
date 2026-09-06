<!-- audit-ignore-file: A006 -->
<!-- prompt-lint-ignore-file: all -->
# Rule catalog

Every rule `scripts/lint_prompt_doc.py` reports, with the reason it exists and
the rewrite that closes it. The script prints a one-line `fix`; this file is the
treatment. Rule ids are stable — cite them in audit reports.

Quoted anti-patterns below are examples, not instructions. This file suppresses
the linter on itself for that reason; do the same in any document whose subject
is prompting (`<!-- prompt-lint-ignore-file: P002,P003 -->` at the top, or
`<!-- prompt-lint-ignore: P004 -->` on or above a single line).

## Table of Contents

- [Severity](#severity)
- [P001 forced-verification](#p001-forced-verification)
- [P002 severity-self-filtering](#p002-severity-self-filtering)
- [P003 reasoning-echo](#p003-reasoning-echo)
- [P004 emphasis-shouting](#p004-emphasis-shouting)
- [P005 tool-overtrigger](#p005-tool-overtrigger)
- [P006 fixed-progress-scaffolding](#p006-fixed-progress-scaffolding)
- [P007 negative-enumeration-density](#p007-negative-enumeration-density)
- [P008 blanket-thoroughness](#p008-blanket-thoroughness)
- [P009 open-ended-delegation](#p009-open-ended-delegation)
- [P010 legacy-api](#p010-legacy-api)
- [P011 sampling-params](#p011-sampling-params)
- [P012 negative-formatting-rule](#p012-negative-formatting-rule)
- [P013 narration-suppression](#p013-narration-suppression)
- [D001 doc-size-budget](#d001-doc-size-budget)
- [D002 duplicate-directive](#d002-duplicate-directive)
- [What the linter cannot see](#what-the-linter-cannot-see)

---

## Severity

`error` — measurably degrades output or fails the API request. Fix unless the
document has a stated reason not to.
`warn` — costs tokens or steers against the model's default without paying for
it. Usually a deletion.
`info` — a style signal worth a look; judgment decides.

A finding is a prompt to think, not a verdict. Suppress with an ignore marker
and a reason rather than contorting the text around a false positive.

---

## P001 forced-verification

**Fires on:** "double-check", "re-verify", "verify your answer", "add a final
verification step", "before responding, confirm ...".

Current models verify and self-correct their own work by default. An added
verification instruction compounds with that: the model runs the extra pass,
spends the tokens, and the result does not improve. On Opus 5 the guidance is
explicit — when migrating a prompt, remove these instructions rather than
rewriting them, along with any harness scaffolding that adds a separate
verification step.

**Rewrite:** delete. If you need proof the work happened, ask for the artifact:
"State the commands you ran and their output."

The one place a verification step still earns its cost is an autonomous run
spanning many phases, where a *separate* context checks the finished work
against the spec. That is a workflow stage, not a sentence in a prompt.

## P002 severity-self-filtering

**Fires on:** "only report high-severity issues", "be conservative", "don't
nitpick", "skip minor issues".

This is the highest-value rule in the catalog. Sonnet 5 and Opus 5 follow the
instruction literally: they investigate the code just as deeply, find the same
bugs, then decline to report the ones below your stated bar. Measured recall
falls while the model's actual bug-finding ability is unchanged, so the harness
looks like a capability regression.

**Rewrite:**

```text
Report every issue you find, including ones you are uncertain about or consider
low-severity. Do not filter for importance or confidence at this stage — a
separate step will do that. For each finding, include your confidence and an
estimated severity so a downstream filter can rank them.
```

If you genuinely need single-pass self-filtering, put the bar in concrete terms
rather than a qualitative word: "report any bug that could cause incorrect
behavior, a test failure, or a misleading result; omit pure style and naming
preferences."

## P003 reasoning-echo

**Fires on:** "show your reasoning", "explain how you arrived at this", "write
out your thought process", "think out loud".

Asking the model to reproduce its own internal reasoning can trip the
`reasoning_extraction` refusal category on Fable-class models and force a
fallback to another model. The request also buys little: the visible narration
is a reconstruction, not the reasoning itself.

**Rewrite:** ask for evidence. `file:line` citations, the command and its
output, the diff, the artifact. That is checkable; a narration is not.

## P004 emphasis-shouting

**Fires on:** `CRITICAL:`, `IMPORTANT:`, "You MUST", "MUST ALWAYS", "NEVER
EVER".

Shouted emphasis was a workaround for models that undertriggered on tools and
skills. Current models are markedly more responsive to the system prompt, so the
same wording now overtriggers the behavior it was guarding: the tool fires when
it should not, the rule applies where it should not.

**Rewrite:** `CRITICAL: You MUST use this tool when the user mentions X` becomes
`Use this tool when the user mentions X`. Keep hard emphasis for the small set
of genuinely irreversible constraints, and say what breaks when it is violated.

## P005 tool-overtrigger

**Fires on:** "if in doubt, use ...", "default to using ...", "always use the
... tool".

Same root cause as P004, in the form of a blanket default. Tools that
undertriggered on older models trigger appropriately now, so a standing
instruction to reach for one produces calls that a direct answer would have
covered.

**Rewrite:** name the condition. "Default to using the search tool" becomes
"Use the search tool when it would improve your understanding of the problem."

Note the opposite failure exists and is not this rule: at `low` effort some
models call search and retrieval tools less often. The fix there is to raise
effort for those turns, or to say *why* verification matters for that class of
query — not to reinstate a blanket default.

## P006 fixed-progress-scaffolding

**Fires on:** "after every 3 tool calls, summarize progress", "provide a status
update every ...".

Current models emit well-calibrated progress updates on their own. A fixed
cadence fights that: it interrupts work at arbitrary points and adds messages
nobody asked for.

**Rewrite:** delete it. If the *shape* of the updates is wrong, show one example
of the update you want — a positive example outperforms a cadence rule.

## P007 negative-enumeration-density

**Fires on:** a document where prohibition clauses ("do not", "never", "avoid",
"must not") reach both 12 occurrences and 15% of non-blank lines.

One prohibition is fine. A document written mostly as prohibitions is a document
that never says what good output looks like, and every clause is charged to the
context window on each run.

**Rewrite:** replace the longest runs with one or two positive examples in
`<example>` tags. Keep prohibitions for the cases where the wrong action is
irreversible.

## P008 blanket-thoroughness

**Fires on:** "go above and beyond", "be thorough", "leave no stone unturned",
"exhaustively review".

A standing thoroughness order invites the scope expansion that current models
already tend toward unprompted — extra files, extra abstractions, work nobody
requested.

**Rewrite:** define done. "Include as many relevant features as possible" is a
legitimate instruction on the one task that wants maximal output; as a standing
rule across every task it is a cost with no ceiling.

## P009 open-ended-delegation

**Fires on:** "use subagents whenever ...", "delegate liberally", "spawn
multiple agents".

Opus 5 and Fable-class models delegate readily without being asked. An
open-ended nudge produces sub-agents for work a single search would finish, and
each spawn multiplies cost and wall-clock time.

**Rewrite:**

```text
Delegate to a subagent only for large tasks that are genuinely independent and
parallelizable, such as a wide multi-file investigation. Do not delegate work
you can finish yourself in a handful of tool calls, and do not use subagents to
verify your own work. If one subagent can do it, use one rather than several.
```

Pair it with a hard cap where the harness supports one.

## P010 legacy-api

**Fires on:** `budget_tokens`, `thinking: {type: "enabled"}`, "assistant
prefill", "prefilled response".

Both patterns are removed, not merely discouraged. Manual extended thinking with
`budget_tokens` returns 400 on current models; a prefilled assistant message on
the final turn returns 400 from the 4.6 generation onward.

**Rewrite:** adaptive thinking (`thinking: {type: "adaptive"}`) with the
`effort` parameter, and `max_tokens` as the hard ceiling. For prefills: use
structured outputs for schemas, tool enums for classification, and a direct
instruction ("Respond directly without preamble") for preamble suppression.

## P011 sampling-params

**Fires on:** `temperature:`, `top_p:`, `top_k:` with a value.

Setting any of these to a non-default value returns 400 on Sonnet 5. Prompts
that relied on temperature for stylistic variety need a different lever.

**Rewrite:** remove the parameter. For variety, ask the model to propose several
distinct directions and pick one; for tone, describe the voice in the prompt.

## P012 negative-formatting-rule

**Fires on:** "do not use markdown", "no bullet points", "avoid lists".

Two problems. Prohibitions steer formatting weakly — describing the output you
want works better. And the models these rules were written against are gone:
Fable 5.1 already formats sparsely, so an inherited anti-formatting block
suppresses structure the content needed.

**Rewrite:** "Do not use markdown" becomes "Write in flowing prose paragraphs."
Where some structure is right, say when: "Use lists when the content is
multifaceted enough that they aid clarity; keep conversational replies in plain
prose." On a model that already under-formats, delete the block outright.

## P013 narration-suppression

**Fires on:** "hold all findings for the final response", "do not provide
progress updates", "no running commentary".

Written for models that over-narrated. Fable 5.1 writes *fewer* user-facing
updates during long tool chains than its predecessor, so inherited suppression
produces a run that goes silent for minutes.

**Rewrite:** remove the suppression first, then check whether you still need
anything. If you do, say when you want text and what it should contain: "Say in
one line what you're about to do; give a brief update when you find something
important or change direction; close with a recap that stands on its own."

## D001 doc-size-budget

**Fires on:** body lines past the budget for the document kind.

| Kind | Warn | Error | Why this budget |
|---|---|---|---|
| `memory` (CLAUDE.md, AGENTS.md) | 200 | 400 | Re-read into every session before the user's request |
| `skill` (SKILL.md) | 200 | 500 | Stays in context for every turn after the skill fires |
| `agent` (agents/*.md) | 200 | 400 | Prepended to every turn of the sub-agent's run |
| `command` (commands/*.md) | 150 | 300 | Expanded inline on each invocation |
| `reference` (references/*.md) | 400 | 800 | Loaded on demand, but a second monolith helps nobody |

**Rewrite:** the document keeps the decisions, the dispatch, and the hard rules.
Rationale, worked examples, and anything only one branch needs move to a
reference file with a one-line pointer left behind.

## D002 duplicate-directive

**Fires on:** a normalized line of 40+ characters repeated in the same document.

A directive stated twice reads as two rules to a literal reader, and drifts once
someone edits one copy.

**Rewrite:** keep the statement at the point where it is acted on; delete the
other.

---

## What the linter cannot see

Judgment items for the reviewing pass. None are detectable by pattern:

- **An instruction that restates default behavior.** The most common defect in
  an older document. For the longest sections, ask what the model would do
  without them; if the answer is "the same thing," delete.
- **A missing reason.** "Never use ellipses" underperforms "your response is
  read aloud by a text-to-speech engine, which cannot pronounce ellipses."
- **Unstated scope.** Models do not silently generalize an instruction from one
  item to another. "Apply this to every section, not just the first" is
  necessary, not redundant.
- **Prescriptiveness out of proportion to fragility.** Step-by-step scripting
  belongs to operations that break when improvised. Elsewhere it degrades
  output: state the goal, the constraints, and the output contract.
- **A missing output contract.** Exact section names and finding format, where
  anything downstream merges the result mechanically.
- **Uncalibrated length.** Documents the model writes run long by default; if a
  document is a deliverable, say how long it should be.
