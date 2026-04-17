# Hook Patterns Reference

ハーネスエンジニアリングの4パターンに基づく、コピー&ペースト可能なHook設定テンプレート集。

全hookは `.claude/settings.json` または `.claude/settings.local.json` に settings-based hooks として記述する。

## 1. Safety Gates (PreToolUse)

### 1-1. リンター設定保護

Agentがリンターエラーに直面した際、コードではなくリンター設定を変更してエラーを消す行為を防止する。

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'FILE=$(jq -r \".tool_input.file_path // .tool_input.path\" <<< \"$(cat)\"); PROTECTED=\".eslintrc eslint.config biome.json biome.jsonc oxlint.json pyproject.toml ruff.toml .prettierrc tsconfig.json lefthook.yml .golangci.yml Cargo.toml clippy.toml rustfmt.toml .swiftlint.yml .pre-commit-config.yaml\"; for p in $PROTECTED; do case \"$FILE\" in *$p*) echo \"BLOCKED: $FILE is a protected config file. Fix the code, not the linter config.\" >&2; exit 2;; esac; done'"
          }
        ]
      }
    ]
  }
}
```

WHY: Agentはリンターエラーを回避するために設定を緩める傾向がある。設定保護により「コードを直す」以外の選択肢を構造的に排除する。

### 1-2. 破壊的コマンドブロック

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'CMD=$(jq -r .tool_input.command <<< \"$(cat)\"); case \"$CMD\" in *\"rm -rf /\"*|*\"rm -rf ~\"*|*\"drop table\"*|*\"drop database\"*|*\"truncate table\"*) echo \"BLOCKED: Destructive command detected: $CMD\" >&2; exit 2;; esac'"
          }
        ]
      }
    ]
  }
}
```

### 1-3. 機密ファイル編集禁止

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'FILE=$(jq -r \".tool_input.file_path // .tool_input.path\" <<< \"$(cat)\"); case \"$FILE\" in *.env|*.env.*|*credentials*|*secrets*|*.pem|*.key) echo \"BLOCKED: $FILE is a sensitive file. Do not edit secrets directly.\" >&2; exit 2;; esac'"
          }
        ]
      }
    ]
  }
}
```

### 1-4. git commit --no-verify 禁止

settings.json の deny リストに追加:

```json
{
  "permissions": {
    "deny": [
      "Bash(git commit --no-verify*)",
      "Bash(git commit * --no-verify*)"
    ]
  }
}
```

WHY: Agentにプリコミットフックをバイパスさせない。人間には `--no-verify` の柔軟性を残しつつ、Agentには厳格性を保つ。

## 2. Quality Loops (PostToolUse)

### 2-1. TypeScript/JavaScript 自動リント+フォーマット

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/post-ts-lint.sh"
          }
        ]
      }
    ]
  }
}
```

`.claude/hooks/post-ts-lint.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
file="$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<< "$input")"

case "$file" in
  *.ts|*.tsx|*.js|*.jsx) ;;
  *) exit 0 ;;
esac

# Phase 1: 自動修正（サイレント）
npx biome format --write "$file" >/dev/null 2>&1 || true
npx oxlint --fix "$file" >/dev/null 2>&1 || true

# Phase 2: 残った違反をAgent にフィードバック
diag="$(npx oxlint "$file" 2>&1 | head -20)"

if [ -n "$diag" ]; then
  jq -Rn --arg msg "$diag" '{
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: $msg
    }
  }'
fi
```

**Biome版（リント+フォーマット統合）:**

`.claude/hooks/post-biome.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
file="$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<< "$input")"

case "$file" in
  *.ts|*.tsx|*.js|*.jsx|*.json|*.jsonc) ;;
  *) exit 0 ;;
esac

# 自動修正
npx biome check --write "$file" >/dev/null 2>&1 || true

# 残りの違反
diag="$(npx biome check "$file" 2>&1 | head -20)"

if [ -n "$diag" ]; then
  jq -Rn --arg msg "$diag" '{
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: $msg
    }
  }'
fi
```

