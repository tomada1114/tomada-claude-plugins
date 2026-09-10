<!-- platform-annex -->

# Skills and Plugins

Reference current as of Codex CLI 0.153.4 / docs current as of 2026-09.

## SKILL.md mechanics on Codex

A skill is a directory holding `SKILL.md` plus optional `references/`, `scripts/`, and `assets/`. The published docs (`learn.chatgpt.com/docs/build-skills`) describe these discovery paths:

- `$CWD/.agents/skills/` and `$CWD/../.agents/skills/` — repo-scoped, resolved from the working directory upward.
- `<repository-root>/.agents/skills/` — repo-scoped, checked in, shared with the team.
- `$HOME/.agents/skills/` — user-scoped, personal, available across all projects.
- `/etc/codex/skills/` — system-scoped.
- plus a bundled set shipped with Codex itself.

In addition, this CLI also scans `$CODEX_HOME/skills/` (defaults to `~/.codex/skills/`) — undocumented in the published discovery-paths list above, but confirmed by `codex debug prompt-input`, which reports it as a skill root (`r0`) and lists every skill actually loaded from it. It is also where Codex's own bundled `skill-installer` and `skill-creator` skills install and scaffold new skills by default. Treat `$CODEX_HOME/skills/` as the practical equivalent of `$HOME/.agents/skills/` for personal, cross-project skills on this CLI.

Codex supports symlinked skill folders and follows the symlink target when scanning any of the above locations — a skill can live elsewhere (e.g. a Claude Code skill directory) and be exposed to Codex via a symlink into one of these paths.

```text
<repository-root>/
- .agents/
  - skills/
    - commit-message/
      - SKILL.md
      - references/
      - scripts/
      - assets/
```

`SKILL.md` frontmatter requires exactly two fields — `name` and `description` — nothing else is mandatory:

```markdown
---
name: commit-message
description: Write commit messages following this project's rules. Use when the user asks to create, check, or improve a commit message.
---

# Commit Message

...body...
```

`description` is the field that decides whether the skill gets read at all — write it as "what this skill does" + "when to use it," with concrete triggers (task type, situation), not a bare category label like "commit message skill." An ambiguous description keeps a well-written body from ever loading.

### The 4-step load flow

1. Codex holds a catalog of every available skill in context — `name`, `description`, `path` only, never the body.
2. The catalog budget is capped at roughly 2% of the active context window, or 8000 characters if the window size is unknown. Installing too many skills truncates descriptions or drops entries from the catalog, so add only what the current work needs.
3. The body loads only when either (a) the user explicitly mentions the skill, or (b) the task matches the `description` closely enough that Codex decides to read it.
4. Once loaded, the body's procedures and judgment criteria inform the rest of the turn.

Verify a new skill two ways, separately: confirm it fires when the description's scenario is asked for, and confirm it does *not* fire for a superficially similar but out-of-scope request (e.g., "write a commit message" should load it; "review this diff" should not). If it never fires, fix `description`. If it fires but behaves wrong, fix the body — these are independent failure modes.

### references / scripts / assets

Move long checklists, examples, or rule tables out of `SKILL.md` into `references/` — the body should stay the entry point and core procedure. Put helper scripts (data lookups, format checks) in `scripts/`; `SKILL.md` reaches them by relative path and can execute them via shell. Put templates or other work material in `assets/`.

### Explicit invocation

Two ways to force a specific skill to load, bypassing description-matching:

- Mention `$skill-name` in the prompt.
- Open the `/skills` picker and select it.

Codex has no per-skill slash command — `/skills` is a single picker over all available skills, and `$name` is the inline-mention form. Neither is the same shape as Claude Code's `/skill-name`.

### Suppressing auto-invoke

To stop a skill from loading on description-match while keeping explicit invocation available, add an `agents/openai.yaml` file next to `SKILL.md`:

```yaml
policy:
  allow_implicit_invocation: false
```

The skill then loads only via `$skill-name` or `/skills`, never automatically.

### Disabling without deleting

Turn an installed skill off — keeping the files in place — from `config.toml`:

```toml
[[skills.config]]
name = "commit-message"
enabled = false
```

This is the standard way to try a skill, decide it doesn't fit, and park it without removing the directory.

### `agents/openai.yaml` — the Codex-specific extension file

This file is Codex's analogue of Claude Code frontmatter extensions such as `allowed-tools`: a place for tool-specific metadata that doesn't belong in the portable `SKILL.md` frontmatter (which stays limited to `name` + `description` for cross-tool compatibility). It carries:

- Display metadata shown in catalogs/pickers (title, category, icon-equivalent info).
- MCP dependency declarations — which MCP servers a skill expects to be available.
- `policy.allow_implicit_invocation` — the auto-invoke toggle above.

A worked example on disk:

```text
~/.agents/skills/review/
├── SKILL.md
├── references/
│   └── review-checklist.md
├── scripts/
│   └── summarize_diff.py
└── agents/
    └── openai.yaml
```

