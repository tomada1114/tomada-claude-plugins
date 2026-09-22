<!-- prompt-lint-ignore-file: D002 -->
# Issue body template

One file per issue under `bodies/`, named after its plan key. The shape below is the
planning-tickets skeleton trimmed for chore work: no user-facing behaviour is changing,
so the User Story collapses to one line and the Concrete Examples section is replaced by
exact steps.

The reader to write for is someone who has never seen the reference repository and
cannot open it. Everything they need is either in the body or under
`docs/harness-reference/` in their own checkout.

## Table of Contents

- [Skeleton](#skeleton)
- [What the script appends](#what-the-script-appends)
- [Cross-issue references](#cross-issue-references)
- [Titles](#titles)
- [Worked example](#worked-example)

---

## Skeleton

````markdown
## Goal

**As a** contributor to this repository **I want** [what changes] **so that** [what
becomes possible or stops going wrong].

## Background & Context

[Two or three lines: what the repo does today with a `file:line` citation, what the
reference does instead, and which rubric item this closes (e.g. R4.3).]

**Reference material**

| In-repo path | What to take from it |
|---|---|
| `docs/harness-reference/[path]` | [the specific thing — a section, a job list, a principle — and what to ignore] |

## Steps

1. [Exact command or exact file path and the exact change.]
2. …

## Requirements (EARS)

| ID | Requirement | Verification |
|----|-------------|--------------|
| REQ-001 | **When** [trigger], the system shall [action]. | [command or file that shows it] |
| REQ-002 | **If** [failure condition], **then** the system shall [behaviour]. | [how to check] |

## Translation notes

<!-- adapt items only; delete this section for agnostic ones -->

| Reference tool | Target tool | Must stay invariant |
|---|---|---|
| [tool] | [tool] | [the one sentence that has to remain true after the swap] |

## Acceptance Criteria

- [ ] REQ-001: [checkable condition with real values]
- [ ] [the repo's own check command] passes

## Not In Scope

- NOT [excluded thing] → {{#other-key}}
- NOT [edge case] → [reason it is deferred]
````

Notes on the sections that carry the weight:

- **Reference material** is the reason the seed pull request exists. Every path in this
  table is inside the target repository, under `docs/harness-reference/`. An absolute
  path, a path in a clone, or a GitHub URL to the reference repo makes the row unusable
  for whoever picks the issue up. The right-hand column matters as much as the left: a
  row that says "copy this file" invites copying the parts that do not apply.
- **Steps** are where junior-proofing happens. Name the file, the command and the string
  to add. "Configure the coverage threshold" is not a step; "set `minimum_coverage` to
  `80` in `scripts/coverage.sh:14`, and add `Packages/MyAppKit/MyAppUI` to the excluded
  targets list" is.
- **Acceptance Criteria** always include the repo's own check command, because that is
  what the implementer will actually run before opening the pull request.
- Match the body's length to the work. A labels-file copy does not need a Translation
  notes table or five requirements.

## What the script appends

Do not write these by hand — `create_issues.py` adds all three, and a hand-written copy
either duplicates or contradicts what it generates:

- `## Dependencies` with `Depends on #N` / `Blocks #N` lines, resolved from `depends_on`
  and its reverse edges.
- The ship contract comment (`<!-- ship: tier=… area=… blocked-by=… blocks=…
  touches=… design=… -->`), from the plan fields.
- The idempotency marker (`<!-- harness-transplant: key=… -->`), which is how a re-run
  recognises an issue it already created.

## Cross-issue references

Issue numbers do not exist when the bodies are written. Refer to another issue in the
plan by its key in double braces — `{{#coverage-floors}}` — anywhere in the prose. The
script substitutes the real number during creation. A literal `#12` written by hand will
point at whatever issue happens to be number 12 in that repository.

## Titles

Follow the target repository's own commit and pull request convention, which preflight
read out of its AGENTS.md or CONTRIBUTING. With Conventional Commits that is usually
`chore(harness): <imperative summary>`; a scope of `ci`, `test` or `docs` is better when
the change sits squarely in one of those.

Titles are English unless the target repository's language policy says otherwise. Do not
carry across bracket prefixes or tags from another repo's convention — they mean nothing
here and they collide with whatever the target already uses.

## Worked example

`bodies/hook-verify-install.md`, an adapt item closing R4.3:

````markdown
## Goal

**As a** contributor to this repository **I want** the git hooks to be verified after
install **so that** a clone that silently failed to install them cannot pass review on
checks that never ran.

## Background & Context

`just install` sets `core.hooksPath` (`justfile:12`) but nothing confirms the hooks were
placed, so a clone whose install step failed looks identical to one that succeeded. The
reference repo runs a verifier after install that exits non-zero with a named error code,
and documents a single opt-out for environments that legitimately have no hooks. Closes
rubric item R4.3.

**Reference material**

| In-repo path | What to take from it |
|---|---|
| `docs/harness-reference/scripts/verify-hooks.mjs` | the check order (hooks path set → file exists → file executable) and the `ERR_HOOKS_*` codes; not the JavaScript |
| `docs/harness-reference/AGENTS.md` | the "Enforcement layers" paragraph naming the opt-out as a deliberate gap |

## Steps

1. Create `scripts/verify-hooks.sh`, executable, no dependencies beyond `git` and a
   POSIX shell.
2. Have it fail with `ERR_HOOKS_PATH` when `git config core.hooksPath` is unset,
   `ERR_HOOKS_MISSING` when `.githooks/pre-commit` does not exist, and
   `ERR_HOOKS_NOEXEC` when it is not executable. Write each message to stderr.
3. Exit 0 immediately when `ALLOW_MISSING_GIT_HOOKS=1` is set, printing one line saying
   the check was skipped.
4. Call it from the `install` recipe in `justfile`, after the `core.hooksPath` line.
5. Add the opt-out and its reason to the enforcement layers section of `AGENTS.md`.

## Requirements (EARS)

| ID | Requirement | Verification |
|----|-------------|--------------|
| REQ-001 | **When** `just install` completes, the system shall verify the hooks are installed and executable. | `just install` on a clean clone exits 0 |
| REQ-002 | **If** a hook is missing, **then** the system shall exit non-zero with an `ERR_HOOKS_*` code on stderr. | `rm .githooks/pre-commit && ./scripts/verify-hooks.sh` prints `ERR_HOOKS_MISSING` and exits 1 |
| REQ-003 | **While** `ALLOW_MISSING_GIT_HOOKS=1` is set, the system shall skip the check and report that it did. | `ALLOW_MISSING_GIT_HOOKS=1 ./scripts/verify-hooks.sh` exits 0 |

## Translation notes

| Reference tool | Target tool | Must stay invariant |
|---|---|---|
| a Node postinstall verifier | a shell script called from the `install` recipe | the failure is loud and names which hook is missing; the opt-out is explicit and written down |

## Acceptance Criteria

- [ ] REQ-001: a fresh clone followed by `just install` leaves `core.hooksPath` set and
      `.githooks/pre-commit` executable
- [ ] REQ-002: removing the hook makes the verifier exit 1 with `ERR_HOOKS_MISSING`
- [ ] REQ-003: the opt-out is honoured and documented in `AGENTS.md`
- [ ] `just check` passes

## Not In Scope

- NOT adding new hook steps → {{#hook-calls-task-runner}}
- NOT installing hooks in CI — CI runs the commands directly, so hooks there would be
  duplicate work
````
