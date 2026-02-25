---
name: tomada-writing
allowed-tools: Read, Edit, Write, Bash, Task, Grep, Glob, AskUserQuestion
description: とまだ式の技術記事執筆・改善スキル。Use PROACTIVELY when user mentions「とまだ式」「記事を書いて」「Zenn記事」「技術記事執筆」「リライト」or requests article writing, rewriting, improvement in Japanese. Plan modeで構成ヒアリング後に執筆開始。Pre-Writing Phaseで構成案を事前評価し、サブエージェントによる7軸並列評価で95点以上を目指す。 Examples: <example>Context: User requests article user: '記事を書いて' assistant: 'I will use tomada-writing skill' <commentary>Triggered by article writing request</commentary></example> <example>Context: Rewrite request user: 'この記事をリライトして' assistant: 'I will use tomada-writing skill' <commentary>Triggered by rewrite request</commentary></example>
---

# とまだ式記事執筆スキル

## 執筆前チェックリスト（★最重要★）

**執筆開始前に必ず確認し、初稿から全て適用すること:**

| # | ルール | 詳細 |
|---|--------|------|
| 1 | 冒頭挨拶 | 「こんにちは、とまだです。」で始める |
| 2 | 結論先出し | 冒頭で「読者が得られるベネフィット」を伝える（設定方法の簡単さより価値） |
| 3 | 両面提示 | 「一方で」「ただ」でデメリット・限界も正直に伝える |
| 4 | 控えめな断定 | 意見は「〜と考えています」「〜ではないでしょうか」 |
| 5 | 見出し直後に説明文 | 見出し→箇条書きは禁止。必ず説明文を挟む |
| 6 | 見出し前の予告禁止 | 「次は〜について説明します」は書かない |
| 7 | 「大丈夫です」禁止 | 事実ベースの説明で安心感を与える |
| 8 | 「〜しました」回避 | 文末が「〜しました」で終わる文を最小限に |
| 9 | 要約セクション | 「## 忙しい人のために要約」を冒頭に入れる |
| 10 | 接続詞は自然に | 無理に増やさない。同じ接続詞の連続は避ける |
| 11 | 「あなた」禁止 | 「皆さん」「開発者」「ユーザー」に置き換える |
| 12 | `:::message`は短く | 見出し・箇条書き禁止、5行以内が理想（Zenn固有） |

> 上記ルールは `tone-and-style.md` の文体スタイルルールに基づく。

---

## 冒頭パターン（必須構造）

```markdown
こんにちは、とまだです。

【結論先出し】← 最重要（ベネフィットを伝える）
今回伝えたいことの要点は「〇〇できるようになる」ということです。
（設定方法の簡単さより、読者が得られる価値・メリットを伝える）

【価値提示】
この記事では、〇〇から△△までを解説します。

## 忙しい人のために要約

- 要点1
- 要点2
- 要点3
```

**結論先出しのポイント**:
- ❌「設定に1行追加するだけで〜」（手段の簡単さ）
- ✅「処理を待たずに作業を継続できる」（得られるベネフィット）

---

## 3つのモード

1. **タイトルのみモード**: タイトルだけ → ゼロから執筆
2. **ざっくりメモモード**: メモがある → 肉付けして執筆
3. **リライトモード**: 本文がある → とまだ式に変換

---

## 5つのテンプレート

| テンプレート | 重さ | 文字数 | 目標スコア |
|------------|------|--------|-----------|
| 体系的チュートリアル型 | 重め | 3000-5000字 | 95点 |
| 検証レポート型 | 重め | 2000-4000字 | 95点 |
| 比較分析型 | 中程度 | 1500-3000字 | 95点 |
| 今日の発見（TIL）型 | 軽め | 500-1000字 | **80点** |
| 使ってみた感想型 | 軽め | 300-800字 | **80点** |

→ 詳細: `references/templates/`

---

## ワークフロー

### ステップ0: Plan mode（計画）

1. ファイル読み込み & モード判断
2. テンプレート選択（AskUserQuestion）
3. **Pre-Writing Phase使用確認**（AskUserQuestion）
   - デフォルト: No（従来通り）
   - `use_pre_writing: true`指定時: 自動でYes
4. タイトル評価 & 見出し構成案
5. ExitPlanModeで承認取得

### ステップ0.5: Pre-Writing Phase（オプション）

**条件**: Plan modeでPre-Writing使用を選択した場合、または`use_pre_writing: true`が指定された場合

**目的**: 執筆前に7軸評価基準を意識した構成案を作成し、初稿品質を80-90点に向上させる

#### 0.5.1: outline-generator呼び出し

