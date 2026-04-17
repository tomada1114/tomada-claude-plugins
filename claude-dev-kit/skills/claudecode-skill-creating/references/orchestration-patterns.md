# Orchestration Patterns: Subagents and Phase Handoffs in Skills

This reference documents battle-tested patterns extracted from a real production set of skills (`~/draever/.claude/skills/*` and `~/.claude/skills/*`) that orchestrate sub-agents and chain skills via file artifacts. Use these patterns when a skill needs to do more than a single linear task — when it must spawn specialists, run independent investigations in parallel, or hand off to a downstream skill.

If your skill is a single linear walkthrough, you do not need this file. Stay with the basics in `SKILL.md`.

## Table of Contents

- [When to reach for these patterns](#when-to-reach-for-these-patterns)
- [Mental model: parallel within phase, sequential across phase](#mental-model-parallel-within-phase-sequential-across-phase)
- [A. Subagent invocation patterns](#a-subagent-invocation-patterns)
  - [A1. Parallel specialist review (3-lens pattern)](#a1-parallel-specialist-review-3-lens-pattern)
  - [A2. Bootstrap-then-investigate](#a2-bootstrap-then-investigate)
  - [A3. Parallel domain split (BE/FE, backend/frontend, etc.)](#a3-parallel-domain-split)
  - [A4. Curated multi-source context](#a4-curated-multi-source-context)
  - [A5. Synchronous join, no agent-to-agent messaging](#a5-synchronous-join)
- [B. Phase handoff patterns](#b-phase-handoff-patterns)
  - [B1. Artifact-driven handoff](#b1-artifact-driven-handoff)
  - [B2. Conditional skip based on prior artifact](#b2-conditional-skip-based-on-prior-artifact)
  - [B3. Deterministic output paths](#b3-deterministic-output-paths)
- [Anti-patterns](#anti-patterns)
- [Source skills (further reading)](#source-skills-further-reading)

---

## When to reach for these patterns

Use this file's patterns when **at least one** of the following is true:

- The work has multiple independent angles that can be investigated in parallel (e.g., backend safety vs. frontend hooks vs. cross-layer parity).
- A single main-context pass would burn too much context just reading checklists or large reference docs.
- The skill is one node in a larger pipeline (intake → design → review → implement → test → ship), and needs to read/write structured files that the next skill consumes.
- Different "lenses" need different specialty checklists, and merging the results is the whole point.

If the skill is a one-shot generator or a simple lookup, skip this file.

---

## Mental model: parallel within phase, sequential across phase

The skills observed in production converge on one structural rule:

> **Parallelism happens inside a single phase. Phases run in strict sequence. Sub-agents never talk to each other directly — the main agent joins their results.**

Concretely:

```
Phase 1 ── (spawn N sub-agents in parallel) ── join results
            │
            ▼
Phase 2 ── (read Phase 1 outputs, maybe spawn more sub-agents) ── join
            │
            ▼
Phase 3 ── (write final artifact)
```

This rule matters because it constrains how you write SKILL.md:

- Each phase becomes a numbered section (`## Phase 1: ...`, `## Phase 2: ...`).
- Sub-agents receive prompts that are **complete**: the parent extracts what they need to know and embeds it in the prompt. Sub-agents do not "send back" anything other than their final report.
- The main agent's job between phases is to read, summarize, and decide what to feed into the next phase.

Phase numbering also lets the user (and future-you reading the SKILL) skim the workflow and re-enter at the right step if work was interrupted.

---

## A. Subagent invocation patterns

### A1. Parallel specialist review (3-lens pattern)

**Use when**: a single review needs multiple expert lenses applied in parallel, each with its own checklist that would be too heavy to load into the main context.

**Source**: `~/draever/.claude/skills/design-review/SKILL.md:47-134`. The skill spawns three Explore agents simultaneously:
- Agent 1: React/hooks specialist, primed with `references/fe-bug-patterns.md` (RB1–RB8 checklist)
- Agent 2: Sibling/impact-analysis specialist, primed with `references/design-vs-reality-checklist.md`
- Agent 3: BE query-safety specialist, primed with `references/be-bug-patterns.md` (LB1–LB8) and `references/cross-layer-parity-patterns.md`

**Why it works**: each checklist is a few hundred lines. Loading all three into the main context would crowd out the design book itself. Pushing them into specialist sub-agents keeps the main context focused on synthesis.

**Minimum prompt template** (for each specialist sub-agent):

```
You are reviewing <ARTIFACT_NAME> from the lens of <SPECIALTY>.

Step 1: Read this checklist file completely:
  <ABSOLUTE_PATH_TO_CHECKLIST>

Step 2: Read these context files (the things being reviewed):
  - <PATH_1>
  - <PATH_2>

Step 3: For each numbered item in the checklist (e.g. RB1 ... RB8),
report PASS / FAIL / N-A with a one-line justification and a file:line citation.

Step 4: At the end, list any FAIL items as actionable findings ranked by severity.

Output format:
## Findings
- RB3 FAIL: <reason> (<file>:<line>)
- ...
## Summary
<one paragraph>
```

**Why the numbered checklist format is critical**: when three sub-agents return findings keyed `RB3`, `LB5`, `XL2`, the main agent can deduplicate, group by severity, and merge into a single ranked list mechanically. See `C4` in `patterns-and-structure.md` for the checklist convention.

**Parallelism**: spawn all three in a single tool-call message so they execute concurrently.

---

### A2. Bootstrap-then-investigate

**Use when**: a sub-agent needs to understand a large codebase before it can answer the actual question, and the codebase has pre-existing "map" reference docs (whether in the same skill, another skill, or a generated index).

**Source**: `~/draever/.claude/skills/unsoul-feature-designing/SKILL.md:80-119`. Sub-agents are told to **first** read mapping references like `unsoul-backend-mapping/references/routes-and-controllers.md`, **then** dive into actual source code. Without this bootstrap, the sub-agent wastes time grepping blindly and often misses domain conventions.

**Pattern shape**:

```
Step 1 (BOOTSTRAP): Read the following reference files in order:
  1. <skill-A>/references/architecture-overview.md
  2. <skill-A>/references/<domain>-map.md
These give you the codebase's structure. Do NOT skip this step.

Step 2 (INVESTIGATE): Now answer <THE QUESTION> by reading the
files identified in Step 1, plus these explicit candidates:
  - <PATH_1>
  - <PATH_2>
```

**Cross-skill reuse**: Bootstrap references can live in a different skill from the one spawning the sub-agent. This is how a project ends up with a small number of "map" skills (`*-backend-mapping`, `*-frontend-mapping`, `*-api-bridge`) that everyone else's sub-agents read first. See "Cross-skill reference reuse" in `patterns-and-structure.md`.

---

### A3. Parallel domain split

**Use when**: the work cleanly divides along an axis like backend/frontend, server/client, infra/app, model/view. Two sub-agents are usually enough.

**Source**: `~/draever/.claude/skills/ticket-intake/SKILL.md:165-198`. The parent skill first identifies a list of BE files and a list of FE files (in an earlier step), then spawns two Explore agents in parallel — one for BE, one for FE — embedding the relevant file list in each prompt.

**Key trick**: the parent does the file-list extraction, **not** the sub-agents. By the time a sub-agent starts running, it has a concrete list to investigate, not "go find the relevant files." This makes the sub-agent's work bounded and reproducible.

```
[BE Agent prompt]
Investigate the current behavior of <FEATURE> on the backend.
Files to read (in order):
  - app/Http/Controllers/.../FooController.php
  - app/UseCases/.../UpdateFoo.php
  - app/Models/Foo.php
For each file, capture:
  1. Inputs and validation rules
  2. Key business logic
  3. Database side effects
Report in <300 words.
```

```
[FE Agent prompt]
Investigate the current behavior of <FEATURE> on the frontend.
Files to read (in order):
  - src/pages/foo/FooPage.tsx
  - src/api/foo.ts
  - src/hooks/useFoo.ts
For each file, capture:
  1. State variables and their lifecycle
  2. API calls (endpoint, params, response handling)
  3. Permissions/role gates
Report in <300 words.
```

---

### A4. Curated multi-source context

**Use when**: you want to maximize signal-to-noise in a sub-agent's prompt. This is less a discrete pattern than a discipline applied to all the above.

Every effective sub-agent prompt observed in production is composed of **four layers**:

1. **Bootstrap pointers** — references the sub-agent must read before doing anything else.
2. **Concrete file/path lists** — the parent extracts these from diffs, design books, or mapping references. Never `find` or `grep` from inside a sub-agent for things the parent could have located.
3. **Embedded content slices** — the parent pastes the relevant section of a design book or diff directly into the prompt, so the sub-agent doesn't have to fetch it.
4. **Output contract** — the exact shape the sub-agent must return (numbered findings, severity, citation format), so merging is mechanical.

The temptation is to write "investigate X" and let the sub-agent figure it out. Resist this. Sub-agents that get under-specified prompts return shallow, generic reports. The parent should do all the orienting work that doesn't require parallelism.

---

### A5. Synchronous join

Sub-agents in this style of skill **never talk to each other**. The main agent waits for all spawned sub-agents in a phase to complete, then reads their outputs and merges. There is no "Phase 1.5" where Agent A receives Agent B's output mid-flight.

Why this matters when designing a skill:

- Don't try to chain sub-agents. If Phase 2 needs Phase 1's output, that's a sequential phase, not a parallel one.
- The main agent is responsible for deduplication, severity ranking, and conflict resolution. Build a "Phase 1.5: Merge findings" step into SKILL.md whenever you spawn multiple sub-agents.
- If two sub-agents disagree, the main agent's merge step is where that gets resolved — possibly by spawning a third tie-breaker sub-agent in a follow-up phase.

---

## B. Phase handoff patterns

### B1. Artifact-driven handoff

**Use when**: a skill is one stop in a multi-skill pipeline, and the next skill needs to know what this one produced.

**Source**: the entire `~/draever/.claude/skills/` directory. The pipeline `ticket-intake → unsoul-feature-designing → design-review → implementation-review → e2e-testing → mr-description` is wired together purely through files in `~/draever/design/{ticket-no}-{slug}/`. Each skill reads a known set of input files and writes a known set of output files. There is no shared memory, no message bus.

**The contract is the directory layout:**

```
~/draever/design/{ticket-no}-{slug}/
├── ticket.md                ← created by ticket-intake
├── 00_current-state.md      ← created by ticket-intake
├── overview.md              ← created by unsoul-feature-designing
├── backend.md               ← created by unsoul-feature-designing
├── frontend.md              ← created by unsoul-feature-designing
├── e2e-testcases.md         ← created by unsoul-feature-designing
├── references.md            ← created by unsoul-feature-designing
├── mr-description-be.md     ← created by mr-description
└── mr-description-fe.md     ← created by mr-description
```

Each skill:
- **Declares its inputs** at the top of SKILL.md (e.g. "Reads `overview.md`, `backend.md`, `frontend.md`").
- **Declares its outputs** at the top of SKILL.md (e.g. "Writes `mr-description-be.md` and `mr-description-fe.md`").
- **Treats other files in the directory as opaque** — does not edit files it didn't create unless explicitly designed as a sync skill.

This is the single most important pattern for building chains of skills. The directory becomes the source of truth and the API surface.

**How to apply it to a new pipeline:**

1. Pick a deterministic root path. See `workspace-conventions.md`.
2. Pick stable filenames. Use kebab-case, prefix with order-hint (`00_`, `01_`) when the user might want to read them in order.
3. In each skill's SKILL.md, write a "## Inputs" and "## Outputs" section listing exact filenames.
4. In CLAUDE.md, list the recommended pipeline order so users can follow it sequentially.

---

### B2. Conditional skip based on prior artifact

**Use when**: a downstream skill might be invoked after the upstream skill has already done some of its work, and re-asking the user the same questions would be rude.

**Source**: `~/draever/.claude/skills/unsoul-feature-designing/SKILL.md:27-43`. The skill checks for `00_current-state.md` (produced by `ticket-intake`) and inspects whether the "担当者確認事項" (clarification questions) section is already filled in. If yes, the design skill skips re-asking those questions and only hears the still-open ones.

**Pattern shape:**

```markdown
## Phase 0: Check for prior artifacts

1. If `<DESIGN_DIR>/00_current-state.md` exists, read it.
2. Locate the "Clarification Questions" section.
   - For each question with an answer, treat it as confirmed and skip in Phase 1.
   - For each question without an answer, queue it for Phase 1 hearings.
3. If the file does not exist, treat all standard questions as open.
```

The artifact gates the scope of the next phase. Without this, you build a chain of skills that re-do each other's work.

---

### B3. Deterministic output paths

**Use when**: any skill that writes files. Default to a deterministic path computed from the user's input — not `/tmp`, not a random UUID.

**Why deterministic, not /tmp**:

- The user can re-enter the workflow days later and find their work.
- Downstream skills can locate input files without being told the path.
- Re-running a skill on the same input updates the existing artifacts in place rather than creating duplicates.
- Failures leave a usable workspace to inspect, not a vanished tmpdir.

**Examples observed in production:**

| Skill class | Path convention |
|---|---|
| Design pipeline (`unsoul-feature-designing` etc.) | `~/draever/design/{ticket-no}-{slug}/` |
| Verification scratch (`cc-cli-verify`) | `~/Desktop/testing/{YYYYMMDD}_{slug}/` |
| Single-file outputs | `~/<project>/<deterministic-name>.md` |

**Slug derivation**: take 1–3 keywords from `$ARGUMENTS` or the ticket title, lowercase, kebab-case, ASCII-only. Document the rule in SKILL.md so the user can predict the path.

**Snapshot subdirectory** (for destructive operations): under the workspace, create a `.snapshot/` subdir to hold copies of files you're about to mutate, so you can restore on failure. See `cc-cli-verify` and the workspace conventions reference.

See [workspace-conventions.md](workspace-conventions.md) for the full set of rules.

---

## Anti-patterns

These are mistakes the production skills have already paid the price for. Do not repeat them.

**1. "Investigate the codebase" as a sub-agent prompt.**
Sub-agents under-specified like this return shallow, generic findings. Always pre-extract concrete file lists in the parent and embed them.

**2. Loading every checklist into the main context.**
If you find yourself reading three large checklists in SKILL.md and then doing a review in main, you have just used the entire context window for setup. Push each checklist into a sub-agent (A1).

**3. Trying to chain sub-agents directly.**
Sub-agents complete and return. They don't message each other. If Phase 2 depends on Phase 1's output, write Phase 2 as a separate phase the main agent triggers after the join.

**4. Writing outputs to `/tmp` or random paths.**
The user loses their work, the next skill in the pipeline can't find the input, and re-runs create orphans. Use B3.

**5. Re-asking questions a previous skill already answered.**
If your skill is downstream of another, check for the prior artifact and read the answers. See B2.

**6. Implicit file contracts.**
"This skill writes some markdown to the design dir" is not a contract. Pin down the exact filename and section structure, write it in the skill's "Outputs" section, and treat it as a public API.

**7. Copy-pasting checklists into SKILL.md instead of `references/`.**
Numbered checklists belong in `references/` so sub-agents can read them in isolation. SKILL.md should reference them by path, not duplicate them.

**8. Forgetting to spawn sub-agents in a single message.**
Spawning them sequentially defeats the parallelism. All sub-agents for a phase must be invoked in one tool-call message.

---

## Source skills (further reading)

When in doubt, read the source. These are the skills that pioneered the patterns above.

**Subagent orchestration:**
- `~/draever/.claude/skills/design-review/SKILL.md` — 3-lens parallel review (A1, A4, A5)
- `~/draever/.claude/skills/design-review/references/be-bug-patterns.md` — numbered checklist example (LB1–LB8)
- `~/draever/.claude/skills/design-review/references/fe-bug-patterns.md` — numbered checklist example (RB1–RB8)
- `~/draever/.claude/skills/unsoul-feature-designing/SKILL.md` — bootstrap-then-investigate (A2)
- `~/draever/.claude/skills/ticket-intake/SKILL.md` — parallel domain split (A3)
- `~/draever/.claude/skills/implementation-review/SKILL.md` — dataflow analysis with 2 parallel sub-agents

**Phase handoff:**
- The whole `~/draever/.claude/skills/` pipeline (`ticket-intake → unsoul-feature-designing → design-review → implementation-review → e2e-testing → mr-description → effort-estimation`) — artifact-driven chains (B1, B2)
- `~/draever/.claude/skills/design-sync/SKILL.md` — the canonical example of "read the artifacts, reconcile with current code, rewrite"

**Workspace and paths:**
- `~/.claude/skills/cc-cli-verify/SKILL.md` and `scripts/` — snapshot/restore for destructive ops (B3)

**Cross-skill reference reuse:**
- `~/draever/.claude/skills/unsoul-backend-mapping/`, `unsoul-frontend-mapping/`, `unsoul-api-bridge/` — referenced by other skills via bootstrap-then-investigate (A2)
