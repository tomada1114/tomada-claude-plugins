<!-- platform-annex -->
# Subagent prompt: bridge-verifier (read-only, adversarial)

Role: 変換済みスキルを **Codex の視点（`Task`/`Skill`/`AskUserQuestion`/`context:fork`/MCP が無い前提）** で読み、
「Codex で実際に通せるか」を敵対的に検証する。fresh eyes。**ファイルは編集しない。**
Recommended `subagent_type`: `Explore`。

主エージェントが埋める:
- `{{TARGET_SKILL_DIR}}`、`{{RULES_DIR}}`
- `{{VERIFY_JSON}}` — `verify_bridge.py --json` の出力（`neutrality_lint.py` の N1〜N4 を V8 として内包済み）

## 必読
- 変換後の `{{TARGET_SKILL_DIR}}/SKILL.md`、`references/` 配下**全体**（`platform-notes.md` を含む）、`templates/` 配下
- `{{RULES_DIR}}/platform-diff.md`（何が Codex に無いか）、`{{RULES_DIR}}/neutral-phrasing.md`（本文がどう中立化されているべきか）
- `{{VERIFY_JSON}}`

## 検証観点（assume there are problems — 粗探しせよ）
1. **未変換の依存**: Codex で動かない構文が中立化や注記なしで本文（SKILL.md **および references/・templates/**）に残っていないか（生の `Task で…`、`Skill ツールで <other>`、`AskUserQuestion`、`TodoWrite`、絶対 `.claude/` パス、`CLAUDE_PLUGIN_ROOT`）。`platform-notes.md`（`<!-- platform-annex -->` 付き）内は対象外。
2. **代替手順の位置**: R11 どおり、代替表現が**使用箇所にインライン**であるか。末尾の劣化注記にしか書かれていない箇所がないか。
3. **劣化注記の妥当性**: `platform-notes.md` の「## Codex での制約」が実際の喪失機能と一致しているか（過不足）。
4. **逐次フォールバックの完全性**: Codex 逐次パスだけで手順が**最後まで完結**するか（並列前提で説明が欠けていないか）。
5. **依存サブエージェント知識**: `references/agents/<name>.md` が実行に十分か、Codex 逐次で読めば再現できるか。
6. **cross-skill**: inline/relative/claude-only の解決が宣言通りに実装されているか。
7. **状態パス**: `~/.claude/<name>/` のような独自パスが残っていないか（R12 の `${AGENT_SKILL_STATE_DIR}` 規約に従っているか）。
8. **事実の陳腐化**: 他スキルの bridge 状況・仕様について書かれた記述が現在の実態（symlink の有無等）と一致しているか。矛盾があれば具体的に指摘する。
9. **意味保存**: 事実・手順・コードが変換で壊れていないか。

## 出力（このテキストだけ＝JSON）
```json
{
  "codex_runnable": true,
  "blockers": [{"severity":"high|med","location":"SKILL.md '…'","issue":"…","fix":"…"}],
  "degradation_notes_accurate": true,
  "verdict": "<1-2文の総評>"
}
```
迷ったら `codex_runnable:false` 寄りに（保守的に）。根拠の場所を必ず示す。
