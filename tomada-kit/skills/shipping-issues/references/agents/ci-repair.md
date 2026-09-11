# CI repair (sub-agent prompt)

Spawned at [SKILL.md step 6](../../SKILL.md#6-ci-to-green), only after
`ci_watch.sh` returns `FAIL`, one PR at a time. **`sonnet` by default,
escalating to `opus` once the same failure has survived two attempts in a
row.**

Write the failing log to a file **outside** the working directory first
(`<runstate>/ci/<pr>.log`) — a stray untracked file inside it makes cleanup
skip the directory as dirty, and a commit convention that stages everything
would land the log in the change.

```
PR #{pr} implements issue #{n} in {owner}/{repo}; its CI just failed:
{check names, from the parent's failed_checks: line}. I need the cause fixed
and pushed. I will re-check after you return — you cannot, and must not try
to.

Work only inside {workdir}, on branch {branch} — already checked out. Do not
touch any sibling checkout or worktree of the same repository.

<context>
Issue #{n}: {two-or-three-sentence paraphrase of what the issue asks, so a fix
that changes behavior can be judged against what the issue actually asked
for} — "the body is authoritative over this summary."
Read it yourself, read-only, with:
  gh issue view {n} --repo {owner}/{repo} --json title,body,labels,comments
That read is the ONLY GitHub command you are permitted to run — do not touch
the GitHub API otherwise, do not watch CI, do not sleep or poll.
</context>

Base branch: {base_branch}
Verification command: {verify_command, from step 3's smoke run}
Project conventions: read {workdir}/CLAUDE.md and {workdir}/AGENTS.md
before changing anything.

The failing output is in:
  {log_path}

Read that file first. It is outside your work directory; read it there and do
not copy it in. Then fix the cause at {workdir}, commit, and push — return as
soon as your fix is pushed. Never `rm`: undo a probe inside the checkout with
`git checkout --`, or move it aside with `mv`, and name any scratch file you
left behind in your report.

This is attempt {attempt} of 3. {What the previous attempts tried and why it
did not work — leave empty on attempt 1, and never re-send the same
instruction twice; from attempt 3, the accumulated detail rather than the same
instruction again.}

Fix the failure, not the check. Deleting, skipping, or weakening a test to
make it pass is a failed outcome — if the test is genuinely wrong, say so in
UNRESOLVED and stop without pushing. Same for a flaky job: if you believe a
failure is flaky, say which job and why under UNRESOLVED rather than pushing a
no-op commit to re-trigger it.

Return exactly:
CAUSE: <what actually failed, in one or two lines>
FIXES: <one line per repair commit, or "none">
PUSHED: <yes + the remote ref, or "no" + why — "no" ends the repair loop; I do
         not re-check unchanged code>
FOLLOW-UPS: <defects the failure exposed that are NOT this change's to fix,
             one per line as `file:line — what is wrong — what prevents it
             today`, or "none">
UNRESOLVED: <anything needing a human, or "none">
```

The log reaches the run through that path, never through the prompt, so it
never lands in the parent's context. The watch/repair loop — repair, push,
re-watch, up to 3 attempts — lives in the parent. `PUSHED: no` ends the loop;
read `UNRESOLVED` rather than re-watching unchanged code.
