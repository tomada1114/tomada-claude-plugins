# Harness rubric

A coverage checklist for surveying a repository's development harness. It is
deliberately generic: it names *what to look for*, while *what good looks like* is
extracted from the reference repository on each run. The checklist earns its place twice
over — it keeps the survey from drifting into whatever the reference happens to be proud
of, and it catches the areas the reference itself leaves open.

Item IDs (`R1.3`, `R7.2`, …) are stable. Both inventories and the gap table key off
them, so merging two surveys is mechanical rather than a matching exercise.

## Table of Contents

- [The strength ladder](#the-strength-ladder)
- [R1. Policy docs](#r1-policy-docs)
- [R2. Agent harness](#r2-agent-harness)
- [R3. Task runner and developer ergonomics](#r3-task-runner-and-developer-ergonomics)
- [R4. Hooks and local gates](#r4-hooks-and-local-gates)
- [R5. Tests and coverage](#r5-tests-and-coverage)
- [R6. Architecture enforcement](#r6-architecture-enforcement)
- [R7. CI and supply chain](#r7-ci-and-supply-chain)
- [R8. OSS hygiene](#r8-oss-hygiene)
- [R9. Release](#r9-release)
- [Where the reference itself falls short](#where-the-reference-itself-falls-short)
- [What to weigh heaviest](#what-to-weigh-heaviest)

---

## The strength ladder

Presence is a poor comparison on a mature target, where nearly every area exists in some
form. Rate each item on both repos and compare the levels:

| Level | Meaning |
|---|---|
| S0 | Absent. |
| S1 | Written down only — a contributor or an agent can ignore it and nothing fails. |
| S2 | Runnable by hand, but nothing runs it for you. |
| S3 | Enforced in one place, usually CI. |
| S4 | Enforced in CI *and* locally, through the same command, so the two cannot drift. |
| S5 | S4 plus a second, independent mechanism — or an install that verifies itself — so removing one layer still fails the build. |

Four questions separate S3 from S5, and they apply to every area below:

1. **Same command everywhere?** If the hook, the CI job and the contributor each spell
   the check differently, they will diverge, and the divergence surfaces as a PR that
   passed locally and failed in CI.
2. **Is the install verified?** Setup steps that swallow their own errors leave a
   contributor believing a gate is on. A verifier that fails loudly, with an explicit
   opt-out, is the difference.
3. **Can the number be moved quietly?** Coverage excludes, skipped tests,
   `continue-on-error`, `|| true` — a gate that can be widened without review is S1
   wearing an S3 costume.
4. **Are the open gaps named?** A harness that states which gaps it leaves open, and
   why, is stronger than one that silently has the same holes, because the next person
   can tell a decision from an oversight.

---

## R1. Policy docs

**Look for**

- R1.1 One root policy document (`AGENTS.md`, `CLAUDE.md`, or equivalent) that is the
  single source of truth for how the repo is worked on.
- R1.2 A quick reference: the exact commands a contributor runs, and a table mapping
  kind-of-change → the narrowest check that catches it.
- R1.3 An architecture section, or a pointer to one: named zones and the allowed
  direction of dependency between them.
- R1.4 An index of the agent skills and scoped rule files — skill → when to load it.
- R1.5 A security and human-approval section: what an agent may do unattended and what
  needs a human.
- R1.6 An enforcement-layers section separating what is mechanical from what is
  procedural, **naming the gaps left deliberately open** and the reason for each.
- R1.7 A second host document carrying only the differences (typically `CLAUDE.md`
  importing `AGENTS.md`), plus something that detects drift between them.

**Strength** — spot-check three of the doc's claims against the files: a doc that
describes an earlier version of the repo is S1 at best. Check whether the commands it
quotes are the same strings the task runner defines, and whether anything fails when
they drift.

**Typical class** — agnostic in structure, adapt in content. The section skeleton copies
directly; every command inside it is rewritten.

---

## R2. Agent harness

**Look for**

- R2.1 A skills directory, with thin entry documents and details pushed into references.
- R2.2 The index in R1.4 actually matching the directory.
- R2.3 Multi-host duality handled explicitly: one authoring source plus a generated
  mirror for the other host, rather than two hand-maintained copies.
- R2.4 Drift detection over that mirror — a check command, a test, and a hook step.
- R2.5 Path-scoped rule files that load only for the files they govern.
- R2.6 A mention-triggered agent workflow, with least-privilege token permissions.

**Strength** — hand-maintained copies are S1 however tidy they look today; generated +
checked is S4. Note the known trap: a symlinked skills directory can make some hosts
register nested reference files as skills of their own, which is why the reference may
have chosen generation over linking.

**Typical class** — the sync and drift machinery is agnostic; the individual skills
classify one by one (see `transplant-classes.md`).

---

## R3. Task runner and developer ergonomics

**Look for**

- R3.1 One task runner as the single entry point (package scripts, `justfile`,
  `Makefile`, task definitions) — not commands scattered across README, CI and hooks.
- R3.2 One-command setup from a bare clone to a runnable checkout, with tool versions
  pinned by a version manager rather than prose.
- R3.3 A narrowest-check-per-change mapping, so a one-line docs change does not cost a
  full build, and a full check that is still one command.
- R3.4 A fix command that applies everything auto-fixable.
- R3.5 Repo scripts that run before install (no dependencies of their own), report stable
  error codes on stderr, and refuse to write outside the repo.
- R3.6 The manual steps that remain after bootstrap either scripted or listed with the
  trigger that makes each necessary.

**Strength** — count the steps between `git clone` and a green check. Then check whether
a CI job asserts that path from scratch; a documented bootstrap that nothing exercises
rots within a release.

**Typical class** — agnostic in shape, adapt in tool. The narrowest-check table is the
part worth carrying across regardless of runner.

---

## R4. Hooks and local gates

**Look for**

- R4.1 A hook configuration under version control covering at least pre-commit.
- R4.2 Every hook step calling the same task-runner command CI and humans call — the
  hook file defining no rules of its own.
- R4.3 Install-then-verify: hooks installed by a lifecycle step, then a verifier that
  fails loudly when they were not placed, with a named opt-out for the cases that need
  one.
- R4.4 A staged-content guard: environment files, secret directories and
  credential-shaped content blocked before they can be committed.
- R4.5 A written principle that judgment calls belong in PR review — the hook blocks only
  what it can decide mechanically.
- R4.6 A documented bypass, and the bypass acknowledged as a named gap rather than left
  implicit.

**Strength** — does a fresh clone get the hooks, or only a contributor who happened to
run the right command? Is the guard itself covered by tests? A hook that duplicates CI's
rules in its own syntax is S2, not S4, no matter how complete it looks.

**Typical class** — agnostic principle, adapt tool.

---

## R5. Tests and coverage

**Look for**

- R5.1 A stated rule for where a new test goes, not just a directory that exists.
- R5.2 Test kinds separated (unit, component, integration, UI, smoke) and each runnable
  on its own.
- R5.3 Coverage measured in CI and reported.
- R5.4 Per-area floors rather than one repo-wide number, with the riskiest areas held
  highest.
- R5.5 A written rule that the number is not moved by adding excludes or skipping tests.
- R5.6 A related-tests-only mode, fast enough for the pre-commit hook.
- R5.7 Tests that pin the harness itself: template placeholder strings, workflow
  invariants, generated-mirror equality.

**Strength** — a single global floor lets a well-covered area subsidise an uncovered
one, so per-area floors are a real step up. Check whether CI fails on a drop or merely
prints it, whether every entry in the exclude list has a reason next to it, and — where
the stack has no reliable branch coverage — whether that limitation is written down as
deliberate rather than quietly absent.

**Typical class** — agnostic policy, adapt runner.

---

## R6. Architecture enforcement

**Look for**

- R6.1 Named zones or modules with an allowed dependency direction.
- R6.2 That direction enforced mechanically — import restrictions in the linter, a
  module-graph assertion in a test, or separate build targets that cannot see each other.
- R6.3 Enforced twice by independent mechanisms.
- R6.4 A public contract distinguished from the private surface behind it.
- R6.5 A single reader for configuration and environment, so access is greppable.

**Strength** — the test is subtractive: imagine the lint rule deleted, and ask whether
anything still fails. "Core must not import the UI framework", written in a doc and
nowhere else, is S1 — one of the most common S1 items on an otherwise strong repo.

**Typical class** — adapt, and the area most likely to have no equivalent in the target
stack. When the cheapest mechanical enforcement is not obvious, this is the natural spike
issue rather than a guess.

---

## R7. CI and supply chain

Rows here map onto OpenSSF Scorecard checks, which is a useful second opinion on
coverage and a shared vocabulary for the issue bodies.

| Item | Look for | Scorecard check |
|---|---|---|
| R7.1 | CI running the same task-runner commands, split into a cheap static job and a test job | CI-Tests |
| R7.2 | `permissions: {}` at workflow top level, re-declared least-privilege per job | Token-Permissions |
| R7.3 | Actions pinned by commit SHA with a version comment; toolchain versions pinned once, not per job | Pinned-Dependencies |
| R7.4 | Dependabot or Renovate configured, with a cooldown matching the package manager's minimum release age | Dependency-Update-Tool |
| R7.5 | Code scanning and workflow linting | SAST |
| R7.6 | Scheduled dependency audit and secret scanning, the scanner itself pinned | Vulnerabilities |
| R7.7 | Dependency review on pull requests, with a license deny-list | Dependency-Update-Tool, License |
| R7.8 | Branch protection on the default branch with required checks | Branch-Protection |
| R7.9 | Scorecard itself running on a schedule | — |

**Strength** — check whether each job can actually fail the build: `continue-on-error`,
an advisory-only scanner, or a required check that was never marked required all read as
green while enforcing nothing. Branch protection is worth checking through the API
rather than the docs; its absence is invisible until the day it matters.

**Typical class** — agnostic. Workflow YAML moves across stacks almost unchanged; only
the build and test commands inside it are rewritten.

---

## R8. OSS hygiene

**Look for**

- R8.1 A README stating what the project is, how to run it, and how to contribute.
- R8.2 Community health files: CONTRIBUTING, LICENSE, CODE_OF_CONDUCT, SUPPORT, FUNDING,
  and a security route — either SECURITY.md or private vulnerability reporting, linked
  from the issue-template config.
- R8.3 Issue forms (bug / feature / task) and a pull request template.
- R8.4 Labels as code: a labels file in the repo plus a create-or-update sync script.
- R8.5 CODEOWNERS.
- R8.6 The community profile complete enough that GitHub stops nagging.

**Strength** — labels that exist only in the web UI cannot be reviewed or restored, so a
labels file is a genuine step up rather than bureaucracy. A missing SECURITY.md is not a
gap when private reporting is enabled and linked; check before proposing one.

**Typical class** — agnostic, and the cheapest wins in the whole rubric.

**Note** — `priority: P0`–`P3` labels are a prerequisite for the issues this skill files.
When the target has no priority vocabulary, that is a P0 of its own (see
`sequencing.md`).

---

## R9. Release

**Look for**

- R9.1 A release workflow, tag- or manually triggered, producing the distributable
  artifact.
- R9.2 Signing, notarization and publishing steps gated on the secrets being present, so
  a fork's run degrades instead of failing.
- R9.3 Build provenance attestation.
- R9.4 A stated home for the version number and the thing that updates it.
- R9.5 Changelog or release notes generated rather than hand-written.

**Strength** — can the artifact be rebuilt from a clean checkout at a tag by someone
without the secrets, at least up to the signing step?

**Typical class** — adapt; packaging is the most stack-specific area here.

---

## Where the reference itself falls short

Rows neither repo satisfies are part of the survey result, recorded in the inventory as
missing on both sides. They are not automatically proposals — the reference is the
standard the user asked for, not this file. Raise them only when the fix is cheap and
the value is clear, and mark them as not-from-reference so the user can tell a
transplant from an addition.

## What to weigh heaviest

When the gap table is longer than one sitting of work, R3 (task runner and ergonomics),
R5 (tests and coverage) and R4 (hooks) carry the most weight: they are what a contributor
touches on every change, and every later issue is easier once a single check command
exists. R8 is the cheapest, so it fills the tail. R6 is the most likely to need a design
decision before it can be scoped at all.
