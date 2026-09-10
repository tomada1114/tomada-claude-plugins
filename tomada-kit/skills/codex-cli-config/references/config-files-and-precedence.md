<!-- platform-annex -->

# Config Files and Precedence

Facts current as of Codex CLI 0.153.4 / docs current as of 2026-09.

## Precedence chain

Codex resolves every config key by walking this chain, highest to lowest:

1. CLI flags and `-c`/`--config` overrides
2. Project config files: `.codex/config.toml`, discovered from the project root
   down to the current working directory (closest to cwd wins) — **trusted
   projects only**
3. Profile file selected with `--profile <name>` / `-p <name>`
4. User config: `~/.codex/config.toml`
5. System config (if present): `/etc/codex/config.toml` on Unix
6. Built-in defaults

Project beats profile beats user beats system. Within nested project configs,
the file nearest the current working directory wins per key — not "last file
loaded overall," but per matching key across the loaded set.

### Nearest-project-config-wins example

```text
my-project/
├── .codex/
│   └── config.toml
└── packages/
    └── api/
        └── .codex/
            └── config.toml
```

Starting Codex inside `my-project/packages/api` loads the root
`.codex/config.toml` first, then `packages/api/.codex/config.toml`. Any key
defined in both resolves to the `packages/api` value — the file closer to the
working directory, not the project root.

For sandbox and permission *values* referenced anywhere in this chain (
`sandbox_mode`, `[sandbox_workspace_write]`, `default_permissions`,
`[permissions.<name>]`), see `references/permissions-and-sandbox.md`. This file covers
only where those values are read from and in what order.

## The project trust gate

Project-local `.codex/config.toml` only loads for **trusted** projects.
Trust is recorded in **user-level** `~/.codex/config.toml`, never in the
project itself:

```toml
[projects."/absolute/path/to/project"]
trust_level = "trusted"   # or "untrusted"
```

Config key reference:

```
key: "projects.<path>.trust_level"
description: 'Mark a project or worktree as trusted or untrusted ("trusted" |
  "untrusted"). Untrusted projects skip project-scoped `.codex/` layers,
  including project-local config, hooks, and rules.'
```

An **untrusted** project skips project-scoped `.codex/` layers entirely —
project-local config, hooks, and rules. User and system config still load,
including user/global hooks and rules under `~/.codex/`.

Trust is granted interactively: the first launch inside a new directory shows
a trust prompt ("Yes, proceed" / "No, quit" or similar); accepting writes the
`trust_level = "trusted"` entry shown above. Trust can also be revisited later
via `/permissions`. Do not mark a shared or unreviewed repository trusted
without first checking its contents — a project's own `.codex/` directory,
once trusted, can add rules, hooks, and config the user did not write.

## Keys ignored in project-local config

These keys have no effect when set in a project's `.codex/config.toml` — they
only take effect from user or system config:

```
openai_base_url
chatgpt_base_url
apps_mcp_product_sku
model_provider
model_providers
notify
profile
profiles
experimental_realtime_ws_base_url
otel
```

A project cannot redirect the API endpoint, switch model providers, or select
a profile on the user's behalf — those stay under user/system control.

### Project root detection

Codex walks up from the current working directory looking for a marker
directory — `.git` by default — to find the project root; discovery then
walks back down from that root to the cwd, loading `.codex/config.toml` at
each level (see precedence above). The marker set is configurable:

```toml
project_root_markers = [".git", ".hg", ".sl"]
```

An empty list disables the upward walk (Codex checks only the current
directory).

## Profile mechanism (current, since Codex 0.134.0)

**Removed**: `[profiles.<name>]` tables nested inside `config.toml`, and the
top-level `profile = "profile-name"` selector key. Verbatim from the docs:
*"In Codex 0.134.0 and later, `--profile` no longer reads
`[profiles.profile-name]` from `config.toml`, and the top-level
`profile = "profile-name"` selector is no longer supported."* If any material
you encounter shows that nested-table form, treat it as obsolete — do not use
it.

