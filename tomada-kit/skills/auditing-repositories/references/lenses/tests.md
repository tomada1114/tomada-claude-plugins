# Lens: tests (`TS`)

Whether the test suite would catch the regressions that matter, and whether the
production code lets a test be written first. Line coverage is a weak signal on its
own. Judge the suite by the behavior it pins.

## Survey (facts to collect, no judgment)

- **S-TS1 Layout and runners.** Test directories per area, their runner and config
  files, any coverage floor (`path:line` of the threshold), and which gate command runs
  which suite locally and in CI.
- **S-TS2 Untested units.** Start from the inventory's `untested_candidates`. For each
  candidate, confirm whether any test imports or exercises it (grep the module name).
  Report confirmed-untested units with their line counts.
- **S-TS3 Tests of the implementation.** Tests that mock the unit under test or a
  module it owns, assert only on call counts or arguments, or are snapshot-only. List
  each with `path:line`.
- **S-TS4 Non-determinism.** Real time (`now()`, `Date.now`, `sleep`, timers),
  unseeded randomness, real network or file system outside a temp dir, and
  order-dependent shared state. Include skipped, `xfail`, `.only` or `@disabled` tests,
  with the reason given, if any.
- **S-TS5 Shape.** Test files over 500 lines, setup blocks repeated across files
  (quote the repeated lines once and list the locations), and the test-to-source line
  ratio per area.
- **S-TS6 Core-flow coverage.** For each core flow the Product section or the
  requirements name, which tests (unit, integration, end-to-end) exercise it. Name the
  test functions.

## Analysis (judge each item; "keep, because …" is a valid result)

- **TS1 Behavior coverage of what matters.** Core flows and risky decisions (money,
  data loss, auth, state transitions) without a test that fails when they break.
- **TS2 Tests that cannot fail.** Tests from S-TS3 that would still pass with the
  behavior broken. Say what to assert instead, through which public surface.
- **TS3 Level and placement.** Work done at the wrong level: an end-to-end test
  checking a pure rule, a unit test standing up a database. The same behavior covered
  three times while a neighbor goes uncovered. Placement that contradicts the
  repository's own placement rules.
- **TS4 Determinism.** Each S-TS4 item that can flake. Name the seam (clock, id
  source, fake) that removes it, and whether the repository already has one.
- **TS5 Test design debt.** Copy-pasted setup that should be a fixture or builder.
  Giant files that hide what is covered. Names that do not say the behavior.
- **TS6 Gate integrity.** Suites that CI does not run. A coverage floor far below or
  far above reality. Local and CI commands that differ.
- **TS7 Testability blockers.** Production code that prevents writing the test first:
  hidden globals, constructors doing I/O, no injection point. The fix is often an
  `AR4` seam. Cross-reference it rather than reporting twice.

## What a good proposal looks like here

Name the first test to write: file, test name, the behavior it asserts, and why it
fails today or what it pins. A bug found while surveying is a finding with a failing
test as its close condition. A suite restructure moves in steps that keep the suite
green and the coverage floor met at each step.