This confirms `agents/openai.yaml` is a real, generated file (the `$skill-creator` System Skill writes one alongside `SKILL.md` when scaffolding a new skill), not a hypothetical extension point.

## Codex vs Claude Code — skill mechanics compared

Both tools read the same `SKILL.md` open-standard format — `name` + `description` frontmatter, progressive disclosure (catalog first, body on demand). A skill body written for one works almost unchanged on the other. What differs is placement, invocation, and the tool-specific extension mechanism:

| Aspect | Codex | Claude Code |
|---|---|---|
| Project skill location | `.agents/skills/` | `.claude/skills/` |
| Config file format | `config.toml` (TOML) | `settings.json` (JSON) |
| Context file name | `AGENTS.md` | `CLAUDE.md` |
| Explicit invocation | `$skill-name` mention, or `/skills` picker | `/<skill-name>` (the skill name becomes a slash command) |
| Auto-invoke-off mechanism | `agents/openai.yaml` → `policy.allow_implicit_invocation: false` | frontmatter `disable-model-invocation: true` |
| Disable without deleting | `config.toml` `[[skills.config]]` with `enabled = false` | remove from `.claude/skills/` (no separate toggle) |
| Tool-specific extension file | `agents/openai.yaml` (display metadata, MCP dependency declarations) | frontmatter extensions (`allowed-tools`, `context: fork`, etc. — no separate file) |

The clearest divergence: Claude Code treats a skill name as a slash command, folding "reusable workflow" and "thing you invoke with `/`" into one identity. Codex keeps them separate — a skill is "a work rule read when the task calls for it," invoked with `$name` or through `/skills`, while `/<command>` is reserved for session controls (see `references/permissions-and-sandbox.md` for `/permissions`, `/status`, etc.). Moving a skill between tools means adjusting placement, invocation syntax, and the tool-specific extension file — the `SKILL.md` body itself is the portable part and rarely needs rewriting.

## Subagents

A subagent is a separate execution unit with its own context window — the same underlying model capability as the main agent, but scoped to a limited file/log/test range, with the main agent responsible for composing its instructions, integrating its result, and giving the final answer to the user.

### Trigger conditions — exactly 4, and vague phrasing does not count

Codex spawns a subagent only when one of these is explicitly true:

1. The user says so in the prompt (asks for delegation or parallel work).
2. `AGENTS.md` instructs delegation for this kind of task.
3. A Skill's body instructs delegation.
4. `reasoning effort = ultra` is set — the one condition that isn't an explicit human instruction. Under `ultra`, Codex may spawn subagents on its own judgment when it decides parallelizing improves speed or quality, without the user asking.

A request like "look into this thoroughly" or "investigate exhaustively" does **not** trigger a subagent on its own — depth or exhaustiveness alone isn't delegation. If a split is wanted reliably, say so explicitly ("split this out to a subagent," "one agent per concern"), or encode that instruction once in `AGENTS.md` or a Skill so it repeats without being retyped.

### Built-in agents

| built-in agent | suited for |
|---|---|
| `default` | general-purpose work |
| `explorer` | codebase exploration and investigation (read-heavy) |
| `worker` | feature implementation, test fixes, bug fixes |

### Custom agent definitions

Define custom agents as TOML files:

- `~/.codex/agents/` — personal, all projects.
- `.codex/agents/` — project-scoped.

Each file specifies `name`, `description`, `developer_instructions`, and similar fields, letting you define role-scoped agents such as "PR-review-only," "read-only investigation," or "docs-check-only."

### Thread and depth limits

| setting | controls | default |
|---|---|---|
| `agents.max_threads` | concurrent agent threads open at once | 6 |
| `agents.max_depth` | how deep a subagent may spawn its own subagents | 1 |

`agents.max_depth` treats the root session as depth 0, so the default of 1 allows direct children but blocks a child from spawning grandchildren. Raising it lets instructions cascade — more subagents, more tokens, more latency, less predictable behavior — so treat depth as something to design deliberately, not maximize.

### The 3 splitting axes

These aren't mutually exclusive categories — splitting on one often implies another — but they're useful as separate motivations when deciding whether and how to delegate:

- **Work** — divide the same goal across parallel subagents (frontend vs. backend investigation, area-by-area sweep of a large codebase). The straightforward "more hands, faster" case.
- **Context** — isolate a subagent from the main conversation's accumulated compromises, rejected approaches, and mid-implementation reasoning, so its judgment isn't anchored to decisions already made. Useful for review: an implementer reviewing their own change tends to be lenient about the path they already committed to: a context-isolated subagent gives feedback closer to an independent reviewer.
- **Perspective** — narrow a subagent to a single axis of judgment (spec conformance only, or test coverage only, or security only) rather than asking one pass to weigh several axes at once, which tends to under-serve all but one. Conflicting subagent conclusions get reconciled by the main agent against overall goals and constraints.

