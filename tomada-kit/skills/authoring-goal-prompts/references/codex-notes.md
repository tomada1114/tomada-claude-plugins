# Codex での制約（best-effort 劣化）

- 並列 `Task`（Phase 1 の `Explore` fan-out）→ Codex ではメインが逐次実行（所要時間増、結果は同じ）。
- `AskUserQuestion`（Phase 4）→ Codex では通常の文章でユーザーに質問し回答を待つ。確認する軸（done-state / scope / verify / stop ceiling / design fork）は不変。
- `/goal` コマンドと出力先 `~/.claude/goal-prompts/<slug>/` は **Claude Code 固有の慣習**。本スキルの成果物（goal プロンプト本文＋サポートファイル）の作成手順は両プラットフォームで同一だが、Codex には `/goal` が無いため「貼り付け先」は対象ホストに合わせて読み替える（バンドル時の `~/.claude/goal-prompts/` 配置と `/goal` 起動は Claude Code 前提）。≤4000 文字の上限と `wc -m` 計測は両対応で有効。
