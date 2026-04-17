---
name: claudecode-skill-creating
description: Create, audit, refactor, or troubleshoot Claude Code skills via explicit command. Modes: new (scaffold a fresh skill), audit (run validate + audit scripts and write a report), convert (turn an existing doc into a skill), troubleshoot (diagnose activation, frontmatter, or link issues), add-subagents (introduce multi-phase orchestration). Accepts a skill name or path as the second argument.
argument-hint: "[new|audit|convert|troubleshoot|add-subagents] [skill-name-or-path]"
---

# claudecode-skill-creating

Workshop for building and maintaining Claude Code skills. This skill is designed for **explicit command invocation** — the dispatch table below is the entry point.

## Contract

**Inputs:**
- `$1` (mode, required): `new` | `audit` | `convert` | `troubleshoot` | `add-subagents`
- `$2` (target, required for `audit`/`troubleshoot`/`add-subagents`): skill name or absolute path
- For `new` and `convert`, ask the user for missing details before scaffolding.

**Outputs:**
- `new`: a scaffolded skill at `~/.claude/skills/<name>/` (or `<cwd>/.claude/skills/<name>/` with `--scope project`)
- `audit`: a Markdown report at `~/.claude/skills-audit/<skill-name>/report.md`
- `convert`: same path layout as `new`
- `troubleshoot`: a diagnosis printed in chat plus optional fix patches
- `add-subagents`: edited SKILL.md plus new subagent files

**Bundled scripts** (always invoke with absolute paths):
- `scripts/init_skill.sh` — scaffold new skill from template
- `scripts/validate_skill.py` — frontmatter / line-count / link-integrity checks (JSON or text)
- `scripts/audit_skill.py` — wraps validate, adds editorial checks, writes Markdown report

## Dispatch

Inspect `$ARGUMENTS`. If the first token is missing or unrecognized, **stop and ask** the user which mode they want — do not silently default. Then jump to the matching section below.

