---
name: pr-review-pipeline
description: Example multi-phase skill — reviews a pull request by spawning a security specialist and a performance specialist in parallel, each primed with a numbered checklist, then merges their findings into a deterministic workspace. Structural reference for building phased skills with sub-agents; not wired to anything, do not invoke it.
---

# PR Review Pipeline (structural example)

Shows one shape: parallelism inside a phase, phases in strict sequence, sub-agents that never talk to each other, and a workspace path derived from the arguments rather than invented per run.

## Contract

**Input:** a PR number in `$ARGUMENTS`.

**Workspace:** `~/code-reviews/{pr-number}-{slug}/`, slug = PR title lowercased, kebab-cased, ASCII, max 5 words.

**Outputs:** `diff.patch` (snapshot) · `findings-security.md` · `findings-performance.md` · `review.md` (merged, severity-ranked).

Deriving the path from the input rather than a timestamp is what makes a re-run after a force-push land on top of the previous review instead of beside it.

## Phase 0: Workspace

1. Take the PR number from `$ARGUMENTS`; ask if missing.
2. `gh pr view <num> --json title -q .title` → slug → workspace path. Create it. If it already exists, ask whether to overwrite or read the existing findings.
3. `gh pr diff <num> > <workspace>/diff.patch`.
4. Read `diff.patch` once here and extract the changed-file list grouped by directory, with hunk line ranges.

Step 4 is what makes the Phase 1 prompts concrete. Fetching once and writing to disk also means two fresh contexts can both read the diff without two round trips.

## Phase 1: Parallel specialists

Spawn both in a single message so they run concurrently. Both run on `opus` — each returns a judgment call about whether a finding is real, which is the line that requires it. Each prompt is complete on its own; a sub-agent that has to ask the parent a follow-up was under-specified.

`${CLAUDE_SKILL_DIR}` expands to an absolute path before the model sees it. Never hand a sub-agent a path relative to the skill directory — it has no idea where that is.

### Sub-agent 1 — security (`model: opus`)

```
Reviewing PR #<NUM> from a security lens.

BOOTSTRAP: read completely —
  ${CLAUDE_SKILL_DIR}/references/security-checklist.md
It defines six numbered checks, SEC1..SEC6.

CONTEXT: read <workspace>/diff.patch
Changed files: <PARENT-EXTRACTED LIST>

REVIEW: for each of SEC1..SEC6 report PASS / FAIL / N-A with a one-line
justification and a <file>:<line> citation. Rank FAILs critical/high/medium/low.

Write to <workspace>/findings-security.md in this form:

## Findings
- SEC3 FAIL (high): SQL string concatenation at <file>:<line> — use a prepared statement
- SEC5 PASS: all new endpoints carry auth middleware

## Summary
<one paragraph>
```

### Sub-agent 2 — performance (`model: opus`)

```
Reviewing PR #<NUM> from a performance lens.

BOOTSTRAP: read completely —
  ${CLAUDE_SKILL_DIR}/references/performance-checklist.md
It defines five numbered checks, PERF1..PERF5.

CONTEXT: read <workspace>/diff.patch
Changed files: <PARENT-EXTRACTED LIST>

REVIEW and output format: identical to the security sub-agent, substituting
PERF1..PERF5.

Write to <workspace>/findings-performance.md
```

## Phase 2: Merge

1. Read both findings files.
2. Merge into one severity-ranked list. Stable IDs make this mechanical rather than a judgment call: new checklist items append at the bottom and old IDs never renumber, so `SEC3` means the same thing across every review ever run.
3. Where a security FAIL and a performance PASS touch the same code, the security severity wins; keep both entries.
4. Write `<workspace>/review.md`: title, timestamp, workspace path, findings grouped by severity, a full `SEC1 PASS, SEC2 PASS, …` roll call so a passing check is visibly checked rather than absent, and a closing paragraph on the highest-impact actions.

## Phase 3: Report

Print the path to `review.md` and one paragraph. Do not paste the review into chat; the file is the artifact.

## Why this shape

- **Two sub-agents, not one main-context pass** — each checklist is ~50 lines; both plus the diff plus the synthesis prompt would crowd the main context for no gain.
- **Sequential phases, parallel within** — the merge cannot start before both specialists finish, and specialists that could see each other's drafts would converge instead of covering different ground.
- **No scripts here** — nothing in this flow is fragile enough to warrant them. If diff fetching or finding extraction grew complex, they would move to `scripts/` and be invoked with the workspace path as an argument.
