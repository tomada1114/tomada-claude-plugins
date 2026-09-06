<!-- platform-annex -->
# Codex での制約（best-effort 劣化）

This skill is platform-neutral: it produces ASCII wireframes, flow diagrams, and Markdown spec sections with no Claude-only constructs (`Task`, `AskUserQuestion`, MCP tools, or hardcoded `.claude/` paths). The single template (`templates/wireframe-patterns.md`) is referenced by a skill-relative link, so it resolves identically on both platforms (on Codex via the `~/.codex/skills/` symlink). The `refining-requirements` / `planning-tickets` handoffs are dual-platform and resolve by name on each host. **No functional degradation on Codex.**

The "user decisions from `refining-requirements`" used in Step 3 are the requirements-document output, not a filesystem path, so they carry over unchanged.
