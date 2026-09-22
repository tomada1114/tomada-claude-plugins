---
name: building-function-hook-mods
description: Build a Claude Mod — a Claude Code plugin whose behaviour lives in a TypeScript hooks module, registered as ($, e, next) function hooks behind CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1. Covers drawing on Claude Code's own UI (recolouring its output, pixel art with Raster, games and ambient bands above the prompt via Client surface modules), the 117-event API across the engine, op and classic families, and the validate/test/--plugin-dir loop. Use when asked to write, debug, review or publish a mod or function hook, when a hooks module silently does nothing, when changing how Claude Code itself looks or behaves, or when working with hooks/hooks.json, $.ui.render, $.ui.blit, /plugin-types, or claude plugin validate. Not for classic settings.json shell hooks, which are a separate mechanism.
metadata:
  platforms: claude-code
when_to_use: "write a Claude Mod, function hooks, CLAUDE_CODE_ENABLE_FUNCTION_HOOKS, change Claude Code's colours, draw above the prompt, a game in the terminal, ui.render, hooks/hooks.json, plugin-types"
---

# Building Claude Mods

A **mod** is an ordinary Claude Code plugin whose `hooks/hooks.json` names a
TypeScript module instead of a shell command. The module exports
`register(on, options)` and hooks the engine's events as functions `($, e, next)`
— Koa-style middleware over the whole engine, including its UI.

"Claude Mods" is Anthropic's product name (committed 2026-09-09); "function
hooks" is the implementation primitive. **EARLY ACCESS**: not in the published
docs, and the surface may change between releases.

## Before anything else: the gate

```bash
CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude
```

Without it a hooks module is **ignored with no warning** — no error, no log
line, exit 0, the mod simply does nothing. This is the first thing to check
when a mod appears dead. (`claude plugin validate` is the exception; it works
either way.)

## Quickstart

Copy the starter, which is validated and has passing tests:

```bash
cp -r assets/starter-mod ./my-mod        # relative to this skill's directory
cd my-mod
claude plugin validate .                 # prints every event hooked and every $ call made
CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude plugin test .
CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude --plugin-dir .
```

Then generate the types for your own machine, and point the tsconfig at them:

```bash
CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude -p '/plugin-types'
```

It writes `.claude/types/{claude-code,claude-code-mcp,claude-code-plugins}.d.ts`.
Regenerate after every Claude Code update rather than editing them; the first
line names the version that wrote the file.

## The five facts that make the rest readable

1. **A hook is `($, e, next)`.** `$` is the effect object, `e` the event, `next`
   the rest of the chain. Return a result, or `next(e)` to pass through, or
   `next({...e, ...})` to rewrite on the way down.
2. **Three event families, 117 names.** 34 engine (`session.*`, `turn.*`,
   `tool.call`, `ui.render`), 50 op — **every call on `$` is itself hookable** —
   and 33 `classic.*`, which are the old settings/shell hooks. The classic family
   is a computed template type, so grepping the declarations misses it.
3. **Return shape differs by family.** Engine events each have a bespoke result
   type. Op events (and plugin-added noun events) take `{ value }` to answer or
   `{ deny }` to refuse. Getting this backwards is the most common type error.
4. **Five tiers, outermost first**: `prepend > user > append > builtin > core`.
   Earlier is outer is more authority. A mod you load with `--plugin-dir` is
   `user`, so anything gated on a managed tier is inert for you.
5. **`$` calls are positional; the hook's `e` is an object.**
   `$.ui.toast(text, options?)` but `e: { text, timeoutMs? }`. A mismatch does
   not throw — it silently arrives as `"[object Object]"`.

## Drawing something

Two moves:

```tsx
// REPLACE: read the component's typed props, draw your own tree.
on('ui.render', { component: 'AssistantMessage' }, ($, e, next) => {
  if (e.surface !== 'terminal') return next(e)
  const { Text } = $.ui.resolve(e)
  return <Text color="#7c3aed">{e.props.text}</Text>
})

// WRAP: keep what was beneath and add to it.
on('ui.render', { component: 'AssistantMessage' }, async ($, e, next) => {
  const { Box, Text } = $.ui.resolve(e)
  const beneath = await next(e)
  return (
    <Box flexDirection="column">
      <Text color="green" dimColor>{'┌─ claude'}</Text>
      {beneath}
    </Box>
  )
})
```

