# The CI review contract

A repository can review every pull request in CI with Claude Code
(`anthropics/claude-code-action`). When it does, that review replaces the local
`/code-review` pass, and [SKILL.md step 6b](../SKILL.md#6b-review-rounds) reads
its result through `review_digest.py`. This file is the one place the format
both sides depend on is written down: the repository's review prompt emits it,
the script parses it.

## Table of Contents

- [Why a contract at all](#why-a-contract-at-all)
- [The summary comment the review posts](#the-summary-comment-the-review-posts)
- [The response comment this skill posts](#the-response-comment-this-skill-posts)
- [Severity](#severity)
- [What the review prompt must say](#what-the-review-prompt-must-say)
- [review_digest.py](#review_digestpy)

## Why a contract at all

The review job's check **succeeds whether or not it found anything**, so a
green `ci_watch.sh` verdict says nothing about the review. And a review that
never ran — a fork or Dependabot pull request that gets no secret, a pull
request that edits the review workflow itself, which the action refuses to run
against — leaves exactly what a clean review leaves: no inline comments and a
green check. The summary marker is what tells the three apart: present with
findings, present with none, absent.

## The summary comment the review posts

Exactly one top-level pull-request comment per reviewed head commit, whose
**first line** is the marker:

```
<!-- claude-review v1 sha=<40-hex head sha> must=<n> should=<n> nit=<n> pre=<n> -->
```

followed by one line per finding, in this shape and nothing else on the line:

```
- [<severity>] R<n> `<path>:<line>` — <what is wrong> — <why it matters>
```

`R1`, `R2`, … restart at 1 in every summary. The four counts must equal the
number of lines of each severity. Anything else in the comment (a heading, the
skills applied, "No issues found.") is free prose and is ignored by the parser.

The same findings are also posted as inline comments, prefixed
`[<severity>] R<n>:`, for a human reader. The parser reads the summary only.

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

## What the review prompt must say

Whatever else a repository's review prompt contains, it must instruct the
reviewer to:

1. post the summary above as its last action, with the marker's `sha=` set to
   `${{ github.event.pull_request.head.sha }}`, even when there are no findings;
2. read earlier `claude-review-response` comments (`gh pr view --comments`) and
   not raise again a finding marked rejected or deferred, unless the stated
   reason is factually wrong — and then say why it does not hold;
3. confirm each finding against the code before reporting it.

`gh pr comment`, `gh pr view` and `gh pr diff` must be in its `--allowedTools`.

## review_digest.py

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/review_digest.py <pr> [--repo o/r] \
    [--sha <sha>] [--reviewer <login>]...
python3 ${CLAUDE_SKILL_DIR}/scripts/review_digest.py <pr> --respond <body-file> \
    [--sha <sha>]
```

Reads the pull request's top-level comments and prints:

```
review: REVIEWED | NOT_REVIEWED
sha: <sha looked for, default the PR head>
round: <n distinct head shas the reviewer has summarized on this PR>
counts: must=<n> should=<n> nit=<n> pre=<n>
findings:
  R1 must-fix src/x.ts:12 — <what> — <why>
warnings:
  <counts disagree with the lines / unparseable finding lines / marker comments
   ignored because their author is not a reviewer>
```

Exit 0 when `REVIEWED`, 3 when `NOT_REVIEWED`, 2 when GitHub could not be read.

Only comments by a **bot** account whose login is in `--reviewer` (default
`claude[bot]`) count. The repository is public-facing: anyone can post a
comment carrying the marker, and a forged `must=0` would otherwise wave a
pull request through. A marker from anyone else is listed under `warnings:`
with its author's login — if the real reviewer shows up there, pass its login
with `--reviewer` rather than loosening the check.

When several summaries match the sha, the last one wins.
