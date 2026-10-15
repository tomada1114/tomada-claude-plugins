# Finding the hosts a repository needs

The goal is a host list `scripts/check_allowlist.py` can test, so the answer to "does
this repository work in that environment" rests on evidence rather than on guessing
what Trusted covers.

## Method

1. **List the toolchain the repository pins**, from its files rather than its README:
   `.node-version` / `.nvmrc`, `package.json` (`engines`, `packageManager`,
   `devEngines`), `.python-version` and `requires-python`, `rust-toolchain.toml`,
   `go.mod`'s `go` / `toolchain` lines, `.tool-versions`, `mise.toml`, Dockerfiles and
   compose files, CI workflows (they show what a clean machine installs), and the
   SessionStart hook in `.claude/settings.json`.
2. **Compare each pin with the base image** (`platform-facts.md`, "The base image").
   A version the image lacks means a download at setup or install time.
3. **Find each download's real host from the tool's own source**, not memory. Fetch
   the exact version the lockfile pins and search it for the URL constant, for example:
   ```bash
   npm pack <package>@<version> --silent && tar -xzf <package>-<version>.tgz
   grep -rhoE "https://[a-z0-9.-]+" package/ | sort -u
   ```
   For a CLI installer, read its install script; for a Python build backend, its
   download URL template. Note the version and date beside each host.
4. **Run the checker** with every host found, plus the Custom domains the target
   environment already has:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/check_allowlist.py <host> ... [--extra <domain> ...] [--no-defaults]
   ```
   `MISSING` hosts are what a Custom allowed-domains list must add.
5. **Say what stays unverified.** A host allowed is not a download proven; the first
   real session settles it. Record the hosts and the check date in the reply.

## Verified hosts

"Tool → host" says where a tool downloads from, confirmed in its own source; "In
Trusted" is the checker's answer against the docs allowlist. A need missing from this
table is not known — verify it with the method above before relying on it.

| Need | Host(s) | Tool → host (source, date) | In Trusted (2026-10-13) |
|---|---|---|---|
| Playwright browser downloads (`playwright install`) | `cdn.playwright.dev`, `playwright.download.prss.microsoft.com` | `playwright-core@1.63.0` `PLAYWRIGHT_CDN_MIRRORS`, 2026-10-13 | No — add both on Custom |
| Node.js runtime fetched by pnpm (`devEngines.runtime`, `pnpm env use`) | `nodejs.org` | `pnpm@11.18.0` `DEFAULT_NODE_MIRROR_BASE_URL`, 2026-10-13 | Yes |
| The same, from pnpm's unofficial-builds mirror | `unofficial-builds.nodejs.org` | `pnpm@11.18.0` `UNOFFICIAL_NODE_MIRROR_BASE_URL`, 2026-10-13; when pnpm picks it over the default is UNCHECKED | No |
| npm packages; pnpm fetching the version `packageManager` pins | `registry.npmjs.org` | npm and pnpm default registry | Yes |
| PyPI packages | `pypi.org`, `files.pythonhosted.org` | pip and uv default index | Yes |

`microsoft.com` in Trusted is an exact entry; it does not cover
`playwright.download.prss.microsoft.com`.
