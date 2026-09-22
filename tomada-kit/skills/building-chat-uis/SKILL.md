---
name: building-chat-uis
description: >-
  Field notes for building LLM chat interfaces on the Vercel AI SDK (`ai` +
  `@ai-sdk/react`), whose API is renamed on a roughly six-month major cadence — so
  training data, blog posts, and parts of the official docs still show dead v4/v5 code.
  Covers the v7 API map and how to spot a stale snippet, what the SDK does not provide
  (persistence, thread management, screens), choosing a UI layer (AI Elements,
  assistant-ui, ChatKit, CopilotKit), and separating sessions and scoring from the chat
  library. Use when adding a chat or streaming LLM feature, writing or reviewing
  `useChat` / `streamText` / `generateObject` code, upgrading an AI SDK major, deciding
  which chat UI library to adopt, or designing a conversation-based practice,
  assessment, or intake flow.
metadata:
  platforms: claude-code, codex
---

# building-chat-uis

Without this skill, chat code gets written from memory of AI SDK v4/v5 — `input` and `handleInputChange` off `useChat`, `message.content` as a string, `system:` as a generation argument — all of which fail or are deprecated on current versions. The API has been renamed in every major, and stale examples survive inside the official repository.

## Establish the version first

Never write AI SDK code before checking what the project has:

```bash
npm ls ai @ai-sdk/react 2>/dev/null || grep -E '"(ai|@ai-sdk/)' package.json
```

Then match the guidance to that major. [references/v7-api-map.md](references/v7-api-map.md) covers v7 (`ai@7.x`, current as of 2026-09-15) and lists the tells that identify an older snippet. If the project is on v5 or v6, read its own migration guide rather than assuming these notes apply.

If the installed major is above 7, this skill is out of date: say so, work from `ai-sdk.dev` and `https://registry.npmjs.org/ai`, and treat everything here as a starting hypothesis.

**Do not trust a snippet because it is on ai-sdk.dev.** As of 2026-09-15 several cookbook and RSC pages in `vercel/ai` still carried v4-era code. Version-check the snippet, not the domain.

For anything version-sensitive, work from current sources rather than recall. `context7`'s `/vercel/ai` index lagged the live docs by a major as of 2026-09-15 — cross-check against `ai-sdk.dev`, `https://registry.npmjs.org/ai`, or the shipped type definitions (`unpkg.com/ai@<version>/dist/index.d.ts`, which cannot be stale by construction).

## What the SDK does not do

Expecting any of these from the SDK produces a broken design:

- **Persistence.** No thread management, no history storage. The official persistence page is a sample with no authorization and no error handling. A database is required.
- **Screens.** `useChat` is a state machine. No bubbles, no composer, no scrolling. See [references/ui-layer-choice.md](references/ui-layer-choice.md).
- **Stable values.** `generateObject` enforces and validates the *shape* of output. Keeping scores from drifting is a rubric, temperature, and model-pinning problem.
- **Cancelling spend.** `stop()` aborts the client request; the server keeps generating and billing.

## Traps that cost the most time

| Trap | Reality |
|---|---|
| `useChat` owns the input field | The app holds it in its own state — since v5 |
| `system:` on a generation call | v7 takes `instructions`; a `system` message inside `messages` is rejected by default |
| `onFinish` everywhere | v7 server side is `onEnd`; client `useChat` is still `onFinish` |
| `message.content` | `message.parts[]` — filter `type === 'text'` for readable text |
| Provider packages should match the core major | `ai@7.x` pairs with `@ai-sdk/openai@4.x`; compatibility rides on `@ai-sdk/provider` |
| `result.toUIMessageStreamResponse()` | Deprecated in v7 for the top-level `createUIMessageStreamResponse()` |
| Node 18/20, CommonJS | v7 needs Node 22+ and is ESM-only |
| Resumable streams are a flag | They need Redis, the `resumable-stream` package, and your own stream-ID tracking |
| assistant-ui means a sidebar | `Thread` works standalone |

## Separate the conversation from the record

When the conversation is a means to an end — practice, assessment, intake, triage — sessions, scores, and history are business data. They do not belong in a chat library's thread abstraction, because the UI library is the part you are most likely to replace.

Two calls, not one prompt: `streamText` for the conversation (optimize for time to first token), `generateObject` for assessment after it ends (optimize for stable structure). One system prompt asked to both converse warmly and grade strictly does neither well. The model returns per-criterion scores with evidence; **the pass threshold lives in application code**.

Full treatment, including session boundaries, transcript extraction, and what to cut from a first version: [references/session-architecture.md](references/session-architecture.md).

## Choosing the UI layer

The deciding question is how much of the screen is *not* the chat, not which library has more features.

- Already on Next.js + shadcn/ui + Tailwind → **AI Elements** (Vercel's registry; copies source into the repo, no dependency added).
- Otherwise, or when branching / editing / virtualization are wanted out of the box → **assistant-ui** (`Thread`, dropping to primitives for custom layouts). On AI SDK v7 as of 2026-09-15.
- **ChatKit** and **CopilotKit** do not connect to `useChat` at all — each brings its own protocol. Pick one only for a reason specific to it.

Details, licenses, and the comparison table: [references/ui-layer-choice.md](references/ui-layer-choice.md).

## Resources

- [references/v7-api-map.md](references/v7-api-map.md) — read before writing or reviewing AI SDK code: release cadence, stale-snippet tells, the v7 rename table, `useChat` surface, `parts`, transport, structured output, agent loop, persistence, standalone use.
- [references/ui-layer-choice.md](references/ui-layer-choice.md) — read when picking or questioning a chat UI library.
- [references/session-architecture.md](references/session-architecture.md) — read when the conversation is not itself the product: session boundaries, conversation vs. assessment calls, transcript extraction, result screens, first-version cuts.
