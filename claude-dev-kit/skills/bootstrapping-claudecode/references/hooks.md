# Hook Templates Reference

フックの詳細リファレンス。

## Hook JSON Format

```json
{
  "matcher": "tool == \"ToolName\" && tool_input.param matches \"pattern\"",
  "hooks": [{
    "type": "command",
    "command": "#!/bin/bash\n..."
  }],
  "description": "What this hook does"
}
```

## Matcher Syntax

### Basic Matchers

```javascript
// Tool name
tool == "Edit"
tool == "Bash"
tool == "Write"

// Tool input
tool_input.file_path matches "\\.ts$"
tool_input.command matches "npm"

// Wildcard
*
```

### Combining Matchers

```javascript
// AND
tool == "Edit" && tool_input.file_path matches "\\.ts$"

// OR
tool == "Edit" || tool == "Write"

// NOT
!(tool_input.file_path matches "README\\.md")
```

### Regex Patterns

```javascript
// File extensions
"\\.ts$"
"\\.(ts|tsx|js|jsx)$"

// Commands
"(npm|pnpm|yarn) (install|test)"
"git push"

// Paths
"README\\.md|CLAUDE\\.md"
```

## Hook Events

### PreToolUse

**Timing**: ツール実行前

**Use Cases**:
- ブロック/拒否
- 警告/リマインダー
- 検証

**Exit Codes**:
- `exit 0`: 続行
- `exit 1`: ブロック（ツール実行しない）

---

### PostToolUse

**Timing**: ツール実行後

**Use Cases**:
- 自動フォーマット
- 検証/チェック
- ログ記録

**Note**: exit code は無視される（ツールは既に実行済み）

---

### Stop

**Timing**: セッション終了時

**Use Cases**:
- 最終検証
- クリーンアップ
- サマリー出力

---

## Available Hooks

### PreToolUse Hooks

#### pretool-dev-server.json

**Purpose**: tmux外での開発サーバー起動をブロック

**Matcher**:
```javascript
tool == "Bash" && tool_input.command matches "(npm run dev|pnpm( run)? dev|yarn dev|bun run dev)"
```

**Behavior**: exit 1 でブロック、tmuxコマンドを提案

---

#### pretool-long-running.json

**Purpose**: 長時間コマンドにtmux使用を推奨

**Matcher**:
```javascript
tool == "Bash" && tool_input.command matches "(npm (install|test)|pnpm (install|test)|cargo build|make|docker|pytest|vitest|playwright)"
```

**Behavior**: 警告を表示、続行

---

#### pretool-git-push.json

**Purpose**: git push前にレビュー確認

**Matcher**:
```javascript
tool == "Bash" && tool_input.command matches "git push"
```

**Behavior**: Enter待機、エディタ起動オプション

---

#### pretool-docs-blocker.json

**Purpose**: 不要な.mdファイル作成をブロック

**Matcher**:
```javascript
tool == "Write" && tool_input.file_path matches "\\.(md|txt)$" && !(tool_input.file_path matches "README\\.md|CLAUDE\\.md|AGENTS\\.md|CONTRIBUTING\\.md")
```

**Behavior**: exit 1 でブロック

---

### PostToolUse Hooks

#### posttool-prettier.json

**Purpose**: JS/TSファイルを自動フォーマット

**Matcher**:
```javascript
tool == "Edit" && tool_input.file_path matches "\\.(ts|tsx|js|jsx)$"
```

**Behavior**: `prettier --write` を実行

---

#### posttool-typescript.json

**Purpose**: TypeScriptの型チェック

**Matcher**:
```javascript
tool == "Edit" && tool_input.file_path matches "\\.(ts|tsx)$"
```

**Behavior**: `tsc --noEmit` を実行、エラーを表示

---

#### posttool-console-warn.json

**Purpose**: console.log を警告

**Matcher**:
```javascript
tool == "Edit" && tool_input.file_path matches "\\.(ts|tsx|js|jsx)$"
```

**Behavior**: console.log を検出したら警告

---

### Stop Hooks

#### stop-console-audit.json

**Purpose**: 変更ファイルのconsole.log最終監査

**Matcher**:
```javascript
*
```

**Behavior**: git diff で変更ファイルを取得、console.log をチェック

---

## Installation

`~/.claude/settings.json` に追加:

```json
{
  "hooks": {
    "PreToolUse": [
      { /* pretool-dev-server.json の内容 */ },
      { /* pretool-git-push.json の内容 */ }
    ],
    "PostToolUse": [
      { /* posttool-prettier.json の内容 */ },
      { /* posttool-typescript.json の内容 */ }
    ],
    "Stop": [
      { /* stop-console-audit.json の内容 */ }
    ]
  }
}
```

## Creating Custom Hooks

### Example: Python Black Formatter

```json
{
  "matcher": "tool == \"Edit\" && tool_input.file_path matches \"\\.py$\"",
  "hooks": [
    {
      "type": "command",
      "command": "#!/bin/bash\ninput=$(cat)\nfile_path=$(echo \"$input\" | jq -r '.tool_input.file_path // \"\"')\nif [ -n \"$file_path\" ] && [ -f \"$file_path\" ]; then\n  black \"$file_path\" 2>&1\nfi\necho \"$input\""
    }
  ],
  "description": "Auto-format Python files with Black"
}
```

### Example: Lint Check

```json
{
  "matcher": "tool == \"Edit\" && tool_input.file_path matches \"\\.(ts|tsx)$\"",
  "hooks": [
    {
      "type": "command",
      "command": "#!/bin/bash\ninput=$(cat)\nfile_path=$(echo \"$input\" | jq -r '.tool_input.file_path // \"\"')\nif [ -n \"$file_path\" ]; then\n  eslint \"$file_path\" --max-warnings 0 2>&1 | head -10 >&2\nfi\necho \"$input\""
    }
  ],
  "description": "Run ESLint after editing TypeScript files"
}
```

## Best Practices

1. **高速に実行**: フックは毎回実行されるため高速であること
2. **明確なメッセージ**: `[Hook]` プレフィックスで識別しやすく
3. **必要最小限**: 本当に必要なフックだけを有効化
4. **エラーハンドリング**: スクリプトが失敗してもクラッシュしないように
5. **stdin/stdoutの処理**: 入力を読み、処理し、出力すること

## Debugging

フックが動作しない場合:

1. matcher の構文を確認
2. settings.json の JSON 形式を確認
3. スクリプトを単独でテスト
4. `echo` でデバッグ出力
