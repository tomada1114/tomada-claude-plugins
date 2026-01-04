---
description: Sync skills with CLAUDE.md Skill Activation Rules sections (check missing/orphaned entries)
allowed-tools: Read, Glob, Grep, Edit, Write, AskUserQuestion
---

# Sync Skills Command

スキルディレクトリとCLAUDE.mdの「Skill Activation Rules」セクションの整合性をチェックし、過不足を修正する。

## ワークフロー

### Step 1: スキルディレクトリをスキャン

以下のディレクトリからスキルを検出:

**ホームディレクトリ（user skills）**:
- パス: `~/.claude/skills/**/SKILL.md`
- 対応CLAUDE.md: `~/.claude/CLAUDE.md`

**プロジェクトディレクトリ（project skills）**:
- パス: `.claude/skills/**/SKILL.md`
- 対応CLAUDE.md: `./CLAUDE.md` または `./.claude/CLAUDE.md`

### Step 2: CLAUDE.mdをパース

各CLAUDE.mdから「## Skill Activation Rules」セクションを探し、テーブル内のスキル名を抽出。

**現在のテーブル形式**:
```markdown
| Skill | When to Use |
|-------|-------------|
| `skill-name` | いつ使うか。目的・用途の説明 |
```

### Step 3: 不整合を検出

| 状態 | 説明 | アクション |
|------|------|-----------|
| **Missing** | スキルあり、CLAUDE.md記載なし | 追加を提案 |
| **Orphaned** | CLAUDE.md記載あり、スキルなし | 削除を提案 |

### Step 4: レポート出力

**形式**:
```
=== User Skills (~/.claude/skills/) ===

Missing (スキルあり、CLAUDE.md記載なし):
- skill-name-1: いつ使うか
- skill-name-2: いつ使うか

Orphaned (CLAUDE.md記載あり、スキルなし):
- old-skill-name

=== Project Skills (.claude/skills/) ===

Missing:
- project-skill-1: いつ使うか

Orphaned:
- removed-skill
```

### Step 5: ユーザー確認

AskUserQuestionで修正の確認:
- 追加するスキルの選択
- 削除するエントリの選択

### Step 6: CLAUDE.md修正

承認されたエントリを追加・削除:

**追加時**:
- スキルのSKILL.mdを読み取り
- 「いつ使うか」「目的」を簡潔にまとめる
- テーブルに行を追加

**削除時**:
- テーブルから該当行を削除

---

## AI Instructions

このコマンドが実行されたら:

1. **Globでスキルをスキャン**:
   ```
   ~/.claude/skills/**/SKILL.md
   .claude/skills/**/SKILL.md
   ```
   ※ `examples/` 配下は除外する

2. **各SKILL.mdを読み取り**:
   - `name` フィールドを抽出
   - 「When to Use」セクションから用途を把握
   - 簡潔な「いつ使うか」の説明を生成

3. **CLAUDE.mdをパース**:
   - `~/.claude/CLAUDE.md` の「## Skill Activation Rules」セクション
   - プロジェクトの `CLAUDE.md` の同セクション
   - テーブルから `skill-name` を抽出（バッククォート内）

4. **比較して不整合を検出**:
   - スキルディレクトリにあるがCLAUDE.mdにない → Missing
   - CLAUDE.mdにあるがスキルディレクトリにない → Orphaned

5. **レポートを表示**:
   - User Skills と Project Skills を分けて表示
   - Missing/Orphaned それぞれリスト

6. **AskUserQuestionで確認**:
   - 修正するか確認
   - 追加/削除対象を選択

7. **CLAUDE.mdを修正**:
   - Missing → テーブルに行を追加
   - Orphaned → テーブルから行を削除

### 「When to Use」の書き方

SKILL.mdの内容から、以下の形式で生成:

**形式**: `〜する時。目的・特徴`

**例**:
- `tomada-writing` → 技術記事を執筆・リライトする時。95点評価システムで品質担保
- `claude-code-knowledge` → Claude Codeの機能・設定を調べる時。公式ドキュメントベースの回答
- `agile-ticket-planner` → 要件からGitHub Issueを作成する時。並列作業の特定と依存関係管理

**ポイント**:
- キーワードは書かない（descriptionで自動判定されるため）
- 「いつ使うか」を明確に
- 何が得られるか/何をしてくれるかを簡潔に

### Never

- 既存のテーブルエントリを勝手に変更しない
- ユーザー確認なしにCLAUDE.mdを修正しない
- descriptionのキーワードをそのままコピーしない（冗長なため）
- 長文を書かない（1行で収める）

### テーブル追加時のフォーマット

```markdown
| `skill-name` | いつ使うか。目的・特徴 |
```

- 1行で簡潔に
- 「〜する時。〜」の形式
- 日本語で記述
