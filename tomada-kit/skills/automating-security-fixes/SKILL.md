---
name: automating-security-fixes
description: >-
  Set up, port, or maintain a daily GitHub Actions workflow that turns open Dependabot
  alerts into one security-fix pull request in a repository that refuses releases
  younger than a supply-chain window (uv exclude-newer, pnpm minimumReleaseAge,
  Dependabot cooldowns). Only the advisory's first patched version may skip the window,
  through a one-package exception the workflow adds and later drops once the lock
  stays put; alerts are read with GITHUB_TOKEN (vulnerability-alerts: read) and the PR
  is opened with a GitHub App token held in a main-only environment. Bundles the
  stdlib script, its tests, and the workflow as a template. Use when bringing security
  fixes past a release-age window into a repository, porting the Security Fixes
  workflow to another repository, a Security Fixes run is red or its PR looks wrong,
  rotating its App key, or changing the window or exception rules.
metadata:
  platforms: claude-code, codex
---

# Automating Security Fixes

Without this, an agent re-derives the design and repeats known mistakes: it opens the
PR with `GITHUB_TOKEN` (required checks never start), pins through `uv lock -P
pkg==ver` (which moved unrelated packages), drops exceptions on the calendar (which
downgraded to a vulnerable release), or widens the window. This skill holds the
settled design, a working template, and the traps already hit.

## Contract

**Input:** a repository path or `owner/name`, and the task — port, maintain, or debug.

**Output:** a branch and PR in that repository (port or design change), or a diagnosis
and fix (maintenance). The owner does the credential and settings steps and merges.

## The invariants

Keep these in any repository, and question a request that would break one:

1. The window stays; no blanket exception, no shorter window.
2. Only the advisory's first patched version is exempted — uv as a cutoff one second
   after its last upload, pnpm as an exact `"name@version"`.
3. An exception is dropped only after `cutoff + window` and only if the lock does not
   move (`uv lock` keeps every version; `pnpm install --frozen-lockfile
   --lockfile-only` passes).
4. After relocking, every newly locked version is checked against the GitHub Advisory
   Database (`GET /advisories?affects=<name>@<version>`) — Dependabot alerts only
   describe the old versions — and a match raises the target and relocks; no locked
   version may then match any advisory's vulnerable range.
5. One PR per run; skip while one is open; never force-push; never merge.
6. Alerts are read with `GITHUB_TOKEN` (`vulnerability-alerts: read`); the push and PR
   use a GitHub App token, because a `GITHUB_TOKEN` PR starts no workflow.
7. The App key lives in an environment limited to the default branch; the job holding
   it runs no project code and accepts a diff touching only the policy and lock files.
8. A failure in one lockfile restores it and still proposes the other's change; the
   run ends red, and that red run is the notification.

Why each holds, the facts behind them with sources, and the traps:
[references/design.md](references/design.md).

## Porting to a new repository

1. Survey the target: its window, lockfiles, pnpm version, Dependabot settings, open
   alerts, and its own rules for scripts, workflows, gates, and approvals.
2. Confirm in one question round: App (recommended) or PAT, ecosystems in scope, one PR
   per run, and leaving today's open alerts to the first run.
3. Copy the template from `assets/` (`security_fixes.py` → `scripts/`,
   `test_security_fixes.py` → `tests/`, `security-fixes.yml` →
   `.github/workflows/`), adapt it, add the empty exception table and list, the typos
   ignore, and the doc changes.
4. Prove it: the full gate, an end-to-end run on a scratch copy against live alerts,
   and the bot's diff applied in a throwaway worktree against the real gates.
5. Open the PR with the owner-setup steps and the manual verification in its body.
6. Help with the owner setup only as far as the owner allows: never touch the private
   key; confirm before every submit.
7. After merge, on request: dispatch a dry run, then a real run.

Every step's details, including what to change in the template:
[references/porting.md](references/porting.md).

## Maintaining a running setup

Red runs and their error codes, a lingering exception, the 60-day schedule disable,
key rotation, changing the window, adding an ecosystem:
[references/maintenance.md](references/maintenance.md).

## The template

`assets/` holds the tomada1114/intent-to-english version as of 56efb72: PR #111 plus
the advisory recheck from PR #118. Its first clean bot PR was #119:

- `security_fixes.py` — stdlib-only planner: reads alerts through `gh`, PyPI and npm
  publish times through HTTPS, edits the exception table and list, relocks, and writes
  `title.txt` and `body.md`. Exit 1 on any recorded failure.
- `test_security_fixes.py` — pytest suite that fakes `gh`, `uv`, `pnpm`, and the
  registries.
- `security-fixes.yml` — `plan` → `open-pr` → `Result` jobs; daily cron,
  `workflow_dispatch` with `dry-run` (default on), and a dry run on PRs that change it.

When the source repository's copy is newer, port from it and refresh `assets/`.
