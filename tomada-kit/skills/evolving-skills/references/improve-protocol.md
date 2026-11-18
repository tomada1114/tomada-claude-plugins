# The improve protocol

One promotable group becomes at most one change. This file covers the judgment the
gate cannot make: what is wrong, where the fix belongs, and how to write it so it
holds beyond the incidents that prompted it.

## Table of Contents

- [Diagnose](#diagnose)
- [Where the fix belongs](#where-the-fix-belongs)
- [Prune before adding](#prune-before-adding)
- [Writing the change](#writing-the-change)
- [Changes that may land unmeasured](#changes-that-may-land-unmeasured)
- [Commit message](#commit-message)
- [After landing](#after-landing)

## Diagnose

Read the skill's SKILL.md and the references the signals touch, then put the group in
one category. Search the skill for an existing rule first: "no rule" is the least
common true cause.

| Category | Sign | Change |
|---|---|---|
| Missing rule | Nothing in the skill covers the behavior | Add the rule, with its reason |
| Wrong rule | The skill was followed and the result was what the user rejected | Rewrite or delete the rule |
| Rule not followed | The rule exists and was skipped | Do not repeat it louder. Move it earlier, give it a reason, or make it mechanical |
| Belongs in a script | The rule is a deterministic check or transformation | Move it to `scripts/` with a test, and delete the prose |
| Instruction overweight | `unused-instruction` signals: a step skipped with no loss | Delete the step |
| Not the skill | The signals describe the user's taste on one piece of work, or a problem in another asset | Mark `rejected` with a note; change nothing |

When the signals in a group point at different categories, the key was too broad:
mark the group `deferred` with a note and let new, better-keyed signals arrive.

## Where the fix belongs

| The rule is | Put it in |
|---|---|
| Decidable by a program (format, presence, order of tool calls, forbidden strings) | `scripts/`, or the skill's lint config. Never prose |
| A hard stop before an action that cannot be undone | A `PreToolUse` hook in the skill's frontmatter, if the skill is Claude Code only |
| A judgment the model makes while working | SKILL.md body, at the step where it applies |
| Detail needed only on one path | The reference that path already reads |
| A criterion for "is this output acceptable" | The skill's self-check criteria |
| True for every session, whatever the skill | Not here. Record it as `blocked`: memory files are the user's |

## Prune before adding

Open the file the fix will go into and look for, in this order: a rule the fix
contradicts (rewrite that one instead of adding a second), a rule the fix duplicates
(strengthen its reason or placement instead), a rule that restates what the model does
unprompted (delete it and count the lines as budget). The gate enforces the size
budget: a SKILL.md body over 150 lines and a reference over 400 may not grow, so a
change to a full file has to remove at least as much as it adds.

## Writing the change

- State the rule and its reason in the terms of the skill's task, never in the terms
  of the incident. The gate rejects a change that shares wording with an eval prompt,
  because a rule phrased as its own test case passes that case and nothing else.
- Write current behavior only. No dates, no "previously", no "after the incident".
  The commit message is where history goes.
- One change per group. A second idea noticed along the way becomes a `review` signal.
- Follow the authoring rules the skill was written under (the `creating-agent-skills`
  skill, `references/prompt-authoring.md`): plain imperatives with reasons, no added
  emphasis, no extra verification passes.

## Changes that may land unmeasured

`gate.py land --allow-unmeasured` is for a change whose effect no isolated eval run can
observe. That covers exactly:

- a fix to a path, command or link that was simply wrong;
- deleting an instruction on `unused-instruction` evidence;
- a change to a step that needs something an eval run does not have (sub-agent
  definitions, other skills, the user's settings, a connector, a browser).

For the third kind, first try to write a case for the part of the step that is
observable in a single context. Mark the commit subject with `[unmeasured]`.

## Commit message

```
<skill>: <what changed, imperative, under 72 chars> [unmeasured]

Why: <the diagnosis category and the problem, one or two sentences>
Signals: SIG-xxxxxxxx SIG-yyyyyyyy (sessions: 2, explicit: no)
Gate: pass; eval <base> -> <head> over <n> cases; new case <name> <base> -> <head>
Run: <run directory>
```

The signal ids are what make a later revert decidable: they say which evidence the
change rested on.

## After landing

`signals.py set --id ... --status applied --commit <sha>`. If the same key produces
new signals after a change landed for it, the change did not work: revert it before
trying another, so that two half-fixes do not pile up.
