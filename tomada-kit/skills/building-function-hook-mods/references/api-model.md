# Claude Code function-hooks ("mods") API model

Covers: hook execution model, return-value shaping, full event catalogue,
the `$` object noun-by-noun, `engine.create` noun contracts, `on()`
overloads, security model. UI/render-tree API: `references/drawing-ui.md`.

**EARLY ACCESS**, behind `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` (session env
or `~/.claude/settings.json` → `{"env":{"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS":"1"}}`);
"may change between releases without notice." Facts below are drawn from
`claude-code.d.ts` written by **Claude Code 2.1.271** (10,736 lines); the
installed declarations are now **2.1.273** (10,920 lines) — line numbers may
have drifted. Regenerate with `/plugin-types` before trusting exact lines.

## Contents

1. [Execution model](#1-execution-model) — `($, e, next)`, `next.*`, the five tiers
2. [Return-value shaping](#2-return-value-shaping--read-this-before-writing-a-hook) — read before writing a hook
3. [The `$` object, noun by noun](#3-the--object-noun-by-noun)
4. [Event catalogue](#4-event-catalogue) — engine, op, classic, noun events
5. [`engine.create` and noun contracts](#5-enginecreate-and-noun-contracts)
6. [`on()` overloads](#6-on-overloads) — including the matcher form
7. [Security model](#7-security-model) — pointer; full detail in security-model.md
8. [Open questions](#8-open-questions-unverified-in-the-declarations)

---

## 1. Execution model

**Signature:** `($: EngineInterface, e: Frozen<Args<N>>, next: Next<N>) => Result`.
`$` and `e` frozen to every depth. One TS/JS module per plugin
(`hooks/hooks.json` → `{"modules":["./register.ts"]}`), no DOM, no Node,
imports only types from `'claude-code'`.

**The onion.** Same-event hooks nest by tier, outermost first: `prepend >
user > append > builtin > core`. `prepend`/`append` = managed (admin-listed)
plugins, `user` = person-installed, `builtin` = shipped in binary, `core` =
engine's own innermost link. Within one plugin, registrations nest in
declaration order, outermost first (a repeat throws); across plugins, tier
order governs nesting.

**`next` semantics:**
- Return **without** calling `next` → answers the event yourself; nothing
  beneath (other hooks, core) runs for this dispatch.
- Call and return `next(e)` (or `await` it) → dispatch continues through
  every hook still beneath, then core. `next(e)` is a full sub-dispatch of
  everything beneath, not a passthrough.
- `next({...e, field})` → rewrites the event going down.
- Calling `next(e)` **more than once** is legal — each call opens a *fresh*
  run of everything beneath. `next.trace` reflects "the one started last."
- `next()`/`next.to()` may be fired **without awaiting** and read later
  (`void $.prompt.submit(...)` is the documented fire-and-forget pattern);
  unresolved links simply appear in `.trace` once they settle.

**`next.*` members:**

| Member | Type | Semantics |
|---|---|---|
| `.signal` | `AbortSignal` | Aborts when dispatch is abandoned (user interrupt, outer hook settled first, budget out); hook-started timers/requests should stop on it: `await $.clock.sleep(500,{signal: next.signal})`. |
| `.origin` | `{plugin, tier}` | Who dispatched this call; engine itself reads `{plugin:'engine',tier:'core'}`. E.g. `next.origin.tier==="prepend" ? next.to(e,"append") : next(e)`. |
| `.to(e, tier)` | — | Continues at a named tier, skipping links between here and there. `TargetTier=Exclude<Tier,'prepend'\|'user'>` — jump *to* `append`/`builtin`/`core` only, **never** to `prepend`/`user`. Skipped links: `.trace` `outcome:'skipped'`, `reason:"bypassed by <plugin>"`. |
| `.is(pattern, e)` | type predicate | Narrowing for a glob/`*`/negation hook. |
| `.event` / `.trace` | `N` / `TraceEntry[]` | Event name at runtime / per-link audit trail — §7.3. |

**Failure handling.** A hook that throws, overruns its budget, or answers a
wrong shape is *skipped*: hooks beneath and core run in its place, or its
last `next` result stands. `HookFailure = {kind:'throw'|'timeout', message?, budget}`.
`.trace` outcomes (7): `caught | expired | kept | passed | rejected |
returned | skipped` (`kept` = failed after calling `next`, that result
stands; `rejected` = failure actually propagated — deepest entry is origin).

`.catch(handler)` — settable once on the `Registration` `on()` returns
(second `.catch`, or one after `register()` returned, or on `engine.create`,
throws). Its answer within the grace stands as the hook's result; its `next`
carries `Caught = {error: HookFailure, called: boolean}` and is replay-safe
(`called` → `next(e)` resolves to last settled result, nothing reruns; not
`called` → runs beneath once, a later call replays). **Without `.catch`, a
failed hook is simply absent** from the chain — no hard dispatch failure.

No default hook timeout is stated for production (only `claude-code/testing`'s
`test()` states 5000 ms as its own default).

**Streaming (`turn.step`, the only streaming event today).** Hook is
`async function* ($, e, next) {}`, yielding chunks, returning the result:
`return yield* next(e)` passes through; `for await (const c of next(e)) yield f(c)`
transforms; yielding without `next` answers alone. `next(e)` returns a
`HookStream` (not a Promise) — each call opens a *fresh* stream (a fresh
model request, for `turn.step`); read the generator to its end, then `await
stream.result`. Chunks not built by this hook carry an opaque `ref` tying
them to the engine's own stream item; passthrough preserves that handle.

---

## 2. Return-value shaping — read this before writing a hook

**There is no universal `{ value }` envelope.** Shape is event-family–specific:

| Family | Shape | Notes |
|---|---|---|
| **Engine lifecycle events** (33) | bespoke, per event | e.g. `tool.call` → `{result,context?}\|{deny}`; `prompt.suggest` → `{isShown}`; `config.set` → `{value}\|{deny}` — this one *happens* to use the field name `value`, that's its own shape, not a wrapper. |
| **Classic events** (33) | subset of `ClassicResult` | named after classic JSON hook fields (`block`, `additionalContext`, …); `classic.PreToolUse` alone keeps `allow/ask/deny`. |
| **Op events** (49 — every `$` method call) | **always** `ValueOrDeny<Value>` | `{value: V, deny?: undefined} \| {deny: string, value?: undefined}`. A hook on `fs.read` sees `{value: string}\|{deny: string}`, never a bare string. |
| **Noun events** (plugin-added, §5) | **always** `ValueOrDeny<Value>` | Same wrapper as op events — a plugin noun's methods behave exactly like core ops. |

**Rule of thumb:** `{value}|{deny}` appears *exactly* on dispatches
corresponding to a method call on `$` — core ops and plugin-added noun ops.
Events the engine raises at its own sites (turn/session/prompt/tool/ui
lifecycle, classic hooks) use their own named result type instead.

Transforming a downstream result: `const r = await next(e); return {...r, text: r.text + "!"}`
(streaming: `const r = yield* next(e); return {...r}`).

---

## 3. The `$` object, noun by noun

`$: EngineInterface extends CoreEngineInterface`, frozen, no `on` (`on` is
only on the `register` param — "registration happens before `$` exists").
`EngineInterfaceBuilt` is open to nouns no declaration names yet.

**Not callable nouns:** `$.skill` and `$.attribution` do **not** exist —
`skill.prompt`/`attribution.text` are pure *events* the engine raises at its
own call sites, hookable via `on(...)` but with no `$.skill.prompt(...)` /
`$.attribution.text(...)` call. **No `$.engine`** either — `engine.create`
is the sole `engine.*` event and the noun-contract mechanism (§5), not an object.

| Noun.member | Signature | Semantics |
|---|---|---|
| `plugin` | `{name, root}` | This plugin as loaded. |
| `ui.*` | see `references/drawing-ui.md` | `notice, invalidate, blit, resolve, log, ask, toast, status, open, close, scroll, focus`. |
| `model.complete` | `(req: ModelCompleteRequest) => Promise<string>` | One text completion, no tools/history. |
| `model.fork` | `(req: ModelForkRequest) => Promise<ModelForkResult\|null>` | Tool-less completion over session transcript, shares prompt cache; null on cold snapshot/API error. |
| `model.classify` | `(text, labels, options?) => Promise<string\|undefined>` | Picks one label via fixed classifier prompt. |
| `audio.play` | `(clip, options?) => Promise<void>` | Not queued — two calls play together. |
| `audio.speak` | `(text, options?) => Promise<SpeakResult>` | Platform TTS; utterances queue among themselves. |
| `mcp.call` | `(server, tool, args?) => Promise<McpToolResult>` | Via engine's own connection; no permission prompt. |
| `session.messages` | `() => Promise<SessionMessage[]>` | Newest 4096 max. |
| `session.cwd` / `.model` / `.turns` / `.id` | `() => Promise<...>` | Working dir / main-loop model / turn count / session id. |
| `session.repo` | `() => Promise<SessionRepo\|null>` | Fresh each call; null outside a repo. |
| `session.surfaces` | `() => Promise<readonly RenderSurface[]>` | Every surface drawing now. |
| `session.surface` | `() => Promise<RenderSurface\|null>` | **Deprecated**, use `surfaces()`. |
| `session.usage` | `(args?) => Promise<SessionUsage>` | Plain call free; `"full"` costs a token-count call. |
| `session.compact` | `EventCalls['session']['compact']` | Same as `/compact`; `{skip}` if a hook vetoed. |
| `session.authorize` | `() => Promise<SessionAuthorization>` | Opaque credential handle; secret never reaches plugin; spend via `$.http.fetch(url,{auth: handle})` to first-party hosts only. |
| `turn.abort` | `(input:{turnId}) => Promise<void>` | Rejects if `turnId` isn't the running turn's. |
| `prompt.submit` | `EventCalls['prompt']['submit']` | Submits a user turn; runs when idle; every plugin's hooks see it. |
| `prompt.fill` | `EventCalls['prompt']['fill']` | Writes draft text; `{isFilled:false}` if dialog holds keys / headless. |
| `prompt.suggest` | `EventCalls['prompt']['suggest']` | Tab-to-take suggestion; `{isShown:false}` if box has text/turn runs/headless. |
| `tool.list` | `() => Promise<ToolInfo[]>` | Model's own order. |
| `tool.call` | `EventCalls['tool']['call']` | Full permission+hook chain, fresh `tool_use_id`. |
| `tool.check` | `EventCalls['tool']['check']` | Permission verdict only — no dialog, no PreToolUse, no classifier. |
| `tool.register` | `(tool: ToolSpec) => Promise<{tool}>` | `mcp__<plugin>__<name>`; served by a `tool.call` hook; rejects before `session.start`. |
| `command.list` | `() => Promise<CommandInfo[]>` | Typeahead order. |
| `command.run` | `EventCalls['command']['run']` | Runs `/command args`; queued until idle. |
| `command.register` | `(cmd: CommandSpec) => Promise<{command}>` | Built-in name refused. |
| `config.list` | `() => Promise<ConfigRow[]>` | After every `config.describe` hook. |
| `config.set` | `EventCalls['config']['set']` | `{deny}` on refusal/wrong-kind/trusted-owned. |
| `agent.spawn` | `EventCalls['agent']['spawn']` | Same path as the Agent tool; `{agentId}\|{deny}`. |
| `agent.list` | `() => Promise<AgentInfo[]>` | Model-spawned + plugin-spawned so far. |
| `fs.read` / `.write` | `(path)=>Promise<string>` / `(path,text)=>Promise<void>` | UTF-8 only; relative under session cwd; >4 MiB rejects. |
| `fs.list` | `(path?) => Promise<FsEntry[]>` | `{name,kind,size}`. |
| `fs.exists` / `.stat` | `(path)=>Promise<boolean>` / `Promise<FsStat>` | `.exists` never rejects; `.stat` rejects if missing. |
| `fs.ancestors` | `(req: FsAncestorsRequest) => Promise<readonly FsAncestor[]>` | Like CLAUDE.md directory-tree loading. |
| `store.get/.set/.delete/.keys` | — | Plugin's persistent JSON k/v store; 4 MiB cap; functions/cycles rejected. |
| `clock.now` / `.sleep` | `()=>Promise<number(ms)>` / `(ms,options?)=>Promise<void>` | `.sleep` rejects at once on `signal` abort. |
| `clock.after` / `.every` | `(ms, fn) => Timer` | `fn` runs in plugin's own env; hot reload cancels pending waits. |
| `http.fetch` | `(url, init?: HttpInit) => Promise<HttpResponse>` | Through host, never plugin's own network; admin policy can refuse; `auth` handle only to first-party hosts. |
| `process.run` | `(argv, init?) => Promise<ProcessRunResult>` | Argv only, no shell; output buffered whole; git runs with repo hooks off. |
| `settings.read` | `(args?) => Promise<Settings>` | Precedence `user < project < local < flag < policy`; OAuth session / `~/.claude.json` never included. |
| `env.get` / `.set` | `(name) => ...` | **`name` must be a string literal** — enables static scan (§7.1). |
| `telemetry.log`/`.mark` | plugin-added, §5 | Internal-build-only; absent (`$.telemetry` undefined) unless seated. |

---

## 4. Event catalogue

`EventName = keyof EventOf`; `EventOf = CoreEventOf & NounEventOf`;
`CoreEventOf = EngineEventOf & ClassicEventOf & OpEventOf`. Exhaustive
literal count for a stock install: **34 engine + 50 op + 33 classic = 117** (counted on 2.1.273)
built-in names, plus however many `<noun>.<method>` a loaded plugin's
`engine.create` adds. `on('*', ...)` sees every dispatch, engine+op+classic+noun alike.

### 4.1 Engine lifecycle events (33)

| Event | Result shape | Semantics |
|---|---|---|
| `tool.call` | `{deny}\|{result,context?,ref?,text?}\|{isError:true,...}` | About to run a tool; `next(e)` → permission prompt + real tool. |
| `tool.check` | `{decision:'allow'\|'ask'\|'deny',reason?,rule?}` | Verdict only, no side effects. |
| `tool.describe` | `{description}` | Once per tool, cached. |
| `ui.render` | `RenderElement` | Draw a component; cached until invalidated. |
| `ui.resolve` | `ElementTable` | Per-surface element-constructor table, resolved once. |
| `ui.press`/`.input`/`.select` | `{element}`/`{element,value}`/`{element,value}` | Drawn control interacted with. |
| `ui.message` | `{props?}` | `Client.surface.post(data)`; only this plugin's hooks see it. |
| `ui.scroll`/`.focus` | `{}\|{deny}` | Before a site's window/focus moves. |
| `agent.offer` | `{isOffered}` | Engine offering an agent type (listing+dispatch). |
| `agent.spawn` | `{model,agentId?}\|{deny}` | prompt/description/subagentType/model/background/cwd rewritable, rest pinned. |
| `prompt.submit` | `{text,context?}\|{drop}` | Before turn starts. |
| `prompt.fill` | `{isFilled}` | Into prompt box as draft. |
| `prompt.suggest` | `{isShown}` | Tab-to-take suggestion. |
| `prompt.section` | `{text}` (null=out) | Once per named system-prompt section, cached. |
| `prompt.context` | `{blocks}` | Once per conversation: first user message's context blocks. |
| `command.run` | `{text}` | `/name args` about to run. |
| `command.describe` | `{description,argumentHint,isHidden}` | Once per command, cached. |
| `config.set` | `{value}\|{deny}` | `/config` row about to change. |
| `config.describe` | `{label,description,isHidden}` | Once per row, cached. |
| `skill.prompt` | `{text}` | Skill's prompt about to expand. Event only — no `$.skill`. |
| `attribution.text` | `{text}` | Commit/PR/exemption/remedy text composing. Event only — no `$.attribution`. |
| `session.start` | `{cwd}` | Once per process per plugin, before first prompt (+again on reload). |
| `session.receive` | `{text}\|{consumed}` | Relay/peer/Remote Control delivery, before queued. |
| `session.compact` | `{messages,tokensBefore?,tokensAfter?}\|{skip}` | Conversation about to compact. |
| `session.attach`/`.detach` | `{clientId}` | Remote client joining/leaving surfaces roster. |
| `plugin.register` | `{allow:true}\|{refuse:string}` | Once per module about to join the chain (§7.2). |
| `turn.start` | `{turnId}` | Before first model call. |
| `turn.step` | `{turnId,index,answer,toolUses,stopReason,usage}` (**streaming**, §1) | One model request inside a turn. |
| `turn.complete` | `{text}` | Turn ended. |
| `engine.create` | `Partial<EngineInterface> & {[noun]:unknown}` | `$` being built for this load/reload (§5). |

### 4.2 Op events — every `$` method call (49)

Input = the call's argument(s); result = `ValueOrDeny<Value>` always (§2).
One entry per `CoreEngineInterface` method — full semantics in §3 table.

| Noun | Ops (→ value type) |
|---|---|
| `model` | `.complete`→string · `.classify`→string\|undefined · `.fork`→ModelForkResult\|null |
| `audio` | `.play`→void · `.speak`→SpeakResult |
| `mcp` | `.call`→McpToolResult |
| `session` | `.cwd`→string · `.model`→string · `.turns`→number · `.id`→string · `.messages`→SessionMessage[] · `.repo`→SessionRepo\|null · `.surface`→RenderSurface\|null (deprecated) · `.surfaces`→readonly RenderSurface[] · `.authorize`→SessionAuthorization · `.usage`→SessionUsage |
| `turn` | `.abort`→void |
| `tool` | `.list`→ToolInfo[] · `.register`→{tool} |
| `command` | `.list`→CommandInfo[] · `.register`→{command} |
| `config` | `.list`→ConfigRow[] |
| `agent` | `.list`→AgentInfo[] |
| `ui` | `.toast`→void · `.status`→void · `.log`→void · `.notice`→void · `.invalidate`→void · `.open`→void · `.close`→void · `.blit`→UiBlitResult |
| `fs` | `.read`→string · `.write`→void · `.list`→FsEntry[] · `.exists`→boolean · `.stat`→FsStat · `.ancestors`→readonly FsAncestor[] |
| `store` | `.get`→unknown · `.set`→void · `.delete`→void · `.keys`→string[] |
| `clock` | `.now`→number(ms) · `.sleep`→void · `.after`→void · `.every`→void |
| `http` | `.fetch`→HttpResponse |
| `process` | `.run`→ProcessRunResult |
| `settings` | `.read`→Settings |
| `env` | `.get`→string\|undefined · `.set`→void |

### 4.3 Classic events (33) — `classic.<HookEvent>`

**How a mod intercepts the old settings-hooks system** — name computed as
`classic.${ClassicHookEvent}`, so grepping a module for the bare
`HookEvent` name (without the `classic.` prefix) misses it; grep for
`classic.PreToolUse`-style literals instead. `e` = same JSON the classic
hook gets on stdin (`ClassicHookInputs[E]`), except `classic.PreToolUse`
where `e` is `ToolCallEnvelope` alone. Every input extends `BaseHookInput`
(`session_id, transcript_path, cwd, prompt_id?, permission_mode?, agent_id?,
agent_type?, effort?`). Result: per-event subset of `ClassicResult`; any may
answer `block`, `preventContinuation`, `stopReason`; `classic.PreToolUse`
alone keeps its own `allow/ask/deny` shape. Order: `[managed settings hooks,
...hooks modules, other settings hooks as core]` — a managed block ends it
above every module.

Names (prefix each with `classic.`, e.g. `classic.PreToolUse`): `PreToolUse ·
PostToolUse · PostToolUseFailure · PostToolBatch · PermissionDenied ·
Notification · UserPromptSubmit · UserPromptExpansion · SessionStart ·
SessionEnd · Stop · StopFailure · SubagentStart · SubagentStop · PreCompact ·
PostCompact · PreModelSwitch · PostModelSwitch · PermissionRequest · Setup ·
TeammateIdle · TaskCreated · TaskCompleted · Elicitation · ElicitationResult ·
ConfigChange · InstructionsLoaded · WorktreeCreate · WorktreeRemove ·
CwdChanged · FileChanged · DirectoryAdded · MessageDisplay`

### 4.4 Noun events — dynamic, plugin-defined

Empty by default. The instant a plugin's `engine.create` step adds a noun
(§5), every one of that noun's methods becomes a hookable `<noun>.<method>`
event automatically, wrapped `ValueOrDeny` like op events. Example: the
shipped `telemetry` mod adds `$.telemetry`, which makes `telemetry.log` and
`telemetry.mark` hookable exactly like `fs.write`.

---

## 5. `engine.create` and noun contracts

**Adding a noun.** `engine.create` runs while `$` is being built, once per
load/reload of this plugin, before any other hook of it. Inside the hook `$`
is `NoEngineInterface` (every property reads `never`) — call `next(e)` first
to get the real partially-built interface. A step may **add** nouns and
**withhold** nouns (leave one out, or return without `next`); it may **not
replace** one another step added — that step fails (named, both plugins),
its plugin unloads, `$` rebuilds.

```ts
on('engine.create', async ($, e, next) => {
  const beneath = await next(e)
  const telemetry: EngineInterface['telemetry'] = telemetryOf({...})
  return { ...beneath, telemetry }
})
```
`EngineCreateInput.plugins` lists plugins folding in, outermost first
(managed plugins first, so an org plugin's withholding wins).

**Declaring the TS contract.** The plugin ships its own `.d.ts`
(`plugin.json` → `"types": "./types/index.d.ts"`), exporting the noun's type
and declaration-merging it onto `EngineInterface`:

```ts
export type Telemetry = { log: (entry: TelemetryLogEntry) => Promise<void>; ... }
declare module 'claude-code' {
  interface EngineInterface { telemetry: Telemetry }
}
```
`/plugin-types` copies every enabled plugin's noun contract to
`.claude/types/claude-code-plugins/<plugin>.d.ts` for consumers.

**Consuming the noun.** Any declared noun is auto-walked into
`NounEvent`/`NounEventOf` — every method `M` on noun `K` becomes event
`${K}.${M}`, args = method's first parameter, value = its awaited return,
wrapped `ValueOrDeny` (§2). A second mod calls the noun directly (`await
$.telemetry.log(...)`, once loaded after the noun-adding mod folds in) or
hooks its events to observe/veto/rewrite calls other mods make to it. If the
noun-adding mod is absent, `$.telemetry` is `undefined` — a caller throws.

---

## 6. `on()` overloads

`register: (on: On, options: PluginOptions) => unknown` is the module's sole
export. `on` is not on `$` — registration happens before `$` exists.

```ts
on(pattern, hook)                    // plain / glob / '*' / negation pattern
on(pattern, matcher, hook)           // matcher-narrowed: hook only fires when matcher fields match
```
Example matcher form: `on('tool.check', { tool: 'Read' }, hook)` — narrows
to `Read` calls only; `next.is(pattern, e)` gives the same narrowing as a
type predicate inside the hook body.

`options: PluginOptions = Readonly<Record<string, string|number|boolean|readonly string[]>>`
— manifest's `userConfig` fields, defaults filled in, validated against
declared `type` before load; a required field with no value fails the load,
naming the field.

`on(...)` returns `Registration<F>` with one settable `.catch(handler)`
(§1). Tier is the host's reading of where the plugin is installed — never
declared by the module itself, and never `'core'`.

---

## 7. Security model

Moved to references/security-model.md — the static `PluginRegisterUses` scan,
`plugin.register` refusal, the string-literal spelling requirement, and
`next.to` as an organization's way to keep a dispatch unreachable.

## 8. Open questions (unverified in the declarations)

- **Default hook budget** — unstated for production; only `test()` states
  5000 ms as its own default. `HookFailure.budget` implies a real runtime
  number exists, unnamed.
- **`CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` gate** — confirmed only via a
  secondary community README, not inside `claude-code.d.ts` itself.
- **`settings.read()` policy switch refusing `$.http.fetch`** — that such a
  policy can exist is stated; its name/shape is not.
- **`user`-tier noun-name collision with an org noun** — fails only that
  plugin or the whole load is not spelled out explicitly, only inferred.
