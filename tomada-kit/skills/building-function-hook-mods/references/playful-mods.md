<!-- prompt-lint-ignore-file: D002 -->
# Playful and decorative mods

Recipes for the fun end of the API: recolouring Claude Code's own output,
drawing pixel art, hosting a small game above the prompt, and decorating the
band while Claude works. Builds on references/drawing-ui.md — read that
for `ui.render`, the element tables, `Client` and `Raster` in full.

EARLY ACCESS: runs only under `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`.

## Contents

1. Recolouring Claude Code's own output — frozen trees, the `{type:'engine'}` marker, colour strings, free hover styling
2. Pixel / dot art — `Raster` in depth, with a worked sprite animation
3. Games — `Client` as the game-loop host, `onKey` / `onPointer` / `hotkey`
4. Ambient decoration — a band that shows only while Claude works
5. What the surface will refuse

### 9.1 Recolouring Claude Code's own output

**The tree is frozen — you rebuild, you never mutate.** Every element `$.ui.resolve(e)` hands out is "a constructor from props to **the frozen plain-data element**" (`claude-code.d.ts:2696-2697`); the table itself is a "frozen table of constructors" (`d.ts:1869`), and the hook's event argument `e` is "frozen to every depth" (`d.ts:3446`). Writing `node.props.color = 'red'` on anything you got back from `next(e)` is a no-op at best, a throw at worst. To restyle a node you call its constructor again with new props: `Text({ ...node.props, color: 'cyan' }, ...children)`.

**`next(e)` does not always hand you a walkable tree.** `RenderElement` is a discriminated union tagged by `type` (`Box`/`Text`/`Button`/`Input`/`Select`/`Link`/`Code`/`Client`/`Svg`/`Raster`, each with `props` and, for the container types, `children?: RenderNode[]` — `d.ts:5926-6178`) — **but one more variant exists**:
```ts
{ type: 'engine'; ref: number }   // d.ts:6169-6178
```
Doc: "The component core draws itself, with the props held under `ref`... the number core answered from `next(e)`... `0` draws the original props." When a component's built-in rendering is opaque (core drew it internally, nothing below your hook replaced it with a literal tree), `next(e)` resolves to this **marker**, not a `Box`/`Text` tree — there is nothing to walk or recolour. None of the six mods read for this document ever received (or walked) a literal tree back from `next(e)` on a built-in transcript component; every one of them either (a) rewrote `props` and let the engine/next hook re-render with those, or (b) skipped `next(e)` and drew its own small tree from the component's typed props.

**The recipe every real mod actually uses: skip `next(e)`, draw from props.** Recolouring in practice means: register on the component, read the plain-data `props` it was handed (the text is already there — `AssistantMessage.text`, `UserMessage.text`, `ToolUse.tool`/`.input`, `CommandOutput.text`, `InfoNotice.text`, …), and return your own small `Box`/`Text` tree built with your own `TextProps`. This is the "wrap" as far as any observed mod goes: you still call `$.ui.resolve(e)` to get real constructors, and you still fall back to `next(e)` when your own guard doesn't apply (see the `next` table in references/drawing-ui.md §1) — you just never dereference `next(e)`'s result as a tree to walk.

```tsx
/* @jsx h */
export const register = (on) => {
  on('ui.render', { component: 'AssistantMessage' }, async ($, e, next) => {
    if (e.surface !== 'terminal') return next(e)
    const { Text } = $.ui.resolve(e)
    // Recolour Claude's own reply text. isFirstOfReply / text come straight
    // off RenderPropsOf['AssistantMessage'] (claude-code.d.ts:6285-6294).
    return <Text color="#7c3aed">{e.props.text}</Text>
  })
}
```

**Rewriting props instead (the pattern actually observed for restyling a component whose props include something style-relevant), from `Mindful-Claude`:**
```ts
// Mindful-Claude/hooks/register.tsx:98-100 — rewrites Spinner's `message`, not colour,
// but the same next({ ...e, props: {...} }) shape applies to any RenderPropsOf field.
return next({ ...e, props: { ...e.props, message: phase.word } })
```

