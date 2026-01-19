# Command Templates Reference

スラッシュコマンドの詳細リファレンス。

## Command File Format

```markdown
---
description: Brief description shown in /help
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: <feature-description>
model: sonnet
---

# Command Name

Instructions for what this command does...
```

## YAML Frontmatter Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `description` | **Yes** | - | `/help` で表示される簡単な説明。256文字以下推奨 |
| `allowed-tools` | Recommended | All tools | コマンド実行中に使用可能なツールを制限。セキュリティと効率のため明示的に指定 |
| `argument-hint` | Optional | - | `/command <hint>` の形式で表示されるヒント。ユーザーに必要な引数を示す |
| `model` | Optional | User's default | `opus` / `sonnet` / `haiku` から選択。コマンドの複雑さに応じて指定 |
| `disable-model-invocation` | Optional | false | `true` にするとLLM呼び出しを無効化。Bashスクリプト実行のみのコマンド用 |

### Field Details

#### `description`
- `/help` コマンドで一覧表示される
- 簡潔かつ具体的に（動詞で始める）
- 例: "Run security scan on uncommitted changes"

#### `allowed-tools`
- カンマ区切りでツールを指定: `Read, Write, Edit, Bash, Grep, Glob`
- 制限することで安全性向上（例: 読み取り専用なら `Read, Grep, Glob`）
- 明示的に指定することでユーザーに許可確認の回数を減らせる

#### `argument-hint`
- コマンド入力時のオートコンプリートで表示
- `<required>` または `[optional]` の形式で
- 例: `<feature-description>`, `[path/to/analyze]`

#### `model`
- **opus**: 複雑な推論、アーキテクチャ決定、セキュリティ分析
- **sonnet**: 通常の開発作業、コード生成、テスト
- **haiku**: 軽量タスク、頻繁な呼び出し、シンプルな検証
- 指定しない場合はユーザーのデフォルトモデルを使用

#### `disable-model-invocation`
- LLMを呼び出さずにBashコマンドのみ実行するときに `true`
- 例: フォーマッターの実行、ビルドスクリプト起動など
- コマンド本文は `!` プレフィックスで始めることでBash実行

## Available Commands

### /plan

**Purpose**: 実装計画の作成

**Agent**: planner

**When to Use**:
- 新機能の実装前
- 複雑なタスクの分解
- チームとの共有用

**Output**:
- 実装ステップ
- 必要なファイル変更
- 依存関係
- リスクと考慮事項

**Example**:
```
/plan ユーザー認証機能を実装したい
```

---

### /tdd

**Purpose**: テスト駆動開発ワークフロー

**Agent**: tdd-guide

**When to Use**:
- 新機能の実装
- バグ修正
- リファクタリング

**Workflow**:
1. インターフェース定義
2. 失敗するテストを書く (RED)
3. テストを通す最小限のコード (GREEN)
4. リファクタリング (REFACTOR)
5. カバレッジ確認

**Example**:
```
/tdd メール検証関数を作りたい
```

---

### /code-review

**Purpose**: コード品質とセキュリティのレビュー

**Agent**: code-reviewer

**When to Use**:
- コード変更後
- PR作成前
- セキュリティ懸念がある時

**Checklist**:
- コードの可読性
- エラーハンドリング
- セキュリティ脆弱性
- テストカバレッジ
- パフォーマンス

**Example**:
```
/code-review 最近の変更をレビューして
```

---

### /build-fix

**Purpose**: ビルドエラーの修正

**Agent**: build-error-resolver

**When to Use**:
- ビルドが失敗した時
- TypeScriptエラー
- 依存関係の問題

**Workflow**:
1. エラーメッセージを分析
2. 原因を特定
3. 修正を実装
4. ビルドを再実行
5. 成功を確認

**Example**:
```
/build-fix ビルドが失敗した
```

---

### /e2e

**Purpose**: E2Eテストの生成

**Agent**: e2e-runner

**When to Use**:
- クリティカルなユーザーフロー
- UI変更後
- リグレッションテスト

**Test Framework**: Playwright

**Example**:
```
/e2e ログインフローのテストを作成して
```

---

### /refactor-clean

**Purpose**: デッドコードの削除とクリーンアップ

**Agent**: refactor-cleaner

**When to Use**:
- 長いコーディングセッション後
- 機能削除後
- コードベースの整理

**Targets**:
- 未使用のインポート
- 未使用の変数/関数
- コメントアウトされたコード
- 不要なファイル

**Example**:
```
/refactor-clean コードベースを整理して
```

---

### /test-coverage

**Purpose**: テストカバレッジの分析

**When to Use**:
- カバレッジ確認
- テスト追加の判断
- CI/CD前のチェック

**Output**:
- 現在のカバレッジ率
- カバーされていない部分
- 改善提案

**Example**:
```
/test-coverage src/utils/ のカバレッジを確認
```

---

### /update-docs

**Purpose**: ドキュメントの同期と更新

**Agent**: doc-updater

**When to Use**:
- API変更後
- 新機能追加後
- README更新

**Documents**:
- README.md
- API documentation
- JSDoc/TSDoc
- CHANGELOG

**Example**:
```
/update-docs 新しいAPIエンドポイントのドキュメントを追加
```

---

### /update-codemaps

**Purpose**: コードマップの更新

**When to Use**:
- 大きな変更後
- 新しいモジュール追加後
- ナビゲーション改善

**Example**:
```
/update-codemaps
```

## Command Chaining

コマンドは連鎖させることが可能:

```
/plan 新機能を実装 → /tdd テストを書く → /code-review レビュー
```

## Creating Custom Commands

### Example: Security Scan

```markdown
---
description: Run security vulnerability scan on the codebase
---

# Security Scan

Invoke the security-reviewer agent to perform a comprehensive security audit.

## What This Command Does

1. Scan for hardcoded secrets
2. Check for SQL injection risks
3. Verify input validation
4. Audit authentication/authorization
5. Report findings with severity levels

## Output Format

- CRITICAL: Must fix immediately
- HIGH: Should fix before release
- MEDIUM: Recommended to fix
- LOW: Nice to have

## Usage

Run `/security-scan` after implementing authentication, payment, or data handling features.
```

## Best Practices

1. **Single Purpose**: 1コマンド = 1目的
2. **Clear Description**: /help で分かりやすく
3. **Agent Integration**: 適切なエージェントと連携
4. **Examples**: 使用例を含める
5. **Output Format**: 期待される出力を明記