### 2-2. Python 自動リント+フォーマット

`.claude/hooks/post-python-lint.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
file="$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<< "$input")"

case "$file" in
  *.py) ;;
  *) exit 0 ;;
esac

# Phase 1: 自動修正
ruff format "$file" >/dev/null 2>&1 || true
ruff check --fix "$file" >/dev/null 2>&1 || true

# Phase 2: 残りの違反
diag="$(ruff check "$file" 2>&1 | head -20)"

if [ -n "$diag" ]; then
  jq -Rn --arg msg "$diag" '{
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: $msg
    }
  }'
fi
```

### 2-3. Go 自動リント+フォーマット

`.claude/hooks/post-go-lint.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
file="$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<< "$input")"

case "$file" in
  *.go) ;;
  *) exit 0 ;;
esac

gofmt -w "$file" >/dev/null 2>&1 || true

diag="$(golangci-lint run "$file" 2>&1 | head -20)"

if [ -n "$diag" ]; then
  jq -Rn --arg msg "$diag" '{
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: $msg
    }
  }'
fi
```

### 2-4. Rust 自動リント+フォーマット

`.claude/hooks/post-rust-lint.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
file="$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<< "$input")"

case "$file" in
  *.rs) ;;
  *) exit 0 ;;
esac

rustfmt "$file" >/dev/null 2>&1 || true

diag="$(cargo clippy --message-format=short 2>&1 | grep "$file" | head -20)"

if [ -n "$diag" ]; then
  jq -Rn --arg msg "$diag" '{
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: $msg
    }
  }'
fi
```

## 3. Completion Gates (Stop)

### 3-1. テスト実行による完了検証

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/stop-test-gate.sh"
          }
        ]
      }
    ]
  }
}
```

`.claude/hooks/stop-test-gate.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

# 無限ループ防止
if [ "${STOP_HOOK_ACTIVE:-}" = "1" ]; then
  exit 0
fi
export STOP_HOOK_ACTIVE=1

# プロジェクトタイプに応じたテスト実行
if [ -f "package.json" ]; then
  npm test 2>&1 | tail -30
elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
  python -m pytest --tb=short 2>&1 | tail -30
elif [ -f "go.mod" ]; then
  go test ./... 2>&1 | tail -30
elif [ -f "Cargo.toml" ]; then
  cargo test 2>&1 | tail -30
fi
```

WHY: Agentは機能を「完了」と宣言する傾向があるが、テストを通していないことが多い。Stop hookでテスト実行を強制し、パスするまで完了させない。

### 3-2. CLI アプリ用テスト (bats)

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'if [ -f ./test/cli.bats ]; then bats ./test/cli.bats 2>&1 | tail -20; fi'"
          }
        ]
      }
    ]
  }
}
```

### 3-3. アニメーション関連変更の検出

CSS/アニメーション関連ファイルの変更時のみテスト実行:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'git diff --name-only HEAD | grep -qE \"\\.(css|scss|less)$|animation|transition|motion|framer\" && npx playwright test --grep @animation --reporter=line 2>&1 | tail -30 || echo \"No animation-related changes, skipping.\"'"
          }
        ]
      }
    ]
  }
}
```

## 4. Observability

### 4-1. プロンプトログ

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'cat >> .claude/logs/tool-usage.jsonl <<< \"$(jq -c \"{timestamp: now | todate, tool: .tool_name, input_keys: (.tool_input | keys)}\" <<< \"$(cat)\")\"'"
          }
        ]
      }
    ]
  }
}
```

### 4-2. PreCompact での重要情報保護

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'echo \"IMPORTANT: Before compaction, ensure critical task context and decisions are preserved in git commits or task files.\"'"
          }
        ]
      }
    ]
  }
}
```

## フィードバック JSON フォーマット

PostToolUse hookからAgentへフィードバックを返す際は、通常stdoutではなく `hookSpecificOutput.additionalContext` を含むJSONで返す:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "lint errors or diagnostics here"
  }
}
```

この形式でないと、Agentはhookの出力を適切に解釈できない場合がある。
