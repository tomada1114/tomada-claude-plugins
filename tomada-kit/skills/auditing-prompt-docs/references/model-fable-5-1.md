<!-- audit-ignore-file: A006 -->
<!-- prompt-lint-ignore-file: P001,P004,P006,P008,P012,P013 -->
# Prompting Claude Fable 5.1

Covers Claude Fable 5.1 and Claude Mythos 5.1. Existing Fable 5 prompts perform
well without changes; the sections below are the behavioral differences worth
knowing. Provenance in `sources.md`.

Thinking is always on and adaptive is the only mode. Safety classifiers can
return `stop_reason: "refusal"`.

## Table of Contents

- [Symptom index](#symptom-index)
- [Effort](#effort)
- [Progress updates](#progress-updates)
- [Tool-call batching in agent loops](#tool-call-batching-in-agent-loops)
- [Append-only conversation history](#append-only-conversation-history)
- [Writing density](#writing-density)
- [Formatting in chat](#formatting-in-chat)
- [Quoting retrieved sources](#quoting-retrieved-sources)
- [Finishing the whole task](#finishing-the-whole-task)
- [Compaction summaries](#compaction-summaries)
- [Scope and test coverage](#scope-and-test-coverage)
- [Search triggering at low effort](#search-triggering-at-low-effort)
- [Safeguard false positives](#safeguard-false-positives)
- [Targeted edits over rewrites](#targeted-edits-over-rewrites)
- [Long outputs at high effort](#long-outputs-at-high-effort)
- [Subagents and vision](#subagents-and-vision)

---

## Symptom index

| What you observe | Section |
|---|---|
| Little or no text between tool calls | [Progress updates](#progress-updates) |
| One tool call per turn in an agent loop | [Tool-call batching](#tool-call-batching-in-agent-loops) |
| `bound to a different conversation` errors | [Append-only history](#append-only-conversation-history) |
| Prose runs long and dense | [Writing density](#writing-density) |
| Replies carry less structure than the content needs | [Formatting in chat](#formatting-in-chat) |
| Summaries reproduce source wording unmarked | [Quoting retrieved sources](#quoting-retrieved-sources) |
| Turn ends before the work is done, or asks permission for requested work | [Finishing the whole task](#finishing-the-whole-task) |
| Unrequested fixes, or more test files than the task called for | [Scope and test coverage](#scope-and-test-coverage) |
| Answers from memory instead of searching | [Search triggering at low effort](#search-triggering-at-low-effort) |
| Benign coding requests return a refusal | [Safeguard false positives](#safeguard-false-positives) |
| Whole files rewritten for small changes | [Targeted edits](#targeted-edits-over-rewrites) |
| Long deliverables hit `max_tokens` | [Long outputs](#long-outputs-at-high-effort) |

## Effort

Start at `high`, then sweep `low`, `medium`, `xhigh`, and `max` against your own
evals. Re-run the sweep even after one on Fable 5 — effort names do not
correspond to the same amount of thinking across models.

Gains over Fable 5 show at every level and are largest at the high end. At
`medium`, results roughly match Fable 5 at lower cost. At `low` it is often
competitive on cost per task with smaller models while scoring higher, so
include it wherever you would otherwise run a smaller model at higher effort.

## Progress updates

It writes fewer user-facing updates during long tool-calling turns than Fable 5,
more so at higher effort and in longer chains. Users see minutes of silence, or
a final message covering only the last step.

Check three things in order:

1. **Is the client receiving them at all?** Short notes between tool calls come
   back as progress-update thinking blocks, which are empty under the default
   `thinking.display` of `"omitted"`. Set `display: "updates"` and render each
   non-empty block as a status line, or use `"summarized"`.
2. **Does the prompt suppress narration?** Lines like "hold all findings for the
   final response" were written for models that over-narrated. Remove them
   before adding anything.
3. **Then ask for what you want:**

```text
Before you start, say in a line what you're about to do; brief updates while you
work help the user follow along. Close with a short recap that stands on its own
— what you found, what you did, and what's next — so a reader who only sees the
last message has the full picture.
```

If the product collapses or hides tool output, say so, or the model will run
commands to "show" the user output the UI never displays.

## Tool-call batching in agent loops

Parallel calls work as expected when a request names several things to fetch.
The exception is coding and computer-use loops where the next independent calls
are implied by the task rather than requested: there it may issue one per turn.
Answer quality is unaffected; each extra turn costs tokens and a round trip.

```text
First privately list what you need next; then request every item that doesn't
depend on another's result in this one response.
```

Send it as a turn-scoped system message appended after each round of tool
results, appending a fresh copy each turn and leaving earlier copies byte-for-byte
in place — deleting or rewriting them is an edit to earlier turns.

## Append-only conversation history

Append each assistant turn exactly as returned, thinking blocks included, and do
not edit earlier turns between requests. On newer accounts a thinking block is
valid only in the exact conversation that produced it: replaying one after its
prefix changed returns 400 (or drops the block if you opt in).

The edits that trip this are the same ones that restart the prompt cache:
injecting and removing per-turn reminders, summarizing older turns in place,
rebuilding `system` or `tools` mid-session. Use turn-scoped system messages for
per-turn reminders, mid-conversation system messages for instruction changes,
and server-side compaction or context editing for trimming. Client-side
compaction is safest as a full replacement: one summary message plus the new
user turn, replaying nothing else.

## Writing density

Writing is a step up overall — fewer stock phrases, less unexplained jargon —
but prose can be denser than Fable 5's, with longer sentences and fewer
paragraph breaks. Define the anti-pattern rather than asking for shorter text:

```text
Mannered prose substitutes metaphor and flourish for direct statement. Instead
of "a parameter worth varying," the mannered writer produces "a dial worth
turning." The phrases exist to display the writer, not to convey the idea, and
readers can tell. It is also imprecise: metaphors drag in connotations the
writer did not choose. The fix is to say what you mean. When a literal phrase is
available, use it.
```

"Please remove all mannered prose" also tends to work.

## Formatting in chat

It uses bold less and is less likely to reach for headers, lists, or quotation
marks. Anti-formatting language inherited from earlier models suppresses
structure the content needs — remove it, or replace it with a rule that says
when formatting is appropriate:

```text
Use lists and bullet points when asked to, or when the content is multifaceted
enough that they help with clarity. If the person explicitly requests minimal
formatting, format without bullet points, headers, lists, or bold emphasis. In
conversational, personal, or emotional exchanges, keep to plain prose.
```

## Quoting retrieved sources

When summarizing documents it is more likely than Fable 5 to reproduce source
passages without marking them as quotations. The fix is one complete example in
the system prompt: the user's request, a correct response, and a rationale
sentence explaining why it is correct — the response organized around where
sources agree and differ, each conveyed in the assistant's own indirect speech,
with at most one short marked phrase quoted.

## Finishing the whole task

On complex asynchronous work it sometimes describes what it would do next
instead of doing it, or stops to ask permission for a step the original request
already covered. Two system prompt additions together mitigate it; the first
carries most of the effect:

```text
You are operating autonomously. The user is not watching in real time and cannot
answer questions mid-task, so asking 'Want me to…?' will block the work. For
reversible actions that follow from the original request, proceed without
asking. Stop only for destructive actions or genuine scope changes the user must
decide.

Exception: when the user is describing a problem, asking a question, or thinking
out loud rather than requesting a change, the deliverable is your assessment.
Report your findings and stop.

Before ending your turn, check your last paragraph. If it is a plan, an
analysis, a question, or a promise about work you have not done, do that work
now with tool calls. That includes retrying after errors and gathering missing
information yourself. Do not stop because the session is long.
```

Keep the opening sentence as written — it carries much of the effect. The block
also makes the model less likely to ask about genuinely ambiguous requests, so
check that trade-off. The second addition defines the user's request as the
scope of the deliverable; see `general-practices.md#scope-control`.

## Compaction summaries

It responds well to being told exactly what a compaction summary must retain.
Server-side compaction already does this. For client-side compaction, require:
difficulties and how they were resolved; options raised, tried, or set aside and
why; anything asked for, decided, agreed, ruled out, or established as a
constraint, stated exactly; where things stand; what is still open; and details
hard to reconstruct (names, numbers, dates, exact wording, links). Weight the
two voices differently — keep the user's words closely, condense the
assistant's reasoning to its conclusions.

## Scope and test coverage

On open-ended feature work it may fix nearby code, extend unmentioned behavior,
or commit more test files than the change warrants:

```text
If, while working or testing, you find a pre-existing bug, a performance
concern, or behavior the task doesn't mention, don't fix, optimize or extend it
in this change unless the requested behavior cannot work without it; report it
as a follow-up in your summary. Where the task is ambiguous, implement the
reading its wording and the surrounding code most directly support, and state
that assumption. Commit tests only where the task asks for them or the
repository already keeps tests for this kind of change, sized like the
neighboring test files. This is about extras only: implement every behavior the
task asks for, completely.
```

## Search triggering at low effort

At `low` it calls search and retrieval tools less often and answers from memory
more. Often the simplest fix is raising effort for the affected turns. Otherwise:

```text
When a query centers on a name you do not confidently recognize, or recognize
from a fast-moving area like AI models and developer tools, the name itself is
the thing to verify: search before answering, and include the name as the user
wrote it in at least one query. Partial background is exactly what makes an
out-of-date answer sound authoritative, so familiarity is not a reason to skip
the search.
```

## Safeguard false positives

Classifiers produce fewer false positives than at Fable 5's launch, and finding
vulnerabilities in source code is permitted. Three situations still raise the
rate: compile-check phrasing (ask "are there any bugs in this program?" rather
than "does this compile without errors?"), lesser-known programming languages
(supply the language's documentation), and base64 data returned into context by
a tool (remove it).

## Targeted edits over rewrites

It is more likely than Fable 5 to rewrite an entire text file rather than make a
targeted edit. The result is usually the same file at more output tokens and
more time.

```text
The number of tokens used to edit files is best minimized, all else being equal.
Therefore, when it will not affect the end result, try to surgically edit a file
rather than rewrite the entire thing.
```

## Long outputs at high effort

At `xhigh` and especially `max` it can draft much of a long deliverable in
thinking and then write it out again as the reply — a longer wait and double the
output tokens. Run these requests at `high` unless a quality gain is measured.
Where they do run higher, set `max_tokens` to cover thinking plus reply, and
append a note to the user message stating that both share one limit, that a
doubled draft would not improve the result, and that the reasoning space is for
settling structure and difficult decisions rather than composing the output
twice.

## Subagents and vision

Do not force the lead agent to stop and wait for each subagent. On coding tasks,
letting the lead continue lowers average time to completion at similar quality
and cost: have the spawn tool return immediately, deliver each result in a later
user message, and give the lead a separate tool for when it wants to wait.

For vision work on dense charts, give it a container with the raw images and
basic image-processing libraries, or at minimum a crop tool that returns a
chosen region enlarged. That scales test-time compute with image tokens and
delivers most of the uplift on its own.
