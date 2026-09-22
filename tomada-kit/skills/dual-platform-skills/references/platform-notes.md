<!-- platform-annex -->
# Platform notes（このスキル自身の Codex での制約・best-effort 劣化）

## ツール対応
- サブエージェントの起動 → Claude Code: `Agent` に `references/agents/<role>.md` の本文（`{{…}}` を実値で埋めたもの）を渡す。`subagent_type` は tier で選ぶ（`orchestrating-models` スキル）: skill-analyzer・bridge-verifier = `architect`（深読み・判断・レビュー）、skill-rewriter・subagent-extractor = `executor`（確定プランの適用）。この 2 つが定義されていない環境では `general-purpose` で代替 / Codex: メインが同ファイルを skill 相対で読み逐次インライン実行
- P2 の並列起動 → Claude Code: rewriter と extractor を 1 メッセージで並列起動 / Codex: rewriter→extractor の順に逐次
- 読取専用の役割（analyzer・verifier）は、プロンプト内の「ファイルは編集しない」で縛る（tier の agent は書込ツールを持つため）

## Codex での制約（best-effort 劣化）
これは委譲能力が公開されていないランタイムでの劣化パスであって、製品の機能一覧ではない。
- 並列委譲 → 逐次インライン実行（所要時間増＋コンテキスト隔離の喪失: analyzer の深読みがメインに積み上がる）。
- 敵対的検証サブエージェント → メインの自己レビュー（独立した読み手という保証を失う。P4 レポートに明記）。
- 選択肢提示 → 通常対話で確認。
