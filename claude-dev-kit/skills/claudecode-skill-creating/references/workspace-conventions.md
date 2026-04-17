# Workspace and Output Path Conventions

This reference covers how production skills choose output paths, structure their workspaces, and protect destructive operations with snapshots. These conventions matter for any skill that writes more than a single file, runs in a multi-skill pipeline, or modifies user state.

## Why deterministic paths beat /tmp

The default instinct for "where should this skill write its scratch files?" is `/tmp` or a UUID directory. Production skills almost never do this. Instead, they compute a path from the user's input that is **predictable, persistent, and human-readable**.

**Reasons to avoid `/tmp` and random paths:**

1. **Re-entry**: the user comes back days later wanting to continue. With a deterministic path they `cd` straight in. With a UUID they have to guess.
2. **Pipeline handoff**: the next skill in the chain needs to find this skill's output without being told the absolute path. See "Artifact-driven handoff" in `orchestration-patterns.md`.
3. **Idempotent re-runs**: running the skill again on the same input updates the existing files in place, instead of creating `.../foo-2/`, `.../foo-3/` orphans.
4. **Failure forensics**: if the skill crashes, the workspace is still on disk for inspection. `/tmp` may already be gone.
5. **No permission surprises**: writing under `~/<project>/` inherits the project's permissions and git status. `/tmp` is outside any project.

The only legitimate use of `/tmp` in a skill is for **truly transient byproducts the user will never want to see** — for example, an intermediate JSON that a script consumes and immediately deletes. Even then, prefer a `.tmp/` subdir under the workspace.

## Path conventions observed in production

| Class of skill | Path template | Example |
|---|---|---|
| Design / docs pipeline | `~/<project>/design/{ticket-id}-{slug}/` | `~/draever/design/12345-add-export-button/` |
| Verification / testing scratch | `~/Desktop/testing/{YYYYMMDD}_{slug}/` | `~/Desktop/testing/20260407_config_check/` |
| Single-file outputs | `<project-root>/<deterministic-name>.<ext>` | `~/draever/un-soul/CONTRIBUTING.md` |
| Per-PR artifacts | `~/<project>/pr/{pr-number}/` | `~/draever/pr/4567/` |

The shape that recurs:

```
<persistent-root>/<category>/<id>-<slug>/
                              │
                              ├── input artifacts
                              ├── output artifacts
                              ├── .snapshot/   (if destructive)
                              └── .tmp/        (rare, transient)
```

## Computing the slug

The slug is what makes the path predictable. Rules that work in practice:

1. Take the user's input (`$ARGUMENTS`, ticket title, PR title).
2. Lowercase, replace spaces and punctuation with `-`, strip non-ASCII.
3. Truncate to 4–6 words (~40 chars).
4. **Document the rule in SKILL.md** so the user can predict the path before running the skill.

Example:

```
Input:   "12345 顧客一覧画面に CSV エクスポートを追加"
ID:      12345
Words:   ["顧客一覧画面に", "CSV", "エクスポートを追加"]
Slug:    "csv-export"  ← extracted English keywords; ASCII only
Path:    ~/draever/design/12345-csv-export/
```

If the input is purely non-ASCII, ask the user for an English slug in Phase 0 rather than autogenerating something cryptic. Make the slug a human-friendly handle, not a hash.

## Declaring inputs and outputs in SKILL.md

Every skill that participates in a pipeline should have these two sections at the top of SKILL.md, immediately after the description and before the workflow:

```markdown
## Inputs

This skill reads:
- `<workspace>/ticket.md`        — required
- `<workspace>/00_current-state.md` — optional, gates Phase 1 questions
- `<workspace>/overview.md`      — required if invoked after the design phase

## Outputs

This skill writes:
- `<workspace>/backend.md`       — backend design section
- `<workspace>/frontend.md`      — frontend design section
- `<workspace>/e2e-testcases.md` — numbered acceptance tests (TC-01..TC-NN)
```

This is the **public contract** of the skill. Other skills, future-you, and the user all read this. Treat it as an API surface, not as documentation.

## Snapshot and restore for destructive operations

**Use when**: the skill modifies state outside its workspace — config files, settings.json, environment variables, git branches, database state. Anything you can't `rm -rf workspace/` to undo.

**Pattern (from `~/.claude/skills/cc-cli-verify/`):**

```
1. Create the workspace.
2. mkdir <workspace>/.snapshot/
3. For each file you are about to mutate:
     cp <target> <workspace>/.snapshot/<basename>.orig
4. Perform the mutation.
5. Run the test / verification.
6. Restore: cp <workspace>/.snapshot/<basename>.orig <target>
7. Verify the restoration succeeded before reporting success.
```

The `.snapshot/` directory is **inside the workspace** so the user can manually restore from it if the skill itself crashes mid-flight. Document the restore command in SKILL.md so the user can run it themselves in an emergency.

If your skill spawns a separate process (e.g. a Claude Code session via `tmux-orchestrating`), snapshot before spawning and restore after the process completes — even on error. Wrap in a `trap`/`finally` if you can.

## Idempotent re-runs

When the user runs the skill twice on the same input, the second run should not corrupt the first. Two strategies:

**Strategy A: Update in place (recommended for design pipelines).**
- Detect existing artifacts in the workspace.
- For each output file, ask: "should I overwrite, append, or merge?"
- Default to overwrite for fully-regenerated files (e.g. `mr-description-be.md`).
- Default to merge for files the user may have hand-edited (e.g. `ticket.md` with manual notes).
- Document the per-file policy in SKILL.md.

**Strategy B: Suffix with iteration (for evaluation/eval workspaces).**
- `iteration-1/`, `iteration-2/`, etc. under the workspace root.
- Used when comparing runs is the whole point (e.g. skill-creator's eval loop).

Don't mix strategies in one skill. Pick one and stick with it.

## Cleanup policy

Be explicit about cleanup. The skill should answer:

- What does the workspace contain after a successful run? (kept indefinitely, user owns)
- What does it contain after a failed run? (kept for inspection)
- Is there ever an automatic deletion? (almost always: no)
- Where is `.tmp/` cleaned up? (at the end of the run that created it)

Production skills almost never auto-delete the workspace. The user is in charge of cleanup. The only files that get auto-removed are intermediates explicitly marked as transient.

## Examples to study

- `~/draever/.claude/skills/unsoul-feature-designing/SKILL.md` — design pipeline workspace, deterministic path, file-list outputs
- `~/draever/.claude/skills/ticket-intake/SKILL.md` — first skill in the pipeline; creates the workspace and seeds initial files
- `~/draever/.claude/skills/design-sync/SKILL.md` — idempotent re-run that reconciles existing artifacts with current code (Strategy A done well)
- `~/.claude/skills/cc-cli-verify/SKILL.md` — snapshot/restore of `~/.claude/settings.json` for safe CLI experimentation
- `~/.claude/skills/tmux-orchestrating/scripts/setup.sh` — workspace bootstrap script that creates the queue/state files used by sibling scripts
