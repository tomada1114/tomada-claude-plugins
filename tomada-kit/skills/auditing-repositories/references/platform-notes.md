<!-- platform-annex -->
# Platform notes

## Tool mapping

| Step | Claude Code | Codex |
|---|---|---|
| Survey and analysis delegation | Agent tool with `subagent_type: scout` (survey, template comparison) and `subagent_type: architect` (analysis, cross-lens design). Spawn a phase's agents in one message so they run in parallel. Never a bare `model`, which runs at the session's effort | Read `orchestrating-codex-models`. The survey maps to its light-execution tier, analysis and cross-lens design to its design tier. This skill authorizes read-only survey spawns and analysis spawns that write only to the run directory. Without a permitted sub-agent mechanism, run each brief inline, one lens at a time, in phase order |
| Issue-body drafting (more than ~6 bodies) | Agent tool with `subagent_type: worker` | Inline |
| Surveyor and analyst output | Sub-agents may not write report files: `scout` lacks Write, and the harness refuses report-file writes from any sub-agent. The main session saves each reply. A reply over the display limit arrives as a `persisted-output` path; `cp` that file to `survey-<lens>.md` / `analysis-<lens>.md` instead of retyping it. Then remove the `[harness: …]` banner and any preamble before the first `##` heading, and turn the neutralized `<\` back into `<`, so none of it leaks into issue bodies | The parent saves it |
| GitHub reads and writes (issue search, create, edit, labels, sub-issues, dependencies) | `gh` CLI (`gh issue list/create/edit`, `gh api`), as in `planning-tickets/reference.md` | Load `managing-git-github-workflows` first. Use the GitHub MCP integration for every remote operation; no `gh` and no direct HTTP. If MCP lacks an operation (for example native dependencies), keep the body lines, skip the native link, and say so in the report |
| Asking the user (only for an ambiguous target or a blocked step) | `AskUserQuestion` | `request_user_input` where exposed; otherwise one plain-text question, then wait |

## Codex constraints (best-effort degradation)

- **No parallel fan-out.** Lenses run sequentially in the main context. Phase order is
  unchanged; wall-clock time grows. Keep each lens's survey notes in the run directory
  before starting the next lens, so the context can be compacted between them.
- **No per-spawn effort.** When spawning is unavailable, analysis runs at the session's
  own effort. Say so in the report, so a shallow run is not mistaken for a clean bill
  of health.
- **Sandboxed network.** Cloning the template and every GitHub call may need the
  host's approved escalation path. Retry through it; do not skip the template trace
  silently.
