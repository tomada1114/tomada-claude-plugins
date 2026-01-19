---
name: bootstrapping-claudecode
description: Claude Code ベストプラクティスの対話形式セットアップウィザード。Use PROACTIVELY when setting up new projects, configuring Claude Code, adding agents/rules/hooks, or when user mentions "bootstrap", "setup claude", "configure claude code", "add agents", "add rules", "セットアップ", "初期設定", "ブートストラップ". Examples: <example>Context: User wants to set up Claude Code user: 'Claude Codeをセットアップしたい' assistant: 'I will use bootstrapping-claudecode skill' <commentary>Triggered by setup request</commentary></example>
---

# Claude Code Bootstrap Wizard

[everything-claude-code](https://github.com/affaan-m/everything-claude-code) リポジトリのベストプラクティスを参考に、対話形式でセットアップするウィザードです。

> **Acknowledgment**: このスキルは [Affaan M](https://github.com/affaan-m) による [everything-claude-code](https://github.com/affaan-m/everything-claude-code) を大いに参考にしています。オリジナルのリポジトリは Claude Code のベストプラクティス集として非常に優れています。

## Quick Start

以下のいずれかを伝えてください:
- **"フルセットアップ"** - 全コンポーネントをインストール
- **"エージェントだけ"** - サブエージェントのみ
- **"最小構成"** - CLAUDE.md + 必須ルールのみ
- **"カスタム"** - 必要なものだけ選択

## Workflow

### Phase 0: Target Selection (FIRST STEP)

**最初に必ず作成場所を確認する**

AskUserQuestion で確認:
- **プロジェクトレベル（推奨）** - `./.claude/` に作成。このプロジェクト専用の設定
- **ユーザーレベル** - `~/.claude/` に作成。全プロジェクトで共有

```
TARGET_DIR = プロジェクト選択時 → "./.claude"
TARGET_DIR = ユーザー選択時 → "~/.claude"
```

⚠️ **注意**: ユーザーレベルは全プロジェクトに影響するため、汎用的な設定のみ推奨

### Phase 1: Environment Detection

既存の設定を確認:
1. `~/.claude/` ディレクトリ構造
2. `~/.claude/CLAUDE.md` (ユーザーレベル設定)
3. `./CLAUDE.md` (プロジェクトレベル設定)
4. `~/.claude/agents/`, `rules/`, `commands/`, `skills/`
5. `~/.claude/settings.json` (hooks)
6. `~/.claude.json` (MCP servers)

プロジェクトタイプを検出:
- package.json → Node.js/TypeScript
- pyproject.toml/requirements.txt → Python
- go.mod → Go
- Cargo.toml → Rust

### Phase 2: Interactive Selection

AskUserQuestion で各カテゴリを選択。

**Q1: スコープ選択**
- フルセットアップ（推奨）
- Agents のみ
- Rules のみ
- Hooks のみ
- Commands のみ
- MCP servers のみ
- CLAUDE.md templates のみ
- カスタム選択

**Q2-Q7: コンポーネント選択** (スコープに応じて)

### Phase 3: Conflict Resolution

既存ファイルが見つかった場合:
- **Skip** - 既存を維持
- **Backup** - バックアップして置き換え
- **Merge** - 不足分のみ追加
- **Interactive** - ファイルごとに確認

### Phase 4: Installation

1. ディレクトリ作成
2. 選択したテンプレートをコピー
3. settings.json にフックを設定
4. ~/.claude.json に MCP を設定

### Phase 5: Verification

1. インストールしたコンポーネント一覧
2. クイック使用ガイド
3. 次のステップ

---

## Available Components

### Agents (9)

| Agent | Purpose | Model | Color |
|-------|---------|-------|-------|
| code-reviewer | コード品質・セキュリティレビュー | opus | red |
| security-reviewer | 脆弱性分析 | opus | red |
| architect | システム設計 | opus | purple |
| planner | 実装計画 | opus | blue |
| tdd-guide | テスト駆動開発 | sonnet | green |
| build-error-resolver | ビルドエラー修正 | sonnet | yellow |
| e2e-runner | Playwright E2Eテスト | sonnet | green |
| refactor-cleaner | デッドコード削除 | sonnet | gray |
| doc-updater | ドキュメント同期 | sonnet | blue |

**Note**: 全エージェントに `<example>` タグを追加済み。アクティベート率向上のため。

### Rules (7)

| Rule | Focus |
|------|-------|
| security | シークレット管理、入力検証 |
| coding-style | 不変性、ファイル構成 |
| testing | TDD、80%カバレッジ |
| git-workflow | Conventional commits、PR |
| agents | サブエージェント委譲 |
| performance | モデル選択、コンテキスト管理 |
| patterns | APIレスポンス形式 |

### Hooks (7)

| Event | Hook | Purpose |
|-------|------|---------|
| PreToolUse | dev-server | tmux外の開発サーバーをブロック |
| PreToolUse | git-push | push前にレビュー確認 |
| PreToolUse | docs-blocker | 不要な.mdファイル作成をブロック |
| PostToolUse | prettier | JS/TSを自動フォーマット |
| PostToolUse | typescript | 編集後にTypeScriptチェック |
| PostToolUse | console-warn | console.logを警告 |
| Stop | console-audit | 最終console.log監査 |

### Commands (9)

| Command | Purpose | Allowed Tools |
|---------|---------|---------------|
| /plan | 実装計画作成 | Read, Grep, Glob |
| /tdd | テスト駆動開発 | Read, Write, Edit, Bash, Grep, Glob |
| /code-review | 品質レビュー | Read, Grep, Glob, Bash |
| /build-fix | ビルドエラー修正 | Read, Write, Edit, Bash, Grep, Glob |
| /e2e | E2Eテスト生成 | Read, Write, Edit, Bash, Grep, Glob |
| /refactor-clean | デッドコード削除 | Read, Write, Edit, Bash, Grep, Glob |
| /test-coverage | カバレッジ分析 | Read, Write, Edit, Bash, Grep, Glob |
| /update-docs | ドキュメント同期 | Read, Write, Edit, Grep, Glob |
| /update-codemaps | コードマップ更新 | Read, Write, Edit, Bash, Grep, Glob |

**Note**: 全コマンドに `allowed-tools` フィールドを追加済み。許可確認の回数を削減。

### MCP Servers (9)

| Server | Purpose |
|--------|---------|
| github | PR、Issue、リポジトリ操作 |
| memory | 永続メモリ |
| sequential-thinking | 連鎖思考 |
| supabase | データベース操作 |
| vercel | Vercelデプロイ |
| railway | Railwayデプロイ |
| cloudflare | Workers、ドキュメント |
| context7 | ライブドキュメント検索 |
| filesystem | ファイル操作 |

### CLAUDE.md Templates (5)

| Template | Use Case |
|----------|----------|
| user-level | ~/.claude/CLAUDE.md グローバル設定 |
| project-basic | 最小プロジェクト設定 |
| project-nextjs | Next.js プロジェクト |
| project-python | Python プロジェクト |
| project-fullstack | フルスタック包括設定 |

---

## Context Window Warning

MCP は慎重に選択してください:
- **10個未満**/プロジェクトを推奨
- **80ツール未満**をアクティブに
- 未使用の MCP は `disabledMcpServers` で無効化

---

## Detailed Documentation

詳細は [reference.md](reference.md) または個別のリファレンスを参照:

| Document | Description |
|----------|-------------|
| [reference.md](reference.md) | 索引とクイックスタート |
| [references/agents.md](references/agents.md) | エージェントの詳細 |
| [references/rules.md](references/rules.md) | ルールの詳細 |
| [references/hooks.md](references/hooks.md) | フックの詳細 |
| [references/commands.md](references/commands.md) | コマンドの詳細 |
| [references/mcp.md](references/mcp.md) | MCPサーバーの詳細 |
| [references/claude-md.md](references/claude-md.md) | CLAUDE.mdテンプレートの詳細 |

---

## AI Assistant Instructions

このスキルがアクティブになったとき:

### 0. Ask Target Location (MUST BE FIRST)

**最初に必ず作成場所を確認する**

AskUserQuestion で確認:
```
質問: 設定をどこに作成しますか？
- プロジェクトレベル（推奨）: ./.claude/ に作成。このプロジェクト専用
- ユーザーレベル: ~/.claude/ に作成。全プロジェクトで共有（注意が必要）
```

選択結果を `TARGET_DIR` として保持:
- プロジェクト → `TARGET_DIR="./.claude"`
- ユーザー → `TARGET_DIR="$HOME/.claude"`

### 1. Environment Detection

```bash
# 選択された場所の既存設定を確認
ls -la ${TARGET_DIR}/ 2>/dev/null || echo "${TARGET_DIR}/ does not exist"
ls -la ${TARGET_DIR}/agents/ 2>/dev/null || echo "No agents directory"
ls -la ${TARGET_DIR}/rules/ 2>/dev/null || echo "No rules directory"
ls -la ${TARGET_DIR}/commands/ 2>/dev/null || echo "No commands directory"

# settings.json と MCP は常にユーザーレベル
cat ~/.claude/settings.json 2>/dev/null || echo "No settings.json"
cat ~/.claude.json 2>/dev/null || echo "No ~/.claude.json"
```

### 2. Ask Scope Question

AskUserQuestion で以下を確認:
- スコープ（フル/部分/カスタム）
- 各カテゴリの選択肢

### 3. Handle Conflicts

既存ファイルがある場合:
1. 一覧を表示
2. 対処方法を確認（Skip/Backup/Merge/Interactive）

### 4. Install Components

選択されたコンポーネントを **TARGET_DIR** にインストール:

**Agents**:
```bash
mkdir -p ${TARGET_DIR}/agents
cp ~/.claude/skills/bootstrapping-claudecode/templates/agents/<name>.md ${TARGET_DIR}/agents/
```

**Rules**:
```bash
mkdir -p ${TARGET_DIR}/rules
cp ~/.claude/skills/bootstrapping-claudecode/templates/rules/<name>.md ${TARGET_DIR}/rules/
```

**Commands**:
```bash
mkdir -p ${TARGET_DIR}/commands
cp ~/.claude/skills/bootstrapping-claudecode/templates/commands/<name>.md ${TARGET_DIR}/commands/
```

**Hooks**: `~/.claude/settings.json` に追加（常にユーザーレベル）
**MCP**: `~/.claude.json` に追加（常にユーザーレベル）

### 5. Verification

インストール結果を表示:
```bash
echo "=== Installed to ${TARGET_DIR} ==="
ls ${TARGET_DIR}/agents/ 2>/dev/null
ls ${TARGET_DIR}/rules/ 2>/dev/null
ls ${TARGET_DIR}/commands/ 2>/dev/null
```

### Important Rules

1. **最初に作成場所を確認** - Phase 0 を必ず最初に実行
2. **常に AskUserQuestion を使用** - 大きな仮定をしない
3. **既存設定を尊重** - 上書き前に確認
4. **段階的に進める** - 一度に全部やらない
5. **結果を報告** - 何をインストールしたか明示
6. **次のステップを提案** - 使い方をガイド

### Never

- **作成場所を確認せずにインストールしない** - 必ず最初に確認
- ユーザー確認なしにファイルを上書きしない
- MCP の API キーを自動設定しない（プレースホルダーのみ）
- 全てを一度にインストールすることを強制しない
- ユーザーレベル（~/.claude/）をデフォルトとして扱わない
