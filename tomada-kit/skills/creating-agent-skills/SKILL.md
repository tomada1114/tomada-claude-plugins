---
name: creating-agent-skills
description: "Create or improve Agent Skills (the shared SKILL.md format read by Claude Code and OpenAI Codex CLI — SKILL.md + optional references/scripts/assets). Two playbooks: build a skill from scratch or from an existing doc; or review an existing skill through parallel specialist lenses (prose quality, agent neutrality, structure, scripts, orchestration) and propose fixes. Takes a free-form request — \"I want a skill that…\", \"turn this runbook into a skill\", \"audit this skill\", \"it never fires\", \"split this into sub-agents\" — optionally followed by a skill name or absolute path. Also triggers on Codex skill / skill-creator requests."
argument-hint: "<free-form intent> [skill-name-or-path]"
metadata:
  platforms: claude-code, codex
---

# creating-agent-skills

Workshop for building and maintaining Agent Skills — the shared `SKILL.md` format both Claude Code and Codex CLI read natively (see [references/agent-neutral-authoring.md](references/agent-neutral-authoring.md) for what's common vs. per-host). Most guidance here is host-agnostic; the few Claude Code-only mechanics (`Task`, `AskUserQuestion`, plugin `${CLAUDE_PLUGIN_ROOT}`, etc.) are called out explicitly where they appear. <!-- neutrality-ignore: N1 --> <!-- neutrality-ignore: N2 -->

`$ARGUMENTS` is **free-form text**, in any language. There is no mode keyword to parse. Read the user's intent, optionally pick out a skill name or path token, then route to [Building a skill](#building-a-skill) or [Improving a skill](#improving-a-skill). If the request mixes goals (e.g. "audit it, and fix whatever is broken"), chain playbooks in the order implied by the request.

## Contract

**Input:** free-form natural-language description of the task, optionally including a skill name or absolute path.

**Outputs depend on the inferred task:**
- Building → directory at `~/.claude/skills/<name>/` (or `<cwd>/.claude/skills/<name>/` with `--scope project`). Run `dual-platform-skills` afterward to bridge it onto Codex. <!-- neutrality-ignore: N2 -->
- Improving → `${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/skills-audit/<skill-name>/` holding `report.md`, `lens-<name>.md` per lens, `recommendations.md`. Edits to the skill itself only after the user approves.

**Bundled scripts** (invoke through `${CLAUDE_SKILL_DIR}`, never a hardcoded path): <!-- neutrality-ignore: N2 -->
- `scripts/init_skill.sh` — scaffold new skill from template
- `scripts/validate_skill.py` — frontmatter / size / link-integrity / neutrality checks, `--json`
- `scripts/audit_skill.py` — wraps validate, adds editorial checks A001–A010, emits a `profile` block, writes a Markdown report
- `scripts/check_scripts.py` — for skills with `scripts/`: tests, coverage ≥ 90 %, hardcoded paths, `.gitignore` (S001–S007), `--json`

## Intent inference

Match signals in `$ARGUMENTS` to a playbook on meaning, not wording — the request often arrives in Japanese. Ask one short clarifying question only if genuinely ambiguous.

| Signal in the request | Playbook |
|---|---|
| build / new / scaffold / from scratch / convert / "turn this doc into a skill" / "I want a skill that…" | [Building a skill](#building-a-skill) |
| audit / review / health check / refactor / slim down / "never fires" / "fires too often" / sub-agents / parallel / "split this up" | [Improving a skill](#improving-a-skill) |

If a token in the input matches an existing skill name or `~/.claude/skills/...` path, treat it as the target. Otherwise infer or ask. Both goals in one request ("build it, then review it") → run Building to completion, then Improving. <!-- neutrality-ignore: N2 -->

---

## Core Principles (apply in every playbook)

Full rationale and examples: [references/authoring-principles.md](references/authoring-principles.md) — read it while implementing step 5 below.

- **English is the authoring language.** Every part of a skill, including `description`, and no mirrored Japanese trigger keywords — selection matches on meaning.
- **Concise is key.** The context window is a public good; add only what the model doesn't already have.
- **A skill is a prompt.** Structure decides *when* text reaches the model; wording decides whether it helps. Read [prompt-authoring.md](references/prompt-authoring.md) before writing or approving prose.
- **Degrees of freedom.** High freedom (text) for heuristic tasks; medium (pseudocode/scripts with parameters) for a preferred pattern with leeway; low (specific scripts, few parameters) for fragile, consistency-critical operations.
- **Deterministic work belongs in scripts**, not prose — see [scripts-guide.md](references/scripts-guide.md#conventions) for conventions and tests.
- **Size budget.** SKILL.md body: target ≤150 lines, warning above 200 (`W031`), error above 500 (`E030`). `references/*.md`: warning above 400 lines (`A010`). See [patterns-and-structure.md](references/patterns-and-structure.md#sizing-and-slimming-skillmd) for the split rule and the slimming procedure.
- **Content rules**: references one level deep, ToC over 100 lines, forward slashes, one default not a menu, one term per concept, no time-sensitive statements, MCP tools fully qualified, dependencies named explicitly.

---

## Building a skill

Use for a new skill — from scratch, or from an existing doc/runbook/note.

1. **Capture intent.** If a source doc exists, read it fully first — most of the questions below are answered by it. Otherwise ask in one round: concrete tasks, invocation style (command / description-match / both), inputs/outputs, 1–2 example invocations, and whether this runs on Codex too (default: both — see [agent-neutral-authoring.md](references/agent-neutral-authoring.md) before writing prose either way).
2. **Name the gap before writing anything.** For each example, state what Claude does *without* the skill and where it falls short — that gap is the spec; everything else documents behavior the model already had. Turn it into three test prompts with checkable expected behavior ([evaluating-skills.md](references/evaluating-skills.md)).
3. **Plan reusable contents.** Code rewritten each time → `scripts/` (with a test); a doc to consult → `references/`; boilerplate copied into output → `assets/`. From a source doc over ~300 lines: split by concern into `references/`, keeping only what a competent stranger to *this* system couldn't guess.
4. **Scaffold:** `${CLAUDE_SKILL_DIR}/scripts/init_skill.sh <name> [basic|advanced] [--scope user|project]`.
5. **Implement resources first, SKILL.md last.** Write and test `scripts/`/`references/`/`assets/`, then the body in imperative form, applying the Core Principles above and [prompt-authoring.md](references/prompt-authoring.md). Omit `allowed-tools` unless one of the two reasons in [yaml-spec.md](references/yaml-spec.md#allowed-tools) applies. Markdown links to bundled files use relative paths; commands and sub-agent prompts use `${CLAUDE_SKILL_DIR}/...`. If the skill delegates to fresh contexts, name a model per spawn (table in [prompt-authoring.md](references/prompt-authoring.md#assigning-models-and-effort)), keep delegation prompts in `references/agents/<name>.md`, and state the delegation bar and cap (patterns in [orchestration-patterns.md](references/orchestration-patterns.md)). From a source doc, write in English; keep original wording only for verbatim material (UI labels, error strings, sample output).
6. **Validate:** `python3 ${CLAUDE_SKILL_DIR}/scripts/validate_skill.py <skill-path>` and, if the skill has `scripts/`, `check_scripts.py`. Fix every error, including the neutrality lint.
7. **Check against the gap list.** Run the three step-2 prompts in a fresh session. Separate "didn't activate" (a `description` problem) from "activated but wrong" (a body problem), and delete any instruction covering behavior the no-skill baseline already got right ([evaluating-skills.md](references/evaluating-skills.md) for repeatable measurement).

## Improving a skill

Use for health, drift, bloat, trigger accuracy, or restructuring — including splitting into phases or sub-agents. One agent reading for every concern at once misses things; lenses run in fresh contexts and are merged after.

**P0. Script pass (deterministic).** Resolve the path (`~/.claude/skills/<name>` for a bare name). <!-- neutrality-ignore: N2 --> Run:
```bash
AUDIT_DIR="${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/skills-audit/<skill-name>"
mkdir -p "$AUDIT_DIR"
python3 ${CLAUDE_SKILL_DIR}/scripts/audit_skill.py <skill-path> --json --report "$AUDIT_DIR/report.md" > "$AUDIT_DIR/audit.json"
python3 ${CLAUDE_SKILL_DIR}/scripts/check_scripts.py <skill-path> --json > "$AUDIT_DIR/scripts.json"   # only if scripts/ exists
```
Read the `profile` block of `audit.json` — it decides the lens set below. See [patterns-and-structure.md](references/patterns-and-structure.md#what-the-p0-script-pass-already-covers) for what the scripts already catch, so lenses don't repeat it.

**P1. Lenses (parallel, fresh context each).** Each fills [references/agents/review-lens.md](references/agents/review-lens.md) with one reference's checklist and writes `$AUDIT_DIR/lens-<name>.md`.

| Lens | Checklist | Model | Runs when |
|---|---|---|---|
| prose | [prompt-authoring.md](references/prompt-authoring.md#review-checklist) (`PA`) | `opus` | always |
| neutrality | [agent-neutral-authoring.md](references/agent-neutral-authoring.md#review-checklist) (`AN`) | `sonnet` | always |
| structure | [patterns-and-structure.md](references/patterns-and-structure.md#review-checklist) (`ST`) | `sonnet` | always |
| scripts | [scripts-guide.md](references/scripts-guide.md#review-checklist) (`SC`) | `sonnet` | `scripts/` exists, or a code block in SKILL.md |
| orchestration | [orchestration-patterns.md](references/orchestration-patterns.md#review-checklist) (`OR`) | `opus` | spawns sub-agents, has phases, or body > 150 lines |

**Gate:** if SKILL.md is under 100 lines with no `references/` or `scripts/`, spawn nothing — run the always-on lenses inline. Never more than the five lenses above. Lenses report full coverage with confidence and severity; filtering happens in P2, not the lens.

**P2. Merge and propose.** Deduplicate by checklist ID and location. Rank: blocks the skill → misleads the model → costs context for nothing → cosmetic. Write `$AUDIT_DIR/recommendations.md` with evidence (`file:line`) and old→new text for concrete items. Propose delegation only under the conditions and limits in [orchestration-patterns.md](references/orchestration-patterns.md#proposing-orchestration) (at most one per phase, three per skill). **Do not modify the audited skill until the user approves.**

**P3. Apply and re-run P0.** Repeat until no errors remain and approved items are closed; a `scripts/` change must also pass `check_scripts.py`.

---

## Resources

Load on demand:
- [references/authoring-principles.md](references/authoring-principles.md) — full Core Principles rationale, "what NOT to put in a skill", production patterns worth copying.
- [references/agent-neutral-authoring.md](references/agent-neutral-authoring.md) — write once for both hosts. Holds `AN` checklist.
- [references/prompt-authoring.md](references/prompt-authoring.md) — wording for current models, sub-agent prompt layers, model/effort per spawn. Holds `PA` checklist.
- [references/yaml-spec.md](references/yaml-spec.md) — every frontmatter field, substitutions, bash injection, diagnosing a skill that never activates.
- [references/patterns-and-structure.md](references/patterns-and-structure.md) — content types, storage locations, sizing/slimming, workflow shapes. Holds `ST` checklist.
- [references/scripts-guide.md](references/scripts-guide.md) — script-or-prose decision, conventions, patterns. Holds `SC` checklist.
- [references/orchestration-patterns.md](references/orchestration-patterns.md) — sub-agent and phase-handoff patterns, when to propose orchestration. Holds `OR` checklist.
- [references/platform-notes.md](references/platform-notes.md) — Claude Code / Codex tool mapping for orchestration guidance.
- [references/workspace-conventions.md](references/workspace-conventions.md) — deterministic output paths, snapshot/restore.
- [references/evaluating-skills.md](references/evaluating-skills.md) — eval-driven authoring, baseline comparison, cross-model testing.
- [references/agents/review-lens.md](references/agents/review-lens.md) — the prompt template each Improving lens is filled from.

Templates: [assets/basic-skill-template.md](assets/basic-skill-template.md), [assets/advanced-skill-template.md](assets/advanced-skill-template.md).

Examples: [greeting-generator](examples/greeting-generator/) · [http-status-guide](examples/http-status-guide/) · [project-validator](examples/project-validator/) · [code-analyzer](examples/code-analyzer/) · [pr-review-pipeline](examples/pr-review-pipeline/).

---

## Hard rules

- **Never** confuse `disable-model-invocation: true` (user-only) with `user-invocable: false` (Claude-only).
- **Always** run `validate_skill.py` (and `check_scripts.py` when `scripts/` exists) before declaring a skill done.
- **Always** set `metadata.platforms` when scaffolding. Default `claude-code, codex`, agent-neutral body — `claude-code` only when the skill's actual subject is Claude Code itself.
- **Always** reference bundled scripts as `${CLAUDE_SKILL_DIR}/scripts/...`, never a hardcoded `~/.claude/skills/<name>/...` path. <!-- neutrality-ignore: N2 -->
- **Always** infer intent from `$ARGUMENTS` rather than demanding a mode keyword.
- **Never** write an instruction telling the model to echo, transcribe, or explain its internal reasoning — can trigger a refusal and force a model fallback on some hosts.
- **Always** specify a model when a skill spawns a sub-agent.
- **Never** add `allowed-tools` without one of the two reasons in [yaml-spec.md](references/yaml-spec.md#allowed-tools).
- **Always** author skill content in English; `description` is English-only with no mirrored Japanese keywords.
- **Never** spawn review lenses for a skill under the P1 gate, and never more than the five lenses listed.
