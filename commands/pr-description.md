---
description: Create or update PR title and description for a given PR number
---

# PR Description Generator

指定されたPR番号に対して、タイトルと概要欄を作成または更新します。

## 使い方

```
/pr-description <pr-number>
```

例:
```
/pr-description 10
/pr-description 5
```

---

## 実行内容

PR番号: **$ARGUMENTS**

### 1. PR情報の収集

以下の情報を収集します:

```bash
# PR基本情報
gh pr view $ARGUMENTS --json title,body,headRefName,baseRefName,state

# 変更ファイルリスト
gh pr diff $ARGUMENTS --name-only

# コミット履歴
gh pr view $ARGUMENTS --json commits --jq '.commits[] | "\(.oid[0:7]) \(.messageHeadline)"'
```

### 2. 変更内容の分析

以下の観点で変更を分析:

- **アーキテクチャ変更**: Domain, Application, Infrastructure, Presentationの各層への影響
- **機能追加**: 新規機能、画面、コンポーネント
- **リファクタリング**: 構造改善、コード整理
- **バグ修正**: 不具合修正、エラーハンドリング改善
- **ドキュメント**: README, ガイド、コメント
- **テスト**: 新規テスト、テスト改善
- **設定**: 依存関係、ビルド設定、環境変数

### 3. PR概要の構成

以下の構造でPR概要を作成:

```markdown
## 概要

[変更の要約を3-5行で記述]

## 背景・目的

### 現状の課題
[解決しようとしている問題]

### 目標
[このPRで達成したいこと]

## 主な変更内容

### 1. [カテゴリ1]
- [変更内容1]
- [変更内容2]

### 2. [カテゴリ2]
- [変更内容1]
- [変更内容2]

## テスト結果

### 品質ゲート
\`\`\`bash
npm run check:all
\`\`\`
- ✅/❌ ESLint
- ✅/❌ Prettier
- ✅/❌ TypeScript
- ✅/❌ Jest

## 動作確認

[実機/シミュレータでの動作確認結果]

## 次のステップ

[このPR後の予定、残タスクがある場合は記載]

## 関連リンク

- [関連Issue/PRへのリンク (close #xx 形式)]
```

### 4. タイトルの生成

Conventional Commits形式でタイトルを生成:

**形式**: `<type>(<scope>): <subject>`

**タイプ**:
- `feat`: 新機能
- `fix`: バグ修正
- `refactor`: リファクタリング
- `docs`: ドキュメント
- `test`: テスト
- `chore`: ビルド、設定
- `perf`: パフォーマンス改善

**例**:
- `feat(subscription): 月額・年額サブスクリプション対応`
- `refactor(architecture): サブスク判定経路の一本化`
- `docs(guide): Clean Architecture + DDD ガイドライン整備`

### 5. PRの更新

生成した内容でPRを更新:

```bash
# タイトル更新
gh pr edit $ARGUMENTS --title "<new-title>"

# 概要更新
gh pr edit $ARGUMENTS --body "$(cat <<'EOF'
<new-body>
EOF
)"
```

## 成功基準

- ✅ PR概要が構造化されており、変更内容が明確
- ✅ タイトルがConventional Commits形式
- ✅ テスト結果が記載されている
- ✅ 関連リンク（Issue、PR）が含まれている

## 注意事項

### マージ済みPRの場合

- マージ済みでも概要は更新可能
- 履歴として残すため、詳細な記録を推奨

### 大規模PRの場合

- セクションを折りたたみ可能にする（`<details>`タグ）
- 主要な変更のみハイライト
- 詳細は別ドキュメントへのリンク

## 実装方針

1. **情報収集フェーズ**: すべての関連情報を並列で取得
2. **分析フェーズ**: 変更内容をカテゴライズ
3. **生成フェーズ**: テンプレートに従って概要を作成
4. **検証フェーズ**: 品質チェック（文字数、必須項目）
5. **更新フェーズ**: ghコマンドでPRを更新
