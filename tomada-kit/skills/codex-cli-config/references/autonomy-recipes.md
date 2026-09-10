<!-- platform-annex -->

# Autonomy Recipes

Decision-first guide to how much you let Codex CLI run on its own. Each recipe
is a scenario, a copy-paste config, and a one-line rationale. For the raw
meaning of every key/flag, see the sibling references (this file composes
them, it doesn't re-derive them).

Every recipe below uses `sandbox_mode`/`approval_policy`, the simpler of the
two permission systems. If you need per-path or per-domain control instead of
a single workspace-wide boundary, the same postures are expressible as
`default_permissions` + `[permissions.<name>]` profiles — see
`references/permissions-and-sandbox.md` for the full key namespace and the "don't
combine both systems" rule.

## Recipe 1 — Everyday local coding ("Auto")

Scenario: you're at the keyboard, iterating on a trusted git repo, want Codex
to read/edit/run freely inside the workspace but check before touching
anything outside it or the network.

```bash
# CLI default — no flags needed in a trusted repo
codex
```

Equivalent explicit form:

```bash
codex --sandbox workspace-write --ask-for-approval on-request
```

Or in `~/.codex/config.toml` / `<repo>/.codex/config.toml`:

```toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"
```

Rationale: this is the documented **Auto** preset (`/permissions` → Auto) and
the default Codex assumes for a version-controlled folder — writes stay
inside the workspace, the model decides when something needs your sign-off.

## Recipe 2 — Hands-off local review / read-only exploration

Scenario: you want Codex to read, search, and explain a codebase — summarize,
answer questions, review a diff — without any chance of it writing a file or
running a mutating command, and without being interrupted for approvals it
would never need under a read-only sandbox.

```bash
codex --sandbox read-only --ask-for-approval never
```

Rationale: `read-only` blocks filesystem writes at the sandbox layer, so
`--ask-for-approval never` is safe here — there's nothing destructive left for
the model to attempt, only informational commands that fail closed if they'd
need more. (No finer-grained mapping from `/permissions` presets to exact
`sandbox_mode`/`approval_policy` pairs is published beyond Auto and Full
access — see `references/permissions-and-sandbox.md` — so use the explicit flags above
rather than assuming a preset name matches this recipe exactly.)

## Recipe 3 — Claude-Code-auto-mode equivalent (auto-review)

Scenario: you want the "just keep going, don't make me click Approve" feel of
Claude Code's auto/accept-edits mode, but still want the same guardrails that
on-request approval normally enforces.

```bash
codex --sandbox workspace-write --ask-for-approval on-request \
  -c approvals_reviewer=auto_review
```

Config file form:

```toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"
approvals_reviewer = "auto_review"
```

Non-interactive analogue (`codex exec`):

```bash
codex exec --approve-for-me "Implement the fix and run the test suite"
```

Rationale — read this carefully, it's the crux of the recipe: `approvals_reviewer`
does **not** change what's inside vs. outside the sandbox. The sandbox boundary
is identical to plain Recipe 1 — same `workspace-write`, same `on-request`
trigger conditions. What changes is *who* looks at an escalation once one is
triggered: instead of pausing for you, Codex routes it to the reviewer
subagent (`auto_review`), which approves or denies against `auto_review.policy`
in the background. This is the closest real analogue Codex has to Claude
Code's auto mode — it is not a looser sandbox, it's a delegated approver.
`--approve-for-me` is the `codex exec` shorthand for the same behavior in a
non-interactive/scripted invocation.

## Recipe 4 — Unattended CI / scheduled runs

Scenario: a GitHub Action, a cron job, a scheduled Codex Automation, or any
run where nobody is watching output in real time.

```bash
codex exec --sandbox workspace-write --ask-for-approval never "..."
# or, for a report/analysis run that shouldn't write anything:
codex exec --sandbox read-only --ask-for-approval never "..."
```

Config form for a dedicated profile (`~/.codex/ci.config.toml`):

```toml
sandbox_mode = "workspace-write"
approval_policy = "never"
```

Two things to get right:

- **Never use `danger-full-access` for an unattended run.** With
  `approval_policy = "never"` there is no human in the loop to catch a bad
  command, and a scheduled/CI run inherits whatever sandbox mode is
  configured — a scheduled Automation runs with exactly the sandbox the user
  last set, so widening it for one task widens it for every future run too.
  If a task genuinely needs network access or broader writes, prefer
  `sandbox_workspace_write.network_access = true` (or a scoped custom
  permission profile) over dropping to full access, and if `danger-full-access`
  is truly unavoidable, pair it with Rules that narrow the allowed commands
  rather than leaving it unconstrained.
- **Treat external input as untrusted once nothing is watching.** An
  Issue-triggered CI workflow, a scheduled "check Slack/GitHub and act" run,
  or any Automation that ingests text from outside the repo must not execute
  instructions embedded in that text (an Issue body, a PR comment, a fetched
  page) as if they were the operator's own request — prompt-injection hygiene
  matters exactly because there's no human reviewing each step before it runs.
- Before putting a task on a schedule, run it once by hand in an interactive
  session first. That's how you confirm the request is scoped the way you
  intend and that the resulting diff is something you'd actually approve,
  while you can still see it — a scheduled run gives you no such preview.

For the GitHub Actions path specifically (`openai/codex-action@v1`), use its
`permission-profile: ":read-only"` or `":workspace"` inputs and its
`safety-strategy` (default `drop-sudo`) rather than hand-rolling `-c` flags.

## Recipe 5 — Let git write without full access

Scenario: `workspace-write` still prompts on `git commit` because `.git` is
protected as read-only inside every writable root. Adding `--add-dir` doesn't
fix this — it only adds more writable roots, each with the same `.git`
protection. Widening all the way to `danger-full-access` *would* remove the
protection (it removes sandbox restrictions entirely), but that discards the
whole sandbox just to unblock one command family — overbroad for what a
single Rules entry solves precisely.

The fix is a Rules entry, not a sandbox change — see
`references/rules-execpolicy.md` for the full `prefix_rule()` reference and the headline
recipe in detail. Summary: an `allow` rule in `~/.codex/rules/default.rules`
(or `<repo>/.codex/rules/*.rules`) matching `git add` / `git commit` /
`git status` lets those specific commands run outside the sandbox without a
prompt, while leaving everything else — including `git push --force`,
`rm -rf`, `sudo` — governed normally (or explicitly `forbidden`).

## Preset comparison

| Preset | `sandbox_mode` | `approval_policy` | Use when | Avoid when |
|---|---|---|---|---|
| Auto | `workspace-write` | `on-request` | Everyday local coding — Codex's effective starting point for a trusted, version-controlled repo | The repo/folder isn't trusted yet, or you need zero writes |
| Read Only | `read-only` | `on-request` or `never` | Exploration, review, Q&A, CI reporting jobs that must not mutate anything | Any task that needs to edit files or run build/test commands |
| Auto-review | `workspace-write` | `on-request` + `approvals_reviewer=auto_review` | You want continuous, unattended-feeling progress but still want escalations judged against a policy, not silently allowed | You need a human, not a subagent, to see every escalation (compliance-sensitive changes, first run of a new task shape) |
| CI / unattended | `workspace-write` or `read-only` | `never` | Scheduled Automations, GitHub Actions, cron — nobody is watching in real time | Tasks touching untrusted external input without injection hygiene, or anything that "seems risky enough to want eyes on it" |
| Full access (YOLO) | `danger-full-access` | `never` (`--dangerously-bypass-approvals-and-sandbox` / `--yolo`) | Never as a default. Only inside an externally sandboxed environment (a disposable VM/container) where the sandbox's job is already done for you | Your own machine, any repo with credentials/secrets nearby, any unattended/scheduled run, any run touching untrusted input |

`--dangerously-bypass-approvals-and-sandbox` (alias `--yolo`) and
`danger-full-access` are last resorts, not defaults: they remove both the
sandbox and the approval gate simultaneously. The CLI's own help text frames
this as "intended solely for running in environments that are externally
sandboxed" — meaning the safety boundary has to already exist outside Codex
(container isolation, a throwaway VM) before this flag is a reasonable choice.
