---
name: example-code-review
description: Example multi-phase skill that reviews a pull request by spawning two specialist sub-agents in parallel — one for security, one for performance — each primed with a numbered checklist. Demonstrates the orchestration patterns documented in claudecode-skill-creating. NOT a real working skill — read it for structure, do not invoke it.
---

# Example: Multi-Phase Code Review Skill

This is a **structural example** demonstrating the orchestration patterns from `claudecode-skill-creating`. It is intentionally fictional and is not wired up to anything. Read it to see how the patterns fit together in one place.

It illustrates:
- **Parallel specialist review** (3-lens pattern, A1) — two specialist sub-agents run concurrently
- **Numbered checklist references** — each specialist is primed with `SEC1–SEC6` or `PERF1–PERF5`
- **Curated multi-source context** (A4) — sub-agent prompts include bootstrap, file lists, diff slices, and output contract
- **Synchronous join** (A5) — main agent merges findings between phases
- **Deterministic output paths** (B3) — workspace at `~/code-reviews/{pr-number}-{slug}/`
- **Inputs/Outputs declared as a public contract**

## Inputs

This skill reads:
- A PR number (passed as `$ARGUMENTS`)
- The git diff for that PR (fetched via `gh pr diff`)
- `references/security-checklist.md` (loaded by sub-agent 1)
- `references/performance-checklist.md` (loaded by sub-agent 2)

## Outputs

This skill writes everything under `~/code-reviews/{pr-number}-{slug}/`:

- `diff.patch` — snapshot of the PR diff at review time
- `findings-security.md` — sub-agent 1 output (`SEC1`–`SEC6` results)
- `findings-performance.md` — sub-agent 2 output (`PERF1`–`PERF5` results)
- `review.md` — final merged report ranked by severity

The slug is derived from the PR title: lowercased, kebab-cased, ASCII-only, max 5 words.

## Phase 0: Workspace setup

1. Take the PR number from `$ARGUMENTS`. If missing, ask the user.
2. Fetch PR title via `gh pr view <num> --json title -q .title`.
3. Compute slug from the title.
4. Compute workspace: `~/code-reviews/{pr-number}-{slug}/`. Create it if missing. If it exists, ask whether to overwrite or read existing findings.
5. Save the diff: `gh pr diff <num> > <workspace>/diff.patch`.
6. Read `diff.patch` once in the main context to extract:
   - List of changed files (group by directory: `backend/`, `frontend/`, `migrations/`, etc.)
   - For each changed file, the line ranges of the hunks

This extraction is what makes the sub-agent prompts in Phase 1 concrete instead of vague.

## Phase 1: Parallel specialist review

Spawn **both** sub-agents in a single message so they run concurrently. Each receives a complete prompt — it should not need to ask the parent any follow-up questions.

### Sub-agent 1: Security specialist

```
You are reviewing PR #<NUM> from a security lens.

Step 1 (BOOTSTRAP): Read this checklist file completely:
  ~/.claude/skills/claudecode-skill-creating/examples/5-multi-phase-skill/references/security-checklist.md

It defines six numbered checks (SEC1 through SEC6). You will report against
each one.

Step 2 (CONTEXT): Read the PR diff:
  <workspace>/diff.patch

The changed files are:
  - <PARENT-EXTRACTED LIST GOES HERE>

Step 3 (REVIEW): For each numbered item SEC1..SEC6, report PASS, FAIL, or N-A
with a one-line justification and a `<file>:<line>` citation.

Step 4 (SUMMARY): List all FAIL items as actionable findings, ranked by severity
(critical / high / medium / low).

Output format:

## Findings
- SEC3 FAIL (high): SQL string concatenation in <file>:<line> — recommend prepared statement
- SEC5 PASS: All new endpoints have auth middleware
- ...

## Summary
<one paragraph>

Save your report to: <workspace>/findings-security.md
```

### Sub-agent 2: Performance specialist

```
You are reviewing PR #<NUM> from a performance lens.

Step 1 (BOOTSTRAP): Read this checklist file completely:
  ~/.claude/skills/claudecode-skill-creating/examples/5-multi-phase-skill/references/performance-checklist.md

It defines five numbered checks (PERF1 through PERF5).

Step 2 (CONTEXT): Read the PR diff:
  <workspace>/diff.patch

The changed files are:
  - <PARENT-EXTRACTED LIST GOES HERE>

Step 3 (REVIEW): For each numbered item PERF1..PERF5, report PASS, FAIL, or N-A
with a one-line justification and a `<file>:<line>` citation.

Step 4 (SUMMARY): List all FAIL items as actionable findings, ranked by severity.

Output format: same as the security sub-agent.

Save your report to: <workspace>/findings-performance.md
```

Both sub-agents read their checklists, do their analysis independently, and write
their files. They never communicate with each other. The main agent waits for both to finish.

## Phase 2: Merge findings

1. Read `findings-security.md` and `findings-performance.md`.
2. Build a single ranked list. Because findings are tagged with stable IDs (`SEC3`, `PERF1`, etc.), deduplication and grouping by severity is mechanical.
3. Resolve conflicts: if a security FAIL and a performance PASS touch the same code, the security finding wins on severity but include both.
4. Write the merged result to `<workspace>/review.md` with this structure:

```markdown
# PR #<NUM>: <PR title>

Reviewed at: <timestamp>
Workspace: <workspace>

## Critical Issues
- SEC3: ...

## High Issues
- PERF1: ...

## Medium / Low
- ...

## Items Reviewed
SEC1 PASS, SEC2 PASS, SEC3 FAIL, SEC4 N-A, SEC5 PASS, SEC6 PASS
PERF1 FAIL, PERF2 PASS, PERF3 PASS, PERF4 PASS, PERF5 PASS

## Recommendations
<one paragraph synthesizing the highest-impact actions>
```

## Phase 3: Report to the user

Print the path to `review.md` and a one-paragraph summary. Do not paste the full review into the chat — the user can read the file.

---

## Notes for skill authors reading this example

- **Why two sub-agents instead of one main-context review?** Each checklist is ~80 lines. Loading both into the main context plus the diff plus the synthesis prompt eats too much budget. Specialists keep the main context lean.
- **Why numbered IDs?** The merge in Phase 2 becomes mechanical instead of judgment-based. New checklist items append at the bottom; old IDs never renumber.
- **Why save the diff to disk?** Both sub-agents need it, and they're running in fresh contexts. Putting it on disk means the parent fetches it once, not twice.
- **Why a deterministic workspace?** A reviewer can re-run the skill on the same PR after a force-push and get an updated `review.md` in the same place. The user always knows where to look.
- **What's NOT here**: scripts. This skill is light enough that it doesn't need any. If the diff fetching or finding extraction grew complex, you'd add `scripts/fetch-diff.sh` invoked with the workspace path as an argument. See `references/scripts-guide.md` Real-World Patterns.

Read [orchestration-patterns.md](../../references/orchestration-patterns.md) and [workspace-conventions.md](../../references/workspace-conventions.md) for the full discussion of the patterns shown here.