Three rules that bite immediately:

- **JSX requires a `.tsx` module.** A `.ts` module with JSX is rejected at load
  by `claude plugin validate` with a parse error. Name it in `hooks.json`.
- **Never declare a local `h`.** `h` and `Fragment` are ambient globals the
  engine injects; every JSX tag compiles to a call of `h`.
- **Elements are not globals.** `const { Box, Text } = $.ui.resolve(e)` — a
  synchronous table lookup. `JSX.IntrinsicElements` is empty, so `<box>` will
  not type-check.

For an ambient band, guard on `e.props.isWorking` in an `AbovePrompt` render
hook — that one clause is the whole show-while-working/hide-when-done
behaviour. For pixel art use `Raster` (a base64 grid of
`[codepoint, fg, bg]` u32 triplets) and animate it with `$.ui.blit`, which
repaints without a redraw. For a game, mount a `Client` surface module, which
gets `onKey`/`onPointer`/`setState` on the drawing thread but no `$`.

## Testing

`claude plugin test` ships on 2.1.273 though it is hidden from
`claude plugin --help`. The kit inverts the world: hooks the **test** registers
sit *beneath* the mod, and an unanswered call throws naming its event. So a
passing test answers every `$` call the mod makes. `$.ui.render(input)` drives a
render site directly, so a visual mod is unit-testable with no terminal.

## Before you publish

Run `claude plugin validate` on any mod you did not write. It prints the static
side-effect inventory — every event hooked, every `$.noun.verb` called — derived
before the mod runs, so a mod cannot hide from it. Distribution is the ordinary
plugin path: `claude plugin marketplace add <owner/repo>`, then
`claude plugin install <name>@<marketplace>`.

## References

| File | Read it for |
|---|---|
| [references/api-model.md](references/api-model.md) | The continuation model, tiers, the `$` nouns, the full event catalogue, `engine.create` noun contracts |
| [references/security-model.md](references/security-model.md) | The static side-effect scan, `plugin.register` refusal, what an organization can take away from a mod |
| [references/drawing-ui.md](references/drawing-ui.md) | `ui.render`, the 14 render sites, the rest of `$.ui` |
| [references/client-and-raster.md](references/client-and-raster.md) | `Client` surface modules and the `Raster` cell grid — what a game or an animation is built from |
| [references/element-props.md](references/element-props.md) | Which elements exist per surface, and every prop of each |
| [references/playful-mods.md](references/playful-mods.md) | Recolouring Claude Code's output, pixel art, games, ambient bands, and what the surface refuses |
| [references/authoring-and-testing.md](references/authoring-and-testing.md) | Exact file layout, the built-in mods' patterns, the build loop |
| [references/testing-mods.md](references/testing-mods.md) | The `claude-code/testing` kit, the inversion rule, working test templates |
| [references/traps-and-ecosystem.md](references/traps-and-ecosystem.md) | What is broken today, which community reports are stale, what already exists, open niches |

Anthropic's own three built-in mods — `diff`, `telemetry`, `sec-default` — are
published as source at `anthropics/claude-code/tree/main/mods` and are the best
worked examples available. The feedback thread is `anthropics/claude-code#91870`.

## Hard rules

- Treat a claim from the feedback thread as unconfirmed until it holds on your
  own version — the thread spans v259–2.1.272 and at least 11 of its claims
  were retracted by their own authors. `references/traps-and-ecosystem.md` marks
  which are stale.
- Guard with `tool.check`, not `tool.call` — on `tool.call` the core of the
  dispatch *is* running the tool, so there is nothing left to refuse.
- A path guard is not symlink-safe: `$.fs` still has no realpath, so a symlink
  into a denied location passes.
- Rebuild rather than mutate a tree returned by `next(e)`. Elements are frozen
  plain data, and `next(e)` may resolve to an opaque `{ type: 'engine', ref }`
  marker with nothing to walk. Call a constructor again, or rewrite `e.props` and
  delegate.
