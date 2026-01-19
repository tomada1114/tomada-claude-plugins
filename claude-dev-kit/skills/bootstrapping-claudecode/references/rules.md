# Rule Templates Reference

ルールの詳細リファレンス。

## Rule File Format

```markdown
# Rule Name

## Critical Section

Important guidelines...

## Examples

### Good
```code```

### Bad
```code```

## Checklist
- [ ] Verification item
```

## Available Rules

### security.md

**Purpose**: セキュリティのベストプラクティス

**Key Points**:
- ハードコードされたシークレットの禁止
- 入力検証の要件
- SQLインジェクション対策
- XSS対策

**Pre-Commit Checklist**:
```markdown
- [ ] ハードコードされたシークレットがない
- [ ] すべてのユーザー入力が検証されている
- [ ] パラメータ化クエリを使用
- [ ] HTMLがサニタイズされている
- [ ] CSRF保護が有効
- [ ] 認証/認可が確認されている
- [ ] レート制限が設定されている
- [ ] エラーメッセージが機密情報を漏らさない
```

**Secret Management**:
```typescript
// NEVER
const apiKey = "sk-proj-xxxxx"

// ALWAYS
const apiKey = process.env.OPENAI_API_KEY

if (!apiKey) {
  throw new Error('OPENAI_API_KEY not configured')
}
```

---

### coding-style.md

**Purpose**: コードスタイルと品質

**Key Points**:
- 不変性の維持
- ファイルサイズの制限 (200-400行、最大800行)
- 適切なエラーハンドリング
- 明確な命名

**Immutability Pattern**:
```typescript
// Bad: Mutation
const user = { name: 'John' }
user.name = 'Jane'

// Good: Immutability
const user = { name: 'John' }
const updatedUser = { ...user, name: 'Jane' }
```

**Error Handling**:
```typescript
// Bad: Silent failure
try {
  await operation()
} catch (e) {
  // ignore
}

// Good: Proper handling
try {
  await operation()
} catch (error) {
  logger.error('Operation failed', { error })
  throw new AppError('OPERATION_FAILED', 'User-friendly message')
}
```

---

### testing.md

**Purpose**: テスト要件とTDDワークフロー

**Key Points**:
- TDD: テストを先に書く
- 最低80%カバレッジ
- Unit / Integration / E2E の使い分け

**Test Types**:

| Type | Purpose | Coverage |
|------|---------|----------|
| Unit | 個別の関数、ユーティリティ | 80%+ |
| Integration | API、DB操作 | Critical paths |
| E2E | ユーザーフロー | Happy paths |

**TDD Workflow**:
```
RED → GREEN → REFACTOR → REPEAT

RED:      失敗するテストを書く
GREEN:    テストを通す最小限のコード
REFACTOR: テストを維持しながら改善
REPEAT:   次の機能/シナリオ
```

---

### git-workflow.md

**Purpose**: Gitワークフローとコミット規約

**Conventional Commits**:
```
feat:     新機能
fix:      バグ修正
docs:     ドキュメント
test:     テスト
refactor: リファクタリング
chore:    その他
```

**Branch Strategy**:
```
main          # Production-ready
  └── feature/xxx   # New features
  └── fix/xxx       # Bug fixes
  └── refactor/xxx  # Refactoring
```

**PR Checklist**:
- [ ] テストがパス
- [ ] カバレッジが維持されている
- [ ] コードレビュー完了
- [ ] コンフリクトなし

---

### agents.md

**Purpose**: エージェントの使用ガイドライン

**When to Delegate**:

| Situation | Agent |
|-----------|-------|
| コード変更後 | code-reviewer |
| セキュリティ懸念 | security-reviewer |
| 新機能計画 | planner |
| アーキテクチャ決定 | architect |
| テスト作成 | tdd-guide |
| ビルドエラー | build-error-resolver |
| E2Eテスト | e2e-runner |
| コードクリーンアップ | refactor-cleaner |

**Parallel Execution**:
```
複数の独立したタスクがある場合、Task tool で
並列にエージェントを起動可能。
```

---

### performance.md

**Purpose**: パフォーマンスとコンテキスト管理

**Model Selection**:

| Model | Use Case |
|-------|----------|
| Haiku | 軽量、頻繁な呼び出し |
| Sonnet | 通常の開発作業 |
| Opus | 複雑な推論 |

**Context Window Management**:
- MCP は 10個未満/プロジェクト
- 80ツール未満をアクティブに
- 未使用のMCPは無効化

**When to Avoid Heavy Tasks**:
- コンテキストの残り20%では大規模リファクタリングを避ける
- 複数ファイルにまたがる機能実装も避ける

---

### patterns.md

**Purpose**: 共通パターンとベストプラクティス

**API Response Format**:
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
  }
}
```

**Repository Pattern**:
```typescript
interface UserRepository {
  findById(id: string): Promise<User | null>
  findAll(filter: UserFilter): Promise<User[]>
  create(data: CreateUserInput): Promise<User>
  update(id: string, data: UpdateUserInput): Promise<User>
  delete(id: string): Promise<void>
}
```

---

### hooks.md (meta)

**Purpose**: フックの使用ガイドライン

**Hook Types**:
- PreToolUse: ツール実行前
- PostToolUse: ツール実行後
- Stop: セッション終了時

**Best Practices**:
- 高速に実行できること
- 明確なエラーメッセージ
- 必要最小限のロジック

## Rule Priority

| Priority | Rules |
|----------|-------|
| 必須 | security, coding-style |
| 推奨 | testing, git-workflow |
| オプション | agents, performance, patterns |
