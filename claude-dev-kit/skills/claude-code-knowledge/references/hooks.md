# フックによる自動化（Hooks）

## フックとは

フックは、Claude Code のライフサイクルの特定の時点で自動的に実行されるシェルコマンドです。LLM の判断に依存せず、確実に特定のアクションを実行できます。

## CLAUDE.mdとの違い：決定論的 vs 確率論的

Hooksの最大の特徴は、**LLMの判断に依存しない**点です。

- **CLAUDE.md**: 「ファイル編集後は`npm run format`を実行して」と書いても、Claudeは**確率論的**に判断するため、コンテキストによって実行される時とされない時がある
- **Hooks**: 設定した処理は**決定論的**に実行される。PostToolUseフックに`npm run format`を設定しておけば、ファイル編集のたびに必ず実行される

**使い分けの目安:**
- **CLAUDE.md**: Claudeへの指示や文脈情報を伝える
- **Hooks**: 毎回確実に実行したい処理に使う

## フックの主な用途

- **自動フォーマット**: ファイル編集後に自動整形
- **通知**: 特定のイベント発生時に通知
- **検証**: コードの品質チェック
- **ログ記録**: コマンド実行の記録
- **カスタム権限**: 特定の操作をブロック

## フックの設定場所

フックの設定は、以下の3箇所に記述できます。スコープとGit管理の有無が異なります。

| 設定ファイル | スコープ | Git管理 |
|-------------|---------|:-------:|
| `.claude/settings.json` | プロジェクト | ○（推奨） |
| `.claude/settings.local.json` | プロジェクト（ローカル） | ×（.gitignore推奨） |
| `~/.claude/settings.json` | ユーザー全体 | - |

- チームで共有したいフック（自動フォーマットなど）→ `.claude/settings.json`
- 個人の環境に依存する設定（通知設定など）→ `.claude/settings.local.json`

## フックの管理

```bash
/hooks
```

インタラクティブメニューで:
- フックイベント選択
- マッチャー追加
- コマンド追加
- 設定対象選択（User settings / Project settings）
- 設定の保存

## 全フックイベント（10種類）

| イベント | 説明 | マッチャー |
|---------|------|-----------|
| **PreToolUse** | ツール実行前に実行（ブロック可能） | ○ |
| **PermissionRequest** | 権限ダイアログ表示時に実行 | ○ |
| **PostToolUse** | ツール実行完了後に実行 | ○ |
| **Notification** | 通知送信時に実行 | ○ |
| **UserPromptSubmit** | ユーザープロンプト送信時に実行 | × |
| **Stop** | メインエージェント完了時に実行 | × |
| **SubagentStop** | サブエージェント完了時に実行 | × |
| **PreCompact** | コンパクト実行前に実行 | × |
| **SessionStart** | セッション開始/再開時に実行 | × |
| **SessionEnd** | セッション終了時に実行 | × |

**⚠️ 注意**: PreToolUse/PostToolUseフックは**メインエージェントのみ**で発火します。サブエージェント（Taskツールで起動されるエージェント）がツールを実行しても、これらのフックは発火しません。サブエージェント完了時に処理を行いたい場合は、SubagentStopフックを使用してください。

**よく使われる4つのフック:**
- **PreToolUse**: 事前チェック（特定操作のブロック）
- **PostToolUse**: 自動フォーマット
- **Stop**: 完了通知
- **SessionStart**: 環境初期化（npm install等）

## 実用例

### 1. 自動コードフォーマット

**設定場所**: `.claude/settings.json` または `~/.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "prettier --write \"**/*.{js,jsx,ts,tsx,json,css}\""
          }
        ]
      }
    ]
  }
}
```

ファイル編集後、自動的に Prettier で整形されます。

### 2. Git コミット前のチェック

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit.*)",
        "hooks": [
          {
            "type": "command",
            "command": "npm run lint && npm test"
          }
        ]
      }
    ]
  }
}
```

コミット前にlintとテストを実行し、失敗したらブロックします。

### 3. コマンドログの記録

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '\"\\(.tool_input.command) - \\(.tool_input.description // \"No description\")\"' >> ~/.claude/bash-command-log.txt"
          }
        ]
      }
    ]
  }
}
```

