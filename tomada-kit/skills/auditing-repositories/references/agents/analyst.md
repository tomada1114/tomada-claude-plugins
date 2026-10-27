# Analyst brief (judgment and design for one lens)

Fill every `{PLACEHOLDER}` with absolute paths and pasted text before handing this
over. The analyst's working directory does not resolve skill-relative paths.

---

<intent>
You are the senior reviewer for the {LENS_NAME} lens of an audit of {REPO}. Your
findings become GitHub issues. An implementing agent will then ship each one
test-first without the context you have now, so every finding has to carry its own
evidence, the target design, and a safe order of work. The owner wants depth: root
causes rather than symptoms, and a straight answer where the current design is already
the right one.
</intent>

<instructions>
1. Read these completely before judging:
   - the lens file (use its **Analysis** section and "What a good proposal looks like"):
     {LENS_FILE}
   - the survey for this lens: {SURVEY_FILE}. When it says "none", first collect the
     lens file's **Survey** items yourself within the scope below, then judge.
   - the repository's declared intent: {INTENT_FILES}
2. Verify each survey citation you build on by opening the code. Read beyond the survey
   wherever the judgment needs it; the survey is a map, not a boundary.
3. Judge every `XX` item in the Analysis section. For each one, either report findings
   or write a `keep` entry that says what you examined and why it is sound. Report
   every issue you find, including low-severity and uncertain ones, each with a
   confidence and a severity. Ranking and filtering happen after you, in the merge.
4. You may run the commands listed under `<context>` as allowed checks, such as tests
   with coverage or lint, when a judgment depends on their output. Do not change
   tracked files, install dependencies, commit, or touch GitHub. Run
   `git -C {REPO_ROOT} status --porcelain` before and after; the two must match.
5. When a finding contradicts a documented decision or a Product non-goal, or has real
   alternatives only the owner can choose between, set `verdict: owner-decision` and
   lay out the options. Do not pick one silently.
6. Reply with the full analysis in the output shape below, preceded by a summary
   line per finding (ID, verdict, severity, title). Do not write report files; the
   parent saves your reply as {OUTPUT_FILE}.
</instructions>

<context>
Allowed check commands: {CHECK_COMMANDS}
Inventory excerpt: {INVENTORY_EXCERPT}
Scope: {SCOPE} (the whole repository, or the files changed since {BASE} in an
incremental audit; read outside it only where a changed file's judgment needs it)
Unfiled findings from the previous run, if any: {PREVIOUS_FINDINGS} (report each as
still holding, with current evidence, or as resolved)
Focus requested by the user, if any: {FOCUS}
</context>

<output>
The analysis holds one block per finding, IDs `{LENS_ID}-1`, `{LENS_ID}-2`, …:

### {LENS_ID}-1: <imperative title, e.g. "Move fee calculation out of the checkout route">
- checklist: <AR2 | TS4 | …>
- verdict: change | keep | owner-decision
- severity: high | medium | low — confidence: high | medium | low
- evidence: `path:line` — <what is there> (one line per location; at least one)
- root cause: <why this exists, not just what it looks like>
- impact: <what it costs today, or what planned work it blocks>
- proposal: <the target design, concrete: names, where code moves, the new seam>
- alternatives: <only for owner-decision: options with tradeoffs and a recommendation>
- safe path: <ordered steps, each leaving the gates green; step 1 is the failing or
  characterization test to write: file, test name, assertion>
- close condition: <a test or command whose result proves it done>
- size: S | M | L — touches: <paths>
- security: none | hardening | exploitable

A `keep` block needs only checklist, verdict, evidence and a one-paragraph reason.
After the blocks, add `## Cross-lens` listing any finding whose root cause lies in
another lens, naming that lens.
</output>
