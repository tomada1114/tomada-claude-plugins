# Migration

Folding an existing rule setup into the AGENTS.md-master shape. Content moves first, files are deleted last, and nothing is deleted before its new home has been reread.

## Table of contents

- [Order of operations](#order-of-operations)
- [Classify the sources](#classify-the-sources)
- [Destination table](#destination-table)
- [Preserving a rule's scope](#preserving-a-rules-scope)
- [Fixing an inverted import](#fixing-an-inverted-import)
- [Deduplicating while folding](#deduplicating-while-folding)
- [Deletion rules](#deletion-rules)
- [Language](#language)
- [Worked example](#worked-example)

## Order of operations

1. Run inventory; work from its file list, states, and findings rather than re-walking the tree.
2. Snapshot every file that will be modified or deleted, with a label such as `pre-migrate`. Record the snapshot id for the final report.
3. Classify each source (below) and decide its destination.
4. Write the destinations: create or extend `AGENTS.md` at root and at each real package boundary.
5. Reread each destination file and confirm every rule from the sources is present, in the same language and with its scope intact.
6. Only then remove the migrated originals.
7. Run the stub sync so every directory with an `AGENTS.md` gets its `CLAUDE.md`.
8. Report: what moved where, what was deleted, what was left alone, and the snapshot id.

Steps 5 and 6 are one unit — a source file is deleted only after its content has been read back at the destination, not merely written there.

## Classify the sources

| source | how to read it |
|---|---|
| legacy `CLAUDE.md` body | tool-agnostic project rules, unless the line names a host, its tools, its settings, or its hooks |
| `.claude/CLAUDE.md` | same as above; an alternative root location that must not survive alongside a root `AGENTS.md` |
| `.claude/rules/*.md` with directory-shaped `paths:` | scoped to `scope_dir` from the inventory (the longest literal directory prefix of the glob) |
| `.claude/rules/*.md` with pattern-only `paths:` | scoped to a file pattern, no directory |
| `.claude/rules/*.md` with no `paths:` | global |
| `@` lines inside an `AGENTS.md` | inverted imports; see below |
| `CLAUDE.local.md` | out of scope — personal and gitignored |
| existing `AGENTS.md` | the destination, not a source; extend it in place |

## Destination table

| classification | destination |
|---|---|
| global rule (any source) | section in the root `AGENTS.md` |
| directory-scoped (`scope_dir` exists on disk) | `<scope_dir>/AGENTS.md` + `<scope_dir>/CLAUDE.md` stub — the rule already declared that directory as its scope; this keeps the root master small |
| pattern-only | compact root section titled with the glob: `## Conventions: **/*.test.ts` |
| mixed scope (globs share no common directory) | split by glob, or keep as one pattern-titled root section if splitting would duplicate the text |
| host-specific mechanics (hooks, settings, host-only skills, wording naming an assistant) | free section of the `CLAUDE.md` stub in that directory |
| personal preference | leave in `CLAUDE.local.md`, or tell the user it belongs there |

Trade-off to state in the plan, not to decide silently: a subdirectory master loads lazily in Claude Code but reaches Codex only when Codex is launched inside that directory. When a directory-scoped rule is short (a handful of lines) and the user would rather have it guaranteed on Codex, offer the root-section alternative with the glob in the heading.

## Preserving a rule's scope

A rule file's `paths:` frontmatter is load-bearing information that disappears when the file does. Carry it into the destination text:

- Directory-scoped into that directory's own master: the directory part is implicit — drop it; keep any file filter the glob carried (`src/**/*.jsx` → first line `対象: *.jsx` / `Applies to: *.jsx`). A bare `src/**` needs no scope line.
- Anything folded into the root: state the scope in the heading (`## Conventions: src/**/*.jsx`) or in the first line of the section ("Applies to files under `src/`."). A rule that silently loses its scope will be applied repo-wide.
- Keep one section per original scope. Merging two globs into one section loses both.

## Fixing an inverted import

An `AGENTS.md` whose first line is `@./CLAUDE.md` (as in `youtube-management/AGENTS.md:1`) points the master at the stub: literal junk for Codex, and a cycle risk once `CLAUDE.md` imports back.

1. Snapshot both files.
2. Delete the `@./CLAUDE.md` line from `AGENTS.md`.
3. Fold whatever `CLAUDE.md` holds into `AGENTS.md` (tool-agnostic parts) and into the stub free section (host-specific parts).
4. Rewrite `CLAUDE.md` as the stub — the sync script does this once the body is empty of unique content.
5. Reread `AGENTS.md`: it must now stand alone with no `@` lines outside code fences.

## Deduplicating while folding

- Drop lines that are generic engineering advice; developers already carry host-level global instruction files outside the repo, and the project file's budget is better spent on what is true only here. List what was dropped in the report so the user can object.
- When the same rule appears in two sources, keep it once at the outermost destination that covers both scopes.
- When two sources conflict, do not pick silently: keep the newer wording, and flag the conflict with both citations for the user to settle.

## Deletion rules

| file | deleted when |
|---|---|
| `.claude/rules/<name>.md` | its content is verifiably present at the destination and a snapshot exists; remove `.claude/rules/` itself once it is empty |
| `.claude/CLAUDE.md` | folded into the root `AGENTS.md` and verified |
| legacy `CLAUDE.md` body | replaced by the stub only after its content is verified at the destination; the sync script refuses this without `--force` |
| `CLAUDE.local.md` | never |
| `.claude/settings.json`, hooks, host-only skills | never — they are configuration, not rules; the stub free section describes them |

Leaving `.claude/rules/` in place after a successful fold is not a safe compromise: the rules keep loading on one host and drift from the master. Either finish the move or leave the rule files untouched and report it.

## Language

Keep each rule in the language it was written in. A Japanese `CLAUDE.md` becomes a Japanese `AGENTS.md`; translation changes the rules the team agreed on and is out of scope. Section headings may be normalized to match the surrounding file, and the language of new headings follows the existing content.

## Worked example

`memo-app`: a 36-line Japanese `CLAUDE.md` (概要 / 技術スタック / ディレクトリ構造 / 開発コマンド / コーディング規約 / 禁止事項), no `AGENTS.md`, plus `.claude/rules/component-rules.md` with `paths: ["src/**/*.jsx"]`.

- The whole `CLAUDE.md` body is tool-agnostic → root `AGENTS.md`, Japanese preserved, section order kept.
- `component-rules.md` is directory-shaped (`src/` exists) → `src/AGENTS.md` headed `# コンポーネントルール` with the first line `対象: *.jsx`, so the extension filter survives the move, plus a `src/CLAUDE.md` stub. The plan notes that Codex sees it only when launched inside `src/`; because the rule is three lines, the plan offers the root-section alternative (`## コンポーネントルール: src/**/*.jsx`) and lets the user pick.
- Root `CLAUDE.md` becomes the stub; there is no host-specific content to keep, so the free section stays empty.
- `.claude/rules/component-rules.md` is deleted after rereading `src/AGENTS.md`; `.claude/settings.local.json` and `.claude/skills/` are untouched.
