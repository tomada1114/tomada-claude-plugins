<!-- platform-annex -->
# Frontmatter Fields and Content Substitutions

Reference for the YAML frontmatter of `SKILL.md` and for the placeholders Claude Code substitutes into skill content.

Three sources define these fields, and they are not the same set:

- **Agent Skills standard** ([agentskills.io](https://agentskills.io/specification)) — portable across tools, including Codex CLI. `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`.
- **Claude Code extensions** — everything else in the field summary below. Codex ignores these harmlessly (it reads only `name`/`description`/`metadata`). Portable skills should avoid making body logic *depend* on them; skills that only ever run in Claude Code should use them freely.
- **Codex extensions** — live entirely under `metadata` (the standard field both hosts read), so there is no separate frontmatter block for them. The one this skill set uses is `metadata.platforms: claude-code, codex` (or `claude-code` alone) — see `agent-neutral-authoring.md` (load via SKILL.md). Codex's own UI-facing hint is `metadata.short-description`. A skill's `agents/openai.yaml` (invocation policy / UI metadata) is a separate optional file, not a frontmatter field.

## Table of Contents

- [Field summary](#field-summary)
- [Standard fields](#standard-fields)
- [Claude Code extension fields](#claude-code-extension-fields)
- [How the description actually reaches the model](#how-the-description-actually-reaches-the-model)
- [Diagnosing activation](#diagnosing-activation)
- [Content substitutions](#content-substitutions)
- [Bash injection in skill content](#bash-injection-in-skill-content)

---

## Field summary

```yaml
---
# Agent Skills standard
name: skill-identifier                   # Max 64 chars, kebab-case
description: What it does + when to use  # Max 1024 chars
license: MIT                             # Optional
compatibility: Requires git and jq       # Optional, max 500 chars, env requirements
metadata:                                # Optional, arbitrary string map (both hosts read this key)
  author: tomada
  platforms: claude-code, codex          # Codex-recognized; drives dual-platform-skills' neutrality lint
  short-description: One-line UI hint    # Codex UI only
allowed-tools: Read Grep Glob            # Optional (experimental in the standard)

# Claude Code extensions
when_to_use: "Trigger phrases, example requests"
argument-hint: "[issue-number]"
arguments: [issue, branch]               # Named positional args for $issue / $branch
disable-model-invocation: false
user-invocable: true
disallowed-tools: AskUserQuestion
model: <alias>                           # opus / sonnet / haiku / fable / inherit
effort: high                             # low | medium | high | xhigh | max
context: fork
agent: Explore                           # only with context: fork
background: true                         # only with context: fork
paths: "src/**/*.ts"                     # activate only when working these files
hooks: {}
shell: bash                              # bash (default) | powershell
---
```

All fields are optional to Claude Code; only `description` is genuinely load-bearing. Boolean fields accept `yes`/`no`/`on`/`off`/`1`/`0` in any case as well as `true`/`false` (v2.1.218+).

---

## Standard fields

### `name`

**Type:** String | **Max:** 64 characters

**Rules:**
- Lowercase letters, digits, hyphens only
- Must not start or end with a hyphen
- Must not contain consecutive hyphens (`pdf--processing` is invalid)
- Must match the parent directory name
- Reserved words prohibited: `anthropic`, `claude` — enforced by `validate_skill.py`'s `E013`

**What it controls in Claude Code:** in a personal or project skill, `name` sets only the display label in skill listings — the command you type still comes from the directory name. In a **plugin** skill, `name` replaces the last segment of the command, so `my-plugin/skills/review/SKILL.md` with `name: fancy` becomes `/my-plugin:fancy`. Keeping `name` equal to the directory name avoids the whole class of confusion.

**Naming convention — gerund form (`-ing`) recommended:**

```yaml
# Good
name: processing-pdfs
name: reviewing-code

# Acceptable
name: pdf-processing       # noun phrase
name: process-pdfs         # imperative

# Invalid
name: API-Docs-Writer      # uppercase
name: api_docs_writer      # underscores
name: -api-docs            # leading hyphen
name: claude-helper        # reserved word
```

### `description`

**Type:** String | **Max:** 1024 characters (standard) | **Default:** first paragraph of the body

**The description is the primary trigger mechanism.** All "when to use" information belongs here, not in the body — the body loads only *after* the skill has been selected, so trigger keywords in the body are never seen during selection.

**Structure:**
```
[Action verbs] + [specific technologies/frameworks] + [problem solved].
Use when [scenario 1], [scenario 2], or [working with keywords].
```

Write in **third person**. The description is injected into the system prompt, and first/second person ("I can help you…", "You can use this to…") degrades selection — `validate_skill.py`'s `W024` flags the common patterns.

Write in **English only**, even for a skill whose user speaks Japanese. Selection matches on meaning, so a Japanese request reaches an English description without a mirrored keyword list — and mirroring spends the character budget that truncation eats first.

**Good:**
```yaml
description: >-
  Generate OpenAPI/Swagger documentation from Express routes, FastAPI endpoints,
  or GraphQL schemas. Analyzes code structure and creates comprehensive API
  specifications with request/response examples. Use when documenting APIs,
  creating API specs, or working with OpenAPI, Swagger, REST, GraphQL, API design.
```

**Bad:**
```yaml
description: This skill handles database operations.
# No "Use when..." clause, no specific databases, no trigger keywords
```

Put the most important use case **first** — the text is truncated from the end. See [How the description actually reaches the model](#how-the-description-actually-reaches-the-model).

### `license`

**Type:** String

License name, or the name of a bundled license file. Keep it short.

```yaml
license: MIT
license: Proprietary. LICENSE.txt has complete terms
```

### `compatibility`

**Type:** String | **Max:** 500 characters

Environment requirements — intended product, required system packages, network access. **Not** a Claude Code version constraint.

```yaml
compatibility: Designed for Claude Code (or similar products)
compatibility: Requires git, docker, jq, and access to the internet
compatibility: Requires Python 3.14+ and uv
```

Most skills do not need this field.

### `metadata`

**Type:** Map of string to string

Arbitrary properties not defined by the standard. Use reasonably unique key names to avoid collisions between tools.

```yaml
metadata:
  author: tomada
  version: "1.0"
```

### `allowed-tools`

**Type:** Space-separated string, comma-separated string, or YAML list

Tools Claude may use **without a permission prompt** during the turn that invokes the skill. The grant clears when the user sends the next message.

```yaml
allowed-tools: Read, Grep, Glob
allowed-tools: Bash(gh:*)
allowed-tools:
  - Read
  - Bash(git status:*)
```

In the Agent Skills standard this field is space-separated and marked experimental; Claude Code accepts all three forms.

> **Naming note:** the field grants pre-approval, it does not sandbox. To *remove* a tool from Claude's pool, use [`disallowed-tools`](#disallowed-tools); to block a tool globally, use deny rules in permission settings.

> **Default: omit this field.** The permission prompt is a safety check the user sees; pre-approving tools by default removes it for no reason tied to the skill's actual needs. Write it only for one of two reasons:
> 1. Pre-approving the skill's own bundled scripts — `Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/x.py:*)`.
> 2. An unattended or background run that must not stall waiting on a prompt.
>
> If the goal is to actually restrict what the skill can touch, that's [`disallowed-tools`](#disallowed-tools), not this field — it's outside this default.

When one of those reasons applies, common patterns: `Read, Grep, Glob` (read-only analysis) · `Read, Grep, Glob, Write` (docs generation) · `Read, Bash` (validation runs).

---

## Claude Code extension fields

### `when_to_use`

**Type:** String

Additional trigger context — phrases users say, example requests. Appended to `description` in the skill listing and counted against the same 1,536-character cap.

```yaml
description: Generates release notes from merged PRs.
when_to_use: >-
  Use when the user says "cut the release notes", "draft the changelog",
  "what shipped this week", or asks to summarize merged PRs.
```

Useful when the "what it does" sentence and the trigger vocabulary would otherwise fight for the same field. Splitting them keeps the description readable without losing keywords.

### `argument-hint`

**Type:** String

Hint shown during `/` autocomplete.

```yaml
argument-hint: "[issue-number]"
argument-hint: "[filename] [format]"
```

### `arguments`

**Type:** Space-separated string or YAML list

Declares named positional arguments, which become `$name` placeholders in the body. Names map to positions in order.

```yaml
arguments: [issue, branch]
---
Fix issue #$issue on branch $branch.
```

A named placeholder with no matching argument expands to an empty string.

### `disable-model-invocation`

**Type:** Boolean | **Default:** `false`

| Value | User invokes | Claude invokes | Use case |
|---|---|---|---|
| `false` | Yes | Yes | General skills |
| `true` | Yes | No | Deploy, commit, send — timing-sensitive |

Setting `true` removes the description from context entirely. It also prevents the skill from being preloaded into subagents, and (v2.1.196+) from running when a scheduled task fires with the skill as its prompt.

### `user-invocable`

**Type:** Boolean | **Default:** `true`

| Value | Menu visible | Claude can load | Use case |
|---|---|---|---|
| `true` | Yes | Yes | Normal skills |
| `false` | No | Yes | Background knowledge users shouldn't invoke |

With `user-invocable: false` the description stays in context permanently — that is the point of the field, and also its cost.

### `disallowed-tools`

**Type:** Space/comma-separated string or YAML list

Tools **removed** from Claude's pool while the skill is active. The restriction clears on the user's next message.

```yaml
disallowed-tools: AskUserQuestion
```

Main use: autonomous or background skills that must never stop to ask. The field cannot remove `EndConversation` while any other tool remains.

### `model`

**Type:** String — an alias (`fable` / `opus` / `sonnet` / `haiku`) or `inherit`

Model used while the skill is active. The override applies for the rest of the current turn and is not saved; the session model resumes on the next prompt. Use aliases — full dated IDs (`claude-*-YYYYMMDD`) go stale.

> **Default: omit this field.** Skills that involve judgment, review, or writing should inherit the session model. Pin explicitly only to cost-optimize bulk mechanical work (`model: haiku`).

> **Sub-agent models are separate.** This field sets the model for the skill's *own* turn, never for sub-agents the skill spawns. Set those per spawn — see `prompt-authoring.md` and A6 in `orchestration-patterns.md` (both loaded via SKILL.md).

A model excluded by an organization's `availableModels` allowlist is ignored and the session keeps its current model.

### `effort`

**Type:** `low` | `medium` | `high` | `xhigh` | `max` | **Default:** inherits the session

Reasoning effort while the skill is active. Available levels depend on the model. Lowering effort is the first cost lever to try before dropping to a cheaper model.

### `context`

**Type:** `fork`

Runs the skill in an isolated forked subagent context. The skill content becomes the subagent's prompt; conversation history is not available to it.

**`context: fork` is for Task Contents (active skills), not Reference Contents (passive skills).** A forked agent needs to know *what to do*; a guidelines-only skill leaves it with no objective.

**Correct (Task Contents):**
```yaml
---
name: pr-opener
context: fork
---
## Your Task
1. Get the current branch diff: `git diff main...HEAD`
2. Generate a PR title from the commits
3. Create the PR: `gh pr create --title "..." --body "..."`
```

**Incorrect (Reference Contents):**
```yaml
---
name: coding-standards
context: fork
---
## Guidelines
- Use TypeScript strict mode
# No explicit task — the forked agent has nothing to do
```

### `agent`

**Type:** String | Only with `context: fork`

Which subagent type runs the fork. Built-ins include `Explore` (read-only), `Plan` (no Edit/Write), `general-purpose` (default, all tools); custom agent names from `.claude/agents/` also work.

### `background`

**Type:** Boolean | **Default:** `true` | Only with `context: fork` | Requires v2.1.218+

By default a forked skill runs in the background and its result arrives later in the conversation. Set `background: false` to block the invoking turn and get the result inline — use this when the rest of the turn depends on the fork's output.

### `paths`

**Type:** Comma-separated string or YAML list of globs

Limits automatic activation to work touching matching files. Uses the same format as path-specific memory rules.

```yaml
paths:
  - "src/**/*.tsx"
  - "**/*.test.ts"
```

A skill that never seems to trigger is often gated here. Manual `/skill-name` invocation is unaffected.

### `hooks`

**Type:** Object

Hooks scoped to this skill's lifecycle. Configuration format matches the hooks documentation.

### `shell`

**Type:** `bash` (default) | `powershell`

Shell used for `` !`command` `` injection and ` ```! ` blocks in this skill.

---

## How the description actually reaches the model

The standard caps `description` at 1,024 characters, but that is not the only limit that matters in Claude Code:

1. **Per-entry cap:** `description` + `when_to_use` combined are truncated at **1,536 characters** in the skill listing (configurable via `skillListingMaxDescChars`).
2. **Listing budget:** the whole listing is capped at ~1% of the model's context window (`skillListingBudgetFraction`, or a fixed char count via `SLASH_COMMAND_TOOL_CHAR_BUDGET`). Names are always listed; when the budget overflows, **descriptions are dropped starting with the skills invoked least**.

Consequences for authoring:

- Put the key use case in the **first sentence**. Truncation cuts from the end.
- A description that is technically under 1,024 chars can still lose its tail in a large skill collection.
- To free budget, set low-priority skills to `"name-only"` in the `skillOverrides` setting rather than trimming skills you actually use.
- `/doctor` estimates the listing's context cost and names the biggest contributors; the Skills row in `/context` reports the post-budget size.

---

## Diagnosing activation

### Never activates

Work down this list — ordered by how often each turns out to be the real cause:

1. **Description keywords** — does it contain words a user would actually say? The body loads only after selection, so trigger keywords living there are never seen.
2. **Frontmatter parsed at all** — malformed YAML loads the body with *empty* metadata, so `/skill-name` still works while Claude has no description to match. `claude --debug` prints the parse error.
3. **`disable-model-invocation: true`** — removes the description from context entirely; the skill becomes user-invocable only.
4. **`paths` gating** — automatic activation only fires when the current work touches matching files; manual invocation is unaffected.
5. **Listing truncation** — see [How the description actually reaches the model](#how-the-description-actually-reaches-the-model) above.
6. **Name format** — lowercase, digits, hyphens; no leading/trailing or consecutive hyphens; must match the directory name.
7. **File location** — `~/.claude/skills/<name>/SKILL.md` (personal) or `.claude/skills/<name>/SKILL.md` (project).
8. **Permission deny rules** — a bare `Skill` deny blocks every skill; `Skill(name *)` blocks one. Check permission settings before concluding the skill itself is at fault.
9. **Ask directly** — "What skills are available?" shows what actually reached the model's context, the fastest way to tell "not loaded" from "loaded but not matching."

`user-invocable: false` controls menu visibility only — it never blocks automatic loading; only `disable-model-invocation: true` or a deny rule does that.

### Activates at the wrong times

- Narrow the description — add specific technologies, action verbs, and a "Use when…" clause instead of a vague summary.
- Differentiate near-neighbors with distinct trigger vocabulary, not just longer descriptions.
- Measure it: write should-trigger and should-not-trigger prompts and check the hit rate (`evaluating-skills.md`, load via SKILL.md).
- Last resort: `disable-model-invocation: true` makes the skill manual-only.

Negative triggers in the body ("Don't use for Python testing") do not prevent activation — the body loads only after the decision. They only help the model bail out early once loaded.

### YAML gotchas

```yaml
name:skill-name          # Wrong — missing space after colon
description: Use for: testing & debugging      # Wrong — unquoted colon inside a value
name:	skill-name        # Wrong — tab instead of space
```

Long descriptions are easiest to keep valid with a folded block, which needs no quoting and tolerates internal colons:

```yaml
description: >-
  First sentence carries the key use case.
  Continuation lines need no quoting, and colons are safe here.
```

---

## Content substitutions

Claude Code substitutes these placeholders into the skill body before the model sees it.

| Placeholder | Expands to |
|---|---|
| `$ARGUMENTS` | All arguments passed at invocation. If absent from the body, arguments are appended as `ARGUMENTS: <value>`. |
| `$ARGUMENTS[N]` | A single argument by 0-based index. |
| `$N` | Shorthand for `$ARGUMENTS[N]` — `$0` is the first argument. An index with no argument stays in the text unchanged. |
| `$name` | Named argument declared in the [`arguments`](#arguments) field. |
| `${CLAUDE_SKILL_DIR}` | Directory containing this `SKILL.md`. For plugin skills, the skill's subdirectory — not the plugin root. |
| `${CLAUDE_PROJECT_DIR}` | Project root, the same path hooks and MCP servers receive. |
| `${CLAUDE_SESSION_ID}` | Current session ID. Useful for per-session workspaces and log files. |
| `${CLAUDE_EFFORT}` | Current effort level (`low`…`max`; ultracode reports as `xhigh`). Lets a skill scale its own depth. |

**Use `${CLAUDE_SKILL_DIR}` for every bundled script and asset path.** A hardcoded `~/.claude/skills/<name>/…` breaks the moment the skill is installed as a plugin or committed to a project, and it silently invokes the *wrong copy* when both exist.

`${CLAUDE_SKILL_DIR}` and `${CLAUDE_PROJECT_DIR}` are substituted in two places — the markdown body **and** Bash rules in `allowed-tools`. Using the same variable in both lets a skill run its own script with no permission prompt:

````markdown
---
name: checking-deps
description: Audits dependency versions against the lockfile.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/check_deps.py:*)
---

Run the dependency check and report what it prints:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/check_deps.py --json
```
````

---

## Bash injection in skill content

A line beginning with `` !`command` `` runs the command and injects its output into the skill content before the model reads it. This is how a skill arrives already knowing the current state instead of spending tool calls discovering it.

```yaml
---
name: pr-summary
context: fork
agent: Explore
allowed-tools: Bash(gh:*)
---

## Context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`

## Task
Summarize this PR, focusing on behavior changes reviewers must verify.
```

Keep injected commands cheap and bounded — the output lands in context every single invocation, before the model has decided whether it needs it. A `git log -5` is fine; a full `git log` is not.
