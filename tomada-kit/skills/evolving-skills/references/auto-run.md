# Unattended runs from the session-end hook

`scripts/auto_run.py` lets the loop run without anyone calling it. A `SessionEnd`
command hook runs `auto_run.py hook` when any Claude Code session ends. The hook makes
no model call: it reads the transcript, decides, and at most starts one detached
background process.

## What starts, and on which tier

| Pass | Starts when | Runs as | Tier (agent) |
|---|---|---|---|
| harvest | The session used a skill from the personal skills folder or the project's, and the person wrote at least `min_followups` messages after it | `claude -p "/evolving-skills harvest <digest>"` | `scout` |
| improve | The ledger has a promotable group | `claude -p "/evolving-skills improve"` | `executor` |

Harvest reads a small digest, not the transcript, and only records; it is
classification work, so it runs on the cheapest tier. Improve edits against a fixed
protocol with a mechanical pass or fail, which is the `executor` tier's kind of work.
Nothing in this loop runs on `architect`: a group the `executor` run cannot get
through the gate in two attempts is marked `rejected` and waits for a person. The
tiers are set by agent name in `assets/auto-config.json`; which model and effort a
name means is defined by the agent definitions (see the `orchestrating-models` skill).
The eval judge inside the gate uses the eval command's default small model.

Most session ends cost nothing. Limits on the rest, all in `assets/auto-config.json`:

| Setting | Default | Effect |
|---|---|---|
| `min_followups` | 2 | Sessions with fewer messages after the skill use are not harvested |
| `harvest.daily_cap` / `improve.daily_cap` | 6 / 2 | Launches per day |
| `harvest.max_budget_usd` / `improve.max_budget_usd` | 0.5 / 5 | Spend ceiling per launch, passed to `claude -p` |
| `lock_stale_minutes` | 120 | One run at a time; an older lock is treated as dead |

The gate's eval runs are separate processes with their own ceiling
(`gate.py check --max-cost-usd`).

## Setup

`auto_run.py settings-snippet` prints the `SessionEnd` entry to merge into `hooks` in
the user settings file. The hook is registered there, not in this skill's
frontmatter: a frontmatter hook only exists in sessions that invoked this skill, and
its command does not expand `${CLAUDE_SKILL_DIR}`.

The headless runs get the tools listed in the config plus this skill's own scripts.
They commit through `gate.py land` and never push.

## Watching it and switching it off

- `auto_run.py status`: enabled or not, today's counts, the lock, the last hook
  decisions.
- Logs: `<state>/auto/hook.log` (one line per session end and why it did or did not
  launch) and `<state>/auto/logs/` (one file per headless run), where `<state>` is
  `${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/evolving-skills`.
- `auto_run.py disable` stops all launches until `auto_run.py enable`. Setting
  `EVOLVING_SKILLS_AUTO=0` in the environment does the same for one shell.
- What it changed: `git log --grep 'Signals: SIG-'` in the repository that holds the
  skills, and `signals.py list --status applied --json`.

A headless run is itself a session that ends. The hook skips it
(`EVOLVING_SKILLS_CHILD=1`), so the loop cannot feed itself.
