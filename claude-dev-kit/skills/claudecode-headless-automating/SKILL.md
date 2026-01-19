---
name: claudecode-headless-automating
description: Claude Code をヘッドレスモード（非対話モード）でスクリプトから呼び出すための実装ガイド。Use PROACTIVELY when creating automation scripts, shell scripts calling claude, headless mode, non-interactive mode, batch processing with Claude, CI/CD integration, -p flag, --dangerously-skip-permissions, or building workflows that invoke Claude programmatically. Examples: <example>Context: User wants automation user: 'claudeをスクリプトから呼び出したい' assistant: 'I will use claude-code-headless skill' <commentary>Triggered by script automation request</commentary></example>
---

# Claude Code Headless Mode Guide

Claude Code を非対話モード（ヘッドレスモード）でスクリプトから呼び出すための包括的ガイド。

## When to Use This Skill

- シェルスクリプトから Claude Code を呼び出す仕組みを作るとき
- CI/CD パイプラインで Claude を実行するとき
- バッチ処理や自動化ワークフローを構築するとき
- カスタムコマンド（`/xxx`）をスクリプトから実行するとき
- Claude の出力を他のツールと連携させるとき

---

## 基本構文

```bash
claude -p "プロンプト" [オプション]
```

`-p` (`--print`) フラグが**ヘッドレスモードの鍵**。UI なしで実行し、結果を stdout に出力して終了。

---

## 主要オプション一覧

| オプション | 説明 | 例 |
|-----------|------|-----|
| `-p`, `--print` | 非対話モード（必須） | `-p "タスク"` |
| `--model <name>` | モデル指定 | `--model opus` |
| `--dangerously-skip-permissions` | 権限確認スキップ | 自動化向け |
| `--output-format <fmt>` | 出力形式 | `json`, `text`, `stream-json` |
| `--max-turns <n>` | ターン数上限 | `--max-turns 10` |
| `--verbose` | 詳細ログ | デバッグ用 |
| `--allowedTools` | 許可ツール指定 | `--allowedTools "Bash,Read"` |
| `--disallowedTools` | 禁止ツール指定 | `--disallowedTools "Write"` |
| `--append-system-prompt` | システムプロンプト追加 | カスタム指示 |
| `--continue`, `-c` | 直前の会話を継続 | セッション継続 |
| `--resume`, `-r` | 特定セッション再開 | `--resume abc123` |

### モデル選択ガイド

**注意**: サブスクリプション（Claude Max/Pro）利用時は追加費用がかからないため、品質を優先してモデルを選択する。

| モデル | 用途 | 推奨度 |
|--------|------|--------|
| `opus` | 開発・設計・熟慮が必要なタスク、品質重視のコンテンツ生成 | ★★★ 積極的に使用 |
| `sonnet` | 軽量な処理、定型作業、速度重視のタスク | ★★☆ 速度優先時 |
| `haiku` | 極めてシンプルな処理、大量バッチの軽いタスク | ★☆☆ 特殊用途 |

**原則**: 迷ったら `opus` を使う。品質の高い出力は後工程の手戻りを減らす。

---

## エラー処理パターン

### 重要な注意点

**`claude -p` は成功しても非ゼロ終了コードを返すことがある**

そのため、終了コードではなく**出力ファイルの存在**で成功判定するのが推奨。

### パターン1: ファイル存在で判定（推奨）

```bash
#!/bin/bash
EPISODE_ID="20250127_143022"
EXPECTED_OUTPUT="episodes/$EPISODE_ID/metadata/title.txt"
LOG_FILE="logs/claude.log"

# 終了コードは無視（|| true）
claude -p "/optimize-metadata $EPISODE_ID" \
    --model opus \
    --dangerously-skip-permissions \
    >> "$LOG_FILE" 2>&1 || true

# ファイル存在で成功判定
if [ ! -f "$EXPECTED_OUTPUT" ]; then
    echo "Error: Expected output not created"
    exit 1
fi

echo "Success: $EXPECTED_OUTPUT created"
```

### パターン2: JSON出力でステータス確認

```bash
#!/bin/bash
RESULT=$(claude -p "ファイルを分析して" --output-format json 2>/dev/null)

IS_ERROR=$(echo "$RESULT" | jq -r '.is_error')
RESPONSE=$(echo "$RESULT" | jq -r '.result')

if [ "$IS_ERROR" = "true" ]; then
    echo "Error occurred"
    exit 1
fi

echo "Result: $RESPONSE"
```

### パターン3: リトライ付き実行

```bash
#!/bin/bash
MAX_RETRIES=3
EXPECTED_OUTPUT="output.txt"

for i in $(seq 1 $MAX_RETRIES); do
    echo "Attempt $i/$MAX_RETRIES..."

    claude -p "/my-command" \
        --dangerously-skip-permissions \
        >> log.txt 2>&1 || true

    if [ -f "$EXPECTED_OUTPUT" ]; then
        echo "Success on attempt $i"
        break
    fi

    # Exponential backoff: 60s, 120s, 180s
    if [ $i -lt $MAX_RETRIES ]; then
        WAIT=$((60 * i))
        echo "Retrying in ${WAIT}s..."
        sleep $WAIT
    fi
done

if [ ! -f "$EXPECTED_OUTPUT" ]; then
    echo "Failed after $MAX_RETRIES attempts"
    exit 1
fi
```

---

## 出力形式

### Text（デフォルト）

```bash
claude -p "Hello" --output-format text
# → プレーンテキスト出力
```

### JSON

```bash
claude -p "Hello" --output-format json
```

