# Run record

The persistent log every step appends to, read when setting up `<runstate>` or
auditing what a stopped run already landed.

```bash
python3 {SKILL_DIR}/scripts/run_record.py --repo <owner>/<repo> --event <kind> \
    [--field k=v ...] [--body-file <path>]
```

Appends one line (or, for `run-start`, a heading plus a line) to `<runstate>/run.md`,
where **`<runstate>`** is
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/shipping-issues/<owner>__<repo>/`
— never rewritten or deleted, so a stopped run keeps what already landed.

Every other file this run generates lives there too, and **never inside a
repo checkout** — the main one or a worktree: filled prompts at
`<runstate>/prompts/<issue>-<step>.md`, issue bodies for follow-ups beside
them, verify baselines at `<runstate>/verify/<n>-baseline.log`, CI logs at
`<runstate>/ci/<pr>.log`, and in parallel mode the worktrees themselves at
`<runstate>/worktrees/<n>/`. An untracked file left in a checkout makes that
working tree read as dirty, and a commit convention that stages everything
would land it in the PR. Call it right after the event happens, not batched at
the end; `--repo` can be omitted when cwd is the repo being shipped.

Events: `run-start`, `selection` (the rubric-shaped block from
priority-rubric.md via `--body-file`), `labels`, `design`, `parallel-group`,
`pr-created`, `review`, `ci`, `merged`, `followup`, `cleanup`, `blocked`,
`note`.

`design` records a settled — or deliberately deferred — design, from either
path: `--field issue=<n> --field mode=<inline|background> --field
verdict=<DECIDED|DEFERRED>`. A `DEFERRED` line is the more valuable of the two
to read back: it is a question waiting on a human, and the label still says
blocked.

`parallel-group` records step 2c's decision once per batch —
`--field issues=<n,m,...> --field mode=<parallel|serial> --field reason=<why>`.
A serial fallback is recorded the same way as a parallel batch: the reason a
run did *not* parallelize is the part worth being able to read back.
