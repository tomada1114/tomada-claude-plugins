<!-- audit-ignore-file: A006 -->
<!-- prompt-lint-ignore-file: P001,P003,P004,P006,P008,P009,P010,P012,P013,P014,P016,D002 -->
# Prompting Claude Fable 5.2

Covers Claude Fable 5.2 and Claude Mythos 5.2. Built for demanding reasoning and
long-horizon agentic work; Anthropic's own advice is to start most workloads on
the latest Opus and move here when Opus at higher effort still falls short.
Provenance in `sources.md`.

Fable 5.2 follows what a prompt says more closely than its predecessors — about
approvals, code ownership, caution, and style. Most sections below are that one
trait seen from a different side, and most fixes are deletions.

## Table of Contents

- [Symptom index](#symptom-index)
- [API facts that shape prompts](#api-facts-that-shape-prompts)
- [Effort](#effort)
- [Finishing the whole task](#finishing-the-whole-task)
- [Approvals](#approvals)
- [Code ownership](#code-ownership)
- [Progress updates](#progress-updates)
- [Subagents](#subagents)
- [Caution that piles up](#caution-that-piles-up)
- [Instructions written for earlier models](#instructions-written-for-earlier-models)
- [Final reports](#final-reports)
- [Safeguard refusals](#safeguard-refusals)
- [Migration order](#migration-order)
- [Fable 5.1 items not restated](#fable-51-items-not-restated)

---

## Symptom index

| What you observe | Section |
|---|---|
| Easy requests take too long; unsure which effort to run | [Effort](#effort) |
| Turn ends with a list of what remains, an offer to continue, or a stop at a timeout | [Finishing the whole task](#finishing-the-whole-task) |
| Routine steps wait for approval nobody needs to give | [Approvals](#approvals), [Caution that piles up](#caution-that-piles-up) |
| Repeats existing code instead of merging it; reports nearby problems without fixing them | [Code ownership](#code-ownership) |
| Long silent stretches of tool calls; no opening line | [Progress updates](#progress-updates) |
| Starts more subagents than the task needs | [Subagents](#subagents) |
| Prose turns choppy under a style rule | [Instructions written for earlier models](#instructions-written-for-earlier-models) |
| Final report assumes context the reader never saw | [Final reports](#final-reports) |
| `bound to a different conversation` 400 errors | [API facts](#api-facts-that-shape-prompts) |
| `stop_reason: "refusal"` | [Safeguard refusals](#safeguard-refusals) |

## API facts that shape prompts

- **Thinking is always on, adaptive only.** `budget_tokens` and
  `thinking: {"type": "disabled"}` return 400. Effort is the control.
- **Forced tool use returns 400** (`tool_choice` of `any` or a named tool). Keep
  `auto` and use `strict: true` or JSON outputs for schema-valid results.
- **The prefix check applies to every account.** Changing `system`, `tools`, or
  an earlier message invalidates every later thinking block, and the request
  returns 400. So every prompt change this file suggests goes into **new
  conversations only**; mid-conversation, put the new instruction in the newest
  turn or append a mid-conversation system message. Keep history append-only and
  trim with server-side compaction or context editing. Claude Code, claude.ai,
  Managed Agents, and the Agent SDK already do this.
- **Thinking blocks are bound to the model.** Moving a conversation from Fable
  5.2 to any other model (Opus 5.5 included) loses its reasoning for those turns;
  moving onto Fable 5.2 keeps it.
- **Advisor tool:** a Fable 5.2 executor accepts only a Fable 5.2 or Mythos 5.2
  advisor.
- 1M context, 128k max output. $8 / $40 per MTok (Fable 5.1 was $10 / $50).

## Effort

Start at `high`, the API default, and re-run the sweep rather than carrying over
a level tuned on Fable 5.1 or Opus 5.5 — level names order the same way across
models but do not mean the same amount of thinking.

| Level | Use for |
|---|---|
| `low` | Quick back-and-forth, well-specified tasks, high-volume subagents. Scores sat close to Fable 5.1 at higher levels. |
| `medium` | Interactive coding, chat, everyday knowledge work. |
| `high` | Hard coding, research, agentic work, long unattended runs. Turns take noticeably longer than at `medium`. |
| `xhigh` | The hardest long-running work, only where a gain was measured: slightly higher scores, many more tokens. |
| `max` | Measuring the ceiling; open-ended problems where time and tokens do not matter. |

Most of the capability gain is already present at `high`, and the `medium` →
`high` step is the one that raised scores on most tracked evals. Above `high`
gains are uneven.

Three behaviors follow from the level:

- **Lower effort stops early more often.** For agentic work at `low` or
  `medium`, add the text in [Finishing the whole task](#finishing-the-whole-task).
- **At `high` and above it thinks before almost every reply**, greetings
  included. An instruction to answer directly without deliberating did not stop
  thinking at `medium` and above. Lower the effort for easy turns; delete the
  instruction.
- **Effort barely changes reply length.** Length and tone are a prompt matter.

Levels can be mixed in one workflow — plan and iterate at `medium`, raise effort
for the long unattended part. Use a per-message effort change (beta) to keep the
prompt cache; changing top-level `effort` restarts it.

## Finishing the whole task

On long multistep work it sometimes closes a turn with a list of what remains,
an offer to continue, or a stop at an ordinary obstacle such as a timeout — more
often at `low` and `medium`. The tested system-prompt text:

```text
# Finishing work
Please avoid stopping while you still owe work the user asked for. Be persistent
and do not stop unless needed.

While status notes are welcome, as is clarifying with the user on open
decisions, carry on with work that does not depend on the user's answer without
unnecessary stops.

If you notice yourself inviting the user to redirect you or offering to wait,
instead proceed on the next part of the task. You may meet ordinary obstacles
like errors, timeouts, locked files, empty results or failing tools. Diagnose
them first, and when they are not real blockers, work through them with the
access you have (wait and retry, fix the request, use another tool or source)
rather than stopping unnecessarily.

If someone clearly decided something is a hard blocker, such as a file marked
not to be touched, access that was intentionally withheld, or a safety
guardrail, leave it alone, say plainly what you found, and look for another safe
way to finish the task. Stopping before the task is complete is very rarely
merited, as in when the task can't move forward without user input, or where the
blocker is deliberate and should not be worked past. This does not override the
need for confirmation on risky or destructive actions.
```

The distinction to keep when adapting it: **ordinary obstacles** are diagnosed
and worked through; **deliberate blockers** are left alone and reported.

Measured at `medium` on replayed coding sessions: about half as many sessions
ended with doable work left, at roughly 30% more output tokens. It removes most
endings that ask permission or offer to continue, but not endings that list what
remains and stop. Because the model asks less, keep a harness-side confirmation
step for risky or irreversible actions.

## Approvals

- **Say what you are approving.** "Yes, run the migration on the staging
  database", not "go" or "continue".
- **Name the exact actions an approval rule covers.** The model applies the rule
  as written: a rule that listed "sending messages to people outside this
  conversation" made it hold back about half of its routine requests to
  colleagues and other teams.

## Code ownership

The model reads who owns the code from the prompt. Told nothing, or told the
code is someone else's, it adds to the existing structure — repeating code where
needed — and reports nearby problems rather than fixing them. To have it improve
structure as it works:

```text
This codebase is yours: what it's for and how it's built are your call, and
you'll keep building on it.
```

With the sentence it merged repeated code in about half of tries (under a tenth
without). The cost: about 1.5× the output tokens, unrequested changes (often new
tests and docs), and a behavior change to an existing feature in one try in six
to ten, more at higher effort. Its summary names the larger changes and often
omits small ones, so review the diff.

Leave the sentence out where the user owns the code and wants minimal change. A
scope rule elsewhere does not cancel it: with "No drive-by refactors, renames or
cleanups" in the same prompt, it still merged code in about a third of tries.

## Progress updates

It can run long tool-call chains with little user-facing text, and may make its
first tool call without saying what it is about to do. In order:

1. **Check the client receives updates.** Between-tool updates come back as
   progress-update `thinking` blocks, empty under the default
   `thinking.display: "omitted"`. Set `"updates"` (beta) or `"summarized"` and
   render the non-empty blocks.
2. **Harness reminder (most effective).** Count consecutive tool-calling steps
   with nothing for the user to read; after several, append a turn-scoped system
   message. It roughly halved the longest silent stretch at no noticeable cost.
   Leave each copy in `messages` afterwards.

   ```text
   The user hasn't heard from you in a while: say in a few words what you're doing, then continue.
   ```

3. **System prompt, for an opening line and a closing recap** (about 20% more
   output tokens; use where a human is in the loop):

   ```text
   Before you start, say in a line what you're about to do; brief updates while
   you work help the user follow along. Close with a short recap that stands on
   its own (what you found, what you did, and what's next), so a reader who only
   sees the last message has the full picture.
   ```

4. **Where the harness cannot be changed:** "Every few tool calls, give the user
   a one-line update on where things stand."

Expect runs of several tool calls between updates even with all of these. For
asynchronous work the user returns to, the gaps matter less.

## Subagents

Delegation depends on the harness: with a minimal spawn tool on short tasks it
rarely delegates; in a coding product whose prompts invite delegation it
delegates readily. At `xhigh` and `max` it also used subagents to review its own
work, which Fable 5.1 did not. It works well as planner and orchestrator for
other models. Subagents can be a large share of session cost — check which model
the harness runs them on by default.

Order of fixes when it over-delegates:

1. Review the lines in system prompts, skills, and agent files that tell it to
   delegate. Remove what is no longer needed.
2. Only then rewrite the spawn tool's description: state what a subagent costs
   the session (first), when delegation is and is not worth it, and how to brief
   one. That cut delegation by about a third at equal task success. Say less
   about cost if it then delegates too little.

## Caution that piles up

Cautious instructions accumulate wherever context carries over — memory, notes,
instruction files, messages between agents — and Fable 5.2 follows them
closely, so it asks for approvals it does not need or holds back routine work.
Seen mostly in multi-agent setups.

- **Remove notes no longer needed.** One note among a dozen saying never to
  retry cut retries after a busy tool from nearly all tries to about four in
  ten.
- **Name the steps that need no approval.** Listing retries among them raised
  retries from almost none to about half. A general instruction to act more
  freely changed nothing. Name retries only for calls that are safe to repeat.
- **Check what reviewer agents attach.** A reviewer's "stop at the first error"
  in context suppressed retries in a third of tries despite a line allowing
  them; Fable 5.1 and Opus 5.5 retried.
- **Write the exception into the rule.** Under a bare "never" rule the model
  took an approved step in about one try in ten; a separate line saying approved
  steps may proceed barely moved that. With the rule itself saying "get a
  go-ahead first", about nine in ten.

## Instructions written for earlier models

Reconsider each when a prompt, skill, or harness moves to Fable 5.2:

| Carried-over instruction | On Fable 5.2 | Do |
|---|---|---|
| Standing instructions to delegate | Starts more subagents than tasks need | Remove (see [Subagents](#subagents)) |
| A token budget written into the prompt by the harness | Budget size changes spend; removing a large one lowered cost at equal performance (`high`/`xhigh` coding) | Test without it. Not about the API's task budgets |
| Harness code that edits earlier turns | Invalidates later thinking blocks; 400, or re-thinking and more output tokens with `drop_block` | Keep history append-only |
| "Treat that answer as done" chat lines (from the Opus 5.5 guide) | Less thinking on follow-ups, but far less likely to point out mistakes in its earlier answers | Leave out where self-correction matters; test elsewhere |
| "Answer directly without deliberating" | No effect at `medium` and above | Remove; lower effort |
| Hard style limits ("one instruction per sentence, 20 words or fewer") | Followed closely; prose turns choppy | Remove before adding the [Final reports](#final-reports) text |
| Accumulated cautions in memory, notes, rules — some written by the model itself | Over-asking, withheld routine work | Delete those whose reason no longer holds; give absolute rules a scope and a reason. If a system is stuck, restart it with trimmed memory and keep a copy |
| "Write out your reasoning" | `reasoning_extraction` refusal | Remove; read summarized thinking blocks instead |

## Final reports

Readers of a final report after long agentic work have not seen the tool calls
or files behind it. The tested system-prompt text:

```text
# Communicating clearly
Write for an intelligent but low-context reader. The person reading has not seen
your tool calls, your reasoning or the files you opened, and may be switching in
from other work. Messages should generally be self-contained: the reader should
understand what you mean without having to dig for other context. Put the key
points in the first few sentences. Practice progressive disclosure in your
sentence order, and do not use undefined references and ideas in line 1 that
won't make sense until the reader reaches line 12.

Use plain words, and write in clear, understandable full sentences. Do not use a
term or abbreviation that you made up during the work. Say what the thing is in
a way any reader would understand. Write mostly in the style of ASD-STE100
Simplified Technical English: short sentences, one idea per sentence, active
voice, and consistently using the same word for the same thing. Use a paragraph
of flowing prose where ideas connect, and keep bullets for lists of separate
items. Leave out unnecessary details unless the reader asks and practice
concision, but do ensure that your messages have the key context. Aim to make
your user-facing text as human-readable and clear as possible.
```

It made reports less dense, with shorter sentences on workflow tasks. Add length
or required-detail instructions on top as needed.

## Safeguard refusals

A declined request returns `stop_reason: "refusal"` with
`stop_details.category`: `cyber`, `bio`, `frontier_llm`, `reasoning_extraction`,
or `general_harms`. Benign security and life-sciences work can trigger `cyber`
and `bio`; Anthropic's verification programs (and Mythos 5.2) exist for that.
Remove any instruction that asks the model to write its reasoning into the
response, and read thinking blocks with `display: "summarized"` instead.
Permitted fallback targets are Opus 4.8 and Opus 5; `reasoning_extraction` has
no fallback.

## Migration order

1. Set `effort` to `high` explicitly, then run evals at `medium` and `xhigh`.
2. Read every carried-over system prompt, skill, agent file, memory file, note,
   and harness text against
   [Instructions written for earlier models](#instructions-written-for-earlier-models).
3. Run the longest agentic tasks. Note where it stops early, asks for unneeded
   approvals, goes quiet, over-delegates, or adds to code you wanted
   restructured.
4. Apply the fix for each observed behavior one at a time, measuring effect and
   token cost.

## Fable 5.1 items not restated

The Fable 5.2 page does not repeat these Fable 5.1 findings. Only the first is
confirmed for 5.2; treat the rest as measured on 5.1 and re-test before adding
their text to a 5.2 prompt. Full wording:
[Prompting Claude Fable 5.1](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1).

- **Append-only history — confirmed, and stricter** (see
  [API facts](#api-facts-that-shape-prompts)).
- **Tool-call batching in agent loops.** One independent call per turn where the
  next calls are implied rather than requested; fixed by a turn-scoped reminder
  to request every independent item in one response.
- **Formatting in chat.** Under-formats; inherited anti-formatting blocks
  suppress structure the content needs.
- **Writing density.** Dense prose; define "mannered prose" rather than asking
  for shorter text. On 5.2, prefer the [Final reports](#final-reports) text.
- **Search at `low` effort.** Answers from memory more; raise effort or name the
  class of query to verify.
- **Scope and test coverage.** Extra fixes and test files on open-ended feature
  work. On 5.2 this interacts with [Code ownership](#code-ownership).
- **Whole-file rewrites** for small edits; **doubled long outputs** at
  `xhigh`/`max` (drafted in thinking, written again).
- **Quoting retrieved sources** unmarked; **compaction summaries** respond to an
  explicit retention list.
- **Safeguard false positives** on compile-check phrasing, lesser-known
  languages, and base64 in tool results.
- **Lead agent should not block on each subagent**; give vision work a crop tool
  or an image-processing container.
