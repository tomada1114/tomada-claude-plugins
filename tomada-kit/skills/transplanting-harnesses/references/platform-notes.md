<!-- platform-annex -->
# Platform notes

The body of this skill names capabilities, not tools. This file is the one place that
maps them to what each host offers.

## Concept → host mapping

| Neutral phrasing in the body | Claude Code | Codex CLI |
|---|---|---|
| "batched round of option prompts, recommendation first" (step 4) | `AskUserQuestion` — bundle every open decision into a single call, up to four questions, each with its options and the recommended one first | ask the questions in plain text, numbered, in one message, and wait for the reply |
| "two surveyor sub-agents in parallel" (step 2) | two `Agent` tool calls in one message, `subagent_type: executor` each | run both surveys inline in the main context, one after the other, writing the same two inventory files |
| "delegate the body writing to one `executor` sub-agent" (step 5) | one `Agent` tool call, `subagent_type: executor` | write the bodies inline |
| "continue with the `shipping-issues` skill in `all` mode" (step 6c) | the `Skill` tool, or suggest `/shipping-issues all` | that skill is Claude-side; on Codex use the issue-implementation workflow in `managing-git-github-workflows`, one issue at a time, in the order the plan printed |
| "confirm before pushing a branch and opening a pull request" (step 6a) | ask and wait; the permission prompt on the `git push` is not a substitute, since the user needs the PR's content described first | same, and note that Codex's sandbox may block the network write until approval regardless |
| `${CLAUDE_SKILL_DIR}` in a command | expanded to this skill's directory before the model sees it | substitute the skill's own directory path |

## What is lost on Codex

- **Parallelism.** The two surveys are the only parallel step; running them sequentially
  changes wall-clock time, not the result. Phase order is unaffected.
- **Per-spawn model choice.** Everything runs at the main context's model and effort.
  The surveys are the cheapest part of the run, so the cost lands mostly on context
  rather than money — which is why keeping both inventories on disk matters more here:
  read each one back when the gap table needs it instead of holding both in context.
- **The context isolation of the two surveys.** Inline surveying puts every file read
  into the main context. On a large pair of repositories, write each inventory as you go
  and work from the file afterwards.