実行されるBashコマンドをログファイルに記録します。

### 4. 本番ファイルの保護

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "jq -e '.tool_input.path | test(\"^(src/production/|config/prod)\")' | exit 2"
          }
        ]
      }
    ]
  }
}
```

本番ファイルへの変更をブロックします(終了コード2で拒否)。

### 5. rm -rf（フォルダごと削除）のブロック

**スクリプトファイル（.claude/hooks/block-rm-rf.sh）:**
```bash
#!/bin/bash
# rm -rf をブロック（rm は許可）

# 標準入力からJSONを読み取り、コマンドを抽出
input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command // empty')

# -r や -f オプションがあればブロック（rm file.txt は許可）
if [[ "$command" =~ -[rf] ]]; then
    echo "ブロック: rm -rf / rm -r は許可されていません" >&2
    exit 2
fi

exit 0
```

**settings.json:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/block-rm-rf.sh"
          }
        ]
      }
    ]
  }
}
```

危険な `rm -rf` コマンドをブロックし、誤ってファイルを削除するリスクを軽減します。終了コード2を返すことでツール実行を阻止します。

### 6. UserPromptSubmitフックでプロンプトを加工

UserPromptSubmitフックは、ユーザーがプロンプトを送信したときに発火します。**他のフックと異なり、stdinからJSON形式でデータを受け取ります**。

**stdinから受け取るJSONの構造:**
```json
{
  "session_id": "abc123",
  "prompt": "こんにちは、今日の天気を教えて",
  "cwd": "/Users/username/project",
  "hook_event_name": "UserPromptSubmit"
}
```

`prompt`フィールドにユーザーの入力が格納されています。

**jqコマンドでの取得:**
```bash
# stdin から JSON を読み込み、prompt フィールドを抽出
prompt=$(cat | jq -r '.prompt')
```

**コンテキストの追加（追加指示の注入）:**

stdoutに出力した内容がコンテキストに追加されます。毎回のプロンプトにガイドラインを付与できます。

`.claude/hooks/add-guardrail.sh`:
```bash
#!/bin/bash

# stdin を消費（重要）
cat > /dev/null

# 追加の指示を出力
echo "ユーザーからのプロンプトが曖昧な場合は、AskUserQuestionツールを使用してユーザーに確認してから作業を進めてください。"

exit 0
```

⚠️ **`cat > /dev/null`について**: Claude CodeはJSON-RPC通信を使用しており、stdinのデータを読み捨てないと通信に問題が生じる可能性があります。プロンプト内容を使わない場合でも入れておくのが無難です。

**settings.json:**
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/Desktop/hooks-test/.claude/hooks/add-guardrail.sh"
          }
        ]
      }
    ]
  }
}
```

**簡易版（1行で設定）:**
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'ユーザーからのプロンプトが曖昧な場合は、AskUserQuestionツールを使用してユーザーに確認してから作業を進めてください.'"
          }
        ]
      }
    ]
  }
}
```

**機密情報のブロック（APIキー検知）:**

`.claude/hooks/filter-secrets.sh`:
```bash
#!/bin/bash

# stdin から JSON を読み込み、prompt フィールドを抽出
prompt=$(cat | jq -r '.prompt')

# APIキーパターンを検知（OpenAI形式: sk-xxx）
if echo "$prompt" | grep -qE "sk-[a-zA-Z0-9]{20,}"; then
    echo '{"decision": "block", "reason": "APIキーが含まれている可能性があります。機密情報を削除してから再度お試しください。"}'
    exit 0
fi

exit 0
```

`{"decision": "block", "reason": "..."}`をstdoutに出力すると、プロンプト送信がブロックされます。

**ブロック時の表示:**
```
⏺ UserPromptSubmit operation blocked by hook:
  APIキーが含まれている可能性があります。機密情報を削除してから再度お試しください。

  Original prompt: APIキーをあなたに教えますね。sk-abcdefghijklmnopqrstuvwxyz123456 です。
```