| Mode | Section |
|---|---|
| `new` | [New Mode](#new-mode) |
| `audit` | [Audit Mode](#audit-mode) |
| `convert` | [Convert Mode](#convert-mode) |
| `troubleshoot` | [Troubleshoot Mode](#troubleshoot-mode) |
| `add-subagents` | [Add-Subagents Mode](#add-subagents-mode) |

---

## Core Principles (apply in every mode)

### Concise is key

The context window is a public good. Skills share it with system prompts, history, other skills' metadata, and the user request. **Default assumption: Claude is already very smart.** Only add context Claude does not already have. Challenge each piece: "Does Claude really need this?"

### Degrees of freedom

Match instruction specificity to fragility:

- **High freedom** (text instructions): multiple valid approaches, heuristic-driven.
- **Medium freedom** (pseudocode/scripts with parameters): a preferred pattern with some leeway.
- **Low freedom** (specific scripts, few parameters): fragile operations, consistency critical.

A narrow bridge with cliffs needs guardrails; an open field allows many routes.

### Three-level loading

1. **Metadata** (name + description, ~100 words) — always in context.
2. **SKILL.md body** (target <500 lines) — loaded when skill triggers.
3. **Bundled resources** — loaded as needed; scripts can execute without ever being read.

When SKILL.md approaches 500 lines, split content into `references/` and link with clear "when to read" guidance.

### Canonical directory layout

```
skill-name/
├── SKILL.md              # Required. Instructions
├── scripts/              # Executable code (token-efficient — output only loads)
├── references/           # Loaded only when needed; >100 lines → add ToC
└── assets/               # Templates, images, boilerplate used in output
```

---

## New Mode

Use when scaffolding a brand-new skill from scratch.

### 1. Capture intent

Ask the user (one focused round, not a barrage):

1. What concrete tasks should this skill enable?
2. Will it be invoked by command, by description matching, or both?
3. What inputs/outputs does it consume and produce?
4. Are there 1–2 example invocations you can describe right now?

If the user is mid-conversation with an obvious workflow already discussed, skip the questions and confirm the inferred answers.

### 2. Plan reusable contents

For each example, ask: what code, doc, or template would be rewritten every time?

- Code rewritten repeatedly → `scripts/`
- Doc Claude should consult → `references/`
- Boilerplate copied into output → `assets/`

### 3. Scaffold

```bash
~/.claude/skills/claudecode-skill-creating/scripts/init_skill.sh <name> [basic|advanced] [--scope user|project]
```

This creates the directory, copies the right template, and substitutes the name in frontmatter.

### 4. Implement resources first, SKILL.md last

Write `scripts/`, `references/`, and `assets/` before the SKILL.md prose. Test scripts by actually running them. Then write SKILL.md in the imperative form, referencing resources by relative path.

### 5. Validate

```bash
python3 ~/.claude/skills/claudecode-skill-creating/scripts/validate_skill.py <skill-path>
```

Fix every error before declaring done.

### 6. Iterate on real use

Use the skill on a real task. Notice where Claude struggles. Update SKILL.md or bundled resources. Re-validate.

---

## Audit Mode

Use when reviewing an existing skill for health, drift, or bloat.

### Procedure

1. Resolve the target path. If `$2` is a bare name, expand to `~/.claude/skills/$2`.
2. Run the audit script and capture both JSON (for parsing) and Markdown (for the user):
   ```bash
   mkdir -p ~/.claude/skills-audit/<skill-name>
   python3 ~/.claude/skills/claudecode-skill-creating/scripts/audit_skill.py <skill-path> \
     --report ~/.claude/skills-audit/<skill-name>/report.md
   ```
3. Read the report. For each finding above `info`, decide:
   - **Auto-fixable** (broken link, name regex violation, duplicate heading): propose a concrete `Edit` with old/new strings.
   - **Editorial** (description bloat, leaked trigger headings, orphan references): explain the impact and propose a rewrite.
4. Write a `recommendations.md` next to `report.md` listing the proposed edits in priority order. **Do not modify the audited skill until the user approves.**
5. After approval, apply the edits and re-run audit until no errors remain.

### What the audit checks

- **Validate-level** (errors block): missing SKILL.md, missing frontmatter, missing/invalid `name`, missing description, description >1024 chars, body >800 lines, broken relative links.
- **Editorial** (warnings/hints): trigger-style headings leaked into the body (`A001`), duplicate headings (`A002`), orphan references files (`A003`), still-pure auto-trigger framing in description (`A005`).

---

## Convert Mode

Use when turning an existing markdown doc, runbook, or note into a skill.

1. Read the source document end-to-end first; do not start writing until you understand it.
2. Decide if the result should be one SKILL.md or SKILL.md + `references/`. Rule of thumb: source >300 lines → split.
3. Run `init_skill.sh` to scaffold, then move source content into `references/` if splitting.
4. Write a fresh SKILL.md that **dispatches** rather than duplicates: it should describe inputs, outputs, and when to read each reference, not restate them.
5. Run `validate_skill.py`. Then run a single dry-run invocation against a realistic prompt and refine.

---

## Troubleshoot Mode

Use when an existing skill isn't behaving as expected.

### Triage sequence

1. **Run the validator first** (`validate_skill.py --json`). Most "skill is broken" reports turn out to be a missing field, name regex violation, or broken link.
2. **Frontmatter sanity:** confirm `name` matches the directory, description is non-empty and ≤1024 chars, no Tier 2 fields are misspelled.
3. **Activation issues** (only relevant if the skill is *also* expected to auto-trigger):
   - Description must contain the trigger keywords; the body is loaded only after activation.
   - If the user is invoking by command, activation isn't the problem — focus on Tier 2 fields and tool permissions.
4. **Tool permissions:** the Skill tool is denied by default. Confirm `.claude/settings.json` has:
   ```json
   { "permissions": { "allow": ["Skill(*)"] } }
   ```
5. **Subagent / fork issues:** see [references/orchestration-patterns.md](references/orchestration-patterns.md) — the most common failure is `context: fork` on a Reference-Contents skill (no explicit task → forked agent has nothing to do).

For deeper diagnosis flowcharts, load [references/troubleshooting.md](references/troubleshooting.md).

---

## Add-Subagents Mode

Use when an existing skill has grown into a multi-phase pipeline and needs internal sub-agents.

**Reach for orchestration patterns when at least one is true:**

- The work has multiple independent angles that can run in parallel.
- A single main-context pass would burn too much context just reading checklists.
- The skill is one node in a pipeline (intake → design → review → implement → test → ship), reading and writing structured files.
- Different "lenses" need different specialty checklists, and merging the results is the whole point.

**Structural rule that keeps these skills sane:** parallelism happens **inside** a phase; phases run in **strict sequence**; sub-agents **never talk to each other** — the main agent joins their results between phases.

### Required reading

- [references/orchestration-patterns.md](references/orchestration-patterns.md) — A1–A5 subagent invocation patterns and B1–B3 phase handoff patterns, with concrete prompt templates and anti-patterns.
- [references/workspace-conventions.md](references/workspace-conventions.md) — deterministic output paths from `$ARGUMENTS`, input/output contracts, snapshot/restore for destructive ops, idempotent re-runs.
- [examples/5-multi-phase-skill/](examples/5-multi-phase-skill/) — minimal worked example: 2 specialist sub-agents in parallel, each primed with a numbered checklist, writing to a deterministic workspace.

### Companion conventions

Covered in [references/patterns-and-structure.md](references/patterns-and-structure.md):

- Numbered checklist references (e.g., `LB1`–`LB8`) so sub-agents return findings as `LB3 FAIL: …` and the main agent merges mechanically.
- Templates as either **scaffold** (clone-and-fill) or **reference guide** (consult-while-writing) — declare which in SKILL.md.
- Cross-skill reference reuse: small "map" skills whose `references/` are read by other skills' sub-agents as bootstrap material.

---

## What NOT to put in a skill

- `README.md`, `INSTALLATION_GUIDE.md`, `QUICK_REFERENCE.md`, `CHANGELOG.md` — use git history.
- Auxiliary docs about the creation process or user-facing setup.
- Explanations of concepts Claude already knows (programming basics, common libraries).
- "When to Use" sections in the SKILL.md body — that information must live in the description field if you also want auto-triggering.

## Production patterns worth copying

### QA as bug hunting

From Anthropic's PPTX skill: *"Assume there are problems. Your job is to find them. Your first render is almost never correct. Approach QA as a bug hunt, not a confirmation step."*

### Sub-agent review

*"USE SUBAGENTS — even for 2-3 items. You have been staring at the code and will see what you expect, not what is there. Subagents have fresh eyes."*

### Critical Rules section

For fragile operations (OOXML, complex formats), add a prescriptive "Critical Rules" block at the bottom of SKILL.md listing exact constraints that must never be violated.

---

## References

Load on demand:

- [references/yaml-spec.md](references/yaml-spec.md) — full YAML field reference (Tier 1 + Tier 2), description best practices, regex rules.
- [references/patterns-and-structure.md](references/patterns-and-structure.md) — directory patterns, Skills vs Slash Commands comparison, token efficiency, content type classification, scaffold-vs-guide templates.
- [references/orchestration-patterns.md](references/orchestration-patterns.md) — subagent invocation and phase handoff patterns (load when building add-subagents skills).
- [references/workspace-conventions.md](references/workspace-conventions.md) — deterministic output paths, input/output contracts, snapshot/restore.
- [references/scripts-guide.md](references/scripts-guide.md) — when and how to use scripts, including absolute-path invocation and dry-run/json modes.
- [references/troubleshooting.md](references/troubleshooting.md) — diagnostic flowcharts for common issues.

## Templates

- [assets/basic-skill-template.md](assets/basic-skill-template.md) — single-file skills.
- [assets/advanced-skill-template.md](assets/advanced-skill-template.md) — skills with bundled resources.

## Examples

1. [Simple Skill](examples/1-simple-skill/) — basic structure
2. [Skill with References](examples/2-skill-with-references/) — progressive disclosure
3. [Skill with Scripts](examples/3-skill-with-scripts/) — Python and shell scripts
4. [Tool-Restricted Skill](examples/4-tool-restricted-skill/) — read-only with `allowed-tools`
5. [Multi-Phase Skill](examples/5-multi-phase-skill/) — phased workflow with parallel sub-agents and deterministic workspace

---

## Hard rules

- **Never** put "When to Use" sections in the SKILL.md body — they belong in the description field.
- **Never** include README/CHANGELOG/setup docs in the skill directory.
- **Never** create monolithic SKILL.md files >500 lines without splitting.
- **Never** use `context: fork` on a Reference-Contents skill (no task → forked agent fails silently).
- **Never** confuse `disable-model-invocation: true` (user-only) with `user-invocable: false` (Claude-only).
- **Always** run `validate_skill.py` before declaring a skill done.
- **Always** invoke bundled scripts with absolute paths.
- **Always** ask which mode is intended if `$ARGUMENTS` is empty or unrecognized.
