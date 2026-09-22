# Sub-agent prompt: repository surveyor

Two surveyors run per transplant, one per repository, as `executor`. Fill every
placeholder with an absolute path before sending — a spawned context does not resolve
paths relative to this skill — and send both spawns together so they run at the same
time. Where the environment has no sub-agents, work through the same instructions inline,
once per repository.

Placeholders: `{REPO_PATH}`, `{ROLE}` (`reference` or `target`), `{RUBRIC_PATH}`,
`{OUTPUT_PATH}`, `{OTHER_REPO_NAME}`.

---

```
<intent>
You are surveying one of two repositories. A harness transplant is being planned: the
reference repository's development harness is being translated into the target
repository's stack, and the result will be filed as GitHub issues. Your inventory is one
half of the comparison that decides what gets proposed. It is the only view of this
repository the planner will have before it opens files itself, so a missing row becomes
a missing issue.
</intent>

<context>
Repository to survey: {REPO_PATH}
Its role in this transplant: {ROLE}
The other repository, which you are not surveying: {OTHER_REPO_NAME}

Read only inside {REPO_PATH}. Write only {OUTPUT_PATH}. Change nothing else.
</context>

<instructions>
1. Read {RUBRIC_PATH} completely first. It defines the item IDs (R1.1 … R9.5) and the
   S0-S5 strength ladder you will report against.

2. Survey the repository against every item. The files that carry harness signal are
   usually: root policy and community-health documents, the task runner definition,
   version-manager and tool-pinning files, hook configuration, everything under the CI
   configuration directory, linter and formatter configuration, test and coverage
   configuration, the dependency manifest and its lockfile, agent skill and rule
   directories, and repository scripts. Read the files rather than inferring from names.

3. Where a check runs but its strictness is not visible in the file, say so rather than
   assuming: an advisory-only job, a threshold set elsewhere, a required check that may
   or may not be enforced on the branch.

4. Write the full inventory to {OUTPUT_PATH}, then return the summary described below.
</instructions>

<output_contract>
{OUTPUT_PATH} is markdown, one table per rubric area, one row per item, every item
present including the ones that do not apply:

| ID | Strength | Confidence | Evidence | Notes |
|---|---|---|---|---|
| R4.3 | S1 | medium | justfile:12, .githooks/pre-commit:1 | hooks installed only by `just install`; nothing verifies afterwards, no opt-out documented |
| R7.8 | S0 | low | — | no branch protection visible from the files; needs an API check |

- Strength is S0-S5 from the rubric, or `n-a` with a one-line reason.
- Confidence is high / medium / low, and low is a useful answer — report every item you
  looked at, with whatever confidence it deserves. Nothing is filtered out here; the
  planner does the filtering in a later phase.
- Evidence is `path:line`, comma-separated, or `—` for an absence.
- Notes is at most two lines, naming the specific mechanism or the specific hole.

After the tables, two short sections:

## EXTRA
Harness strengths this repository has that the rubric does not name. One line each with
evidence. This is where the rubric's own blind spots surface.

## UNRESOLVED
Anything that needed a judgment call you were not in a position to make, or a fact that
needs a command or an API call to settle. State the question, not a guess.

Return to the caller a summary of at most 400 words: the count of items at each strength
level per area, the five weakest items with their IDs, everything under EXTRA, and
everything under UNRESOLVED. Do not restate the tables — the caller reads the file.
</output_contract>
```
