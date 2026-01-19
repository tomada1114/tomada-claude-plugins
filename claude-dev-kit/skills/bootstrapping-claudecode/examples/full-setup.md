# Full Setup Example

すべてのコンポーネントをインストールするフルセットアップ例。

## Components Installed

### User-Level (~/.claude/)

```
~/.claude/
├── CLAUDE.md
├── settings.json       # All hooks
├── agents/
│   ├── architect.md
│   ├── build-error-resolver.md
│   ├── code-reviewer.md
│   ├── doc-updater.md
│   ├── e2e-runner.md
│   ├── planner.md
│   ├── refactor-cleaner.md
│   ├── security-reviewer.md
│   └── tdd-guide.md
├── rules/
│   ├── agents.md
│   ├── coding-style.md
│   ├── git-workflow.md
│   ├── patterns.md
│   ├── performance.md
│   ├── security.md
│   └── testing.md
└── commands/
    ├── build-fix.md
    ├── code-review.md
    ├── e2e.md
    ├── plan.md
    ├── refactor-clean.md
    ├── tdd.md
    ├── test-coverage.md
    └── update-docs.md
```

### MCP Configuration (~/.claude.json)

```json
{
  "mcpServers": {
    "github": { ... },
    "memory": { ... },
    "sequential-thinking": { ... }
  }
}
```

### Project-Level

```
./CLAUDE.md             # project-fullstack.md テンプレート
```

## What This Provides

### Agents (9)
- **planner**: 機能実装の計画
- **architect**: システム設計
- **tdd-guide**: テスト駆動開発
- **code-reviewer**: コード品質レビュー
- **security-reviewer**: セキュリティ分析
- **build-error-resolver**: ビルドエラー修正
- **e2e-runner**: E2Eテスト生成
- **refactor-cleaner**: デッドコード削除
- **doc-updater**: ドキュメント同期

### Rules (7)
- **security**: シークレット管理、入力検証
- **coding-style**: 不変性、ファイル構成
- **testing**: TDD、80%カバレッジ
- **git-workflow**: Conventional commits
- **agents**: エージェント委譲
- **performance**: モデル選択、コンテキスト管理
- **patterns**: APIレスポンス形式

### Hooks (7)
- **PreToolUse**: 開発サーバー、git push、ドキュメント
- **PostToolUse**: Prettier、TypeScript、console.log警告
- **Stop**: console.log最終監査

### Commands (8)
- `/plan`, `/tdd`, `/code-review`, `/build-fix`
- `/e2e`, `/refactor-clean`, `/test-coverage`, `/update-docs`

### MCP Servers (3 recommended)
- **github**: PR、Issue操作
- **memory**: 永続メモリ
- **sequential-thinking**: 連鎖思考

## Installation Steps

### 1. Create Directories

```bash
mkdir -p ~/.claude/{agents,rules,commands}
```

### 2. Copy Files

```bash
# Agents
cp templates/agents/*.md ~/.claude/agents/

# Rules
cp templates/rules/*.md ~/.claude/rules/

# Commands
cp templates/commands/*.md ~/.claude/commands/

# CLAUDE.md
cp templates/claude-md/user-level.md ~/.claude/CLAUDE.md
cp templates/claude-md/project-fullstack.md ./CLAUDE.md
```

### 3. Configure Hooks

`~/.claude/settings.json` を作成:

```json
{
  "hooks": {
    "PreToolUse": [
      // pretool-dev-server.json の内容
      // pretool-git-push.json の内容
      // pretool-docs-blocker.json の内容
    ],
    "PostToolUse": [
      // posttool-prettier.json の内容
      // posttool-typescript.json の内容
      // posttool-console-warn.json の内容
    ],
    "Stop": [
      // stop-console-audit.json の内容
    ]
  }
}
```

### 4. Configure MCP

`~/.claude.json` を作成または更新:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_TOKEN_HERE"
      }
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    }
  }
}
```

## Context Window Warning

フルセットアップでは MCP に注意:

- **10個未満** のMCPを有効化
- **80ツール未満** をアクティブに
- 未使用のMCPは `disabledMcpServers` で無効化

## Verification

```bash
# Check installation
ls ~/.claude/agents/
ls ~/.claude/rules/
ls ~/.claude/commands/
cat ~/.claude/CLAUDE.md
cat ~/.claude/settings.json
cat ~/.claude.json

# Test a command
# Claude Code で /plan を実行
```

---

**これで完璧なセットアップが完了です！**
