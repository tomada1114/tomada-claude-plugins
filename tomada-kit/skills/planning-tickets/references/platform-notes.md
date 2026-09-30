<!-- platform-annex -->
# Platform notes

## Tool mapping

- Plan approval before any remote write (section 2) → Claude Code: `AskUserQuestion` (≤4 questions per call) / Codex: `request_user_input` where the session exposes it; otherwise one plain-text message in the format of `../ui-ux-designing/references/questions-core.md` § Presenting as plain text (`N. label — description`, `(Recommended: N)`), then wait. Options: approve / revise; wait for an explicit
  yes. On both hosts the host's own command approval for `gh` is an additional gate,
  not a substitute for the user's yes.
- The repository's issue skills (`triaging-issues`, `shipping-issues`) → they live in
  `.claude/skills/` (read by Claude Code) or `.agents/skills/` (read by Codex); read the
  files from either directory regardless of which host is running.
- Issue drafts' scratch directory (reference.md, two-pass creation) → the caller's
  state directory when one is passed; otherwise Claude Code: the session scratchpad
  when one is listed / Codex: `${TMPDIR:-/tmp}/agent-skills/planning-tickets/`. Never
  the repository.
- Issue creation, backfill, native links → the `gh` CLI on both hosts; no host-specific
  tool.

## Codex constraints (best-effort degradation)

These are degradation paths for runtimes that do not expose the capability, not a
product feature list.

- Network access in the sandbox → `gh issue create`, `gh issue edit`, and `gh api` need
  network, which a workspace-write sandbox may block (connection errors). Degrades to
  rerunning the same command through the host's approved escalation path. Do not work
  around it (no manual creation in the web UI outside the recorded mapping). Cost: time
  (an approval per command or per session), and a run that stops mid-sequence: before
  retrying a failed `gh issue create`, check `gh issue list` for the title so the
  retry does not create a duplicate, and keep the provisional → real number mapping
  so backfill resumes where it stopped.
- `gh` config and cache writes → `gh` may fail with `Operation not permitted` writing
  under the user's home (`~/.config/gh`, `~/.cache`). Rerun that command through the
  approved escalation path. Cost: time only; nothing is skipped.
- Structured option prompt → unavailable when the runtime exposes no user-input tool;
  degrades to a plain-message approval. Cost: the yes arrives as free text, so treat
  anything short of an explicit approval as "revise"; the guarantee (no remote write
  without consent) is unchanged.
