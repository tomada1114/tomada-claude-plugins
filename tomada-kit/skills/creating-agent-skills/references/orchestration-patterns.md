# Orchestration Patterns: Subagents and Phase Handoffs in Skills

Patterns for skills that spawn specialists, run independent investigations in parallel, or hand off to a downstream skill through file artifacts. A single linear walkthrough does not need this file.

> **Triage first.** For parallel or multi-stage execution, a deterministic fan-out runner — deterministic control flow (loops, branching, fan-out), token-budget awareness, resume, progress visibility — is the first candidate where the host offers one; it suits large, decomposable, verification-heavy orchestration. The single-spawn patterns here are the fallback when it doesn't fit or isn't available: steering interactively mid-run, driving a real TUI from outside. Conversational questions and single trivial edits need neither. Host-specific runner names: `references/platform-notes.md`.

## Table of Contents

- [Mental model: parallel within phase, sequential across phase](#mental-model-parallel-within-phase-sequential-across-phase)
- [A. Subagent invocation patterns](#a-subagent-invocation-patterns)
  - [A1. Parallel specialist review](#a1-parallel-specialist-review)
  - [A2. Bootstrap-then-investigate](#a2-bootstrap-then-investigate)
  - [A3. Parallel domain split](#a3-parallel-domain-split)
  - [A4. Spawn prompt layers](#a4-spawn-prompt-layers)
  - [A5. Synchronous join](#a5-synchronous-join)
  - [A6. Model and effort per spawn](#a6-model-and-effort-per-spawn)
- [B. Phase handoff patterns](#b-phase-handoff-patterns)
  - [B1. Artifact-driven handoff](#b1-artifact-driven-handoff)
  - [B2. Conditional skip based on prior artifact](#b2-conditional-skip-based-on-prior-artifact)
  - [B3. Deterministic output paths](#b3-deterministic-output-paths)
- [Proposing orchestration](#proposing-orchestration)
- [Anti-patterns](#anti-patterns)
- [Review checklist](#review-checklist)

---

## Mental model: parallel within phase, sequential across phase

> **Parallelism happens inside a single phase. Phases run in strict sequence. Sub-agents never talk to each other directly — the main agent joins their results.**

```
Phase 1 ── (spawn N sub-agents in parallel) ── join results
            │
            ▼
Phase 2 ── (read Phase 1 outputs, maybe spawn more sub-agents) ── join
            │
            ▼
Phase 3 ── (write final artifact)
```

What this means for SKILL.md:

- Each phase is a numbered section (`## Phase 1: ...`), so a reader can re-enter at the right step after an interruption.
- Sub-agent prompts are **complete**: the parent extracts what they need and embeds it. Sub-agents return only their final report.
- Between phases the main agent reads, summarizes, and decides what feeds the next phase.

---

## A. Subagent invocation patterns

### A1. Parallel specialist review

**Use when**: one review needs several expert lenses, each with a checklist too heavy to load into the main context alongside the others.

**In practice**: a design-review skill spawns three sub-agents at once — a React/hooks specialist with a frontend bug-pattern checklist (RB1–RB8), an impact-analysis specialist with a design-vs-reality checklist, a backend query-safety specialist with a backend checklist (LB1–LB8) plus cross-layer parity patterns. Each checklist is a few hundred lines; keeping them in specialists leaves the main context for synthesis.

**Minimum prompt template** (per specialist):

```
You are reviewing <ARTIFACT_NAME> from the lens of <SPECIALTY>.
Intent: <one sentence — what the parent does with this report>.

Step 1: Read this checklist file completely:
  <ABSOLUTE_PATH_TO_CHECKLIST>

Step 2: Read these context files (the things being reviewed):
  - <PATH_1>
  - <PATH_2>

Step 3: For each numbered item in the checklist (e.g. RB1 ... RB8),
report PASS / FAIL / N-A with a one-line justification and a file:line citation.

Step 4: List every FAIL as a finding, including uncertain and low-severity
ones, each with a confidence and a severity. Ranking happens in the merge.

Output format:
## Findings
- RB3 FAIL [high/medium]: <reason> (<file>:<line>)
- ...
## Summary
<one paragraph>
```

Stable IDs (`RB3`, `LB5`, `XL2`) let the main agent deduplicate and merge the three reports mechanically — see "References as Numbered Checklists" in `patterns-and-structure.md` (load via SKILL.md). Spawn all specialists of a phase together so they run concurrently.

---

### A2. Bootstrap-then-investigate

**Use when**: a sub-agent must understand a large codebase before answering, and "map" reference docs already exist (in this skill, another skill, or a generated index).

**In practice**: a feature-design skill has its sub-agents read a companion map skill's references (`routes-and-controllers.md` and friends) before opening source. Without the bootstrap, the sub-agent greps blindly and misses domain conventions.

```
Step 1 (BOOTSTRAP): Read these reference files in order; they hold the
domain conventions a blind search would miss:
  1. <skill-A>/references/architecture-overview.md
  2. <skill-A>/references/<domain>-map.md

Step 2 (INVESTIGATE): Answer <THE QUESTION> by reading the files
identified in Step 1, plus these explicit candidates:
  - <PATH_1>
  - <PATH_2>
```

Bootstrap references can live in a different skill from the one spawning — see "Cross-Skill Reference Reuse" in `patterns-and-structure.md` (load via SKILL.md).

---

### A3. Parallel domain split

**Use when**: the work divides cleanly along an axis like backend/frontend, server/client, infra/app. Two sub-agents are usually enough.

**Key trick**: the parent extracts the file list per side in an earlier step, **not** the sub-agents. Each sub-agent starts with a concrete list, which keeps its work bounded and reproducible.

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

The FE prompt has the same shape with its own file list and capture items (state lifecycle, API calls, permission gates).

---

### A4. Spawn prompt layers

Every effective sub-agent prompt carries five layers:

1. **Intent** — one sentence on why this investigation exists and what the parent will do with the result. The cheapest quality lever in a spawn prompt.
2. **Bootstrap pointers** — references to read before anything else, by absolute path.
3. **Concrete paths** — the file list the parent already extracted from diffs, design books, or map references. A sub-agent should not `find` what the parent could have located.
4. **Embedded slices** — the relevant section of a diff or design doc pasted in, so the sub-agent doesn't re-fetch it.
5. **Output contract** — the exact return shape (IDs, severity, confidence, citation format), plus an escalation rule: "if a judgment call is needed, report it as unresolved rather than deciding."

"Investigate X" with nothing else returns shallow, generic reports. The parent does all the orienting work that doesn't need parallelism. Phrasings to keep *out* of these prompts: `prompt-authoring.md` (load via SKILL.md).

---

### A5. Synchronous join

Sub-agents never talk to each other; there is no "Phase 1.5" where Agent A receives Agent B's output mid-flight.

- If Phase 2 needs Phase 1's output, it is a sequential phase, not a parallel one.
- When a phase fans out, SKILL.md gets a merge step: the main agent deduplicates, ranks, and resolves conflicts — if needed by a tie-breaker spawn in a follow-up phase.

**Barrier only where the merge needs it.** Block on the whole set only when the next step needs cross-item context — deduplicating across all findings, ranking a complete list, early-exiting on a zero count. Otherwise let each item flow to its next stage as it completes (pipelining, where the runner supports it). A needless barrier costs the gap between the fastest and slowest sub-agent, every phase.

---

### A6. Model and effort per spawn

Every spawn names its tier. Unspecified, the mechanical specialist and the hard one both inherit the session's model and effort — overpaying for a grep or underpowering a review.

Two tiers, assigned by **spec completeness, not task size**: `executor` (Opus 5.5 low) for fully specified, judgment-free work — settled-spec implementation, tests, CI, commit, PR, bulk replace, routine research and enumeration; `architect` (Opus 5.5 high) for complex implementation, design judgment, review and bug-finding, synthesis of scattered findings, and anything with unresolved spec. The criteria live in the `orchestrating-models` skill — point there rather than restating them.

A phase is often mixed rather than uniform: several `executor` collectors on disjoint slices, then one `architect` that reconciles their reports.

See `references/platform-notes.md` for how each host selects a tier (effort is what separates them, and not every spawn mechanism takes it), and `prompt-authoring.md` (load via SKILL.md) for writing the assignment into a skill.

---

## B. Phase handoff patterns

### B1. Artifact-driven handoff

**Use when**: a skill is one stop in a multi-skill pipeline, and the next skill needs to know what this one produced.

**In practice**: a design pipeline (`ticket-intake → feature-designing → design-review → implementation-review → e2e-testing → mr-description`) is wired together purely through files under one workspace directory. No shared memory, no message bus. **The contract is the directory layout:**

```
<project>/design/{ticket-no}-{slug}/
├── ticket.md                ← created by ticket-intake
├── 00_current-state.md      ← created by ticket-intake
├── overview.md              ← created by feature-designing
├── backend.md               ← created by feature-designing
├── frontend.md              ← created by feature-designing
├── e2e-testcases.md         ← created by feature-designing
├── mr-description-be.md     ← created by mr-description
└── mr-description-fe.md     ← created by mr-description
```

Each skill declares its inputs and outputs by exact filename in `## Inputs` / `## Outputs` sections at the top of SKILL.md, and treats other files in the directory as opaque — it does not edit files it didn't create unless it is designed as a sync skill. "Writes some markdown to the design dir" is not a contract.

To build a new pipeline: pick a deterministic root path (`workspace-conventions.md`, load via SKILL.md); pick stable kebab-case filenames, prefixed `00_`, `01_` when reading order matters; list the recommended pipeline order in AGENTS.md (or CLAUDE.md).

---

### B2. Conditional skip based on prior artifact

**Use when**: a downstream skill may run after the upstream one already did part of its work, and re-asking the user would waste their time.

```markdown
## Phase 0: Check for prior artifacts

1. If `<DESIGN_DIR>/00_current-state.md` exists, read it.
2. Locate the "Clarification Questions" section.
   - For each question with an answer, treat it as confirmed and skip in Phase 1.
   - For each question without an answer, queue it for Phase 1 hearings.
3. If the file does not exist, treat all standard questions as open.
```

The artifact gates the scope of the next phase; without it, chained skills redo each other's work.

---

### B3. Deterministic output paths

**Use when**: any skill writes files. Compute the path from the user's input — not `/tmp`, not a random UUID — so the user can re-enter days later, downstream skills find inputs without being told, re-runs update in place instead of duplicating, and failures leave a workspace to inspect.

| Skill class | Path convention |
|---|---|
| Design pipeline | `~/<project>/design/{ticket-no}-{slug}/` |
| Verification scratch | `~/Desktop/testing/{YYYYMMDD}_{slug}/` |
| Single-file outputs | `~/<project>/<deterministic-name>.md` |

Slug rules, snapshot subdirectories for destructive operations, and re-run policy: `workspace-conventions.md` (load via SKILL.md).

---

## Proposing orchestration

The Improving playbook proposes delegation, parallelism, or phase splits for an audited skill only under these conditions, and within these limits.

**Warranted when at least one holds:**

1. Two or more independent angles, each needing its own checklist or reference of 100+ lines — a single pass through all of them would crowd out the synthesis.
2. A phase reads many files whose contents are not needed afterwards — a fresh context keeps that reading out of the main thread.
3. The skill is a node in a pipeline, reading and writing structured files that a separate phase or skill consumes.
4. An autonomous run spans many phases, and a fresh-context verifier at an interval earns its cost against the risk of drift.

**Not warranted:**

- Work the main agent finishes in a handful of tool calls.
- Strictly sequential steps with no independent angle to parallelize.
- Re-checking work the model already verifies by default.

**Limits on any proposal:**

- At most one proposal per phase, three per skill.
- Every proposal names: the condition above that justifies it, the tier for each spawn (A6), the five prompt layers (A4), and a spawn cap.

---

## Anti-patterns

Each is covered above; this is the scan list for a review.

1. **"Investigate the codebase" as the whole spawn prompt** — pre-extract paths and embed them (A3, A4).
2. **Loading every checklist into the main context** — push each into a specialist (A1).
3. **Chaining sub-agents directly** — a dependency is a new phase (A5).
4. **Outputs in `/tmp` or random paths** — use B3.
5. **Re-asking questions a previous skill answered** — use B2.
6. **Implicit file contracts** — declare exact filenames (B1).
7. **Checklists copy-pasted into SKILL.md** — they belong in `references/`, read by path.
8. **Spawning a phase's sub-agents one by one** — issue them together so they run concurrently.
9. **Spawning without naming a tier** — A6.
10. **Open-ended "use sub-agents when helpful"** — state the bar and cap the count (Proposing orchestration).
11. **Telling a sub-agent to double-check itself** — ask for commands run and their output instead; fresh-context verifiers belong only on long autonomous runs, at an interval. <!-- audit-ignore: A006 --> <!-- prompt-lint-ignore: P001 -->
12. **Telling a finder sub-agent to report only what matters** — "only high-severity", "be conservative" are followed literally; ask for full coverage with confidence and severity, filter in the merge. <!-- audit-ignore: A006 --> <!-- prompt-lint-ignore: P002 -->

---

## Review checklist

Used by the Improving playbook's *orchestration* lens.

### OR1: Every spawn names a tier
`executor` or `architect`, chosen by spec completeness (A6), not task size.

### OR2: Every spawn prompt carries the five layers
Intent, bootstrap pointers, concrete paths, embedded slices, output contract (A4).

### OR3: Parallel within a phase, sequential across phases
No sub-agent chaining; the main agent merges (A5).

### OR4: Output contracts pin exact shape and stable IDs
So merging findings across spawns is mechanical.

### OR5: Delegation bar and spawn cap are stated
"Delegate when helpful" with no bar and no cap is a FAIL.

### OR6: Spawn prompts are free of legacy phrasings
No extra verification pass, no severity self-filtering (see `prompt-authoring.md`, load via SKILL.md).

### OR7: Pipeline nodes declare inputs/outputs and use deterministic paths
See B1 and B3.

### OR8: Missing orchestration is reported as a proposal
A phase meeting a condition in "Proposing orchestration" but running inline is a finding — name the condition it meets.
