<!-- platform-annex -->
# Troubleshooting Guide

Common issues with Claude Code skills and how to fix them.

## Table of Contents

- [Skill not activating](#skill-not-activating)
- [Skill activates at the wrong times](#skill-activates-at-the-wrong-times)
- [Description is cut short in the listing](#description-is-cut-short-in-the-listing)
- [Frontmatter parsed as empty](#frontmatter-parsed-as-empty)
- [Files not loading](#files-not-loading)
- [Tool restrictions not working](#tool-restrictions-not-working)
- [Portable-skill validation errors](#portable-skill-validation-errors)
- [Performance issues](#performance-issues)
- [YAML syntax errors](#yaml-syntax-errors)
- [Debugging checklist](#debugging-checklist)

---

## Skill not activating

### Diagnosis order

Work down this list — the causes are ordered by how often they turn out to be the real one.

1. **Description keywords.** Does it contain the words a user would actually say? The body is loaded only *after* selection, so trigger keywords living there are never seen.

2. **Frontmatter parsed at all.** A malformed YAML block loads the body with *empty* metadata — `/skill-name` still works, so the skill looks fine while Claude has no description to match. See [Frontmatter parsed as empty](#frontmatter-parsed-as-empty).

3. **`disable-model-invocation: true`.** This removes the description from context entirely, by design. The skill is then user-invocable only.

4. **`paths` gating.** If set, automatic activation only happens when the current work touches matching files. Manual invocation is unaffected — so "works with `/name`, never fires on its own" points straight here.

5. **Description truncated out of the listing.** In a large skill collection the tail of a description can be dropped. See [Description is cut short in the listing](#description-is-cut-short-in-the-listing).

6. **Name format.** Lowercase, digits, hyphens; no leading/trailing hyphen, no consecutive hyphens; must match the directory name.
   ```bash
   echo "my-skill-name" | grep -E '^[a-z0-9]+(-[a-z0-9]+)*$'
   ```

7. **File location.**
   ```bash
   ls -la ~/.claude/skills/<name>/SKILL.md    # personal
   ls -la .claude/skills/<name>/SKILL.md      # project
   ```

8. **Permission rules.** Claude can invoke any skill by default, but deny rules override that: a bare `Skill` deny blocks all of them, `Skill(deploy *)` blocks one. Check `/permissions` before concluding the skill itself is at fault.

9. **Ask directly.** `What skills are available?` shows what actually reached the model's context — the fastest way to distinguish "not loaded" from "loaded but not matching".

Note that `user-invocable: false` controls menu visibility only; it never blocks Claude from loading the skill. Only `disable-model-invocation: true` (or a deny rule) does that.

Run `claude --debug` to see frontmatter parse errors and skill-listing warnings; `/doctor` reports the listing's context cost.

### Common causes

| Symptom | Likely cause | Fix |
|---|---|---|
| Never activates, `/name` works | Malformed YAML, or `disable-model-invocation` | Fix the frontmatter, or accept manual-only |
| Never activates on its own | `paths` gate, or vague description | Widen/remove `paths`; add trigger keywords |
| Activates but ignores half the instructions | Body too long, or the rule sits below where it stopped reading | Move load-bearing rules up; split into references |
| Claude doesn't know it exists | Wrong directory, or listing budget overflow | Check the location; see the budget section |

## Skill activates at the wrong times

1. **Make the description narrower.**
   ```yaml
   # Bad
   description: Helps with testing
   # Good
   description: Generate Jest tests for React components with hooks and async testing. Use when testing React hooks, async components, or writing Jest tests.
   ```

2. **Differentiate near-neighbors.** Overlapping skills need distinct technology names, action verbs, and "Use when…" clauses — not longer descriptions.

3. **Measure it.** Selection accuracy is testable: write should-trigger and should-not-trigger prompts and check the hit rate. See `evaluating-skills.md` (load via SKILL.md).

4. **Last resort:** `disable-model-invocation: true` makes the skill manual-only.

Negative triggers in the *body* ("Don't use for Python testing") don't prevent activation — the body loads after the decision. They only help the model bail out early once loaded.

## Description is cut short in the listing

Claude Code loads a listing of every skill's name and description. Names are always included; descriptions are budgeted:

- Per entry, `description` + `when_to_use` are capped at **1,536 characters** (`skillListingMaxDescChars`).
- The whole listing is capped at ~1% of the context window (`skillListingBudgetFraction`, or a fixed count via `SLASH_COMMAND_TOOL_CHAR_BUDGET`).
- On overflow, descriptions are dropped **starting with the skills you invoke least**.

Fixes, in order of preference:

1. Put the key use case in the first sentence — truncation cuts from the end.
2. Set low-priority skills to `"name-only"` in `skillOverrides` to free budget for the rest.
3. Raise `skillListingBudgetFraction` (e.g. `0.02`).

`/doctor` estimates the cost and names the biggest contributors. The Skills row in `/context` reports the post-budget size — what the model actually receives.

## Frontmatter parsed as empty

Symptom: `/skill-name` works, the body clearly loads, but Claude never selects the skill and `What skills are available?` shows it with no description.

Cause: the YAML block failed to parse. Claude Code degrades gracefully here — body loaded, metadata empty — so nothing looks broken.

```bash
claude --debug    # prints the parse error
python3 ${CLAUDE_SKILL_DIR}/scripts/validate_skill.py <skill-path>
```

Usual culprits are in [YAML syntax errors](#yaml-syntax-errors): an unquoted colon inside `description`, a tab character, or an unterminated `---`.

## Files not loading

1. **Use plain relative paths** from the skill root:
   ```markdown
   # Wrong
   See [reference](./reference.md)
   # Correct
   See [reference](references/reference.md)
   ```

2. **Keep references one level deep.** A reference that points to another reference gets partially read — Claude previews nested files with `head` rather than reading them whole, and acts on incomplete information. Every reference should be linked directly from SKILL.md.

3. **Forward slashes only**, on every platform. `scripts\helper.py` fails on Unix.

4. **Verify existence and permissions:**
   ```bash
   ls -la ~/.claude/skills/<name>/
   chmod 644 ~/.claude/skills/<name>/**/*.md
   ```

## Tool restrictions not working

```yaml
# Wrong
allowed_tools: Read, Grep, Glob    # underscore

# Correct — all three forms work
allowed-tools: Read, Grep, Glob
allowed-tools: Read Grep Glob
allowed-tools:
  - Read
  - Bash(gh:*)
```

Two distinct fields, frequently confused:

- `allowed-tools` — **pre-approves** tools so they run without a permission prompt. It does not restrict anything.
- `disallowed-tools` — **removes** tools from Claude's pool while the skill is active.

Both clear when the user sends the next message. To restrict tools permanently, use deny rules in permission settings.

**Valid tool names:** `Read`, `Write`, `Edit`, `Grep`, `Glob`, `Bash`, `WebFetch`, `WebSearch`, `Task`, `Skill`, `TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet`, `AskUserQuestion`, `NotebookEdit`.

MCP tools need their fully qualified name (`ServerName:tool_name`, e.g. `BigQuery:bigquery_schema`) both here and in skill prose — a bare tool name fails to resolve when multiple MCP servers are connected.

## Portable-skill validation errors

The Agent Skills standard defines only `name`, `description`, `license`, `compatibility`, `metadata`, and `allowed-tools`. Every other field listed in `yaml-spec.md` (load via SKILL.md) is a Claude Code extension.

Validating with the standard's reference tool flags the extensions:

```bash
skills-ref validate ./my-skill
```

This matters only for skills you intend to publish as portable. A Claude-Code-only skill should use the extensions freely and skip this check.

For portability specifically to **Codex CLI** (not just the abstract standard), the check that matters is `dual-platform-skills/scripts/neutrality_lint.py <skill>` — it catches raw tool names and Claude-namespaced paths leaking into body text, which the standard's own validator doesn't check. See [agent-neutral-authoring.md](agent-neutral-authoring.md).

## Performance issues

1. **SKILL.md too large.** Target <500 lines; the validator warns at 500 and errors at 800. Once loaded, the body stays in context across turns — every line is a recurring cost, not a one-time one.
2. **Too many skills matching.** Narrow the descriptions; split monoliths; set rarely-used skills to `"name-only"`.
3. **Heavy computation in prose.** Move it into `scripts/` — script source never enters context, only its output.
4. **Expensive `` !`command` `` injection.** Injected output lands in context on every invocation, before the model decides it needs it. Keep injected commands bounded.

## YAML syntax errors

```yaml
# Missing space after colon
name:skill-name          # Wrong
name: skill-name         # Correct

# Unquoted colon inside a value
description: Use for: testing & debugging      # Wrong
description: "Use for: testing & debugging"    # Correct

# Tabs instead of spaces
name:	skill-name        # Wrong (tab)
name: skill-name         # Correct
```

Long descriptions are easiest to keep valid with a folded block:

```yaml
description: >-
  First sentence carries the key use case.
  Continuation lines need no quoting, and colons are safe here.
```

## Debugging checklist

- [ ] SKILL.md exists at the right location
- [ ] Frontmatter parses (`claude --debug` shows no error)
- [ ] `name` is kebab-case and matches the directory name
- [ ] Description leads with the key use case and contains trigger keywords
- [ ] No `disable-model-invocation` / `paths` gate you forgot about
- [ ] Description survives the listing budget (`/doctor`)
- [ ] Referenced files exist, are one level deep, and use forward slashes
- [ ] `allowed-tools` / `disallowed-tools` spelled with hyphens
- [ ] MCP tools fully qualified (`Server:tool`)
- [ ] SKILL.md body under the 500-line target (validator warns at 500, errors at 800)
- [ ] Standard-only fields, if the skill is meant to be portable
