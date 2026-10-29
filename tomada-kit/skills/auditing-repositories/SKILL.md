---
name: auditing-repositories
description: >-
  Audit the repository you are in, often a template or an app cut from one, for
  technical debt and room to improve in four areas: architecture and design
  patterns; tests; file structure and code quality; and tooling, CI, dependencies and
  the agent harness. Design a safe, test-first fix for every evidenced finding, and
  file the findings as GitHub issues that follow the repository's own issue
  conventions (triaging-issues, issue forms, past issues). A finding inherited from the
  template is also filed in the template repository. Cheap read-only sub-agents collect
  the evidence and high-effort analysts judge it. Changes no code; shipping-issues and
  tdd do that afterwards. Use when asked to audit a repository, find technical debt,
  review a codebase's architecture or test quality, decide what to refactor, or
  health-check a template repository.
metadata:
  platforms: claude-code, codex
---

# Auditing repositories

Without this skill, a review of a whole repository reads a few files, lists generic
smells, and either files nothing or files noise. This skill does three things instead.
It measures the repository against the design the repository itself declares. It
spends cheap context on collecting evidence and expensive judgment on the root cause
and the target design. And it turns each evidenced finding into an issue that an
implementing agent can ship test-first without asking back. "The current design is
right" is a valid outcome; the report records what was examined and kept.

## Contract

**Input:** free-form, run from inside the target repository. Optional narrowing:

- lens names: `architecture`, `tests`, `code-quality`, `tooling` (default: all four)
- paths, which limit the survey
- `full`, which forces a whole-repository audit when an incremental one would apply
- `dry-run` (also "report only", "don't file"), which stops after drafting

**Authorization:** invoking this skill authorizes creating issues, labels and native
issue links in the audited repository, and in its template repository for inherited
findings. It authorizes nothing else. In particular, it makes no code changes, no
commits, and no comments on or closing of existing issues.

**Output:** `$RUN = ${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/auditing-repositories/<owner>-<repo>/runs/<YYYY-MM-DD>/`,
holding `inventory.json`, `survey-<lens>.md`, `analysis-<lens>.md`, `issues/`, and
`report.md`. The ledger `filed.json` sits one level above `runs/`. A rerun on the same
day overwrites that day's run.

## Phase 0: Orient (main session)

1. Find the repository root and `<owner>/<repo>`. Record `git status --porcelain` and
   `HEAD`. Nothing in this run writes to the repository. If either has changed by the
   end, check whether another process (for example a parallel session merging a pull
   request) caused it before you report.
