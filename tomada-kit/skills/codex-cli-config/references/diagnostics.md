<!-- platform-annex -->

# Diagnostics

Tools for checking what Codex CLI is actually configured to do, plus a
symptom-to-cause table for the questions that come up most often. Use these
before changing config — most "it's not working" reports are a config layer
or protected-path behavior you can confirm directly, not a bug.

## `codex doctor`

Run `codex doctor` as the first step whenever behavior doesn't match what a
config file says it should. It reports, at minimum:

- **`sandbox`** — current filesystem restriction state (`read-only` /
  `workspace-write` / `danger-full-access`), network access state, and the
  active `approval_policy`.
- **`config`** — the loaded config path(s) actually in effect, and the MCP
  server count picked up from `[mcp_servers.*]`.
- **`mcp`** — per-server MCP status.
- **`auth`** — authentication state.
- Feature-flag overrides currently applied (anything set via `-c
  features.<name>=true/false` or `--enable`/`--disable`).

Reach for `codex doctor` when: a session appears more or less restricted than
you configured, an MCP server you defined doesn't show up, or you need to
confirm which config file actually won the precedence chain (see
`references/config-files-and-precedence.md`) without reasoning through the layers by
hand.

## `/status` (in-session)

Inside a running session, `/status` confirms:

- the active model
- the active `approval_policy`
- the current writable roots
- remaining context

Use it mid-session instead of guessing whether a `/permissions` change or a
`-c` override actually took effect — `/status` reflects the live session
state, not just what a config file declares.

## `codex debug prompt-input` — confirming a skill was actually loaded

```bash
codex debug prompt-input
```

Renders the exact model-visible prompt input as JSON, including the
`<skills_instructions>` block: a table of skill roots (`r0`, `r1`, …
resolved to absolute paths) and the `name: description (file: r<N>/…)` line
for every skill Codex actually put in the catalog for this session. Use this
— not just re-reading `SKILL.md` — when a skill isn't triggering and you
need to know whether the problem is discovery (the skill never made it into
the roots table at all) or triggering (it's listed, but the `description`
isn't matching the request). It also confirms whether a symlinked skill
directory resolved correctly (see `references/skills-and-plugins.md` for discovery
paths and symlink support).

## `codex execpolicy check` — testing Rules before you rely on them

```bash
codex execpolicy check --pretty --rules <path> -- <command>
```

- `--rules` / `-r` is repeatable — pass every `.rules` file (or layer) you
  want evaluated together, in the same combination Codex would load them in.
- The trailing `-- <command>` is the exact invocation to test, e.g.:

```bash
codex execpolicy check --pretty --rules ~/.codex/rules/default.rules -- git commit -m "wip"
```

- The output tells you the resulting decision (`allow` / `prompt` /
  `forbidden`) and which rule matched. Run this against any new
  `prefix_rule()` before trusting it in a live session — a rule with a typo'd
  `pattern`, or one that doesn't survive shell-splitting the way you expect,
  silently falls through to a different decision rather than erroring at
  runtime. See `references/rules-execpolicy.md` for how `prefix_rule()` and precedence
  work.

## `codex features list` / `enable` / `disable`

```bash
codex features list
codex features enable <name>
codex features disable <name>
```

`list` shows every feature flag and its current state. `enable`/`disable`
are shorthand for `-c features.<name>=true/false` — use them to flip a flag
for the current shell without hand-writing the dotted-path form, or to check
whether a flag you expect (from `requirements.toml` `[features]`, an admin
layer) is actually landing in the running session.

## Symptom → cause

| Symptom | Cause | Fix / detail lives in |
|---|---|---|
| `git commit` keeps asking for approval even under `workspace-write` | `.git` is a protected path inside every writable root — recursive read-only under the `workspace-write` sandbox policy, and `--add-dir` doesn't help (it only adds more roots, each with the same protection) | `references/permissions-and-sandbox.md` (protected paths) + `references/rules-execpolicy.md` (the `prefix_rule()` recipe to allow it explicitly) |
| My project's `.codex/config.toml` seems to be ignored | Either the project isn't trusted (untrusted projects skip project-scoped `.codex/` layers entirely — config, hooks, rules), or the specific key you set is one of the few always ignored in project-local config regardless of trust (`model_provider`, `notify`, `profile`, `otel`, and a handful of others) | `references/config-files-and-precedence.md` (trust gate + the ignored-keys list) |
| A Rules entry I wrote doesn't seem to take effect | A stricter rule in another layer wins (`forbidden` > `prompt` > `allow` across user/project/admin, no override); the command was shell-split differently than your `pattern` expects (redirection/substitution/env-assignment collapses it into one `["bash","-lc",...]` invocation); or — for a project-layer rule specifically — the project isn't trusted, so `<repo>/.codex/rules/*.rules` never loaded at all | `references/rules-execpolicy.md` + verify with `codex execpolicy check` above |
| `approval_policy = "untrusted"` / `--full-auto` stopped working | Both are retired/deprecated — `untrusted` is no longer a settable `approval_policy` value, `--full-auto` is a deprecated compat-only flag on `codex exec` | `references/permissions-and-sandbox.md` (current values and replacements) |
| `[profiles.x]` in `config.toml` is ignored | Removed since Codex 0.134.0 — `--profile` no longer reads `[profiles.<name>]` from `config.toml`, and `profile = "name"` at the top level is no longer supported | `references/config-files-and-precedence.md` (current profile-file shape) |
| AGENTS.md changes aren't taking effect | Either the combined instruction chain hit `project_doc_max_bytes` (32 KiB default) and later files got truncated, or the edited file is outside the discovery walk (wrong directory, or shadowed by an `AGENTS.override.md` in the same directory) | `references/agents-md.md` |
| A permission profile change seems to have no effect | Both `sandbox_mode`/`[sandbox_workspace_write]` and `default_permissions`/`[permissions.<name>]` are active at once — the docs say use one system per session, not both, and mixing them produces confusing results | `references/permissions-and-sandbox.md` |
| A skill isn't triggering, or doesn't seem to exist at all | Either it's outside every discovery path (or a broken/dangling symlink into one), or it loaded fine but its `description` doesn't match the request — run `codex debug prompt-input` to see the actual skill-roots table and catalog and tell the two apart | `references/skills-and-plugins.md` (discovery paths, symlink support) |

## Process gates vs. CLI diagnostics

The tools above answer "what is Codex technically permitted to do right
now" — sandbox, approvals, rules, config layering. They are a different
axis from a team's quality gates (review, test, security, documentation
sign-off) that decide when a human should stop and check Codex's *output*
before it proceeds. A clean `codex doctor` report or a passing
`execpolicy check` says nothing about whether a diff should be merged —
that judgment stays with a reviewer regardless of how the sandbox is
configured.

---

Verified against Codex CLI 0.153.4 and learn.chatgpt.com/docs as of
2026-09. Re-check `codex --version` and `codex doctor` if observed behavior
doesn't match this file.