### 7. SessionStartフックで環境初期化を自動化

SessionStartフックは、新しいセッションが開始されたとき、または既存セッションを再開したときに自動実行されます。開発環境を毎回同じ状態に保つために活用できます。

**SessionStartフックの特徴:**
- **マッチャー（パターン指定）を使用しない** - セッション開始時に毎回実行される
- 条件分岐が必要な場合は、シェルスクリプト内で対応
- **フックがエラーになってもセッション自体は正常に開始される**

**基本設定（npm install自動実行）:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "npm install"
          }
        ]
      }
    ]
  }
}
```

**条件分岐で効率化（node_modulesが無い場合のみ実行）:**

`.claude/hooks/install-node-modules.sh`:
```bash
#!/bin/bash
if [ ! -d "node_modules" ]; then
    echo "node_modules が見つかりません。npm install を実行します..."
    npm install
else
    echo "node_modules は既に存在します。スキップします。"
fi
```

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/install-node-modules.sh"
          }
        ]
      }
    ]
  }
}
```

**複数コマンドを順番に実行:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "npm install" },
          { "type": "command", "command": "docker-compose up -d" },
          { "type": "command", "command": "npm run db:migrate" }
        ]
      }
    ]
  }
}
```
⚠️ **注意**: 前のコマンドが失敗しても後続のコマンドは実行される。依存関係がある場合はシェルスクリプトで分岐させる。

**環境変数の永続化（CLAUDE_ENV_FILE）:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'NODE_ENV=development' >> \"$CLAUDE_ENV_FILE\""
          }
        ]
      }
    ]
  }
}
```
セッション中、Claude Codeのコンソールで `! echo $NODE_ENV` を実行すると `development` が表示される。

**タイムアウトの設定:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "npm install",
            "timeout": 300
          }
        ]
      }
    ]
  }
}
```
**デフォルトのタイムアウトは30秒**。大規模プロジェクトやDockerコンテナ起動時は適宜延長する。

**動作確認方法:**
- フック実行結果は `Ctrl + o` でトランスクリプトを開いて確認
- 成功時: `SessionStart:startup hook succeeded: ...`
- エラー時: `SessionStart:startup hook error: ...`

### 8. タスク完了時の通知（Stopフック）

Stopフックは、Claudeがタスクを完了して応答を終えたときに自動実行されます。長時間タスクの完了を見逃さないために便利です。

⚠️ **注意**: Stopフックは応答完了のたびに発火します。簡単な質問への回答でも発火するため、通知音が頻繁に鳴りすぎて煩わしくなることがあります。長時間タスクのときだけ有効化する使い分けがおすすめです。

**簡単なログ記録（動作確認用）:**
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo \"応答完了: $(date)\" >> ~/stop.log"
          }
        ]
      }
    ]
  }
}
```

**macOSで通知音を鳴らす:**
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "afplay /System/Library/Sounds/Glass.aiff"
          }
        ]
      }
    ]
  }
}
```

**利用可能なmacOSシステムサウンド:**
- `/System/Library/Sounds/Glass.aiff` - 透明感のある音
- `/System/Library/Sounds/Ping.aiff` - 短いピン音
- `/System/Library/Sounds/Submarine.aiff` - 深みのある音
- `/System/Library/Sounds/Hero.aiff` - 達成感のある音

**macOSでデスクトップ通知を表示:**
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"タスク完了\" with title \"Claude Code\"'"
          }
        ]
      }
    ]
  }
}
```

**通知音とデスクトップ通知を組み合わせる:**
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "afplay /System/Library/Sounds/Glass.aiff"
          },
          {
            "type": "command",
            "command": "osascript -e 'display notification \"タスク完了\" with title \"Claude Code\"'"
          }
        ]
      }
    ]
  }
}
```

**Windowsで通知音を鳴らす（PowerShell）:**
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "powershell -c \"[System.Media.SystemSounds]::Asterisk.Play()\""
          }
        ]
      }
    ]
  }
}
```

