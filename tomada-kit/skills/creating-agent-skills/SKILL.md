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

**Input:** free-form natural-language description of the task, optionally including a skill name or absolute path. No fixed positional parameters.

**Outputs depend on the inferred task:**
- Building → directory at `~/.claude/skills/<name>/` (or `<cwd>/.claude/skills/<name>/` with `--scope project`). Claude Code reads this natively; run `dual-platform-skills` afterward to bridge the same skill onto Codex (Topology A — the real files stay under `.claude/skills/`, Codex reaches them via symlink). <!-- neutrality-ignore: N2 -->
- Improving → `${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/skills-audit/<skill-name>/` holding `report.md` (script pass), `lens-<name>.md` (one per lens), `recommendations.md` (merged, prioritized). Edits to the skill itself only after the user approves.

**Bundled scripts** (invoke through `${CLAUDE_SKILL_DIR}`, never a hardcoded `~/.claude/skills/...` path): <!-- neutrality-ignore: N2 -->
- `scripts/init_skill.sh` — scaffold new skill from template
- `scripts/validate_skill.py` — frontmatter / line-count / link-integrity / neutrality (N1–N4) checks, `--json`
- `scripts/audit_skill.py` — wraps validate, adds editorial checks A001–A009, emits a `profile` block in `--json`, writes a Markdown report
- `scripts/check_scripts.py` — for skills with `scripts/`: test presence, test run, coverage ≥ 90 %, shebang/exec bit, hardcoded personal paths, `.gitignore` coverage (S001–S007), `--json`

## Intent inference

Match signals in `$ARGUMENTS` to a playbook — match on meaning, not wording; the request often arrives in Japanese. If genuinely ambiguous, ask one short clarifying question; otherwise proceed on the most likely interpretation.

