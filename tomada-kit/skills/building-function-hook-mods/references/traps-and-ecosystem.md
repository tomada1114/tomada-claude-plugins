# Claude Mods / function hooks — traps and ecosystem state

Scope: what's broken, what's stale, what already exists, how mods distribute, and where the open niches are, as of Claude Code 2.1.273 (2026-09-15). Community claims are attributed to a GitHub handle from anthropics/claude-code#91870 (Sep 2026, v259–2.1.272); corrections are attributed to "verified on 2.1.273." **Where the two disagree, 2.1.273 wins** — never treat a stale thread claim as current fact.

## Contents
1. Status and terminology
2. Stale vs live — thread claims checked against 2.1.273
3. Design rationale (Anthropic/`poteat`)
4. Retractions — verify before trusting a thread claim
5. What already exists
6. Distribution
7. Idea space

## 1. Status and terminology

Anthropic (`poteat`, maintainer) opened #91870 2026-09-03 as a proposal soliciting feedback. On 2026-09-09 the issue body was edited with a commitment:

> "We're now committed to shipping function hooks, on the scale of weeks in lieu of days or months. As well, from a product perspective, we are going to be calling this functionality 'Claude Mods.' The engineering term of art 'function hook' will still exist as the documented implementation primitive Mods are built on. A mod is just a plugin that uses function hooks, nothing is changing there."
> — poteat, community update, 2026-09-09, issue body

Terminology to keep straight: **"Claude Mods"** is the product name; **"function hooks"** is the implementation primitive; a **mod** is an ordinary Claude Code plugin whose `hooks/hooks.json` names a TypeScript module — not a new plugin type. Gate: `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` (env var, one-off prefix or `settings.json` `env` key). None of this — the flag, `/plugin-types`, the `$` API — is in the published docs yet; every real mod README in the corpus says so independently.

**Verified on 2.1.273**: a hooks module in a plugin loaded without the flag is **ignored with no warning at all** — no error, no load-failure log entry, exit 0, the mod simply does nothing. This is the first thing to check when a mod "does nothing." `claude plugin validate` is the exception: it statically inventories a module's hooked events and `$` calls **without** the flag, before any mod code runs.

## 2. Stale vs live

`poteat`'s own thread demonstrated that a build-pinned claim can flip within the thread itself (Arunjay4213's `$.session.usage` gap, gone two builds later) — every row below is time-boxed to the version in column 2, not a permanent fact.

