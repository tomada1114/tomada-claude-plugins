# `Client` surface modules and `Raster`

The two heavyweight drawing primitives: a `Client` surface module (an
interactive region with its own input handling, on the drawing thread, without
`$`) and `Raster` (a cell grid repainted by `$.ui.blit` without a redraw).
Together they are what a game or an animation is built from.

Read references/drawing-ui.md first for how `ui.render` works.
Line citations are into `.claude/types/claude-code.d.ts` (2.1.271).

## Contents

1. [`Client` surface modules](#client-surface-modules) — the module contract, `ClientSurface`, the string-literal `module` rule, `key` and remounting, posting back with `ui.message`
2. [`Raster` + `$.ui.blit`](#raster--uiblit) — the cell grid, the wire encoding, when to blit instead of re-rendering, measured cost

---

## `Client` surface modules

### `ClientModule` (`d.ts:966`)

```ts
export type ClientModule<P extends JsonValue = JsonValue, S = unknown> =
  (props: P, surface: ClientSurface<S>) => RenderElement;
```
Doc (`d.ts:958-964`): "The component a surface module exports (default, or its one PascalCase export): from props and surface to the tree drawn (no nested `Client`). Runs in the plugin's surface environment **on the drawing thread, under a time budget per call**; a throw or an overrun **unmounts the instance and draws one line naming the plugin and the module in its place**."

### `ClientSurface<S>` — full (`d.ts:1061-1112`)

```ts
export type ClientSurface<S = unknown> = {
    readonly elements: ClientElements;                                   // 1066
    readonly state: S | undefined;                                       // 1071
    setState: (next: S) => void;                                         // 1076
    readonly columns: number;                                            // 1081
    readonly rows: number;                                               // 1086
    every: (ms: number, fn: () => void) => () => void;                   // 1093
    onPointer: (fn: (event: ClientPointerEvent) => void) => () => void;  // 1098
    onKey: (fn: (event: ClientKeyEvent) => void) => () => void;          // 1103
    post: (data: JsonValue) => void;                                     // 1111
};
```
`ClientElements = Omit<Elements['terminal'], 'Client' | 'Raster'>` (`d.ts:938`, doc `930-936`) — the terminal's table minus `Client` (no nesting) and `Raster` (needs `$`). No `$` inside a Client module: `d.ts:1059` — "No `$` here: the hooks module has it, and `post` is the way to reach it."

`ClientPointerEvent` (`d.ts:976-998`): `{ type: 'down'|'move'|'up'|'enter'|'leave'; x; y; button?: 'left'|'middle'|'right'; shift?: true; alt?: true; ctrl?: true }`. `ClientKeyEvent` (`d.ts:944-956`): `{ key: string; ctrl?: true; shift?: true; meta?: true }` — "Escape never arrives: it returns the focus" (`d.ts:942`).

### `path` must be a string literal

`module: string` (`d.ts:1027`) — the field's **TypeScript type is plain `string`**, not a template-literal type; the literal requirement is a **load-time/static-analysis rule**, not TS-enforced: doc (`d.ts:1019-1025`): "The surface module's path, a string literal relative to this file: `module: \"./<name>.tsx\"`... Read off the source: a variable there is refused at load, as is a path outside the plugin or naming no file."

Observed, identically worded: `cc-arcade/README.md:233` ("write Client module paths as string literals, because the engine reads them off the source"); `cc-arcade/hooks/register.tsx:206-219` comment: "module paths must be string literals, since the engine reads them off this source."

### `key` prop and one-instance-per-plugin

`key: string` (`d.ts:1018`): "The instance's address within the drawing: two `Client`s of one plugin in one tree take two keys. What `e.element` carries at `ui.message`." "One instance per plugin" (`RenderElement`'s `Client` branch doc, `d.ts:6119-6125`): "A region one of the plugin's surface modules... draws and handles input for on the drawing thread, without `$`... **One instance per plugin**, drawing and `key` lives while the node stays in the tree, and talks to the plugin's hooks through `ui.message`."

Observed key patterns for controlled remounting:
- `cc-arcade/hooks/register.tsx:206-219` — `const key = `board:${active}`` so switching the active game mounts a fresh instance, while a redraw with the same key keeps the running one.
- `Mindful-Claude/hooks/register.tsx:86-92` — `const key = `breathe:${running.startedAt}:${config.exercise}:${running.style}`` — remounts on style/exercise change, otherwise preserved across ticks.

### `props`

`props?: unknown` (`d.ts:1035`), doc (`d.ts:1032`): "Bounded as a tree's text is; **not a channel for closures**."

### Posting back — `ui.message`

The Client-side call is `surface.post(data: JsonValue): void` (`d.ts:1111`, doc `1104-1110`): "Sends plain data to the plugin's hooks module: `e.data` of a `ui.message` only that plugin's hooks see, **one per frame at most**. A later post in the same frame replaces an undelivered one; a hook answering `{ props }` hands this instance its next props."

Raises hook event `'ui.message': UiMessageArgument` (`d.ts:2900`), full shape (`d.ts:8904-8933`):
```ts
export type UiMessageArgument = {
    surface: RenderSurface;
    component: RenderComponent;
    requestId: string;
    element: string;   // the Client's key
    module: string;
    data: unknown;      // rewritable
};
```
Result `UiMessageResult` (`d.ts:8943-8949`): `{ props?: unknown }`. Doc (`8935-8941`): "Core answers `{}`... A hook that answers `{ props }` hands the posting instance its next props directly, its local state kept, with no `ui.render` run." **There is no `$.ui.message(...)` call** — the only way to push data *into* a running Client is a hook answering `{ props }`, or a normal `ui.render` redraw handing new `props`.

Observed usage: `cc-arcade/hooks/register.tsx:155-167` — `on('ui.message', ...)` reacts to a board's score/finish post; `Mindful-Claude/hooks/register.tsx:66-73` — reacts to `{word, exercise}` posted each phase-line change, feeding the `Spinner` rewrite; `Mindful-Claude/hooks/breathe.tsx` — `surface.post({ word: spinnerWord(next), exercise: exercise.name })`; `cc-arcade/hooks/boards/minesweeper.tsx:45-49`:
```ts
surface.onPointer(ev => {
  if (ev.type !== 'down') return
  act(Math.floor((ev.x - 1) / 2), ev.y - 1, ev.button === 'right' ? 'flag' : 'reveal')
})
```

**Crash isolation confirmed observed**: `cc-arcade/README.md:202` — "A board is replaced by one line naming the plugin and the module. The board threw an error or ran over its time budget and was unmounted." (matches `d.ts:962-964` exactly).

---

## `Raster` + `$.ui.blit`

### Cell grid model (authoritative)

`RasterProps` (full, `d.ts:5840-5867`):
```ts
export type RasterProps = {
    key: string;      // 5845 — unique among the tree's Rasters; addresses $.ui.blit
    columns: number;   // 5850 — 1 to 512; site clips overflow
    rows: number;        // 5854 — 1 to 256
    cells: string;         // 5866 — see encoding below
};
```
Encoding (`d.ts:5855-5864`): "standard padded base64 of `columns * rows` little-endian u32 triplets `[codePoint, foreground, background]`. A code point is one printable width-1 BMP character (blocks, box drawing, braille too), or the tree is refused naming the cell's index; a color is `0x00RRGGBB`, or `0x01000000` (bit 24 alone) for the terminal's default." Example: `const words = Uint32Array.of(0x2588, 0xff8800, 0x01000000); const cells = new Uint8Array(words.buffer).toBase64()`.

Constraints (`d.ts:5833-5838`): "A leaf: no children, `hover` or `onPress` yet; repainted in place by `$.ui.blit`. Terminal only for now (elsewhere a fragment); **its palette paints 1024 distinct color pairs at once and the rest as their nearest.**"

### `$.ui.blit` (authoritative)

`blit: (args: UiBlitArgs) => Promise<UiBlitResult>` (`d.ts:1866`). Doc (`d.ts:1850-1864`): "Repaints a `Raster` this plugin's own render hook drew, still mounted, with new cells, **without the redraw `invalidate` asks for**. The surface keeps the cells for that Raster (by site and `key`) and paints them at its next frame, so blits between frames fold into one: an animation runs at the frame rate. A resize is a redraw instead." Example: `$.clock.every(33, () => $.ui.blit({ requestId, key, cells: frame() }))`.

`UiBlitArgs` (`d.ts:8688-8713`): `{ requestId: string; key: string; cells: string; columns?: number; rows?: number }` — `columns`/`rows`, if given, must equal the mounted size. `UiBlitResult` (`d.ts:8719-8728`): `{ deny?: string }` — "Absent when the cells were taken; else why not: nothing of this plugin's is mounted there, the size is not the mounted one, the cells are bad."

There is also a hook event `'ui.blit': UiBlitArgs` (`d.ts:4613`) — "a hook above the painter may repaint the cells with `next`, or refuse with `{ deny }`" (`4610-4611`).

### `flowpane`'s concrete implementation (observed — this instantiates the abstract wire format above)

Cell grid (`flowpane/hooks/canvas.ts:178-236`, header `4-9`): a flat `Uint32Array`, row-major triplets `[codePoint, fg, bg]`:
```ts
export class Canvas {
  readonly columns: number   // clamped Math.min(512, ...)
  readonly rows: number       // clamped Math.min(256, ...)
  private readonly words: Uint32Array   // columns*rows*3 u32 slots
  put(x, y, codePoint, fg, bg?) { const i = (y*this.columns+x)*3; this.words[i]=codePoint; this.words[i+1]=fg; if (bg!==undefined) this.words[i+2]=bg }
  cell(x, y) { const i = (y*this.columns+x)*3; return { code: this.words[i], fg: this.words[i+1], bg: this.words[i+2] } }
}
```
`Canvas.encode()` (`canvas.ts:284-300`) slices the buffer and calls `Uint8Array.toBase64()` — "the `cells` prop and `$.ui.blit` both take" this same base64.

Colours packed 24-bit ints, not hex/ANSI (`canvas.ts:135-139`):
```ts
export type Rgb = number
export function rgb(r, g, b): Rgb { return ((r&0xff)<<16)|((g&0xff)<<8)|(b&0xff) }
```
Sentinel `DEFAULT_COLOR = 0x01000000` (`canvas.ts:11-12`) — "terminal's own colour." Hex strings appear only at the boundary into an *element* prop (`Text.color`), via `hex()`/`cellColor()` (`hooks/tree.ts:34-40`, `canvas.ts:151-159`), pre-rounded to the Raster's 4-bit-per-channel palette so element-drawn rows visually match Raster-drawn rows (rounding gotcha: `flowpane/docs/engine.md:34-44` — "keeps four bits a channel and rounds each to the nearest seventeenth, so a Raster draws `#282828` as `#222222`").

### When to blit vs. re-render — observed rule and measured cost

`flowpane/CLAUDE.md`: "**A `Raster` is blitted, an element tree is re-rendered.** `ui.blit` repaints a mounted Raster at 120 ms a frame; a redraw through `ui.render` costs a render and runs at 320. Animation belongs in the Raster." Matching constants, `flowpane/hooks/register.ts:68-71`:
```ts
const FRAME_MS = 120         // with a Raster
const FRAME_MS_REDRAW = 320  // without one, every frame is a re-render
```
wired at `register.ts:669`: `$.clock.every(state.hasRaster ? FRAME_MS : FRAME_MS_REDRAW, () => frame($, run))`.

Blit call site (`flowpane/hooks/register.ts:567-629`, `repaint()`):
```ts
if (!state.hasRaster) { $.ui.invalidate('ui.render'); return }  // no Raster mounted: must go through the tree

const bands = bandsOf(state.canvas.rows, drawn.hotspots)
if (!sameBands(bands, state.bands)) {           // node-label rows moved: blit alone can't restructure the tree
  state.sent.clear(); $.ui.invalidate('ui.render'); return
}
for (const band of bands) {
  if (!band.key) continue
  const cells = state.canvas.encode(band.from, band.rows)
  if (state.sent.get(band.key) === cells) continue   // diff before sending
  state.sent.set(band.key, cells)
  void $.ui.blit({ requestId: PANE_ID, key: band.key, cells }).catch(() => state.sent.delete(band.key))
}
```
Bandwidth rationale (`register.ts:126-137` comment): "Every frame used to send every band. A pane a hundred and twenty columns by forty is five thousand cells, twelve bytes each, and at eight frames a second that is most of a megabyte a second crossing the wire to say that nothing moved..." — hence the `state.sent` diff cache before every blit.

Why a Raster can't hold interactive nodes (observed, both flowpane and matches `d.ts`'s own "leaf" wording): `flowpane/docs/engine.md:14-16` / `flowpane/hooks/tree.ts:122-125`: "A Raster is a leaf — 'no children, `hover` or `onPress` yet' — and `Box` lays out in a flex column with no way to overlap, so a Button cannot be put over one. A pane drawn as a single Raster therefore has nothing to click." This is why flowpane splits its canvas into alternating **Raster bands** (pure picture) and **element rows** (`Text`/`Button`, for anything clickable) — see `flowpane/hooks/tree.ts:149-208`.

---

