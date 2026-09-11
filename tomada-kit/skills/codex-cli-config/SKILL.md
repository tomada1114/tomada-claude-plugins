---
name: codex-cli-config
description: >-
  Reference for OpenAI Codex CLI configuration, permissions, sandboxing, and
  autonomy — sandbox_mode and permission profiles, approval_policy, Rules
  (.rules / prefix_rule), config.toml precedence and trust, AGENTS.md
  discovery, task design (Mini Codex, Done When, Plan mode), Skills/Plugins/
  subagents/MCP, and running Codex unattended in CI or Automations.
  Use when asked how to configure Codex CLI, loosen or tighten its sandbox,
  let it run commands (including git) without full access, set up the
  equivalent of an "auto mode," diagnose why a config.toml, AGENTS.md, or
  Rules file isn't taking effect, or write task prompts and AGENTS.md/Skill
  content Codex will act on well. Also use when Codex CLI itself is asked
  about its own configuration, permissions, or sandboxing — 自分（Codex）の
  設定・権限・サンドボックスについて聞かれたとき、承認なしで動かす方法や
  config.toml/AGENTS.md/Rules が効かない原因を尋ねられたときにも使う。
metadata:
  platforms: claude-code, codex
---

# Codex CLI configuration

Reference knowledge base for OpenAI Codex CLI's configuration and permission
system. All facts below and in `references/` were checked against the
official docs (`learn.chatgpt.com/docs/*`) and the installed CLI's own
`--help` output — prefer this over recalled knowledge, which is likely to
carry the CLI's frequent renames and removals (see `references/diagnostics.md`
for the version/date this was last verified against).

## Mental model

Three axes, and they answer different questions:

- **`sandbox_mode` (or the newer `[permissions.<name>]` profile system)** —
  *what* Codex can touch without asking: filesystem and network. Pick one of
  the two systems, never both — see `references/permissions-and-sandbox.md`.
- **`approval_policy`** — *when* it has to ask before touching something
  outside that boundary — `references/permissions-and-sandbox.md`.
- **Rules (`.rules` / `prefix_rule()`)** — narrow, per-command-prefix
  exceptions to the asking, layered user → project → admin, strictest always
  wins — `references/rules-execpolicy.md`.

Config values themselves come from a layered `config.toml` (CLI flags >
project `.codex/config.toml` > `--profile` file > user `~/.codex/config.toml` <!-- neutrality-ignore: N2 -->
> system > built-in defaults) gated by per-project trust —
`references/config-files-and-precedence.md`.

## Headline answers

**"Let git commit run freely without `danger-full-access`."** `workspace-write`
(and every writable root under a permission profile) keeps `.git`, `.codex`,
and `.agents` read-only *recursively* — that's what makes `git commit` ask for
approval even though the rest of the tree is writable. The fix is a Rules
entry, not a looser sandbox:
```python
# $CODEX_HOME/rules/default.rules
prefix_rule(
    pattern = ["git", ["add", "commit", "status", "diff", "log"]],
    decision = "allow",
    justification = "Local git operations are trusted in this workspace.",
    match = ["git commit -m msg", "git add ."],
)
```
Full recipe, safety-complement rules (`push`, `push --force`, `reset --hard`),
and caveats: `references/rules-execpolicy.md`.

**"I picked Full access but now it refuses things instead of asking."**
Full access sets `approval_policy = "never"` alongside the sandbox, and a
Rules `prompt` entry with nobody to ask fails closed into a block. For
"sandbox off, but still ask me," write `default_permissions =
":danger-full-access"` + `approval_policy = "on-request"` in `config.toml`
and select **Custom (config.toml)** in the app's picker — a `-p` profile
*file* never appears in that picker at all.
`references/permissions-and-sandbox.md`.

**"Codex can't write git metadata / commits fail under my profile."**
`:workspace` keeps `.git` recursively read-only. A custom profile needs
`":root" = "write"` in its `filesystem` table — that is usually the whole
fix, and it beats turning the sandbox off.
`references/permissions-and-sandbox.md`.

