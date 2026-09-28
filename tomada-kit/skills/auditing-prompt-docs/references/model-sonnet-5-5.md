<!-- audit-ignore-file: A006 -->
<!-- prompt-lint-ignore-file: P001,P002,P010,P013,P014,P015 -->
# Prompting Claude Sonnet 5.5

Pitched as the best combination of speed and intelligence; for the hardest
long-horizon work an Opus model is the better choice. Sonnet 5 prompts perform
well unchanged, and the Sonnet 5 patterns kept at the end of this file remain a
reasonable starting point; the sections before them are what Sonnet 5.5 changes.
This file replaces the Sonnet 5 file. Provenance in `sources.md`.

## Table of Contents

- [Symptom index](#symptom-index)
- [API changes from Sonnet 5](#api-changes-from-sonnet-5)
- [Effort](#effort)
- [Initiative and scope](#initiative-and-scope)
- [Running without up-front thinking](#running-without-up-front-thinking)
- [Reasoning tasks with JSON output](#reasoning-tasks-with-json-output)
- [Progress updates](#progress-updates)
- [Tool use in chat and knowledge work](#tool-use-in-chat-and-knowledge-work)
- [Mid-turn user messages](#mid-turn-user-messages)
- [Verification on coding tasks](#verification-on-coding-tasks)
- [Tolerant tool-call handling](#tolerant-tool-call-handling)
- [Visual inputs](#visual-inputs)
- [Safeguard refusals](#safeguard-refusals)
- [Carried over from Sonnet 5](#carried-over-from-sonnet-5)

---

## Symptom index

| What you observe | Section |
|---|---|
| Unsure which effort to run, or turns longer/shorter than on Sonnet 5 | [Effort](#effort) |
| Stops to check in before a coding task is done, or does more than asked | [Initiative and scope](#initiative-and-scope) |
| The integration runs with thinking off today | [Running without up-front thinking](#running-without-up-front-thinking) |
| JSON answers to multistep tasks are wrong or don't parse | [Reasoning tasks with JSON output](#reasoning-tasks-with-json-output) |
| Long agentic turns look silent | [Progress updates](#progress-updates) |
| Answers from training knowledge where a search would catch changes | [Tool use in chat](#tool-use-in-chat-and-knowledge-work) |
| Mid-task user messages ignored or treated as injected text | [Mid-turn user messages](#mid-turn-user-messages) |
| Code changes reported done without a test or build run | [Verification on coding tasks](#verification-on-coding-tasks) |
| Tool called with wrong letter case or a near-miss parameter name | [Tolerant tool-call handling](#tolerant-tool-call-handling) |
| Dense charts or technical drawings misread | [Visual inputs](#visual-inputs) |
| `stop_reason: "refusal"` | [Safeguard refusals](#safeguard-refusals) |

## API changes from Sonnet 5

Five breaking changes; each returns 400 where Sonnet 5 succeeded. Flag them in
harness code and in any document that tells a model or a developer how to call
the API.

1. **`thinking: {"type": "disabled"}`** → send `{"type": "between_tools"}`, at
   `high` effort or below. See [Running without up-front thinking](#running-without-up-front-thinking).
2. **Forced tool use.** `tool_choice` `{"type": "any"}` or `{"type": "tool", ...}`
   is rejected (token counting too). Use `auto` plus `strict: true`, or
   structured outputs, and **say in the prompt when the tool applies** — the
   model can now answer without calling it. On Amazon Bedrock strict tool use is
   unavailable for this model: send `auto` and validate the input in code.
3. **Thinking blocks are bound to the model and the conversation.** Keep history
   append-only; editing `system`, `tools`, or an earlier message before a
   replayed block returns 400 (enforced by default for accounts created on or
   after 2026-08-31). Change instructions or tools with mid-conversation system
   messages. Sonnet 5.5 reads Sonnet 5 blocks; no other model reads Sonnet 5.5
   blocks.
4. **Computer use** needs `computer_toolset_20260801` on the Claude API and
   Google Cloud; `computer_20251124` is still accepted on Amazon Bedrock.
5. **Advisor tool** rejects Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5, and Sonnet
   4.6 as advisors for a Sonnet 5.5 executor; accepted advisors return encrypted
   advice.

One response-shape change fails no request: text between tool calls comes back
in `thinking` blocks ([Progress updates](#progress-updates)).

Unchanged from Sonnet 5: non-default `temperature`, `top_p`, or `top_k`, manual
`budget_tokens`, and assistant prefill still return 400 (`rules.md` P010, P011);
adaptive thinking is on by default; the tokenizer is the same. New relative to
Sonnet 5: per-message effort (beta), mid-conversation system messages, and
mid-conversation tool changes (beta); the minimum cacheable prompt drops to 512
tokens.

## Effort

Levels are recalibrated — a level does not produce the thinking it did on Sonnet
5, so re-sweep rather than carrying the Sonnet 5 value. The default stays `high`.

- **General work:** start at `high`.
- **Agentic coding and multistep tool use:** start at `medium` for
  well-specified tasks, `high` for harder or longer ones.
- **Chat and latency-sensitive work:** start at `medium` or `low`; higher effort
  means a longer wait before the reply starts.

Lower effort changes how agentic work finishes: at `low` it can skip verifying a
change ([Verification](#verification-on-coding-tasks)); at `low` and `medium`,
on long agentic tasks, it is more likely to stop and check in before finishing
(see [Initiative and scope](#initiative-and-scope)).

- Size `max_tokens` for thinking plus reply; for agentic coding, 128,000 (the
  maximum) with streaming.
- Reserve `xhigh`/`max` for measured quality gains; thinking and replies get much
  longer there, and `between_tools` is not accepted.
- For less thinking, **lower effort**. From `medium` up it thinks briefly before
  almost every reply, even a greeting; asking in the system prompt to think less
  does not reliably reduce it. At `low` it skips thinking on most simple
  requests.
- Changing top-level `effort` between requests breaks the prompt cache; use a
  per-message effort change (beta, adaptive thinking only — 400 with
  `between_tools`). Example: run a session at `low`, raise to `high` for a hard
  problem.

## Initiative and scope

How far it goes on its own depends on effort and on the request: lower effort
checks in early, higher effort or an open-ended request does more than asked.
Try the effort lever first.

**Carrying work through.** On agentic coding at `low` and `medium` it may pause
to confirm a plan, ask a question it could answer itself, or stop after one part
of a multipart task. To keep it working without changing effort:

```text
Keep working until everything the user asked for is done, and only stop to ask
when you can't go on without the user or before a risky step.

When the work the user asked for is done and checked, stop and report. Don't add
features, tests, files, docs or refactors that weren't asked for. If you think
one would help, mention it at the end instead of doing it.
```

Sessions at `low`/`medium` then run longer and cost more. The block does not
replace the document's own rules for risky or irreversible actions — keep those.

**Unrequested additions when coding.** At every effort level, more at higher
effort, it adds tests, documentation, and small supporting files that fit the
repository's conventions; the requested change itself stays close to what was
asked. This differs from Sonnet 5, which at `low`/`medium` scoped work to
exactly what was asked. Most teams welcome it. To limit changes to what was
requested, add only the second paragraph above ("When the work the user asked
for is done…"); at `xhigh`/`max` it also makes changes smaller overall.

**Thoroughness at `xhigh` and `max`.** After finishing it can start its own
review and verification rounds, sometimes with subagents, and make related fixes
it noticed. Run routine work at `high` or below, where this is rare. To keep the
extra thoroughness pointed at the task itself:

```text
When the work the user asked for is done and its checks pass, stop and report.
Don't start extra rounds of review or hardening on your own, and don't launch
reviewer sub-agents unless the user asked for a review. If you think a deeper
review is worth doing, say so at the end.
```

Measured on coding at `max`: stopped reviewer-subagent launches and cut session
cost by about a third with no quality change. Self-started review rounds by the
main agent become less frequent, not absent.

**Open-ended requests.** "Show me what you can do with this" can start a
presentation, report, or video when only ideas were wanted. Say so in the
request, or:

```text
When the user asks for ideas, options or a plan, give them that and stop. Don't
start building or changing anything until they say to go ahead.
```

## Running without up-front thinking

`thinking: {"type": "between_tools"}` is the lowest setting and replaces
`disabled`. For an integration that runs with thinking off today:

- **`high` effort or below only.** At `xhigh`/`max` it returns 400, and effort
  cannot change mid-conversation (a differing per-message effort returns 400).
  It takes no other field: `display`, `budget_tokens`, or `block_binding`
  alongside it returns 400.
- **Remove any instruction telling the model not to think.** Under
  `between_tools` such instructions make internal XML tags in the visible output
  more likely.
- **Read the response by block type.** It can begin with a progress-update
  `thinking` block.
- **Pass `thinking` blocks back unchanged.** Notes longer than a sentence or two
  still arrive as `thinking` blocks carrying a summary; the block sent back gives
  the model its full note.
- **Use adaptive thinking for reasoning without tools.** In a request without
  tools, `between_tools` answers without thinking first.

With server-side fallback, a `between_tools` request that falls back to Sonnet 5
runs there with `thinking: {"type": "disabled"}`.

## Reasoning tasks with JSON output

For a JSON answer to a task that needs a few steps of working out (totaling
figures, applying a rule, ranking), it often answers without thinking first,
especially at `low` and `medium`. Prefer structured outputs; the response text is
then schema-valid JSON, so the working can happen only in thinking. With adaptive
thinking, add at the end of the system prompt:

```text
Think the problem through before you answer.
```

At `high` this brings accuracy close to `xhigh` for a modest token increase; at
`low`/`medium` it raises accuracy (not to `high`'s level) at a larger token
cost. Alternatively run `xhigh`, the most accurate here even without the line.
Under `between_tools` the line has no effect. This is the opposite of the Opus
5.5 advice to remove "think carefully" lines from chat prompts — on Sonnet 5.5
the line is measured and targeted; keep it on these tasks.

With structured outputs at `low`/`medium` it occasionally thinks until
`max_tokens`. Treat any `stop_reason: "max_tokens"` response as failed even if it
holds valid JSON, and retry; cap `max_tokens` at what one attempt may cost.

Without structured outputs, it often works the problem in the response text and
puts the JSON at the end. Parse the **last** JSON value from the `text` blocks:
try to parse starting at each `{` or `[`, skip past each value that parses (so
nested values are not counted separately), keep the last one, check its fields,
and retry once if they are wrong. Never take everything from the first `{` to the
last `}` — it sometimes writes a draft before the final JSON. `xhigh` with
adaptive thinking nearly always returns the JSON alone at about `high`'s total
output tokens.

## Progress updates

Between tool calls it writes user-facing notes. Notes longer than a sentence or
two arrive as progress-update `thinking` blocks, empty at the default display;
shorter remarks stay `text`. On Sonnet 5 all of this was `text`, so a client that
renders only `text` blocks now looks silent.

1. Set `display: "updates"` (beta, `thinking-display-updates-2026-08-18`
   header), or `"summarized"` to get updates mixed with reasoning. Under
   `between_tools` the notes carry their text without `display`.
2. For exact text mid-turn (a code snippet, a question it needs answered), give
   it a simple send-message tool for that content only, declared in the first
   request so `tools` never changes.
3. Remove older instructions such as "hold all findings for the final response"
   (`rules.md` P013). For updates at set points (a line before the first tool
   call, a recap at the end), say so; it follows such instructions. Set points
   help most in human-in-the-loop work.
4. If turns still go quiet, have the harness count consecutive tool steps with
   no user-facing text; after about five, append a turn-scoped system message
   (beta) after the latest tool results:

```text
The user hasn't heard from you in a while — say in a few words what you're
doing, then continue.
```

Stop after the second or third reminder if the turn stays quiet — frequent
harness text after tool results can read as prompt injection ([Mid-turn user
messages](#mid-turn-user-messages)). Leave each reminder in `messages`; appending
keeps the cache and preserved thinking intact. Measured at `high` with a
send-message tool: more frequent updates, shorter silent stretches, no change in
task quality.

## Tool use in chat and knowledge work

On chat and knowledge work it sometimes answers from training knowledge where a
search would catch details that have changed — what is allowed, required, or
charged. First remove language that discourages tool use ("only use tools when
strictly necessary", "minimize tool calls"). Then, where the product has a search
tool:

```text
Use the search tool to check specifics that may have changed since your
training, such as what is allowed, required or charged, even when you feel
confident. For researched work such as a report or a comparison, gather current
sources rather than writing from your training knowledge.
```

Matters most for research and support products. This is a named condition, not
the blanket default `rules.md` P005 targets.

## Mid-turn user messages

Trained to resist indirect prompt injection, it sometimes treats a genuine user
message as one — telling the user the tool result contained text posing as them,
then ignoring the message or asking for confirmation. Triggers: user text
delivered as a mid-conversation system message right after a tool result or
inside a `tool_result` block; a token countdown after every tool result; harness
instructions or context appended after tool results on every step.

- Never put user text inside a `tool_result` block — the most frequent misread.
- Deliver mid-turn user input as a text block in the user message that carries
  the `tool_result` blocks, after the last `tool_result`.
- Keep harness notices in a separate mid-conversation system message after the
  user's words, never in the same block.
- In interactive sessions where users type mid-turn, add no custom token or
  budget countdown after tool results. Task budgets (beta) have not been seen to
  cause the misread; if it appears with one set, try without.

## Verification on coding tasks

It generally checks its work before reporting a change done, but at `low` it
sometimes skips a check that exercises the change (for example, skipping tests
because dependencies are not installed). Where transcripts show changes reported
complete without test or build output:

```text
When you change code that can be run, built, or type-checked, run a real check
that exercises the change before reporting it done: the project's tests,
type-checker, or build, or the changed command itself. A syntax-only check, or a
check command that failed to start, does not count; if all that is missing is the
project's declared dependencies, install them with its own package manager and
lockfile (e.g. npm install, pip install -r requirements.txt), never via sudo or
the system package manager, unless told not to. Only if no real check can run
here, say which one you did not run and why instead of reporting the change as
done.
```

Measured at `low`: skipped or superficial checks become rare, no change in task
quality, slightly higher cost. This is the one case where an audit should keep a
verification instruction on this model: it asks for a real check with evidence,
not the generic re-check `rules.md` P001 removes.

## Tolerant tool-call handling

It occasionally calls a declared tool by a name differing only in case (`bash`
for `Bash`) or passes a known parameter under a slightly different name. The
harness should not treat that as fatal: accept an unambiguous case-only match,
or return `is_error: true` stating the exact expected name — it usually
corrects on the next turn.

## Visual inputs

For dense charts and technical drawings, give it a way to crop, zoom, or run
code on the image. Tools help on charts at every effort level, and on technical
drawings only from `high` up (most at `xhigh`/`max`). For charts, tools beat
raising effort: with tools at `high` it read charts more accurately than without
tools at `max`, at a fraction of the cost.

## Safeguard refusals

A decline returns `stop_reason: "refusal"` with `stop_details.category` — more
categories than Sonnet 5:

- `cyber` — cyber harm; finding vulnerabilities in source code is allowed,
  high-risk dual-use work is not.
- `bio` — biological harm; everyday health and educational questions are
  unaffected. Blocked life-sciences work can apply to the Life Sciences
  Verification Program.
- `frontier_llm` — assisting development of competing AI models.
- `reasoning_extraction` — asking the model to reproduce its internal reasoning
  in the response text.
- `general_harms` — other usage-policy areas; benign work can trigger it.

Server-side fallback (beta) retries only `cyber` and `frontier_llm` declines,
**on Sonnet 5**; `bio`, `reasoning_extraction`, and `general_harms` come back to
the caller. Remove instructions that ask for reasoning in the response
(`rules.md` P003) and read `display: "summarized"` thinking blocks instead.

---

## Carried over from Sonnet 5

The Sonnet 5.5 page states the Sonnet 5 patterns remain a reasonable starting
point. These were **measured on Sonnet 5**; keep them unless re-testing on
Sonnet 5.5 shows they are no longer needed.

- **Literal instruction following.** Especially at lower effort it does not
  generalize an instruction from one item to another; state scope ("apply this to
  every section, not just the first").
- **Review harnesses.** "Only report high-severity issues" / "don't nitpick"
  lowers recall at the same investigation depth. Ask for full coverage with
  confidence and severity, filter separately (`rules.md` P002).
- **Response length.** Calibrated to task complexity — shorter on lookups,
  longer on open-ended analysis. Where the product needs a shape, prompt for it
  ("Provide concise, focused responses. Skip non-essential context, and keep
  examples minimal."); for one specific kind of verbosity, a positive example of
  the concision wanted beats an instruction about what to avoid.
- **Design and frontend defaults.** Open-ended briefs settle into a default
  style, and generic corrections ("make it clean") only move it to another fixed
  palette. Give a concrete spec (palette hexes, typeface, spacing and radius,
  section structure), or ask for options before building: "Before building,
  propose 4 distinct visual directions (each as bg hex / accent hex / typeface
  plus a one-line rationale). Ask the user to pick one, then implement only
  that." — still the variety lever, since sampling parameters still return 400.
- **Full spec up front.** Give task, intent, and constraints in the first turn.
  Sonnet 5's effort advice for interactive coding (`xhigh`/`high`) is superseded
  by [Effort](#effort).
- **Tone.** Re-evaluate style prompts against the new model rather than assume
  they still land.

Superseded by this page — do not carry forward: the Sonnet 5 effort ladder and
its Sonnet 4.6 mapping; the Sonnet 5 advice to steer thinking depth down by
instruction (lower effort instead); and the thinking-disabled tool-use nudge,
since `disabled` now returns 400 — the Sonnet 5.5 page does not say whether
`between_tools` shares that tool-use drop, so re-test before adding one.
