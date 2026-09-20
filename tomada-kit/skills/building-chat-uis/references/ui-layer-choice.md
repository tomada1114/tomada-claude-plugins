# Choosing the chat UI layer

`useChat` is a state machine, not a UI. It gives you `messages`, `status`, and the send/stop/regenerate transitions. Bubbles, the composer, auto-scroll, markdown rendering, and virtualization are someone else's job.

Verified 2026-09-15.

## The question that decides it

Not "which library has more features" but **how much of the screen is not the chat**.

- The whole screen is the conversation → take the most finished thing that still lets you restyle it.
- The conversation is one panel among several (a brief, a timer, a score, a result view) → take building blocks, not a finished surface.

A product with a prompt before the conversation and a result after it is the second case, even though it looks like a chat app.

## Options

### AI Elements (Vercel)

Registry, not a package. `npx ai-elements@latest add <component>` copies source into your repo (default `@/components/ai-elements/`); from then on it is your code. Apache-2.0.

Requires Next.js, shadcn/ui initialized, Tailwind CSS 4 (CSS-variables mode), React 19. Effectively React/Next-only.

Components: Conversation, Message, PromptInput, Response, Reasoning, Sources, Tool, Chain of Thought, plus code (Artifact, Code Block, Sandbox), voice, and workflow sets. No thread list, no history — it is a parts bin.

Best when the project is already Next.js + shadcn/ui + Tailwind, and you want to own and edit the markup.

### assistant-ui

npm library (`@assistant-ui/react`), MIT. Very active (GitHub ~12k stars, pushed daily as of 2026-09-15).

**On AI SDK v7.** `@assistant-ui/ai-sdk@0.0.6` depends on `ai@^7.0.93` and `@ai-sdk/react@^4.0.96`. Prose in its own docs still says the runtime wraps "AI SDK v5" — that text is stale; check the package dependencies, not the sentence.

Three tiers: **Primitives** (unstyled, accessible building blocks) → **Elements** (styled) → **Examples** (full ChatGPT/Claude-style templates).

**`Thread` works without `ThreadList`.** "Adopting assistant-ui means a sidebar layout" is a myth. For a layout where the conversation is one panel among several, compose `ThreadPrimitive` / `ComposerPrimitive` / `MessagePrimitive` directly.

Ships markdown, auto-scroll, message virtualization, branching, editing, resumable streams, file upload, voice. Radix-based, accessibility-conscious.

Assistant Cloud (paid) adds hosted thread persistence and analytics. It is optional; the library runs against your own backend and your own database.

### OpenAI ChatKit

Embeddable widget — React hook `useChatKit` or the `<openai-chatkit>` web component. Frontend is Apache-2.0.

**Does not connect to `useChat`.** It has its own client SDK and its own backend protocol.

Backend is either OpenAI-managed or self-hosted via the `openai-chatkit` **Python** SDK (`ChatKitServer`). Self-hosting is real: the inference body is yours to write, and `Store` can be implemented against your own Postgres. But the backend SDK is Python-only, which splits the stack for a TypeScript project, and the surrounding examples assume OpenAI models.

Agent Builder was deprecated 2026-06-03 and shuts down 2026-11-30; ChatKit itself "remains available" per the official deprecations page, but a managed-backend setup needs migrating.

Whether the chat surface can sit alongside freely-placed app UI is undocumented — the design centre of gravity is "embed a widget".

### CopilotKit

npm library, MIT. Most active of the four (GitHub ~37k stars, `v1.72.0` on 2026-09-15).

**Does not use `useChat`.** Front-to-runtime traffic rides AG-UI, its own open protocol; the client hook is `useCopilotChat`. Its built-in backend agent *can* use the AI SDK for model calls, so the SDK may appear on the server — but that is not the same as sharing the client layer.

Tiers: finished components (`CopilotChat`, `CopilotSidebar`, `CopilotPopup`) → headless UI → generative UI.

Its premise is "put an assistant beside an existing app". It is not the tool for building the app's primary surface.

## Comparison

| | AI Elements | assistant-ui | ChatKit | CopilotKit |
|---|---|---|---|---|
| Form | copied source (shadcn-style) | npm library | embedded widget | npm library (3 layers) |
| License | Apache-2.0 | MIT (+ optional paid cloud) | Apache-2.0 (frontend) | MIT (+ optional paid cloud) |
| Wires to `useChat` | yes | yes (v7) | **no** | **no** (AG-UI) |
| Backend language | any | any | **Python only** when self-hosted | TypeScript and others |
| App UI outside the chat | free | free (primitives) | unverified | headless tier |
| Threads / history | none | optional, own DB | yes | yes (OSS-only scope unverified) |
| Non-React | no | Vue / RN / Ink emerging | web component | Angular and others |

## Defaults

- Already on Next.js + shadcn/ui + Tailwind → **AI Elements**, because it adds no dependency and the markup stays editable.
- Anything else, or the conversation needs branching / editing / virtualization out of the box → **assistant-ui** with `Thread`, dropping to primitives where the layout demands it.
- Reach for ChatKit or CopilotKit only when something specific to them is wanted — an OpenAI-managed backend, or an assistant docked beside an existing product. Both cost you the shared `useChat` layer.

## Myths worth correcting

- "Adding the AI SDK gets you a UI." It gets you state and transport.
- "assistant-ui forces a sidebar." `Thread` stands alone.
- "OpenAI models mean ChatKit is the natural fit." ChatKit suits embedded support bots; model vendor is a separate axis.
- "The SDK's thread feature can hold scores and history." There is no thread feature. See [session-architecture.md](session-architecture.md).
