# Lens: tooling, CI, dependencies and agent harness (`TL`)

The machinery around the code: the gates that decide whether a change is good, the
toolchain that builds it, the dependencies it trusts, and the instructions and skills
that agents follow. Harness drift is costly because agents act on the instructions
literally. A skill naming a recipe that no longer exists sends every future run down
the wrong path.

## Survey (facts to collect, no judgment)

- **S-TL1 Gates.** Each gate command (justfile recipes, package scripts, Makefile
  targets from the inventory) with what it runs. Which of them CI runs, per workflow
  and job. Git hooks (lefthook, pre-commit, `.githooks/`) and what they run.
- **S-TL2 Toolchain pins.** Every place a language or tool version is declared:
  `.node-version`, `.python-version`, `engines`, `requires-python`, `mise.toml`,
  `.xcode-version`, CI `setup-*` steps. Flag the values that disagree.
- **S-TL3 Dependencies.** Direct dependencies per manifest with their declared ranges.
  Dependencies that serve the same purpose (two date libraries, two HTTP clients).
  Packages marked deprecated in the lockfile or the manifest.
- **S-TL4 Instruction references.** Every command, recipe, path and skill name cited in
  AGENTS.md, CLAUDE.md, nested AGENTS.md and repository skills. Check each exists:
  path exists, recipe defined, skill present. List the dangling ones with `path:line`.
- **S-TL5 Mirrors and generated copies.** Paths kept in sync by a script (for example
  `.agents/skills` and `.claude/skills`, generated API types). Name the sync and check
  commands, and say whether a CI job enforces them.
- **S-TL6 Lint and type strictness** *(repository-wide)*. Rules disabled globally,
  per-directory overrides, and the count of inline suppressions per rule and directory.

## Analysis (judge each item; "keep, because …" is a valid result)

- **TL1 Gate integrity.** A check that runs locally but not in CI, or the reverse. A
  check a commit can skip. Slow feedback where a narrower command exists but is not
  documented.
- **TL2 Reproducibility.** Disagreeing pins from S-TL2. Unpinned tools in CI.
  Lockfiles not enforced (`--frozen-lockfile`, `--locked`).
- **TL3 Dependency health.** Overlapping, deprecated, unused or abandoned packages,
  and ranges that admit breaking majors. A known vulnerability is **security**. Mark
  it so, and follow the filing rules for security findings.
- **TL4 Harness drift.** Dangling references from S-TL4. Instructions that contradict
  each other or the code. Skills whose "Owns" lines overlap, or a recurring task no
  skill owns. Text that restates what the tooling already enforces.
- **TL5 Strictness vs reality.** Global disables that hide real problems. Suppressions
  clustered in one rule, which suggests the rule or the code needs changing.
- **TL6 Repository scripts.** Scripts without tests where the repository's own rules
  require them. Logic duplicated between scripts. Scripts doing what a gate tool
  already does.
- **TL7 Workflow friction.** Setup steps a fresh clone fails on. Docs whose commands no
  longer work. Manual steps that a recipe could do.

## What a good proposal looks like here

Name the exact file and line to change and the gate that proves it: the CI job that
must now run, or the check recipe that must pass. A harness fix states which
instruction changes and which test or check (for example a harness test over skill
references) keeps it from drifting again.