```json
{
  "type": "result",
  "subtype": "success",
  "is_error": false,
  "result": "応答テキスト",
  "total_cost_usd": 0.003,
  "duration_ms": 1234,
  "num_turns": 6,
  "session_id": "abc123"
}
```

### Stream JSON（リアルタイム処理向け）

```bash
claude -p "長いタスク" --output-format stream-json
# → JSONL形式でメッセージごとに出力
```

---

## カスタムコマンドの実行

### カスタムコマンドとは

`.claude/commands/` に配置した Markdown ファイルがスラッシュコマンドになる。

```
.claude/commands/
├── create-thumbnail.md   → /create-thumbnail
├── optimize-metadata.md  → /optimize-metadata
└── my-task.md            → /my-task
```

### コマンドファイルの形式

```markdown
---
description: コマンドの説明
argument-hint: "<episode-id>"
allowed-tools: Bash, Read, Write
model: sonnet
---

# コマンド内容

エピソード $1 を処理する。
引数は $ARGUMENTS または {{$1}}, {{$2}} で参照。
```

### スクリプトからの呼び出し

```bash
# カスタムコマンドも -p で実行可能
claude -p "/create-thumbnail 20250127_143022" \
    --model opus \
    --dangerously-skip-permissions
```

---

## 実践的なワークフロー例

### 複数ステップの自動化

```bash
#!/bin/bash
set -euo pipefail

EPISODE_ID="$1"
LOG_FILE="logs/workflow_$(date +%Y%m%d_%H%M%S).log"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG_FILE"; }

# Step 1: メタデータ生成
log "Step 1: Generating metadata..."
claude -p "/optimize-metadata $EPISODE_ID" \
    --model opus \
    --dangerously-skip-permissions \
    >> "$LOG_FILE" 2>&1 || true

if [ ! -f "episodes/$EPISODE_ID/metadata/title.txt" ]; then
    log "ERROR: Metadata generation failed"
    exit 1
fi

# Step 2: サムネイル生成
log "Step 2: Creating thumbnail..."
claude -p "/create-thumbnail $EPISODE_ID" \
    --model opus \
    --dangerously-skip-permissions \
    >> "$LOG_FILE" 2>&1 || true

if [ ! -f "episodes/$EPISODE_ID/images/thumbnail.png" ]; then
    log "ERROR: Thumbnail generation failed"
    exit 1
fi

log "Workflow completed successfully!"
```

### タイムアウト付き実行

```bash
#!/bin/bash
TIMEOUT_SECS=3600  # 1時間

# バックグラウンドで実行
claude -p "/long-task" --dangerously-skip-permissions &
PID=$!

# タイムアウト監視
sleep $TIMEOUT_SECS && kill $PID 2>/dev/null &
TIMEOUT_PID=$!

# 完了待ち
wait $PID 2>/dev/null
EXIT_CODE=$?

# タイムアウトプロセスを停止
kill $TIMEOUT_PID 2>/dev/null
wait $TIMEOUT_PID 2>/dev/null

# タイムアウトチェック
if kill -0 $PID 2>/dev/null; then
    kill -9 $PID 2>/dev/null
    echo "Timeout after ${TIMEOUT_SECS}s"
    exit 1
fi
```

---

## セキュリティ考慮事項

### `--dangerously-skip-permissions` の注意

このフラグは全ての権限確認をスキップするため：

- **信頼できる環境でのみ使用**（CI/CD、自動化スクリプト）
- **入力を必ずサニタイズ**（ユーザー入力をそのまま渡さない）
- **ログを保存**して監査可能に

### より安全な代替案

```bash
# 特定のツールのみ許可
claude -p "タスク" --allowedTools "Read,Grep,Glob"

# 危険なツールを禁止
claude -p "タスク" --disallowedTools "Write,Bash"
```

---

## トラブルシューティング

### よくある問題

| 症状 | 原因 | 解決策 |
|------|------|--------|
| 非ゼロ終了コード | Claude の仕様 | `\|\| true` で無視し、ファイルで判定 |
| 出力が空 | エラー発生 | `--verbose` で詳細確認 |
| タイムアウト | 処理時間超過 | タイムアウト処理を実装 |
| 権限エラー | ツール使用拒否 | `--dangerously-skip-permissions` |

### デバッグ方法

```bash
# 詳細ログ出力
claude -p "タスク" --verbose 2>&1 | tee debug.log

# JSON で詳細情報取得
claude -p "タスク" --output-format json | jq .
```

---

## ベストプラクティス

1. **終了コードを信頼しない** → ファイル存在で判定
2. **ログを必ず保存** → `>> "$LOG_FILE" 2>&1`
3. **リトライを実装** → API エラー対策
4. **タイムアウトを設定** → 長時間処理対策
5. **迷ったら opus を使う** → 品質優先、手戻り削減
6. **`--dangerously-skip-permissions` は慎重に** → 信頼環境のみ

---

## AI Assistant Instructions

When this skill is activated:

1. **スクリプト作成時**:
   - 必ず `|| true` パターンでエラー処理を推奨
   - ファイル存在チェックによる成功判定を提案
   - 適切なログ出力を含める

2. **モデル選択時**:
   - **デフォルトは opus** を推奨（サブスク利用で追加費用なし）
   - 速度優先・定型作業 → sonnet
   - 極めて軽量なタスク → haiku（特殊用途）

3. **セキュリティ**:
   - `--dangerously-skip-permissions` 使用時は注意喚起
   - 可能なら `--allowedTools` で制限を推奨

4. **デバッグ支援**:
   - 問題発生時は `--verbose` と `--output-format json` を提案
