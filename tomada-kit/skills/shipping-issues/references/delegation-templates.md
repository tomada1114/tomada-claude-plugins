# Delegation Prompt Templates

## Table of Contents

- [Priority research and labeling](#priority-research-and-labeling-sonnet)
- [Implementation](#implementation-step-3)
- [Review fix, parallel mode](#review-fix-parallel-mode)
- [Review fallback](#review-fallback)
- [CI repair](#ci-repair-step-6-only-on-fail)
- [Design decision](#design-decision-step-8b)

Every sub-agent this skill spawns is a fully self-contained prompt: it cannot
ask a question back, so a hole in it returns as a decision made alone rather
than as a question. Leave nothing merge-gating unguessed. The parent — this
session — owns every GitHub **write** (opening the PR, `link_check.sh`,
`ci_watch.sh`, `land_pr.sh`, labels, comments) and every merge-gating
judgment; a sub-agent only touches code inside the checkout.

**Reading its own issue is the one GitHub call a sub-agent makes.** Pasting a
full issue body into the prompt means the parent must first pull it into *this*
context — the exact cost `cost-discipline.md` exists to avoid, paid once per
issue and again on every resume run. So every template below that reads an
issue hands over its *number* and lets the agent run `gh issue view <n>
--repo <o/r> --json title,body,labels,comments` itself, under the standing
prohibitions below. The JSON form is not a style choice: without a TTY — which
is how every sub-agent runs `gh` — `gh issue view <n> --comments` prints the
comments and **not the body**, so an agent handed that command implements an
issue it never read (observed: the agent reported the body's checklist as
unreadable). Give it a
two-or-three-sentence paraphrase alongside, marked as subordinate to the body,
so a misread is visible rather than silent. What never moves to a sub-agent is
a write, or a merge-gating judgment.

`{workdir}` below is the one thing every template must get right: the repo's
main checkout in serial mode, that issue's worktree
(`<runstate>/worktrees/<n>`) in parallel mode. **Two sub-agents never share a
working directory** — that invariant is what makes parallel mode safe, and
filling `{workdir}` with the main checkout for two concurrent runs breaks it
silently rather than loudly. The read-only templates are the exception, and
only because they write nothing: the review fallback and the design agent read
a checkout others are working in without disturbing it. Everything downstream
of implementation still runs one PR at a time in the parent.

## Standing prohibitions for every spawn

Two things stay off-limits in every template below unless it says otherwise.
This is the full statement; each per-agent file restates it compactly in its
own prompt text, so the prompt stays self-contained when pasted on its own —
a spawned sub-agent cannot follow a cross-reference back to this file.

- **No GitHub write.** No `gh pr`, no `gh issue edit/comment/close`, no label
  change, no `gh api` call with a non-GET method. The parent opens the PR,
  watches CI, and writes every label and comment — a sub-agent only reads,
  and only its own issue.
- **No deletion.** No `rm`, no branch deletion, no worktree removal — including
  a scratch fixture or throwaway repository created under a temp directory:
  leave it exactly where it is and name it in the report. `rm` triggers an
  approval prompt that stalls the run, and a disposable temp directory costs
  nothing to keep. Revert a probe inside the checkout with `git checkout --`,
  or move it out of the way with `mv`.

The design agent is the one named exception to the first rule: it writes two
specific things to GitHub (a design comment, a label clear) as its whole
purpose, spelled out in its own template.

## Priority research and labeling (`sonnet`)

Spawned only when more than ~3 open issues still lack a `priority:` label, or
when the top rows of a labeled backlog are close enough that the pick needs
evidence. On a fully labeled backlog, the plan's `select:` line is the answer
and no spawn is warranted.

The worker writes the labels itself — that is the point of the handoff. What
comes back is the pick with its evidence, the order behind it, and the
blocked/unclear lists; the issue prose and the raw digest table never cross
back. In `all` mode it also returns proposed parallel-safe groups — a
proposal, not a decision: [step 2c](../SKILL.md#2c-confirm-the-proposed-batch)
still has to clear the repository's own viability gate before any of it runs.

Prompt body: [references/agents/priority-research.md](agents/priority-research.md).
Fill its `{brace}` placeholders from the current repo and run count, then
spawn a `sonnet` sub-agent with it.

## Implementation (step 3)

Spawn one sub-agent per issue. **`sonnet` is the default; `opus` when the
issue is foundational** — architecture or a skeleton, an interface/port/schema,
or a skill, instruction file, or gate whose shape the rest of the backlog
copies. The test is blast radius, not difficulty:
[cost-discipline.md#the-foundation-exception-opus-for-what-the-backlog-builds-on](cost-discipline.md#the-foundation-exception-opus-for-what-the-backlog-builds-on).
A resume/patch run stays on the model its first run used. In parallel mode
issue every prompt in the batch **in one message** — spawned one after another
they run one after another, which is the whole thing this mode exists to
avoid.

Prompt body: [references/agents/implementation.md](agents/implementation.md).

## Review fix, parallel mode

Only for findings this session has already read and accepted: in parallel mode
at step 4, and at step 6b when the accepted fixes are more than this session
should write itself. `/code-review --fix` writes to the session's own working
tree, which in parallel mode is the main checkout sitting on the default branch
— the wrong tree — so the review runs read-only and the writing is delegated
here instead. See [SKILL.md step 4](../SKILL.md#4-local-review--only-where-ci-does-not-review)
and [step 6b](../SKILL.md#6b-review-rounds). Zero accepted findings → no spawn.
Spawn one **`sonnet`** sub-agent per branch that has any.

Prompt body: [references/agents/review-fix.md](agents/review-fix.md).

## Review fallback

Only when this session's host will not let it launch `/code-review`
directly — see [SKILL.md step 4](../SKILL.md#4-local-review--only-where-ci-does-not-review).
Spawn one independent, **read-only** `opus` sub-agent against the branch.

Prompt body: [references/agents/review-fallback.md](agents/review-fallback.md).

## CI repair (step 6, only on `FAIL`)

Only after `ci_watch.sh` returns `FAIL`. Write the failing log to a file
**outside** the working directory first (`<runstate>/ci/<pr>.log`) — a stray
untracked file inside it makes cleanup skip the directory as dirty, and a
commit convention that stages everything would land the log in the change.
Spawn a **`sonnet`** sub-agent (escalate to **`opus`** once the same failure
has survived two attempts in a row), one PR at a time.

Prompt body: [references/agents/ci-repair.md](agents/ci-repair.md).

## Design decision (step 8b)

Spawned at [SKILL.md step 8b](../SKILL.md#8b-unblock-held-designs-in-the-background),
one **`opus`** sub-agent per design-blocked issue, **in the background** — this
session spawns a round in one message and goes straight back to shipping.

This is the only sub-agent in this skill that writes to GitHub, and only two
writes: one comment on the issue and one label clear. It writes nothing in the
checkout, so `{workdir}` is the repo's main checkout even while a parallel batch
is running — it reads there, it never touches the tree.

Prompt body: [references/agents/design-decision.md](agents/design-decision.md).

`VERDICT: DEFERRED` is a result, not a failure — it is the run declining to
invent a product decision, and its `OPEN-QUESTION` is what the step 10 report
puts in front of the user.
