# Testing a mod

The `claude-code/testing` kit, which `claude plugin test <dir>` runs. It ships
on 2.1.273 although it is hidden from `claude plugin --help`. Tests run in an
environment like the one a plugin runs in — no fs, no network, no process.

The rule that governs everything here: hooks the **test** registers sit
*beneath* the mod, where the rest of the world would be, and nothing is
beneath them — so an unanswered call throws, naming its event. A passing test
answers every `$` call the mod makes.

EARLY ACCESS: requires `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`.

See also references/authoring-and-testing.md for the file layout and build loop.

## Contents

- The inversion rule, and the error the runtime prints when you hit it
- `describe` / `test($, on)` / `expect` / `tier`
- `mock.clock` / `mock.env` / `mock.store`, `clock.advance`, `clock.settle`
- `$.ui.press` and `$.ui.render` — driving a button and a render site with no terminal
- Working test templates, verbatim

---


Exports: `describe`, `test`, `expect`, `mock`, `tier`.

**The inversion, as the runtime states it.** The mod under test loads for real, at its real tier (pinned once per file with `tier(...)`; `user` if omitted). The test's `on(...)` calls sit **beneath** the mod — nothing is beneath *them*. An unanswered `$` call throws, naming the event:
```
Error: no implementation for session.start

nothing beneath the plugins answers session.start: a test answers it with
on('session.start', ...)
```
A passing test must answer every `$` call the mod makes **and** the engine event that drives it. `Plugin = { name; tier?: PluginTier; register }` (`PluginTier = Exclude<Tier, 'core'>`); `test(name, [options], body)` takes `TestOptions = { plugins?: readonly Plugin[]; timeoutMs?: number }` (default 5000ms) — `{ plugins: [...] }` loads *inline* plugins beside the mod under test; `tier(t: PluginTier)` pins the mod's tier, once per file.

**`mock.clock`/`mock.env`/`mock.store`.** `mock.env(on, { USER_TYPE: 'ant' })` answers `$.env.get` from a fixed object (unlisted reads unset). `mock.store(on, { key: value })` answers `$.store.get/set/delete/keys` from an in-memory map. `mock.clock` answers `$.clock` with `MockClock = { now(), advance(ms), set(ms), settle(), sleep(ms) }`: waits (`sleep`/`after`/`every`) hold until an `advance` crosses their due time, resolved in order; `clock.settle()` is `advance(0)` — let in-flight work finish without moving time; held past 10s real time, a wait is let go. Pattern for inspecting a dispatch mid-flight:
```ts
const call = $.command.run(...)   // start unawaited
await clock.settle()              // let it run as far as possible without time moving
await clock.advance(1000)         // let time-dependent parts finish
await call
```

`$.ui.press({ plugin, key, requestId? })` is the chain over every plugin hooked on a pressed `Button`, the Button's own `onPress` at the bottom — exercises a rendered `Button` with no raw keystroke. `$.ui.render(input)` drives a render site directly, no terminal, and the returned tree can be asserted on — a render hook, unit-tested standalone.

**Two verbatim, passing test files (run on 2.1.273):**

Plain `.ts` (`hello/tests/register.test.ts`, paired with a `session.start` hook that toasts):
```ts
import { describe, expect, test, tier } from 'claude-code/testing'

tier('user')

describe('register', () => {
  test('session.start raises a toast', async ($, on) => {
    const toasts: string[] = []
    on('ui.toast', ($, e) => {
      toasts.push(e.text)
      return { value: undefined }
    })
    on('session.start', ($, e) => ({ cwd: e.cwd }))

    await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })

    expect(toasts).toEqual(['hello from a function hook'])
  })
})
```

`.tsx`, testing a render tree (`paint/tests/register.test.tsx`, paired with a mod that replaces `Spinner` and wraps `AssistantMessage`):
```tsx
import { describe, expect, test, tier } from 'claude-code/testing'

tier('user')

describe('register', () => {
  test('the spinner is replaced with a coloured one', async ($, on) => {
    const tree = await $.ui.render({
      surface: 'terminal',
      component: 'Spinner',
      requestId: 'agent-1',
      props: {} as never,
    })

    expect(JSON.stringify(tree)).toContain('magenta')
  })

  test('an assistant message keeps what was beneath and gains a frame', async ($, on) => {
    on('ui.render', { component: 'AssistantMessage' }, ($, e) => {
      const { Text } = $.ui.resolve(e)
      return <Text>ORIGINAL</Text>
    })

    const tree = await $.ui.render({
      surface: 'terminal',
      component: 'AssistantMessage',
      requestId: 'msg-1',
      props: {} as never,
    })

    const json = JSON.stringify(tree)
    expect(json).toContain('ORIGINAL')
    expect(json).toContain('green')
  })
})
```
```
(pass) register > the spinner is replaced with a coloured one [22.36ms]
(pass) register > an assistant message keeps what was beneath and gains a frame [12.63ms]
 2 pass  0 fail   [0.29s]
```
The second test is the template for any wrapping hook: register a hook *beneath* yours that returns a marker, then assert the marker survived and your addition is present. A `.tsx` render tree needs a `.tsx` test file too.

**Naming convention.** A test file is named for what it covers under `hooks/` (`register.test.ts` beside `hooks/register.ts`, `git.test.ts` beside `hooks/git/`), holding its imports, the tier the mod loads in, and one `describe` titled with that name; shared setup sits under `tests/fixtures/`, one export per file.

---

