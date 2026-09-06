<!-- audit-ignore-file: A006 -->
<!-- prompt-lint-ignore-file: P001,P002,P004,P008,P009 -->
# Prompting Claude Opus 5

Built for complex agentic coding and enterprise work, strongest on long-horizon
tasks. Existing Opus 4.8 prompts run well on it; the items below are what
actually needs tuning. Provenance in `sources.md`.

## Table of Contents

- [Capabilities that change what a prompt should say](#capabilities-that-change-what-a-prompt-should-say)
- [Response length and verbosity](#response-length-and-verbosity)
- [Written deliverable length](#written-deliverable-length)
- [Progress updates](#progress-updates)
- [Over-verification](#over-verification--the-migration-item-that-matters-most)
- [Task scope](#task-scope)
- [Subagent spawning](#subagent-spawning)
- [Review harnesses](#review-harnesses)
- [Thinking](#thinking)

---

## Capabilities that change what a prompt should say

- **Agentic coding.** Completes full tasks rather than leaving stubs. Performs
  best given the complete specification up front and then left to run — a
  progressively-revealed spec across many turns costs tokens and quality.
- **Code review.** High precision *and* recall per pass, and accuracy holds at
  lower effort. This is what makes review-bar wording dangerous on it (below).
- **Efficiency at low effort.** `low` and `medium` give strong quality at a
  fraction of the tokens and latency. Use them liberally as the primary cost and
  latency control; step to `xhigh` for demanding agentic work. Effort defaults
  carried over from a prior model should be re-swept.
- **Vision.** Strong on charts, documents, diagrams, and UI replication.
  Prompt-side vision workarounds tuned for older models may now be dead weight.
  Tools that let it crop and verify beat extra thinking.
- **Long context.** 1M tokens as both default and maximum, with instruction
  following and tool calling holding across the window.
- **Multi-agent.** Coordinates writer-verifier patterns well, with few cases of
  agents overwriting each other.

## Response length and verbosity

Default user-facing responses run longer than prior Opus models. `effort`
controls how much it *thinks*, not how much it *says*, so lowering effort does
not reliably shorten the reply. Prompt for length directly:

```text
Keep responses focused, brief, and concise. Keep disclaimers and caveats short,
and spend most of the response on the main answer. When asked to explain
something, give a high-level summary unless an in-depth explanation is
specifically requested.
```

In a long system prompt, repeat a short reminder near the end:

```text
<tone_preference>
Keep outputs reasonably concise.
</tone_preference>
```

## Written deliverable length

Separate from conversational verbosity: files it writes to disk — reports,
Markdown documents, summaries — run long. If a document is the product, say:

```text
Match the length of written documents to what the task needs: cover the
substance, but do not pad with filler sections, redundant summaries, or
boilerplate.
```

## Progress updates

It narrates readily during agentic work, announcing what it is about to do, with
longer per-message output than prior models. To tune down, describe the cadence
and shape rather than prohibiting narration:

```text
Before your first tool call, say in one sentence what you're about to do. While
working, give a brief update only when you find something important or change
direction. When you finish, lead with the outcome: your first sentence should
answer "what happened" or "what did you find," with supporting detail after it.
```

The same lever works upward. Positive examples of the style you want beat
instructions about what not to do.

## Over-verification — the migration item that matters most

It verifies its own work without being told to. Explicit verification
instructions ("include a final verification step for any non-trivial task", "use
a subagent to verify", "double-check your answer") **compound** with that
behavior: more tokens, no quality gain. When migrating a prompt to Opus 5,
**remove** them rather than rewriting them. The same applies to legacy harness
scaffolding that inserts a separate verification stage.

It also self-corrects well, and narrates those corrections more than prior
models — which reads badly in a user-facing product. To bound it:

```text
Only correct an earlier statement when the error would change the user's code,
conclusions, or decisions. State corrections plainly and briefly, then continue
the task. For slips that change nothing for the user, make the fix and move on
without noting it.
```

## Task scope

It expands scope: extra steps, its own judgment about what the task should have
been. For narrow tasks, constrain explicitly with the scope block in
`general-practices.md#scope-control`.

## Subagent spawning

It delegates more readily than prior models. Delegation pays on genuinely
independent, sizeable tracks and loses on small ones. State the bar:

```text
Delegate to a subagent only for large tasks that are genuinely independent and
parallelizable, such as a wide multi-file investigation. Do not delegate work
you can finish yourself in a handful of tool calls, and do not use subagents to
verify or double-check your own work. If one subagent can complete the task, use
one rather than several, and keep spawn counts low.
```

In Claude Code and the Agent SDK the deterministic caps are
`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`,
and the SDK's `max_budget_usd`. Claude Code adds a delegation instruction of its
own only under its `claude_code` system prompt preset; with a custom or omitted
system prompt, supply one.

## Review harnesses

A review prompt that says "only report high-severity issues" or "be
conservative" is followed literally — it reports less while investigating just
as deeply. Ask for full coverage with confidence and severity attached, and
filter in a separate pass. See `rules.md` P002.

## Thinking

Thinking is on by default, and can be disabled only at `high` effort or below.
With thinking disabled, two artifacts appear occasionally: a tool call written
into user-facing text instead of a structured call (it never runs, and the
leaked text persists in agentic history), and internal XML tags in the visible
response. A system prompt rule telling the model not to think or reason
*increases* tag leakage — remove it.

The primary mitigation for both is to keep thinking on and control cost with
lower effort: thinking enabled at `low` beats thinking disabled at similar cost.
Where thinking must stay off, one combined instruction covers both artifacts:

```text
When you use a tool, you may say a brief sentence first. If no tool can express
what the user asked for, say so instead of guessing. Do not include internal or
system XML tags in your response.
```

Naming thinking tags specifically is less effective than that general form.
