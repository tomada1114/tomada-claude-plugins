---
name: claudecode-skill-creating
description: "Create, audit, refactor, convert, or troubleshoot Claude Code skills. Takes a free-form natural-language request describing what the user wants done — e.g. \"I want to build a new skill\" / \"audit this skill\" / \"turn this doc into a skill\" / \"it never fires\" / \"split this into sub-agents\" — optionally followed by a skill name or absolute path."
argument-hint: "<free-form intent> [skill-name-or-path]"
---

# claudecode-skill-creating

Workshop for building and maintaining Claude Code skills.

`$ARGUMENTS` is **free-form text**, in any language. There is no mode keyword to parse. Read the user's intent, optionally pick out a skill name or path token, then jump to the matching playbook below. If the request mixes goals (e.g. "audit it, and fix whatever is broken"), chain playbooks in the order implied by the request.

## Contract

**Input:** free-form natural-language description of the task, optionally including a skill name or absolute path. No fixed positional parameters.

**Outputs depend on the inferred task:**
- Scaffolding a new skill → directory at `~/.claude/skills/<name>/` (or `<cwd>/.claude/skills/<name>/` with `--scope project`).
- Auditing → Markdown report at `~/.claude/skills-audit/<skill-name>/report.md`.
- Converting an existing doc → same layout as scaffolding.
- Troubleshooting → diagnosis (and optional fix patches) printed in chat.
- Adding sub-agents → edited SKILL.md + new sub-agent files.

**Bundled scripts** (invoke through `${CLAUDE_SKILL_DIR}`, never a hardcoded `~/.claude/skills/...` path):
- `scripts/init_skill.sh` — scaffold new skill from template
- `scripts/validate_skill.py` — frontmatter / line-count / link-integrity checks (JSON or text)
- `scripts/audit_skill.py` — wraps validate, adds editorial checks, writes Markdown report

## Intent inference

Match signals in `$ARGUMENTS` to a playbook — match on meaning, not wording; the request often arrives in Japanese. If genuinely ambiguous, ask one short clarifying question; otherwise proceed on the most likely interpretation.

