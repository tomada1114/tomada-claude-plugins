<!-- platform-annex -->

# Permissions and Sandbox

Three orthogonal controls govern what Codex CLI does without stopping to ask.
`sandbox_mode` (or a permission profile) decides **what** Codex can touch —
which paths are writable, whether the network is reachable — regardless of
whether it asks first. `approval_policy` decides **when** it asks, given that
boundary. Rules (`.rules` / `prefix_rule`, see `references/rules-execpolicy.md`) carve out
per-command exceptions to the asking, without moving the sandbox boundary
itself. Fix the boundary first, then tune the asking, then add rule exceptions
only for specific commands you've decided are safe to skip.

## sandbox_mode

```
key: "sandbox_mode"
type: "read-only | workspace-write | danger-full-access"
description: "Sandbox policy for filesystem and network access during command execution."
```

Three values only — no fourth option, no fixed default. The effective value is
context-dependent:

- A version-controlled (git) folder resolves to `workspace-write` paired with
  `on-request` approvals under the **Auto** preset.
- A non-version-controlled or untrusted folder resolves to `read-only` until
  you explicitly trust it, via the onboarding prompt or `/permissions`.
- The shipped config sample (`docs/config-file/config-sample`) shows
  `sandbox_mode = "read-only"`.

```toml
# ~/.codex/config.toml or <repo>/.codex/config.toml
sandbox_mode = "workspace-write"
```

One-shot override: `codex --sandbox workspace-write` (`-s`). Dotted-path form:
`-c sandbox_mode=workspace-write`.

### [sandbox_workspace_write] — exactly 4 keys

```toml
[sandbox_workspace_write]
writable_roots = ["/path/one", "/path/two"]   # array<string>: extra writable roots
network_access = false                        # bool: outbound network in the sandbox
exclude_tmpdir_env_var = false                # bool: exclude $TMPDIR from writable roots
exclude_slash_tmp = false                     # bool: exclude /tmp from writable roots
```

Only `workspace-write` reads this table; it has no effect under `read-only` or
`danger-full-access`. Dotted-path override: `-c sandbox_workspace_write.network_access=true`.

There is no flattened key `sandbox_workspace_write_writable_roots` — that name
does not exist in any Codex version. Use the `[sandbox_workspace_write]`
sub-table's `writable_roots`, or `-c sandbox_workspace_write.writable_roots='[...]'`.

### Protected paths inside a writable root

Even under `workspace-write`, every writable root keeps three paths read-only,
recursively:

- `<writable_root>/.git` — protected whether it's a real directory or a
  pointer file (`gitdir: ...`); when it's a pointer, the resolved Git
  directory it points to is protected too.
- `<writable_root>/.agents` — protected when it exists as a directory.
- `<writable_root>/.codex` — protected when it exists as a directory.

This is why `git commit` still prompts for approval under `workspace-write`
even in a fully trusted project — Codex is not allowed to write `.git`
directly, so committing has to leave the sandbox. Neither `--add-dir` nor
adding more `writable_roots` fixes this: `.git` stays protected inside *every*
writable root, added ones included. The documented fix is a Rules entry that
allows `git commit` (and related git subcommands) to run outside the sandbox
without prompting — see `references/rules-execpolicy.md` for the mechanism and the
canonical `git` allow-rule. Reaching for `danger-full-access` just to unblock
`git commit` is unnecessary and overbroad.

This paragraph is the canonical explanation of the `.git`/`.codex`/`.agents`
protected-path behavior — other reference files in this skill should link here
rather than re-describing it.

## approval_policy

```
key: "approval_policy"
type: "on-request | never | { granular = { sandbox_approval = bool, rules = bool, mcp_elicitations = bool, request_permissions = bool, skill_approval = bool } }"
description: "Controls when Codex pauses for approval before executing commands."
```

- **`on-request`** — the model decides when to ask. This is the interactive
  default and what the **Auto** preset uses.
- **`never`** — never ask; a command failure is returned straight to the model
  to work around instead of escalating to a human. Use for non-interactive/CI
  runs.
- **`{ granular = {...} }`** — five independent booleans
  (`sandbox_approval`, `rules`, `mcp_elicitations`, `request_permissions`,
  `skill_approval`) let you auto-proceed on some prompt categories while
  staying interactive on others.
- **`on-failure`** — deprecated; do not configure it going forward.
- `untrusted` is **retired and unsupported** as a literal value of
  `approval_policy`. Setting it can prevent Codex or ChatGPT Work from
  starting. It survives only as a `trust_level` concept (see below), never as
  something you assign to `approval_policy` directly.

```toml
approval_policy = "on-request"
```

