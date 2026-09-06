<!-- platform-annex -->
# Platform notes（このスキル自身の Codex での制約・best-effort 劣化）

- 調査委譲 → Claude Code: `Agent`（`Explore`、読み書きが要るなら `general-purpose` +
  `model: sonnet`）/ Codex: メインが逐次インライン（コンテキスト分離が失われるだけ）
- ヒアリングでの選択肢確認 → Claude Code: `AskUserQuestion` / Codex: 通常の文章で質問し、回答を待つ
- 引き渡しプロンプト内の「不明時は確認して」→ プラットフォームが分かっている場合は「Claude Code なら
  AskUserQuestion、それ以外では通常の質問で」と書き分けてもよい。分からない場合はツール名を固定せず
  「確認して」とだけ書く