**"Codex equivalent of Claude Code's auto mode."** `workspace-write` +
`approval_policy = "on-request"` + `approvals_reviewer = "auto_review"` (or
`codex exec --approve-for-me`) — same sandbox boundary as standard on-request,
but escalations go to a reviewer subagent instead of stopping for you. In the
TUI: `/permissions` → **Auto**. Details and more recipes:
`references/autonomy-recipes.md`.

**"`sandbox_mode` vs. permission profiles — which one?"** They're mutually
exclusive (`default_permissions` explicitly says don't combine either with
`sandbox_mode`). `sandbox_mode` is simpler and enough for ordinary local work;
permission profiles (Beta) give per-path and per-domain control and are the
forward path for anything finer-grained. `references/permissions-and-sandbox.md`.

**"There's no `/approvals` command."** It's `/permissions`. `/approve` is a
different thing (retry an auto-review denial). `references/permissions-and-sandbox.md`.

**"Does a `forbidden` rule still block under Full Access / `--yolo`?"** Yes.
`--dangerously-bypass-approvals-and-sandbox` just sets `sandbox_mode =
DangerFullAccess` + `approval_policy = Never` — the same two values a
`:danger-full-access` + `never` profile sets explicitly, not a separate
bypass path. A `forbidden` rule always blocks; a `prompt` rule fails closed to
a block under `never` (no one left to ask) instead of silently running; only
`allow` is unaffected. Verified against the `codex-rs` source, not a blog —
full citations and the built-in dangerous-`rm` heuristic that applies even
with zero user rules: `references/diagnostics.md`.

## Reference map

| Question shape | Read |
|---|---|
| sandbox_mode, `[sandbox_workspace_write]`, permission profiles, `approval_policy`, `/permissions` | `references/permissions-and-sandbox.md` |
| `.rules` / `prefix_rule()`, layering, "my rule isn't working" | `references/rules-execpolicy.md` |
| "how far should I let it run" as named, copy-paste recipes | `references/autonomy-recipes.md` |
| config.toml layering, project trust, `--profile` files, `requirements.toml` | `references/config-files-and-precedence.md` |
| AGENTS.md discovery/merge order, SSOT across tools, the retro→AGENTS.md cycle | `references/agents-md.md` |
| Writing task prompts Codex can self-verify: Mini Codex, Done When, Plan mode | `references/task-design.md` |
| SKILL.md on Codex, subagents, `plugin.json`, MCP, Codex vs. Claude Code skills | `references/skills-and-plugins.md` |
| GitHub Action, `codex exec` in CI, scheduled Automations, `@codex review` | `references/ci-and-automation.md` |
| `codex doctor`, `/status`, `execpolicy check`, symptom → cause → fix table | `references/diagnostics.md` |

Read only the file(s) the question needs — they cross-reference each other
rather than repeating shared material, so a "why is X ignored" question
usually resolves in `diagnostics.md`'s symptom table plus one linked file.

## Critical rules

- Never present `approval_policy = "untrusted"`, `--full-auto`,
  `sandbox_workspace_write_writable_roots`, `[profiles.<name>]` inside
  `config.toml`, or `/approvals` as current syntax — all retired, deprecated,
  nonexistent, or removed. `references/diagnostics.md` has the full list and
  what replaced each one.
- `sandbox_mode`/`[sandbox_workspace_write]` and `default_permissions`/
  `[permissions.<name>]` are two different systems — don't mix keys from both
  in one example.
- When a fact in these references looks like it might have drifted (flag
  names change often on Codex CLI releases), say so and suggest checking
  `codex --help` / `codex doctor` / the docs rather than asserting confidently.
- Never verify a `forbidden`/dangerous rule (or answer "will this survive
  Full Access") by having the agent actually run the dangerous command —
  that's a real invocation, not a test. Use `codex execpolicy check` (a
  static, non-executing rule matcher) instead — see `references/diagnostics.md`.

## Platform notes

See [references/platform-notes.md](references/platform-notes.md).
