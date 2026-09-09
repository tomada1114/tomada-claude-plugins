# Design decision (sub-agent prompt)

Spawned at [SKILL.md step 8b](../../SKILL.md#8b-unblock-held-designs-in-the-background),
one **`opus`** sub-agent per design-blocked issue, **in the background** — this
session spawns a round in one message and goes straight back to shipping.

This is the only sub-agent in this skill that writes to GitHub, and only two
writes: one comment on the issue and one label clear. It writes nothing in the
checkout, so `{workdir}` is the repo's main checkout even while a parallel batch
is running — it reads there, it never touches the tree.

```
Decide the design for GitHub issue #{n} in {owner}/{repo}, completely enough
that a later run can implement it without deciding anything. You are not
implementing it: write no code, create no branch, open no PR, modify no file
in the repository, and run no `rm`.

Read, in this order:
  - the issue and its thread:
    gh issue view {n} --repo {owner}/{repo} --comments
  - the project's own conventions: {workdir}/CLAUDE.md, {workdir}/AGENTS.md
  - the code the issue names, and the nearest thing this repo already does that
    solves a similar problem — your design has to look like it, not like a
    greenfield design

{workdir} may be on an unrelated feature branch mid-implementation — a
parallel batch can be running against it while you read. Read default-branch
state, not the working tree, for anything you cite:
  git -C {workdir} show origin/{default_branch}:<path>

<issue>
{the issue body, pasted}
</issue>

<context>
Paths the issue's ship contract declares: {touches, or "none declared"}
Related prior art in this repo: {paths, when known}
</context>

Decide, concretely enough that an implementer never guesses:
- the approach, and the alternatives you rejected with the reason each lost;
- the files and functions that change, and the new ones that appear;
- the data, schema, config and API surface it touches: exact names, shapes,
  defaults, and the migration or compatibility path;
- behavior at the edges — errors, empty, concurrent, already-migrated,
  backward compatibility with what is deployed;
- what the tests must pin, case by case;
- what is explicitly out of scope for this issue.

Two things you must not do:
- Do not decide a product or UX call the repo and the issue thread do not
  already answer: what a user is promised, a policy, a price, wording a user
  sees, a trade between two user-visible behaviors. Return DEFERRED with the
  exact question instead — one question, answerable in a sentence.
- Do not widen the issue. If your design only works by also changing something
  the issue does not mention, say so under RISKS rather than folding it in.

On DECIDED, write it back to GitHub yourself, in this order:
  1. post the design as a comment — it is the design of record and must stand
     alone, without this conversation, starting with `## Design decision`:
     gh issue comment {n} --repo {owner}/{repo} --body-file <file>
  2. only after that comment posted, clear the block:
     python3 ${CLAUDE_SKILL_DIR}/scripts/apply_priority_labels.py --clear-design {n}
On DEFERRED do neither — the issue must stay blocked.

Return exactly:
VERDICT: DECIDED | DEFERRED
APPROACH: <the decision itself, 2-4 lines>
SCOPE: <the files and surfaces that change, one line>
OPEN-QUESTION: <on DEFERRED, the one question a human must answer; else "none">
RISKS: <what this design assumes or could get wrong, or "none">
COMMENT: <url of the comment you posted, or "none">
LABEL: cleared | left-on
```

`VERDICT: DEFERRED` is a result, not a failure — it is the run declining to
invent a product decision, and its `OPEN-QUESTION` is what the step 10 report
puts in front of the user. `LABEL: left-on` with `VERDICT: DECIDED` means only
the label write failed: clear it from this session before treating the issue as
ready. `APPROACH` is the only part worth reading closely in this context — the
full design lives on the issue, where the implementer will read it.
