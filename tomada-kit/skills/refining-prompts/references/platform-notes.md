<!-- platform-annex -->
# Platform notes（このスキル自身の Codex での制約・best-effort 劣化）

## ツール対応

- 当たり付けの調査の委譲 → Claude Code: `Task`（`subagent_type: general-purpose`、`model: sonnet`
  — 定型的な情報収集のため。読み取りだけで足りるなら `Explore`。根拠は `orchestrating-models` §2
  だが、これは Claude Code 専用の参照であり Codex 版は存在しない）を起動 / Codex: `Task` に相当する
  委譲手段がないため、メインセッションが同じ調査を逐次インラインで行う
- ヒアリングでの選択肢確認 → Claude Code: `AskUserQuestion` / Codex: 通常の文章でユーザーに質問し、
  回答を待つ（確認する内容・意図は同じ）
- 出力する引き渡しプロンプト内の「不明時は確認して」という一文 → 受け手のプラットフォームが
  分かっている場合は「Claude Code なら AskUserQuestion、それ以外では通常の質問で」と書き分けても
  よいが、分からない場合はツール名を固定せず「確認して」とだけ書く

## Codex での制約（best-effort 劣化）

- 当たり付けの調査の委譲 → Codex では逐次インライン実行になり、サブエージェントによる
  コンテキスト分離が失われる（調査結果そのものの質は変わらない）