**Current shape**: a profile is a **separate file** at
`$CODEX_HOME/<name>.config.toml` (i.e. `~/.codex/<name>.config.toml` by
default), containing flat, top-level keys — the same key names as
`config.toml`, just not nested under any `[profiles.x]` table:

```toml
# ~/.codex/deep-review.config.toml
model = "gpt-5.6-terra"
model_reasoning_effort = "high"
approval_policy = "never"
sandbox_mode = "read-only"
```

Select it with:

```bash
codex --profile deep-review
codex exec --profile deep-review "review this diff"
```

`-p <name>` is the short form of `--profile <name>`. A profile file sits above
user config and below project `.codex/config.toml` and CLI flags in the
precedence chain — a project config key still beats a profile key for the same
name.

## requirements.toml — admin-managed constraint layer

`requirements.toml` is not a value-overriding config layer like the six above
— it is a **constraint** on the allowed range of values for those layers.
Verbatim: *"Higher-precedence layers override ordinary scalar and list values
from lower layers. Tables merge by key, while requirements such as rules,
hooks, and filesystem restrictions have field-specific composition
behavior."*

### Locations, lowest to highest precedence

1. System `requirements.toml` — `/etc/codex/requirements.toml` (Unix) or
   `%ProgramData%\OpenAI\Codex\requirements.toml` (Windows)
2. Enterprise-managed requirements delivered via a cloud config bundle
3. Legacy `managed_config.toml` fields, reinterpreted as requirements
4. macOS MDM (`com.openai.codex:requirements_toml_base64`)

### What it can constrain

Approval policy, approvals reviewer, automatic review policy, sandbox mode,
permission profiles, web search mode, managed hooks, which MCP servers users
can enable, which plugin marketplace sources users can add/install/refresh
from, plus feature flags via `[features]`. Any key the admin omits stays
unconstrained for the local client.

Keys worth knowing by name: `allowed_approval_policies`,
`allowed_approvals_reviewers`, `allowed_permission_profiles`,
`allowed_permission_profiles.<name>`, `default_permissions` (managed form),
`allowed_sandbox_modes`, `allow_managed_hooks_only`, `[rules] prefix_rules`,
`[permissions.filesystem] deny_read`. `[rules] prefix_rules` composition (its
different, TOML-based syntax and its prompt/forbidden-only restriction) is
covered in `references/rules-execpolicy.md`; `[permissions.filesystem]` is a
`requirements.toml`-only shape — it is not a valid table in a regular user or
project `config.toml` (that file only ever has
`[permissions.<name>.filesystem]` under a named profile — see
`references/permissions-and-sandbox.md`).

### Version gate

Managed permission-profile allowlisting (`allowed_permission_profiles` and a
managed `default_permissions`) requires Codex **≥0.138.0**. Codex 0.137.0 and
earlier silently ignore those keys — an admin targeting older clients must
still rely on `allowed_sandbox_modes`. For 0.138.0 and later, prefer
permission-profile constraints over `allowed_sandbox_modes`, which the docs
now describe as a legacy-deployment fallback.

### Conflict behavior

When a local config value conflicts with an enforced requirement, the local
client does not hard-fail — it falls back to a compatible value and notifies
the user. There is no separate "reject and refuse to start" mode described for
ordinary constraint conflicts.

### `untrusted` survives only as a trust-level concept

`allowed_approval_policies` may still list `untrusted` as an entry — that
refers to the stricter approval behavior Codex derives when a project's
`trust_level = "untrusted"` (see the trust gate above), not to a literal,
settable `approval_policy = "untrusted"` value. Setting
`approval_policy = "untrusted"` directly is not supported at any layer; see
`references/permissions-and-sandbox.md` for the retired-values list.

## Related references

- `references/permissions-and-sandbox.md` — `sandbox_mode`, `[sandbox_workspace_write]`,
  `approval_policy`, and permission profiles in depth. This file only
  documents where those values are *read from*, not what they mean.
- `references/rules-execpolicy.md` — `.rules` / `prefix_rule()` mechanics, including the
  admin `requirements.toml` `[rules] prefix_rules` syntax referenced above.
- `references/agents-md.md` — AGENTS.md discovery order and merge behavior; a separate
  chain from the `config.toml` precedence documented here.
