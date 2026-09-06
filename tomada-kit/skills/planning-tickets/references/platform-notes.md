<!-- platform-annex -->
# Platform notes

## Codex での制約

本スキルは `gh`/`git` CLI とスキル相対参照のみで構成され、Claude 専用機構(並列 `Task`、`AskUserQuestion`、MCP)を使用しないため、Codex 上でも劣化なく同一に動作する。On Codex the skill folder is reached via a symlink in `~/.codex/skills/` (Topology A); the real folder stays under the skill's own directory.