CLI: `-a, --ask-for-approval <on-request|never>` (the CLI surface exposes only
these two values — not `on-failure`, not `untrusted`).

### Replacing the old "untrusted" intent

To get the old strict-approval behavior, mark the project untrusted instead of
setting `approval_policy` at all — do this in **user-level**
`~/.codex/config.toml`:

```toml
[projects."/path/to/project"]
trust_level = "untrusted"
```

Commands then require approval unless an execution-policy rule allows them.
This also disables project-local configuration for that project.

### approvals_reviewer

```
key: "approvals_reviewer"
type: "user | auto_review"
description: "Who reviews eligible approval prompts under on-request or
  granular approval policies. Defaults to user; auto_review uses the reviewer
  subagent. Doesn't change sandboxing or what's already allowed inside the sandbox."
```

Default: `user`. Per-app overrides exist: `apps._default.approvals_reviewer`,
`apps.<id>.approvals_reviewer`. Related: `auto_review.policy` (local Markdown
text steering the reviewer subagent's judgment), and the admin allowlist key
`allowed_approvals_reviewers` (see `requirements.toml` below).

`workspace-write` + `on-request` + `approvals_reviewer = "auto_review"` is the
closest Codex equivalent to an "auto mode" that still keeps a human in the
loop for genuinely risky escalations: the sandbox boundary is unchanged, but
routine on-request prompts route to the reviewer subagent instead of
interrupting you.

```toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"
approvals_reviewer = "auto_review"
```

Or per-invocation: `codex -c approvals_reviewer=auto_review`, or (non-interactive)
`codex exec --approve-for-me`.

## Permission profiles (Beta) — the forward-looking system

> Beta. Permission profiles are under active development and may change.

`default_permissions` + `[permissions.<name>]` is documented as replacing the
`sandbox_mode` + `[sandbox_workspace_write]` combination. Docs are explicit:
*"Don't combine with `sandbox_mode` or `[sandbox_workspace_write]`."* and
*"Permission profiles replace the older combination of `sandbox_mode` and
`sandbox_workspace_write` … Use one system or the other for a session, not
both."* `sandbox_mode` remains fully supported and is simpler for ordinary
local use; permission profiles add per-path and per-domain granularity that
matters more for teams, CI, and anything beyond "workspace read/write,
network on/off." Pick one system per session — never mix them.

### Built-in profiles

- `:read-only` — local command execution stays read-only.
- `:workspace` — writes allowed inside active workspace roots and system temp
  directories.
- `:danger-full-access` — removes local sandbox restrictions; use only when
  broad access is genuinely intended.

### Selection

```
key: "default_permissions"
description: "Name of the default permissions profile to apply to sandboxed
  tool calls. Built-ins are :read-only, :workspace, and :danger-full-access;
  custom profile names require matching [permissions.<name>] tables. Don't
  combine with sandbox_mode or [sandbox_workspace_write]."
```

```toml
default_permissions = ":workspace"
```

### Custom profile shape

```toml
default_permissions = "project-edit"

[permissions.project-edit]
description = "Workspace editing with a limited network allowlist"
extends = ":workspace"

[permissions.project-edit.filesystem.":workspace_roots"]
"." = "write"
"**/*.env" = "deny"
"**/secrets.*" = "deny"

[permissions.project-edit.network]
enabled = true
mode = "limited"

[permissions.project-edit.network.domains]
"github.com" = "allow"
"*.github.com" = "allow"
"api.openai.com" = "allow"
```

Key namespace:

- `permissions.<name>.description` — free text.
- `permissions.<name>.extends` — another named profile, `:read-only`, or
  `:workspace`. `:danger-full-access` cannot be extended, unknown parents are
  rejected, and cycles are rejected.
- `permissions.<name>.workspace_roots.<path>` — bool.
- `permissions.<name>.filesystem` — per-path/glob values of `"read"`,
  `"write"`, or `"deny"`; plus `glob_scan_max_depth`, and the
  `":workspace_roots"` sub-table for globs relative to workspace roots.
- `permissions.<name>.network.*` — `enabled` (bool), `mode`
  (`limited|full`), `domains.<pattern> = "allow"|"deny"`; lower-priority
  proxy/socket keys also exist but are rarely touched directly.

Filesystem special tokens: `:root`, `:minimal`, `:workspace_roots`, `:tmpdir`,
`:slash_tmp`.

`filesystem` itself is a reserved profile name — a custom profile cannot be
named `filesystem`, and no custom profile name may start with `:`.

A **bare** `[permissions.filesystem]` table (a deny-read list, not a named
profile) exists only in the admin `requirements.toml`, never in a
user/project `config.toml`:

```toml
# requirements.toml only
[permissions.filesystem]
deny_read = ["/**/*.env", "~/.ssh"]
```

In `config.toml`, the equivalent per-profile shape is always
`[permissions.<name>.filesystem]` — nested under a profile name, not bare.

### codex sandbox / -P flag

```bash
codex sandbox -P project-edit
codex sandbox --permission-profile project-edit
```

`-P, --permission-profile <NAME>` applies a named permission profile from the
active config stack to the `codex sandbox` invocation.

### What the desktop app's permission picker actually lists

The Codex desktop app's "How should ChatGPT actions be approved?" menu is
built from three sources:

1. the built-in modes — **Ask for approval**, **Approve for me**, **Full
   access**;
2. every named `[permissions.<name>]` profile in `config.toml` (this is why
   a custom `project-edit` shows up there by name);
3. **Custom (config.toml)** — "uses permissions defined in config.toml",
   i.e. whatever `default_permissions` + `approval_policy` say.

A `$CODEX_HOME/<name>.config.toml` profile *file* (the `-p/--profile`
layer) does **not** appear in that menu at all — it is CLI-only. Someone
who builds a "full access" profile file and then goes looking for it in the
app will not find it.

Consequence worth stating up front: picking **Full access** in that menu
sets `approval_policy = "never"` along with the sandbox. Under `never`, a
Rules `prompt` entry has nobody to ask, so it **fails closed into a hard
block** — "ask me before dangerous commands" quietly becomes "refuse
dangerous commands." To run with the sandbox off *and* keep prompts as real
prompts, put it in `config.toml` and pick **Custom (config.toml)**:

```toml
default_permissions = ":danger-full-access"   # sandbox off
approval_policy = "on-request"                # prompts still prompt
```

### `":root" = "write"` — the fix for "Codex can't touch git metadata"

`:workspace` (and `workspace-write`) keeps `.git` recursively read-only
inside every writable root, so a profile that merely `extends = ":workspace"`
leaves `git commit`, `rebase`, and `pre-commit install` failing. Granting
`":root" = "write"` in the profile's `filesystem` table lifts that:

```toml
[permissions.wide.filesystem]
":root" = "write"
"/Users/me/.aws/**" = "deny"
```

Measured on 0.153.4: `.git` writable, `git status`/`commit` fine, `gh`
fine, and paths outside the workspace writable — while the listed denies
still hold. This is a genuine alternative to turning the sandbox off for
someone whose only complaint is that git doesn't work.

### Filesystem-table path syntax (two rules that bite)

- Every key in a bare `[permissions.<name>.filesystem]` table must be
  **absolute**, start with `~/`, or start with `:` — a relative glob like
  `"**/*.env"` is rejected (`must be absolute, use `~/...`, or start with
  `:``). Relative globs belong under the `":workspace_roots"` sub-table.
  For "anywhere on disk," write `"/**/.env"`.
- A glob key that does not end in `/**` supports **`deny` only** — `read`
  and `write` need an exact path or a trailing `/**` subtree. So you cannot
  carve a readable exception out of a deny glob (`"/**/.env.*" = "deny"`
  cannot be un-denied for `.env.example`); enumerate the secret variants
  instead of denying the whole family.

### Denying SSH private keys without breaking `git push`

`"~/.ssh/id_*" = "deny"` also denies the matching `.pub` files, and ssh
needs the public half to select an agent identity — the result is
`Permission denied (publickey)` even with a loaded `ssh-agent`. Deny the
private keys by **exact path** instead and leave `~/.ssh/**` readable:

```toml
"/Users/me/.ssh/**" = "read"
"/Users/me/.ssh/id_ed25519" = "deny"
```

Measured: `git ls-remote` over SSH succeeds via the agent while
`head -c 1 ~/.ssh/id_ed25519` is denied. The cost is that a newly created
key has to be added by hand — no glob can express it.

### `approvals_reviewer` has a third value

`ApprovalsReviewer` is `user | auto_review | guardian_subagent`. Guardian
is a model-based risk classifier ("judging one planned coding-agent action
… assess the exact action's intrinsic risk and whether the transcript
authorizes its target and side effects"), with trigger sources including
`command_execution`, `sandbox_denial`, `network_policy_denial` and
`execve_intercept`. `guardian_approval` ships as a stable, default-on
feature flag; `guardianv2` is still under development. It is the only layer
in Codex that judges an action by **meaning** rather than by argv shape —
relevant whenever someone asks how to catch a destructive operation whose
spelling no `prefix_rule` pattern can anticipate. Whether it fires under
`approval_policy = "never"` has not been verified here; don't assert that it
does.

## /permissions and other in-session controls

There is no `/approvals` command — it's `/permissions`.

```
/permissions — "Set what Codex can do without asking first."
  Relax or tighten approval requirements mid-session, such as switching
  between Auto and Read Only.
```

Type `/permissions`, press Enter, select a preset. Confirmed presets on the
CLI: **Auto**, **Read Only**. The desktop/IDE surface additionally shows "Ask
for approval," "Approve for me," "Full access," plus any named permission
profiles you've configured.

Documented preset meaning:

- **Auto** = workspace write + on-request approvals (`sandbox_mode =
  "workspace-write"`, `approval_policy = "on-request"`).
- **Full access** = `sandbox_mode = "danger-full-access"` together with
  `approval_policy = "never"`.

No finer-grained mapping is published beyond that — don't invent one.

`/approve` is a different command: it approves one retry of a recent
auto-review denial. Do not conflate it with `/permissions`.

Other relevant slash commands: `/status` (active model, approval policy,
writable roots, remaining context), `/init` (scaffold AGENTS.md), `/review`
(non-interactive code review), `/statusline`, `/model`, `/hooks`,
`/experimental`, `/compact` (compresses context — a tradeoff, not free),
`/plan <prompt>` (enter Plan mode; `Shift+Tab` also cycles collaboration mode).

## CLI flags

| Flag | Values / type | Notes |
|---|---|---|
| `-s, --sandbox` | `read-only \| workspace-write \| danger-full-access` | one-shot sandbox override |
| `-a, --ask-for-approval` | `on-request \| never` | CLI only exposes these two |
| `--dangerously-bypass-approvals-and-sandbox` (alias `--yolo`) | bool | skips all confirmation prompts and runs without sandboxing; intended only for environments that are externally sandboxed — not for normal use |
| `-p, --profile <NAME>` | string | layers `$CODEX_HOME/<name>.config.toml` on top of base user config |
| `-c, --config <key=value>` | dotted path, TOML-parsed value | e.g. `-c approvals_reviewer=auto_review`, `-c sandbox_workspace_write.network_access=true` |
| `--add-dir <DIR>` | path, repeatable | additional writable directory alongside the primary workspace; prefer over widening the whole sandbox — does **not** unprotect `.git` inside any writable root |
| `-C, --cd <DIR>` | path | working root for the agent |
| `--enable <FEATURE>` / `--disable <FEATURE>` | feature name, repeatable | shorthand for `-c features.<name>=true/false` |
| `--strict-config` | bool | error on unrecognized `config.toml` fields |
| `-P, --permission-profile <NAME>` | string | on `codex sandbox`: apply a named permission profile |
| `--ignore-rules` | bool | on `codex exec`: skip user/project `.rules` for this run |
| `--ignore-user-config` | bool | on `codex exec`: skip `$CODEX_HOME/config.toml` |
| `--approve-for-me` | bool | on `codex exec`: route approval requests through automatic review using the workspace-write sandbox — non-interactive analogue of `auto_review` |
| `--search` | bool | enable live web_search tool, no per-call approval |

`--full-auto` is deprecated — it exists only on `codex exec`, prints a
warning when used, and Codex prefers `--sandbox workspace-write` instead.
Mention it only as retired, never as a live recommendation.

These flags compose into five named, scenario-driven postures (everyday
coding, read-only exploration, auto-review, unattended CI, full access) with
full rationale for each in `references/autonomy-recipes.md` — read that file for "which
one should I use," this section for the raw flag reference.

`codex doctor` is the health-check command; `codex features list/enable/disable`
inspects and toggles feature flags. Both covered in depth, with output-field
meaning and symptom-driven usage, in `references/diagnostics.md`.

## requirements.toml constraints on this layer

An admin-managed `requirements.toml` can constrain the range of
`sandbox_mode`/`approval_policy`/`approvals_reviewer`/permission-profile
values a user or project may set — it does not itself set values, and a
conflicting local value falls back to a compatible one with a notification
rather than a hard failure. Full mechanics (locations, precedence, the
`allowed_*` key list, the ≥0.138.0 version gate for permission-profile
allowlisting, and the `untrusted`-survives-as-a-trust-concept note) are
covered once, in `references/config-files-and-precedence.md` — read that file rather
than this section for the details.

## Related references

- `references/config-files-and-precedence.md` — the full `config.toml` precedence chain,
  the project trust gate, current profile-file mechanics, and
  `requirements.toml` in depth.
- `references/rules-execpolicy.md` — `.rules` / `prefix_rule()` mechanics and the
  headline "let git write" recipe this file only summarizes.
- `references/autonomy-recipes.md` — the preset combinations above, composed into named,
  scenario-driven recipes with full rationale.
