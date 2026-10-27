# Maintenance

Tasks on a repository that already runs the Security Fixes workflow.

## A red run

Read the `Plan security fixes` step log; the script prints one report per failure.

| Code | Means | Next |
|---|---|---|
| `ERR_FIXES_UNRESOLVED` | A locked version still matches an alert after relocking | A dependent's range holds the package back: an `overrides` entry or a parent upgrade, the owner's call |
| `ERR_FIXES_LOCK` | `uv lock` or `pnpm update` failed | Usually the fix needs another package younger than the window; read the quoted output |
| `ERR_FIXES_EXPIRY` | Dropping an expired exception would move the lock or fail an install | Compare the entry with the release's upload/publish time |
| `ERR_FIXES_VERSION` | A version or range is not plain digits and dots | Fix that package by hand; the script does not guess an order |
| `ERR_FIXES_FILE` | The exception table or list is not in the editable shape | Restore the shape its comment describes |
| `ERR_FIXES_GH` / `_REGISTRY` / `_TOOL` | GitHub, PyPI, npm, or a tool unreachable | Rerun; if it persists, check the named permission |

- **`Open the pull request` fails at the token step:** environment variable/secret
  missing, App uninstalled, or the run was not on `main`.
- **A failure in one lockfile** still opens the other's PR; the body lists it under
  "Failed in this run", and `Result` turns the run red.

## Routine checks

- **Nothing has run for weeks:** GitHub disables scheduled workflows in a public
  repository after 60 days without activity. Actions → Security Fixes → Enable.
- **An exception lingers past its date:** the workflow is failing or its PR is still
  open (runs skip while one is open). Read the latest run; never remove the entry by
  hand while the guard would refuse it.
- **A bot PR is stale or wrong:** close it; the next run opens a fresh one from a new
  branch (`automation/security-fixes/<run id>`). Delete the old branch.
- **Alerts on another manifest** (a Docker image, `requirements.txt`, GitHub Actions)
  are listed under "Alerts not handled here"; handle them by hand.

## Credentials

- **Rotate the App key:** App settings → Private keys → Generate a new key; the owner
  replaces the environment secret, then deletes the old key in the App. Next dispatch
  proves it.
- **App permissions:** only Contents RW and Pull requests RW. A permission change makes
  GitHub ask the owner to accept it on the installation.
- **Never** move the key to a repository secret or widen the environment beyond `main`.

## Changing the design

- **Changing the window:** change `exclude-newer`, `minimumReleaseAge`, and every
  Dependabot cooldown together; the script reads the window from the files, so it
  follows. Shortening any of them is a gate weakening — the owner's decision.
- **Adding an ecosystem** (e.g. Cargo, Go): it needs an exception mechanism that can
  name one exact version and a lock check that proves removal is safe; without both,
  keep that ecosystem manual.
- **Bumping pinned actions** (`create-github-app-token`, setup actions): through the
  repository's Dependabot `github-actions` PRs; re-run zizmor.
- Keep the template in this skill's `assets/` in step with the source repository when
  the script or workflow changes there.
