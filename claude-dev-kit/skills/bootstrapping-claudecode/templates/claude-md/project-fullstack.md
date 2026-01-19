# Project CLAUDE.md (Full-Stack)

フルスタックプロジェクト用の包括的テンプレート。

---

## Project Overview

[プロジェクトの説明]

**Tech Stack:**
- Frontend: [Next.js / React / Vue]
- Backend: [Node.js / Python / Go]
- Database: [PostgreSQL / MySQL / MongoDB]
- Cache: [Redis]
- Deployment: [Vercel / AWS / GCP]

---

## Critical Rules

### 1. Architecture

**Onion Architecture + DDD:**
```
src/
├── domain/           # Core business entities
├── application/      # Use cases, services
├── infrastructure/   # External services, DB
└── presentation/     # API, UI
```

### 2. Code Organization

- 機能/ドメインで整理
- 通常 200-400 行/ファイル、最大 800 行
- 高凝集、低結合
- 依存性逆転の原則

### 3. Code Style

- 絵文字禁止
- 不変性を維持
- console.log を残さない
- 適切なエラーハンドリング
- 入力検証必須

### 4. Security

```
[ ] ハードコードされたシークレットなし
[ ] すべてのユーザー入力を検証
[ ] パラメータ化クエリのみ
[ ] XSS 対策
[ ] CSRF 保護
[ ] 認証/認可の確認
[ ] レート制限
[ ] エラーメッセージが機密情報を漏らさない
```

### 5. Testing

- **Unit Tests**: 個別の関数、ユーティリティ
- **Integration Tests**: API エンドポイント、DB 操作
- **E2E Tests**: クリティカルなユーザーフロー
- **最低 80% カバレッジ**

---

## API Response Format

```typescript
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
    details?: unknown
  }
  meta?: {
    page?: number
    totalPages?: number
    totalCount?: number
  }
}
```

---

## Error Handling

```typescript
// Domain errors
class DomainError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details?: unknown
  ) {
    super(message)
  }
}

// Use case
try {
  const result = await useCase.execute(input)
  return { success: true, data: result }
} catch (error) {
  if (error instanceof DomainError) {
    return {
      success: false,
      error: { code: error.code, message: error.message }
    }
  }
  // Log internal errors, return generic message
  logger.error('Unexpected error', error)
  return {
    success: false,
    error: { code: 'INTERNAL_ERROR', message: 'Something went wrong' }
  }
}
```

---

## Database Guidelines

- マイグレーションを使用
- インデックスを適切に設定
- N+1 クエリを避ける
- トランザクションを使用
- RLS (Row Level Security) を検討

---

## Caching Strategy

```typescript
// Cache-aside pattern
async function getUser(id: string): Promise<User> {
  const cached = await cache.get(`user:${id}`)
  if (cached) return cached

  const user = await db.users.findUnique({ where: { id } })
  if (user) {
    await cache.set(`user:${id}`, user, { ttl: 3600 })
  }
  return user
}
```

---

## Environment Variables

```bash
# Database
DATABASE_URL=
REDIS_URL=

# Auth
JWT_SECRET=
SESSION_SECRET=

# External Services
STRIPE_SECRET_KEY=
SENDGRID_API_KEY=

# Feature Flags
ENABLE_NEW_FEATURE=false
```

---

## Available Agents

| Agent | Use When |
|-------|----------|
| planner | 新機能の計画 |
| architect | アーキテクチャ決定 |
| tdd-guide | テスト駆動開発 |
| code-reviewer | コード変更後 |
| security-reviewer | セキュリティ懸念時 |
| build-error-resolver | ビルド失敗時 |
| e2e-runner | E2E テスト作成 |

---

## Available Commands

| Command | Purpose |
|---------|---------|
| /plan | 実装計画作成 |
| /tdd | テスト駆動開発 |
| /code-review | コードレビュー |
| /build-fix | ビルドエラー修正 |
| /e2e | E2E テスト生成 |
| /refactor-clean | デッドコード削除 |

---

## Git Workflow

1. **Feature Branch**: `feature/xxx` または `fix/xxx`
2. **Conventional Commits**: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
3. **PR Process**:
   - コードレビュー必須
   - CI がパス
   - カバレッジ維持
4. **main への直接コミット禁止**

---

## Performance Guidelines

- 大きなリストには仮想化を使用
- 画像を最適化
- バンドルサイズを監視
- データベースクエリを最適化
- 適切なインデックスを設定
- キャッシュを活用

---

## Monitoring & Logging

```typescript
// Structured logging
logger.info('User created', {
  userId: user.id,
  email: user.email,
  source: 'signup'
})

// Error logging with context
logger.error('Payment failed', {
  error: error.message,
  userId,
  orderId,
  stack: error.stack
})
```
