---
name: configuring-cloud-environments
description: Inspect, create, and edit Claude Code cloud environments (the Name, Network access, Allowed domains, Setup script, and Environment variables behind claude.ai/code's environment selector) and decide what a repository needs from one — which hosts its toolchain downloads from and whether the Trusted allowlist covers them (bundled checker script), whether an existing environment fits or a new one is warranted, and what belongs in the environment's setup script versus the repository's SessionStart hook. Use when asked to look at, create, edit, or tune a cloud environment or its setup script, to add allowed domains, to judge whether a repository or an upcoming issue will work in a cloud session, or to place a cloud install step.
metadata:
  platforms: claude-code
---

# Configuring cloud environments

A cloud environment's settings live only in the claude.ai/code environment selector —
no file, API, or CLI shows or changes them (`/remote-env` only picks the CLI default).
Without this skill an agent guesses at what an environment contains, assumes Trusted
covers a tool's downloads, or puts a VM install in the wrong layer. This skill reads the
real settings through the browser, checks hosts against the live allowlist, and changes
an environment only after the user approves the exact values.

Facts about every field, caching, and the base image: [references/platform-facts.md](references/platform-facts.md).

## Before touching the browser

Load the `operating-chrome` skill and read its `references/site-claude.md`. It owns how
the selector and the environment dialog react to clicks (hover-only submenus, which
button reference misfires, which field reads back its placeholder). This skill owns
what to set and why.

## Inspecting an environment

1. In your own tab at `https://claude.ai/code`, open the environment selector → **Cloud**
   → the settings button beside the environment.
2. Read every field: Name, Network access, Allowed domains and the "Also include default
   list" checkbox (Custom only), Network secrets (names only), Setup script, Environment
   variables. Scroll the dialog; read the setup script from a screenshot.
3. Close with **Cancel**, never **Save changes**, and close the tab.
4. Report the fields as a table, the setup script verbatim, and what the environment
   does *not* configure.

## Judging whether a repository fits

1. If the repository is local, read its `AGENTS.md` / `CLAUDE.md` and
   `.claude/settings.json` first — they may fix what the SessionStart hook may run.
2. Derive the hosts its toolchain needs with [references/finding-hosts.md](references/finding-hosts.md),
   including the work ahead (open issues that add a tool), not only today's tree.
3. Check them against the environment's access level:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/check_allowlist.py <host> ... [--extra <domain> ...] [--no-defaults]
   ```
   Trusted → hosts only. Custom → add each allowed domain as `--extra`, and
   `--no-defaults` when the default-list checkbox is off. Exit 1 lists the `MISSING`
   hosts; exit 2 means the docs page could not be read (rerun with `--docs-file`).
4. Compare the setup script with what the toolchain needs beyond the base image.
5. Answer per need (or per issue): covered, covered by an edit, or needs a new
   environment — and what stays unverified until a real session runs.

**Edit or create.** Edit an environment when it serves only this repository. Create a
new one when the existing environment serves other repositories: a saved change to its
setup script or allowed hosts rebuilds the cache for every one of them, and widening
its network access widens it for all.

## Writing a setup script

Provision the VM here — runtimes the image lacks, CLIs, OS packages, Docker images —
and leave project installs (`npm install`, `uv sync`, git hooks) to a SessionStart
hook. The script must exit 0 and finish in about five minutes to be cached:

```bash
#!/bin/bash
set -uo pipefail
apt-get update -q && apt-get install -y -q <pkg> || echo "WARN: <pkg> install failed"
<toolchain install> || echo "WARN: <toolchain> install failed"
```

Run independent installs in parallel (`&` then `wait`) when the total nears the limit.
Pin versions the repository pins, and keep each pin next to a comment naming the file
it must match.

## Placing a step: setup script or SessionStart hook

Use the table in [platform-facts.md](references/platform-facts.md#setup-script-or-sessionstart-hook).
A repository change (a hook, a cloud-only guard, a script it calls) is proposed as a
diff in the reply, never committed by this skill — the repository's own rules and
review decide it.

## Creating or editing an environment

1. Draft every field. For Custom access, list only the hosts the checker reported
   `MISSING`, and keep the default-list checkbox on unless the user wants a narrow list.
2. Show the exact values (name, access level, each allowed domain, the full setup
   script, each variable name) and ask for a yes before submitting. Creating, saving,
   and archiving change the user's account settings. Never put a secret in Environment
   variables; point to Network secrets instead.
3. Fill the dialog, then submit with **Add environment** or **Save changes**.
4. Reopen the environment's settings, confirm each saved value against the draft, and
   close with **Cancel**.
5. Report what was saved and when it takes effect (platform-facts.md, "Caching and when
   changes take effect"), and what the first session should confirm — for example the
   setup script's tools on `PATH` and a download from each newly allowed host.

Archive an environment only when the user asks for that environment by name; it cannot
be deleted or picked for new sessions afterward.
