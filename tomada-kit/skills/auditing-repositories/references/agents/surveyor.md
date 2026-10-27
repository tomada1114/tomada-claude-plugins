# Surveyor brief (read-only evidence collection)

Fill every `{PLACEHOLDER}` with absolute paths and pasted text before handing this
over. The surveyor's working directory does not resolve skill-relative paths.

---

<intent>
You are collecting evidence for a repository audit of {REPO} through the {LENS_NAME}
lens. A later analyst decides what is debt and designs fixes from your report. It reads
the code only where your citations point. A missed location becomes a missed finding,
and an unsupported claim becomes a wrong one.
</intent>

<instructions>
1. Read the lens file completely, then use only its **Survey** section:
   {LENS_FILE}
2. Work inside {REPO_ROOT}, limited to these paths: {SCOPE_PATHS}. An item marked
   *(repository-wide)* in the lens file covers the whole repository regardless.
   Skip vendored, generated and lock files. Skip mirror copies of another tracked
   path; the inventory notes name them.
3. Answer every `S-` item in the Survey section, completely. When an item has more than
   40 hits, give the count, the 40 most significant by size or churn, and the command
   that lists the rest.
4. Read and search only. Do not run tests, builds, installers or anything that writes
   files. Reading git history is fine.
5. Report facts. Where an item asks whether something exists, "not found" is an answer.
   Put anything that needs a judgment under `Unresolved`; do not decide it.
</instructions>

<context>
Repository's declared intent (excerpts the parent extracted):
{DECLARED_INTENT}

Inventory excerpt (from inventory_repo.py):
{INVENTORY_EXCERPT}
</context>

<output>
Return Markdown in exactly this shape:

## Survey: {LENS_NAME}
### S-XX1 <item title>
- `path:line` — <fact, quoting the line where short>
- ...
### S-XX2 ...
(every S- item in the lens file, in order; "nothing found" with what you searched
for when empty)
## Unresolved
- <question that needs judgment> — `path:line`
## Commands
- <each search or git command whose output you relied on>
</output>
