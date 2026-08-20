<!-- platform-annex -->
# Platform notes（このスキル自身の Codex での制約・best-effort 劣化）

## ツール対応
- Phase 0・Phase 2 の選択肢提示 → Claude Code: `AskUserQuestion` / Codex: 同じ質問・選択肢を通常の文章で提示して回答を待つ
- 進捗追跡 → Claude Code: `TodoWrite` / Codex: 作業メモ内のチェックリスト
- 後続スキル参照 → Claude Code: `Skill` ツールで `designing-wireframes` / `planning-tickets` を起動 / Codex: `~/.codex/skills/` の bridge 経由で同名スキルを起動（両スキルとも両対応化・bridge 済み）

## Codex での制約（best-effort 劣化）
- `AskUserQuestion` → 通常の文章で提示して回答を待つ形に劣化。バッチ化・具体的選択肢・トレードオフ提示・推奨明示の原則は両対応で不変。
- `TodoWrite` による進捗追跡 → 作業メモ内のチェックリストで代替。
- `templates/requirements-section.md` はスキル相対リンクで両対応（変更なし）。
