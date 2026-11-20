---
name: configuring-cloud-environments
description: Inspect, create, and edit Claude Code cloud environments (the Name, Network access, Allowed domains, Setup script, and Environment variables behind claude.ai/code's environment selector) and decide what a repository needs from one — which hosts its toolchain downloads from and whether the Trusted allowlist covers them (bundled checker script), whether an existing environment fits or a new one is warranted, and what belongs in the environment's setup script versus the repository's SessionStart hook. Use when asked to look at, create, edit, or tune a cloud environment or its setup script, to add allowed domains, to judge whether a repository or an upcoming issue will work in a cloud session, to place a cloud install step, or to diagnose a cloud session that fails to start ("Setup script failed with exit code -1"). Ends every change with a minimal smoke-test session in the environment.
metadata:
  platforms: claude-code
---

# Configuring cloud environments

A cloud environment's settings live only in the claude.ai/code environment selector —
no file, API, or CLI shows or changes them (`/remote-env` only picks the CLI default;
docs and the desktop app's tools rechecked 2026-11-18). One read needs no browser: in
the Claude desktop app, `mcp__ccd_session__list_start_targets` lists every cloud
environment's name, id and which one is the default. Use it to see whether an
environment exists before opening the browser; its list can lag a just-created
environment, so confirm a creation in the dialog, not there.
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

Run independent installs in parallel when the total nears the limit, and wait for them
by PID (`a & pa=$!; b & pb=$!; wait "$pa" "$pb"`), never with a bare `wait`. Pin
versions the repository pins, and keep each pin next to a comment naming the file it
must match.

The script must also end. A script that hangs is killed and the session fails to start
with "Setup script failed with exit code -1", and no output is shown. Guard against
that:

- Bound every network step: `curl --connect-timeout 10 --max-time <s>`, and wrap
  installers and other commands that can block in `timeout <s>`.
- Log with a plain redirect, `exec >>/var/log/<name>.log 2>&1`, not
  `exec > >(tee -a …)`. A process substitution is one more child that a bare `wait`
  or the runner can end up waiting on.

## Diagnosing a failed session start

"Setup script failed with exit code -1" means the script did not exit on its own.
Usually it hung until it was killed. It does not mean a command returned an error,
which gives a positive code. So look for what can block forever, not for what can fail:
an unbounded download, an installer waiting for input, a bare `wait`, or a
`> >(tee …)` redirect. Read the script (see "Inspecting an environment"). Check its
hosts with the allowlist checker and its checksum pins against upstream. Then apply the
guards above to every candidate at once: there is no log from the failed run to tell
which one fired. Treat the cause as inferred until the smoke test below passes.

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
3. Fill the dialog, then submit with **Add environment** or **Save changes**. The
   dialog pre-fills **Repositories** with the current repository; set it to the
   repositories the environment is for. Load a long setup script by saving it to a
   file and uploading that to the Setup script's file input (the **Choose file**
   button's input), not by typing it: the upload is exact.
4. Reopen the environment's settings, confirm each saved value against the draft, and
   close with **Cancel**. Compare the setup script by length and a hash computed the
   same way on both sides (in the page, from the editor's state; locally, from the
   file), not by eye. The Chrome extension may block a script's text or a hash from
   being returned (`[BLOCKED: …]`). Then compare the line count, the character count,
   and whether a few distinctive lines are present (`includes()` → true or false). Say
   that this check is weaker than a hash. Never re-encode the text to get it past the
   block.
5. Report what was saved and when it takes effect (platform-facts.md, "Caching and when
   changes take effect").
6. Run a smoke test before calling the environment done: one minimal session in it.
   Ask the user first, since it starts a cloud session on their account.
   - Start it from the desktop app with `start_session` (`target: "cloud"`,
     `environment: "<name>"`). Give it a read-only brief: change no files, commit and
     push nothing. It should print the setup script's log, then `command -v` and
     `--version` for each tool the script installs. Add one download from each newly
     allowed host. It answers whether the log reached its last line, which `WARN`
     lines appeared, and whether each tool is the expected version.
   - The first session reruns the setup script, so it takes a few minutes to start.
   - A cloud session sends no note back when it finishes. Read its answer on its
     claude.ai/code page (`get_page_text`). A start that still fails shows the error on
     that page.
   - Report the result. Treat a version that differs because the base image already
     had the tool as expected, not as a failure. Then the user archives the session.

Archive an environment only when the user asks for that environment by name; it cannot
be deleted or picked for new sessions afterward.