```
Task(subagent_type="outline-generator", prompt="以下の情報で構成案を生成:
- Title: <タイトル>
- Template: <テンプレートタイプ>
- Key Message: <要点>")
```

#### 0.5.2: outline-validator呼び出し

```
Task(subagent_type="outline-validator", prompt="以下の構成案を検証:
<生成された構成案>")
```

#### 0.5.3: 予測スコア確認

| 予測スコア | アクション |
|-----------|-----------|
| 90点以上 | ステップ1へ進む |
| 85-89点 | 軽微な修正後にステップ1へ |
| 85点未満 | outline-generatorに修正依頼（最大2回） |

#### 0.5.4: 構成案承認

構成案をユーザーに提示し、承認後に執筆開始。

→ 詳細: `references/outline-template.md`

### ステップ1-5: 執筆・改善

| ステップ | 内容 |
|---------|------|
| 1 | **チェックリスト確認** → 初稿作成（構成案に基づく/直接編集） |
| 2 | **スクリプト評価** → **サブエージェント評価** (両方使用) |
| 3 | **ターゲット改善** (evaluator結果を基にimproverで改善) |
| 4 | 改善 → 再評価（95点達成まで、最大5回） |
| 5 | 太字化（最終仕上げ）→ 完了 |

---

## 評価・改善オーケストレーション（スクリプトファースト方式）

**設計思想**: まずPythonスクリプトで機械的チェックを実行し、その後サブエージェント（LLM）でスクリプトでは判断できない主観的評価・改善を行う。両方を必ず使用することで、コンテキスト効率と評価品質を両立。

### 評価ツール構造

```
.claude/skills/tomada-writing/
├── scripts/                      # 機械的評価（Phase 1で使用）
│   ├── calculate_score.py        # ★統合スコア計算（メイン）
│   ├── check_ng_words.py
│   ├── check_structure.py
│   ├── check_saborou_style.py
│   ├── check_empathy_expressions.py
│   ├── check_opening_structure.py
│   ├── check_intro_phrases.py
│   ├── check_sentence_endings.py
│   ├── check_bold_formatting.py  # ★太字フォーマット（Phase 5で使用）
│   ├── add_sentence_breaks.py    # ★句点改行挿入（Phase 5で使用）
│   └── check_message_box.py      # ★メッセージボックス（Zenn向け、参考値）
└── references/                   # ルール定義

.claude/agents/tomada-writing/
├── outline/                      # Pre-Writing Phase
│   ├── generator.md              # 構成案生成（sonnet）
│   └── validator.md              # 構成案検証（haiku）
├── conjunction/                  # 接続詞（20点）
│   ├── evaluator.md              # LLM評価（スクリプト補完）
│   └── improver.md               # 改善提案
├── ng-words/                     # NGワード（15点）
├── structure/                    # 文体品質（15点）
├── saborou-style/                # 文体スタイル（15点）
├── empathy/                      # 共感・トーン（15点）
├── explanation-depth/            # 説明深度（15点）★新設★
│   ├── evaluator.md              # LLM評価（主観的評価）
│   └── improver.md               # 改善提案
├── opening/                      # 冒頭構成（10点）
└── intro-phrase/                 # 導入フレーズ（10点）
```

**重要**:
- **Phase 1**: スクリプト（`calculate_score.py`）で機械的評価
- **Phase 2**: サブエージェント（evaluator）でスクリプトでは判断できない主観的評価
- **Phase 3**: サブエージェント（improver）で改善提案
- 両方を必ず使用する

---

### Phase 1: スクリプトによる機械的評価

**★最初に必ず実行★**

```bash
python3 .claude/skills/tomada-writing/scripts/calculate_score.py "<記事パス>"
```

**スクリプト出力例**:
```json
{
  "total_score": 82.5,
  "grade": "B+",
  "requires_retry": true,
  "failed_axes": [
    {"axis": "ng_words", "score": 0, "threshold": 15, "deficit": 15},
    {"axis": "opening_structure", "score": 6, "threshold": 8, "deficit": 2}
  ],
  "breakdown": {
    "conjunction": {"score": 18, "max_score": 20, "min_threshold": 16},
    "ng_words": {"score": 0, "max_score": 15, "min_threshold": 15},
    ...
  }
}
```

**スクリプトでチェックできる項目**:
- NGワード検出（完全一致）
- 接続詞使用率（数値計算）
- 冒頭構成の必須要素（パターンマッチ）
- 導入フレーズ数（カウント）

### Phase 2: サブエージェントによるLLM評価

スクリプトでは判断できない主観的評価をサブエージェントで補完:

**`failed_axes` または低スコアの軸に対して、evaluatorを呼び出す**:

