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
worktree**: filled prompts at `<runstate>/prompts/<issue>-<step>.md`, issue
bodies for follow-ups beside them, CI logs at `<runstate>/ci/<pr>.log`. An
untracked file left in a worktree makes cleanup's branch pass skip it as dirty,
and a commit convention that stages everything would land it in the PR. Call
it right after the event happens, not batched at the end; `--repo` can be
omitted when cwd is the repo being shipped.

Events: `run-start`, `selection` (the rubric-shaped block from
priority-rubric.md via `--body-file`), `labels`, `pr-created`, `review`, `ci`,
`merged`, `followup`, `cleanup`, `blocked`, `note`.
