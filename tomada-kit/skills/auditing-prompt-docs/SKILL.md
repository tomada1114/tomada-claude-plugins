---
name: auditing-prompt-docs
description: >-
  Audit and fix prompt-bearing documents — SKILL.md, CLAUDE.md, AGENTS.md, agent
  and command definitions, reference files, whole repositories — against
  Anthropic's published prompting guidance for current Claude models, proposing
  edits for approval before writing anything. Also answers how to prompt a
  specific model: holds the per-model guidance for Claude Fable 5.1, Claude Opus
  5, and Claude Sonnet 5 alongside the cross-model practices. Use when reviewing
  or slimming a CLAUDE.md, AGENTS.md, skill, or agent definition, when
  instructions are being ignored or fire too often, when migrating a prompt to a
  newer model, when asking what makes an instruction good for Claude, or when
  refreshing this guidance after a model release.
metadata:
  platforms: claude-code, codex
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/lint_prompt_doc.py:*)
---

# Auditing prompt docs

Without this skill, prompting advice comes from memory that predates the current
models, and a document review is an eyeball pass. This skill carries the
published guidance and a linter that finds the phrasings that measurably hurt.

## Contract

**Input:** free-form. Either a question about prompting a model, or one or more
targets to audit (a file, a directory, a repository, a skill name). With no
target named for an audit request, ask which one.

**Output:** for a question, an answer grounded in the reference files. For an
audit, a proposal at
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/auditing-prompt-docs/<target-slug>/findings.md`,
then edits to the target — only after the user approves them.

## Path A: answer a prompting question

Read [references/general-practices.md](references/general-practices.md) first; it holds the cross-model practices
and the table of where the three models diverge. Open the file for the model in
question when the answer turns on that model's behavior. Answer from those files
rather than from memory, and say which model a claim is measured on — guidance
for one model is not automatically true of another.

## Path B: audit documents

### 1. Scan

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/lint_prompt_doc.py <target...> --json
```

Directories are walked for SKILL.md, CLAUDE.md, AGENTS.md, and `*.md` under
`agents/`, `commands/`, and `references/`. Any other document has to be passed
as an explicit file path. Exit code 1 means findings, 2 means bad invocation.

[references/rules.md](references/rules.md) holds the rationale and the rewrite for every rule id.
Read the entry before proposing a change; the linter's one-line `fix` is a
label, not the treatment.

### 2. Read for what the linter cannot see

The mechanical findings are the smaller half. Read each document for the
judgment items in [references/rules.md](references/rules.md#what-the-linter-cannot-see) — above all,
instructions that restate behavior the model already has, which are the most
common defect and always a deletion.

Expect the proposal to remove more than it adds. Length is a recurring cost:
every line of a memory file or a skill body is re-read on each run.

Above ten documents, split this reading across parallel workers where the
environment supports it (one `sonnet` worker per group of documents, at most
four; otherwise read them in sequence). Give each worker the document paths, the
linter output for them, and the two reference files, and ask for findings in the
same shape as the linter's — file, line, what is wrong, proposed replacement.

Suppress a false positive rather than contorting the text around it: a document
whose subject *is* prompting will quote anti-patterns legitimately. Add
`<!-- prompt-lint-ignore-file: P002,P003 -->` near the top, or
`<!-- prompt-lint-ignore: P004 -->` on or directly above the line.

### 3. Propose

Write `findings.md` to the output path: one section per document, each item
giving `file:line`, the rule id where one applies, the current text, the
replacement, and one line on why. Rank by whether the item degrades output,
costs context for nothing, or is cosmetic. Deletions state what is being deleted
and why the model no longer needs it.

Present the list and wait for the user to say which items to apply. **Do not
edit any target document before that answer.**

### 4. Apply

Apply the approved items only, then re-run the scan. Findings the user declined
stay declined — record them in `findings.md` rather than raising them again.

## Scope boundary

This skill covers what a document *says*. For a skill's structure — frontmatter
validity, size and link integrity, script conventions, agent neutrality — use
the `creating-agent-skills` skill, whose validators cover that ground. The two
compose: run its structural pass, this skill's wording pass.

## Resources

- [references/general-practices.md](references/general-practices.md) — cross-model practices and the divergence
  table. Read first on any question or audit.
- [references/rules.md](references/rules.md) — every linter rule with its rationale and rewrite, plus
  the judgment items no pattern can catch. Read before proposing changes.
- [references/model-fable-5-1.md](references/model-fable-5-1.md) — Claude Fable 5.1 and Mythos 5.1: progress
  updates, batching, append-only history, writing density, task completion.
- [references/model-opus-5.md](references/model-opus-5.md) — Claude Opus 5: verbosity, over-verification,
  scope, subagent caps, thinking disabled.
- [references/model-sonnet-5.md](references/model-sonnet-5.md) — Claude Sonnet 5: effort ladder, literal
  instruction following, review-harness recall, sampling parameters.
- [references/sources.md](references/sources.md) — which source page and model version each reference
  was collected from, and the refresh procedure to run after a model release.
- `scripts/lint_prompt_doc.py` — run it; do not read it. `--json` for parsing,
  `--list-rules` for the catalog, `--ignore` and `--min-severity` to narrow.
  Standard library only.
- `scripts/tests/test_lint_prompt_doc.py` — `python3 -m unittest discover -s
  scripts/tests -p 'test_*.py'` from the skill directory.

## Maintenance

The per-model files describe models that ship on their own schedule, so they go
stale. [references/sources.md](references/sources.md) records what each file was collected from and the
steps to refresh it; the user decides when to run them.
