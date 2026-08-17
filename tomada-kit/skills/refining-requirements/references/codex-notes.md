# Codex での制約（best-effort 劣化）

- `AskUserQuestion`（Phase 0・Phase 2）→ Codex では同じ質問・選択肢を通常の文章で提示して回答を待つ。バッチ化・具体的選択肢・トレードオフ提示・推奨明示の原則は両対応で不変。
- `TodoWrite` による進捗追跡 → Codex では作業メモ内のチェックリストで代替。
- 後続スキル `designing-wireframes` / `planning-tickets` は両対応化済み。名前参照で Claude Code（`Skill`）／Codex（`~/.codex/skills/` の bridge）の双方で解決する。`templates/requirements-section.md` はスキル相対リンクで両対応。
