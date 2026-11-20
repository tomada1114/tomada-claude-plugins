# planning-tickets reference

Commands for turning an approved plan into linked issues.

## Contents

- [Batch the writes](#batch-the-writes)
- [Two-pass creation](#two-pass-creation)
- [Native sub-issues and dependencies](#native-sub-issues-and-dependencies)
- [Fallback labels](#fallback-labels)
- [Verification](#verification)

## Batch the writes

Each `gh` call is one permission prompt for the user (and, on a sandboxed host, has to
run as a bare command). Filing 25 issues one call at a time means about 100 prompts,
so send each phase as **one GraphQL request** built by a local script:

1. **Generate** the request JSON with a short local script (no network), so only the
   `gh` call itself needs approval. Use aliases (`m0: …`, `m1: …`), one per write:
   - read state or ids: `i218: issue(number:218){id number title}`, plus
     `repository{id labels(first:100){nodes{id name}}}` once for `createIssue`;
   - create: `createIssue(input:{repositoryId, title, body, labelIds}){issue{number}}`;
   - backfill: `updateIssue(input:{id, body}){issue{number}}`;
   - link: `addSubIssue(input:{issueId, subIssueId}){subIssue{number}}` and
     `addBlockedBy(input:{issueId, blockingIssueId}){issue{number}}`. These take node
     ids (`I_kw…`), not the REST database ids below.
   Pass bodies as GraphQL variables (`"variables": {"b0": "…"}`, `$b0: String!`) so no
   Markdown has to be escaped into the query string.
2. **Send** it with `gh api graphql --input <file>.json --jq '<summary>'`.
3. **Keep a request to about 20 writes.** A larger one can time out and return an HTML
   page (`invalid character '<'`) while GitHub still applies part of it. Never resend
   blindly: re-run the state query, then send only what is missing. For `createIssue`,
   chunk to about 10 and search by title before any retry, or the retry duplicates.

Fall back to one REST call per write (the sections below) only where GraphQL is refused:
a Claude Code cloud session's GitHub proxy rejects `gh api graphql`, `gh issue` and
`gh pr`, and allows `gh api` REST calls.

## Two-pass creation

Issue numbers do not exist until creation, so cross-references are written twice.

1. **Draft every body** to its own file, `NNN-<slug>.md`, where `NNN` is a provisional ID
   in dependency order. Write edges with provisional IDs (`Depends on #P010`). Keep the
   drafts in the caller's state directory (`kicking-off-apps` uses `$STATE/issues/`) or a
   scratch directory — never in the repository.
2. **Create in dependency order** — tracking parents, then foundation, parallel streams,
   integration — recording provisional → real number as you go:
   ```bash
   gh issue create --title "<title>" --body-file 010-schema.md --label "enhancement" --label "priority: P1"
   ```
   Use only labels that exist (`gh label list`); a missing label fails the command.
3. **Backfill**: replace every provisional reference with the real number in all
   drafts, then `gh issue edit <n> --body-file <file>` for each issue whose body changed.
   A foundation issue's `Blocks #N` and a parent's checklist can only be written now.

## Native sub-issues and dependencies

Both REST endpoints take the issue's **database id** in the body, not its number:

```bash
id() { gh api "repos/$REPO/issues/$1" --jq .id; }

# sub-issue under a tracking parent
gh api -X POST "repos/$REPO/issues/<parent-number>/sub_issues" -F sub_issue_id="$(id <child-number>)"

# <blocked-number> is blocked by <blocker-number>
gh api -X POST "repos/$REPO/issues/<blocked-number>/dependencies/blocked_by" -F issue_id="$(id <blocker-number>)"
```

`-F` sends the id as an integer; `-f` would send a string and fail. Link every
`Depends on` edge this way, and every child listed in a parent's checklist. If an
endpoint is unavailable (an old GitHub Enterprise Server), keep the body lines — they
are what automation parses — and say the native links were skipped.

Sources: <https://docs.github.com/en/rest/issues/sub-issues>,
<https://docs.github.com/en/rest/issues/issue-dependencies> — checked 2026-09-29.

## Fallback labels

Only for a repository with no label set of its own (no `.github/labels.yml`, no
`triaging-issues`). Create once:

```bash
gh label create "foundation"  --color 5319E7 --description "Must complete before parallel work"
gh label create "parallel"    --color 0E8A16 --description "Can be worked in parallel"
gh label create "integration" --color FBCA04 --description "Connects parallel streams"
gh label create "tracking"    --color C5DEF5 --description "Checklist of sub-issues; not work itself"
```

## Verification

`gh issue list --state open --json number,title,labels --limit 200` shows the count and
labels; `gh api repos/$REPO/issues/<parent>/sub_issues --jq 'length'` and
`gh api repos/$REPO/issues/<n>/dependencies/blocked_by --jq '.[].number'` show the
native links on one parent and one dependent issue.
