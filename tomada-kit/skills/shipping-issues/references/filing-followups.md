# Filing follow-ups

What a run does with a defect it turns up that is not the issue being shipped:
fix it in the diff already open, file it and ship it in the same run, file it
and leave it, or not file it at all. Read it at the filing step, before writing
any issue body.

## Table of Contents

- [Fix inline, file and ship, or file and leave](#fix-inline-file-and-ship-or-file-and-leave)
- [What is not an issue](#what-is-not-an-issue)
- [Verify before filing](#verify-before-filing)
- [What the body needs](#what-the-body-needs)
- [Design not settled](#design-not-settled)

Shipping an issue surfaces defects that are not that issue: a sibling of the bug
just fixed, a latent gap the diff walked past, a scope the implementing run
deliberately declined. Each one is a finding the run paid for, and the run is
the cheapest place it will ever be fixed — the context is loaded, the tests are
running, a reviewer already read the code. Saying it only in the final report
loses it the moment the conversation ends. The question is never *whether* to
deal with it, only *where*.

## Fix inline, file and ship, or file and leave

Prefer, in this order, the outcome that leaves the least behind.

**Fix it inline — in the diff already open — when all of these hold:**

- it is the same behavior change the issue is about: a sibling case of the bug
  just fixed, another branch of the function being changed, the same missing
  guard one call site over;
- the issue's own tests already exercise the path, or one test added beside
  them covers it;
- it needs no schema change, no new public surface, and no decision;
- the branch has not merged yet.

Pushing a green PR back through CI for this is fine when the change is
genuinely part of that PR's own story. What is not fine is a PR that quietly
becomes about something else — that is the line, and it is about coherence, not
about patch size.

**File it, and ship it in this same run**
([SKILL.md step 8c](../SKILL.md#8c-take-the-runs-own-output-back-into-the-queue))
when it is a real, separate change — its own branch, its own PR — but nothing
about it is undecided: the defect is verified, the fix is obvious, its scope is
one coherent thing. This is the normal outcome for what an implementation run
returned under `SCOPE-NOTES` as out of scope: out of that *diff*, not out of
this run. It costs a full steps 3-8 cycle, which is exactly what it is worth.

**File it and leave it** when the run genuinely cannot finish it: it needs a
product or UX decision, it depends on something still open, it is large enough
to be its own batch of work, or the run is out of budget. Say which in the
report, so "left for later" never reads as "forgotten".

**Do not file** a restatement of the issue being shipped, nor a speculative
"we could someday" with no observed defect behind it. An issue nobody will act
on costs the next run's ranking pass real attention. Note what an inline fix
already covered — do not also file that.

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
something nobody can implement without answering first — a real choice between
approaches, an undecided scope boundary, a product/UX call — so the finding
stays out of automatic *implementation* until the approach is decided (see
`dependency-triage.md`'s "Deciding a held design"). Do not add it for a
verified defect with an obvious fix merely because it is large or touches many
files — size is not the test, an undecided approach is.

Treat the label as temporary, and write the body accordingly. Every issue filed
this way gets a background `opus` sub-agent sent after it at
[SKILL.md step 8b](../SKILL.md#8b-unblock-held-designs-in-the-background), which
decides the approach from the repo and the issue thread, records it as a
comment, and clears the block — often within this same run. So name the open
questions precisely, and separate the two kinds: the ones answerable from this
codebase, which that agent will answer, and the ones only a human can settle,
which it hands back as `DEFERRED`. A vague "design TBD" wastes that agent's
run; a sharp question gets the issue unblocked before you next look at it.
