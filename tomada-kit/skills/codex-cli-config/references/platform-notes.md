<!-- platform-annex -->

# Platform notes (this skill's own Codex/Claude Code dual-use)

This skill is a read-only reference knowledge base, not an orchestrator: it
never delegates, prompts for options, calls another skill or tool, or depends
on a host built-in command. The body reads identically from Claude Code and
Codex CLI (Topology A — see `dual-platform-skills/references/topology.md`),
so there is no tool mapping and nothing to degrade.

## Re-auditing this skill

`scripts/classify_skill.py` from `dual-platform-skills` flags 50+ hits here —
`/status`, `/review`, `/init`, `/plan`, `/compact`, `/permissions`, "Plan
mode", `git commit`/`git push`, `pytest`/`cargo`/`npm install`, and
`~/.codex/...` paths. Nearly all are false positives: the skill's subject is
Codex CLI, so these strings document Codex's own commands, Rules example
patterns, and paths being explained. Before neutralizing one, check whether
the sentence *describes Codex CLI* (leave it) or *tells the reader to invoke
a platform-specific mechanism* (the actual target — this skill has almost
none). For the same reason the sandbox-write-op note (R14 in
`dual-platform-skills/references/transformation-rules.md`) does not apply.
