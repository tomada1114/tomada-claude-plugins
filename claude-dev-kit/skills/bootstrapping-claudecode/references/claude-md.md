# CLAUDE.md Templates Reference

CLAUDE.md テンプレートの詳細リファレンス。

## CLAUDE.md Overview

CLAUDE.md は Claude Code に対する指示を記述するファイルです。

### Configuration Levels

| Level | Location | Scope |
|-------|----------|-------|
| User | `~/.claude/CLAUDE.md` | 全プロジェクトに適用 |
| Project | `./CLAUDE.md` | 特定プロジェクトのみ |

### Priority

```
Project CLAUDE.md > User CLAUDE.md
```

プロジェクトレベルの設定がユーザーレベルを上書き/補完します。

## Template Structure

### Common Sections

```markdown
# Project/User CLAUDE.md

## Overview
プロジェクト/ユーザーの説明

## Critical Rules
絶対に守るべきルール

## Code Style
コーディングスタイル

## Testing
テスト要件

## Git Workflow
Gitワークフロー

## Available Commands
利用可能なコマンド

## Agents
利用可能なエージェント
```

## Available Templates

### user-level.md

**Purpose**: ユーザーレベルのグローバル設定

**Location**: `~/.claude/CLAUDE.md`

**Contents**:
- コア哲学（Agent-First, Parallel Execution, etc.）
- モジュラールールへのリンク
- 利用可能なエージェント一覧
- 個人的な好み（コードスタイル、Git、テスト）
- 成功の定義

**Best For**:
- 個人の開発スタイルを定義
- 全プロジェクト共通のルール
- エージェント/ルールの参照

---

### project-basic.md

**Purpose**: 最小限のプロジェクト設定

**Location**: `./CLAUDE.md`

**Contents**:
- プロジェクト概要（placeholder）
- 基本的なルール（コード構成、スタイル、テスト、セキュリティ）
- ファイル構造
- 環境変数（placeholder）
- Gitワークフロー

**Best For**:
- 小規模プロジェクト
- シンプルな要件
- 素早いセットアップ

---

### project-nextjs.md

**Purpose**: Next.js + TypeScript プロジェクト

**Location**: `./CLAUDE.md`

**Contents**:
- Tech Stack（Next.js 15, TypeScript, etc.）
- ディレクトリ構造（App Router）
- Next.js ベストプラクティス
- TypeScript 規約
- テスト（Vitest, Testing Library, Playwright）
- APIレスポンス形式
- エラーハンドリング
- 環境変数

**Best For**:
- Next.js プロジェクト
- React/TypeScript 開発
- フロントエンド中心

---

### project-python.md

**Purpose**: Python プロジェクト

**Location**: `./CLAUDE.md`

**Contents**:
- Tech Stack（Python 3.11+, FastAPI/Django/Flask, etc.）
- ディレクトリ構造
- Python ベストプラクティス（type hints, docstrings, etc.）
- コードスタイル（PEP 8, Black, isort, mypy）
- テスト（pytest, pytest-cov, pytest-asyncio）
- 環境変数
- 開発コマンド

**Best For**:
- Python プロジェクト
- バックエンド API
- データ処理

---

### project-fullstack.md

**Purpose**: フルスタックプロジェクトの包括的設定

**Location**: `./CLAUDE.md`

**Contents**:
- アーキテクチャ（Onion Architecture + DDD）
- コード構成（domain, application, infrastructure, presentation）
- コードスタイル
- セキュリティチェックリスト
- テスト（Unit, Integration, E2E）
- APIレスポンス形式
- エラーハンドリング
- データベースガイドライン
- キャッシング戦略
- 環境変数
- エージェント/コマンド一覧
- Gitワークフロー
- パフォーマンスガイドライン
- モニタリング/ロギング

**Best For**:
- 大規模プロジェクト
- フルスタック開発
- チーム開発

## Customization Guide

### Adding Project-Specific Rules

```markdown
## Project-Specific Rules

### Database
- PostgreSQL を使用
- マイグレーションは Prisma で管理
- RLS を有効化

### External APIs
- Stripe で決済処理
- SendGrid でメール送信
- S3 でファイル保存
```

### Adding Custom Commands

```markdown
## Available Commands

| Command | Purpose |
|---------|---------|
| /plan | 実装計画 |
| /tdd | テスト駆動開発 |
| /deploy | デプロイ手順 |
```

### Tech Stack Specification

```markdown
## Tech Stack

- **Frontend**: Next.js 15, TypeScript, Tailwind CSS
- **Backend**: tRPC, Prisma
- **Database**: PostgreSQL (Supabase)
- **Auth**: NextAuth.js
- **Deployment**: Vercel
```

## Best Practices

### 1. Keep It Concise

長すぎる CLAUDE.md は読まれません。重要なポイントに絞る。

### 2. Use Tables

情報を整理するためにテーブルを活用:

```markdown
| Rule | Description |
|------|-------------|
| No emojis | コードに絵文字を使わない |
| Immutability | オブジェクトをミューテートしない |
```

### 3. Link to Rules

詳細は rules/ ファイルにリンク:

```markdown
詳細は `~/.claude/rules/security.md` を参照。
```

### 4. Include Examples

良い例と悪い例を示す:

```markdown
### Good
```typescript
const updated = { ...user, name: 'Jane' }
```

### Bad
```typescript
user.name = 'Jane' // Mutation!
```
```

### 5. Define Success

何をもって成功とするか明記:

```markdown
## Success Metrics

- すべてのテストがパス
- 80%+ カバレッジ
- セキュリティ脆弱性なし
- ユーザー要件を満たす
```

## Integration with Rules

CLAUDE.md からルールファイルを参照:

```markdown
## Modular Rules

詳細なガイドラインは `~/.claude/rules/` に:

| Rule | Contents |
|------|----------|
| security.md | セキュリティチェック |
| coding-style.md | コードスタイル |
| testing.md | テスト要件 |
```

## Integration with Agents

CLAUDE.md でエージェントの使用を明記:

```markdown
## When to Use Agents

| Situation | Agent |
|-----------|-------|
| コード変更後 | code-reviewer |
| 新機能計画 | planner |
| セキュリティ懸念 | security-reviewer |
```
