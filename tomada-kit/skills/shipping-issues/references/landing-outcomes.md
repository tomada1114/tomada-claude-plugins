# Landing outcomes

What `land_pr.sh` can return and what each result requires. Read it when the
merge step returns anything other than a clean merge.

`land_pr.sh <pr> --issue <n>` prints two lines — `result:` and `issue:`. The
`--issue` flag makes it re-check the closing link before merging and confirm the
issue really closed after, closing it explicitly with a back-reference comment
if GitHub's auto-close did not fire. Add `--auto` when the PR is blocked on a
review requirement rather than on failing checks.

| `result:` | What it means | What to do |
|---|---|---|
| `NOT_LINKED` / `WRONG_BASE` | the script refused to merge because the issue would be orphaned | repair it — `link_check.sh --fix` for a missing keyword, `gh pr edit <pr> --base <default>` for a wrong base — then retry. Pass `--no-link-check` only if the user asked for a PR that deliberately does not close its issue. |
| `DRAFT` | still a draft, and the script could not (or was told not to) mark it ready | `gh pr ready <pr>`, then retry. |
| `reviewDecision: REVIEW_REQUIRED` or `mergeStateStatus: BLOCKED` in the JSON it echoes (the same two facts `ci_watch.sh` prints as `review_decision` / `merge_state`) | a human review gate, not a failing check | re-run with `--auto` to arm auto-merge, report that it is armed and that the issue closes when it lands, and move on to the next issue. |
| `MERGE_REFUSED` / conflicts | the merge itself was rejected | report the reason; for conflicts, rebase in the branch's worktree and return to the CI step. |
| `ALREADY_MERGED` / `NOT_OPEN` | the PR left the open set before this call | take the issue's state from the `issue:` line and move on without retrying. |
| `MERGE_UNCONFIRMED` / `ERROR` | the outcome is unestablished | re-read PR and issue state with `gh`. **Never report a merge on this result alone.** |
