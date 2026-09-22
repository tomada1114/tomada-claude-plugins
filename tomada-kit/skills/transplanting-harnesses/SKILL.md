---
name: transplanting-harnesses
description: >-
  Translate a reference repository's development harness — policy docs (AGENTS.md /
  CLAUDE.md), agent skills, task runner, git hooks, tests and coverage floors,
  architecture enforcement, CI and supply-chain gates, OSS hygiene, release — into the
  repository being worked in, which is usually a different language and framework, and
  file the work as a sequenced set of GitHub issues: one tracking parent, sub-issues,
  `priority: P0`-`P3` labels, dependency edges, plus one seed pull request carrying the
  reference material into the repo so every issue body can cite an in-repo path. Use
  when asked to bring this repository up to the standard of another one, to port a
  harness, an AGENTS.md setup, CI, hooks or coverage gates from a reference repo, to
  make a repository developable as production-grade public OSS, or when handed a
  reference repo path or URL and asked what this repository is missing.
argument-hint: "<reference repo: absolute path or public GitHub URL>"
metadata:
  platforms: claude-code, codex
---

# Transplanting a development harness

Left to itself a model reads the reference repo, copies its tool names into a stack that
has no such tools, and files a flat list of issues too vague to hand anyone. What is
worth moving is not the tools but the invariants underneath them: one command shared by
hook, CI and human; an install that verifies itself; a gap left open on purpose and
named in writing; a boundary enforced twice. This skill surveys both repositories,
judges strength rather than presence, and orders the issues so each is implementable by
the time its turn comes.

## Contract

**Input:** `$ARGUMENTS` — the reference repository, an absolute path or a public GitHub
URL. Ask for it when it is missing. Run from inside the target repository.

