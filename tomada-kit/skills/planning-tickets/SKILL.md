---
name: planning-tickets
description: "Plan and create GitHub Issues with agile/scrum methodology. Analyze requirements, identify parallel work, manage dependencies, and suggest git worktree strategies. Use PROACTIVELY when creating tickets, planning sprints, breaking down features, organizing issues, identifying parallel tasks, managing dependencies, or working with GitHub Issues, scrum, agile planning, ticket breakdown, worktree planning. Examples: <example>Context: User wants to plan implementation user: 'Let us start cutting tickets' assistant: 'I will use planning-tickets skill' <commentary>Triggered by ticket creation request</commentary></example> <example>Context: User has requirements user: 'Split these requirements into issues' assistant: 'I will use planning-tickets skill' <commentary>Triggered by issue breakdown request</commentary></example>"
---

# Planning Tickets

Break requirements into GitHub Issues with agile/scrum methodology. Focus on **parallel work, explicit dependencies, and git worktree optimization**. The full issue body skeleton is the single source of truth in [templates/issue-template.md](templates/issue-template.md) — this file holds the principles; do not duplicate the template here.

## Core Principles

### 1. Independence over granularity
Prioritize independence over small size. A larger independent ticket beats several small dependent ones. Merge related tasks if splitting would create dependencies. Ideal size is still 1–3 hours and independently testable, but never split at the cost of introducing a blocking edge.

### 2. Parallel work first
Identify what can run simultaneously. Design tickets to minimize blocking relationships so multiple developers (or agents/worktrees) can work concurrently. Maximizing parallelism is the primary optimization target.

### 3. Concrete values are mandatory
"誰が実装しても要件は絶対に満たせる" — anyone (human or AI agent) must be able to implement and definitely satisfy the requirement. Every requirement uses **real values** extracted from the source (numbers, colors, sizes, exact text) with the source section cited. Never write vague requirements ("properly displays") or placeholders ("XX", "[value]").

### 4. Not In Scope is required
Every ticket must state explicitly what it does **not** include, referencing the tickets that own the excluded work. This is the primary guard against scope creep.

## Requirements: EARS format (required)

Every ticket's functional requirements use **EARS (Easy Approach to Requirements Syntax)** so they are unambiguous and testable. The five patterns (+ combination):

| Pattern | Template | Example |
|---------|----------|---------|
| **Ubiquitous** | The [system] shall [action] | The button shall have a 44pt minimum touch target. |
| **Event-driven** | **When** [trigger], the [system] shall [action] | **When** user taps "Coffee", the system shall display the size selection sheet. |
| **State-driven** | **While** [state], the [system] shall [action] | **While** loading, the system shall display a spinner. |
| **Unwanted** | **If** [condition], **then** the [system] shall [action] | **If** save fails, **then** the system shall show an error toast. |
| **Optional** | **Where** [feature], the [system] shall [action] | **Where** Pro is active, the system shall allow unlimited custom drinks. |
| **Complex** | Combine patterns | **While** after cutoff, **when** user selects a caffeine drink, the system shall show a warning. |

Give each requirement an ID (e.g. `REQ-001`) and map each ID to an acceptance criterion. Cover boundary conditions (min/max, empty/null, over-limit) in EARS form too.

## Issue body: required sections

Full skeleton in [templates/issue-template.md](templates/issue-template.md). Required sections:

1. **User Story** — As a [user], I want [goal], So that [benefit].
2. **Background & Context** — position in the whole, source-document section references, all concrete values with sources.
3. **Functional Requirements (EARS)** — each with an ID and a verification method.
4. **Boundary Conditions** — edge cases (0, max, over-limit, empty, null) in EARS form.
5. **Concrete Examples** — at least 3 (happy path / boundary / error) with real values.
6. **Not In Scope** — what this ticket excludes and where it lives instead (mandatory).
7. **Acceptance Criteria** — each tied to a requirement ID and testable with specific values.
8. **Dependencies** — bidirectional, in the fixed phrasing below.

## Dependency phrasing (machine-readable contract)

Write dependencies exactly as `Depends on #N` / `Blocks #N` (one per line, in the Dependencies section). Automation — the shipping-issues skill's issue digest among others — extracts dependency edges from issue bodies by regex; free-form phrasings ("needs the schema ticket first") create hidden edges that break automated ordering. If there are none, write `None`.

## Title format

```
【並列可】Feature - Specific scope
【依存あり】Feature - Specific scope
【基盤】Infrastructure - Must complete first
【並列可/worktree:feature-xxx】Feature with worktree suggestion
【順次】Feature - Must follow specific order
```

| Prefix | Meaning |
|--------|---------|
| 【並列可】 | Parallel OK (independent) |
| 【依存あり】 | Has dependencies |
| 【基盤】 | Foundation, required before parallel work |
| 【並列可/worktree:name】 | Parallel + suggested worktree branch |
| 【順次】 | Sequential |

## Dependency & parallelism analysis

1. **Identify foundation tasks** others depend on (schema, core types, base components, config).
2. **Map dependencies** as layers: Foundation → Layer 1 (parallel within) → Layer 2 → Integration.
3. **Group into parallel streams** (e.g. UI / Data / Logic), each an independent worktree. Parallel tickets must not touch the same files.
4. **Always create an integration ticket** where parallel streams converge.

## Git worktree strategy

Suggest a worktree when parallel tickets touch different areas, for long-running features, or for multiple developers/agents. Naming: `../{project}-{feature-category}/` (e.g. `../hydro-ui-home/`). Set up with `git worktree add`, clean up with `git worktree remove` once merged.

## Creating issues (two-pass, gh CLI)

Issue numbers don't exist until creation, so draft first, then create, then backfill:

1. Write every ticket body to a local file (`NNN-<slug>.md`, provisional IDs in dependency order).
2. Create in dependency order (foundation → parallel → integration) with `gh issue create --body-file`.
3. Replace provisional IDs with real numbers and backfill via `gh issue edit --body-file` — foundation tickets' `Blocks #N` can only be written in this pass.

Exact procedure and label/milestone bootstrap commands: [reference.md](reference.md).

## Output when planning

1. **Summary table** of all tickets first.
2. **Dependency graph** if the breakdown is complex.
3. **Phase breakdown** grouped by implementation phase (foundation → parallel streams → integration → polish).
4. **Worktree plan** listing suggested worktrees.

## Never

- Write vague requirements without specific values, or use placeholders (`XX`, `[value]`).
- Omit the **Not In Scope** section.
- Create acceptance criteria that don't map to requirement IDs.
- Express a dependency outside the `Depends on #N` / `Blocks #N` phrasing, or leave one unmarked.
- Mark tickets as parallel when their file sets overlap.

## Resources

- [templates/issue-template.md](templates/issue-template.md) — **SSOT** for the full issue body skeleton and its foundation/integration variants.
- [reference.md](reference.md) — creation order and number backfill, label/milestone bootstrap, sizing guidance.

## Platform compatibility (Claude Code / Codex)

Platform-neutral: uses only `gh` and `git` CLIs and skill-relative references (`templates/`, `reference.md`), with no Claude-only session or path constructs. Runs identically on Claude Code and Codex CLI with **no degradation**. On Codex the skill folder is reached via a symlink in `~/.codex/skills/` (Topology A); the real folder stays under the skill's own directory.

## Codex での制約（best-effort 劣化）

- なし。本スキルは `gh`/`git` CLI とスキル相対参照のみで構成され、Claude 専用機構（並列 `Task`、`AskUserQuestion`、MCP、ハードコード絶対パス）を使用しないため、Codex 上でも劣化なく同一に動作する。
