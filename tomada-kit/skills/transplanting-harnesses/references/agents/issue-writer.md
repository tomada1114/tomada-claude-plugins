# Sub-agent prompt: issue body writer

One `executor` spawn, used only when the plan holds more than 8 issues. Below that the
bodies are quicker to write inline than to specify. By the time this runs the spec is
settled — the gap table is decided, the priorities and dependency edges are fixed — so
the work is transcription into a fixed skeleton, not judgment.

Fill every placeholder with an absolute path or with literal content before sending; a
spawned context resolves nothing relative to this skill. `{ISSUE_SPEC}` is a block
pasted into the prompt, one entry per issue: key, title, priority, area, touches,
depends_on, the rubric items it closes, the evidence lines for the target's current
state, and the `docs/harness-reference/` paths it may cite.

Placeholders: `{TEMPLATE_PATH}`, `{BODIES_DIR}`, `{TARGET_REPO_PATH}`, `{ISSUE_SPEC}`.

---

```
<intent>
You are writing the issue bodies for a development-harness transplant. Each body will be
filed as a GitHub issue and implemented by someone who has never seen the repository it
was modelled on and cannot open it. Everything they need is in your body or in their own
checkout under docs/harness-reference/. A vague step here becomes a stalled issue later.
</intent>

<instructions>
1. Read {TEMPLATE_PATH} completely: it is the skeleton, the rules about what the script
   appends, and a worked example of the level of detail expected.

2. For each entry in <issue_spec>, write {BODIES_DIR}/<key>.md following that skeleton.
   Open the files named in the entry's evidence lines under {TARGET_REPO_PATH} so the
   Background section and the Steps cite real paths and real line numbers. Do this for
   every entry, not only the first.

3. Steps are exact: the file to edit, the command to run, the string to add. Verification
   columns and acceptance criteria name a command whose result changes when the work is
   done.

4. Write nothing outside {BODIES_DIR}, and change nothing in {TARGET_REPO_PATH}.
</instructions>

<issue_spec>
{ISSUE_SPEC}
</issue_spec>

<output_contract>
- One file per key, named <key>.md, containing only the sections in the template.
- Never write a `## Dependencies` section, a `<!-- ship: … -->` comment, or a
  `<!-- harness-transplant: … -->` marker: the creation script appends all three, and a
  hand-written copy is duplicated or contradicted.
- Refer to other issues in the plan as {{#key}} in prose. A literal issue number is
  wrong — the numbers do not exist yet.
- Every reference-material path is inside the target repository, under
  docs/harness-reference/. No absolute path, no path in a clone, no URL to the source
  repository.
- The implementer sees only the issue. Never mention plan.json, this spec, or any
  planning file; ordering between issues is expressed as {{#key}} and by the
  Dependencies section the script appends.
- Write "after", "depends on", "blocked by", "requires" or "blocks" next to a {{#key}}
  only for an edge the spec declares. Downstream tooling reads those phrasings as
  dependencies; for a loose ordering remark write "once {{#key}} lands".
- Match the body's length to the work: a file-copy issue does not need a Translation
  notes table or five requirements.

Return a list of the files written, and — separately — any entry you could not write
completely, naming the specific fact that was missing rather than filling the gap with a
plausible one.
</output_contract>
```
