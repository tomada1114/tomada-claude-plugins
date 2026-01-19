# Project CLAUDE.md (Basic)

プロジェクトルートに配置する最小構成のテンプレート。

---

## Project Overview

[プロジェクトの簡単な説明 - 目的、技術スタック]

---

## Critical Rules

### 1. Code Organization

- 大きなファイルより小さなファイルを多く
- 高凝集、低結合
- 通常 200-400 行、最大 800 行/ファイル
- 型ではなく機能/ドメインで整理

### 2. Code Style

- コードやコメントに絵文字を使用しない
- 常に不変性 - オブジェクトや配列をミューテートしない
- 本番コードに console.log を残さない
- try/catch で適切なエラーハンドリング

### 3. Testing

- TDD: テストを先に書く
- 最低 80% カバレッジ
- ユーティリティには Unit tests
- API には Integration tests
- クリティカルフローには E2E tests

### 4. Security

- ハードコードされたシークレット禁止
- 機密データには環境変数を使用
- すべてのユーザー入力を検証
- パラメータ化クエリのみ

---

## File Structure

```
src/
├── components/       # UIコンポーネント
├── lib/              # ユーティリティ
├── types/            # 型定義
└── ...
```

---

## Environment Variables

```bash
# Required
# DATABASE_URL=
# API_KEY=

# Optional
# DEBUG=false
```

---

## Git Workflow

- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
- main/master に直接コミットしない
- PR にはレビューが必要
- マージ前にすべてのテストがパスすること
