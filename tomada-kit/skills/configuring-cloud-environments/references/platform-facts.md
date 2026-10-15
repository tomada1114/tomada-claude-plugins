# Cloud environment facts

What the environment dialog holds and how each field behaves. Source:
[Configure cloud environments](https://code.claude.com/docs/en/cloud-environments),
checked 2026-10-13. When a fact here decides a recommendation, re-read that section
of the page first — the product changes, and the page wins over this file.

## Contents

- [Where environments live](#where-environments-live)
- [Dialog fields](#dialog-fields)
- [Network access](#network-access)
- [Setup script](#setup-script)
- [Caching and when changes take effect](#caching-and-when-changes-take-effect)
- [Setup script or SessionStart hook](#setup-script-or-sessionstart-hook)
- [The base image](#the-base-image)

## Where environments live

- Only in the environment selector at claude.ai/code (or the Desktop app's prompt
  box). There is no settings page, URL, API, or CLI that creates or edits one;
  `/remote-env` only picks the default environment for CLI-started cloud sessions.
- Environments a user creates are personal to their account and apply on every
  surface that starts a cloud session (web, Desktop, mobile, `claude --cloud`,
  routines).
- An organization-shared environment opens read-only in the selector; an Owner edits
  it from the **Cloud environments** page in admin settings.
- An environment cannot be deleted, only archived. Archiving removes it from the
  selector and `/remote-env`, and no new session can start in it.

## Dialog fields

| Field | Behavior |
|---|---|
| Name | Free text shown in the selector. |
| Network access | None / Trusted (default) / Full / Custom. |
| Allowed domains | Custom only. One domain per line; a leading `*.` matches subdomains. A checkbox, "Also include default list of common package managers", adds the Trusted list. |
| Network secrets | Pro and Max only. A key the agent proxy attaches to requests for listed hosts; the value cannot be viewed after saving. |
| Setup script | Bash, run as root on Ubuntu 24.04 before Claude Code launches. |
| Environment variables | `.env` format. Readable by anyone who uses the environment, so never a secret. `OTEL_*` is not passed to commands. |

## Network access

- Trusted reaches package registries, GitHub, cloud SDKs, and the other entries
  under "Default allowed domains" — and nothing else through the session's network.
- Every level still reaches GitHub (separate proxy), enabled MCP connectors, the hosts
  of the environment's network secrets, and the Anthropic API.
- A tool's own download host (a browser build, a toolchain tarball, a model file) is
  often outside Trusted even when its package registry is inside. That is the usual
  reason a Custom environment is needed.

## Setup script

- **Exit zero.** A non-zero exit fails the session start. Keep the script resilient:
  `set -uo pipefail` without `-e`, and `|| echo "WARN: <step> failed"` on each
  non-critical step, so a flaky download degrades to a warning instead of a blocked
  session.
- **Finish within about five minutes**, or the environment is not cached. Run
  independent installs in parallel with `&` and `wait`; move one oversized download
  into a SessionStart hook that runs it in the background.
- **Root and apt work.** `apt update && apt install -y <pkg>` is fine.
- The script's output is not shown in the dialog. Confirm its effect from inside a
  session (for example `command -v <tool>`, `<tool> --version`).

## Caching and when changes take effect

| Change | Reaches |
|---|---|
| Network access level or allowed domains | Existing sessions within about a minute, for requests through the session's network allowlist. A changed allowed-hosts list also rebuilds the cache, so the next new session reruns the setup script. |
| Setup script | New sessions only, after the setup script reruns once to rebuild the cache (that first session pays the setup time); an existing session sees it only when its VM is reclaimed and rebuilt. |
| Environment variables | An existing session only when its VM is next restored after idling or rebuilt; new sessions immediately. |
| Nothing (about seven days pass) | The cache expires and the setup script reruns. |

The cache is a filesystem snapshot: installed packages, pulled Docker images, and
written files carry over; started databases and other processes do not. The setup
script does not rerun when an idle VM is restored.

## Setup script or SessionStart hook

| | Setup script | SessionStart hook |
|---|---|---|
| Configured in | The environment dialog (the user's account) | A settings file, usually the repository's `.claude/settings.json` |
| Runs | Before Claude Code launches; skipped when the cache exists | After launch, on every start and resume |
| Runs where | Cloud only | Local and cloud — guard with `[ "$CLAUDE_CODE_REMOTE" = true ] \|\| exit 0` |
| Suits | Provisioning the VM: toolchains, CLIs, OS packages, Docker images | Project setup: `npm install`, `uv sync`, git hooks |

- A session with several repositories loads no repository's hooks; only the setup
  script runs there.
- User-level hooks in `~/.claude/settings.json` never reach a cloud session.
- A `command` hook is cancelled after 600 seconds unless the entry sets `timeout`.
- Some package managers break behind the session's security proxy; the docs name Bun.

## The base image

Ubuntu 24.04 on x86_64, 4 vCPUs, 16 GB RAM, 30 GB disk. Pre-installed: Python 3.x with
pip, poetry, uv, ruff, mypy, pytest; Node.js 20, 21, and 22 at `/opt/node20`…`/opt/node22`
with 22 on `PATH`, plus npm, yarn, pnpm, bun; Ruby 3.1–3.3; PHP 8.3; OpenJDK 21; Go;
Rust; GCC and Clang; Docker with compose; PostgreSQL 16 and Redis 7.0 (installed, not
running — `service postgresql start`); git, gh, jq, yq, ripgrep. A session can print
most versions with the `check-tools` command. Anything else — another Node major, a
newer Python, a browser build — comes from the setup script or the project's own
tooling.
