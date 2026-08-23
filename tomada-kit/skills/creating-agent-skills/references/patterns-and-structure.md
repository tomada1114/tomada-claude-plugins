<!-- platform-annex -->
# Skills Structure and Patterns

This document covers directory structure, integration patterns, workflow patterns, and best practices for Claude Code skills.

## Table of Contents

- [Skill Content Types: Reference vs Task](#skill-content-types-reference-vs-task)
- [Skills vs Slash Commands](#skills-vs-slash-commands)
- [Three Storage Locations](#three-storage-locations)
- [Directory Structure](#directory-structure)
- [Sizing and slimming SKILL.md](#sizing-and-slimming-skillmd)
- [Subagent Integration](#subagent-integration)
- [References as Numbered Checklists](#references-as-numbered-checklists)
- [Templates: Scaffold vs Reference Guide](#templates-scaffold-vs-reference-guide)
- [Cross-Skill Reference Reuse](#cross-skill-reference-reuse)
- [Workflow and Output Patterns](#workflow-and-output-patterns)
  - [Checklist Workflow](#checklist-workflow)
  - [Feedback Loop](#feedback-loop)
- [One Skill = One Capability](#one-skill--one-capability)
- [Tool Restrictions](#tool-restrictions)
- [What the P0 script pass already covers](#what-the-p0-script-pass-already-covers)
- [Review checklist](#review-checklist)

---

## Skill Content Types: Reference vs Task

### Reference Contents

Knowledge-oriented skills providing context and guidelines. The **task is determined by the main agent**, not the skill. Like a passive buff -- always active in background.

Examples: coding conventions, domain terminology, architecture guidelines.

Best pattern: Subagent + `skills:` field.

```yaml
# .claude/agents/code-reviewer.md
---
name: code-reviewer
tools: Read, Grep, Glob
skills: coding-standards, security-guidelines
---
```

### Task Contents

Action-oriented skills defining specific tasks. The **task is defined within SKILL.md itself**. Runs autonomously.

Examples: "Open a PR with this format", "Build and run tests", "Generate changelog".

Best pattern: `context: fork`.

```yaml
# .claude/skills/pr-opener/SKILL.md
---
name: pr-opener
context: fork
---
## Task
1. Get current branch diff
2. Generate PR title and description
3. Create PR using gh CLI
```

### Choosing the Right Pattern

| Content Type | What Determines Task | Best Pattern | `context: fork` |
|--------------|---------------------|--------------|-----------------|
| Reference | Main agent decides | Subagent + `skills:` | Not recommended |
| Task | SKILL.md defines | `context: fork` | Recommended |

Warning: `context: fork` with Reference Contents fails because the forked context needs explicit task instructions, not just guidelines.

---

## Skills vs Slash Commands

Custom commands have been merged into skills. `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both produce `/deploy` and behave the same way; existing `commands/` files keep working.

What the skill form adds over a bare command file:

| Capability | `commands/*.md` | `skills/<name>/SKILL.md` |
|---|---|---|
| Bundled resources (`scripts/`, `references/`, `assets/`) | No | Yes |
| Automatic loading when relevant | No | Yes (via `description`) |
| Invocation control (`disable-model-invocation`, `user-invocable`) | No | Yes |
| Fork execution (`context: fork`, `agent`) | No | Yes |

Write new work as skills. A single-file command is fine for a one-liner you only ever type yourself, but converting later costs nothing, so the directory form is the safer default.

---

## Three Storage Locations

**1. Personal (`~/.claude/skills/`)** -- Available across all projects. Not shared with team. Use for personal preferences, experimental skills.

**2. Project (`.claude/skills/`)** -- Specific to one project, committed to git, shared with team. Use for team standards, project workflows.

**3. Plugin (`<plugin>/skills/<name>/SKILL.md`)** -- Distributed through a plugin marketplace, versioned, installed with `/plugin install`. Use for org-wide standards and anything shared beyond one repo. Plugin skills get a `/plugin-name:skill-name` command, are unaffected by `skillOverrides`, and are the reason bundled paths must use `${CLAUDE_SKILL_DIR}` rather than `~/.claude/skills/...`.

---

## Directory Structure

The canonical layout, the three loading levels, and the degrees-of-freedom scale are defined in SKILL.md's Core Principles. Two additions that only matter when reorganizing an existing skill:

**Migration from legacy structure:** if a skill uses flat files like `reference.md`, `examples.md`, `templates/`, or `docs/`, consolidate into `scripts/` + `references/` + `assets/` — documentation to `references/`, templates to `assets/`, utility code to `scripts/`.

**Organizing `references/`:** split by domain concern, not by file type, and say in SKILL.md when each file should be read. Conditional branches ("React project → read `react-patterns.md`") are fine as long as every reference stays one level deep from SKILL.md.

---

## Sizing and slimming SKILL.md

The numbers, stated once: SKILL.md body target ≤150 lines, warning above 200
(`W031`), error above 500 (`E030`, `validate_skill.py`'s enforced ceiling).
`references/*.md` warns above 400 lines (`A010`, `audit_skill.py`) — the same
budget applied one level down, so content pushed out of the body doesn't just
become a new monolith.

**Decision rule.** The body keeps the dispatch map (what routes to what),
the decision points (branches only the model needs to see every time), and
the hard rules. Everything else moves to `references/`:

- content only one branch of the skill's logic ever needs;
- rationale for *why* a rule exists, as opposed to the rule itself;
- a worked example, once the rule itself is stated;
- any single sub-topic running past roughly 15 lines in the body.

**Slimming an existing skill.** Read the body top to bottom and mark each
section against the four bullets above. For each marked section: create (or
extend) one `references/<topic>.md` scoped to a single domain concern — not a
dumping ground — move the content verbatim, add a Table of Contents if the
result exceeds 100 lines, and leave a one-line pointer in SKILL.md saying what
the reference holds and when to read it. Re-run `validate_skill.py` and
`audit_skill.py` after each move; `A010` catches a reference that grew past
400 lines and needs splitting again by concern rather than by file size alone.

A body sitting comfortably under 150 lines after this pass is not itself proof
the skill still does its job — check it against `evaluating-skills.md`'s gap
list (load via SKILL.md); a rule moved out of
the body is only safe to remove if nothing depended on the model seeing it on
every trigger.

---

## Subagent Integration

Sub-agent invocation and phase-handoff patterns (A1–A6, B1–B3) live in `orchestration-patterns.md` (load it via SKILL.md). Read it when a skill spawns specialists, runs parallel investigations in one phase, or is one node in a multi-skill pipeline; `workspace-conventions.md` covers the file contracts between those nodes.

The frontmatter choice — subagent + `skills:` for Reference Contents, `context: fork` (optionally with `agent:`) for Task Contents — decides *where* the work runs. It is independent of *how capable* the thing running it is: name a model on every spawn (A6 in `orchestration-patterns.md`, fuller treatment in `prompt-authoring.md`).

---

## References as Numbered Checklists

When a `references/` file is meant to be **applied** rather than just read (e.g., bug-pattern checklists, design-vs-reality validation, security audits), give every item a stable ID like `LB1`, `RB3`, `XL2`. The IDs let sub-agents return findings as `RB3 FAIL: <reason>` and let the main agent merge results from multiple sub-agents mechanically.

```markdown
# Backend Bug Patterns

## LB1: Missing tenant filter
A query that touches a multi-tenant table without filtering by `m_division_id`.
- How to verify: grep the query, check the WHERE clause.
- Severity: critical.

## LB2: N+1 in list endpoints
...
```

Why this works:
- Sub-agents have a stable vocabulary to report against.
- The main agent can deduplicate findings across sub-agents (`LB1` is `LB1` no matter who found it).
- The user can ask "what does LB3 mean?" and get a precise answer.
- New items append at the bottom without renumbering, so URLs/links stay stable.

A production review skill runs three such files side by side — backend bug patterns (`LB1`–`LB8`), frontend bug patterns (`RB1`–`RB8`), cross-layer parity patterns (`XL1`–`XLn`) — one per specialist lens.

In SKILL.md, list these checklist files in a "Reference Documents" TOC section near the top, with one-line descriptions. Sub-agent prompts then point to the absolute path of the relevant checklist as a bootstrap step (see A1 / A2 in `orchestration-patterns.md`).

---

## Templates: Scaffold vs Reference Guide

Templates in `assets/` (or `templates/`) come in two distinct flavors. SKILL.md must say which kind it is, because the workflow is different.

### Type 1: Scaffold (clone-and-fill)

A skeleton that gets **copied to the output directory** and filled in. Used by skills that produce a fixed set of artifacts.

```
<design-skill>/templates/
├── overview.md       ← copied to <workspace>/overview.md, then edited
├── backend.md
├── frontend.md
└── e2e-testcases.md
```

The template is mostly empty headings + section labels. The skill copies it verbatim and then fills the body.

### Type 2: Reference Guide (consult-while-writing)

A structural guide that is **read** for orientation but **never copied**. Used by skills that produce free-form output where the template informs structure rather than dictating it.

```
<script-writing-skill>/templates/
├── script-structure.md       ← read to understand the 3-part structure
├── section-templates.md      ← read for examples of intro/body/outro
└── duration-guide.md         ← read for time allocation rules
```

These are essentially mini-references that happen to live in `templates/` because they describe output format. SKILL.md should treat them like references — point at them, don't copy them.

**Pick one type per template file** and say so in SKILL.md:

```markdown
## Templates

- `templates/overview.md` — **scaffold**. Copy to <workspace>/overview.md and fill in.
- `templates/duration-guide.md` — **reference**. Read for orientation; do not copy.
```

---

## Cross-Skill Reference Reuse

A surprising and very effective pattern in production: **one skill's `references/` files are read by another skill's sub-agents as bootstrap material**. This creates a small number of "map" skills that the rest of the skill ecosystem leans on.

A production example: three thin `*-backend-mapping` / `*-frontend-mapping` / `*-api-bridge` skills exist almost entirely so that other skills' sub-agents can read their `references/*.md` first and learn the codebase structure (route → controller → use case → model, FE page → API call → BE endpoint). Every consumer skill opens its sub-agent prompts with "first read these mapping files, then investigate the actual code" — the bootstrap-then-investigate pattern (A2) in `orchestration-patterns.md`.

**When to build a map skill**:

- Multiple downstream skills need the same codebase orientation.
- The orientation is large (>500 lines total) and shouldn't be repeated in every consumer.
- The orientation evolves slowly compared to the consumer skills.

**When NOT to**:

- Only one consumer needs the references — keep them in the consumer.
- The references would be outdated within days — they'll cause more bugs than they solve.

The map skill itself doesn't need a workflow or sub-agents. It is a reference asset with a thin SKILL.md that exists mainly to give its references a stable home and a discoverable name.

---

## Workflow and Output Patterns

### Template Pattern

Use templates from `assets/` for consistent output. Distinguish strict sections (do not modify structure) from flexible sections (adapt to content).

```markdown
## Output Format
Use [assets/report-template.md](assets/report-template.md).
- Strict: header metadata, summary table, footer timestamp
- Flexible: analysis body, recommendations, code examples
```

### Checklist Workflow

For multi-step procedures where skipping a step is the failure mode, give the model a checklist to copy into its response and tick off. It survives long turns better than prose steps.

```markdown
## Form filling workflow

Copy this checklist and check items off as you complete them:

- [ ] 1. Analyze the form — `python3 ${CLAUDE_SKILL_DIR}/scripts/analyze_form.py input.pdf`
- [ ] 2. Fill in values in `fields.json`
- [ ] 3. Validate — `python3 ${CLAUDE_SKILL_DIR}/scripts/validate_fields.py fields.json`
- [ ] 4. Apply — `python3 ${CLAUDE_SKILL_DIR}/scripts/fill_form.py input.pdf fields.json out.pdf`
- [ ] 5. Verify the output

**Step 3: Validate.** Fix every reported error before continuing to step 4.
```

Reserve this for genuinely fragile sequences. On work with many valid routes, a checklist is over-prescription and costs quality.

### Feedback Loop

Pair any generation step that has an objective correctness criterion with a check that can fail, and say explicitly that the loop repeats until it passes.

```markdown
1. Edit `word/document.xml`
2. Validate: `python3 ${CLAUDE_SKILL_DIR}/scripts/validate.py unpacked_dir/`
3. If validation fails, fix the reported element and return to step 2
4. Only once validation passes: repack with `pack.py`
```

The validator does not have to be a script. A style guide plus "review against the checklist, revise, review again" is the same pattern with a document as the validator.

---

## One Skill = One Capability

Metadata for every installed skill costs only ~50-100 tokens each, so a large collection of narrow skills is cheap; a monolith is not, because the whole body loads whenever any part of it is relevant. Split monoliths so only the relevant context loads.

```
# Bad: 2000-line monolith covering testing, docs, debugging
coding-assistant/SKILL.md

# Good: focused skills
testing-code/SKILL.md           # 140 lines
writing-documentation/SKILL.md  # 110 lines
debugging-errors/SKILL.md       # 90 lines
```

---

## Tool Restrictions

`allowed-tools` pre-approves; `disallowed-tools` removes (field semantics in `yaml-spec.md`). Most skills need neither. `allowed-tools` specifically defaults to omitted — `yaml-spec.md`'s `allowed-tools` section has the two reasons that justify writing it. The combinations below are for skills that have one of those reasons, or that need `disallowed-tools` to actually restrict the tool pool.

### Common Patterns

**Read-Only Analysis** -- `allowed-tools: Read, Grep, Glob` + `disallowed-tools: Write, Edit, NotebookEdit`
Use for code analysis, security audits, complexity analysis. The second field is what makes it read-only.

**Documentation Only** -- `allowed-tools: Read, Grep, Glob, Write` + `disallowed-tools: Edit`
Use for generating new docs without touching existing files.

**Safe Exploration** -- `allowed-tools: Read, Grep, Glob, WebSearch`
Frictionless exploration; nothing is blocked, prompts are just skipped for the safe tools.

**Autonomous / background run** -- `disallowed-tools: AskUserQuestion`
Use when the skill must never stop to ask, e.g. a loop or scheduled task.

**Own scripts, no prompts** -- `allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/check.py:*)`
`${CLAUDE_SKILL_DIR}` expands inside `allowed-tools` too, so a skill can pre-approve exactly its own bundled scripts and nothing else.

### Available Tools

File ops: `Read`, `Write`, `Edit`, `Glob`, `NotebookEdit`. Search: `Grep`. Execution: `Bash`. Web: `WebFetch`, `WebSearch`. Agents: `Task`, `Skill`. Tasks: `TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet`. Utility: `AskUserQuestion`.

---

## What the P0 script pass already covers

The Improving playbook's lenses (`prompt-authoring.md`, `agent-neutral-authoring.md`, this file, `scripts-guide.md`, `orchestration-patterns.md`) should not re-derive what `validate_skill.py` and `audit_skill.py` already emit as findings:

- frontmatter validity, name rules (reserved words: `E013`), description length and listing truncation, description person (`W024`), body and code-block size (`E030`/`W031`), broken and escaping links — E/W codes;
- trigger headings in the body, duplicate headings, orphan references, reference-to-reference links, missing ToC, oversized references, Japanese frontmatter, legacy phrasings as a hint — `A001`–`A010`;
- raw tool names and platform paths in body text, missing `metadata.platforms` — `N1`–`N4`;
- test presence, test results, coverage, shebang, hardcoded paths, `.gitignore` — `S001`–`S007` (`check_scripts.py`, only when the skill has `scripts/`).

A lens finding that only restates one of these codes is redundant; a lens exists to see what the scripts cannot.

---

## Review checklist

Used by the Improving playbook's *structure* lens. `A001`/`A002`/`A003`/`A005`/`A007`/`A008`/`A009`/`A010` and the E/W codes handle the mechanical part; these items are about whether the structure does its job.

### ST1: SKILL.md dispatches rather than duplicates
Each reference has a one-line "read when" in SKILL.md, and no content is repeated in both places.

### ST2: Three-level loading respected
Body target ≤150 lines, warning above 200, error above 500 (see [Sizing and slimming SKILL.md](#sizing-and-slimming-skillmd)). Nothing in SKILL.md that only one branch needs and runs past ~15 lines (belongs in `references/`); nothing in `references/` that every run re-reads (belongs in SKILL.md).

### ST3: Description is accurate against what the body actually does
Key use case in the first sentence, third person, concrete trigger vocabulary, and specific enough that should-not-trigger requests stay out. No "When to use" section in the body. For "never fires" / "fires too often" complaints, use `yaml-spec.md`'s "Diagnosing activation" section (load via SKILL.md) and the should/should-not cases in `evaluating-skills.md` (load via SKILL.md).

### ST4: Content type matches pattern
Reference-type content is not run as a forked task; Task-type content states an explicit task.

### ST5: Every template is declared scaffold or reference guide
A template in `assets/` or `templates/` says which of the two it is, so the workflow around it is unambiguous.

### ST6: Checklists meant to be applied carry stable IDs
A `references/` file meant to be applied item-by-item (not just read) uses stable IDs like `LB1`, `RB3` so findings can be reported and merged mechanically.

### ST7: No files that do not belong
README / CHANGELOG / setup guides / concept explanations the model already has are FAILs — they cost tokens without adding trigger-relevant instruction.

### ST8: One skill, one capability
Unrelated sections or a body past 500 lines are split candidates.

### ST9: References stay scoped, not just relocated
No `references/*.md` file over 400 lines (`A010`) without a Table of Contents and a clear single domain concern — content moved out of SKILL.md to satisfy ST2 must land in a scoped reference, not become a second monolith.
