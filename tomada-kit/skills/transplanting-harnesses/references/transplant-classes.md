# Transplant classes

Every gap-table row gets one of three classes. The class decides what the issue asks
for, and — for one of the three — that the work is split across two issues rather than
one.

## Table of Contents

- [The three classes](#the-three-classes)
- [Classify the invariant, not the file](#classify-the-invariant-not-the-file)
- [Placeholder first, translation second](#placeholder-first-translation-second)
- [When the target stack has no equivalent](#when-the-target-stack-has-no-equivalent)
- [Example translations](#example-translations)

---

## The three classes

| Class | Test question | What the issue asks for |
|---|---|---|
| **agnostic** | Would this file work in the target repo with nothing changed but paths and names? | Copy it in, adjust paths, prove the repo's own check command still passes. |
| **adapt** | Does the invariant carry over while the implementation cannot? | Two issues: place a copy or placeholder, then translate it. |
| **specific** | Is this about the reference project's own domain? | Skip — after extracting any agnostic pattern buried inside it. |

Agnostic is more common than it looks. Workflow YAML, label definitions, issue forms,
pull request templates, CODEOWNERS, the section skeleton of a policy document, and the
*wording* of a guard principle all move across stacks nearly untouched; only the
commands inside them change.

Specific is rarer than it looks, and skipping it wholesale loses the best material in
the reference. A skill about the reference project's own feature is specific; the
review pattern inside it — two independent graders plus an adjudication step, say — is
agnostic and worth an issue of its own. Read a specific item once, extract the pattern,
then skip the item.

## Classify the invariant, not the file

One file often holds rows of more than one class. Split the row before classifying it:

- A hook config is agnostic in principle ("every hook step calls the same command CI
  calls") and adapt in content (the commands themselves).
- A coverage config is agnostic in policy (per-area floors, no moving the number with
  excludes) and adapt in mechanism (the coverage tool and its threshold syntax).
- A policy document is agnostic in structure (quick reference, architecture,
  enforcement layers with named gaps) and adapt in every command it quotes.

When in doubt, write the invariant as one sentence that does not name a tool. If that
sentence is still true in the target repo, the row is agnostic or adapt, never specific.

## Placeholder first, translation second

Adapt rows are split into two issues, in this order, because the alternative is one
issue that stalls halfway with nothing to show.

**Issue A — place it.** Put the file at its final path in the target repo, wired into
the task runner, using the target's own naming. The content is either the reference's
file with paths adjusted, or a minimal stand-in that does the smallest true version of
the job. Issue A is small, mergeable, and answers the question "where does this live?"
once, so every later issue has a real path to edit.

**Issue B — translate it.** Replace the stand-in with the real implementation in the
target stack, and make it gate. Issue B carries the Translation notes: reference tool →
target tool, and the one or two sentences of invariant that must survive the swap.

Two rules keep the pair honest:

- **A placeholder reports, it does not gate.** A stand-in that exits zero is a gate
  everyone believes in and nothing behind it. Have it print what it is not yet checking,
  and leave the command non-blocking until issue B lands. The seam is then visible in
  every run rather than discovered months later.
- **Issue B exists before issue A is merged.** It is filed in the same plan, with A as
  its dependency, so the placeholder can never become the permanent answer by default.
  Where anything else in the plan depends on the gate actually gating, B inherits that
  priority — see `sequencing.md`.

## When the target stack has no equivalent

Some invariants have no ready tool on the other side; import-boundary enforcement is the
usual one. Handle it in this order:

1. **State the invariant without the reference's tool in it.** "Core code cannot depend
   on the UI framework" is portable; "add a `no-restricted-imports` zone rule" is not.
2. **Enumerate what the target stack could do mechanically**, cheapest first: a test that
   asserts the property, a build-level separation that makes the violation not compile, a
   custom rule in whatever linter is already installed, a grep in CI. Cheapest that
   actually fails the build beats most elegant.
3. **Ask which of three routes to take**, with a recommendation:
   - a **spike issue** — `design: open` in the plan, which gives the issue the
     `blocked: design` label so a downstream shipping workflow holds it rather than
     implementing a guess;
   - a **named deliberate gap** — an issue that records the gap in the policy document's
     enforcement-layers section along with the reason it stays open. This is a real
     outcome and often the right one: a gap someone chose beats a gap nobody noticed;
   - **skip**, when the invariant does not apply to the target at all.

## Example translations

Illustrative only. This table is one pair of repositories, captured once; the run's own
reference and target decide the real mapping, and a stack not listed here is normal.

| Invariant | Reference side (TypeScript / Node) | One target-side option (Swift / macOS) |
|---|---|---|
| Format and lint on every change | Prettier + ESLint | SwiftFormat + SwiftLint |
| Types checked separately from build | `tsc --noEmit` | the compiler, via a build task |
| Unit tests with a fast related-only mode | Vitest projects | Swift Testing + XCTest, filtered by target |
| Coverage floors per area | V8 coverage with per-glob thresholds | `llvm-cov` / `xccov` plus a script asserting a floor per target |
| Import boundaries enforced twice | `no-restricted-imports` zones + a module-graph test | package target graph + access control, plus a custom lint rule or an assertion test |
| One task runner | package scripts | `just`, with tool versions pinned by a version manager |
| Hooks that call the task runner | a hook manager with an install lifecycle step | `core.hooksPath` set by the install task, plus a verifier |
| Dependency updates with a cooldown | Dependabot, npm ecosystem | Dependabot, Swift ecosystem |
| Template identity pinned | a placeholders test | a bootstrap script plus a smoke job that runs it |

The interesting row is import boundaries: no established equivalent, which makes it the
worked example for the previous section rather than a copy job.
