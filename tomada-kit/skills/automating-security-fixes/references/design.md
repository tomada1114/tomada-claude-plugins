# Design: why each piece is shaped this way

The decisions behind the template in `assets/`, the facts they rest on, and the traps
each one closes. Read before changing the workflow or the script, in any repository.

## Contents

- [The problem](#the-problem)
- [Decisions](#decisions)
- [Verified facts](#verified-facts)
- [Traps already hit](#traps-already-hit)

## The problem

A repository that refuses releases younger than N days (`[tool.uv] exclude-newer =
"7 days"`, pnpm `minimumReleaseAge`, Dependabot `cooldown` equal to it) blocks
supply-chain attacks, but also blocks fresh security fixes. Dependabot security updates
skip the cooldown, not the window, so their job fails and no PR opens. The alert stays
open until a person notices, decides on a one-package exception, and later remembers
to remove it.

## Decisions

| Decision | Why | Rejected alternative |
|---|---|---|
| Keep the window; never shorten it or add a blanket exception | The window is the supply-chain gate | A shorter global window loosens every package |
| Exempt only the advisory's **first patched version** | The advisory is the trust signal for that exact release | The latest release: unreviewed by the advisory |
| uv exception = absolute cutoff one second after the fix's **last file upload** | uv admits files uploaded before the cutoff; the fix locks, nothing later does | `uv lock -P pkg==ver` (see traps) |
| pnpm exception = exact `"name@version"` in `minimumReleaseAgeExclude` | pnpm accepts exact versions since 10.19.0 | A name or pattern exempts every future release |
| Fix already older than the window: plain `uv lock --upgrade-package` / `pnpm update --recursive --lockfile-only --no-save` | No exception needed; the window still bounds the pick, so it may lock a newer release | Pinning the advisory version |
| Drop an exception on the first run after `cutoff + window`, **only if the lock does not move** | Early removal downgrades to a vulnerable version | Calendar-only removal |
| One PR per run, skip while an `automation/security-fixes/*` PR is open | Two PRs always conflict in the lockfile | One PR per package |
| A failure in one lockfile restores it and still proposes the other's change; the run still ends red | One stuck package must not block every other fix indefinitely | Fail the whole run |
| Read alerts with `GITHUB_TOKEN`; write with a **GitHub App** installation token | A `GITHUB_TOKEN` PR starts no workflow, so required checks never report | Fine-grained PAT: expires, PR authored as the owner |
| Two jobs: `plan` (read-only, runs `uv lock`) and `open-pr` (no project code, App token) | `uv lock` may build sdists; the write token never shares that runner | One job that mints the token late |
| `open-pr` refuses a diff touching anything but the four policy/lock files | The plan job's output is untrusted input to the privileged job | Applying the diff blindly |
| App key in an **environment** limited to `main` | Only workflows on `main` can read it (zizmor `secrets-outside-env`) | Repository secret |
| Never merges; no auto-merge | The owner judges each lock change | Auto-merge on green |
| Failure signal = red scheduled run (GitHub emails whoever last changed the cron line) | No Issue noise | Opening Issues |

## Verified facts

Each was checked against a primary source on 2026-10-25; recheck when it matters.

- `GITHUB_TOKEN` reads Dependabot alerts with `permissions: vulnerability-alerts: read`
  ("Only `read` and `none` are supported"). Source: github/docs
  `data/reusables/actions/github-token-scope-descriptions.md`, feature flag
  `vulnerability-alerts-permission` (fpt, ghec; not GHES yet). Live-confirmed in a run.
  `security-events` does **not** cover Dependabot alerts.
- "events triggered by the `GITHUB_TOKEN` ... will not create a new workflow run"
  (docs: trigger-a-workflow); `workflow_dispatch` and `repository_dispatch` are the
  exceptions. Use an App or PAT for the push and the PR.
- REST `GET /repos/{o}/{r}/dependabot/alerts` filters: `state`, `ecosystem` (`pip`,
  `npm`, ...), `manifest`, `per_page` ≤ 100; uv alerts report ecosystem `pip` and
  manifest `uv.lock`. `gh api --paginate ... --jq '.[]'` yields one JSON object per line.
- `actions/create-github-app-token` takes `client-id` (`app-id` is deprecated), a
  `private-key`, and `permission-<name>` inputs; outputs `token`, `app-slug`.
- pnpm `minimumReleaseAgeExclude`: names, patterns (10.17+), exact versions and `||`
  lists (10.19+); `minimumReleaseAgeExcludePrune` exists from 11.22. The lockfile does
  not record the exclusion list.
- `pnpm update --recursive --lockfile-only <pkg>` updates a transitive dependency
  within its dependents' ranges; `pnpm update pkg@ver` on an indirect dependency fails
  (`ERR_PNPM_UPDATE_VERSION_ON_INDIRECT_DEP`).
- A public repository's scheduled workflows are disabled after 60 days without
  repository activity (docs: events-that-trigger-workflows).
- `GET /repos/{o}/{r}/automated-security-fixes` shows whether Dependabot security updates
  are on; `GET .../vulnerability-alerts` returns 204 when alerts are on.

## Traps already hit

- **The relocked version had its own advisory.** The fix for `< 21.14.9` was outside
  the window, so `uv lock --upgrade-package virtualenv` took the newest admitted
  release, 21.14.11 — inside GHSA-cx6f-vjhg-g3cc (`>= 21.14.9, < 21.14.13`). No
  Dependabot alert named it (alerts track the version locked before), so the first bot
  PR failed the required Dependency Review and OSV-Scanner checks. Hence the Advisory
  Database recheck of every newly locked version, which raised the target to 21.14.13
  with an exception. `GET /advisories?ecosystem=pip&affects=a@1,b@2` takes
  comma-separated specs, any token reads it, and `first_patched_version` is a plain
  string there (an object in the Dependabot alerts API).
- **`uv lock -P pkg==version`** removed the package and moved httpx to a pre-release
  (uv 0.12.1). Never pin through `-P`; pin through the cutoff.
- **Dropping a uv exception early** re-resolved certifi from 2026.10.19 down to the
  vulnerable 2026.10.18. Hence the "lock must not move" guard.
- **pnpm removal check**: with `minimumReleaseAgeStrict: true`, a dropped exclusion
  makes `pnpm install --frozen-lockfile --lockfile-only` fail with
  `ERR_PNPM_MINIMUM_RELEASE_AGE_VIOLATION` until the window admits the version — use
  that as the guard.
- **typos** flags some package names (`certifi` → `certify`) inside `pyproject.toml`,
  so a bot PR fails Spell Check. Narrow `extend-ignore-re` for the two generated line
  shapes only; keep package names out of generated comments.
- **`verifyDepsBeforeRun: error`** refuses `pnpm exec` after `minimumReleaseAgeExclude`
  changes ("The value of the minimumReleaseAgeExclude setting has changed"): reinstall
  locally after pulling such a change; CI installs fresh and is unaffected.
- **A repository test asserting the exception lists are empty** fails every bot PR
  that adds one. Assert they parse, not that they are empty.
- **`gh api --paginate` without `--jq '.[]'`** concatenates pages; a jq object filter
  on an array fails with "expected an object but got: array".
- **A collapsed GitHub settings section** swallows ref clicks silently; expand it and
  verify the selection on screen.
- **Dependabot security updates on** would duplicate fixes already outside the window:
  keep them off where this automation runs.
