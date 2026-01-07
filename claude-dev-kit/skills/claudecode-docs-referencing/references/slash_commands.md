# 05. スラッシュコマンド一覧

## スラッシュコマンドとは

スラッシュコマンドは `/` で始まる特別なコマンドで、Claude Code の設定や機能にアクセスできます。

## ビルトインコマンド一覧

| コマンド | 用途 |
|---------|------|
| `/add-dir` | 追加の作業ディレクトリを追加 |
| `/agents` | カスタムAIサブエージェントを管理 |
| `/bashes` | バックグラウンドタスクをリストして管理 |
| `/bug` | バグ報告（Anthropicに送信） |
| `/clear` | 会話履歴をクリア |
| `/compact [instructions]` | 会話をコンパクト化（オプション指示付き） |
| `/config` | 設定画面を開く（設定タブ） |
| `/context` | コンテキスト使用状況を色付きグリッドで表示 |
| `/cost` | トークン使用統計を表示 |
| `/doctor` | Claude Code インストール状態を診断 |
| `/exit` | REPL を終了 |
| `/export [filename]` | 現在の会話をファイルまたはクリップボードにエクスポート |
| `/help` | 使用方法ヘルプを表示 |
| `/hooks` | ツールイベント用のフック設定を管理 |
| `/ide` | IDE統合を管理し状態を表示 |
| `/init` | `CLAUDE.md` ガイドでプロジェクトを初期化 |
| `/install-github-app` | リポジトリ用Claude GitHub Actionsをセットアップ |
| `/login` | Anthropicアカウントを切り替え |
| `/logout` | Anthropicアカウントからサインアウト |
| `/mcp` | MCP サーバー接続と OAuth 認証を管理 |
| `/memory` | `CLAUDE.md` メモリファイルを編集 |
| `/model` | AIモデルを選択または変更 |
| `/output-style [style]` | 出力スタイルを直接設定またはメニューから選択 |
| `/permissions` | 権限を表示または更新 |
| `/plugin` | Claude Code プラグインを管理 |
| `/pr-comments` | プルリクエストコメントを表示 |
| `/privacy-settings` | プライバシー設定を表示および更新 |
| `/release-notes` | リリースノートを表示 |
| `/rename <name>` | 現在のセッション名を変更 |
| `/resume [session]` | IDまたは名前で会話を再開、またはセッションピッカーを開く |
| ~~`/review`~~ | **撤廃** → `/code-review:code-review`（プラグイン）に移行 |
| `/rewind` | 会話またはコードをリワインド |
| `/sandbox` | ファイルシステムとネットワーク分離を備えたサンドボックス bash ツール |
| `/security-review` | 現在のブランチのペンディング変更のセキュリティレビュー |
| `/stats` | 日次使用状況、セッション履歴、ストリーク、モデル選択を表示 |
| `/status` | 設定画面を開く（ステータスタブ：バージョン、モデル、アカウント、接続性表示） |
| `/statusline` | Claude Code のステータスライン UI をセットアップ |
| `/terminal-setup` | Shift+Enter キーバインディング（iTerm2・VS Code のみ） |
| `/todos` | 現在の TODO アイテムをリスト |
| `/usage` | サブスクリプションプランのみ：プラン使用制限とレート制限状態 |
| `/vim` | Vim モード（insert/command モード切り替え） |

## 基本コマンド

### /help
ヘルプメニューを表示します。

```bash
/help
```

利用可能なコマンド一覧と簡単な説明が表示されます。

### /status
設定画面を開き、ステータスタブを表示します。

```bash
/status
```

表示される情報:
- Claude Code のバージョン
- 使用中のモデル
- アカウント情報
- 接続状態

### /usage
サブスクリプションプラン（Max プラン）の使用状況を表示します。

```bash
/usage
```

- プラン使用制限
- レート制限の状態

### /cost
トークン使用統計を表示します。

```bash
/cost
```

### /stats
日次使用状況、セッション履歴、ストリークを表示します。

```bash
/stats
```

## プロジェクト管理

### /init
プロジェクトを初期化し、CLAUDE.md を生成します。

```bash
/init
```

詳細は **04_project_initialization.md** を参照。

### /memory
CLAUDE.md ファイルを編集します。

```bash
/memory
```

プロジェクトのコンテキストや規約を追加・編集できます。

## モデルとアカウント

### /model
使用する AI モデルを選択します。

```bash
/model
```

選択肢:
- **default** - 推奨モデル（アカウント種別によって異なる）
- **sonnet** - 最新 Sonnet モデル（日常のコーディング）
- **opus** - Opus モデル（複雑な推論タスク向け）
- **haiku** - Haiku モデル（高速で効率的な単純タスク向け）
- **sonnet[1m]** - 1百万トークンコンテキストウィンドウ付き Sonnet
- **opusplan** - ハイブリッドモード：プラン時は Opus、実行時は Sonnet に自動切り替え

### /login
Anthropic アカウントにログインまたは切り替えます。

```bash
/login
```

### /logout
現在のアカウントからログアウトします。

```bash
/logout
```

## 権限管理

### /permissions
ツールの権限を表示・設定します。

```bash
/permissions
```

できること:
- 許可/拒否されたツールの確認
- 新しいルールの追加
- 既存のルールの編集
- デフォルトモードの設定

権限モード:
- `default` - 標準動作（新しいツール使用時にプロンプト）
- `acceptEdits` - セッション中、ファイル編集権限を自動承認
- `plan` - プランモード（分析は可能だが、ファイル変更やコマンド実行は不可）
- `bypassPermissions` - すべての権限プロンプトをスキップ（安全な環境が必須）

