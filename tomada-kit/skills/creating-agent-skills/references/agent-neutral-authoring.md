<!-- platform-annex -->
# Agent-neutral authoring (Claude Code × Codex CLI)

Both hosts read the same **Agent Skills standard** directory shape: `SKILL.md` (required `name`/`description`) plus optional `references/`, `scripts/`, `assets/`. Neither host requires special conversion of that structure — the gap is entirely in what the **body text** assumes about the runtime. This reference is the authoring-time counterpart to the `dual-platform-skills` skill, which retrofits *existing* skills; use this doc while *writing* a new one so it never needs retrofitting.

## Decide scope up front

Every skill declares its intended reach via `metadata.platforms` in frontmatter (a Codex-recognized field; Claude ignores unknown `metadata` keys harmlessly):

```yaml
metadata:
  platforms: claude-code, codex   # or just: claude-code
```

- `claude-code, codex` — body text must be **agent-neutral** (next section). This is the default for any skill whose actual task (not just its mechanics) makes sense on both hosts.
- `claude-code` only — body may use Claude constructs freely (this is the honest choice for skills that are inherently about Claude Code itself, e.g. reference docs for Claude Code's own settings/hooks).

`dual-platform-skills/scripts/neutrality_lint.py` enforces this declaration; run it (or `scripts/validate_skill.py`, which calls it) before considering a new skill done.

## Writing agent-neutral body text

**Never name a Claude-specific tool in `SKILL.md` or `references/**/*.md` body text.** Write what the model should *do*, not which tool does it:

| Instead of naming... | Write... |
|---|---|
| `AskUserQuestion` | "present 2-4 options with tradeoffs and a recommendation, then wait for the user's answer" |
| `TodoWrite` | "track completed phases as a checklist" |
| `Task` fan-out | "delegate independent work in parallel where the environment supports it, otherwise run it sequentially — preserve phase order either way" |
| `Skill` (invoking another skill) | just name the other skill (`Use the <name> skill`) — let each host resolve it |
| `context: fork` | don't mention it in the body at all — it's a frontmatter-only hint |

The full lookup table is [`../dual-platform-skills/references/neutral-phrasing.md`](../dual-platform-skills/references/neutral-phrasing.md) (same file `dual-platform-skills` uses when retrofitting — do not duplicate it here).

**The one place tool names belong**: a `references/platform-notes.md` file, marked on its first line with `<!-- platform-annex -->`. That marker exempts the file from the neutrality lint entirely — put the Claude/Codex tool mapping and the "what's lost on Codex" list there, nowhere else. See any bridged skill's `platform-notes.md` for the shape.

**Alternatives go where they're used, not just at the end.** If a phase needs "wait for user input," write the neutral phrasing on that phase's own line. A single "Codex limitations" section at the bottom that a Codex reader never reaches mid-procedure is not real coverage — see `dual-platform-skills/references/transformation-rules.md` R11.

## Frontmatter: what each host reads

Both hosts parse `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` — the Agent Skills standard fields. Everything else is a **Claude Code extension** Codex silently ignores (harmless, so keep using them freely for Claude-only behavior): `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `disallowed-tools`, `model`, `effort`, `context`, `agent`, `background`, `paths`, `hooks`, `shell`. See `yaml-spec.md` (load via SKILL.md) for the full three-way split (standard / Claude extension / Codex extension).

`description` should carry trigger language useful on both hosts — avoid phrasing that only makes sense inside Claude Code's own routing vocabulary (e.g. don't write "Use PROACTIVELY when..." as the *only* trigger signal; Codex's own skill-selection reads the same field but doesn't share that convention).

## Paths

- **Intra-skill references** (`references/x.md`, `scripts/y.py`): always relative. Codex reaches the same files through a symlink (Topology A, see `dual-platform-skills/references/topology.md`), so relative paths resolve identically on both hosts.
- **Cross-skill references**: `../<other-skill>/references/x.md` — only resolves if both skills are bridged into the same Codex skills directory. Don't assume it without checking (`dual-platform-skills` P0 handles this when retrofitting).
- **Passing a path into a spawned sub-agent**: relative paths do NOT resolve there (the sub-agent's cwd is the repo root, not the skill directory). Either inline the referenced content into the prompt, or resolve to an absolute path first. Never use `${CLAUDE_PLUGIN_ROOT}` or any other platform environment variable inside a template meant to run on both hosts — use a `{SKILL_DIR}` placeholder that the *calling* context fills in with a real absolute path.
- **Persistent state / output the skill writes** (run records, generated reports, cached artifacts): `${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/<skill-name>/`. Never invent a `~/.claude/<name>/` or `~/.codex/<name>/` location — those are platform-namespaced and the whole point of this convention is that both hosts write to the same place. Use `${TMPDIR:-/tmp}/agent-skills/<skill-name>/` for scratch that doesn't need to survive.

## Sub-agent delegation

Don't hardcode a sub-agent's instructions as an inline prompt string scattered across `SKILL.md`. Put them in `references/agents/<name>.md` (skill-relative, one canonical copy) and have `SKILL.md` say "delegate using `references/agents/<name>.md`" in neutral phrasing. Both hosts then have one thing to read — Claude Code hands its *contents* to a spawned sub-agent, Codex's main context reads it directly and works through it inline. See `dual-platform-skills/references/transformation-rules.md` R4/R10/R13 for the exact mechanics (especially: never pass a skill-relative path into a spawned sub-agent — its cwd won't resolve it).

## When a skill genuinely can't be neutral

Some content is legitimately about Claude Code itself (this is different from "hasn't been converted yet"): a skill documenting Claude Code's own hooks system, for instance, has no Codex equivalent to be neutral toward. Declare `metadata.platforms: claude-code` and don't force neutral phrasing that would just be confusing. This is an honest declaration, not a workaround — see `dual-platform-skills/references/transformation-rules.md` R8/R9 for the equivalent judgment call when retrofitting an existing skill.

## Review checklist

Used by the Improving playbook's *neutrality* lens. The lint (`N1–N4`, run by `validate_skill.py`) catches literal tool names and platform paths; these items are what it cannot see.

### AN1: The `metadata.platforms` declaration matches the skill's real reach
`claude-code` only is justified solely when the subject *is* Claude Code itself (its hooks, settings, its own tools, its plugin system). Any other skill declared Claude-only, or declared dual but written for one host, is a FAIL.

### AN2: No paraphrased tool use the regex misses
Watch for "use the Agent tool," "spawn a task agent," "call the skill tool," "fork the context," "run it in the background," or a slash command given as an instruction. The body should say what to do, not which tool does it.

### AN3: Sub-agent instructions live in `references/agents/<name>.md`
One canonical copy, and SKILL.md delegates in neutral phrasing with the sequential fallback stated on the same line — not only in a trailing note.

### AN4: No skill-relative path is handed to a spawned context
Placeholders are filled with absolute paths by the caller, not left as `references/x.md` for a sub-agent whose working directory won't resolve them. No platform environment variable appears inside a template meant for both hosts.

### AN5: Persistent state and scratch use the shared conventions
Persistent state under `${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/<skill>/`; scratch under `${TMPDIR:-/tmp}/agent-skills/<skill>/`. No platform-namespaced write targets.

### AN6: Alternatives sit where they are used
Neutral phrasing appears on the phase's own line, not only in a trailing "limitations" section. Tool names appear only in `references/platform-notes.md` marked `<!-- platform-annex -->`.

### AN7: `description` trigger language works on both hosts
Not solely Claude Code routing vocabulary such as "Use PROACTIVELY" — the trigger phrasing should read naturally as a description of when the skill applies, on either host.