2. **Choose the mode.** Take the most recent run under `runs/` that has a `report.md`
   (read it now if it is today's, since this run overwrites it). Its `inventory.json`
   `head` is the base. Run a **full** audit in four cases: there is no such run, the
   user said `full`, the last full audit (each `report.md` records its mode) is more
   than 90 days old, or the base is unreachable. Otherwise run an **incremental**
   audit of what changed since the base.
3. Run the inventory and save it:
   `python3 ${CLAUDE_SKILL_DIR}/scripts/inventory_repo.py <repo-root> --json [--since <base>] > $RUN/inventory.json`
   (on hosts that do not expand that variable, use the directory holding this file).
   It reports scale, areas, the largest and most-churned files, untested candidates,
   markers, gates, harness files, issue conventions, and `template_origin`. With
   `--since` it adds `changes_since`: the changed files with their kind and area, or
   `reachable: false`, which means fall back to a full audit.
4. Read the repository's **declared intent** yourself, because every lens is judged
   against it: AGENTS.md and nested AGENTS.md (the Product section and its non-goals
   above all), the one-line "Owns / Does not own" of each repository skill, and the
   design each skill records (its body and `references/`), which is where the owner
   keeps how the app is built and why. Keep the excerpts; they go into every brief. A
   leftover architecture document or roadmap is itself a finding (stale design kept
   outside the skills), not declared intent.
5. Read the previous run's `report.md` and `filed.json` if they exist, so known and
   already-filed findings are not rediscovered as new.

**Incremental mode.** Only lenses that the changes reach run:

- architecture and code-quality, for changed source files;
- tests, for changed source or test files;
- tooling, for changed config, CI, manifests, instruction files or skills.

Each brief's scope is the changed files. Each brief also gets the previous run's
report-only and owner-decision findings for its lens, so it can confirm that they
still hold, or that they no longer do. With no relevant change, write a short report
that says so and stop.

## Phase 1: Survey (cheap, read-only)

Scouts pay off only where the survey means enumerating a lot of code, so this phase
covers only the [architecture](references/lenses/architecture.md) and
[code-quality](references/lenses/code-quality.md) lenses. The
[tests](references/lenses/tests.md) and [tooling](references/lenses/tooling.md)
analysts collect their own survey items, because they have to read the same files
anyway.

Fill [references/agents/surveyor.md](references/agents/surveyor.md) with the lens file
and one slice of the inventory's areas. Size each slice at roughly 10k source lines or
less, which keeps a scout's context out of the model's high-price tier. Hand each brief
to a `scout` sub-agent, in parallel where the host supports it; otherwise run the
briefs one after another inline. Cap: 6 scouts. Save the replies for a lens, slice
after slice, as `$RUN/survey-<lens>.md`.

The whole phase is skipped for a small repository (inventory `scale: small`). It is
also skipped for an incremental run touching fewer than about 40 source files. In
both cases the analysts survey as they read.

## Phase 2: Analyze (deep, one analyst per lens)

Fill [references/agents/analyst.md](references/agents/analyst.md) per lens. Include
absolute paths to the lens file, the survey (or "none" when Phase 1 did not cover the
lens), and the intent files, plus the scope and any previous findings. Add the gate
commands the repository documents for tests, coverage and lint as allowed checks. Hand
each to an `architect` sub-agent in parallel, or inline in sequence. Cap: 4 analysts.
For a small repository, give one `architect` all selected lenses in a single brief.
Sub-agents return text and write no files. Save each analyst's reply verbatim as
`$RUN/analysis-<lens>.md`; when the host has already stored a long reply in a file,
copy that file rather than retyping it. Tier criteria live in the
`orchestrating-models` skill.

## Phase 3: Synthesize (main session)

1. Merge the analyses. Collapse findings that share a root cause across lenses into
   one, keeping every piece of evidence; the `Cross-lens` sections point at them.
   Check each surviving claim against its cited `path:line`.
2. If a merged root cause needs a redesign spanning lenses, hand that cluster and its
   findings to one more `architect` for a single combined design. Cap: 1.
3. Apply the filing table in [references/issue-filing.md](references/issue-filing.md)
   §2: what becomes an issue, what is grouped, what stays in the report, and how
   security findings are handled. Then run §3 there to classify each finding as
   inherited, fixed upstream, or local.

## Phase 4: File

Follow [references/issue-filing.md](references/issue-filing.md) §1, §4 and §5. Learn
the target repository's conventions, deduplicate, draft into `$RUN/issues/`, then
create, link and verify. In `dry-run`, stop after the drafts.

## Phase 5: Report

Write `$RUN/report.md`, as long as its substance requires, with these sections:

- **Summary:** the mode (`full`, or `incremental` since `<base>`) and the overall
  verdict in a few sentences.
- **Filed:** issue links grouped by lens, template-side issues included.
- **Already tracked:** findings an existing issue covers.
- **Report-only findings:** each with the reason it was not filed.
- **Owner decisions:** the options for each.
- **Examined and kept:** what was looked at and found sound.
- **Security:** say whether a private report is needed.

Give the user the summary, the filed links, the owner decisions, and the report path.

## Resources

- [references/lenses/](references/lenses/): one checklist per lens, with survey
  items `S-XX` (collected by scouts or by the analyst) and analysis items `XX`.
- [references/agents/surveyor.md](references/agents/surveyor.md) and
  [references/agents/analyst.md](references/agents/analyst.md): the sub-agent briefs.
- [references/issue-filing.md](references/issue-filing.md): conventions, the filing
  bar, duplicates, the template trace, drafting, creation and its postconditions.
- [references/platform-notes.md](references/platform-notes.md): the tool mapping for
  each host, and what changes on hosts without parallel sub-agents.
- `scripts/inventory_repo.py`: run it, do not read it. Standard library only; tests in
  `scripts/tests/`.
