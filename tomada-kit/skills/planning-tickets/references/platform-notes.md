<!-- platform-annex -->
# Platform notes

## ツール対応

本スキルは `gh`/`git` CLI とスキル相対参照（`templates/`, `reference.md`）のみで構成され、Claude 専用のツール機構（並列 `Task`、`AskUserQuestion`、MCP 等）を一切使用しない。したがって Claude → Codex のツール対応表は不要——両プラットフォームで同一のコマンドがそのまま動く。On Codex the skill folder is reached via a symlink in `~/.codex/skills/` (Topology A); the real folder stays under the skill's own directory.

## Codex での制約（best-effort 劣化）

なし。本スキルは `gh`/`git` CLI とスキル相対参照のみで構成され、Claude 専用機構（並列 `Task`、`AskUserQuestion`、MCP、ハードコード絶対パス）を使用しないため、Codex 上でも劣化なく同一に動作する。
