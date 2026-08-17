# Codex での制約（best-effort 劣化・このスキル自身にも適用）

- 並列 `Task` → Codex では逐次インライン実行（所要時間増）。
- 敵対的検証サブエージェント → Codex ではメインの自己レビュー。
- `AskUserQuestion` 相当 → 通常対話で確認。