```
Task(subagent_type="<axis>-evaluator", prompt="<記事パス>を評価")
```

**サブエージェントでチェックする項目**:
- 共感表現の質と配置の適切さ
- 文体スタイル要素の自然さ
- 文体・トーンの一貫性
- 両面提示の説得力

### Phase 3: ターゲット改善

スクリプト結果とevaluator結果を統合し、improverで改善:

```
Task(subagent_type="<axis>-improver", prompt="以下の評価結果を基に改善提案:
- Article: <記事ファイルパス>
- Script Score: <スクリプトのスコア>
- LLM Evaluation: <evaluatorの評価結果>
- Issues: <統合した問題点>")
```

| 軸名（failed_axes） | evaluator (subagent_type) | improver (subagent_type) |
|--------------------|--------------------------|--------------------------|
| ng_words | `ng-words-evaluator` | `ng-words-improver` |
| conjunction | `conjunction-evaluator` | `conjunction-improver` |
| style_quality | `structure-evaluator` | `structure-improver` |
| saborou_style | `saborou-style-evaluator` | `saborou-style-improver` |
| empathy_tone | `empathy-evaluator` | `empathy-improver` |
| explanation_depth | `explanation-depth-evaluator` | `explanation-depth-improver` |
| opening_structure | `opening-evaluator` | `opening-improver` |
| intro_phrases | `intro-phrase-evaluator` | `intro-phrase-improver` |

### Phase 4: 適用 & 再評価

1. improverの改善提案をレビュー
2. 記事に修正を適用（Edit tool使用）
3. **Phase 1に戻る（スクリプトで再評価）**
4. **以下の条件を全て満たすまで繰り返し（最大5回）**:
   - 総合スコア109点以上（115点満点の95%）
   - 全軸が最低基準（80%）を超えている（`requires_retry: false`）
   - NG表現が0件
5. **5回で達成できない場合**: 現状と残課題を報告し、ユーザーに判断を委ねる

### Phase 5: 完了（太字化 + 句点改行 + CommonMarkチェック）

1. 太字強調を適用（`references/bold-emphasis.md`参照）
2. **句点改行の自動挿入**を実行:
   ```bash
   python3 ~/.claude/skills/tomada-writing/scripts/add_sentence_breaks.py "<記事パス>" --fix
   ```
3. **太字フォーマットチェック**を実行:
   ```bash
   python3 ~/.claude/skills/tomada-writing/scripts/check_bold_formatting.py "<記事パス>"
   ```
4. **問題があれば自動修正**を適用:
   ```bash
   python3 ~/.claude/skills/tomada-writing/scripts/check_bold_formatting.py "<記事パス>" --fix
   ```
5. 完了レポートを出力

**太字チェックの重要性**: CommonMark仕様では、約物（「」、（）など）が`**`に直接接すると太字にならない場合がある。スクリプトで検出し、自動修正を適用する。

---

## 評価システム（115点満点）

→ 詳細は「サブエージェントオーケストレーション」セクション参照

### 合格条件（★全て満たすこと★）

1. **総合スコア109点以上**（115点満点の95%）
2. **各軸が最低基準（80%）を超えていること**
3. **NG表現が0件であること**（1件でも即不合格）

| 項目 | 配点 | 最低基準 | subagent_type |
|------|------|---------|---------------|
| 接続詞スコア | 20点 | 16点（80%） | `conjunction-evaluator` |
| NGワードスコア | 15点 | **15点（100%）** | `ng-words-evaluator` |
| 文体品質スコア | 15点 | 12点（80%） | `structure-evaluator` |
| 文体スタイルスコア | 15点 | 12点（80%） | `saborou-style-evaluator` |
| 共感・トーンスコア | 15点 | 12点（80%） | `empathy-evaluator` |
| 説明深度スコア | 15点 | 12点（80%） | `explanation-depth-evaluator` |
| 冒頭構成スコア | 10点 | 8点（80%） | `opening-evaluator` |
| 導入フレーズスコア | 10点 | 8点（80%） | `intro-phrase-evaluator` |

**説明深度の評価項目**:
- 概念の適切な導入（専門用語・新概念に説明があるか）
- 一文の完結性（意味不明瞭な文が放置されていないか）
- 補足・具体例の充実（箇条書きや表に導入文・まとめ文があるか）
- Why/Howの明示（理由・方法が説明されているか）

**評価基準**:
- A+（109点以上 + 全軸合格）: 公開可能
- A（103-108点）: 軽微な改善で公開可能
- B+（92-102点）: 軽めテンプレートならOK
- B（80点未満）: 要改善

