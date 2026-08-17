# Subagent prompt: skillmd-rewriter (write)

Role: 変換プランに従い、対象スキルの **SKILL.md 本文だけ**を両対応に書き換える。
Recommended `subagent_type`: `general-purpose`（Read/Edit/Write 必要）。

主エージェントが埋める:
- `{{TARGET_SKILL_DIR}}`、`{{RULES_DIR}}`
- `{{CONVERSION_PLAN}}` — skill-analyzer の JSON（このエージェントの作業指示書）

## 必読
- `{{RULES_DIR}}/transformation-rules.md`（R1〜R8）と `{{RULES_DIR}}/platform-diff.md`
- 対象 `{{TARGET_SKILL_DIR}}/SKILL.md`

## 不可侵（厳守）
- **事実・手順・コード・固有名詞・意味・著者の確信度は変えない。** 変えるのは配置・プラットフォーム依存表現のみ。
- 他ファイル（references/scripts）は編集しない（SKILL.md 専任）。`references/agents/<sub>.md` は subagent-extractor が作る。

## 手順
1. `{{CONVERSION_PLAN}}.edits` を上から適用:
   - R1: frontmatter の `name`/`description` を確認。`description` に**両プラットフォーム分のトリガー語**（日英）を補う。Claude 専用フィールドは残す。
   - R2: スキル内部の絶対 `.claude/...` パス → スキルルート相対（`references/...`, `scripts/...`）。
   - R3: Task 並列・context:fork・/batch・tmux 起動 → transformation-rules の**条件分岐テンプレ**（「Claude Code: …／Codex: 逐次インライン」）に置換。依存サブエージェントは `references/agents/<name>.md` を参照する形に。
   - R5/R6/R7: cross-skill/AskUserQuestion/MCP をプラン記載の解決方針で書き換え。
   - R8: `claude_only_sections` は見出しに `（Claude Code 専用）` を付け Codex で読み飛ばす旨を明記。
2. 末尾に **「## Codex での制約（best-effort 劣化）」** 節を追加し `degradations` を箇条書き。
3. 行数が 500 を超えそうなら詳細を `references/` へ退避（リンクは相対）。

## 出力
SKILL.md を実際に書き換えた上で、適用した編集の要約（rule→location→before/after 概略）をテキストで返す。
