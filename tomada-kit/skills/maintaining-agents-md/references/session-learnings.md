# Folding session learnings into the rules

The end-of-session pass: turn what this session had to discover into rules the next one starts with. Part of audit mode; also the right response to "add what we learned today to the project rules".

## 1. Reflect

Go back over the session and collect what was missing at the start, with the evidence still in reach:

- Commands run or discovered that were not in the rule files — including the ones found by reading a manifest or a CI file.
- Conventions followed after being corrected, or inferred from existing code.
- Testing approaches that worked: how to run one test, fixtures, isolation requirements.
- Environment and configuration quirks that cost a retry.
- Gotchas hit: ordering dependencies, silent failures, tools that must not be run twice.
- Anything the user said in the session that reads as a standing rule rather than a one-off instruction.

Skip anything that will not recur: a specific bug fixed, a one-time data cleanup, a decision already captured in code.

## 2. Route each item

| item | destination |
|---|---|
| applies repo-wide, tool-agnostic | root `AGENTS.md`, in the section it belongs to |
| applies inside one package or app directory | that directory's `AGENTS.md` (create it plus its stub only if that directory is a real boundary) |
| applies to a file pattern with no directory | root section titled with the glob |
| host-specific mechanics — hooks, settings, host-only skills | free section of that directory's `CLAUDE.md` stub |
| personal or machine-local | `CLAUDE.local.md` (gitignored); say so rather than writing it into a shared file |

Before adding, check whether the fact is already stated somewhere in the chain. Extending an existing line beats appending a near-duplicate section.

## 3. Draft

One line per concept, in the file's existing language and section order. Format: `` `<command or pattern>` — <what it does or why it matters> ``. No preamble, no explanation of standard technology, no new top-level section when an existing one fits.

Watch the budget: the root file targets ≤ ~150 lines and the chain ≤ 32 KiB. If the additions push past that, propose a move (a long directory-scoped section to that directory's master) or a deletion of something now stale in the same pass.

## 4. Show the diff and apply

Present each addition as a diff against the target file, with one line of justification tied to what happened in the session:

<example>
### AGENTS.md — Gotchas

Why: the suite failed twice in this session before `--runInBand` was found.

```diff
 ## Gotchas

+- Tests share one SQLite file — run with `--runInBand`; parallel runs fail with `SQLITE_BUSY`.
```
</example>

Apply only the additions the user approves, then snapshot and run the stub sync so any newly created directory master gets its `CLAUDE.md`.
