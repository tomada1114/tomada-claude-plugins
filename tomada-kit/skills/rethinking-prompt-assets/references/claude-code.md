# Claude Code specifics

## Table of Contents

- [Where the estate lives](#where-the-estate-lives)
- [Tools for each step](#tools-for-each-step)
- [The live listing](#the-live-listing)
- [How blind the designer really is](#how-blind-the-designer-really-is)
- [Parts and their own side effects](#parts-and-their-own-side-effects)
- [Follow-ups after applying moves](#follow-ups-after-applying-moves)

## Where the estate lives

| Scope | Configuration root | Extra memory files |
|---|---|---|
| User level (the default) | `~/.claude`: `CLAUDE.md`, `AGENTS.md`, `skills/`, `commands/`, `agents/` | none |
| A repository | `<repo>/.claude` | `--memory <repo>/CLAUDE.md --memory <repo>/AGENTS.md` |

Session transcripts are under `~/.claude/projects`, one directory per working
directory. The whole-estate collector call:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/collect_estate.py ~/.claude \
  --transcripts ~/.claude/projects --json > "$RUN/evidence.json"
```

The scan reads every session file and takes on the order of twenty seconds for a few
gigabytes. For a repository, keep `--transcripts ~/.claude/projects`: the usage of the
repository's skills is recorded there too.

## Tools for each step

| Step | Tool |
|---|---|
| Needs round (Phase 1), approval round (Phase 5), removal confirmation (Phase 6) | `AskUserQuestion`, questions batched into one call. The approval round uses `multiSelect` over the move ids when there are four or fewer, and otherwise offers the recommended set, "all", "choose by ID" (the user types the ids), and "none" |
| Blind designer | `Agent` with `subagent_type: architect`, one spawn. Never a bare `model`, which runs at the session's effort |
| Card writers | `Agent` with `subagent_type: scout`, all slices in one message so they run in parallel. `scout` has no write tool: save each reply to `$RUN/cards/` yourself. A reply over the display limit arrives as a persisted-output path; copy that file instead of retyping it. Re-request an empty reply |
| Loading a part | `Skill`, by name |
| The proposal as a page | Offer once, in one line, to publish `proposal.md` with `Artifact` when it has more than about ten moves; a long move table is easier to approve from a page than from the terminal |
| Tracking phases | The task list, one entry per phase, when the scope is the whole estate |

## The live listing

Claude Code caps the skill listing it gives the model: each entry at 1,536 characters
of `description` + `when_to_use`, and the whole listing at about 1% of the context
window. Names are always listed; when the budget overflows, descriptions are dropped
starting with the least-invoked skills. A skill listed by name only can still be typed
as a command and can no longer be selected by meaning. Budget and overrides:
`skillListingBudgetFraction`, `skillListingMaxDescChars` and `skillOverrides` in
settings; `/doctor` and the Skills row of `/context` report the cost.

For Phase 0 step 5, the listing to compare against is the one in this session's own
context. Entries from plugins and from the working directory's repository appear there
too; ignore names the collector did not inventory.

## How blind the designer really is

Not fully. Sub-agents load user-level skills by name (the collector's `sidechain`
counts are those loads), so a spawned designer has the skill listing, and it can read
the configuration root. Whether it also receives the user-level memory files has not
been established; assume it does. The brief closes the file channel by naming the
off-limits paths and asking for a tool-free answer. It cannot close the listing. Two
things limit the damage: the needs document carries no asset names, and Phase 2 checks
the returned design for names and boundaries lifted from the listing. Report the run
as blind only with that caveat in the proposal.

Fill `{OFF_LIMITS_PATHS}` with the configuration root, `~/.claude/projects`, and the
run directory.

## Parts and their own side effects

| Part | Its normal behavior | How this skill calls it |
|---|---|---|
| `auditing-prompt-docs` | Writes its own findings file and stops for approval | Run only its linter (`lint_prompt_doc.py <files> --json`) and read its rules and per-model references. Findings go into `reword` moves |
| `creating-agent-skills` (Improving) | Fans out up to five lenses and stops for approval | Run only `audit_skill.py <skill> --json` for an asset slated to be kept and restructured. Run the lenses only if the user asks for a deep review of one skill |
| `creating-agent-skills` (Building) | Scaffolds and validates a skill | Used as written, in Phase 6, for `rebuild`, `new`, `split`, `merge` |
| `auditing-repositories` | Files GitHub issues on invocation | Invoke with `dry-run` and the `tooling` lens only, from inside the repository; read its drafts. Nothing is filed |

## Follow-ups after applying moves

| A move changed… | Then |
|---|---|
| A skill published to the plugin marketplace | `distributing-plugins` |
| A tier definition, or the tier set | `orchestrating-models` §2 lists every file that must agree; `syncing-agent-tiers` carries the change to repositories |
| The user-level memory files | Nothing to sync; they take effect in the next session |
