# Porting to another repository

Bring the automation into a repository that does not have it yet. The template in
`assets/` is the tomada1114/intent-to-english version as of 56efb72; if that
repository is reachable, diff its `scripts/security_fixes.py` and
`.github/workflows/security-fixes.yml` against `assets/` first and port the newer one.

## Contents

- [1. Survey the target](#1-survey-the-target)
- [2. Adapt the template](#2-adapt-the-template)
- [3. Gates and docs](#3-gates-and-docs)
- [4. Prove it before the PR](#4-prove-it-before-the-pr)
- [5. Owner setup](#5-owner-setup)
- [6. After merge](#6-after-merge)

## 1. Survey the target

Read, do not assume:

- **Window:** `[tool.uv] exclude-newer` (a relative `"N days"` — an absolute date needs
  a different expiry rule) and/or `pnpm-workspace.yaml` `minimumReleaseAge` (minutes),
  plus `minimumReleaseAgeStrict`. No window → this automation is the wrong tool; plain
  Dependabot security updates suffice.
- **Lockfiles and manifests:** where `uv.lock` / `pnpm-lock.yaml` live, the workspace
  members (`backend/pyproject.toml`, `frontend/package.json`, ...), and the pnpm version
  (≥ 10.19.0 for exact-version exclusions). A Python-only or pnpm-only repository drops
  the other ecosystem.
- **Settings:** `gh api repos/{o}/{r}/automated-security-fixes` and
  `gh api -i repos/{o}/{r}/vulnerability-alerts` (204 = alerts on). Open alerts:
  `gh api --paginate 'repos/{o}/{r}/dependabot/alerts?state=open&per_page=100' --jq '.[] | [.dependency.package.ecosystem, .dependency.package.name, .dependency.manifest_path, .security_vulnerability.first_patched_version.identifier] | @tsv'`.
- **Repository rules:** its contribution guide and agent instructions (`AGENTS.md`,
  `CLAUDE.md`), how it writes scripts (stdlib only? error format?), workflow hygiene
  tests, typos/zizmor/pre-commit gates, required checks, whether new Actions or gate
  changes need the owner's sign-off. Follow them over this template.

Then confirm the design with the owner in one question round: App vs PAT (recommend
App), ecosystems in scope, PR shape (recommend one per run), and whether to fix the
currently open alerts in the same PR (recommend not: the first run is the acceptance
test).

## 2. Adapt the template

Copy `assets/security_fixes.py` → `scripts/`, `assets/test_security_fixes.py` →
`tests/`, `assets/security-fixes.yml` → `.github/workflows/`. Then change:

- **Script constants:** `MANIFESTS` (the manifest paths Dependabot reports per
  ecosystem), the file paths in `Context`, `BRANCH_PREFIX` if the repository already
  uses `automation/`. Remove an ecosystem by dropping it from `plan_run`'s loop and
  `MANIFESTS`.
- **Doc pointers:** the script, the workflow comments, and the generated PR body name
  `managing-dependencies` and `merging-dependency-prs` (skills of the source
  repository). Point them at the target's own dependency doc, or drop them.
- **Error codes / output style:** match the target's script conventions if they differ
  (the template prints `ERR_FIXES_<KIND>` / `Expected:` / `Next:` on stderr).
- **Workflow:** keep the three jobs; drop `pnpm/action-setup` + `setup-node` for a
  uv-only repo; copy the exact action SHAs the target already pins (checkout,
  setup-uv, setup-node) and pin `actions/create-github-app-token` by SHA to a release
  older than the target's Actions cooldown. Adjust the base branch if not `main`.
- **Policy files:** add an empty `[tool.uv.exclude-newer-package]` table right after
  `[tool.uv]`'s keys, and `minimumReleaseAgeExclude: []` to `pnpm-workspace.yaml`, each
  with a comment saying the workflow owns the entries. Check `uv lock --check` and
  `pnpm install --frozen-lockfile --lockfile-only` stay green.
- **Tests:** the template test loads the script by path and fakes `call` and
  `fetch_json`; keep its parse-only assertion on the committed files.

## 3. Gates and docs

- **typos:** add the two `extend-ignore-re` patterns (generated uv entry, generated pnpm
  item) to the target's typos config; it is a gate change — get the owner's yes and say
  in the PR what now passes.
- **zizmor / workflow lints:** run them; the App key must sit in an environment
  (`secrets-outside-env`). Run zizmor with `--persona=pedantic` too.
- **Dependabot comments and dependency docs:** rewrite the parts that say a fix inside
  the window is "handled by hand"; state that Dependabot security updates stay off.
- **pnpm repositories:** document that `verifyDepsBeforeRun` needs a reinstall after an
  exclusion change.

## 4. Prove it before the PR

1. Run the target's full gate.
2. **End to end against live alerts on a scratch copy** of the lockfiles and policy
   files (load the script, call `main([...], root=<scratch>)`): check the diff, rerun
   (expect no change), and run with `--now` past an entry's expiry to see the guard
   restore files.
3. **Simulate the bot's PR against the real gates:** in a throwaway worktree, apply the
   scratch run's diff and run the lock check, the root tests, typos on the policy
   files, and `pnpm install --frozen-lockfile --lockfile-only`. This is what caught the
   typos and empty-list-test traps.
4. The PR's own `Plan security fixes` dry run is the first live proof that
   `vulnerability-alerts: read` works there; read its step summary after CI.

## 5. Owner setup

Creating credentials and changing settings is the owner's; with a browser and their
go-ahead, an agent may fill forms and click submit after confirming each one, but
never handles the private key.

1. GitHub App (Settings → Developer settings → GitHub Apps → New): webhook **off**,
   repository permissions **Contents: Read and write**, **Pull requests: Read and
   write** (Metadata read-only is automatic), installable only on the owner's account.
   GitHub asks for sudo confirmation first. The repository-permissions list is
   collapsed: expand it before choosing, then verify on screen.
2. The owner generates the private key (`.pem` download).
3. Install the App → **Only select repositories** → the target only.
4. Environment `security-fixes` (repo Settings → Environments): deployment branches
   **Selected branches and tags** → rule `main`; variable
   `SECURITY_FIXES_APP_CLIENT_ID` = the App's Client ID.
5. The owner adds secret `SECURITY_FIXES_APP_PRIVATE_KEY` = the whole `.pem`
   (`pbcopy < file.pem`), then moves the `.pem` somewhere safe.
6. Verify by API (names only for secrets):
   `gh api repos/{o}/{r}/environments/security-fixes/variables`,
   `.../deployment-branch-policies`, `.../secrets`.

## 6. After merge

On the owner's request: `gh workflow run security-fixes.yml --ref main -f dry-run=true`,
read the plan output, then `-f dry-run=false` to open the first PR. The owner merges it.
