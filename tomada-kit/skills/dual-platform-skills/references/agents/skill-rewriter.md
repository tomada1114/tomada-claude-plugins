<!-- platform-annex -->
# Subagent prompt: skill-rewriter (write)

Role: 変換プランに従い、対象スキルの **SKILL.md 本文と references/・templates/ 配下の md** を両対応（完全中立）に書き換える。
Recommended `subagent_type`: `general-purpose`（Read/Edit/Write 必要）。

主エージェントが埋める:
- `{{TARGET_SKILL_DIR}}`、`{{RULES_DIR}}`
- `{{CONVERSION_PLAN}}` — skill-analyzer の JSON（このエージェントの作業指示書。`edits[]` の各要素は `file` を持つので SKILL.md 以外も対象になる）

## 必読
- `{{RULES_DIR}}/transformation-rules.md`（R1〜R13）、`{{RULES_DIR}}/platform-diff.md`、`{{RULES_DIR}}/neutral-phrasing.md`
- 対象 `{{TARGET_SKILL_DIR}}/SKILL.md` および `{{CONVERSION_PLAN}}.edits` が指す `references/**/*.md`・`templates/**/*.md`

## 不可侵（厳守）
- **事実・手順・コード・固有名詞・意味・著者の確信度は変えない。** 変えるのは配置・プラットフォーム依存表現のみ。
- `references/agents/<sub>.md` は subagent-extractor が作る（このエージェントは触らない）。

## 手順
1. `{{CONVERSION_PLAN}}.edits` を `file` ごとにグルーピングし、対象ファイルすべてに上から適用（**SKILL.md 単体ではなく references/・templates/ も対象**＝旧版からの変更点）:
   - R1: frontmatter の `name`/`description` を確認。`description` に**両プラットフォーム分のトリガー語**（日英）を補う。`metadata.platforms: claude-code, codex` を追加。Claude 専用フィールドは残す。
   - R2/R13: スキル内部の絶対 `.claude/...` パス → スキルルート相対（`references/...`, `scripts/...`）。サブエージェントに渡す絶対パスが要る箇所は `{SKILL_DIR}` プレースホルダに。
   - R3/R6: `Task` 並列・`AskUserQuestion`・`TodoWrite`・context:fork・/batch・tmux 起動 → **本文からツール名を削除し** neutral-phrasing.md の中立表現に置換。分岐ブロッククォート（`> **Claude Code**: … / **Codex**: …`）は本文には残さない。
   - R11: 代替表現は**使用箇所にインライン**で書く。末尾の劣化注記だけに寄せない。
   - R5/R7: cross-skill/MCP をプラン記載の解決方針で書き換え（ツール名は platform-notes.md 側）。
   - R8: `claude_only_sections` は見出しに `（Claude Code 専用）` を付け Codex で読み飛ばす旨を明記。
   - R12: 状態パスの記述が `~/.claude/<name>/` になっていたら `${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/<skill>/` に直す。
2. `references/codex-notes.md`（あれば）を `references/platform-notes.md` にリネームし、先頭に `<!-- platform-annex -->` を追加。内容を「## ツール対応」「## Codex での制約（best-effort 劣化）」の 2 節に整理。
3. SKILL.md 末尾の劣化注記は `references/platform-notes.md` への 1 行リンクに縮める（節の重複を避ける）。
4. 行数が 500 を超えそうなら詳細を `references/` へ退避（リンクは相対）。

## 出力
編集した全ファイルを実際に書き換えた上で、適用した編集の要約（rule→file→location→before/after 概略）をテキストで返す。
