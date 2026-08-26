# Quality criteria

Checks, not scores. Each check is a question with a definite answer and a place in the repo to get it. Every failure becomes one finding line; no totals, no grades.

## Table of contents

- [How to run the checks](#how-to-run-the-checks)
- [Content checks](#content-checks)
- [Master-file checks](#master-file-checks)
- [Size and placement](#size-and-placement)
- [Red flags](#red-flags)
- [Finding format](#finding-format)

## How to run the checks

Read every effective instruction source, every canonical `AGENTS.md`, every stub free section, and every `.claude/rules/*.md` in the inventory. Content checks `C1`–`C7` and the red flags apply to every file read; master-file checks `M1`–`M7` apply to `AGENTS.md` files only (a rule file's placement is migrate's job, so audit judges only its content). For each check, look at the evidence named below before judging — a claim in the rule file is only correct if the repo agrees. Record every failure you find, at every severity, with a `file:line` citation; ranking and trimming happen when the findings are presented, not while looking.

Evidence sources, in the order they usually settle a question: package manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`), task runners (`Makefile`, `justfile`, `Taskfile.yml`, npm scripts), CI workflows (`.github/workflows/*.yml`), `README.md`, the top-level directory listing, and lockfiles for the package manager actually in use.

## Content checks

### C1 Commands

Is every command a contributor needs present, and does each one exist in the repo? Install, dev/run, build, test, lint/format, and whatever CI actually invokes. Check each documented command against the manifest scripts or the task runner; check the reverse direction too — a CI step with no counterpart in the master is a gap. Single-test invocation is worth a line whenever the suite is slow.

### C2 Architecture map

Can a session that reads only this file work out where code lives and which direction dependencies run? Directory tree with one purpose per entry, entry points, and the layering rule if there is one. Compare against the real top-level tree: entries for directories that no longer exist fail this check, as do trees that stop at `src/`.

### C3 Non-obvious patterns and gotchas

Does the file capture what the code cannot say for itself — ordering dependencies, required env for the test suite, workarounds and why they exist, traps that have already cost someone an afternoon? Evidence: comments marked with a warning in source, unusual CI steps, retry or serialization flags in test config. A file with no gotchas section in a project older than a few weeks is usually an omission, not a clean bill of health.

### C4 Conciseness

Does every line change what a session would do? Failures: restating an identifier's meaning that the name already gives, explaining a well-known framework, ceremony sections ("Introduction", "Summary"), the same fact stated in two sections.

### C5 Currency

Do the file's claims still hold? Spot-check paths, command names, dependency versions, and the tech stack list against the manifest. Anything referring to a deleted path or a renamed script fails.

### C6 Actionability

Is each instruction executable as written? Commands copy-pasteable with the right runner prefix, paths real and repo-relative, rules stated as directives rather than aspirations ("run `just check` before pushing", not "quality matters").

### C7 Semantic scope preservation

When content came from `.claude/rules` or another host-specific source, does the destination preserve the original intent, scope, exceptions, and enforcement strength? A mechanically copied `paths:` header, a silently broadened rule, or an unreported loss of a Claude-only trigger fails this check. Use [semantic-rule-conversion.md](semantic-rule-conversion.md) as the evidence record.

## Master-file checks

### M1 Project-specific, not generic engineering advice

The master is team-shared and must stand alone, but it must not spend its budget on advice that holds for every project ("write tests", "use meaningful names", "handle errors"). Developers already carry host-level global instruction files outside the repo for that. Keep only what is true of *this* project. Flag generic lines individually so the user can decide.

### M2 No host-specific wording in AGENTS.md

Both hosts read the master, so it must be tool-agnostic. Any mention of a specific assistant, its tools, its settings files, its hooks, or its slash commands belongs in the stub's free section. Cite the line and propose the move.

### M3 No import syntax in AGENTS.md

A line starting with `@` outside a code fence is literal text to Codex and an inverted dependency inside Claude Code. Inventory reports these as R004; the fix is in `migration.md`.

### M4 Stub integrity

Managed block present, well-formed, first thing in the file, content exactly `@AGENTS.md`. Free section holds only Claude-only mechanics — if it has grown project rules, they belong in the master.

### M5 No duplication across files

The same rule stated in the root master and a package master, or in a master and a rule file, will drift. Keep it once, at the outermost level where it is true. Cite both locations in one finding.

### M6 Path-scoped content is where its scope is

A section that only applies under one directory belongs in that directory's master (plus its stub), or — when the user prefers it guaranteed on Codex — stays at the root with the scope in its heading. A rule about `packages/api/**` living unmarked in the root master will be applied everywhere.

### M7 Codex effective source is understood

Does the report identify the selected non-empty source in each relevant directory, the launch-directory boundary, the configured document budget, and any global Codex instruction source? An active `AGENTS.override.md` or configured fallback must not be silently treated as the canonical master; report the divergence and preserve it until the user decides.

## Size and placement

- Root `AGENTS.md`: target **≤ ~150 lines**. Root bloat is the failure mode this skill exists to prevent — every line at the root is loaded by every session in every directory.
- Effective chain root→cwd: stay within the configured `project_doc_max_bytes` (32 KiB by default), including any global instruction bytes the inventory can detect. Codex stops adding documents at the cap; inventory reports R005 with the effective value.
- When a long section applies to exactly one directory, do not shorten it by deleting substance — propose moving it to that directory's `AGENTS.md` plus stub, and leave a one-line pointer at the root only if a session at the root genuinely needs to know it exists.
- When a long section applies everywhere and is still long, cut it to the decisions it changes.
- Match length to substance. No filler sections, no redundant summaries, no boilerplate carried from a template.

## Red flags

Scan for these directly; each is a finding on sight.

- Commands that would fail as written — wrong runner, wrong path, script no longer in the manifest.
- References to deleted or renamed files and directories.
- Dependency or runtime versions that disagree with the manifest.
- Unedited template placeholders (`<project name>`, `<command>`, `TODO`, `TBD`).
- Advice that would be identical in any repo.
- `TODO` items with no owner that predate the last release.
- The same information in the root master, a package master, and a rule file.
- A rule file whose `paths:` glob matches nothing on disk.
- A free section containing tool-agnostic project rules.

## Finding format

One line per finding, grouped by file, nothing else in the report body:

```
- [<check-id>] <path>:<line> — <what is wrong> → <proposed fix>  (<severity>)
```

Severity is `must` (wrong or broken — will mislead a session), `should` (degrades quality or budget), `could` (worth doing when touching the file anyway). Use the check id from this file (`C1`–`C7`, `M1`–`M8`) or the inventory code (`R001`–`R013`, `H001`–`H009`) when a script already found it. Inventory severities map directly: `error` → `must`, `warn` → `should`, `info` → `could`. Findings whose fix is a fold or deletion (R001, R003, R004, R007, R008) are reported with "run `migrate`" as the fix; audit does not apply them.

<example>
- [C5] AGENTS.md:22 — `npm run test:watch` is not in package.json (scripts: dev, build, test, lint) → replace with `npm test -- --watch`  (must)
- [M2] AGENTS.md:48 — "Claude Code will run the hook automatically" is host-specific → move to the CLAUDE.md free section  (should)
- [C1] AGENTS.md — CI runs `npx tsc --noEmit` (.github/workflows/ci.yml:31) but no type-check command is documented → add to the commands table  (should)
</example>

No numeric scores, no letter grades, no overall verdict line. Present the list, then wait for the user to choose what to apply.
