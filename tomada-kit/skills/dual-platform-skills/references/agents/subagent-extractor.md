<!-- platform-annex -->
# Subagent prompt: subagent-extractor (write)

Role: 対象スキルが依存する**1 つの**サブエージェントの知識を、対象スキル内の
`references/agents/<name>.md` に抽出して両プラットフォーム共有化する。
Recommended `subagent_type`: `general-purpose`。**1 サブエージェント＝1 起動**（並列時はファイルが別なので競合しない）。

主エージェントが埋める:
- `{{TARGET_SKILL_DIR}}`、`{{RULES_DIR}}`
- `{{SUBAGENT_NAME}}` — 抽出対象の名前
- `{{SUBAGENT_SOURCE}}` — 元定義。在処は 3 系統: `<skill>/agents/<name>.md`（skill-local）／`.claude/agents/<name>.md`（project）／`~/.claude/agents/<name>.md`（user）。**別スキルの `agents/` に定義された cross-skill サブエージェント**もあり得る。`undefined`（定義ファイル無し）なら抽出せず、その旨を返してメインに claude-only 扱いを促す。

## 必読
- `{{SUBAGENT_SOURCE}}` 全文
- `{{RULES_DIR}}/transformation-rules.md` の R4

## 種類とパス（R4 / R10 厳守）
- まず種類を判定: **(i) 登録済み Claude サブエージェント**（frontmatter `tools/model/color` あり・名前起動）か、**(ii) プロンプト同梱の指示ファイル**（素の手順）か。
- (ii) の場合、`references/agents/<name>.md` を**唯一の canonical** にし**ミラーを作らない**（drift 防止）。(i) の場合は元の `.claude/agents/<name>.md` を Claude 名前起動用に残し、ここへは知識コピー（snapshot 注記）。
- **R10**: この reference は「メインが読んで Task に内容を渡す／Codex はメインが相対で読む」前提。内部のデータパス（`../<other>/...` 等）は skill 相対で書き、Claude Task 実行時はメインが**絶対化して渡す**前提であることを 1 行注記する。

## 不可侵
- 元サブエージェントの**指示内容・チェックリスト・採点基準・出力契約を変えない**。プラットフォーム中立な「知識」だけを残す。

## 手順
1. `{{SUBAGENT_SOURCE}}` から、実行に必要な**手順・チェックリスト（番号付き）・入出力契約・採点/判定基準**を抽出。
2. Claude 固有の起動メタ（frontmatter の `tools`/`model`/`color` 等）は**落とす**（知識ではないため）。
3. `{{TARGET_SKILL_DIR}}/references/agents/{{SUBAGENT_NAME}}.md` に、次の形で書き出す:
   ```markdown
   # Subagent knowledge: {{SUBAGENT_NAME}}
   Role: <一行>
   ## チェックリスト / 手順
   1. ...
   ## 出力契約
   ...
   ```
   - **Claude**: `Task`（subagent_type: general-purpose）でこの内容をプロンプトとして渡す。
   - **Codex / Task 無し**: メインがこの内容を逐次インライン実行する。
   （上記 2 文を各 reference 末尾に明記し、両対応であることを自己説明させる。）
4. 既に共有 reference が存在する共通サブエージェント（複数スキル利用）は**重複作成せず**、その旨を返す。

## 出力
作成/更新したファイルパスと、抽出した要素の要約をテキストで返す。
