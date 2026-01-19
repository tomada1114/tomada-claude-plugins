# Project CLAUDE.md (Next.js)

Next.js + TypeScript プロジェクト用のテンプレート。

---

## Project Overview

Next.js 15 App Router を使用した [アプリケーション名/説明]。

**Tech Stack:**
- Next.js 15 (App Router)
- TypeScript
- [Tailwind CSS / shadcn/ui]
- [Prisma / Drizzle]
- [その他のライブラリ]

---

## Critical Rules

### 1. Code Organization

```
src/
├── app/              # Next.js App Router
│   ├── (routes)/     # Route groups
│   ├── api/          # API routes
│   └── layout.tsx
├── components/       # Reusable UI
│   ├── ui/           # Base components
│   └── features/     # Feature components
├── hooks/            # Custom React hooks
├── lib/              # Utilities
├── types/            # TypeScript definitions
└── server/           # Server-only code
```

### 2. Next.js Best Practices

- Server Components をデフォルトで使用
- 必要な場合のみ `'use client'`
- App Router の規約に従う
- Image、Link、Font を使用
- Metadata API で SEO 最適化

### 3. Code Style

- 絵文字禁止
- 不変性を維持
- console.log を残さない
- Zod で入力検証
- 適切なエラーバウンダリ

### 4. TypeScript

- `any` を避ける
- 厳格モード有効
- 型を明示的に定義
- ジェネリクスを適切に使用

### 5. Testing

- Vitest / Jest でユニットテスト
- Testing Library でコンポーネントテスト
- Playwright で E2E テスト
- 80%+ カバレッジ

---

## API Response Format

```typescript
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}
```

---

## Error Handling

```typescript
try {
  const result = await operation()
  return { success: true, data: result }
} catch (error) {
  console.error('Operation failed:', error)
  return { success: false, error: 'User-friendly message' }
}
```

---

## Environment Variables

```bash
# Required
DATABASE_URL=
NEXTAUTH_SECRET=
NEXTAUTH_URL=

# Optional
NEXT_PUBLIC_API_URL=
```

---

## Available Commands

- `/tdd` - テスト駆動開発
- `/plan` - 実装計画作成
- `/code-review` - コードレビュー
- `/build-fix` - ビルドエラー修正

---

## Git Workflow

- Conventional commits
- main に直接コミットしない
- PR にはレビュー必須
- CI がパスしてからマージ
