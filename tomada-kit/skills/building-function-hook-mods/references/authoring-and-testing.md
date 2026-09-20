# Authoring and testing a Claude Code Mod

Scope: how to lay out, write, build, and test a function-hooks mod (a plugin whose behavior lives in TypeScript, not shell commands), grounded in Anthropic's three shipped built-in mods and in commands actually run on this machine. **EARLY ACCESS**, gated by `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`. Facts are pinned to Claude Code 2.1.273; regenerate type declarations with `/plugin-types` after any update rather than trusting this file's version. Where the built-in-mod source and machine-verified findings disagree, the verified findings win — noted inline each time.

## Contents
1. File layout, `plugin.json`, `hooks.json`
2. JSX needs `.tsx`; tsconfig; JSX globals
3. `register(on, options)` idioms
4. The build loop, verified
5. [Testing](#5-testing) — pointer; the kit is in testing-mods.md
6. The shape trap
7. Walkthroughs: `diff`, `telemetry`, `sec-default`
8. Unverified

---

## 1. File layout

```
<mod>/
  .claude-plugin/plugin.json   # manifest: identity + optional noun contract
  hooks/
    hooks.json                 # {description, modules: [...]}
    register.ts                # entry point: export function register(on)
    <feature>/<feature>.ts     # implementation, one function/type per file
    <feature>/index.ts         # barrel re-export
    types/                     # only if the mod adds a $ noun
  tests/
    register.test.ts           # one describe(), named for hooks/register.ts
    <feature>.test.ts          # named for the hooks/ file it covers
    fixtures/<name>.ts         # one export per file, shared setup
  README.md
```

The smallest mod that runs is three files: `plugin.json`, `hooks/hooks.json`, `hooks/register.ts`. No tsconfig, no build step. The engine reads `hooks/hooks.json` by convention; the TypeScript **loads directly**.

`plugin.json` — verbatim (`diff`, no noun; `telemetry`, with one):
```json
{
  "name": "diff",
  "version": "0.1.0",
  "description": "The diff pane as a plugin: /diff opens the session's uncommitted changes beside the transcript, file by file with their hunks, refreshed as Claude edits and runs commands; the first edit opens it where the terminal is wide enough, and a file's ask button rides its hunks on the next prompt.",
  "author": { "name": "Anthropic" }
}
```
```json
{
  "name": "telemetry",
  "version": "0.1.0",
  "description": "Plugin analytics: adds $.telemetry in the engine.create fold, so a plugin logs an event or marks a feature's use as one first-party row per call, sent with the session's own credential.",
  "author": { "name": "Anthropic" },
  "types": "./types/index.d.ts"
}
```
No `commands`, `hooks` (classic-style), or `agents` fields — a mod's manifest is just identity. `types` publishes a noun contract for other mods (§7).

`hooks/hooks.json` — verbatim, and the whole schema:
```json
{
  "description": "The diff pane: /diff and its Pane drawing, a refresh on Claude's edits, shell commands and finished turns, the pane's opening on the first edit, and the ask that rides a file's hunks on the next prompt",
  "modules": ["./register.ts"]
}
```
Only `{description, modules}`. `description` is documentation, not consumed for behavior. `modules` is an **array** of paths relative to `hooks/`, so one mod's registration can be split across several entry files; each must `export function register(on: On, options?: PluginOptions)`. No separate "main" field — `hooks.json` is the only place naming the module, and `register.ts` is a convention, not an enforced name.

Classic (shell-command) hooks run as an external subprocess with JSON on stdin/stdout — no `$`, no shared state, no types. A function-hooks module runs **in process** instead: `register(on)` runs once at load/reload and closes over module-level state for the session (and can even reach classic hooks via `on('classic.*', ...)`, `sec-default`, §7).

---

## 2. JSX requires a `.tsx` module

**Verified.** A `.ts` module containing JSX is rejected at load by `claude plugin validate`, before any code runs:
```
✘ modules../register.ts: paint: .../hooks/register.ts does not parse:
  Expected ">" but found "color" (line 9, column 15);
  Expected ")" but found "bold" (line 9, column 31); ...
```
Renaming to `register.tsx` (and pointing `hooks.json` at it) passes. The built-in mods are all `.ts` because none writes JSX — they build trees by calling element constructors directly. **If your mod draws with JSX, the module (and its test file) must be `.tsx`.**

tsconfig — verbatim (what the built-ins compile against; `/plugin-types` prints the same one for an out-of-repo project):
```json
{
  "compilerOptions": {
    "target": "es2023",
    "lib": ["es2023"],
    "types": [],
    "module": "esnext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noEmit": true,
    "skipLibCheck": true,
    "jsx": "react",
    "jsxFactory": "h",
    "jsxFragmentFactory": "Fragment"
  },
  "include": [".claude/types", "hooks", "tests"]
}
```
`"lib": ["es2023"]` names **no DOM** — the hooks environment has none, and DOM's own `Text` would shadow the UI element. `"types": []` — no ambient `@types/*`; everything comes from `import type ... from 'claude-code'` / `'claude-code/testing'`, resolved against `declare module 'claude-code' {...}` ambient blocks (no real package on disk; erased at runtime).

**JSX pragma/globals**: `h`/`Fragment` are **environment globals at runtime**, not imports — a module declaring a local named `h` breaks its own JSX. Elements (`Box`, `Text`, `Button`, ...) are **not** globals either — a render hook gets them off the surface: `const { Box, Text } = $.ui.resolve(e)`. Other globals: the JSX namespace and web APIs (`URL`, `TextEncoder`, `AbortController`, `crypto.subtle`). No `WebAssembly` (0 hits) — a WASM engine runs out-of-process, reached through `$.http.fetch`.

---

## 3. `register(on, options)` idioms

**State as closures.** All mutable session state lives in `let`/`Map`/`Set` locals declared inside `register`, closed over by every `on(...)` handler — the mod's entire persistence model. `diff/hooks/register.ts` closes over ~20 such locals (`host`, `backend`, `model`, `timers: Map<...,Timer>`, `bodyLoads: Map<...>`, plus scalars). The only externalized state is two `$.store` keys (pane-open preference, per-repo diff base) — `command.run` of `clear`/`resume` explicitly resets every closure variable.

**One memo shared by every hook that needs it.** `sec-default` creates `readPolicy = Policy.createPolicyMemo(Policy.POLICY_MEMO_MS)` once in `register`; both its `tool.register` and `tool.list` hooks call `readPolicy(() => $.settings.read(Policy.SOURCE))`, so one `$.settings.read` serves a whole burst of callers (full hooks in §7). `register.ts` itself reads as a table of "which event → which move" — logic (`pastUsers`, `decidedByPolicy`, `hasMcpAllowlist`) is factored to pure functions elsewhere. `Policy` is a named default export grouping related one-function files under a barrel `index.ts`, imported as a namespace (`Policy.createPolicyMemo`, `Policy.SOURCE`) — the same barrel convention runs throughout `hooks/`.

**Extreme one-function-per-file decomposition.** `diff` splits its ~900-line logic into ~40 sub-modules (`hooks/<feature>/<feature>.ts` + `index.ts` barrel), each independently unit-tested, threaded through a `Host` abstraction (a plain object of thunks: `run`, `readFile`, `storeGet`, `openPane`) built once from `$` in `session.start`, rather than passing literal `$` everywhere. **A small mod should not copy this** — it exists because `diff` is genuinely large; a few-hook mod is better as one `register.ts` plus at most a couple of pure helper files.

`options` (`PluginOptions` — the manifest's `userConfig` fields, defaults filled in) is unused by all three shipped mods; none declares `userConfig`.

---

## 4. The build loop, verified on 2.1.273

**The flag is a silent gate.** A hooks module loaded with `--plugin-dir` is **ignored with no warning** when `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` is unset — no error, no load-failure entry, exit 0. Check this first when a mod "does nothing":
```
$ claude --plugin-dir ./hello -p 'reply with the single word: ok'
ok
proof: NOT WRITTEN

$ CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude --plugin-dir ./hello -p 'reply ...'
ok
proof: loaded at 2026-09-15T23:37:46.669Z cwd=/.../scratchpad
```

**`claude --plugin-dir <path>`** loads a folder from source, at the `user` tier by default. A mod whose only real move requires a managed tier (`sec-default`) is inert this way since `next.to` is refused outside one.

**`claude plugin validate <path>`** works **without the flag**, statically scanning source before any runs, printing every event hooked (including matchers) and every `$` call made:
```
$ claude plugin validate ./hello
Validating hooks: /.../hello/hooks/hooks.json

  ❯ ./register.ts hooks: session.start
  ❯ ./register.ts calls: $.ui.toast

✔ Validation passed with warnings
```
With matchers, the inventory shows them inline:
```
❯ ./register.tsx hooks: ui.render{component=Spinner}, ui.render{component=AssistantMessage}
❯ ./register.tsx calls: $.ui.resolve
```
Exact because a module that spells `on`, `$`, or `$.env` other than literally does not load (e.g. `$.env.get(someVariable)` fails to load).

**`claude plugin test <path>`** exists and runs on 2.1.273, though **hidden from `claude plugin --help`** (a report claiming it's missing was stale, from v259–2.1.272):
```
$ CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude plugin test ./hello
tests/register.test.ts:
(pass) register > session.start raises a toast [472.82ms]

 1 pass
 0 fail
Ran 1 test across 1 file. [2.52s]
```
With no tests: `claude plugin test: no *.test.ts or *.test.tsx under <path>` (exits cleanly).

**`/plugin-types`**, run inside a session from the plugin directory, writes three files under `.claude/types/`:
```
$ CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude -p '/plugin-types'
Wrote .claude/types/claude-code.d.ts: the plugin API (module 'claude-code',
  early access: it may change between releases) and 29 built-in tools.
Wrote .claude/types/claude-code-plugins.d.ts: no enabled plugin names a type
  contract (plugin.json `types`), so it declares nothing.
Wrote .claude/types/claude-code-mcp.d.ts: 78 MCP tools from 5 servers.
```
`claude-code.d.ts` is the API plus built-in tools typed (`e` narrows per tool in `tool.call`); `claude-code-mcp.d.ts` is your own MCP servers' tools, per-machine (`.gitignore` it); `claude-code-plugins.d.ts` is the noun contracts of enabled plugins declaring `types` — how you consume another mod's noun with nothing copied (before that's available for an out-of-repo dependency, point tsconfig `include` at the dependency's `types/` folder directly). Regenerate after every update — the file's first line names the version that wrote it. `tsc -p <tsconfig>` typechecks hooks and tests.

---

## 5. Testing

The `claude-code/testing` kit has its own file: references/testing-mods.md.

The one rule to carry into the rest of this file: hooks a **test** registers
sit *beneath* the mod, and an unanswered call throws naming its event.

## 6. The shape trap

`$` calls are **positional**; the hook's `e` is an **object**. This is the single most common authoring mistake, and types don't always catch it because the call and the hook see different shapes of the same operation:

| You call | The hook receives |
| --- | --- |
| `$.ui.toast(text, options?)` | `e: { text, timeoutMs? }` |
| `$.store.get(key)` | `e: { key, ... }` |
| `$.mcp.call(server, tool, args)` | `e: { server, tool, args }` |
| `$.model.classify(text, labels, options)` | `e: { text, labels, options? }` |

Measured: calling `$.ui.toast({ text: 'hi' })` compiles under a loose setup and arrives at the hook as `e.text === "[object Object]"` — silent corruption, not a throw. A prior report attributed this to a generated-types bug specific to `$.mcp.call`; it is in fact the general design. Fix: read the `$` call signature, not the event type, when writing a caller.

Related: **every call on `$` is itself a hookable event** (`OpEventOf`, 50 on 2.1.273, plus 34 `EngineEventOf` engine events and 33 computed `ClassicEventOf`, e.g. `classic.PreToolUse`, `classic.Stop`). `{ value: ... }` answers a `$` call, `{ deny }` refuses it, a hook cannot recurse into its own call, and `next.origin` names the caller. These counts are identical between the 2.1.271 repo snapshot and 2.1.273-generated declarations — pin *behavior* claims to a version, not the event catalogue. `on()`'s second overload takes an optional matcher narrowing both when the hook runs and its types: `on('tool.check', { tool: 'Read' }, () => ({ decision: 'allow' }))`. `tool.check` (event + `$` call, resolving to `{ decision, reason?, rule? }`) shipped on 2.1.273 — prefer it over `tool.call` for a guard, since on `tool.call` the core of the dispatch *is* running the tool.

**Still missing on 2.1.273**: no realpath/symlink resolution in `$.fs` (only `read`, `write`, `list`, `exists`, `stat`, `ancestors`) — a path guard ported from a classic hook's `realpathSync` check matches only the unresolved path, and a symlink into a denied location passes.

---

## 7. Walkthroughs

**`diff` — a stateful pane mod.** Registers `/diff` once in `session.start` (guarded idle if another `/diff` is registered); opens a `Pane` via `$.ui.open({ id, title, holdToasts, closeOnEscape, rows })` — "a request, not a grant"; draws it with matcher-keyed `on('ui.render', { component: 'Pane' }, ...)`, pulling elements from `$.ui.resolve(e)`; refreshes on `tool.call` for editing/shell tools, **debounced** via `$.clock.after` and reentrancy-guarded, plus a `$.clock.every` HEAD poll for out-of-session commits. **Lesson**: a command registration + a render hook + a debounced refresh trigger, everything else in plain `register`-closure state (only two `$.store` keys survive reload; `clear`/`resume` resets the rest) — not an external store.

**`telemetry` — adding a noun.** One `engine.create` hook does an ADD-only fold: `const beneath = await next(e); return { ...beneath, telemetry }` — a step may ADD or WITHHOLD nouns but may **not REPLACE** one another step added (fails, naming both plugins). The contract is a **zero-import** `types/index.d.ts`:
```ts
export type Telemetry = { log(entry: TelemetryLogEntry): Promise<void>; mark(entry: TelemetryMarkEntry): Promise<void> }
declare module 'claude-code' { interface EngineInterface { telemetry: Telemetry } }
```
published via `plugin.json`'s `"types"` field; the returned value is typed against `EngineInterface['telemetry']` before spreading, so implementation can't drift from the contract. **Lesson**: a noun is one `engine.create` spread, one import-free `.d.ts`, one `types` pointer — nothing more. A consumer (`diff`) calls `$.telemetry.mark(...)` typed against it purely because its tsconfig `include` covers `*/types/**/*.d.ts`; if `telemetry` isn't loaded the call throws — graceful degradation is `diff`'s own promise, not a guarantee the noun gives.

**`sec-default` — a managed-tier gate.** Seated **outermost** (`prepend` of `["prepend","user","append","builtin","core"]`) on managed/Team/Enterprise machines. Its one real move, `next.to(e, tier)` (`Exclude<Tier, 'prepend' | 'user'>`), is **refused outside a managed tier** — so `--plugin-dir` seats a plugin that can only pass; it's inert. Three moves: continue past `user` (`next.to(e, 'append')`), refuse a `user`-tier caller (`{ deny }`), or pass (`next(e)`). Reaches classic hooks via `on('classic.*', ($, e, next) => next.to(e, 'append'))`; gates `tool.register` (refuses a `user`-tier caller by the exact string `'allowedMcpServers (managed): plugins outside policy may not add tools'` whenever managed settings define `allowedMcpServers`, even empty) and reshapes `tool.list` (merges the org's listing, read past `user`, with the rest as `user` left it; fail-closed). One `readPolicy` memo serves every caller within its TTL, including a *failed* read, so failure stays consistently closed. **Does NOT hook `plugin.register`** — a separate load-time gate (per hooks module joining the chain, judged by declared `tier`/scanned `uses`) that no mod here uses; `sec-default` enforces policy per-event at runtime instead. **Lesson**: a handful of `next.to`/`deny` one-liners plus one memoized policy read — its power is its seat (`prepend`, managed), not its code.

---

## 8. Unverified

- The exact CLI output format of `claude plugin validate` (table vs. JSON, flags beyond the plain invocation shown here).
- Whether `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` is a stable, long-term name for the gating variable, or specific to this early-access window — it appears in no shipped declaration file, only in the run commands above; re-check before quoting it as permanent.
- Whether `plugin.register`'s full gating semantics (judged by declared `tier` and scanned `uses`, per its doc comment) match how a real managed deployment would use it — no shipped mod exercises it.