権限ルールの優先度:
- **Deny** - 最高優先（ツール使用を完全に禁止）
- **Ask** - 中優先（毎回確認をプロンプト）
- **Allow** - 最低優先（確認なしで許可）

## コンテキスト管理

### /context
現在のコンテキストウィンドウの使用状況を表示します。

```bash
/context
```

表示される情報:
- 使用中のトークン数
- 利用可能なトークン数
- 主要なコンテキスト要素

### /clear
会話履歴をクリアします。

```bash
/clear
```

用途:
- 新しいタスクを開始する前
- コンテキストを節約したい時
- 不要な情報を削除

### /compact
会話履歴を要約・圧縮します。

```bash
/compact
```

- 古い会話を要約
- コンテキストウィンドウを節約
- 重要な情報は保持

### /rewind
会話や変更を巻き戻します。

```bash
/rewind
```

オプション:
- 会話のみ巻き戻し
- コードも巻き戻し
- 特定の時点まで巻き戻し

## IDE連携

### /ide
IDE に接続します(VS Code/JetBrains)。

```bash
/ide
```

詳細は **06_ide_integration.md** を参照。

### /terminal-setup
改行用のキーバインド(Shift+Enter)を設定します。

```bash
/terminal-setup
```

対応ターミナル:
- iTerm2
- VS Code のターミナル

## コードレビュー

### /code-review:code-review（プラグイン）
コードレビューをリクエストします。

> **注意**: 旧 `/review` コマンドは撤廃され、プラグイン方式に移行しました（2025年12月）。

**導入手順**:
```bash
# 1. Claude Code を起動
claude

# 2. マーケットプレイスを追加
/plugin marketplace add anthropics/claude-code

# 3. code-review プラグインをインストール
/plugin install code-review@anthropics/claude-code

# 4. インストール範囲を選択（推奨: "Install for you (user scope)"）
```

**使用方法**:
```bash
/code-review:code-review
```

レビュー内容:
- コード品質
- セキュリティ
- ベストプラクティス
- パフォーマンス

### /pr-comments
プルリクエストのコメントを表示します。

```bash
/pr-comments
```

GitHub PR と連携している場合に使用。

## 高度な機能

### /config
詳細な設定を管理します。

```bash
/config
```

設定できる項目:
- テーマ
- デフォルトモデル
- 権限ルール
- 通知設定
- その他のオプション

### /agents
サブエージェントを管理します。

```bash
/agents
```

できること:
- 利用可能なエージェント表示
- 新しいエージェント作成
- 既存のエージェント編集
- ツール権限の管理

詳細は **08_subagents.md** を参照。

### /hooks
フックを管理します。

```bash
/hooks
```

フックイベント:
- PreToolUse
- PostToolUse
- UserPromptSubmit
- Notification
- SessionStart
- SessionEnd

詳細は **09_hooks.md** を参照。

### /plugin
プラグインを管理します。

```bash
/plugin
```

できること:
- プラグインのインストール
- プラグインの有効化/無効化
- マーケットプレイスの追加
- プラグイン一覧の表示

詳細は **10_plugins.md** を参照。

### /mcp
Model Context Protocol (MCP) サーバーを管理します。

```bash
/mcp
```

外部ツールやサービスとの接続を管理。

### /vim
Vim モードを切り替えます。

```bash
/vim
```

Vim キーバインディング:
- `Esc` で NORMAL モード
- `i/a/o` で INSERT モード
- `h/j/k/l` で移動
- `w/e/b` で単語移動

## カスタムコマンド

### プロジェクトコマンド
プロジェクト固有のコマンドを作成できます（チーム共有向け）。

場所: `.claude/commands/`

使用方法:
```bash
/command-name [引数]
```

例:
```bash
mkdir -p .claude/commands
echo "Fix issue #\$ARGUMENTS following our coding standards" > .claude/commands/fix-issue.md
# 使用: /fix-issue 123
```

### ユーザーコマンド
すべてのプロジェクトで使えるコマンドを作成できます（個人向け）。

場所: `~/.claude/commands/`

使用方法:
```bash
/command-name [引数]
```

**優先順位**: プロジェクトコマンド > ユーザーコマンド

**Frontmatter フィールド**:
```yaml
---
description: コマンドの説明
allowed-tools: Bash(npm run test:*), Bash(git add:*)
argument-hint: [issue-number] [priority]
model: claude-opus-4-20250805
disable-model-invocation: false
---
```

**引数の使用方法**:
- `$ARGUMENTS` - すべての引数を受け取る
- `$1`, `$2`, `$3` - 個別の位置引数

詳細は **07_custom_commands.md** を参照。

## コマンドのヒント

### Tab 補完
コマンド名の途中で Tab キーを押すと、候補が表示されます。

```bash
/mod<Tab>  # → /model
```

### ヘルプの確認
各コマンドで `--help` オプションが使える場合があります。

### よく使うコマンドの組み合わせ

#### 新しいタスクを開始
```bash
/clear      # コンテキストをクリア
/model      # 必要に応じてモデル変更
```

#### プロジェクト設定を確認
```bash
/status     # ステータス確認
/context    # コンテキスト確認
/memory     # プロジェクト情報確認
```

#### デバッグ
```bash
/rewind     # 変更を巻き戻し
/code-review:code-review  # コードレビュー（プラグイン）
/permissions # 権限確認
```

## 次のステップ

スラッシュコマンドを理解したら:
- **06_ide_integration.md** - IDEとの連携
- **07_custom_commands.md** - カスタムコマンドの作成
- **08_subagents.md** - サブエージェントの活用
