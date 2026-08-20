<!-- platform-annex -->
# Platform notes（このスキル自身の Codex での制約・best-effort 劣化）

## ツール対応
- P1 の分析 → Claude Code: `Task`（`subagent_type: Explore`）で skill-analyzer.md を起動 / Codex: メインが同ファイルを skill 相対で読み逐次インライン実行
- P2 の変換（rewriter・extractor の並列起動）→ Claude Code: `Task`（`subagent_type: general-purpose`）で並列起動 / Codex: メインが rewriter→extractor の順に逐次インライン実行
- P3 の敵対的検証 → Claude Code: `Task`（`subagent_type: Explore`）で bridge-verifier.md を起動 / Codex: メインが同観点で自己レビュー

## Codex での制約（best-effort 劣化）
- 並列 `Task` → Codex では逐次インライン実行（所要時間増）。
- 敵対的検証サブエージェント → Codex ではメインの自己レビュー。
- `AskUserQuestion` 相当 → 通常対話で確認。