| # | Claim (thread) | Version measured | Status on 2.1.273 | Note |
|---|---|---|---|---|
| 1 | `tool.check` not implemented, absent from generated types | 2.1.267 (sirmaelstrom) | **STALE → shipped** | Ships as both an event and `$.tool.check({tool, input})`, resolving `{decision, reason?, rule?}`. Use it, not `tool.call`, for guards — `tool.call`'s core *is* running the tool, so there's nothing left to refuse there. |
| 2 | `claude plugin test` documented but not shipped as a runnable command | 2.1.270 (lperezmo) | **STALE → shipped** | Ships on 2.1.273, runs, has a working test harness (`claude-code/testing`) — but is hidden from `claude plugin --help`. |
| 3 | Event catalogue: "84 event names" (undifferentiated) in the `.d.ts` | 2.1.272 (Marat) | **CLARIFIED** | 2.1.273 declarations: 34 `EngineEventOf` + 50 `OpEventOf` = 84 (matches Marat's count) + 33 `ClassicEventOf` (computed, not string literals — a naive grep misses this family) = **117 hookable names total**. Engine+Op counts unchanged 2.1.271→2.1.273. |
| 4 | `$.fs` has no `realpath`/symlink resolution; a ported `realpathSync`-based path guard is bypassable via symlink | Sep 15 declarations (djscruggs) | **STILL LIVE** | Grep of 2.1.273 declarations: 0 hits for `realpath`, `symlink`. `$.fs` only has `read`/`write`/`list`/`exists`/`stat`/`ancestors`. Unresolved. |
| 5 | `$.mcp.call`'s generated types "show the wrong call shape" — a bug | 2.1.270 (lperezmo) | **STALE → reclassified** | Not `$.mcp.call`-specific: `$` calls are positional (`$.mcp.call(server, tool, args)`), the *event* `e` is always an object (`{server, tool, args}`). This is the general `$`-vs-`e` design, not a types bug. Calling `$.ui.toast({text:'hi'})` compiles but silently arrives as `e.text === "[object Object]"` — no throw. |
| 6 | No `WebAssembly` global in the hooks sandbox | Sep 15 (nateschickler0, maddiedreese) | **LIVE, confirmed** | Grep of 2.1.273 declarations: 0 hits for `WebAssembly`. A WASM engine must run out-of-process, reached via `$.http.fetch`. |
| 7 | (new, not a thread claim) JSX in a `.ts` module | — | **LIVE trap** | A `.ts` module using JSX fails `claude plugin validate` at load ("does not parse"). Must be `.tsx`. Built-in mods are `.ts` only because none of them writes JSX. |
| 8 | Hook timeout/throw is fail-open; engine skips the hook and dispatches as if unregistered — a 10,000ms-stalled `PreToolUse`-style guard let a gated Bash call complete | 2.1.263 (Spencer-Morley, 42tahara) | **UNVERIFIED, design in flux** | `poteat` proposed `.catch(($,e,err)=>...)` semantics on `on(...)` Sep 8 as a fix (§3); not retested on 2.1.273 here. Treat as still-open until reverified. |
| 9 | Capability withholding at plugin load is fail-**closed** (opposite polarity from runtime fail-open) | 2.1.263 (Spencer-Morley) | UNVERIFIED | No 2.1.273 retest in this corpus. |
| 10 | `hooks.json` silently accepts unknown keys (e.g. a bogus `"timeout"`) with no warning and no effect | 2.1.263/2.1.250 (gbrussich52, yonatangross) | UNVERIFIED | Presumed still live; not retested. |
| 11 | `claude plugin validate` checks shape/spelling only — `banana.PreToolUse` and a nonexistent `$` noun both "pass with warnings," then throw and fail open at runtime | 2.1.263 (autorundev) | UNVERIFIED | 2.1.273 confirms `validate` does static inventory of hooks/`$` calls, but this corpus does not retest depth of runtime-semantic checking. |
| 12 | "Watcher fires on being discussed" — content-matching guards trigger on conversation merely mentioning the watched thing, independently rediscovered 8+ times | multiple | UNVERIFIED | Presumed still live; classic quirk, not addressed by function-hooks changes. |
| 13 | Exec-bit fail-open: a guard script's mode reverting to 644 produces `exit 126` (not `exit 2`), treated as non-blocking, guard silently stops working | unspecified (koko1000ban) | UNVERIFIED | Applies to classic/command hooks; not retested. |
| 14 | `Stop` hook exit-code polarity is inverted vs `PreToolUse` (exit 2 on `Stop` = "don't stop") — a uniform fail-closed wrapper is actively dangerous there | unspecified (koko1000ban, frsorrentino) | UNVERIFIED | Not retested; treat as still live given no ship note. |
| 15 | `hookSpecificOutput.updatedInput` is a full replacement, not a patch — omitting a sibling field silently drops it | pre-function-hooks era (deafsquad) | UNVERIFIED | Classic-hook behavior; likely unchanged. |
| 16 | Background/headless subagents largely invisible to hooks: `agent.spawn` never fires, `$.session.*` reads as parent, no dispatch identity | unspecified (jdainsworthsnb); contradicted same-day by fragmentsstudio vs. poteat's "works in our internal prototype" | UNVERIFIED, unresolved in-thread | `poteat`'s prototype claim and fragmentsstudio's shipped-build measurement were never reconciled in the source thread. |
| 17 | Bash command-string guards are blind to variable expansion and in-script file ops (e.g. Python `open(path,"w")` invisible to a regex guard) | unspecified (xtrianta-gif, cadoganp20, sidhartha1s) | UNVERIFIED | Structural limitation of string-matching guards; not a version-specific bug. |
| 18 | `$.model.complete` has no `effort`/`timeoutMs`, `maxTokens` defaults to 256, hard 8,192-token ceiling, `prompt` is a single string only | 2.1.272 (Marat) | UNVERIFIED | Not retested on 2.1.273 in this corpus. |
| 19 | `turn.step` can replace a model request but not forward one (no system blocks/tool defs/cache breakpoints exposed) | 2.1.272 (Marat, corrected point 5 after retraction) | UNVERIFIED | Not retested. |
| 20 | No event reaches the prompt composer while the user is typing (only submitted prompts) | v268 declarations (wkasekende) | UNVERIFIED, believed still true | Matches 2.1.273's documented "two event families" (engine + op); no composer-keystroke family exists in either. See §7. |
| 21 | `ui.scroll` declared in 2.1.271 types but engine refuses registration on it at load | 2.1.271 (mpolatcan) | UNVERIFIED | Not retested. |
| 22 | Mods in `~/.claude/skills/` do not hot-reload; `--plugin-dir` does | 2.1.270 (lperezmo) | UNVERIFIED, `--plugin-dir` side confirmed | 2.1.273 dev workflow in this corpus only exercises `--plugin-dir`, confirmed hot-reload-capable there; `~/.claude/skills/` path not retested. |
| 23 | Plugin integrity / `plugin.register` allowlisting is by declared name, not by bytes (cache dir is writable and unrechecked) | Sep 8 (VanguardBit, filed as #93426) | UNVERIFIED | Not retested. |

## 3. Design rationale (Anthropic / `poteat`)

**Continuation ("onion") model.** Express/Koa-style: the plugin registered first wraps everything below it and alone controls veto/rewrite. "The Koa-inspired model means that the plugin registered first 'owns' all subsequent hooks on a given event instance... it's an 'onion model.'" Registration order is *configured* order, not install time or wall-clock order.

**Hook ordering / topo-sort.** Plugin-declared dependencies drive order within a tier (a topo-sort honoring both the user's stated order and plugins' declared order); a plugin cannot reorder itself. A five-tier skip mechanism, `next.to(e, tier)`, lets a `prepend` (org-managed) plugin jump straight to `"builtin"` or `"core"`, skipping `user`/`append` tiers; when tiers disagree the engine takes the lowest common tier. Tiers: `[prepend] [user] [append] [builtin] [core]`.

**Concurrency by not awaiting `next`.** "You can run function hooks concurrently today by not calling `await` on `next`. If you kick off `next` early and then do your work, essentially all function hooks are running concurrently." Only work that must transform the return value forces an `await`. Dispatch is literally `reduceRight` with a target p99 of ~50μs/hook (dispatch overhead only, not hook work), in-process on Bun.

**`tool.check` vs `tool.call` for guards.** `tool.call`'s core *is* the act of invoking the tool — a guard hooking it cannot meaningfully run concurrently with the call it's supposed to gate. `tool.check` exists precisely so a guard can start `next(e)` early and race its own async check against it: `on('tool.check', async ($,e,next) => { const beneath = next(e); if (await isDestructive(e.input)) return {decision:'deny', reason:'...'}; return beneath })`. (Per §2 row 1, `tool.check` has since shipped.)

**Fail-open/fail-closed — the policy visibly changed mid-thread.** Sep 3, initial framing was skip-and-route-around ("the engine just dispatches again... as if no plugins were registered at all"). Same day, converged toward catch-log-route-around after deafsquad's critique. By Sep 5, fixed to exactly three skip triggers — throw, timeout, wrong data shape — with `poteat` explicitly declining a declared per-hook `failMode`: "You can always just wrap your hook in a try-catch... I'm leaning against some separate declaration re throw behavior." By Sep 8, under pressure from guard authors reporting *measured* fail-open on real tool execution, `poteat` reversed and proposed `.catch(...)` semantics on `on(...)` so an author can opt into fail-closed per hook. Net: as of the thread's close, fail-open-by-default was still the shipped behavior, with a declared-catch escape hatch proposed but not confirmed shipped.

**`tool.call` responsibility model.** Denying a `tool.call` is not automatic — not calling `next(e)` is what stops the tool. The return value is only what the model is *told* happened; the engine can't independently verify ground truth, since a hook can reify its own side effects (e.g. proxy a `Read` through `$.http`). "Our logic for 'did the chain say it denied it or not' is merely `const approved = result.deny === undefined`." MCP tool calls route through the same `tool.call` hook as native tools.

## 4. Retractions

At least 11 claims in the thread were retracted or corrected by their own authors after re-measurement — rule: **verify against your own version before trusting a thread claim**, including this document's unverified rows.

- **gbrussich52** withdrew a "model routes around an empty `{deny:""}` refusal" claim after a 30-run re-test on 2.1.263 reproduced it 0/30, versus 2/4 originally claimed on 2.1.261: "I withdraw the measurement as evidence for it."
- **yourstrulyeden** fully retracted claimed `additionalContext` truncation caps (8,000 chars / 200 lines) after reproducing the opposite: "I read those constants out of the binary and reported them as behaviour. They do not act on this path."
- **Marat** self-retracted mid-comment that "a mod cannot see the session's own model request" — `turn.step` is exactly that hook; the claim was rewritten in place rather than left standing.
- **frsorrentino** retracted "the typings are not there yet" after being shown `/plugin-types`, which this document's §1 and the 2.1.273 verification confirm is the real (if undocumented) entry point.

## 5. What already exists

| Name | Repo | What it does | Uses |
|---|---|---|---|
| cc-arcade | sezaakgun/cc-arcade | 9 games + a pet above the prompt | `ui.render(AbovePrompt)`, `tool.call` unmatched, `$.clock` |
| Mindful-Claude | halluton/Mindful-Claude | Breathing exercises drawn above the prompt while a turn runs | `ui.render(AbovePrompt,Spinner)`, `command.register` |
| cc-storytime | maddiedreese/cc-storytime | On-device 260K-param transformer writes a live story above the prompt | `tool.call`, `ui.render`, no WASM (hand-ported) |
| flowpane | mpolatcan/flowpane | Live graph of a running Workflow-tool run in a side pane | `ui.render(Pane)`, `$.ui.blit/Raster`, `turn.step` |
| context-lens / quota-meter / token-ledger / budget-guard | Arunjay4213/claude-mods | Context/usage/cost dashboards + a spend guard | `$.session.usage()`, `$.store`, `tool.call`, `prompt.submit` |
| awesome-claude-code-mods | karanb192/awesome-claude-code-mods | Nightly scanner: clones candidates, runs `claude plugin validate`, publishes a capability-footprint table | subprocess over `claude plugin validate` |
| cctop | tomstagl/cctop | btop-style dashboard: context, cost, cache-hit, latency | `compaction`, `tool.call` unmatched |
| claude-agent-flow | Charlie0113-T/claude-agent-flow | Live subagent/teammate tree beside the transcript | subagent spawns, `tool.call` unmatched |
| claude-master | frsorrentino/claude-master | Orchestrates up to 8 parallel sessions + Wear OS companion | `turn.start/complete`, `tool.call`, `$.session.usage()` |
| drawer | Sureffi/drawer | Renders fenced graphviz blocks as terminal images (kitty/ghostty) | `ui.render(AssistantMessage)` |
| Katzensteg plugin | rjwittams/katzensteg | Embeds SDL games in the terminal via kitty graphics | `$.process.run`, raw tty writes |
| PromptSign | VanguardBit/PromptSign | Signing/verification spec for skills/agents/CLAUDE.md | classic `SessionStart`/`PreToolUse` (function-hook port pending) |
| lcm / kindex-modern / segmem / commonplace | 4 separate repos | Four non-interoperating memory/context systems | system prompt, every prompt/tool call |
| **diff** (built-in) | anthropics/claude-code/mods/diff | `/diff` pane, refreshed live | `session.start`, `ui.render`, `tool.call`, `$.fs`, `$.process.run` |
| **sec-default** (built-in) | anthropics/claude-code/mods/sec-default | Org security default, seated outermost on managed Team/Enterprise only | classic hooks, system prompt, every skill |
| **telemetry** (built-in) | anthropics/claude-code/mods/telemetry | Adds `$.telemetry` for plugin analytics | `engine.create` fold |

**Capability-footprint stats** (`awesome-claude-code-mods`, scanned 2026-09-15 against 2.1.272): 31 cataloged mods in 92 candidate repos. 14 run host processes, 4 write files, 7 read files, 4 reach the network, 13 see every tool call unfiltered, 11 see every prompt, 1 fails `claude plugin validate`. Reach tiers: L0 draws/remembers 12 · L1 reads 2 · L2 writes/runs/drives Claude 13 · L3 network 4. The three Anthropic built-ins are listed separately as "Built into Claude Code" and excluded from the 31/92 totals.

## 6. Distribution

Mods use the existing plugin/marketplace machinery — nothing new was added for mods specifically. Two-step pattern used by every real mod in the corpus:

1. `claude plugin marketplace add <owner/repo>` (or `/plugin marketplace add <owner/repo>`) — registers a GitHub repo as a marketplace; several mods ship a `marketplace.json` whose `source` is `"./"`, making the repo its own marketplace.
2. `claude plugin install <name>@<marketplace>` (or `/plugin install <name>@<marketplace>`).

`CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` must also be set — installing without it leaves the plugin present but inert (§1). Setting the flag globally loads the hooks module of *every* installed plugin that ships one, which is the mechanism the nightly scanner's discovery depends on. For development, `claude --plugin-dir <path>` is the one load path confirmed hot-reload-capable on save.

Anthropic's own three built-in mods (diff, sec-default, telemetry) ship **inside the binary** and load on every machine with function hooks on — a deliberate channel entirely separate from the plugin-marketplace path, and they are in **no marketplace at all**.

Per Anthropic's published plugin docs (outside this thread's corpus): two official marketplaces exist — **`claude-plugins-official`** (curated by Anthropic, no application process) and **`claude-community`** (third-party submissions after review, added with `claude plugin marketplace add anthropics/claude-plugins-community`). Submission is via platform.claude.com/plugins/submit. Neither name appears anywhere in the #91870 thread or in any cataloged mod's docs — treat any thread-sourced detail about them as absent, not confirmed, from that corpus specifically.

## 7. Idea space

**Crowded — games above the prompt (6+ independent builds).** cc-arcade (9 games + pet), claude-games (dodge/Breakout/dino/shooter), cc-pokedex, the cc-arcade Doom PR, Katzensteg's SDL embedding, plus ambient variants (Mindful-Claude, cc-storytime) that explicitly cite cc-arcade as prior art. Empty sub-niche: no mod draws an actual raster *image* on terminal — only the character-cell `Raster` grid or a kitty-graphics side channel exist, because there's no first-class image element on that surface.

**Crowded — observability/cost dashboards.** cctop, the claude-mods trackers, agent-flow, flowpane, autotel (OpenTelemetry-for-mods) all solve "surface a figure the engine already knows." Proposed but unbuilt: a multi-session cockpit aggregating many concurrent sessions via the `*` wildcard event bus.

**Crowded and most bug-ridden — security/guards/redaction.** secret-redactor, honmoon-redact, kb-settings-guard, claude-doctor, plugin-health, PromptSign, plus real production ports (djscruggs's fail-closed classifier, Spencer-Morley's Anchorwatch) all hit the same two open walls: fail-open on timeout (§2 row 8) and no `realpath` (§2 row 4). **No shipped guard in this corpus is both fail-closed-on-timeout and symlink-safe** — this is the clearest open niche in the most-attempted category.

**Empty — composer/editor integration.** No event fires on live prompt-box keystrokes; only a submitted prompt is visible (§2 row 20). OpenCues is the one real attempt and its own gap analysis is why this niche stays empty — it proposes an unimplemented `prompt.edit` event to do what it wants.

**Crowded, non-consolidating — memory/context.** lcm, kindex-modern, segmem, commonplace: four separate approaches to durable memory, none referencing or building on another.
