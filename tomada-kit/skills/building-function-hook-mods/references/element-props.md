# Element and prop reference

Which elements exist on which surface, and the full prop type of every one.
Split out of references/drawing-ui.md as a lookup table — read that file
for how rendering works; come here for "what props does `Box` take".

Line citations are into `.claude/types/claude-code.d.ts` (2.1.271).


`RenderSurface = 'terminal' | 'desktop' | 'mobile'` (`d.ts:6635`). Doc (`d.ts:6626-6634`): "terminal is Ink, which draws the hook's whole tree; desktop (Claude Code Desktop) and mobile (the Claude mobile app) are remote surfaces that draw the tree themselves."

`Elements` table (`d.ts:2721-2758`), doc (`d.ts:2713-2720`): "All carry `Box`, `Text`, `Button`, `Link`, `Code`; terminal and desktop add `Input`, `Select`, `Client`; desktop and mobile `Svg`; terminal `Raster`."

| Surface | Elements | Count |
|---|---|---|
| `terminal` | Box, Text, Button, Input, Select, Link, Code, Client, Raster | 9 |
| `desktop` | Box, Text, Button, Input, Select, Svg, Link, Code, Client | 9 (no Raster) |
| `mobile` | Box, Text, Button, Link, Code, Svg | 6 (no Input, Select, Client, Raster) |

Mobile gap is deliberate, not a device limitation (`d.ts:2744-2749`): "No `Input` or `Select`: the control protocol carries presses (`ui_press`) but no `ui_input` or `ui_select` yet; not a limit of the device. The table grows when those messages exist."

**Elements are NOT globals / not JSX intrinsics.** Header (`d.ts:15-17`): "The elements a render hook draws with (`Box`, `Text`, `Button`, ...) are not globals: they come from the surface's table, `const { Box, Text } = $.ui.resolve(e)`." Each entry is `ElementConstructor<P> = (props: P & ElementChildren) => RenderElement` (`d.ts:2703`) — a **function value**, not a string tag. `$.ui.resolve` (`d.ts:1882`, doc `1867-1882`): "A read, not a dispatch: the engine ran `ui.resolve` ... at load, per surface and component. Narrowed `e.surface`: that table exactly." — it is synchronous, despite being on `$.ui`.

## Contents

