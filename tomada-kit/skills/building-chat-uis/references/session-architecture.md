# Session architecture

For apps where the conversation is a means to an end — practice, assessment, intake, triage — rather than the product itself.

## Three layers, kept apart

1. **Model calls** — which model says what. Swappable.
2. **Conversation protocol** — message shape, streaming, tools, errors. This is the AI SDK.
3. **Screen** — bubbles, composer, scroll, result view.

Sessions, scoring, and history belong to **none of them**. They are business data. Storing them inside a chat library's thread abstraction couples your durable records to a UI dependency you will eventually replace.

The AI SDK has no persistence at all, so a database is required regardless. Point it at your own schema from day one.

## The session is the product

An open-ended chat has no natural end, which means no natural moment to score, save, or summarize. Decide what bounds one session before anything else:

- elapsed time, or
- a turn count, or
- a task being completed.

Everything downstream depends on this. A session without an ending has ambiguous scoring and ambiguous storage.

The unit people revisit is the **session**, not the message. "Yesterday's negotiation practice", not message #47. Model history that way.

## Conversation and assessment are different calls

Do not put "be an encouraging partner" and "grade strictly" in one system prompt. Tone and scores both degrade.

| | Conversation | Assessment |
|---|---|---|
| Call | `streamText` | `generateObject` + schema |
| Optimize for | time to first token | stability of the output |
| Timing | every turn | once, after the session ends |
| Input | recent turns | the full transcript |

Grading on every message is slow, expensive, and breaks the flow the user is supposed to be practising. Corrections mid-conversation should be short if they appear at all; the real verdict comes at the end.

**The model reports; the app decides.** Have the model return per-criterion scores with evidence. Keep the pass threshold in application code. A model asked "did they pass?" gives an opinion that drifts between runs and cannot be tuned without re-prompting.

The schema enforces shape, not stability. Score consistency comes from a concrete rubric, low temperature, and pinning the model version.

## Extracting the transcript

`UIMessage.parts` mixes rendered text with tool calls, reasoning, and data parts. Assessment should see what a human would have read:

```ts
const transcript = messages
  .filter(m => m.role === 'user' || m.role === 'assistant')
  .map(m => ({
    role: m.role,
    text: m.parts.filter(p => p.type === 'text').map(p => p.text).join(''),
  }));
```

Feeding raw `parts` to a grader leaks internal machinery into the judgement.

## Failure is the normal path

In a practice app, people stop mid-sentence, retry, and rephrase constantly. Retry, stop, and resend are primary controls, not error handling.

- `stop()` cancels the client request only — server generation and its cost continue.
- `regenerate()` works from `ready` or `error`.
- Resumable streams need Redis and stream-ID tracking. Skip them in a first version; revisit if disconnects prove common.

## The result screen is not more chat

Show the transcript, the scores, the verdict, and the specific rewrites separately. Appending the assessment as another assistant bubble buries the one thing the user opened the app for.

## Mobile

Practice apps skew mobile, where the on-screen keyboard covers the composer. Pin the composer and scroll the transcript independently. Verify on a real device — this is where desktop-built chat UIs fall over.

## First-version cuts

Drop, in this order:
- resumable streams (Redis)
- voice input — text quality decides whether the product works at all, and audio makes storage and assessment much harder
- multi-session analytics
- thread lists and conversation search

Keep: the session boundary, end-of-session assessment, and stored history. Those three are the product.