> **重要**: 総合スコアが109点以上でも、1軸でも最低基準を下回っていれば再実行必須。

---

## 絶対に避けること

1. **とまだの経験を捏造しない**
2. **過度な例え話に依存しない**
3. **見出し前に予告文を書かない**
4. **NGワード**: 「大丈夫です」「安心してください」「劇的に」「ヤバい」

→ 詳細: `references/forbidden-expressions.md`

---

## テンプレート

| テンプレート | 適用条件 | 内容 |
|------------|---------|------|
| `templates/udemy-promotion.md` | Claude Code関連記事 | Udemy講座宣伝セクション |

> **Udemy宣伝**: Claude Code・CLAUDE.md・rules・カスタムコマンド・サブエージェント・Skills・Hooksに関連する記事には、末尾にUdemy講座の宣伝を追加すること。詳細は`templates/udemy-promotion.md`参照。

---

## リファレンスガイド

### 核心（必ず参照）

| ドキュメント | 内容 |
|-------------|------|
| `tone-and-style.md` | 文体スタイルルール（結論先出し、両面提示、控えめ断定） |
| `forbidden-expressions.md` | 禁止表現・NGワード |
| `grammar-rules.md` | 見出し構造、段落ルール |

### 補助

| ドキュメント | 内容 |
|-------------|------|
| `persona-and-tone.md` | ペルソナ、トーン定義 |
| `expression-patterns.md` | 冒頭・締めテンプレート |
| `evaluation-rules.md` | LLM評価ルール |
| `note-markdown-constraints.md` | note.com固有のMarkdown制約（テーブル不可等） |

### 目的別

| 目的 | 参照先 |
|------|--------|
| スコアを上げたい | `troubleshooting.md` |
| タイトル改善 | `title-guidelines.md` |
| 太字化 | `bold-emphasis.md` |

---

## AI Instructions

### Always

1. **執筆前チェックリストを確認** → 初稿から全ルール適用
2. **Plan modeで開始** → ExitPlanMode承認後に執筆
3. **元ファイルを直接編集**
4. **スクリプト→サブエージェントの順で評価** → 両方必ず使用
5. **failed_axesの軸を中心にevaluator→improverで改善**
6. **目標スコアまで繰り返す**（重め: 95点、軽め: 80点、最大5回）
7. **Claude Code関連記事にはUdemy宣伝を追加** → `templates/udemy-promotion.md`参照

### Never

1. とまだの経験を捏造しない
2. Plan mode承認前に執筆開始しない
3. NGワードを使用しない
4. 見出し前に予告文を書かない
5. 評価をスキップしない
6. **「品質は高いがスコアは低い」と判断しない**
7. **最低基準未達の軸がある場合、改善なしで完了としない**

### When Uncertain

- ターゲット不明 → AskUserQuestionで確認
- 技術的正確性に自信なし → ユーザーに確認
- スコアが改善しない → 現状を最終稿として報告

### On Error

1. **サブエージェント失敗** → スクリプト直接実行にフォールバック
2. **スクリプト失敗** → ユーザーに報告し手動評価を依頼
3. **5回ループ後も95点未達** → 現状と残課題を報告（既存ルール）
4. **ファイル読み込み失敗** → パスを確認しユーザーに報告

---

## 関連スキル

### tomada-ai-dev-philosophy

AI駆動開発に関する記事を書く際は、`tomada-ai-dev-philosophy`スキルのreferenceを参照して、とまだの思想・哲学を正確に反映させること。

**使用場面**:
- AI駆動開発の解説記事
- 仕様駆動開発（SDD）の記事
- 品質・テスト・レビューに関する記事
- 人間とAIの協働に関する記事
- コンテキストエンジニアリングの記事

**参照パターン**:

| 記事テーマ | 参照するreference |
|-----------|-------------------|
| AI駆動開発全般 | `core-philosophy.md` |
| SDD、仕様駆動 | `sdd-principles.md` |
| 品質、テスト | `quality-mindset.md` |
| 人間とAI | `human-ai-collaboration.md` |
| コンテキスト | `context-engineering.md` |
| 段階的開発 | `iterative-development.md` |
| 判断基準 | `practical-judgments.md` |

**使用方法**:

```
1. 記事テーマを確認
2. 対応するreferenceファイルを読み込む
   例: Read .claude/skills/tomada-ai-dev-philosophy/references/core-philosophy.md
   (iObsidianリポジトリ内に配置)
3. 格言や考え方を記事に反映
```

**引用例**:

```markdown
私はAI駆動開発において「要件定義が全て」と考えています。
曖昧な指示からは曖昧な成果しか生まれないからです。
```
