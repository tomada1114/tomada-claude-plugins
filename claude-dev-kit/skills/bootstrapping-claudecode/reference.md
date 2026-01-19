# Claude Code Bootstrap Reference

bootstrapping-claudecode スキルの詳細ドキュメント索引。

## Reference Documents

各コンポーネントの詳細は個別のリファレンスファイルを参照してください。

| Document | Description |
|----------|-------------|
| [references/agents.md](references/agents.md) | エージェントの詳細、YAML形式、モデル選択 |
| [references/rules.md](references/rules.md) | ルールの詳細、チェックリスト、ベストプラクティス |
| [references/hooks.md](references/hooks.md) | フックの詳細、matcher構文、カスタムフック作成 |
| [references/commands.md](references/commands.md) | コマンドの詳細、使用例、カスタムコマンド作成 |
| [references/mcp.md](references/mcp.md) | MCPサーバーの詳細、設定方法、コンテキストウィンドウ管理 |
| [references/claude-md.md](references/claude-md.md) | CLAUDE.mdテンプレートの詳細、カスタマイズガイド |

---

## Quick Start

### Prerequisites

- Claude Code CLI インストール済み
- Node.js 18+ (MCP サーバー用)
- Git リポジトリ初期化済み

### Directory Structure

```
~/.claude/
├── CLAUDE.md           # グローバル指示
├── settings.json       # フック設定
├── agents/             # サブエージェント
├── rules/              # ルール
├── commands/           # コマンド
└── skills/             # スキル
```

---

## Component Summary

### Agents (9)

| Agent | Purpose | Model |
|-------|---------|-------|
| code-reviewer | コード品質レビュー | opus |
| security-reviewer | セキュリティ分析 | opus |
| architect | システム設計 | opus |
| planner | 実装計画 | opus |
| tdd-guide | TDD指導 | sonnet |
| build-error-resolver | ビルドエラー修正 | sonnet |
| e2e-runner | E2Eテスト | sonnet |
| refactor-cleaner | リファクタリング | sonnet |
| doc-updater | ドキュメント更新 | sonnet |

→ 詳細: [references/agents.md](references/agents.md)

### Rules (8)

| Rule | Focus |
|------|-------|
| security | シークレット管理、入力検証 |
| coding-style | 不変性、ファイル構成 |
| testing | TDD、80%カバレッジ |
| git-workflow | Conventional commits |
| agents | エージェント委譲 |
| performance | モデル選択、コンテキスト |
| patterns | APIレスポンス形式 |
| hooks | フックガイドライン |

→ 詳細: [references/rules.md](references/rules.md)

### Hooks (8)

| Event | Purpose |
|-------|---------|
| PreToolUse | 開発サーバーブロック、git push確認 |
| PostToolUse | Prettier、TypeScript、console.log警告 |
| Stop | console.log最終監査 |

→ 詳細: [references/hooks.md](references/hooks.md)

### Commands (9)

| Command | Purpose |
|---------|---------|
| /plan | 実装計画 |
| /tdd | テスト駆動開発 |
| /code-review | コードレビュー |
| /build-fix | ビルドエラー修正 |
| /e2e | E2Eテスト |
| /refactor-clean | リファクタリング |
| /test-coverage | カバレッジ分析 |
| /update-docs | ドキュメント更新 |
| /update-codemaps | コードマップ更新 |

→ 詳細: [references/commands.md](references/commands.md)

### MCP Servers (9)

| Server | Purpose |
|--------|---------|
| github | PR、Issue操作 |
| memory | 永続メモリ |
| sequential-thinking | 連鎖思考 |
| supabase | データベース |
| vercel | デプロイ |
| railway | デプロイ |
| cloudflare | Workers、ドキュメント |
| context7 | ライブドキュメント |
| filesystem | ファイル操作 |

→ 詳細: [references/mcp.md](references/mcp.md)

### CLAUDE.md Templates (5)

| Template | Use Case |
|----------|----------|
| user-level | グローバル設定 |
| project-basic | 最小構成 |
| project-nextjs | Next.js |
| project-python | Python |
| project-fullstack | フルスタック |

→ 詳細: [references/claude-md.md](references/claude-md.md)

---

## Context Window Management

**重要**: MCPが多すぎるとコンテキストウィンドウが縮小します。

| MCPs | Context |
|------|---------|
| 0-5 | ~200k |
| 5-10 | ~150k |
| 10+ | ~100k以下 |

**推奨**: 10個未満/プロジェクト、80ツール未満

---

## Troubleshooting

### Agents Not Activating

1. description にトリガーワードを追加
2. YAML構文を確認
3. tools が有効か確認

→ 詳細: [references/agents.md](references/agents.md#agent-activation-pattern)

### Hooks Not Firing

1. matcher 構文を確認
2. settings.json の JSON を確認
3. スクリプトを単独テスト

→ 詳細: [references/hooks.md](references/hooks.md#troubleshooting)

### MCP Not Working

1. API キーを確認
2. Node.js バージョンを確認
3. ネットワーク接続を確認

→ 詳細: [references/mcp.md](references/mcp.md#troubleshooting)

---

## Best Practices

1. **少なく始める**: 必須コンポーネントから開始
2. **段階的に追加**: 必要に応じて追加
3. **コンテキストを意識**: MCPは10個未満に
4. **テスト**: 変更後は必ず動作確認
5. **バックアップ**: 上書き前にバックアップ
