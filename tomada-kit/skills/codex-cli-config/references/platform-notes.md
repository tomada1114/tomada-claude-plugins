<!-- platform-annex -->

# Platform notes (this skill's own Codex/Claude Code dual-use)

This skill is a **read-only reference knowledge base**, not an orchestrator.
It never delegates, never runs in parallel, never calls another skill or
tool, and never depends on a host built-in slash command. So unlike most
skills bridged by `dual-platform-skills`, there is effectively **nothing to
degrade**: the entire body reads identically from Claude Code and from
Codex CLI, because the same file is opened either way (Topology A — see
`dual-platform-skills/references/topology.md`).

## Tool mapping

Not applicable. No delegation, no option-prompting, no MCP dependency, no
built-in-command dependency exists in this skill's body.

## Best-effort degradation on Codex

None. Nothing in this skill's execution changes between hosts.

## The one thing to get right when re-auditing this skill

`scripts/classify_skill.py` from `dual-platform-skills` will flag roughly
50+ hits in this skill's body — `/status`, `/review`, `/init`, `/plan`,
`/compact`, `/permissions`, "Plan mode", `git commit`/`git push` examples,
and `~/.codex/...` paths. **Nearly all of these are false positives.** This
skill's *subject matter is Codex CLI itself*, so those strings are facts
being documented (Codex's own slash commands, Codex's own Plan mode, Rules
example patterns that reference `git commit` as data, and paths being
explained rather than paths being instructions to the reader). None of them
are this skill instructing its own reader to invoke a host-specific tool.

Before "fixing" any of these on a future pass: check whether the surrounding
sentence is *describing Codex CLI to the reader* (leave it — neutralizing it
would delete the fact) versus *telling the reader what to do with a
platform-specific mechanism* (the actual target of neutralization). This
skill has essentially none of the latter.

## Sandbox / execution-environment note

This skill does not itself run git, a package manager, or a test runner —
its `git commit` / `git push` / `pytest` / `cargo` / `npm install` mentions
are all example strings inside documented Rules patterns or Done-When
criteria, not commands this skill executes. The sandbox-write-op failure
mode described in `dual-platform-skills/references/transformation-rules.md`
(R14) does not apply here.
