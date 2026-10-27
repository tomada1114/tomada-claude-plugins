# Lens: file structure and code quality (`CQ`)

Whether a newcomer, human or agent, can find things, read them, and change them
without tripping over leftovers. This lens works at the file and function level. A
problem that is really about module boundaries belongs to `AR`; cross-reference it.

## Survey (facts to collect, no judgment)

- **S-CQ1 Layout conventions.** The directory and file-naming conventions the
  repository or its framework states, and files that do not follow them: a wrong
  directory, a mixed case style, a test beside the source where the rule says
  otherwise.
- **S-CQ2 Complexity hotspots.** Functions over 60 lines or nested more than four
  levels deep, in the files from the inventory's `largest_files` and `churn_hotspots`,
  with `path:line` spans.
- **S-CQ3 Duplication.** Blocks of 8 or more near-identical lines in two or more places.
  Quote the block once and list the locations. Note when the copies have already
  diverged.
- **S-CQ4 Leftovers.** Exported symbols with no reference outside their own file and
  its tests. Commented-out code. Template placeholders or sample code that survived a
  bootstrap. Dependencies declared but never imported. The inventory's
  TODO/FIXME/HACK markers.
- **S-CQ5 Escape hatches.** Type escape hatches (`any`, `as unknown as`,
  `# type: ignore`, `cast(`, force unwraps, `@ts-expect-error`, `noqa`) and broad or
  empty exception handlers, with `path:line` and any reason given beside them.
- **S-CQ6 Literal repetition.** The same magic number or string in three or more places.

## Analysis (judge each item; "keep, because …" is a valid result)

- **CQ1 Findability.** Whether the layout tells a reader where a new screen, route,
  rule or script goes. Misplaced files from S-CQ1. A structure that fights the
  framework's conventions.
- **CQ2 Hotspots.** Complexity that sits on high churn is debt with interest. Leave
  complex but stable code alone unless it is wrong.
- **CQ3 Duplication.** Separate copies that change for the same reason are worth
  extracting. Look-alike code with different reasons to change is not; say so
  explicitly.
- **CQ4 Dead and obsolete code.** Confirm each S-CQ4 item is truly unused: check dynamic
  references, framework conventions and public API status. Then propose removal, or
  wiring it in when it is unfinished work.
- **CQ5 Error handling and types.** Swallowed errors, errors converted to strings too
  early, and escape hatches without a reason. Inconsistent error types across one
  layer.
- **CQ6 Readability.** Names that mislead, comments that contradict the code, and
  literals from S-CQ6 that deserve a name.
- **CQ7 Currency.** APIs deprecated in the versions the manifests pin. Hand-rolled code
  the framework or standard library now provides. Idioms the language version has
  superseded.

## What a good proposal looks like here

Batch mechanical cleanups by kind and area, such as "remove the 7 unused exports in
`frontend/src/lib`", into one issue. One issue per symbol is noise. A cleanup that
changes no behavior needs no new test; its close condition is the existing suite plus a
grep or lint rule that keeps the problem from returning.
