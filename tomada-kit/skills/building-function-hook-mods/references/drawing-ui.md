# Drawing UI from a Claude Code Mod

Everything a mod can put on screen: the `ui.render` hook, the 14 render sites,
the per-surface element tables, `Client` surface modules, `Raster` + `$.ui.blit`,
and the rest of `$.ui`. For colour/pixel-art/game recipes built on this, see
references/playful-mods.md.

EARLY ACCESS: this API only runs under `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` and
may change between releases. Regenerate the declarations with `/plugin-types`
after every Claude Code update. Line citations below are into
`.claude/types/claude-code.d.ts` as written by 2.1.271; the event and element
surface is unchanged on 2.1.273.

## Contents

1. [`ui.render`](#1-uirender) — registration, `RenderInput`, the 14 components, wrapping vs replacing
2. [Element tables](#2-element-tables) — pointer; full props in element-props.md
3. [JSX / `h` mechanics](#3-jsx--h-mechanics) — the ambient globals and the local-`h` trap
4. [`Client` and `Raster`](#4-client-surface-modules-and-5-raster) — pointer; full detail in client-and-raster.md
6. [Other `ui.*` verbs](#6-other-ui-verbs)
7. [Constraints and gotchas](#7-practical-constraints-and-gotchas-actually-observed)
8. [Minimal examples](#8-minimal-copy-pasteable-examples)

---

## 1. `ui.render`

### Registration

There is **no** plugin-callable `$.ui.render(...)`. `CoreEngineInterface.ui` (the real runtime `$.ui`) exposes only: `notice, invalidate, blit, resolve, log, ask, toast, status, open, close, scroll, focus` (`d.ts:1824-1996`). `ui.render` exists only as a **hook event** a plugin registers on.

A plugin's hooks module exports `register: Register`:

```ts
export type Register = (on: On, options: PluginOptions) => unknown;  // d.ts:5880
export type On = {
    <P extends Pattern>(pattern: P, hook: NoInfer<HookFor<P>>): Registration<HookFor<P>>;
    <P extends Pattern, const M extends Matcher<...>>(pattern: P, matcher: M, hook: ...): Registration<...>;
};  // d.ts:4428-4431
```

Registered as `on('ui.render', matcher, ($, e, next) => ...)` or `on('ui.render', hook)`. Fires (`d.ts:2847-2849`): "when the engine is about to draw a component: once per input value (props, viewport width), plugin load or `$.ui.invalidate('ui.render')`."

(Note: `EventCalls.ui` does list a `render` member, `d.ts:3406-3411`, but this is internal call-signature plumbing for the *testing kit's* `$` — type `Engine` from `claude-code/testing`, `d.ts:9463-9465` — which alone can call `$.ui.render(...)` to simulate a draw in a test. Production plugin code never calls it.)

### `RenderInput` — full shape (`d.ts:6190-6228`)

```ts
export type RenderInput<C extends RenderComponent = RenderComponent, P extends RenderSurface = RenderSurface> =
  C extends RenderComponent ? P extends RenderSurface ? RenderInputOf<C, P> : never : never;  // d.ts:6190

export type RenderInputOf<C extends RenderComponent, P extends RenderSurface> = {
    surface: P;                  // d.ts:6203 — one literal per member
    component: C;                 // d.ts:6207 — matcher key
    requestId: string;             // d.ts:6214 — instance id (tool_use_id / message id / agent id / pane id)
    viewport?: RenderViewport;      // d.ts:6223 — { columns: number; rows: number } (d.ts:6645-6657); absent where unmeasured
    props: RenderPropsOf[C];         // d.ts:6227 — component's plain-data props
};  // d.ts:6195-6228
```

### `RenderComponent` — full list, 14 members (`d.ts:5916`)

```ts
export type RenderComponent = 'AskUserQuestion' | 'UserMessage' | 'AssistantMessage' | 'ToolUse'
  | 'ToolResult' | 'ToolGroup' | 'CommandOutput' | 'Spinner' | 'TurnDuration' | 'InfoNotice'
  | 'SessionMode' | 'PromptHint' | 'AbovePrompt' | 'Pane';
```

Doc (`d.ts:5908-5915`): "Everything `ui.render` can draw: one name per component that has a render site... The permission dialog is drawn by the engine alone... `Pane` is the one component whose instances a plugin opens (`$.ui.open`)."

| # | Component | Props (`RenderPropsOf`, `d.ts`) | Scope | What it is |
|---|---|---|---|---|
| 1 | `AskUserQuestion` | `{ tool: string; questions: unknown[]; metadataSource?: string }` (`6247-6262`) | all | The dialog the AskUserQuestion tool opens |
| 2 | `UserMessage` | `{ text: string; origin: PromptOrigin }` (`6267-6280`) | all | `origin` is read-only; a rewrite dropping/changing it is refused |
| 3 | `AssistantMessage` | `{ text: string; isFirstOfReply: boolean }` (`6285-6294`) | all | Rendered assistant text |
| 4 | `ToolUse` | `{ tool_use_id, tool, input, isRunning, isErrored, isInterrupted, output? }` (`6299-6338`) | all | A single tool call row |
| 5 | `ToolResult` | `{ tool_use_id, tool, output, isErrored }` (`6347-6371`) | all | A tool's result row |
| 6 | `ToolGroup` | `{ calls: readonly ToolGroupCall[]; isActive; isExpanded }` (`6379-6396`); `ToolGroupCall` (`8114-8146`) | all | Batched/parallel tool calls |
| 7 | `CommandOutput` | `{ command, args, text, isErrored }` (`6405-6429`) | all | Slash-command output |
| 8 | `Spinner` | `{ word, message: string \| null, mode: 'requesting'\|'responding'\|'thinking'\|'tool-input'\|'tool-use' }` (`6434-6447`) | **terminal only** (`6431-6432`) | The working spinner |
| 9 | `TurnDuration` | `{ word, durationMs }` (`6452-6462`) | terminal only | Turn-elapsed indicator |
| 10 | `InfoNotice` | `{ text, command: string \| null }` (`6467-6477`) | terminal only | One-off transcript notice |
| 11 | `SessionMode` | `{ modes: readonly string[] }` (`6485-6490`) | one instance, terminal only | Mode indicator (e.g. plan mode) |
| 12 | `PromptHint` | `{ isDraft, isWorking, hint }` (`6498-6515`) | one instance, terminal only | Hint line near the prompt |
| 13 | `AbovePrompt` | `{ hasSurvey, isWorking, maxRows, bodyColumns, scroll: SiteScroll, view: SiteView }` (`6524-6566`) | one instance, terminal only | "The band directly above the prompt input, where the surveys draw" (`6517-6522`) |
| 14 | `Pane` | `{ title, isFocused, bodyColumns, placement: 'dock'\|'inline', scroll: SiteScroll, view: SiteView }` (`6575-6614`) | terminal (+desktop/mobile per surface table) | "The framed region a plugin opened with `$.ui.open({ id })`" (`6568`) |

`RenderElement` (what a hook returns / what `next` resolves to; `d.ts:5926-6178`) is a discriminated union: `StyledElement<'Box'|'Text', ...>`, plus explicit branches for `Button` (`5935-5993`), `Input` (`6008-6047`), `Select` (`6057-6093`), `Link` (`6103-6105`), `Code` (`6115-6117`), `Client` (`6127-6136`), `Svg` (`6146-6148`), `Raster` (`6158-6167`), and `{ type: 'engine'; ref: number }` (`6171-6178` — "the component core draws itself, with the props held under `ref`"; `ref=0` draws the original props).

### `next(e)`: wrapping vs. replacing

Generic doc (`d.ts:2851-2853`): "`next(e)` resolves to the drawing: return it, wrap it, draw your own, or rewrite `props`. A tree that does not validate draws the engine's own; `--plugin-dir` is told why." `next: Next<'ui.render'>` resolves `Promise<RenderElement>`.

Validation-fallback (`d.ts:5922-5924`): "Props are an allowlisted subset of Ink's Box/Text props (the ones `ElementProps` declares); a tree with any other prop fails validation as a whole and the engine's own component is drawn with the original props."

Patterns observed in real mods:

| Pattern | Example | Source |
|---|---|---|
| Pure pass-through (observe only, always `next(e)`) | `PromptHint` hook only reads `e.viewport.columns`, then `return next(e)` | `diff/hooks/register.ts:622-628` |
| Full replace, no `next` call when guard passes | Pane hook returns `Views.paneView(...)` directly; falls back to `next(e)` when `e.requestId !== PANE_ID` etc. | `diff/hooks/register.ts:637-661` |
| Conditional intercept | `on('ui.close', ...)` returns `{ deny: 'back to the file list' }` to cancel, or `await next(e)` and inspects the result | `diff/hooks/register.ts:715-747` |
| Rewrite the **incoming** event before delegating | `next({ ...e, context: [...context, text] })` on `prompt.submit` | `diff/hooks/register.ts:862-908` |
| Rewrite **outgoing** props (wrap) | `return next({ ...e, props: { ...e.props, message: phase.word } })` on `Spinner` | `Mindful-Claude/hooks/register.tsx:98-100` |
| Stack own content under `next`'s result | `const below = await next(e); if (disabled) return below; ...; return stack(Box, below, band)` on `AbovePrompt` | `cc-storytime/hooks/register.ts:135-138` |
| Guard, else build own tree | `if (!active \|\| e.props.hasSurvey \|\| e.surface !== 'terminal') return next(e)` then builds its own `Box`/`Button`/`Client` tree | `cc-arcade/hooks/register.tsx:169-172` |

---

## 2. Element tables

Which elements each surface carries, and the full props of `Box`, `Text`,
`Button`, `Raster`, `Client`, `Svg`, `Input`, `Select`, `Link` and `Code`, are
in references/element-props.md.

Two rules that matter everywhere else in this file:

- **Elements are not globals and not JSX intrinsics.** They come from the
  surface's frozen constructor table: `const { Box, Text } = $.ui.resolve(e)`.
  `JSX.IntrinsicElements` is explicitly empty, so `<box>` does not type-check.
- `$.ui.resolve` is **synchronous** despite living on `$.ui` — a precomputed
  per-surface table lookup, not a dispatch (`claude-code.d.ts:1882`).

## 3. JSX / `h` mechanics

### In the type declarations (authoritative)

Header (`d.ts:12-14`): "the globals a hooks module has: `h` and `Fragment` (what JSX compiles against), the JSX namespace, and the environment's web APIs... A hooks module runs in an environment of its own: no DOM, no Node."

`global` block (`d.ts:9291-9323`):
```ts
global {
  const h: (
    tag: string | ((props: never) => RenderNode | null | undefined),
    props: Record<string, unknown> | null | undefined,
    ...children: unknown[]
  ) => RenderNode | null | undefined   // 9296-9300
  // doc 9292-9295: "The JSX factory (classic runtime, @jsx h; the engine prepends
  // the pragma): a plain-data element from a string tag or a component."

  const Fragment: (props: { children?: RenderNode[] }) => RenderElement  // 9305
  // doc 9302-9304: "<>...</>: a column Box around the children."

  namespace JSX {
    type Element = RenderElement
    type Children = RenderChildren
    type ElementType = (props: never) => RenderNode | null | undefined
    interface IntrinsicElements {}                              // 9316 — EXPLICITLY EMPTY
    interface ElementChildrenAttribute { children: unknown }
    interface IntrinsicAttributes { key?: string }               // 9320-9322
  }
}
```
Doc (`d.ts:9307-9311`): "JSX over the element table: every tag is a constructor from `$.ui.resolve(e)` (`const { Box, Text } = $.ui.resolve(e)`), typed by its props; **there are no intrinsic (string) tags.**" `IntrinsicElements {}` is intentional and empty — lowercase tags like `<box>` do not type-check; only `<Box>` bound from the destructured table works.

`h` calls a function tag with its props (`d.ts:2698-2703`): "`h(Box, { gap: 1 }, ...children)`, and `h` calls a function tag with its props, so the table's constructors are the JSX tags." `h` and `Fragment` are **ambient globals the engine injects** — never imported, never locally declared by the mod.

The suggested tsconfig (`d.ts:34-44`) is reproduced verbatim in references/authoring-and-testing.md §2; its `lib` names no DOM because "its `Text` would shadow the element" (`d.ts:51-52`).

### The "local `h`" gotcha — observed by community authors

The type system cannot catch this: `h` is only an *ambient* global, so any local binding named `h` shadows it and JSX silently compiles to calls against the wrong `h`, breaking every tag in the file. `cc-arcade/README.md:233` states it as a rule ("a local `h` breaks the board at its first draw"), and `cc-arcade/hooks/boards/common.tsx:7` and `Mindful-Claude/hooks/breathe.tsx:11` carry the same warning as a comment.

### tsconfig.json compared across repos

| Repo | `jsx` options | JSX used? |
|---|---|---|
| `diff/` | (not inspected directly, but every `.tsx` file opens with the classic pragma trio, see below) | yes, real `<Box>` JSX |
| `flowpane/` | **none at all** — no `jsx`, `jsxFactory`, or `jsxFragmentFactory` fields; `include` covers only `.ts` | **no JSX** — builds trees via direct calls: `Box({ flexDirection: 'column', children: [...] })`, `Raster({ key, columns, rows, cells })` (`flowpane/hooks/register.ts:1186-1194`, `hooks/tree.ts:189-190`) |
| `cc-arcade/`, `Mindful-Claude/`, `cc-storytime/`, `claude-mods/` | `"jsx": "react", "jsxFactory": "h", "jsxFragmentFactory": "Fragment"` (each `tsconfig.json`) | yes |

Pragma-comment style varies file to file, both are equivalent:
- Full 3-line block `/* @jsxRuntime classic */ /* @jsx h */ /* @jsxFrag Fragment */` — used by every `diff/hooks/views/*.tsx`, `cc-storytime/hooks/views.tsx`, `claude-mods/plugins/token-ledger/hooks/register.tsx`, `claude-mods/plugins/budget-guard/hooks/register.tsx`.
- Just `/* @jsx h */` — used by `cc-arcade/hooks/register.tsx`, `Mindful-Claude/hooks/register.tsx`, `claude-mods/plugins/context-lens/hooks/register.tsx`, `claude-mods/plugins/quota-meter/hooks/register.tsx`.

### How built-ins and community mods actually get elements into scope

`diff/hooks/register.ts:659`: `const { Box, Text, Button, Select, Code } = await $.ui.resolve(e)` at the top-level render hook, then threaded down through a `Kit` object (`kit.ui.Box`, etc.) destructured per sub-view — e.g. `diff/hooks/views/dialog-pane/dialog-pane.tsx:33`: `const { Box, Text } = kit.ui`.

Community mods are **inconsistent about `await`ing `$.ui.resolve(e)`** even though it is synchronous per the type declaration (`d.ts:1882`): `cc-arcade` and `claude-mods/quota-meter` `await` it; `Mindful-Claude`, `claude-mods/context-lens`, `claude-mods/token-ledger`, `cc-storytime` call it unawaited. Both work.

---

## 4. `Client` surface modules, and 5. `Raster`

Both live in references/client-and-raster.md: the `Client` module contract and
its input handling, and the `Raster` cell grid with `$.ui.blit`. The short
version:

- A `Client` is an interactive region one of the plugin's surface modules draws
  and handles input for, on the drawing thread, **without `$`**. One instance
  per plugin; `surface.post()` is the only way back to the hooks module.
- A `Raster` is a leaf: a fixed grid of `[codepoint, fg, bg]` u32 triplets,
  base64-packed, repainted in place by `$.ui.blit` without the redraw that
  `$.ui.invalidate` asks for. Terminal only.

## 6. Other `ui.*` verbs

Direct `$.ui.*` calls live on `CoreEngineInterface.ui` (`d.ts:1824-1996`):

| Verb | Signature | Line | Notes |
|---|---|---|---|
| `open` | `(pane: PaneOpenArgs) => Promise<void>` | `1951` | Opens a `Pane` instance. Width gating: "unasked, it waits undrawn below 144 columns (110 once asked), judged at each open" (`1940-1941`, `4877-4878`). `id`: "1-64 of letters, digits, `_`, `-`" (`1943`, `4882`). |
| `close` | `(pane: PaneCloseArgs) => Promise<void>` | `1965` | Also a **hook event** (`on('ui.close', {id}, ...)`) a plugin can intercept/cancel — see `diff/hooks/register.ts:715-747`. |
| `focus` | `(args: UiFocusArgs) => Promise<UiFocusResult>` | `1995` | Also a hook event — `diff` uses it to re-center a dialog window on the landing element, remapping via `next({ ...e, element: focus.landing })`. |
| `invalidate` | `(event: InvalidatableEventName) => void` | `1849` | `InvalidatableEventName = RenderEventName \| 'prompt.section' \| 'prompt.context' \| 'tool.describe' \| 'command.describe' \| 'config.describe'` (`3782`). **Rate limit** (`1842-1844`): "at most ten a second, thirty for the shown pane and the band (calls sooner fold); a `prompt.section` or `prompt.context` hook: dropped next turn." This is the standard way to trigger a redraw after internal state changes. |
| `log` | `(text: string) => void` | `1895` | Debug text, visible via `--plugin-dir`. |
| `notice` | `(tool_use_id: string, text: string \| undefined) => void` | `1837` | Attaches/clears a transient notice on a specific tool-use row. |
| `resolve` | `<E extends ResolveInput>(e: E) => Elements[E['surface']]` | `1882` | **Synchronous**, not a dispatch — see §2/§3. |
| `scroll` | `(args: UiScrollArgs) => Promise<UiScrollResult>` | `1980` | Also a hook event, used by `diff` to distinguish list-vs-body scroll regions (`diff/hooks/register.ts:777-789`). |
| `status` | `(text: string \| undefined) => void` | `1934` | Persistent one-line pinned status. Primary surface used by `claude-mods`' context-lens/quota-meter/token-ledger/budget-guard. |
| `toast` | `(text: string, options?: ToastOptions) => void` | `1923` | `ToastOptions = { timeoutMs?: number }`, default 4000ms (`7855-7860`). |
| `ask` | `(question: string, options?: readonly string[] \| AskOptions) => Promise<string>` | `1911` | Ties into `AskUserQuestion`'s `ui.render` site (`1900-1902`): "A `tool.call` of `AskUserQuestion` through every hook but the calling one, drawn by `ui.render` on `AskUserQuestion`; a multi-select answer is comma-joined. Rejects when dismissed, and in a `-p` run (no one to ask)." Used by `budget-guard` for its "Send anyway / Do not send" dialog (`budget-guard/register.tsx:298-303`). |
| `blit` | `(args: UiBlitArgs) => Promise<UiBlitResult>` | `1866` | See §5. |

**Hook-only** events (a plugin can register `on(...)`, but there is no matching `$.ui.*` call to invoke them directly — except the testing kit):

| Verb | Argument/Result types | Notes |
|---|---|---|
| `render` | `RenderInput` / `RenderElement` | §1. |
| `press` | `UiPressResult` etc. (`8958-8996`) | Fired on a Button press. Testing kit only exposes `$.press(target)` (`9499`) to simulate a click in tests. |
| `input` | `UiInputArgument`/`UiInputResult` (`8843-8894`) | Fired on `Input` value change/submit. |
| `select` | `UiSelectArgument`/`UiSelectResult` (`9191-9238`) | Fired on `Select` value change. |
| `message` | `UiMessageArgument`/`UiMessageResult` (`8904-8949`) | Fired by a Client's `surface.post()` — §4. |

Structural note: `EngineEventOf` (what `on(...)` can hook into — includes `render`, `press`, `input`, `select`, `message`) is distinct from `CoreEngineInterface`/`OpEventOf` (what `$.ui.*` can directly call — excludes those five). Render/press/input/select/message are draw-time/interaction events a plugin **reacts to**, never operations it **initiates**, except through the testing kit's simulated `$`.

---

## 7. Practical constraints and gotchas actually observed

| # | Constraint | Status | Detail + source |
|---|---|---|---|
| 1 | AbovePrompt band height ≈ half the terminal | **Observed only** (not a numeric constant in `d.ts`) | `cc-arcade/README.md:146`: "The board takes the rows above the prompt that Claude Code gives plugins, about half the terminal height." Repeated `README.md:201,209`. `d.ts`'s `AbovePrompt.props.maxRows` doc (`6524-6566` area) describes it only structurally: "Rows the band may take: in fullscreen, what the bottom slot has left above the prompt; otherwise the terminal's height" — no fraction given. |
| 2 | Redraw rate ≈ 10/s | **Authoritative, and more precise than the rumor** | `d.ts:1842-1844`: "at most ten a second, thirty for the shown pane and the band (calls sooner fold)" — i.e. `$.ui.invalidate` is capped at 10/s in general, **30/s** specifically for an open `Pane` or the `AbovePrompt` band. A mounted `Client`'s own `surface.every()` clock is independent of this cap: `cc-arcade` boards run at 10/s (doom 20/s, pet/turn-based games 5/s — `README.md:208`); `Mindful-Claude`'s `breathe.tsx` ticks at 10/s (`TICK_MS=100`, matching `README.md:64`). |
| 3 | Client tree node limit ≈2000, serialized size ≈100,000 chars | **Not found anywhere** — treat as unverified | No repo or `d.ts` states either number. Closest evidence is `cc-arcade`'s own tuned local budget of **1500** (not 2000), `cc-arcade/hooks/boards/doom.tsx:293-295`: `"// what is left of the engine's node budget for this frame..."` `const maxRuns = Math.max(6, Math.floor(1500 / Math.max(1, rows)) - 1)` — an author's empirical guess, not a cited constant. What happens on overrun **is** documented, but only for the *time* budget: `d.ts:962-964` — "a throw or an overrun unmounts the instance and draws one line naming the plugin and the module in its place," confirmed observed at `cc-arcade/README.md:202`. |
| 4 | No `WebAssembly` in the hooks environment | **Observed, one repo** | `cc-storytime/README.md:77-78`: "The hooks environment has no Node and no DOM, only web globals, so the whole runtime is plain ES2023 on typed arrays. Nothing here uses WebAssembly." Corroborated structurally by `d.ts:13-14`: "A hooks module runs in an environment of its own: no DOM, no Node." (Phrased as a design note, not an explicit platform prohibition.) |
| 5 | `$.ui.resolve` read "loosely" so a build without `Raster`/`Button` degrades | **Not found anywhere** — treat as unverified | `d.ts` describes `resolve` only as a precomputed synchronous table lookup (`1867-1882`), with no mention of missing keys or capability probing. No community mod branches on whether an element constructor exists. |
| 6 | `Box` cannot overlap; `Raster` is a leaf | **Raster-is-leaf: authoritative. Box-can't-overlap: observed + inferred** | Raster leaf, `d.ts:5833-5838` and `6150-6156` ("A leaf, one node however many cells; hooks above wrap or replace it whole"). Box non-overlap is stated explicitly by `flowpane/docs/engine.md:14-16` / `hooks/tree.ts:122-125`: "`Box` lays out in a flex column with no way to overlap, so a Button cannot be put over [a Raster]." `d.ts`'s `BoxProps` (§2) has no `position`/`zIndex`/absolute-placement props, consistent with this but not stated as a rule in `d.ts` itself. |
| 7 | Measured costs | **Mixed** | `flowpane`: blit ≈120ms/frame vs. re-render ≈320ms/frame (`CLAUDE.md`, `register.ts:68-71`); naive full-band send ≈1MB/s at 8fps for a 120×40 pane before diffing (`register.ts:126-137`). `claude-mods/budget-guard`: `$.session.usage()` read latency **5ms cold / 62ms reloaded worker**, threshold `SLOW_READ_MS=30`, cache `3000ms` (`budget-guard/README.md:130,134`, `register.tsx:43-45`). `d.ts` hard caps: `Code.source` ≤10,000 chars (`1138-1139`); `Svg.source` ≤131,072 chars (`7694`); `Link.href` ≤2048 chars (`3858-3872`); Raster 1–512 cols × 1–256 rows, palette "1024 distinct color pairs at once" (`5847-5854`, `5838`); Pane visible only ≥144 cols unasked / ≥110 cols once asked (`1940-1941`); Pane `id` 1–64 chars `[A-Za-z0-9_-]` (`1943`); `ui.message` one post/frame max (`1107-1108`); `$.store` cap "4 MiB for the whole plugin" (`claude-mods/token-ledger/hooks/register.tsx:23`). |

Additional observed conventions worth keeping: all four community repos gate on `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` and require Claude Code ≥2.1.269 (`cc-storytime` states ≥2.1.272).

---

## 8. Minimal copy-pasteable examples

Both examples are reconstructed from real, cited code (not invented): the `AbovePrompt` guard/resolve/row-cap pattern from `Mindful-Claude/hooks/register.tsx:75-100` and `cc-arcade/hooks/register.tsx:169-172`, the plain `Box`/`Text` band style from `cc-storytime/hooks/views.tsx`; the `Pane` example from `diff/hooks/register.ts:637-661` and `claude-mods/plugins/context-lens/hooks/register.tsx:232-237`.

### 8.1 A band above the prompt (`AbovePrompt`, no `Client`)

`hooks/hooks.json` (pattern per `diff/hooks/hooks.json`):
```json
{
  "modules": ["./register.tsx"]
}
```

`hooks/register.tsx`:
```tsx
/* @jsxRuntime classic */
/* @jsx h */
/* @jsxFrag Fragment */

// Never name a local `h` in this file: every JSX tag compiles to a call of `h`,
// and a local `h` breaks the band at its first draw.
// (cc-arcade/hooks/boards/common.tsx:7; Mindful-Claude/hooks/breathe.tsx:11)

export const register = (on) => {
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    // Other surfaces draw their own band; a survey owns the band when one is up.
    // (cc-arcade/hooks/register.tsx:169-172; Mindful-Claude/hooks/register.tsx:75)
    if (e.surface !== 'terminal' || e.props.hasSurvey) return next(e)

    const { Box, Text } = $.ui.resolve(e) // synchronous read (claude-code.d.ts:1882)

    const rows = Math.min(3, e.props.maxRows)

    return (
      <Box flexDirection="column" height={rows}>
        <Text bold>hello from above the prompt</Text>
      </Box>
    )
  })
}
```

Redraw on internal state change: call `$.ui.invalidate('ui.render')` (capped ~10/s, ~30/s for the band — `claude-code.d.ts:1842-1844`).

### 8.2 A minimal `Pane`

`hooks/register.tsx`:
```tsx
/* @jsx h */
/* @jsxFrag Fragment */

const PANE_ID = 'my-pane' // 1-64 chars of letters, digits, _, - (claude-code.d.ts:1943)

export const register = (on) => {
  on('command.call', { command: '/mypane' }, async ($) => {
    await $.ui.open({ id: PANE_ID, title: 'My Pane' })
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    // Not our pane instance: let core/another plugin draw it.
    // (diff/hooks/register.ts:638-640; claude-mods/context-lens/hooks/register.tsx:232-233)
    if (e.requestId !== PANE_ID) return next(e)

    const { Box, Text } = await $.ui.resolve(e)

    return (
      <Box flexDirection="column" padding={1}>
        <Text bold>My Pane</Text>
        <Text dimColor>columns: {e.props.bodyColumns}</Text>
      </Box>
    )
  })

  // Optional: intercept close to redirect instead of letting it happen.
  // (diff/hooks/register.ts:715-747)
  on('ui.close', { id: PANE_ID }, async ($, e, next) => {
    return next(e)
  })
}
```

Note the Pane visibility gate: it "waits undrawn below 144 columns (110 once asked)" (`claude-code.d.ts:1940-1941`) — narrow terminals get nothing until the user has explicitly opened it once.

---

## Unverified

Not confirmed in any searched source (`d.ts`, `diff/`, `flowpane/`, `cc-arcade/`, `Mindful-Claude/`, `cc-storytime/`, `claude-mods/`), beyond the rows §7 already marks as observed-only or unverified:

1. **The full enumerated "allowlisted subset of Ink's Box/Text props" referenced at `d.ts:5922-5924`** — assumed to match the `BoxProps`/`TextProps` listed in §2, but not independently cross-checked field-by-field against a separate `ElementProps` allowlist type.
2. **Generic recolour-by-walking a literal tree returned from `next(e)`** (references/playful-mods.md §9.1) — legal by the `RenderElement` type shape (a tagged union with inspectable `type`/`props`/`children`), but no community mod in this corpus was observed actually doing it; every mod either rewrote `props` via `next({ ...e, props })` or skipped `next(e)` and built its own tree from the component's props. Whether built-in components ever hand back a literal (non-`{type:'engine',ref}`) tree in practice is therefore unconfirmed.
3. **Full syntax accepted by `color`/`backgroundColor` as a "raw color"** — hex (`#rrggbb`) and Ink/chalk-style named colours (`"yellow"`, `"magentaBright"`) were observed in community code; `d.ts` does not enumerate the grammar. ANSI-256 numeric indices or `rgb(...)` function syntax were not found stated or used anywhere and should be treated as unconfirmed.
4. **The sprite/pixel-art `Raster` example in references/playful-mods.md §9.2** is assembled from the documented `RasterProps`/`$.ui.blit` API and `flowpane`'s real `Canvas` cell-packing shape (`put`/`encode`) — no repo in this corpus actually draws character/sprite pixel art (flowpane draws graph diagrams, not sprites), so this specific example is reconstructed, not copied from an existing mod.