### 9. SubagentStopフック（サブエージェント完了時）

SubagentStopフックは、**サブエージェント（Taskツールで起動されたエージェント）がタスクを完了したとき**に自動実行されます。

**StopフックとSubagentStopフックの違い:**

| フック | 発火タイミング |
|--------|----------------|
| **Stop** | メインエージェント（ユーザーと直接対話するClaude）の完了時 |
| **SubagentStop** | サブエージェント（タスクを委任されたClaude）の完了時 |

⚠️ **重要**: PreToolUse/PostToolUseフックは**サブエージェント内では発火しません**。サブエージェントがファイルを編集しても、PostToolUseフックで設定した自動フォーマットは実行されません。サブエージェント完了後に処理を行いたい場合は、SubagentStopフックを使用してください。

**簡単なログ記録:**
```json
{
  "hooks": {
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo \"$(date): Subagent completed\" >> ~/subagent.log"
          }
        ]
      }
    ]
  }
}
```

⚠️ **matcherは省略**: SubagentStopフック（およびStopフック）では、**matcherフィールドは省略**します。マッチャーの概念がないためです。

**プロンプトベースのフック（type: "prompt"）:**

SubagentStopフックには `type: "command"` のほかに `type: "prompt"` も利用可能です。プロンプトベースのフックはLLM（Haiku）を使用してサブエージェントの完了を評価する仕組みですが、処理時間がかかるため、ほとんどのケースでは `type: "command"` で十分です。

**継続指示を出すJSON出力:**
```json
{
  "decision": "block",
  "reason": "More work needed - tests still failing"
}
```
Exit Code 0でこのJSONをstdoutに出力すると、サブエージェントに追加作業をさせることも可能です。

## フック設定の基本構造

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",  // オプション
        "hooks": [
          {
            "type": "command",
            "command": "your-command-here",
            "timeout": 30  // オプション(秒)
          }
        ]
      }
    ]
  }
}
```

## shファイル化のすすめ

複雑なコマンドをsettings.jsonに直接記述すると、JSONエスケープが大変になります。コマンドをshファイルに切り出すことで、この問題を解決できます。

### shファイル化のメリット

| メリット | 説明 |
|---------|------|
| 可読性の向上 | コメントも自由に書け、複数行にわたる処理も見やすい |
| テストが簡単 | shファイル単体で実行でき、Hooks経由ではなく直接動作確認可能 |
| 再利用しやすい | 同じスクリプトを複数のイベントから呼び出したり、他のプロジェクトでも使い回せる |

### 簡単なテスト例

まずはシンプルな例で動作を確認してみましょう。

**1. テスト用のフォルダ構造を作成:**
```bash
mkdir -p ~/Desktop/hooks-test/.claude/hooks
cd ~/Desktop/hooks-test
touch .claude/settings.json
```

**2. settings.jsonを設定:**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "~/Desktop/hooks-test/.claude/hooks/hello.sh"
          }
        ]
      }
    ]
  }
}
```

**3. hello.shを作成:**
```bash
#!/bin/bash
echo "Hooks が実行されました！" >> ~/Desktop/hooks-test/hooks.log
```

**4. 実行権限を付与:**
```bash
chmod +x .claude/hooks/hello.sh
```

**5. 動作確認:**
Claude Codeを起動し、ファイルを作成・編集すると、hooks.logにメッセージが記録されます。

まずは簡単なechoで動作確認してから、より複雑な処理に進むのがおすすめです。

## マッチャーパターン

マッチャーは**フックの発火条件を指定する文字列**です。

### すべてにマッチ
```json
"matcher": ""   // 空文字列（公式推奨）
"matcher": "*"  // ワイルドカード（同様に動作）
```

### ツール名でマッチ
```json
"matcher": "Bash"   // Bash ツールのみ
"matcher": "Edit"   // Edit ツールのみ
"matcher": "Write"  // Write ツールのみ
"matcher": "Read"   // Read ツールのみ
```

**⚠️ 大文字小文字を区別**: `"Bash"` は正しいが、`"bash"` はマッチしない

