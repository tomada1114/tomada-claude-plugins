# Review fix, parallel mode (sub-agent prompt)

Spawned at [SKILL.md step 4](../../SKILL.md#4-local-review--only-where-ci-does-not-review)
in parallel mode, or at [step 6b](../../SKILL.md#6b-review-rounds) when the
accepted findings are more than the session should write itself — only for
findings this session has already read and accepted, one **`sonnet`** sub-agent
per branch that has any.

`/code-review --fix` writes to the session's own working tree, which in
parallel mode is the main checkout sitting on the default branch — the wrong
tree — so the review runs read-only and the writing is delegated here
instead. Zero accepted findings → no spawn.

```
Branch {branch} implements issue #{n} in {owner}/{repo} and is, or is about to
become, a PR. A review has already run against it and I have triaged the findings
myself; below are the ones I accepted. Apply exactly these and nothing else.

Work only inside {workdir} — not any sibling checkout or worktree of the same
repository. Branch {branch} is already checked out there; do not switch
branches, and do not create one.

<context>
Issue #{n}: {two-sentence paraphrase of what issue #{n} asks for}, "the body
is authoritative over this summary."
Read it yourself, read-only, with:
  gh issue view {n} --repo {owner}/{repo} --comments
That read is the ONLY GitHub command you are permitted to run.
</context>

<findings>
{one per line, pre-numbered by me as `F<n> file:line — what is wrong — why it
matters`. Findings I rejected are not listed here and must not be inferred.}
</findings>

Project conventions: read {workdir}/CLAUDE.md and {workdir}/AGENTS.md before
changing anything.
Verification command: {verify_command}

Do:
1. Fix each finding at its cause, not at its symptom.
2. If a finding is wrong on closer reading — the code already handles it, or
   the fix would change behavior issue #{n} did not ask to change — do NOT
   apply it. Report it under REJECTED with the reason. A finding I accepted
   from a summary can still be wrong in front of the code, and you are the
   one in front of the code.
3. Do not fix anything that is not in the list. Real defects you notice go to
   FOLLOW-UPS, not into this diff.
4. Run the verification command in the **foreground** — never in the
   background where you then have to poll it — then commit and push. Push
   before you return.
5. No GitHub write of any kind beyond the read above — no `gh pr`, no
   `gh issue edit/comment/close`, no label change. Never `rm`: undo a probe
   inside the checkout with `git checkout --`, or move it aside with `mv`,
   and name any scratch file — including a throwaway fixture or repository
   you created under a temp directory — you left behind in your report.
6. Use my F-numbers verbatim in APPLIED and REJECTED; do not renumber.

Return exactly:
APPLIED: <one line per finding fixed, `F<n> -> <what changed>`, or "none">
REJECTED: <one line per finding not applied, with why, or "none">
VERIFY: <exact command run> -> <pass/fail + the failing output if any>
PUSHED: <yes + the remote ref, or "no" + why>
FOLLOW-UPS: <defects you saw that are NOT in the list, one per line as
             `file:line — what is wrong — what prevents it today`, or "none">
```

`REJECTED` is read, not skimmed — it is the run's only signal that a finding
this session accepted did not survive contact with the code, and a rejection
that reads like a real defect goes back through the same loop with the reason
addressed. `FOLLOW-UPS` feeds step 8 like every other one.