| Signal in the request | Playbook |
|---|---|
| build / new / scaffold / from scratch / "I want a skill that…" | [Scaffolding a new skill](#scaffolding-a-new-skill) |
| audit / health check / review / "see if it is broken" | [Auditing an existing skill](#auditing-an-existing-skill) |
| convert / "turn this doc into a skill" / "make this Markdown a skill" | [Converting an existing doc into a skill](#converting-an-existing-doc-into-a-skill) |
| does not work / never fires / not triggering / frontmatter looks wrong / broken links | [Troubleshooting an existing skill](#troubleshooting-an-existing-skill) |
| sub-agents / parallel / multi-phase / orchestration / "split this skill up" | [Adding sub-agents to a skill](#adding-sub-agents-to-a-skill) |

If a token in the input matches an existing skill name or `~/.claude/skills/...` path, treat it as the target. Otherwise infer or ask.

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

## Scaffolding a new skill

Use when the user wants to build a brand-new skill from scratch.

### 1. Capture intent

Ask the user (one focused round, not a barrage):

1. What concrete tasks should this skill enable?
2. Will it be invoked by command, by description matching, or both?
3. What inputs/outputs does it consume and produce?
4. Are there 1–2 example invocations you can describe right now?

If the user is mid-conversation with an obvious workflow already discussed, skip the questions and confirm the inferred answers.

### 2. Name the gap before writing anything

For each example invocation, state what Claude does **without** the skill and where that falls short. That gap list is the skill's actual spec — everything else is documentation of behavior the model already had.

Turn it into three concrete test prompts with checkable expected behavior. Writing them now takes a minute and is what keeps the skill from doubling in size later; see [references/evaluating-skills.md](references/evaluating-skills.md) for the format.

If a candidate instruction doesn't map to a gap, don't write it.

### 3. Plan reusable contents

For each example, ask: what code, doc, or template would be rewritten every time?

- Code rewritten repeatedly → `scripts/`
- Doc Claude should consult → `references/`
- Boilerplate copied into output → `assets/`

### 4. Scaffold

```bash
${CLAUDE_SKILL_DIR}/scripts/init_skill.sh <name> [basic|advanced] [--scope user|project]
```

This creates the directory, copies the right template, and substitutes the name in frontmatter.

### 5. Implement resources first, SKILL.md last

Write `scripts/`, `references/`, and `assets/` before the SKILL.md prose. Test scripts by actually running them. Then write SKILL.md in the imperative form.

Push anything deterministic into `scripts/` rather than describing it in prose — script source never enters the context window, only its output. This is also what keeps a skill from becoming over-prescriptive: the fragile mechanics live in code, so the prose can state goals and constraints and leave the route open. Apply [references/prompt-authoring.md](references/prompt-authoring.md) while writing the prose.

Two path forms, and they are not interchangeable: **markdown links** to bundled files use relative paths (`references/foo.md`) so the validator can resolve them; **commands and sub-agent prompts** use `${CLAUDE_SKILL_DIR}/...`, which expands to an absolute path before the model sees it.

### 6. Validate

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/validate_skill.py <skill-path>
```

Fix every error before declaring done.

### 7. Check against the gap list

Run the three prompts from step 2 in a fresh session with the skill loaded. Two failure modes to separate: the skill didn't activate (a `description` problem) versus it activated and the output was still wrong (a body problem). Delete any instruction that covers behavior the no-skill baseline already got right.

For repeatable measurement — pass rates, token cost, blind A/B between versions — see [references/evaluating-skills.md](references/evaluating-skills.md).

---

## Auditing an existing skill

Use when reviewing an existing skill for health, drift, or bloat.

### Procedure

1. Resolve the target path. If the user gave a bare skill name, expand to `~/.claude/skills/<name>`.
2. Run the audit script and capture both JSON (for parsing) and Markdown (for the user):
   ```bash
   mkdir -p ~/.claude/skills-audit/<skill-name>
   python3 ${CLAUDE_SKILL_DIR}/scripts/audit_skill.py <skill-path> \
     --report ~/.claude/skills-audit/<skill-name>/report.md
   ```
3. Read the report. For each finding above `info`, decide:
   - **Auto-fixable** (broken link, name regex violation, duplicate heading): propose a concrete `Edit` with old/new strings.
   - **Editorial** (description bloat, leaked trigger headings, orphan references): explain the impact and propose a rewrite.
4. Write a `recommendations.md` next to `report.md` listing the proposed edits in priority order. **Do not modify the audited skill until the user approves.**
5. After approval, apply the edits and re-run audit until no errors remain.

### What the audit checks

- **Validate-level** (errors block): missing SKILL.md, missing frontmatter, missing/invalid `name`, missing description, description >1024 chars, body >800 lines, broken relative links.
- **Editorial** (warnings/hints): trigger-style headings leaked into the body (`A001`), duplicate headings (`A002`), orphan references files (`A003`), still-pure auto-trigger framing in description (`A005`), legacy prompt phrasings in SKILL.md or `references/` (`A006`), a references file linking to another references file (`A007`), a references file over 100 lines with no table of contents (`A008`).

`A006` is a hint, not a verdict — it pattern-matches wording and cannot read intent. Confirm each hit against [references/prompt-authoring.md](references/prompt-authoring.md) before proposing a rewrite. A file that legitimately quotes these phrasings (a style guide, this skill's own references) can opt out with an `audit-ignore-file: A006` HTML comment in its first 5 lines; a single line opts out with an `audit-ignore: A006` comment on that line.

The script cannot see prescriptiveness, missing intent, or unassigned sub-agent models. After the script pass, read the skill against the self-check list at the end of `prompt-authoring.md` and the [Content rules](#content-rules) above.

Findings a script also can't produce, worth checking by hand on any audit:

- **Hardcoded `~/.claude/skills/...` paths** in script invocations — breaks on plugin install and project checkout.
- **Instructions with no gap behind them.** For the two or three longest sections, ask what the model would do without them. If the answer is "the same thing", that's the highest-value deletion in the file.
- **Trigger accuracy.** If the complaint is "fires too often" or "never fires", that's the description, and it's measurable — see [references/evaluating-skills.md](references/evaluating-skills.md).

---

## Converting an existing doc into a skill

Use when turning an existing markdown doc, runbook, or note into a skill.

1. Read the source document end-to-end first; do not start writing until you understand it.
2. Decide if the result should be one SKILL.md or SKILL.md + `references/`. Rule of thumb: source >300 lines → split.
3. Run `init_skill.sh` to scaffold, then move source content into `references/` if splitting.
4. Write a fresh SKILL.md that **dispatches** rather than duplicates: it should describe inputs, outputs, and when to read each reference, not restate them.
5. Write the skill in English even when the source doc is Japanese. Keep the original wording only for material that must stay verbatim — quoted UI labels, error strings, command output, sample text the skill has to reproduce.
6. Cut what the model already knows. A doc written for humans explains concepts, motivates decisions, and repeats itself for readers who skipped a section — all of it dead weight here. The parts worth keeping are the ones a competent stranger to *this* system could not have guessed.
7. Run `validate_skill.py`, then one invocation against a realistic prompt, and refine.

---

## Troubleshooting an existing skill

Use when an existing skill isn't behaving as expected.

### Triage sequence

1. **Run the validator first** (`python3 ${CLAUDE_SKILL_DIR}/scripts/validate_skill.py <path> --json`). Most "skill is broken" reports turn out to be a missing field, name regex violation, or broken link.
2. **Does the frontmatter parse at all?** A malformed YAML block loads the body with *empty* metadata — `/skill-name` keeps working while Claude has no description to match, so nothing looks broken. `claude --debug` prints the parse error.
3. **Activation issues** (only relevant if the skill is *also* expected to auto-trigger). In order of frequency: trigger keywords in the body instead of the description → `disable-model-invocation: true` → a `paths` glob gating activation → description truncated out of the skill listing (`/doctor`).
4. **Invoked by command and still wrong?** Activation isn't the problem. Look at `allowed-tools` / `disallowed-tools`, `model` / `effort` overrides, and whether the body's load-bearing rule sits below the point where the model stopped reading.
5. **Subagent / fork issues:** see [references/orchestration-patterns.md](references/orchestration-patterns.md) — the most common failure is `context: fork` on a Reference-Contents skill (no explicit task → forked agent has nothing to do).

For deeper diagnosis flowcharts, load [references/troubleshooting.md](references/troubleshooting.md).

---

## Adding sub-agents to a skill

Use when an existing skill has grown into a multi-phase pipeline and needs internal sub-agents.

**Reach for orchestration patterns when at least one is true:**

- The work has multiple independent angles that can run in parallel.
- A single main-context pass would burn too much context just reading checklists.
- The skill is one node in a pipeline (intake → design → review → implement → test → ship), reading and writing structured files.
- Different "lenses" need different specialty checklists, and merging the results is the whole point.

**Not warranted when** the main agent could finish the work in a handful of tool calls, when the steps are sequential, or when the point is to re-check work the model already verifies itself. Current models delegate readily; an open-ended "use sub-agents when helpful" produces spawns for work a single grep would finish. State the bar and cap the count.

**Structural rule that keeps these skills sane:** parallelism happens **inside** a phase; phases run in **strict sequence**; sub-agents **never talk to each other** — the main agent joins their results between phases.

### Assign a model to every spawn

A skill that spawns sub-agents must say which model each one runs on, or the mechanical specialist and the hard one both run on whatever the session happens to be.

| Sub-agent's job | Model |
|---|---|
| Hard implementation, code review and bug-finding, synthesizing scattered findings, anything with unresolved spec | `opus` |
| Fully specified work with a clear pass/fail: run tests, add coverage, make CI green, commit, open a PR, bulk replace | `sonnet` |
| Enumerating, formatting, judgment-free greps | `haiku` |

The dividing line is **spec completeness, not size**. If the sub-agent could plausibly come back asking what you meant, it needed `opus`. Do not use the frontmatter `model:` field for this — that sets the model for the skill's own turn. See [references/prompt-authoring.md](references/prompt-authoring.md#assigning-models-and-effort).

This table is a derived copy of the canonical one in the `orchestrating-models` skill (§2). When the two disagree, that skill wins — revise there first, then propagate here. Skills authored with this table bake the conclusions in (with a one-line rationale), rather than referencing `orchestrating-models` at runtime. <!-- derived from orchestrating-models §2 -->

### Required reading

- [references/prompt-authoring.md](references/prompt-authoring.md) — the five layers every sub-agent prompt needs, model and effort assignment, and the phrasings to keep out of spawn prompts.
- [references/orchestration-patterns.md](references/orchestration-patterns.md) — A1–A6 subagent invocation patterns and B1–B3 phase handoff patterns, with concrete prompt templates and anti-patterns.
- [references/workspace-conventions.md](references/workspace-conventions.md) — deterministic output paths from `$ARGUMENTS`, input/output contracts, snapshot/restore for destructive ops, idempotent re-runs.
- [examples/pr-review-pipeline/](examples/pr-review-pipeline/) — minimal worked example: 2 specialist sub-agents in parallel, each primed with a numbered checklist and an explicit model assignment, writing to a deterministic workspace.

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

- **QA as bug hunting** (from Anthropic's PPTX skill): assume problems exist and hunt for them — QA is a bug hunt, not a confirmation step. First renders are almost never correct. Frame the finding step as coverage and put filtering in a later phase, so the model doesn't suppress findings it judges minor.
- **Fresh-context verification, for long runs only**: on autonomous runs that stretch across many phases, a separate sub-agent checking the work against the spec beats self-critique, because drift accumulates. On a scoped task it is waste — the model verifies its own work by default, and instructing it again causes over-verification. Set an interval rather than a per-task rule.
- **Critical Rules section**: for fragile operations (OOXML, complex formats), add a prescriptive "Critical Rules" block at the bottom of SKILL.md listing exact constraints that must never be violated. Keep the block scoped to what is genuinely fragile; prescriptiveness elsewhere costs quality.

---

## Resources

Load on demand:
- [references/prompt-authoring.md](references/prompt-authoring.md) — how to word skill prose and sub-agent prompts for current models: legacy phrasings to remove, sub-agent prompt layers, model and effort assignment, prescriptiveness budget.
- [references/yaml-spec.md](references/yaml-spec.md) — every frontmatter field (Agent Skills standard + Claude Code extensions), description budget and truncation rules, `$ARGUMENTS` / `${CLAUDE_SKILL_DIR}` substitutions, bash injection.
- [references/evaluating-skills.md](references/evaluating-skills.md) — eval-driven authoring, baseline comparison, eval case format, the skill-creator plugin, what to watch when Claude navigates a skill.
- [references/patterns-and-structure.md](references/patterns-and-structure.md) — content type classification (Reference vs Task), Skills vs Slash Commands, storage locations, numbered-checklist references, scaffold-vs-guide templates, workflow shapes, tool restrictions.
- [references/orchestration-patterns.md](references/orchestration-patterns.md) — subagent invocation and phase handoff patterns (load when building add-subagents skills).
- [references/workspace-conventions.md](references/workspace-conventions.md) — deterministic output paths, input/output contracts, snapshot/restore.
- [references/scripts-guide.md](references/scripts-guide.md) — when and how to use scripts, including absolute-path invocation and dry-run/json modes.
- [references/troubleshooting.md](references/troubleshooting.md) — diagnostic flowcharts for common issues.

Templates: [assets/basic-skill-template.md](assets/basic-skill-template.md) (single-file skills), [assets/advanced-skill-template.md](assets/advanced-skill-template.md) (skills with bundled resources).

Examples: [greeting-generator](examples/greeting-generator/) (single-file skill) · [http-status-guide](examples/http-status-guide/) (progressive disclosure into `references/`) · [project-validator](examples/project-validator/) (bundled scripts) · [code-analyzer](examples/code-analyzer/) (`allowed-tools` vs `disallowed-tools`) · [pr-review-pipeline](examples/pr-review-pipeline/) (phased workflow with parallel sub-agents and deterministic workspace)

---

## Hard rules

- **Never** confuse `disable-model-invocation: true` (user-only) with `user-invocable: false` (Claude-only).
- **Always** run `validate_skill.py` before declaring a skill done.
- **Always** reference bundled scripts as `${CLAUDE_SKILL_DIR}/scripts/...`. A hardcoded `~/.claude/skills/<name>/...` breaks on plugin install and project checkout, and runs the wrong copy when both exist. Absolute paths are correct only when calling *another* skill's script.
- **Always** infer intent from `$ARGUMENTS` rather than demanding a mode keyword. Ask one focused clarifying question only if the request is genuinely ambiguous.
- **Never** write an instruction telling the model to echo, transcribe, or explain its internal reasoning. On Fable this can trigger the `reasoning_extraction` refusal and force a fallback to an older model. Ask for evidence — citations, command output, the artifact — not for thinking.
- **Always** specify a model when a skill spawns a sub-agent.
- **Always** author skill content in English, and keep `description` English-only with no mirrored Japanese keywords. The exception is content whose subject *is* another language — see [English is the authoring language](#english-is-the-authoring-language).
