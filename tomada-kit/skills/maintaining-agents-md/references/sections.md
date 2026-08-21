# Sections and templates

Shapes for `AGENTS.md`. Use the sections a project actually needs; an empty section is worse than a missing one.

## Table of contents

- [Length calibration](#length-calibration)
- [Section catalogue](#section-catalogue)
- [Template: root (minimal)](#template-root-minimal)
- [Template: root (comprehensive)](#template-root-comprehensive)
- [Template: monorepo root](#template-monorepo-root)
- [Template: package or app directory](#template-package-or-app-directory)
- [Pattern-scoped conventions](#pattern-scoped-conventions)
- [Agent hooks](#agent-hooks)
- [What to add](#what-to-add)
- [What not to add](#what-not-to-add)

## Length calibration

- Root `AGENTS.md`: target **≤ ~150 lines**. Every root line is loaded by every session in every directory of the repo.
- Effective chain root→working directory: stay within `project_doc_max_bytes` (32 KiB by default), including detected global instructions. Codex stops adding documents at the cap.
- When a long section applies to exactly one directory, move it to that directory's `AGENTS.md` (plus its stub) rather than compressing it at the root. That is the intended way to stay under the line target without losing detail.
- Match length to substance. No filler sections, no summary of the file inside the file, no template headings left in because the template had them. A fact the survey could not establish is omitted — never written as "unknown" or "TBD" in the master.

## Section catalogue

| section | include when | shape |
|---|---|---|
| Overview | always | 1–3 lines: what the project is, what it runs on |
| Commands | always | table, one row per command, copy-pasteable |
| Architecture | more than a handful of source files | tree with one purpose per entry, plus the dependency direction |
| Key files | a few files carry outsized meaning | `path — why it matters` |
| Conventions | the project deviates from its ecosystem default | directives, not preferences |
| Environment | the app needs env vars or setup steps | `VAR — purpose`, and where the values come from |
| Testing | the test workflow is non-obvious | how to run one test, fixtures/factories location, isolation requirements |
| Gotchas | always, once the project has any history | one line per trap |
| Review checklist | there is a gate before PR | numbered, each item verifiable |
| Agent hooks | the repo wires hooks both hosts run | 3–6 lines: event, what it blocks, how to trust them |

## Template: root (minimal)

````markdown
# <Project name>

<One line: what it is and what it runs on.>

## Commands

| Command | Purpose |
|---|---|
| `<install>` | Install dependencies |
| `<dev>` | Run locally |
| `<test>` | Run the test suite |
| `<lint>` | Lint and format |

## Architecture

```
src/
├── <dir>/   # <purpose>
└── <file>   # <purpose>
```

<One line on the dependency direction or layering rule.>

## Gotchas

- <trap and the one-line reason it exists>
````

## Template: root (comprehensive)

Same as minimal plus the sections the project earns, in this order: Overview, Commands, Architecture, Key files, Conventions, Environment, Testing, Gotchas, Review checklist.

`neonify/AGENTS.md` is a working example at 71 lines: Overview, Quick Reference (a `just` command block plus the fallback for people without `just` and the single-test invocation), Architecture (tree plus the one-way layering rule and why it is testable), Review Checklist, and a short reminders list.

## Template: monorepo root

````markdown
# <Repo name>

<One line.>

## Packages

| Package | Path | Purpose |
|---|---|---|
| `<name>` | `packages/<name>` | <purpose> |

Each package has its own `AGENTS.md`; package-local rules live there, not here.

## Commands (repo-wide)

| Command | Purpose |
|---|---|
| `<bootstrap>` | Install all workspaces |
| `<test-all>` | Test every package |

## Cross-package rules

- <shared convention, e.g. generated code direction, version pinning policy>
````

Keep the root thin in a monorepo: it loads for every session anywhere in the repo, and a session working in one package pays for every other package's rules.

## Template: package or app directory

For new content, applies to a directory that is a real boundary — its own manifest, its own test or build command, its own deploy target; do not create one for a plain source folder. A directory-scoped rule file being migrated is the exception: it goes to its directory regardless (see `migration.md`), and then this template is only a loose guide — keep the rule's own heading and text.

````markdown
# <package name>

<What this package is responsible for, and what it must not do.>

## Commands

| Command | Purpose |
|---|---|
| `<test>` | Run this package's tests (from this directory) |

## Boundaries

- Depends on: `<sibling packages>`
- Must not import: `<forbidden direction>`

## Notes

- <local gotcha>
````

Pair it with a `CLAUDE.md` stub in the same directory. Remember that a Codex session started at the repo root never reads it — anything a root-level session must know goes in the root master instead.

## Pattern-scoped conventions

For rules bound to a file pattern rather than a directory, keep them compact in the root master, with the glob in the heading so the scope survives:

```markdown
## Conventions: `**/*.test.ts`

- One `describe` per exported symbol; file name mirrors the source file.
- Factories in `tests/factories/`; no inline mock objects.
```

This is the destination for a Claude-only rule file whose `paths:` glob has no literal directory prefix. Directory-shaped globs go to that directory's master instead — see `migration.md`.

## Agent hooks

Hooks under `.agents/hooks/` run on both hosts, so what they enforce belongs in the master, not in the stub's free section. Keep it to what changes a session's behaviour:

```markdown
## Agent hooks

`.agents/hooks/` runs on both hosts; wiring lives in `.claude/settings.json` and `.codex/hooks.json`.

- `guard.py` (before a tool call) — refuses edits to `uv.lock`, `.env*`, `secrets/**`, and `git commit --no-verify`.
- `format.py` (after an edit) — formats the edited file. Do not run the formatter again yourself.
- `stop_check.py` (end of turn) — runs `just check` when the tree has changes; fix what it reports.

Codex project hooks require a trusted project layer and exact command-definition review (`/hooks`); review again when a command string changes. Start Claude Code at the repo root — hooks do not load from a subdirectory launch.
```

Skip the section when the repo has no hooks. Place it after the commands and quality-gate sections and before any project-specific closing sections (reminders, checklists). Claude-only events stay in the stub's free section; see `hooks.md`.

## What to add

One example each; keep the real entries this dense.

- **Commands discovered the hard way** — `npm run build:dev` — fast build, skips minification.
- **Gotchas** — tests must run with `--runInBand`: they share one database.
- **Dependency and ordering facts** — `src/bootstrap.ts` initializes crypto before auth; import order matters.
- **Testing approach that works** — API tests use `supertest` with the helper in `tests/setup.ts`.
- **Configuration quirks** — `NEXT_PUBLIC_*` are baked at build time, not read at runtime.

## What not to add

- Restatements of code — "the `UserService` class handles user operations."
- Universal advice — "always write tests", "use meaningful names."
- One-off history — "fixed the login button in abc123."
- Background explanations of standard technology — describe how *this* project uses JWT in one line, not what JWT is.
- Anything host-specific — that belongs in the `CLAUDE.md` free section.
