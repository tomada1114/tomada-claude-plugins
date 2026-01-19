# Agent Templates Reference

サブエージェントの詳細リファレンス。

## Agent File Format

```markdown
---
name: agent-name
description: What it does. Use PROACTIVELY when [triggers].
tools: Read, Grep, Glob, Bash, Edit, Write
model: opus|sonnet|haiku
---

# Agent Instructions

Your role and responsibilities...

## Workflow
1. Step one
2. Step two

## Checklist
- [ ] Item one
- [ ] Item two
```

## YAML Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | **Yes** | lowercase-with-hyphens、64文字以下 |
| `description` | **Yes** | 説明 + トリガーワード + `<example>`タグ、1024文字以下 |
| `tools` | **Yes** | 使用可能なツールのリスト |
| `model` | **Yes** | opus / sonnet / haiku |
| `color` | Optional | UI表示色: red, green, blue, yellow, purple, cyan, gray など |

## Agent Activation: The ~25% Problem

エージェントの `description` だけでは **約25%の確率でしか自動アクティベートされない** という問題があります。

### 解決策1: `<example>` タグを使用（推奨）

description に `<example>` タグを含めることでアクティベート率を向上:

```yaml
description: >-
  Expert code reviewer for quality and security.
  Use PROACTIVELY after writing code.
  MUST BE USED for all code changes.
  Examples:
  <example>
  Context: User finished implementing a feature
  user: 'Review my changes'
  assistant: 'I will use code-reviewer agent'
  <commentary>Triggered by code review request</commentary>
  </example>
  <example>
  Context: User modified authentication code
  user: '認証コードを書いた'
  assistant: 'I will use code-reviewer agent'
  <commentary>Triggered after security-critical code change</commentary>
  </example>
```

### 解決策2: CLAUDE.md 統合（100%保証）

`~/.claude/CLAUDE.md` または `./.claude/CLAUDE.md` にスキルアクティベーションルールを記載:

```markdown
## Skill Activation Rules

| Agent | Trigger |
|-------|---------|
| `code-reviewer` | コード変更後、PRレビュー依頼 |
| `security-reviewer` | 認証・決済・入力処理のコード |
| `tdd-guide` | 新機能実装、バグ修正 |
```

### ベストプラクティス

1. **`Use PROACTIVELY`** - 自動使用を促す
2. **`MUST BE USED`** - 強制的な使用を示す
3. **トリガーワード** - 日本語・英語両方含める
4. **`<example>` タグ** - 具体的な使用シナリオを示す
5. **CLAUDE.md** - テーブル形式で明示的にルール化

## Model Selection Guide

| Model | Cost | Speed | Use Case |
|-------|------|-------|----------|
| **opus** | 高 | 遅 | 複雑な推論、アーキテクチャ決定、セキュリティ分析 |
| **sonnet** | 中 | 中 | 通常の開発作業、コード生成、テスト |
| **haiku** | 低 | 速 | 軽量タスク、頻繁な呼び出し、シンプルな検証 |

## Available Tools

| Tool | Description |
|------|-------------|
| Read | ファイルを読む |
| Write | ファイルを書く |
| Edit | ファイルを編集 |
| Bash | コマンドを実行 |
| Grep | テキスト検索 |
| Glob | ファイルパターン検索 |

## Agent Descriptions

### code-reviewer

**Purpose**: コード品質とセキュリティのレビュー

**Tools**: Read, Grep, Glob, Bash

**Model**: opus

**When to Use**:
- コード変更後
- PR作成前
- セキュリティ懸念がある時

**Checklist**:
- [ ] コードがシンプルで読みやすい
- [ ] 関数と変数の命名が適切
- [ ] 重複コードがない
- [ ] 適切なエラーハンドリング
- [ ] シークレットが露出していない
- [ ] 入力検証が実装されている

---

### security-reviewer

**Purpose**: セキュリティ脆弱性の分析

**Tools**: Read, Write, Edit, Bash, Grep, Glob

**Model**: opus

**When to Use**:
- セキュリティクリティカルなコード
- 認証/認可の実装
- 外部入力の処理

**Security Checks**:
- [ ] ハードコードされた認証情報
- [ ] SQLインジェクションリスク
- [ ] XSS脆弱性
- [ ] CSRF脆弱性
- [ ] パストラバーサルリスク
- [ ] 認証バイパス

---

### architect

**Purpose**: システム設計とアーキテクチャ決定

**Tools**: Read, Grep, Glob

**Model**: opus

**When to Use**:
- 新機能の設計
- 大規模なリファクタリング
- 技術選定

**Considerations**:
- スケーラビリティ
- 保守性
- パフォーマンス
- セキュリティ
- テスタビリティ

---

### planner

**Purpose**: 機能実装の計画

**Tools**: Read, Grep, Glob

**Model**: opus

**When to Use**:
- 新機能の実装前
- 複雑なタスクの分解
- 見積もりが必要な時

**Output**:
- 実装ステップ
- 必要なファイル変更
- 依存関係
- リスク

---

### tdd-guide

**Purpose**: テスト駆動開発の指導

**Tools**: Read, Write, Edit, Bash, Grep, Glob

**Model**: sonnet

**When to Use**:
- 新機能の実装
- バグ修正
- リファクタリング

**TDD Cycle**:
1. RED - 失敗するテストを書く
2. GREEN - テストを通す最小限のコードを書く
3. REFACTOR - コードを改善

---

### build-error-resolver

**Purpose**: ビルドエラーの解決

**Tools**: Read, Write, Edit, Bash, Grep, Glob

**Model**: sonnet

**When to Use**:
- ビルドが失敗した時
- TypeScriptエラー
- 依存関係の問題

**Workflow**:
1. エラーメッセージを分析
2. 原因を特定
3. 修正を実装
4. ビルドを再実行

---

### e2e-runner

**Purpose**: Playwright E2Eテストの生成と実行

**Tools**: Read, Write, Edit, Bash, Grep, Glob

**Model**: sonnet

**When to Use**:
- クリティカルなユーザーフロー
- UI変更後
- リグレッションテスト

**Test Pattern**:
```typescript
test('user can complete checkout', async ({ page }) => {
  await page.goto('/products')
  await page.click('[data-testid="add-to-cart"]')
  await page.click('[data-testid="checkout"]')
  await expect(page).toHaveURL('/checkout/success')
})
```

---

### refactor-cleaner

**Purpose**: デッドコードの削除とリファクタリング

**Tools**: Read, Write, Edit, Bash, Grep, Glob

**Model**: sonnet

**When to Use**:
- 長いコーディングセッション後
- 機能削除後
- コードクリーンアップ

**Targets**:
- 未使用のインポート
- 未使用の変数/関数
- コメントアウトされたコード
- 不要な.mdファイル

---

### doc-updater

**Purpose**: ドキュメントの同期と更新

**Tools**: Read, Write, Edit, Grep, Glob

**Model**: sonnet

**When to Use**:
- API変更後
- 新機能追加後
- README更新

**Documents**:
- README.md
- API documentation
- JSDoc/TSDoc
- CHANGELOG

## Agent Activation Pattern

description に以下を含めることで自動アクティベートを促進:

```yaml
description: ... Use PROACTIVELY when [trigger1], [trigger2], or working with [keyword].
```

**Example triggers**:
- "Use PROACTIVELY when reviewing code"
- "Use immediately after code changes"
- "Use when security concerns arise"