- [Which elements each surface carries](#element-tables-terminal--desktop--mobile)
- `BoxProps`, `TextProps`, `ButtonProps` (including `hotkey`)
- `RasterProps`, `ClientProps`, `SvgProps`
- `InputProps`, `SelectProps`, `LinkProps`, `CodeProps`

### `BoxProps` — full (`d.ts:518-571`)

```ts
export type BoxProps = {
    key?: string;                                    // 527 — hover-scope key
    hover?: BoxHoverProps;                             // 536
    flexDirection?: 'row' | 'column' | 'row-reverse' | 'column-reverse';
    flexGrow?: number; flexShrink?: number;
    flexWrap?: 'nowrap' | 'wrap' | 'wrap-reverse';
    alignItems?: 'flex-start' | 'center' | 'flex-end' | 'stretch';
    alignSelf?: 'flex-start' | 'center' | 'flex-end' | 'auto';
    justifyContent?: 'flex-start' | 'center' | 'flex-end' | 'space-between' | 'space-around' | 'space-evenly';
    gap?: number; columnGap?: number; rowGap?: number;
    width?: number | string; height?: number | string;
    minWidth?: number | string; minHeight?: number | string;
    margin?: number; marginX?: number; marginY?: number;
    marginTop?: number; marginBottom?: number; marginLeft?: number; marginRight?: number;
    padding?: number; paddingX?: number; paddingY?: number;
    paddingTop?: number; paddingBottom?: number; paddingLeft?: number; paddingRight?: number;
    borderStyle?: string; borderColor?: string; borderDimColor?: boolean;
    backgroundColor?: string;
    overflow?: 'visible' | 'hidden';
    display?: 'flex' | 'none';
};  // 518-571
```
`BoxHoverProps` (`497-512`): `{ scope?: string; borderStyle?: string; borderColor?: string; borderDimColor?: boolean; backgroundColor?: string; display?: 'flex' }`.

Note: `BoxProps` has **no `position`, `zIndex`, `top`/`left`** — consistent with pure flexbox flow with no overlap (see §7.6).

### `TextProps` — full (`d.ts:7796-7814`)

```ts
export type TextProps = {
    hover?: TextHoverProps;   // 7804
    color?: string; backgroundColor?: string; dimColor?: boolean;
    bold?: boolean; italic?: boolean; underline?: boolean; strikethrough?: boolean; inverse?: boolean;
    wrap?: 'wrap' | 'end' | 'middle' | 'truncate' | 'truncate-start' | 'truncate-middle' | 'truncate-end';
};  // 7796-7814
```
`TextHoverProps` (`7772-7790`): same fields as above minus `wrap`, plus `scope?: string`.

### `ButtonProps` — full, incl. `hotkey` (`d.ts:641-702`)

```ts
export type ButtonProps = {
    key?: string;         // 646 — defaults to label
    label?: string;        // 650
    hotkey?: string;        // 659 — see below
    action?: string;         // 668 — engine keybinding action name, e.g. "app:cycleDiffBase"
    plain?: true;             // 673
    dimColor?: boolean;       // 678
    autoFocus?: true;          // 687
    hover?: TextHoverProps;     // 696
    onPress: () => void;         // 701
};  // 641-702
```
`hotkey` doc (`651-658`): "One digit (`\"1\"`) or one lowercase letter (`\"w\"`)... A digit presses from an empty composer; a digit or letter presses on keydown while one of the band's Buttons has the focus (Shift+w matches `\"w\"`; held keys repeat). Of two Buttons on one hotkey the later wins." **The type is plain `string`** — the digit/lowercase-letter rule is JSDoc-only, not TS-enforced.

### `RasterProps`, `ClientProps`, `SvgProps` — full

`RasterProps` (`d.ts:5840-5867`) — see §5 for encoding detail:
```ts
export type RasterProps = {
    key: string;      // 5845 — address $.ui.blit names, unique among the tree's Rasters
    columns: number;   // 5850 — 1 to 512; site clips overflow
    rows: number;        // 5854 — 1 to 256
    cells: string;         // 5866 — base64 of columns*rows little-endian u32 triplets
};
```

`ClientProps` (`d.ts:1010-1051`) — see §4:
```ts
export type ClientProps = {
    key: string;                 // 1018
    module: string;               // 1027
    props?: unknown;               // 1035 — JsonValue, bounded like tree text
    width?: number | string;        // 1040
    height?: number | string;        // 1045
    flexGrow?: number;                // 1050
};
```

`SvgProps` — full (`d.ts:7692-7719`):
```ts
export type SvgProps = {
    source: string;         // 7696 — SVG document, at most 131072 characters
    alt: string;              // 7701 — required accessibility text
    width?: number;            // 7705 — CSS pixels
    height?: number;             // 7709 — CSS pixels
    isInteractive?: boolean;      // 7718 — sandboxed iframe for hover/CSS :hover/SMIL/tooltips
};
```
`isInteractive` doc (`7714-7716`): "It never enables script or event-handler attributes (the frame has no allow-scripts and the scrub strips them); presses that other plugins should observe go on an enclosing element."

### Other prop types

- `InputProps` (`d.ts:3724-3766`): `{ key: string; label?: string; placeholder?: string; value?: string; submitLabel?: string; autoFocus?: true; onInput?: (value, e: UiInputArgument) => void; onSubmit: (value, e: UiInputArgument) => void }`
- `SelectProps` (`d.ts:6732-6764`): `{ key: string; label?: string; options: readonly SelectOption[]; value?: string; autoFocus?: true; onSelect: (value, e: UiSelectArgument) => void }`; `SelectOption` (`6719-6722`): `{ value: string; label?: string }`
- `LinkProps` (`d.ts:3858-3872`): `{ href: string; label?: string }` — `href` must be `https:` (or `http://localhost`), ≤2048 printable-ASCII chars, spelled as `new URL(href).href`, no `user@host`/`@`/space/non-ASCII (`3860-3865`)
- `CodeProps.source`: at most 10,000 characters; "tab and newline are the only control characters it may hold" (`d.ts:1138-1139`)

---

