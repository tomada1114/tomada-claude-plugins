# The CI review convention

A repository can review every pull request in CI with Claude Code
(`anthropics/claude-code-action`). When it does, that review replaces the local
`/code-review` pass, and [SKILL.md step 6b](../SKILL.md#6b-review-rounds) reads
its result through `review_digest.py`. This file is the one place the
convention both sides depend on is written down: the repository's review prompt
follows it, this skill reads it.

## Table of Contents

- [Why a marker at all](#why-a-marker-at-all)
- [The summary comment the review posts](#the-summary-comment-the-review-posts)
- [The response comment this skill posts](#the-response-comment-this-skill-posts)
- [Severity](#severity)
- [What the review prompt must say](#what-the-review-prompt-must-say)
- [review_digest.py](#review_digestpy)

## Why a marker at all

The review job's check **succeeds whether or not it found anything**, so a
green `ci_watch.sh` verdict says nothing about the review. And a review that
never ran — a fork or Dependabot pull request that gets no secret, a pull
request that edits the review workflow itself, which the action refuses to run
against (it logs "Workflow validation failed" and exits green) — leaves exactly
what a clean review leaves: no inline comments and a green check. The summary
marker is what tells the three apart: present with findings, present with none,
absent.

**The marker is the only part read by a script; everything else is read by a
model.** Both ends of the findings are models — one writes them, this session
reads them — so the finding lines are a convention for clarity, not a grammar.
An earlier version parsed them strictly and reported a real finding as "zero
findings" because the reviewer had left out its `R<n>`. Reading them as prose
costs nothing and cannot drop one.

## The summary comment the review posts

One top-level pull-request comment per reviewed head commit, containing the
marker on a line of its own (first line by preference):

```
<!-- claude-review v1 sha=<40-hex head sha> must=<n> should=<n> nit=<n> pre=<n> -->
```

The `sha=` is load-bearing and must be the head commit reviewed. The four
counts are the reviewer's own tally, shown back to this session as
`declared:` — useful as a cross-check, never trusted over the list itself.

Then, one line per finding, in this shape:

```
- [<severity>] R<n> `<path>:<line>` — <what is wrong> — <why it matters>
```

`R1`, `R2`, … restart at 1 in every summary and cover every finding,
`pre-existing` included; the number is how the response refers back. Anything
else in the comment (a heading, the skills applied, "No issues found.") is free
prose. When the reviewer slips — a missing number, a missing tag, a different
dash — the reader numbers it by position, judges its severity from the table
below, and says so in the response.

The same findings, except `pre-existing`, are also posted as inline comments,
prefixed `[<severity>] R<n>:`. `review_digest.py` prints those too, so the
reader sees any detail that did not fit on the summary line.

## The response comment this skill posts

After triaging a round, this skill posts one comment whose first line is:

```
<!-- claude-review-response v1 sha=<40-hex sha the findings were made against> -->
```

followed by one line per finding:

```
- R<n> fixed — <what changed>
- R<n> rejected — <why the finding is wrong, against the code>
- R<n> deferred — <#issue, or "follow-up" when it is filed after the merge>
```

The next round's review reads these, so a rejected finding is not raised again
unless the stated reason is itself wrong. Post it through
`review_digest.py --respond`, which writes the marker.

## Severity

| Severity | Means | Example |
|---|---|---|
| `must-fix` | The change is wrong: a bug, a broken contract, a rule violation with a concrete consequence | a handler that now returns 200 on invalid input; a secret written to a tracked file |
| `should-fix` | Real and in the changed lines, but low risk today | a missing test for an edge the change introduced; a rule broken without breakage yet |
| `nit` | A suggestion: naming, simplification, a comment | "this helper duplicates `x()`" |
| `pre-existing` | A defect in lines the pull request did not touch | a sibling function with the same bug |

The reviewer's tag is a claim like any other: a `nit` that is really a broken
contract is triaged as `must-fix`, and the response says why.

## What the review prompt must say

Whatever else a repository's review prompt contains, it must instruct the
reviewer to:

1. post the summary above as its last action, with the marker's `sha=` set to
   `${{ github.event.pull_request.head.sha }}`, even when there are no findings;
2. give every finding a severity and an `R<n>` — `pre-existing` ones included,
   though they get no inline comment;
3. read earlier `claude-review-response` comments (`gh pr view --comments`) and
   not raise again a finding marked rejected or deferred, unless the stated
   reason is factually wrong — and then say why it does not hold;
4. confirm each finding against the code before reporting it.

`gh pr comment`, `gh pr view` and `gh pr diff` must be in its `--allowedTools`.
A worked example line in the prompt holds the shape better than a template
with placeholders alone.

## review_digest.py

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/review_digest.py <pr> [--repo o/r] \
    [--sha <sha>] [--reviewer <login>]...
python3 ${CLAUDE_SKILL_DIR}/scripts/review_digest.py <pr> --respond <body-file> \
    [--sha <sha>]
```

Reads the pull request's comments and prints:

```
review: REVIEWED | NOT_REVIEWED
sha: <sha looked for, default the PR head>
round: <n distinct head shas the reviewer has summarized on this PR>
declared: <the marker's counts, or none>
summary:
  | <the summary comment, verbatim>
inline:
  - <path>:<line>
    | <an inline comment by the reviewer on this sha, verbatim>
warnings:
  <markers ignored because their author is not a reviewer / inline comments
   that could not be read>
```

Exit 0 when `REVIEWED`, 3 when `NOT_REVIEWED`, 2 when GitHub could not be read.
It decides only what a script can decide exactly — is there a summary for this
head, from whom, which round — and hands the findings over unparsed.

The marker is found tolerantly: `claude-review v<n>` and `sha=<40 hex>` on one
line, anywhere in the comment, any spacing or case. What is **not** tolerant is
who wrote it. Only comments by a **bot** account whose login is in
`--reviewer` (default `claude[bot]`, confirmed on a real review) count. The
repository is public-facing: anyone can post a comment carrying the marker,
and a forged "No issues found." would otherwise wave a pull request through. A
marker from anyone else is listed under `warnings:` with its author's login —
if the real reviewer shows up there, pass its login with `--reviewer` rather
than loosening the check.

When several summaries match the sha, the last one wins.
