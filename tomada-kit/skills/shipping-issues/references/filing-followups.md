# Filing follow-ups

What to file as its own issue when a run turns up a defect that is not the issue
being shipped, what to fix inline instead, and what not to file at all. Read it
at the filing step, before writing any issue body.

## Table of Contents

- [File, or fix inline](#file-or-fix-inline)
- [What is not an issue](#what-is-not-an-issue)
- [Verify before filing](#verify-before-filing)
- [What the body needs](#what-the-body-needs)
- [Design not settled](#design-not-settled)

Shipping an issue surfaces defects that are not that issue: a sibling of the bug
just fixed, a latent gap the diff walked past, a scope the implementing run
deliberately declined. Each one is a finding the run paid for. Fixing it inline
silently widens a PR that is about to auto-merge; saying it only in the final
report loses it the moment the conversation ends. File it.

## File, or fix inline

**File — do not fix inline — when any of these hold:**

- it needs its own tests, schema change, or design decision;
- it changes behavior outside the shipped issue's stated scope;
- an implementation, review, or CI-repair run already returned it under
  `SCOPE-NOTES`, `OUT-OF-SCOPE`, or `FOLLOW-UPS` as something it declined on
  purpose;
- the fix would push a green PR back through CI for a reason unrelated to its
  own issue.

**Do not file** what a one-line edit inside the current diff covers and the
issue's own tests already exercise, nor a restatement of the issue being
shipped, nor a speculative "we could someday" with no observed defect behind it.
An issue nobody will act on costs the next run's ranking pass real attention.

## What is not an issue

An operational action is not an issue: something resolved by running an existing
command or skill, or by changing a machine or account setting, changes nothing
in the repository, so no PR can ever close it. Report it as an operator action
instead.

The same test applies to the backlog itself — an existing open issue that turns
out to be purely operational is not shippable; close it with a comment naming
the action that resolves it, and record the closure in the report.

## Verify before filing

A run's out-of-scope observation is a lead, not a fact — it saw the code while
working on something else. Read the lines it names and confirm the defect is
real, and confirm what actually prevents it today. That check routinely changes
the tier: a gap that sounds severe but is already blocked at an adapter boundary
is a missing defense layer (P3), not a live bug (P1). File what you verified,
including the mitigation, never the run's summary taken on faith. If it does not
survive the check, say so in the report and file nothing.

## What the body needs

Give the body what the next session needs and cannot cheaply re-derive:

- the observed defect with `file:line`;
- why it matters in this codebase's terms;
- **what currently prevents it, and why that is not enough**;
- the invariants a fix must not break — quote the canonical doc;
- a completion checklist.

Name the open design questions and leave them open rather than deciding them
here.

## Design not settled

Pass `file_followup.py --needs-design` when the body's open questions are
something nobody can implement without answering first — a real choice
between approaches, an undecided scope boundary, a product/UX call — so the
finding stays out of automatic selection until a run deliberately takes it on
and decides (see `dependency-triage.md`'s "Deciding a held design"). Do not
add it for a verified defect with an obvious fix merely because it is
large or touches many files — size is not the test, an undecided approach is.