### OR条件（複数ツール）
```json
"matcher": "Write|Edit"  // Write または Edit
```

### コマンドパターン（Bash専用）
```json
"matcher": "Bash(npm install)"  // 完全一致のみ
```
**注意**: `Bash(npm install)` は `npm install lodash` にはマッチしない（完全一致）

### SessionStart用マッチャー
```json
"matcher": "startup"  // 新規セッション起動時
"matcher": "resume"   // セッション再開時
"matcher": "clear"    // /clear コマンド実行時
"matcher": "compact"  // コンパクト実行時
```
SessionStartではmatcherを省略するとすべてのセッション開始イベントで発火

**Stop/SubagentStopフック**: matcherフィールド自体を省略する（マッチャーの概念がない）

### 正規表現
```json
"matcher": "Notebook.*"  // Notebookで始まるツールすべて
```

## マッチャーの重要な制約

### プレフィックスマッチングは動作しない

パーミッション設定とHooksのマッチャーでは動作が異なる:

- ✅ permissions: `"Bash(npm:*)"` → 動作する
- ❌ Hooks matcher: `"Bash(npm:*)"` → 動作しない

### スクリプト内でのコマンド判別

特定のコマンド（例：npmコマンド）だけに反応させたい場合は、フックスクリプト内でチェック:

```bash
#!/bin/bash
input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command // empty')

# npmで始まるコマンドかチェック
if [[ "$command" == npm* ]]; then
    echo "npmコマンドが実行されました: $command"
fi
exit 0
```

**よく使うチェックパターン:**
| 対象 | 条件式 |
|------|--------|
| npmコマンド | `[[ "$command" == npm* ]]` |
| gitコマンド | `[[ "$command" == git* ]]` |
| 危険なrm -rf | `[[ "$command" =~ rm.*-[rf] ]]` |

### パターンの優先順位

同じイベントに複数のマッチャーを設定した場合、**配列の順番通りに評価され、マッチしたすべてのフックが順に実行される**

## 環境変数

| 変数 | 説明 | 使用可能なフック |
|------|------|------------------|
| **`$CLAUDE_PROJECT_DIR`** | プロジェクトのルートディレクトリ（絶対パス） | すべてのフック |
| **`$CLAUDE_CODE_REMOTE`** | `"true"`=リモート環境、空/未設定=ローカルCLI | すべてのフック |
| **`$CLAUDE_ENV_FILE`** | 環境変数を永続化するファイルパス | SessionStartのみ |

### CLAUDE_PROJECT_DIR の活用

プロジェクトルートを基準にした相対パスを扱えます:

```bash
#!/bin/bash
project_root="$CLAUDE_PROJECT_DIR"

# プロジェクト固有の設定ファイルを参照
if [[ -f "$project_root/.prettierrc" ]]; then
    echo "Prettier設定が見つかりました"
fi

# プロジェクト内のログファイルに記録
echo "$(date): フック実行" >> "$project_root/.claude/hooks.log"
```

settings.jsonでの使用例:
```json
{
  "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check-style.sh"
}
```

### CLAUDE_ENV_FILE の活用（SessionStartのみ）

セッション開始時に環境変数を永続化できます。`KEY=VALUE`形式でファイルに書き込むと、セッション中に他のフックから参照可能になります:

```bash
#!/bin/bash
# SessionStartフックでの活用例
env_file="$CLAUDE_ENV_FILE"

# 環境変数を永続化
echo "PROJECT_TYPE=nodejs" >> "$env_file"
echo "DEBUG_MODE=true" >> "$env_file"
```

⚠️ **注意**: `CLAUDE_ENV_FILE`はSessionStartフックでのみ利用可能です

### ツール情報へのアクセス
フックは JSON 形式のツール情報を stdin で受け取ります。

**共通フィールド（すべてのイベント）:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/.../.claude/projects/.../xxx.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "default|plan|acceptEdits|bypassPermissions",
  "hook_event_name": "PreToolUse"
}
```

**PreToolUse/PostToolUseの例:**
```json
{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.txt",
    "content": "file content"
  },
  "tool_use_id": "toolu_01ABC123..."
}
```

**jqでの取得例:**
```bash
# tool_input.path を取得
jq -r '.tool_input.file_path'