**Colour string format.** Doc (`d.ts:7793-7794`): "Colors are a theme key or a raw color." Neither is enumerated further in the type declarations; observed raw-colour strings in the wild:
- Named (Ink/chalk-style) colours: `"yellow"`, `"magentaBright"` — `cc-arcade/hooks/boards/common.tsx:25`, `cc-arcade/hooks/boards/pet.tsx:60`.
- Hex: `"#ff8800"`-style strings, produced by `flowpane`'s own `hex()` helper (`flowpane/hooks/tree.ts:34-40`) when handing a colour to a `Text`/`Box` prop.
- Theme keys (semantic, not a literal colour): `"inactive"` — `claude-mods/plugins/context-lens/hooks/register.tsx:264`, e.g. `<Text color="inactive">...`.
No ANSI-256 numeric index or `rgb(...)`-function syntax was found stated or used anywhere in the six repos — treat that as unconfirmed, not as unsupported.

**`hover` — a zero-hook, client-side-only override.** `TextHoverProps`/Button's `hover?: TextHoverProps` carry `color`, `backgroundColor`, `dimColor`, `bold`, `italic`, `underline`, `strikethrough`, `inverse`, plus `scope` (`d.ts:7772-7790`); `BoxHoverProps` carries `borderStyle`, `borderColor`, `borderDimColor`, `backgroundColor`, `display: 'flex'`, plus `scope` (`d.ts:497-512`). Doc, identical wording on `Text`/`Button`/`Box`: **"No hook runs and nothing crosses to the plugin. Refused outside a keyed Box unless it names a `scope`."** (`d.ts:7801-7802` for Text; `693-694` for Button). `scope` (`d.ts:7774-7778`, `499-504`): "Names a hover group of this plugin's: every element it draws with the same `scope`, in any site on the surface, lights while any is hovered... One to 64 characters, no control characters; no keyed Box needed." So: to recolour-on-hover you either (a) nest the element inside a `Box key="anything"` (the key makes that Box a hover scope for everything beneath it), or (b) give the element a `hover: { scope: 'my-group' }` so it lights in sync with every other element sharing that scope string, with no keyed Box needed.

### 9.2 Pixel / dot art (`Raster` in depth)

Full `RasterProps` and the wire encoding are in references/client-and-raster.md — recap of the parts that matter for drawing art:

