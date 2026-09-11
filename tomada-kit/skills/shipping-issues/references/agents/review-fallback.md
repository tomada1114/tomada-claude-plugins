# Review fallback (sub-agent prompt)

Spawned at [SKILL.md step 4](../../SKILL.md#4-local-review--only-where-ci-does-not-review),
only when this session's host will not let it launch `/code-review` directly.
One independent, **read-only** `opus` sub-agent against the branch.

```
Read-only review only — do not edit, create, or delete any file (no `rm`, no
`mv`, no writes), and do not run any command that writes to disk or to git.
Branch {branch} implements
issue #{n} in {owner}/{repo}. It becomes a PR and merges as soon as CI is
green, so a defect you miss here merges. Lint, types and tests already pass.
What no one has done is read the change as a change. That is your job, and
you are reading it in a context that did not write it.

The branch {branch} is checked out at {workdir}. Read the project's own
conventions first — {workdir}/CLAUDE.md and {workdir}/AGENTS.md — then
the specification and the diff against {base}:

  GIT_OPTIONAL_LOCKS=0 git -C {workdir} diff {base}...HEAD

<context>
Issue #{n}: {two-or-three-sentence paraphrase of what the issue asks} — "the
body is authoritative over this summary."
Read it yourself, read-only, with:
  gh issue view {n} --repo {owner}/{repo} --comments
That read is the ONLY GitHub command you are permitted to run.
</context>

Judge exactly what the test suite cannot:
- does the implementation match what the spec actually asked for — nothing
  missing, nothing quietly widened beyond it;
- unnecessary complexity: indirection, options, or abstraction the task did
  not need;
- maintainability: names that mislead, duplicated logic, a comment that is
  already wrong about the code beside it;
- the tests: do they pin the behavior the task is about, or only the shape of
  the implementation? A test that would pass with the bug still present is a
  finding;
- anything the diff walked past — a sibling of the case it fixed, an error
  path it left silent.

Report the defect, never the patch: file, line, what is wrong, why it matters.
I re-derive the fix in the code I can see.

Attach a severity and a confidence to every finding and report all of them; I
decide what blocks. A finding outside this task's scope is still worth
reporting — mark it OUT-OF-SCOPE. Number findings sequentially starting at F1
in the order you list them, and out-of-scope items sequentially starting at
O1 — do not skip numbers or reuse one.

Return exactly:
FINDINGS: <one per line as `F<n> [sev] file:line (conf) — what is wrong — why
           it matters`, sev = high|medium|low and conf = high|medium|low, or
           "none">
OUT-OF-SCOPE: <same shape with `O<n>` instead of `F<n>`, or "none">
TESTS: <verdict on the test changes in one or two lines>
INTENT-MATCH: <does the diff implement the spec as written — yes / no + what
               is missing or extra>
```

`INTENT-MATCH: no` is read before the findings — it says the diff is not
issue #{n}'s change and can arrive with an empty `FINDINGS:` list; send the
missing part back through the Implementation request. Triage every finding in
this session before fixing anything, the same way `--fix`'s output is
triaged.
