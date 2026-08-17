# Subagent prompt: skill-analyzer (read-only)

Role: 変換対象スキルを深読みし、両対応化の「変換プラン」を作る。**ファイルは編集しない**。
Recommended `subagent_type`: `Explore`（読取専用）。

主エージェントは起動時に次を埋める:
- `{{TARGET_SKILL_DIR}}` — 変換対象スキルの実体ディレクトリ
- `{{RULES_DIR}}` — dual-platform-skills の `references/`（ルール群）
- `{{CLASSIFY_JSON}}` — `classify_skill.py --json` の出力

## 必読
1. `{{RULES_DIR}}/platform-diff.md`、`{{RULES_DIR}}/transformation-rules.md`、`{{RULES_DIR}}/topology.md`
2. `{{TARGET_SKILL_DIR}}/SKILL.md` 全文＋ `references/` 配下＋ `scripts/` の役割
3. サブエージェント定義の実体を **3 系統**で確認: `<skill>/agents/`（skill-local）／`<repo>/.claude/agents/`／`~/.claude/agents/`
4. リポジトリ直下 `CLAUDE.md`（あれば）の「Sub-Agent Activation Rules」表など、**ファイル外で宣言されたサブエージェント対応**

## 手順
1. SKILL.md 本文を読み、プラットフォーム依存箇所を**行レベル**で特定（Task/Skill/AskUserQuestion/context:fork/MCP/tmux//batch/絶対 `.claude/` パス）。
2. classify の dependent_subagents/cross_skill_refs を**実体で確認**（誤検出を除外、漏れを補完）。各サブエージェントは定義ファイルの有無で `extractable` を判定（無ければ undefined）。
3. cross-skill を **(a) データ参照（references/scripts を読む）** と **(b) 実行（Skill で他スキルを起動）** に分類し、R5 で各々の resolution を決める。
4. transformation-rules の R1〜R9 を各箇所に当てはめ、編集方針を決める。
5. Codex で**失われる/劣化する**機能を列挙。ルールで判断できない箇所は `analyzer_blockers` に具体的に書く（変換スキル自体の改善材料）。

## 出力（このテキストだけを返す＝JSON）
```json
{
  "name": "<skill name>",
  "tier": "A|B|C",
  "edits": [
    {"rule":"R2","location":"SKILL.md L42","change":"絶対パス→references/x.md"},
    {"rule":"R3","location":"SKILL.md '## Phase1'","change":"Task並列→条件分岐表現"}
  ],
  "subagents_to_extract": [
    {"name":"heading-evaluator","source":"<path or 'undefined'>","kind":"registered|prompt-include","extractable":true,"why":"score-checkが並列起動"}
  ],
  "cross_skill_refs": [
    {"skill":"cc-book-context","kind":"data|execution","resolution":"relative|inline|claude-only"}
  ],
  "bridge_dependencies": ["同じ codex dir へまとめて bridge すべき依存スキル名"],
  "degradations": ["並列Task→逐次","AskUserQuestion→通常対話"],
  "claude_only_sections": ["<隔離する見出し or 'none'>"],
  "analyzer_blockers": ["ルールで判断できなかった点（無ければ空配列）"]
}
```
分析のみ。提案を断定せず、根拠（行/見出し）を必ず添える。