### Delegation-prompt template

Subagent instructions follow the same Goal / Context Pointers / Constraints / Done When shape used for any Codex task (see `references/task-design.md` for the full template and its rationale) — a subagent delegation is just that template with a delegation-specific Goal and a Done When that specifies the exact return shape (bullet list, table, file-path list, JSON), since the return shape *is* the point of cutting the work out at all. A subagent that returns a long free-form narrative forces the main agent to re-read and re-summarize, erasing the benefit of delegating.

```text
Goal:
Delegate front-work investigation for the login-screen change to a subagent.

Context Pointers:
- login screen implementation
- auth handling
- related tests
- spec notes

Constraints:
- limit investigation to the four pointers above
- no implementation or file edits
- report only facts readable from the files — no inferred root cause

Done When:
- input validation, error display, auth API calls, and existing test coverage are listed as bullets
- each item cites the file path it came from
```

Start with read-only, investigation-shaped delegation (exploration, test-failure triage, pre-change impact review) before delegating file edits — edits raise the difficulty because overlapping subagent changes can collide, and the main agent must reconcile diffs on integration.

## Plugins

A plugin bundles Agent Skills, Apps, MCP server configs, and Hooks into one installable package — the unit for distributing a set of skills and connections together, as opposed to a single skill distributed alone.

### `plugin.json` schema

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "description": "Plugin description",
  "skills": "./skills",
  "mcpServers": "./mcp.json",
  "apps": "./apps/apps.json",
  "hooks": "./hooks/hooks.json"
}
```

| field | role |
|---|---|
| `name`, `version`, `description` | identity and description |
| `skills` | relative path to the directory holding this plugin's skills |
| `mcpServers` | relative path to the MCP server config for this plugin |
| `apps` | relative path to the Apps config |
| `hooks` | relative path to the Hooks config |

Only include the fields a given plugin actually needs.

### Directory layout

```text
my-plugin/
├── .codex-plugin/
│   └── plugin.json
├── skills/
│   ├── skill-a/
│   │   └── SKILL.md
│   └── skill-b/
│       └── SKILL.md
├── mcp.json
└── hooks/
    └── hooks.json
```

Two things to get right: `plugin.json` lives inside the hidden `.codex-plugin/` directory, not at the plugin root — Codex looks there first when reading a plugin. And the default locations are `./skills/`, `./mcp.json`, `./hooks/hooks.json` relative to the plugin root; `plugin.json`'s path fields only need setting when deviating from those defaults. Note `skills/` here — the directory a plugin bundles its skills in — is a different directory from `.agents/skills/`, the standalone-skill discovery path; a skill inside a plugin is not independently discoverable the way a standalone skill is.

### Activation

A plugin sitting in a directory isn't active until named in `config.toml`:

```toml
[plugins."my-plugin@my-marketplace"]
enabled = true
```

The section key takes the form `<plugin-name>@<marketplace-name>` — the part after `@` names the marketplace (source) the plugin comes from, itself declared in a separate `config.toml` section; a marketplace can point at a local directory or a remote registry. `enabled` defaults to `true` once an entry exists; set it to `false` explicitly to keep the config entry but disable the plugin temporarily.

### Cache path

A plugin's resolved contents live under `$CODEX_HOME` (default `~/.codex/`):

```text
$CODEX_HOME/plugins/cache/<marketplace-name>/<plugin-name>/<version>/
```

The `config.toml` activation key and the cache directory name correspond directly, which makes it straightforward to trace which on-disk version a given `[plugins."name@marketplace"]` entry resolves to.

## MCP

MCP (Model Context Protocol) is the standard for connecting Codex to tools and data sources outside the repository — third-party docs, browser control, Figma, and similar. It sits alongside Apps (connectors to already-known services like GitHub or Slack, bundled with authentication) as the "connect externally" layer; Skills and Plugins are the "define the work" and "package for distribution" layers respectively.

Add an MCP server from the CLI:

```bash
codex mcp add context7 -- npx -y @upstash/context7-mcp
```

Check what's currently connected:

```
/mcp
```

Configure directly in `config.toml`:

```toml
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp"]
```

When a plugin bundles its own MCP server, the server's startup is already defined by the plugin — the user only adjusts enablement and tool-approval policy, under:

```toml
[plugins.<plugin-name>.mcp_servers.<server-name>]
```

MCP servers run as either a local STDIO process or a remote Streamable HTTP endpoint (the latter supporting Bearer-token or OAuth auth). Representative servers referenced in official examples: OpenAI Docs, Context7, Figma, Playwright, Chrome DevTools, Sentry, GitHub — covering documentation lookup, browser automation, design access, and issue/PR operations respectively.

Prefer a plugin's bundled App connector over configuring the same service as a standalone MCP server when both exist for it — the plugin route bundles authentication and related skills in one step. Reach for a direct MCP server when no plugin covers the service, or when you need finer control over the connection than a plugin exposes.
