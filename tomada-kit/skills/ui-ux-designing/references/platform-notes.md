<!-- platform-annex -->
# Platform notes（このスキル自身の Codex での制約・best-effort 劣化）

## ツール対応

- 選択肢提示による確認（Phase 1・3・4）→ Claude Code: `AskUserQuestion` / Codex: 通常対話で同じ選択肢を提示して確認
- Phase 2 の競合/人気アプリ調査 → Claude Code: `WebSearch` / Codex: 同等の web 検索ツールがあれば使用
- 質問パターンの平文化 → `references/question-patterns.md` の「平文で提示する場合の例」を参照（JSON データを番号付き選択肢の文章に変換して提示する）

## Codex での制約（best-effort 劣化）

- `AskUserQuestion`（Phase 1・3・4 の各確認）→ Codex では通常対話で同じ選択肢を提示して確認する。「質問設計の原則」（選択肢2〜4個・トレードオフ説明・`（推奨）`明示・3-4個ずつバッチ化）はそのまま適用する。
- `WebSearch`（Phase 2）→ Codex では同等の web 検索ツールがあれば使用し、無ければユーザー提供の参考情報（アプリ名・URL・スクリーンショット）で調査する（調査観点・3アプリ以上の原則は維持）。

参照（`references/`・`templates/`）はすべてスキル相対パスなので、Claude Code でも Codex（`~/.codex/skills/` の symlink 経由）でも同一に解決する。
