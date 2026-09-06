<!-- platform-annex -->
# Platform notes（このスキル自身の Codex での制約・best-effort 劣化）

## Codex での制約（best-effort 劣化）
- Phase 0・Phase 2 の選択肢提示: `AskUserQuestion` → 通常の文章で同じ質問・選択肢を提示して回答を待つ形に劣化。バッチ化・具体的選択肢・トレードオフ提示・推奨明示の原則は両対応で不変。
- 進捗追跡: `TodoWrite` → 作業メモ内のチェックリストで代替。
- 後続スキル参照: Claude Code は `Skill` ツールで `designing-wireframes` / `planning-tickets` を起動、Codex は `~/.codex/skills/` の bridge 経由で同名スキルを起動（両スキルとも両対応化・bridge 済み）。
- `templates/requirements-section.md` はスキル相対リンクで両対応（変更なし）。