**Output:** issues in the target repo (one tracking parent plus sub-issues) and one seed
pull request. Working files live in the run directory
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/transplanting-harnesses/<owner>-<repo>/`
(`<owner>-<repo>` from the *target*, so a re-run lands on top of it): the two
inventories, `plan.json`, `bodies/*.md`, `created.json`, and — for a URL argument — a
shallow clone of the reference under `reference/`.

Beyond the seed PR this skill writes nothing into the target repository. Every harness
change, AGENTS.md included, becomes an issue; AGENTS.md is the first P0.

## 1. Preflight

Confirm the working directory is a git repository with a GitHub remote, and that
`gh auth status` succeeds. Resolve the reference: a path is read in place, a URL is
cloned with `git clone --depth 1` into `reference/` inside the run directory. Record the
reference's commit SHA and its license file, and the target's visibility
(`gh repo view --json visibility,defaultBranchRef`). Compare the local default
branch with its remote: the issues describe the remote's state, so unpushed commits
there (a renamed policy doc, say) are raised with the user before anything is planned.

Read the target's own AGENTS.md / CLAUDE.md / CONTRIBUTING for two things the issues
must obey: the language they are written in (an English-only repo gets English issues,
whatever language this conversation is in) and the commit and PR title convention.

## 2. Survey both repositories

Inventory each repo against [references/rubric.md](references/rubric.md), every item,
with `file:line` evidence.

Delegate this to two surveyor sub-agents in parallel — one per repo, disjoint reads,
as `executor` each (tier choice: the `orchestrating-models` skill), prompt from
[references/agents/repo-surveyor.md](references/agents/repo-surveyor.md) with its
placeholders filled in as absolute paths. They write `inventory-reference.md` and
`inventory-target.md` and return a summary only. Where the environment has no
sub-agents, or the combined harness surface is under roughly 15 files (policy docs,
task-runner and gate configs, workflows, hook definitions), run both passes inline and
sequentially instead: the split exists to keep two large file sweeps out of this
context, and below that bar it costs more than it saves.

Then open the load-bearing files directly — both repos' policy docs in full, and every
gate config a proposal hinges on. Judging from a summary alone is how this skill ends up
asking for a gate the target already has.

## 3. Build the gap table

One row per rubric item: **status** (equal-or-better / weaker / missing / n-a) ×
**transplant class** (agnostic / adapt / specific, defined in
[references/transplant-classes.md](references/transplant-classes.md)) → **verdict**
(adopt / translate / skip).

Rows where the target is equal or better get one line saying so, not a proposal. On a
mature target most rows come back "exists but weaker", where presence is the wrong
comparison — compare strength instead, with the rubric's questions: enforced
mechanically or only written down, install verified afterwards, same command in the
hook, in CI and at a human's terminal.

## 4. Propose

Clear wins are adopted by default: list them in one line each so the user can veto,
rather than asking about each.

Genuinely ambiguous calls go into one batched round of option prompts — bundle them all
into a single round, recommendation first, tradeoffs stated.

Where the reference's invariant has no equivalent in the target stack, state the
invariant rather than the tool, propose the cheapest mechanical enforcement the target
stack does offer, and ask per case which of three routes to take: a spike issue
(`design: open`, which earns the `blocked: design` label so a downstream shipping
workflow holds it), a named deliberate gap recorded in the policy doc with its reason,
or skip.

## 5. Plan

Write `plan.json` and one body file per issue, following
[references/issue-template.md](references/issue-template.md) for the bodies,
[references/sequencing.md](references/sequencing.md) for priorities and dependency
edges, and the schema in
[references/github-mechanics.md](references/github-mechanics.md) for the plan. With more
than 8 issues, delegate the body writing to one `executor` sub-agent using
[references/agents/issue-writer.md](references/agents/issue-writer.md); the spec is
settled by then, so the work is transcription. Three sub-agent spawns per run is the
cap.

Validate and preview:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/create_issues.py <run-dir>/plan.json
```

Show the user the sequenced list it prints — key, title, priority, depends-on.

## 6. Create

Only after the user explicitly approves that list.

**(a) The seed PR.** One branch, one PR, copying the reference material the issue bodies
cite verbatim into `docs/harness-reference/`, plus a README there recording the source
repository, the commit SHA, the license, and that this is a reference snapshot rather
than live code, removed again by the final issue. Make the target's own gates pass on it
— typo, lint, format and coverage checkers usually need the directory excluded. Store a
dependency manifest or lockfile under a changed name (`package.json.txt`) and say so in
the README and the bodies: GitHub's dependency graph ingests manifests anywhere in the
tree, and the snapshot's dependencies would show up as this repository's. Copying
requires the reference's license to permit it: stop and ask when the license is missing
or unclear. Pushing a branch and opening a PR is an external write: confirm it first.

**(b) The issues.** Once the seed PR is merged, re-run the script with `--apply`. The
bodies cite paths that must exist on the default branch, and a pull request is not
something a dependency edge can point at, so merge order is the only guard.

**(c) Report** the tracking issue URL and offer to continue with the `shipping-issues`
skill in `all` mode.

## Resources

- [references/rubric.md](references/rubric.md) — the nine harness areas, what to look for
  in each, how to judge strength, typical class. Step 2.
- [references/transplant-classes.md](references/transplant-classes.md) — agnostic /
  adapt / specific, the placeholder-first procedure, no-equivalent handling, example
  stack translations. Step 3.
- [references/sequencing.md](references/sequencing.md) — priority ladder, dependency
  chains, issue sizing, the tracking issue. Step 5.
- [references/issue-template.md](references/issue-template.md) — issue body skeleton and
  a filled example. Step 5.
- [references/github-mechanics.md](references/github-mechanics.md) — the `plan.json`
  schema and what the script does with the GitHub API. Step 5.
- [references/agents/repo-surveyor.md](references/agents/repo-surveyor.md) and
  [references/agents/issue-writer.md](references/agents/issue-writer.md) — sub-agent
  prompt templates.
- [references/platform-notes.md](references/platform-notes.md) — host mapping for option
  prompts, sub-agents and skill handoff.
- `scripts/create_issues.py` — run it, do not read it. Python 3 standard library plus the
  `gh` CLI.

## Critical rules

- **No issue body cites a path outside the target repository.** An absolute path to the
  reference repo is meaningless to whoever implements the issue. Reference material is
  cited as `docs/harness-reference/...`, which is what the seed PR exists to create.
- **`--apply` runs once per plan, after approval.** The script is idempotent through a
  body marker, so a re-run after a partial failure resumes; approval is per plan.
- **The seed PR is the only write to the target's working tree.** Editing AGENTS.md, a
  workflow or a hook config directly deletes exactly the work the issues exist to carry,
  and leaves an unreviewed change on someone's branch.
