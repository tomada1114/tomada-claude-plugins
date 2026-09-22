# AI SDK v7 API map

Checked 2026-09-15 against `ai@7.0.102` (npm registry, the shipped `dist/index.d.ts` via unpkg, GitHub Releases, and ai-sdk.dev live docs). If the current `ai` major is no longer 7, treat this file as stale — see [Release cadence](#release-cadence).

## Release cadence

| Major | Released | Gap |
|---|---|---|
| `ai@5.0.0` | 2025-07-31 | — |
| `ai@6.0.0` | 2025-12-22 | ~5 months |
| `ai@7.0.0` | 2026-06-25 | ~6 months |

A major lands roughly every six months and every one of them has renamed public API. Treat any AI SDK snippet older than a few months as suspect, including your own memory of the API. Check the project's installed version first (command in SKILL.md).

## Detecting a stale source

Training data, blog posts, Stack Overflow, and **parts of the official docs** still carry v4-era code. As of 2026-09-15 these files in `vercel/ai` main were still on the old API: `content/cookbook/00-guides/24-o3.mdx`, `content/docs/05-ai-sdk-rsc/10-migrating-to-ui.mdx`. Being on ai-sdk.dev is not evidence that a snippet is current.

| Sign in the snippet | Verdict |
|---|---|
| `useChat()` returns `input`, `handleInputChange`, `handleSubmit`, `setInput` | v4-era, dead since v5 |
| `message.content` read as a string | v4-era, dead since v5 |
| `system:` passed to a generation function | pre-v7 |
| `result.toUIMessageStreamResponse()` | pre-v7 (deprecated, still present) |
| `stepCountIs(n)` | pre-v7 |
| `convertToCoreMessages` | pre-v6 |
| `Experimental_Agent` | pre-v6 |
| `experimental_*` prefixes generally | pre-v7 — most graduated |

## v7 renames

| Old | New |
|---|---|
| `system` (arg to `generateText` / `streamText` / `generateObject` / `streamObject`) | `instructions` |
| `onFinish` (server: `streamText` / `generateText` / agents) | `onEnd` |
| `onStepFinish` | `onStepEnd` |
| `stepCountIs` | `isStepCount` |
| `experimental_output` | `output` |
| `experimental_activeTools` | `activeTools` |
| `experimental_prepareStep` | `prepareStep` |
| `experimental_repairText` | `repairText` |
| `experimental_telemetry` | `telemetry` |
| `ToolCallOptions` | `ToolExecutionOptions` |
| `streamText().fullStream` | `streamText().stream` |
| `result.toUIMessageStreamResponse()` | `createUIMessageStreamResponse()` (top-level, stateless) |
| `result.totalUsage` | `result.usage` (now sums all steps) |
| `cachedInputTokens` | `inputTokenDetails.cacheReadTokens` |
| `reasoningTokens` | `outputTokenDetails.reasoningTokens` |

Also in v7:

- **A `system` message inside `messages` is rejected by default.** Use top-level `instructions`, or opt in with `allowSystemInMessages: true`.
- File parts collapsed: `image-data` / `image-url` / `file-data` → a single `file` with `mediaType`. New `reasoning-file` part.
- OpenTelemetry moved to `@ai-sdk/otel`, registered via `registerTelemetry(new OpenTelemetry())`.
- **Node.js 22+ required** (18 and 20 dropped) and **ESM only** — `require()` is gone.
- Step-final data moved to `result.finalStep` (`reasoning`, `request`, `response`, `providerMetadata`).

## The `onFinish` / `onEnd` split

The rename applies to the **server** side only. `useChat` on the client still takes `onFinish`. Same concept, two names, depending on which side of the wire you are on. Client callbacks are `onFinish`, `onError`, `onData`, `onToolCall`, `sendAutomaticallyWhen`.

## Package versions do not line up

Majors are independent across packages. As of 2026-09-15: `ai@7.0.102`, `@ai-sdk/react@4.0.105`, `@ai-sdk/openai@4.0.67`, `@ai-sdk/anthropic@4.0.54`. Compatibility is carried by the shared `@ai-sdk/provider` and `@ai-sdk/provider-utils` versions, not by matching the core major. Do not "fix" a provider package to `^7`.

Zod 3 and Zod 4 are both supported (`peerDependencies.zod = "^3.25.76 || ^4.1.8"`).

## `useChat` surface

Returns: `id`, `messages`, `sendMessage`, `status`, `error`, `stop`, `regenerate`, `setMessages`, `clearError`, `resumeStream`, `addToolOutput`, `addToolApprovalResponse`.

- **The app owns the input field state.** The hook does not.
- `status` is `'submitted' | 'streaming' | 'ready' | 'error'`. `stop()` is only meaningful during `submitted`/`streaming`; `regenerate()` during `ready`/`error`.
- **`stop()` aborts the client request only.** It does not cancel server-side generation, so it does not stop the spend. If cancelling the model call matters, wire an explicit server-side abort.

## Messages are `parts`, not strings

```ts
interface UIMessage<METADATA = unknown, ...> {
  id: string;
  role: 'system' | 'user' | 'assistant';
  metadata?: METADATA;
  parts: Array<UIMessagePart<...>>;
}
```

Part types: `text`, `reasoning`, `reasoning-file`, `tool-{NAME}`, `dynamic-tool`, `file`, `source-url`, `source-document`, `data-{NAME}`, `custom`, `step-start`.

Tool part states: `input-streaming` → `input-available` → (`approval-requested` → `approval-responded` →) `output-available` / `output-error` / `output-denied`. Handle the approval states even for tools that never request approval — automatic approvals flow through the same states with `part.approval.isAutomatic === true`.

To pull out just the human-readable utterances (for grading, export, or a transcript view), write it yourself — there is no official helper:

```ts
const said = (m: UIMessage) =>
  m.parts.filter(p => p.type === 'text').map(p => p.text).join('');
```

`convertToModelMessages()` (renamed from `convertToCoreMessages` in v6, unchanged in v7) converts to the model-facing shape.

## Transport

`DefaultChatTransport` takes `api`, `headers`, `body`, `credentials` — each of which may be a function for dynamic values. **It sends the entire history on every turn by default.** `prepareSendMessagesRequest` overrides the body; both "last N" and "last message only" are documented patterns.

Trimming history is a cost decision, not a correctness one: if the server reloads the conversation from its own store, sending only the newest message is cheaper and avoids trusting client-supplied history.

## Structured output

`generateObject` and `streamObject` are alive in v7 — they are missing from the docs reference index but present in the shipped type definitions.

- The old `mode: 'json' | 'tool' | 'auto'` parameter is gone. Use `output: 'object' | 'array' | 'enum' | 'no-schema'`.
- Validation failure throws `NoObjectGeneratedError`. `repairText` hooks in to make raw model output parseable.
- `maxRetries` is transport-level retry. Whether any built-in retry re-prompts the model after a *schema* failure is unconfirmed — assume not, and handle it yourself.
- The SDK enforces and validates **shape**. It does not make values stable. Score consistency is a model-settings and prompt problem (temperature, rubric wording), not an SDK feature.

## Agent loop

- `ToolLoopAgent` (was `Experimental_Agent`). **Default step cap is 20.**
- `WorkflowAgent` (new in v7, for durable/resumable runs) has **no default cap** — pass `stopWhen` or it runs until the model stops calling tools.
- `stopWhen` takes an array; any one condition stops the loop: `isStepCount(n)`, `hasToolCall(name)`, `isLoopFinished()`.
- `prepareStep` swaps `activeTools` / `toolChoice` per step, for phase control.

## Persistence: not included

The SDK has no thread management and no history storage. The official guide is explicitly a sample with no authorization and no error handling.

- Persist `UIMessage` (parts included) — it is the source of truth; convert to `ModelMessage` only at call time.
- Message IDs are generated in two different places by default (user messages client-side, assistant messages server-side). Issue stable IDs explicitly if persistence matters.
- Validate inbound messages server-side with `validateUIMessages({ messages, tools, metadataSchema, dataPartsSchema })`. Client-supplied message arrays are untrusted input.

## Resumable streams: infrastructure, not a flag

`useChat({ id, resume: true })` on the client needs, on the server: the `resumable-stream` package, **Redis**, and your own tracking of which stream ID is active for which chat. Explicit stop conflicts with it, so a separate stop endpoint is needed too.

For a first version, skip it. Adopt it only after observing how often streams actually break for real users.

## Standalone use

The default onboarding path is Vercel AI Gateway (`AI_GATEWAY_API_KEY`), and `ai` depends on `@ai-sdk/gateway`. Using a provider package directly with your own key is a documented, supported path (`@ai-sdk/anthropic` → `anthropic('...')`). No official sentence promises "no Vercel account needed" — the direct-provider path is well documented, but that absolute claim is not something the docs make.

Runtimes: Node 22+, ESM. Getting-started guides exist for Node, Svelte, Nuxt, Expo, TanStack Start, with Express / Hono / Fastify / Nest.js backends. Edge runtime support is not stated in the v7 docs.