| Signal in the request | Playbook |
|---|---|
| build / new / scaffold / from scratch / convert / "turn this doc into a skill" / "I want a skill that…" | [Building a skill](#building-a-skill) |
| audit / review / health check / refactor / slim down / "never fires" / "fires too often" / sub-agents / parallel / "split this up" | [Improving a skill](#improving-a-skill) |

If a token in the input matches an existing skill name or `~/.claude/skills/...` path, treat it as the target. Otherwise infer or ask. <!-- neutrality-ignore: N2 -->

If the request is both ("build it, then review it"), run Building to completion and then Improving.

---

## Core Principles (apply in every playbook)

### English is the authoring language

Write every part of a skill in English: `description`, SKILL.md body, `references/`, `assets/`, script comments, sub-agent prompts, and the user-facing text the skill instructs Claude to emit (questions, reports, summaries). This holds even when the request arrives in Japanese and even for skills only tomada will ever run — these skills ship as plugins, and tomada uses them to keep reading English.

Descriptions are **English-only**, with no mirrored Japanese trigger keywords. A Japanese request still matches an English description; trigger vocabulary is matched on meaning, so pairing each English trigger with its Japanese equivalent buys nothing and costs the description budget that truncation eats first.

Use another language only where that language *is* the subject matter:

- the skill produces Japanese output (copy, release notes, mail drafts) — say so explicitly in the body;
- a reference quotes Japanese source material, UI labels, or error strings verbatim;
- a pattern must match Japanese text (audit regexes, slug rules for Japanese `$ARGUMENTS`).

Existing Japanese skills are not retrofitted. Translate one only when the user asks, or when a playbook is already rewriting that file for another reason.

### Concise is key

The context window is a public good, shared with system prompts, history, other skills' metadata, and the user request. **Default assumption: Claude is already very smart.** Add only context it doesn't already have — challenge each piece with "does Claude really need this?"

### A skill is a prompt

Structure decides *when* text reaches the model; wording decides whether it helps once it gets there. Several instructions that were load-bearing for earlier models are now neutral or harmful — forced re-verification, severity self-filtering in review steps, requests to echo reasoning. Before writing or approving skill prose, read [references/prompt-authoring.md](references/prompt-authoring.md).

The single most common defect in an older skill: instructions that restate behavior the model now has by default. They are not free — they crowd context and pull toward a worse-specified version of what would have happened anyway.

### Degrees of freedom

Match instruction specificity to fragility:

- **High freedom** (text instructions): multiple valid approaches, heuristic-driven.
- **Medium freedom** (pseudocode/scripts with parameters): a preferred pattern with some leeway.
- **Low freedom** (specific scripts, few parameters): fragile operations, consistency critical.

A narrow bridge with cliffs needs guardrails; an open field allows many routes.

### Deterministic work belongs in scripts

Any step whose result would be identical on every run — enumerating files, counting, validating structure, converting formats, applying a rule table, running tests — is a script, not prose. A script is faster, costs no context for its source, and can be tested; prose describing the same procedure is re-derived by the model each time and drifts. Keep judgment in the prose: what the numbers mean, what to do about a failure, which of several valid routes to take.

Scripts follow the conventions in [references/scripts-guide.md](references/scripts-guide.md#conventions): `scripts/` + `scripts/tests/test_<name>.py`, `--json` for anything an agent parses, exit codes 0/1/2, one responsibility per script, stdlib first with other dependencies declared in SKILL.md, test coverage ≥ 90 %, and generated files (`__pycache__/`, `.pytest_cache/`, `.coverage*`) in `.gitignore`. `scripts/check_scripts.py` enforces the checkable parts.

### Three-level loading

1. **Metadata** (name + description, ~100 words) — always in context.
2. **SKILL.md body** (target <500 lines; the validator warns at 500 and errors at 800) — loaded when skill triggers.
3. **Bundled resources** — loaded as needed; scripts can execute without ever being read.

As SKILL.md approaches that target, split content into `references/` and link with clear "when to read" guidance. Once loaded, the body stays in context across turns — every line is a recurring cost, not a one-time one.

### Content rules

Cheap, mechanical, and each one fixes a real failure mode:

- **References one level deep from SKILL.md.** A reference that links to another reference gets previewed with `head`, not read — the model then acts on half the file.
- **Table of contents in any reference over 100 lines**, so a partial read still shows the full scope.
- **Forward slashes everywhere**, on every platform.
- **One default, not a menu.** "Use pdfplumber" beats "you could use pypdf, pdfplumber, or PyMuPDF". Give the escape hatch only where it's real: "for scanned PDFs, use pdf2image with pytesseract instead".
- **One term per concept.** Mixing "field"/"box"/"element" for the same thing makes instructions ambiguous to a literal reader.
- **No time-sensitive statements.** "Before August 2026, use the old API" rots. Put superseded material under an "Old patterns" heading instead.
- **MCP tools fully qualified** — `ServerName:tool_name`, or resolution fails when several servers are connected.
- **Name dependencies explicitly.** Don't assume a package is installed.

### Canonical directory layout

```
skill-name/
├── SKILL.md              # Required. Instructions
├── scripts/              # Executable code (token-efficient — output only loads)
├── references/           # Loaded only when needed; >100 lines → add ToC
└── assets/               # Templates, images, boilerplate used in output
```

---

## Building a skill

Use when the user wants a new skill — from scratch, or from an existing markdown doc, runbook, or note.

### 1. Capture intent

**If a source document exists, read it end-to-end before asking anything** — the questions below are answered by the doc more often than not; confirm the inferred answers instead of asking.

Ask the user (one focused round, not a barrage):

1. What concrete tasks should this skill enable?
2. Will it be invoked by command, by description matching, or both?
3. What inputs/outputs does it consume and produce?
4. Are there 1–2 example invocations you can describe right now?
5. Should this skill run on Codex CLI too, or is its subject Claude Code itself? (default: both)

If the user is mid-conversation with an obvious workflow already discussed, skip the questions and confirm the inferred answers.

**Settle platform scope in the same round.** Default to `metadata.platforms: claude-code, codex` — ask the user only when the skill's actual subject might be Claude Code itself. This decides how the body must be worded, so it cannot wait until step 6's validator; read [references/agent-neutral-authoring.md](references/agent-neutral-authoring.md) before writing prose.

### 2. Name the gap before writing anything

For each example invocation, state what Claude does **without** the skill and where that falls short. That gap list is the skill's actual spec — everything else is documentation of behavior the model already had.

Turn it into three concrete test prompts with checkable expected behavior. Writing them now takes a minute and is what keeps the skill from doubling in size later; see [references/evaluating-skills.md](references/evaluating-skills.md) for the format.

If a candidate instruction doesn't map to a gap, don't write it.

### 3. Plan reusable contents

For each example, ask: what code, doc, or template would be rewritten every time?

- Code rewritten repeatedly → `scripts/`
- Doc Claude should consult → `references/`
- Boilerplate copied into output → `assets/`

Apply the deterministic-work rule above: anything on the candidate list that is a procedure with one right answer goes to `scripts/`, with a test. From a source doc: if it exceeds ~300 lines, the body of it goes under `references/` split by concern and SKILL.md dispatches to it; cut what the model already knows — a doc written for humans explains concepts, motivates decisions, and repeats itself, all of it dead weight here. Keep only what a competent stranger to *this* system could not have guessed.

### 4. Scaffold

```bash
${CLAUDE_SKILL_DIR}/scripts/init_skill.sh <name> [basic|advanced] [--scope user|project]
```

This creates the directory, copies the right template, and substitutes the name in frontmatter.

### 5. Implement resources first, SKILL.md last

Write `scripts/`, `references/`, and `assets/` before the SKILL.md prose. Test scripts by actually running them. Then write SKILL.md in the imperative form.

Push anything deterministic into `scripts/` rather than describing it in prose — script source never enters the context window, only its output. This is also what keeps a skill from becoming over-prescriptive: the fragile mechanics live in code, so the prose can state goals and constraints and leave the route open. Apply [references/prompt-authoring.md](references/prompt-authoring.md) while writing the prose.

If step 1 settled `platforms: claude-code, codex` (the default), read [references/agent-neutral-authoring.md](references/agent-neutral-authoring.md) before writing the prose — write what the model should *do*, not which tool does it. Step 6's linter only catches what this step missed; it is a backstop, not where neutrality gets decided.

Omit `allowed-tools` from frontmatter unless one of the two reasons in [yaml-spec.md](references/yaml-spec.md#allowed-tools) applies — pre-approving this skill's own bundled scripts, or an unattended/background run that must not stall on a permission prompt.

Two path forms, and they are not interchangeable: **markdown links** to bundled files use relative paths (`references/foo.md`) so the validator can resolve them; **commands and sub-agent prompts** use `${CLAUDE_SKILL_DIR}/...`, which expands to an absolute path before the model sees it.

If the skill delegates work to fresh contexts, name a model for every spawn by spec completeness (table in [prompt-authoring.md](references/prompt-authoring.md#assigning-models-and-effort)), keep the delegation prompts in `references/agents/<name>.md`, and state the bar and the cap for delegation in the body — the patterns and their limits are in [references/orchestration-patterns.md](references/orchestration-patterns.md).

From a source doc: write in English even when the source is Japanese; keep the original wording only for material that must stay verbatim — quoted UI labels, error strings, command output, sample text the skill has to reproduce.

### 6. Validate

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/validate_skill.py <skill-path>
python3 ${CLAUDE_SKILL_DIR}/scripts/check_scripts.py <skill-path>   # only if the skill has scripts/
```

Fix every error before declaring done. This includes the neutrality lint it runs internally — a real error here means step 5's guidance was skipped or missed, not a substitute for reading it. `check_scripts.py` fails on failing tests and warns below 90 % coverage; both are done-criteria, not advice.

### 7. Check against the gap list

Run the three prompts from step 2 in a fresh session with the skill loaded. Two failure modes to separate: the skill didn't activate (a `description` problem) versus it activated and the output was still wrong (a body problem). Delete any instruction that covers behavior the no-skill baseline already got right.

For repeatable measurement — pass rates, token cost, blind A/B between versions — see [references/evaluating-skills.md](references/evaluating-skills.md).

---

## Improving a skill

Use when reviewing an existing skill for health, drift, bloat, trigger accuracy, or to restructure it — including splitting it into phases or sub-agents. One agent reading for every concern at once misses things, so the review is split into lenses that run in fresh contexts and are merged afterwards.

### P0. Script pass (deterministic)

1. Resolve the target path. A bare skill name expands to `~/.claude/skills/<name>`. <!-- neutrality-ignore: N2 -->
2. Run the scripts and keep both the JSON (for P1/P2) and the Markdown report (for the user):
   ```bash
   AUDIT_DIR="${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/skills-audit/<skill-name>"
   mkdir -p "$AUDIT_DIR"
   python3 ${CLAUDE_SKILL_DIR}/scripts/audit_skill.py <skill-path> --json --report "$AUDIT_DIR/report.md" > "$AUDIT_DIR/audit.json"
   python3 ${CLAUDE_SKILL_DIR}/scripts/check_scripts.py <skill-path> --json > "$AUDIT_DIR/scripts.json"   # only if scripts/ exists
   ```
3. Read the `profile` block of `audit.json` — body lines, reference count, whether `scripts/` and tests exist, whether the skill spawns sub-agents or has phases, declared platforms. It decides the lens set below.

What the scripts already cover, so the lenses do not repeat it: frontmatter validity, name rules, description length and listing truncation, body and code-block size, broken and escaping links (E/W codes); trigger headings in the body, duplicate headings, orphan references, reference-to-reference links, missing ToC, Japanese frontmatter, legacy phrasings as a hint (A001–A009); raw tool names and platform paths in body text, missing `metadata.platforms` (N1–N4); test presence, test results, coverage, shebang, hardcoded paths, `.gitignore` (S001–S007).

### P1. Lenses (parallel, fresh context each)

Each lens reads one reference's "Review checklist" and reports against its item IDs. Fill [references/agents/review-lens.md](references/agents/review-lens.md) once per lens and run them in parallel where the environment supports it; otherwise work through them one at a time, in table order, in the same fresh-context discipline (read the checklist first, then the skill). Write each result to `$AUDIT_DIR/lens-<name>.md`.

| Lens | Checklist | Looks for (what the scripts cannot see) | Model | Runs when |
|---|---|---|---|---|
| prose | [references/prompt-authoring.md](references/prompt-authoring.md#review-checklist) (`PA`) | instructions with no gap behind them, over-prescription, legacy phrasings in context, implicit scope | `opus` | always |
| neutrality | [references/agent-neutral-authoring.md](references/agent-neutral-authoring.md#review-checklist) (`AN`) | hollow `platforms` declarations, paraphrased tool use the regex misses, inline sub-agent prompts, relative paths handed to sub-agents, state-dir convention | `sonnet` | always |
| structure | [references/patterns-and-structure.md](references/patterns-and-structure.md#review-checklist) (`ST`) | SKILL.md duplicating instead of dispatching, missing "read when" guidance, description accuracy against what the body does, files that don't belong | `sonnet` | always |
| scripts | [references/scripts-guide.md](references/scripts-guide.md#review-checklist) (`SC`) | deterministic procedures written as prose, convention drift in existing scripts, what the test/coverage numbers mean | `sonnet` | `scripts/` exists, or SKILL.md has a code block |
| orchestration | [references/orchestration-patterns.md](references/orchestration-patterns.md#review-checklist) (`OR`) | model per spawn, the five prompt layers, phase discipline, and phases that *should* be delegated under the conditions in that file | `opus` | the skill spawns sub-agents, has phases, or body > 150 lines |

**Gate:** if SKILL.md is under 100 lines and the skill has neither `references/` nor `scripts/`, spawn nothing — run the always-on lenses inline yourself. A five-agent review of a 40-line skill is the over-delegation this skill warns other skills about. Never spawn more than the five lenses above; if a lens needs more than one pass, that is a sign the skill should be split, which is itself a finding.

Lens prompts ask for full coverage with confidence and severity attached. Filtering happens in P2, not in the lens — a lens told to report only what matters investigates just as deeply and then hides findings.

### P2. Merge and propose

1. Deduplicate by checklist ID and location; where two lenses disagree, keep both readings and mark the item unresolved.
2. Rank: blocks the skill from working → misleads the model → costs context for nothing → cosmetic.
3. Write `$AUDIT_DIR/recommendations.md`: one entry per proposed change with the ID, the evidence (file:line), the old → new text where it is concrete, and the cost of not doing it. Auto-fixable items (broken link, name regex, duplicate heading) come first as ready-to-apply edits; editorial items explain impact.
4. **Orchestration proposals** — when a lens or your own reading shows a phase of the audited skill that meets one of these, propose delegating it:
   - two or more independent angles, each needing its own checklist or reference of 100+ lines;
   - a phase that reads many files whose contents are not needed afterwards (context isolation);
   - the skill is one node in a pipeline reading and writing structured files;
   - an autonomous run spanning many phases, where drift makes a fresh-context verifier at an interval worthwhile.
   Each proposal names the condition it meets, the model per spawn (`opus` where the sub-agent could come back asking what you meant; `sonnet` for fully specified pass/fail work; `haiku` for judgment-free enumeration), the five prompt layers, and a spawn cap. **Limits:** at most one proposal per phase and three per skill. Do not propose delegation for work the main agent finishes in a handful of tool calls, for strictly sequential steps, or for re-checking work the model already verifies — and say so when a lens suggested it anyway.
5. Present the recommendations and stop. **Do not modify the audited skill until the user approves.**

### P3. Apply and re-run the script pass

Apply the approved edits, then re-run P0. Repeat until no errors remain and the approved items are closed. If a change touched `scripts/`, the tests and coverage in `check_scripts.py` are part of "no errors".

---

## What NOT to put in a skill

- `README.md`, `INSTALLATION_GUIDE.md`, `QUICK_REFERENCE.md`, `CHANGELOG.md` — use git history.
- Auxiliary docs about the creation process or user-facing setup.
- Explanations of concepts Claude already knows (programming basics, common libraries).
- "When to Use" sections in the SKILL.md body — that information must live in the description field if you also want auto-triggering.

## Production patterns worth copying

- **QA as bug hunting** (from Anthropic's PPTX skill): assume problems exist and hunt for them — QA is a bug hunt, not a confirmation step. First renders are almost never correct. Frame the finding step as coverage and put filtering in a later phase, so the model doesn't suppress findings it judges minor.
- **Fresh-context verification, for long runs only**: on autonomous runs that stretch across many phases, a separate sub-agent checking the work against the spec beats self-critique, because drift accumulates. On a scoped task it is waste — the model verifies its own work by default, and instructing it again causes over-verification. Set an interval rather than a per-task rule.
- **Critical Rules section**: for fragile operations (OOXML, complex formats), add a prescriptive "Critical Rules" block at the bottom of SKILL.md listing exact constraints that must never be violated. Keep the block scoped to what is genuinely fragile; prescriptiveness elsewhere costs quality.

---

## Resources

Load on demand:
- [references/agent-neutral-authoring.md](references/agent-neutral-authoring.md) — write once for both hosts; load whenever `platforms` includes `codex` (default). Holds the `AN` review checklist.
- [references/prompt-authoring.md](references/prompt-authoring.md) — wording for current models: legacy phrasings, sub-agent prompt layers, model and effort per spawn, prescriptiveness budget. Holds the `PA` review checklist.
- [references/yaml-spec.md](references/yaml-spec.md) — every frontmatter field, description budget and truncation, `$ARGUMENTS` / `${CLAUDE_SKILL_DIR}` substitutions, bash injection, and diagnosing a skill that never activates (`#diagnosing-activation`).
- [references/patterns-and-structure.md](references/patterns-and-structure.md) — content types, storage locations, numbered checklists, scaffold-vs-guide templates, workflow shapes, tool restrictions. Holds the `ST` review checklist.
- [references/scripts-guide.md](references/scripts-guide.md) — script-or-prose decision, script conventions, CLI contract, tests and coverage, patterns. Holds the `SC` review checklist.
- [references/orchestration-patterns.md](references/orchestration-patterns.md) — sub-agent invocation (A1–A6) and phase handoff (B1–B3) patterns, when to propose orchestration and its limits. Holds the `OR` review checklist.
- [references/workspace-conventions.md](references/workspace-conventions.md) — deterministic output paths, input/output contracts, snapshot/restore. Load for any skill that writes more than one file.
- [references/evaluating-skills.md](references/evaluating-skills.md) — eval-driven authoring, baseline comparison, should/should-not-trigger cases, the skill-creator plugin.
- [references/agents/review-lens.md](references/agents/review-lens.md) — the prompt template each Improving lens is filled from.

Templates: [assets/basic-skill-template.md](assets/basic-skill-template.md) (single-file skills), [assets/advanced-skill-template.md](assets/advanced-skill-template.md) (skills with bundled resources).

Examples: [greeting-generator](examples/greeting-generator/) (single-file skill) · [http-status-guide](examples/http-status-guide/) (progressive disclosure into `references/`) · [project-validator](examples/project-validator/) (bundled scripts) · [code-analyzer](examples/code-analyzer/) (`allowed-tools` vs `disallowed-tools`) · [pr-review-pipeline](examples/pr-review-pipeline/) (phased workflow with parallel sub-agents and deterministic workspace)

---

## Hard rules

- **Never** confuse `disable-model-invocation: true` (user-only) with `user-invocable: false` (Claude-only).
- **Always** run `validate_skill.py` (and `check_scripts.py` when the skill has `scripts/`) before declaring a skill done — the validator also runs the dual-platform neutrality lint.
- **Always** set `metadata.platforms` in frontmatter when scaffolding a new skill. Default to `claude-code, codex` and write the body agent-neutral unless the skill's actual subject is Claude Code itself (then declare `claude-code` only, deliberately — see [agent-neutral-authoring.md](references/agent-neutral-authoring.md)).
- **Always** reference bundled scripts as `${CLAUDE_SKILL_DIR}/scripts/...`. A hardcoded `~/.claude/skills/<name>/...` breaks on plugin install and project checkout, and runs the wrong copy when both exist. Absolute paths are correct only when calling *another* skill's script. <!-- neutrality-ignore: N2 -->
- **Always** infer intent from `$ARGUMENTS` rather than demanding a mode keyword. Ask one focused clarifying question only if the request is genuinely ambiguous.
- **Never** write an instruction telling the model to echo, transcribe, or explain its internal reasoning. On Fable this can trigger the `reasoning_extraction` refusal and force a fallback to an older model. Ask for evidence — citations, command output, the artifact — not for thinking.
- **Always** specify a model when a skill spawns a sub-agent.
- **Never** add `allowed-tools` without one of the two reasons in [yaml-spec.md](references/yaml-spec.md#allowed-tools) — pre-approving this skill's own bundled scripts, or an unattended/background run that must not stall on a permission prompt. Default is to omit the field.
- **Always** author skill content in English, and keep `description` English-only with no mirrored Japanese keywords. The exception is content whose subject *is* another language — see [English is the authoring language](#english-is-the-authoring-language).
- **Never** spawn review lenses for a skill under the P1 gate, and never more than the five lenses listed.