# tool_input.command を取得
jq -r '.tool_input.command'
```

## 終了コードの意味

| 終了コード | 意味 | 処理 |
|---------|------|------|
| **0** | 成功 | stdoutがJSONなら解析、テキストなら表示 |
| **1** | 非ブロックエラー | stderrがverboseモード（Ctrl+O）で表示 |
| **2** | ブロックエラー | stderrのみ使用、tool呼び出しをブロック |

**Exit Code 2の動作（イベント別）:**

| イベント | Exit 2の動作 |
|---------|------------|
| PreToolUse | tool呼び出しをブロック、stderrをClaudeに表示 |
| PermissionRequest | 権限を拒否、stderrをClaudeに表示 |
| PostToolUse | stderrをClaudeに表示（既に実行済み） |
| UserPromptSubmit | プロンプト処理をブロック、消去、stderrをユーザーに表示 |
| Stop | 停止をブロック、stderrをClaudeに表示 |

## JSON出力による高度な制御

Exit Code 0でJSONをstdoutに出力すると、より詳細な制御が可能です。

**PreToolUseの入力修正:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Auto-approved",
    "updatedInput": {
      "command": "npm run lint"
    }
  }
}
```

**UserPromptSubmitでコンテキスト追加:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Current time: 2025-12-17"
  }
}
```

**Stop/SubagentStopで継続指示:**
```json
{
  "decision": "block",
  "reason": "More work needed - tests still failing"
}
```

## セキュリティ注意事項

⚠️ **重要**: フックは自動実行されるため、セキュリティリスクがあります。

### ベストプラクティス
1. 信頼できるスクリプトのみ使用
2. フックコードを常にレビュー
3. 最小権限の原則
4. プロジェクトフックは Git にコミット前にレビュー

## フック実行の確認

フックが実行されると、処理に時間がかかる場合（数秒程度）は以下のようなメッセージが表示されます：

```
⎿  Running PostToolUse hooks… (1/2 done)
```

`1/2 done` は、2つのフックのうち1つが完了したことを示しています。ただし、瞬時に完了するフック（単純なログ記録など）ではこのメッセージが表示されないこともあります。

## トラブルシューティング

### フックエラーの確認

フックでエラーが発生すると、以下のようなメッセージが表示されます:

```
⎿  PostToolUse:Write hook error
```

このメッセージは「PostToolUse イベントの Write マッチャーでフックエラーが発生した」ことを示しています。

### よくあるミスと対処法

| ミス | 対処法 |
|-----|--------|
| 相対パスの指定 | 絶対パス（`~/path/to/script.sh`または`$CLAUDE_PROJECT_DIR/...`）を使用 |
| 実行権限がない | `chmod +x script.sh`で権限を付与 |
| JSON文法エラー | 設定ファイルのカンマや括弧を確認 |
| マッチャーの書き方 | 正規表現として正しいか確認 |

### エラー原因の特定手順

1. **shファイルを直接実行** - Hooks経由ではなく、ターミナルでスクリプトを直接実行してエラーを確認
2. **終了コードを確認** - スクリプトの終了コードが0以外だとエラー扱いになる
3. **settings.jsonを確認** - スクリプトに問題がなければ設定ファイルの書き方を確認
4. **デバッグモードで確認** - `claude --debug`で詳細ログを確認

### フックが実行されない
1. 設定ファイルのJSON文法を確認
2. マッチャーパターンを確認
3. `claude --debug` で詳細ログを確認

### スクリプトの権限エラー
```bash
chmod +x your-script.sh
```

### タイムアウト
```json
{
  "command": "long-running-task",
  "timeout": 300  // 5分
}
```

## 次のステップ

- **subagents.md** - カスタムサブエージェントの作成
- **plugins.md** - フックをプラグイン化
- **settings.md** - 詳細な設定管理
