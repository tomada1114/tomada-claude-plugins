# The mod security model

How Claude Code constrains what a mod can do, and what an organization can
take away from one: the static side-effect scan behind `claude plugin validate`,
refusal at `plugin.register`, why event and method names must be spelled as
string literals, and `next.to(e, tier)` for keeping managed dispatches out of
reach of installed plugins.

Read references/api-model.md for the tiers and the execution model this builds on.

---

## Security model

### 7.1 Static side-effect inventory (`PluginRegisterUses`)

Before a module loads, the host statically scans its source (no mod code
runs) and reports exactly what it uses:

```ts
type PluginRegisterUses = {
  events: readonly string[];   // on(...) patterns, as written, registration order
  calls: readonly string[];    // "noun.method" spelled literally, sorted
  env?: { reads: readonly string[]; writes: readonly string[] };
};
```
Exact **because a module that spells `on`, `$`, or `$.env` other than
literally does not load** — why `$.env.get`/`$.env.set` require
string-literal `name` args (a dynamic name can't be scanned, so it's
refused), and generally why event/method names must be literals: the
scanner needs literal strings to build `events`/`calls`. `claude plugin
validate` prints this inventory without running the module.

### 7.2 `plugin.register`: gating another module before it loads

Fires once per hooks module about to join the chain, at load and reload;
`core` allows by default. A hook above it can refuse outright — return
`{refuse: reason}` and it never joins (no hook, no noun, no tool of it;
transcript names who refused). `PluginRegisterInput = {name, tier (never
'core'), root, version?, provenance, uses: PluginRegisterUses}`. Judges are
only plugins admitted *before* this one, plus the binary's own — judge by
`tier`/`uses`. E.g. `on("plugin.register", {tier:"user"}, () => ({refuse:"managed only"}))`.

**`next.to` for keeping org dispatches unreachable.** The shipped
`sec-default` mod (seated outermost, managed installs) uses `next.to(e,
'append')` on org-sensitive events (`classic.*`, `prompt.section`,
`prompt.context`, `skill.prompt`, `attribution.text`, `settings.read`) to
jump past every `user`-tier hook to the managed `append` tier — a
user-installed plugin never sees or rewrites those dispatches. Enforced
tier-structurally (no lower tier can undo it), not by convention. It also
denies ops by origin tier + policy (e.g. `tool.register`, checking
`next.origin.tier` against a managed MCP-allowlist via `$.settings.read`,
`{deny: reason}` — §2's uniform mechanism), and restores org tools a
lower-tier hook filtered from `tool.list` by reconciling
`next.to(e,'append')` against `next(e)`.

### 7.3 Observability: `next.trace`

Every `Next`/`GlobNext`/`StreamNext`/`StarNext` exposes `.trace: readonly
TraceEntry[]` — one entry per link beneath the caller: `index, plugin, tier,
event, outcome (§1), reason?, ms (own wall time, next() excluded), chunks?
(streaming only), received, returned`. Runtime audit trail: which plugins
ran, were skipped (and by whom, via `next.to`), or failed.

---

