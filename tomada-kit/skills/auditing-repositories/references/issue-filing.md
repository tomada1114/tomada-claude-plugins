# Filing findings as issues

Invoking this skill authorizes creating issues, labels and native issue links in the
audited repository. When a finding is inherited, it also authorizes them in the
template repository the audited one was cut from. It does not authorize code changes,
comments on existing issues, or closing anything. In dry-run mode, stop after writing
the drafts.

## Contents

- [1. Learn the repository's conventions](#1-learn-the-repositorys-conventions)
- [2. Decide what gets an issue](#2-decide-what-gets-an-issue)
- [3. Trace inherited findings to the template](#3-trace-inherited-findings-to-the-template)
- [4. Draft](#4-draft)
- [5. Create and verify](#5-create-and-verify)

## 1. Learn the repository's conventions

Conventions are looked up in this order. Where an earlier source speaks, it wins.

1. **A `triaging-issues` skill**, in `.claude/skills/` or `.agents/skills/` (read
   whichever exists). It defines labels, priority meaning, what a body must contain, and
   how a dependency is spelled. Follow it exactly.
2. **A `shipping-issues` skill**, the consumer. Read its ship-contract reference and
   write every field it parses, so the backlog ranks and parallelizes without a
   research pass.
3. **`.github/ISSUE_TEMPLATE/`** forms. Pick the form matching the finding's type and
   render each form field as the `### <label>` heading GitHub produces. Apply the
   form's default labels. **`.github/labels.yml`** gives the label set.
4. **Past issues.** Read the latest ~30 issues, open and closed. They show title style
   (prefixes, tense, language), body headings, and how labels are actually used.

When none of these exist, the format is free. A body that serves an implementing agent
usually carries the problem with `path:line`, why it matters, the proposed design, the
safe test-first path, and a checkable close condition. The analyst's finding block
already holds all of these.

## 2. Decide what gets an issue

| Finding | Outcome |
|---|---|
| `change`, confidence high or medium, with evidence and a concrete proposal | Issue |
| Every other low-severity `change` finding in one lens | One grouped issue per lens: a checklist with each item's `path:line` and close condition. Split it by area only when it would not fit one pull request |
| `change` with low confidence, or a matter of taste with no cost named | Report only |
| `owner-decision` with real alternatives | Issue, marked as awaiting a design decision the way the repository spells it (`blocked: design` where that label exists), with the options in the body |
| Contradicts a Product non-goal or a documented decision | Report only. Moving scope is the owner's call |
| `security: exploitable` | **Never a public issue, PR or comment.** Follow `SECURITY.md`'s private route if there is one; otherwise report it to the user only |
| `keep` | Report only, under "Examined and kept" |

There is no cap on the count. Size each issue to one reviewable pull request. A
redesign that needs several pull requests becomes a tracking parent with sub-issues.
Use the breakdown rules of the `planning-tickets` skill: independence over
granularity, foundation first, explicit dependency edges. Its approval stop does not
apply here, because invoking this skill already authorized filing.

**Duplicates.** Before drafting, search the target repository's issues: open issues,
issues closed as not planned, and the ledger from earlier runs (`filed.json`). Search
by the evidence paths and the key terms of the title.

- An open issue that covers the finding: no new issue. Report it as "already tracked
  as #N".
- An issue closed as not planned: the owner already decided. Report it; do not refile.
- An issue closed as completed whose problem is back: file a new issue that links the
  old one.

**Priority.** An audit is triage, so tier every issue with the repository's rubric
when it has one, and write the same tier into a ship contract when the repository uses
one. Without a rubric, state severity in the body and apply no priority label.

## 3. Trace inherited findings to the template

Applies when the inventory's `template_origin` names a template.

1. Get a read-only copy of the template's default branch. Prefer an existing local
   clone of that repository; run `git fetch` there and read `origin/<default>` without
   touching its working tree. Otherwise shallow-clone it into
   `${TMPDIR:-/tmp}/agent-skills/auditing-repositories/templates/<name>`.
2. For each `change` or `owner-decision` finding, look at the template's file at the
   matching path, or the same symbol when files were renamed by the bootstrap. Classify
   it as one of:
   - `inherited` — the same problem is present in the template today
   - `fixed-upstream` — the template has since fixed it; the audited repo can port the fix
   - `local` — the problem originated in the audited repo
   With many findings, a read-only research sub-agent can do the comparison when given
   both roots and the finding list.
3. `inherited` findings get an issue in **both** repositories. The template issue
   follows the template's own conventions (step 1, read from its copy), cites template
   paths, and avoids product details of the derived app. Each issue links the other.
4. `fixed-upstream` findings get an issue only in the audited repo, citing the
   template commit or path to port.

## 4. Draft

Write each body to `<run>/issues/NNN-<slug>.md`, numbered in creation order: tracking
parents, then foundations, then the rest. Write cross-references with provisional IDs
(`#P003`). Template-side drafts go to `<run>/issues-template/`. Drafting is
mechanical once conventions and findings are fixed. When there are more than about six
bodies, a single-shot writing sub-agent can produce them, given the conventions
excerpt and the finding blocks verbatim.

## 5. Create and verify

Create in draft order through the host's GitHub access, the audited repository first
and then the template. Then backfill real numbers into the bodies, including the
cross-repository "also filed" links, and add native sub-issue and blocked-by links. The creation mechanics (the
two-pass method, which labels must exist first, the native-link endpoints) are in the
`planning-tickets` skill's `reference.md`. Labels the repository defines but GitHub
lacks are created through the repository's own sync recipe when it has one; GitHub
drops an unknown label silently.

Before retrying a failed create, search for the title so the retry does not
duplicate. Record every created issue in the ledger as soon as it exists:
`filed.json` maps each finding ID and its evidence paths to the issue URL.

Postconditions, checked from the tracker itself:

- Every drafted issue exists, with its intended labels.
- Native links match the `Depends on` and parent lines.
- `git status --porcelain` in the audited repository matches the start of the run,
  or the difference is traced to another process.