- **Fixed box.** `columns: number` 1–512, `rows: number` 1–256 (`d.ts:5850-5854`); the box size is set at mount and does not change without a redraw ("A resize is a redraw instead," `d.ts:1864`).
- **Per-cell colour.** Each cell is a `[codePoint, foreground, background]` little-endian `u32` triplet, base64-packed (`d.ts:5855-5864`). A colour is `0x00RRGGBB`, or the single sentinel `0x01000000` (bit 24 set, RGB bits zero) for "the terminal's default." Palette ceiling: "its palette paints 1024 distinct color pairs at once and the rest as their nearest" (`d.ts:5837-5838`).
- **Glyph constraint.** "A code point is one printable width-1 BMP character (blocks, box drawing, braille too), or the tree is refused naming the cell's index" (`d.ts:5860-5861`) — no double-width emoji, no astral-plane codepoints.
- **`$.ui.blit` for animation.** `blit: (args: UiBlitArgs) => Promise<UiBlitResult>` (`d.ts:1866`) repaints a *mounted* Raster's cells "without the redraw `invalidate` asks for... blits between frames fold into one: an animation runs at the frame rate" (`d.ts:1850-1864`). `UiBlitArgs.columns`/`.rows`, if given, are "refused unless it is the mounted" size (`d.ts:8704`, `8709`); mismatched/foreign/bad cells come back as `UiBlitResult.deny` naming why (`d.ts:8719-8728`).
- **Measured cost** (`flowpane`, observed, not authoritative): blitting a mounted Raster runs its animation clock at **~120ms/frame**; falling back to a full `ui.render` redraw (no Raster mounted, or the tree's row layout changed) runs at **~320ms/frame** — `flowpane/CLAUDE.md`, constants `FRAME_MS = 120` / `FRAME_MS_REDRAW = 320` at `flowpane/hooks/register.ts:68-71`.

**Worked example — a sprite drawn as a Raster, animated on a clock.** Reconstructed from the documented `RasterProps`/`$.ui.blit` API (`d.ts:1850-1866`, `5840-5867`) plus the real cell-packing shape `flowpane`'s own `Canvas` class uses (`put`/`encode`, `flowpane/hooks/canvas.ts:178-300`) — no repo in this corpus actually draws sprite/character pixel art (flowpane draws graph diagrams), so this is assembled from real APIs, not copied verbatim:

```tsx
/* @jsx h */
const COLS = 8, ROWS = 4
const HEART_ON = 0x00ff4d6d   // 0x00RRGGBB
const BG = 0x01000000          // terminal default

// Two frames of an 8x4 blinking heart, as codepoint grids (space = blank).
const FRAMES = [
  ['  ██  ██  ', ' ████████ ', '  ██████  ', '   ████   '],
  ['          ', '  ██  ██  ', '   ████   ', '    ██    '],
]

function cellsFor(frame: string[]): string {
  const words = new Uint32Array(COLS * ROWS * 3)
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      const i = (y * COLS + x) * 3
      const lit = frame[y][x] !== ' '
      words[i] = lit ? 0x2588 : 0x20        // '█' or space
      words[i + 1] = lit ? HEART_ON : BG
      words[i + 2] = BG
    }
  }
  return new Uint8Array(words.buffer).toBase64()  // same encoding RasterProps.cells expects
}

export const register = (on) => {
  let frame = 0
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.hasSurvey) return next(e)
    const { Box, Raster } = $.ui.resolve(e)
    return (
      <Box flexDirection="column">
        <Raster key="heart" columns={COLS} rows={ROWS} cells={cellsFor(FRAMES[frame])} />
      </Box>
    )
  })

  // Animate purely by blit — no ui.render redraw needed once mounted (d.ts:1850-1864).
  on('ui.render', { component: 'AbovePrompt' }, ($, e, next) => {
    $.clock.every(500, () => {
      frame = (frame + 1) % FRAMES.length
      void $.ui.blit({ requestId: e.requestId, key: 'heart', cells: cellsFor(FRAMES[frame]) })
    })
    return next(e)
  })
}
```

### 9.3 Games (`Client` as the game-loop host)

Full `ClientModule`/`ClientSurface`/`ClientProps` are in references/client-and-raster.md. For a game, the pieces that matter:

- `surface.state: S | undefined` / `surface.setState(next: S): void` (`d.ts:1071-1076`) — per-instance game state, kept alive by the `key` across the plugin's redraws.
- `surface.onKey((event: ClientKeyEvent) => void): () => void` (`d.ts:1103`, event shape `d.ts:944-956`: `{ key, ctrl?, shift?, meta? }`, "Escape never arrives: it returns the focus" — `d.ts:942`).
- `surface.onPointer((event: ClientPointerEvent) => void): () => void` (`d.ts:1098`, event shape `d.ts:976-998`: `{ type: 'down'|'move'|'up'|'enter'|'leave'; x; y; button?; shift?; alt?; ctrl? }`).
- `surface.every(ms, fn): () => void` (`d.ts:1093`) — the board's own tick clock, independent of `$.ui.invalidate`'s rate cap.
- **Why no `$` on the drawing thread**: `d.ts:1059` — "No `$` here: the hooks module has it, and `post` is the way to reach it." The surface module "Runs in the plugin's surface environment on the drawing thread, under a time budget per call; a throw or an overrun unmounts the instance and draws one line naming the plugin and the module in its place" (`d.ts:962-964`) — confirmed observed: `cc-arcade/README.md:202`.
- **`surface.post(data: JsonValue): void`** (`d.ts:1111`) is the only way back to the hooks module — see the `ui.message` section of references/client-and-raster.md for the full round trip.

`cc-arcade`'s real pattern (`cc-arcade/hooks/boards/snake.tsx:8-38`):
```ts
// surface.state, surface.setState(...), surface.every(100, ...), surface.onKey(({ key }) => ...),
// surface.post({ game: 'snake', score: game.score })
```
and pointer handling (`cc-arcade/hooks/boards/minesweeper.tsx:45-49`):
```ts
surface.onPointer(ev => {
  if (ev.type !== 'down') return
  act(Math.floor((ev.x - 1) / 2), ev.y - 1, ev.button === 'right' ? 'flag' : 'reveal')
})
```
Mounting and remounting via `key` (`cc-arcade/hooks/register.tsx:206-219`):
```tsx
// the key names the board, so switching mounts a fresh one and a redraw keeps the running one;
// module paths must be string literals, since the engine reads them off this source
const key = `board:${active}`
const board =
  active === 'snake' ? <Client key={key} module="./boards/snake.tsx" width={cols} height={rows} props={props} />
  : active === 'tetris' ? <Client key={key} module="./boards/tetris.tsx" width={cols} height={tall(23)} props={props} />
  : /* ... */ null
```
Above/alongside the `Client` board, `cc-arcade` draws a plain `Box`/`Button` picker in the **hooks module itself** (not inside the Client), so `Button`'s `hotkey` can drive game selection from the keyboard directly — `ButtonProps.hotkey` (`d.ts:651-658`): "One digit (`\"1\"`) or one lowercase letter (`\"w\"`) that presses it where the site honours one (the `AbovePrompt` band)... A digit presses from an empty composer; a digit or letter presses on keydown while one of the band's Buttons has the focus." This is the keyboard-input mechanism for controls that live in the band's own element tree (menus, pause/quit buttons) as distinct from `onKey` inside a mounted `Client` (in-game movement, etc).

**Limits that matter for games specifically** (see references/drawing-ui.md §7 for full detail and sourcing):
- Node budget: **not a documented engine constant** — `cc-arcade` tunes its own doom renderer to a working budget of **1500** nodes, divided across rows (`cc-arcade/hooks/boards/doom.tsx:293-295`), described only as "what is left of the engine's node budget for this frame."
- Band height: observed only, "about half the terminal height" (`cc-arcade/README.md:146,201,209`).
- Redraw rate: `$.ui.invalidate` is capped at 10/s generally, 30/s for the shown Pane/band (`d.ts:1842-1844`) — but a `Client`'s own `surface.every` tick is independent of this cap: `cc-arcade` boards run their own loop at 10/s, doom at 20/s, turn-based games/pet at 5/s (`cc-arcade/README.md:208`).
- Crash/overrun: unmounts the instance, replaced by "one line naming the plugin and the module" (`d.ts:962-964`, observed `cc-arcade/README.md:202`).

### 9.4 Ambient decoration (a band that appears only while Claude works)

The `AbovePrompt` props carry `isWorking: boolean` directly (`d.ts:6532`, also on `PromptHint` at `d.ts:6506`) — the engine already recomputes this and re-fires `ui.render` whenever a watched input value changes ("once per input value (props, viewport width), plugin load or `$.ui.invalidate('ui.render')`," `d.ts:2847-2849`). That means the entire "show while working, hide when done" behavior collapses into **one guard clause in the render hook** — no need to track `turn.start`/`turn.complete` hook events yourself. `Mindful-Claude`'s real guard (`Mindful-Claude/hooks/register.tsx:75-77`):

```ts
on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
  if (e.surface !== 'terminal' || !config.enabled || !e.props.isWorking || e.props.hasSurvey) return next(e)
  // ...draw the band; it simply isn't called again with isWorking:true after the turn ends
})
```
`!e.props.isWorking` is one clause among several in a single `if` — the moment the turn completes, the engine recomputes `AbovePrompt`'s props with `isWorking: false`, the hook re-runs, the guard fails, and `next(e)` (nothing) is returned instead. No explicit hide-on-complete code is needed.

A lower-level alternative exists if you need more than a boolean (e.g. correlating a specific turn's id): `'turn.start': TurnStartInput` and `'turn.complete': TurnCompleteInput` are separate hook events (`d.ts:3153`, `3171`), with a worked pattern for holding a `turnId` shown at `d.ts:2217-2226`. `isWorking` is the right tool for a purely visual on/off band; `turn.start`/`turn.complete` are for correlating or cancelling ("`turn.start` handed... `$.turn.abort`," `d.ts:2217-2226") a specific turn.

### 9.5 What the surface will refuse (reject, unmount, or silently drop)

| Condition | Outcome | Source |
|---|---|---|
| A prop outside the allowlisted Box/Text prop set anywhere in the tree | **Whole tree** fails validation; engine draws its own component with the **original** props (your tree is discarded entirely, not partially) | `d.ts:5922-5924` |
| `Client.module` is not a string literal in the source (e.g. a variable), or names a path outside the plugin / no file | Refused **at load** | `d.ts:1019-1025` |
| A `Client` surface module tries to render a nested `Client` (or a `Raster`) | Impossible, not just disallowed: `ClientElements = Omit<Elements['terminal'], 'Client' \| 'Raster'>` — those two constructors are absent from the table handed to a Client module at all | `d.ts:938`, `960` |
| `Code`, `Client`, `Svg`, or `Raster` given children | **Type-enforced** — each variant's `children` field is `undefined` in the `RenderElement` union; cannot even construct one with children | `d.ts:6106-6178` |
| `Raster` or `Svg` drawn on a surface whose table lacks it (Raster on desktop/mobile; Svg on terminal) | Tree refused | `d.ts:6144`, `6156` |
| `Button.hotkey` is anything other than one digit or one lowercase letter | Refused | `d.ts:652-653` |
| `Button.action` names an unknown engine keybinding | Refused | `d.ts:662` |
| Two `Button`s in one drawing share a hotkey | **Not refused** — resolved by precedence: "the later wins" | `d.ts:657` |
| `hover` on `Box`/`Text`/`Button` used outside a keyed enclosing `Box` and without a `scope` | Refused | `d.ts:693-694`, `7801-7802` |
| `Link.href` not `https:`/`http://localhost`, not spelled as `new URL(href).href`, containing `user@host`/`@`/space/non-ASCII, or over 2048 chars | Tree refused | `d.ts:6100-6101`, `3860-3865` |
| `Code.source` over 10,000 chars, or holding a control character other than tab/newline | Tree refused | `d.ts:6112-6113`, `1138-1139` |
| `Svg.source` over 131,072 chars | Tree refused | `d.ts:6144`, `7694` |
| `Svg` given `isInteractive`, expecting script/event-handler attributes to work | They never do — "the frame has no allow-scripts and the scrub strips them" | `d.ts:7714-7716` |
| A `Raster` cell holds a non-printable, double-width, or non-BMP code point | Tree refused, **naming the offending cell's index** | `d.ts:5860-5861` |
| `$.ui.blit` sent with `columns`/`rows` not matching the mounted size, targeting another plugin's Raster, or malformed cells | Refused via `UiBlitResult.deny`, with a reason string | `d.ts:8704`, `8709`, `8719-8728` |
| A `Client` module (or any hook) throws or overruns its per-call time budget | Instance/hook **unmounted or skipped**; one line names the plugin+module (Client), or the hooks beneath/core run in its place (any hook) | `d.ts:962-964` (observed `cc-arcade/README.md:202`), `d.ts:2821-2823` |
| `UserMessage.origin`, or a `SessionMode`/`PromptHint`/`AbovePrompt`/`Pane` prop marked read-only, rewritten or dropped by a hook | Refused, "the hook that passed it failing" | `d.ts:6277`, `6563`, `6597`, `6611` |
| A Client tree with "too many nodes" or "too large serialized size" | **Not documented as a hard number anywhere searched** — only the time-budget overrun path above is specified | see references/drawing-ui.md §7 row 3 |

---

