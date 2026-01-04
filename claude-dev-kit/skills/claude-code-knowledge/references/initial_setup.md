# 02. 初期設定ガイド

## 認証方法の選択

Claude Code を使用するには、以下のいずれかの方法で認証する必要があります:

### 1. Claude.ai（サブスクリプション）
- Web版Claude（https://claude.ai）と同じアカウントを使用
- Pro プラン($20/月)または Max プラン($100/月)に加入で追加料金なし
- 月額固定で使い放題（一定の制限あり）
- **こんな人におすすめ**: 毎日使う、Web版も使いたい、月額固定で予算管理したい

### 2. Anthropic Console（API従量課金）
- [console.anthropic.com](https://console.anthropic.com) で開発者向けアカウント
- 事前にクレジットをチャージし、使用トークン数に応じて課金
- 初回ログイン時に「Claude Code」ワークスペースが自動作成
- **こんな人におすすめ**: たまにしか使わない、CI/CDで自動実行、使用量を細かく管理

### 同じメールで両方のアカウントを持てる
Claude.ai と Anthropic Console は同じメールアドレスで両方のアカウントを作成可能。ログイン時に「Use claude.ai」か「Use Anthropic Console」を選択できる。日常使いはClaude.ai、自動化用途はAnthropic Consoleと使い分けるパターンも有効。

### 3. API キーを直接設定
環境変数で API キーを設定することも可能:

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

### 4. エンタープライズクラウドプロバイダー
企業向けに以下のプロバイダー経由でも利用可能:
- Amazon Bedrock
- Google Vertex AI
- Microsoft Foundry

各プロバイダーのクレデンシャル設定が必要です。

## 初回起動と認証

### 1. Claude Code を起動

```bash
claude
```

ターミナルでコマンドを実行すると、ブラウザが開いてログインページに遷移。ブラウザが使える環境であれば特別な準備は不要。

**ブラウザが使えない環境（SSH接続など）の場合**: 表示されるURLを手動でコピーし、別のブラウザに貼り付けてログイン。

### 2. テーマについて

Claude Codeはターミナルアプリケーションのテーマに自動で対応します。テーマ変更はターミナル側（Terminal.app、iTerm2、VS Code等）で設定してください。

`/config` コマンドでインターフェース設定をカスタマイズできます。

### 3. API キーの設定

Anthropic Console の指示に従い、ブラウザでログインして認証を完了します。

APIキーを手動で取得する場合:
1. [console.anthropic.com](https://console.anthropic.com) にアクセス
2. ログインまたはアカウント作成
3. API セクションで新しい API キーを生成
4. キーをターミナルに貼り付け

## ターミナル設定の最適化

Claude Code は適切に設定されたターミナルで最適に動作します。

### 改行入力の設定

メッセージに改行を入れる方法は3つあります:

#### 方法1: バックスラッシュエスケープ
```
\<Enter>
```
`\` を入力してから Enter を押すと改行が作成されます。

#### 方法2: 自動設定(推奨)
```bash
/terminal-setup
```
Claude Code 内でこのコマンドを実行すると、Shift+Enter で改行できるようになります(iTerm2とVS Codeのみ)。

#### 方法3: Option+Enter (Mac)

**Terminal.app の場合:**
1. 設定 → プロファイル → キーボード
2. 「Option をMeta キーとして使用」をチェック

**iTerm2 / VS Code の場合:**
1. 設定 → プロファイル → キー
2. 左/右 Option キーを「Esc+」に設定

### 通知設定

タスク完了時に通知を受け取る設定:

#### iTerm2 システム通知
1. iTerm2 環境設定を開く
2. プロファイル → ターミナルに移動
3. 「Silence bell」をチェック
4. Filter Alerts → 「Send escape sequence-generated alerts」を選択

#### カスタム通知フック
settings.json にカスタムフックを設定することも可能:
```json
{
  "hooks": {
    "Notification": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "afplay /System/Library/Sounds/Glass.aiff"
      }]
    }]
  }
}
```

## グローバル設定

設定の確認と変更:

```bash
# 設定を確認
claude config list

# 設定を変更（例）
claude config set --global autoUpdates false
```

settings.json を直接編集することも可能:
```json
{
  "model": "sonnet",
  "permissions": {
    "allow": ["Bash(npm run test:*)"],
    "deny": ["Read(./.env)"]
  }
}
```

## 初めてのプロジェクト設定

プロジェクトディレクトリで Claude Code を起動:

```bash
cd your-project-directory
claude
```

Claude Codeはカレントディレクトリを作業対象として認識するため、**目的のプロジェクトディレクトリで起動する**ことがポイント。

### 基本コマンド

対話モードでは、スラッシュ（/）で始まるコマンドを使用:

| コマンド | 機能 |
|---------|------|
| `/help` | 利用可能なコマンド一覧を表示 |
| `/resume` | 以前の会話を継続 |
| `/clear` | 会話履歴をクリア |
| `exit` または `Ctrl+C` | Claude Codeを終了（複数回`Ctrl+C`で強制終了） |

### 初回起動時の推奨手順

1. **プロジェクトの全体像を把握させる**
   ```
   > このプロジェクトについて教えてください
   ```
   Claude Codeはプロジェクト内のファイルを**自動的に読み込んで**回答する。手動でのファイル追加は不要。

2. **CLAUDE.mdを生成**
   ```
   /init
   ```
   プロジェクトの情報を記憶する CLAUDE.md ファイルが作成される。

3. **CLAUDE.mdをコミット**
   ```
   > 生成された CLAUDE.md をgitにコミットして
   ```

### ファイル指定方法

ファイルやフォルダパスがあらかじめ分かっている場合は、`@` に続けてパスを指定すると探索範囲が限定され、回答精度が向上:

```
> @src/auth/login.ts を参考に、ログアウト機能を実装して
```

同じファイル名が複数ある場合は入力候補が表示される。

### プロジェクトを理解させるコツ

いきなりタスクを依頼するより、**探索→理解→実行**の順で進める方が精度の高い結果が得られる:

1. **全体像を把握させる**: 「このプロジェクトの概要を教えて」
2. **関連ファイルを特定させる**: 「認証機能に関係するファイルはどれ？」
3. **具体的なタスクを依頼する**: 「ログイン機能のバグを修正して」

### 日本語対応

Claude Codeは日本語に対応。日本語で質問すれば日本語で回答が返る。ただし、Claude自体が英語で学習されているモデルのため、技術的な質問では英語の方が精度が高くなる場合もある。日常的な開発作業では日本語で十分実用的。

## モデルの選択

使用する AI モデルを選択:

```bash
/model
```

選択肢:
| エイリアス | モデル | 用途 |
|-----------|--------|------|
| `sonnet` | Claude Sonnet 4.5 | 日常的なコーディングタスク（デフォルト） |
| `opus` | Claude Opus 4.5 | 複雑な推論が必要なタスク |
| `haiku` | Claude Haiku | シンプルなタスク・高速処理 |
| `opusplan` | Plan: Opus / 実行: Sonnet | ハイブリッド使用 |
| `sonnet[1m]` | Sonnet + 100万トークン | 長期セッション |

コマンドラインでの指定:
```bash
claude --model opus
```

環境変数での設定:
```bash
export ANTHROPIC_MODEL=opus
```

## 設定ファイルの場所

### グローバル設定（ユーザー設定）
```
~/.claude/settings.json
```
すべてのプロジェクトに適用される設定

### プロジェクト共有設定
```
.claude/settings.json
```
特定のプロジェクトの設定（チームと共有、リポジトリにコミット）

### プロジェクトローカル設定
```
.claude/settings.local.json
```
個人用設定（自動で.gitignoreに追加される）

### エンタープライズ管理設定
組織管理者による設定（最優先）:
- macOS: `/Library/Application Support/ClaudeCode/`
- Linux/WSL: `/etc/claude-code/`
- Windows: `C:\Program Files\ClaudeCode\`

### その他の設定ファイル
- `~/.claude.json`: 状態管理、OAuthトークン、MCPサーバー設定、キャッシュ
- `.mcp.json`: プロジェクトMCPサーバー設定

## 会話の継続

作業を中断してClaude Codeを終了しても、次回起動時に会話を継続できる。

### コマンドラインオプション

```bash
claude -c  # 直近の会話を継続（continueの略）
claude -r  # 過去の会話から選んで再開（resumeの略）
```

- `-c`: 直近の会話を自動的に再開
- `-r`: 過去の会話一覧から選択して再開

### 対話モード内での再開

対話モード内では `/resume` コマンドでも同様の操作が可能。

### 会話履歴の保存

会話履歴はローカルに保存されるため、プライバシーに配慮しつつ過去のコンテキストを活用できる設計。

## コストの確認

使用量とコストを確認:

```bash
# 今月の使用量を表示
npx ccusage@latest

# 詳細な使用状況
/usage
```

## 次のステップ

初期設定が完了したら、**03_basic_usage.md** で基本的な使い方を学びましょう。

## トラブルシューティング

### API接続エラー
- VPNを無効にして再試行
- インターネット接続を確認
- 時間をおいて再度実行

### 認証の問題
```bash
# 再ログイン
/logout
/login
```

## 認証情報の管理

### 認証情報の保存
一度ログインすると、認証情報はシステムに安全に暗号化されて保存される。次回 `claude` コマンド実行時は再ログイン不要。

**セキュリティ注意**: 共有PCやサーバーでClaude Codeを使う場合、認証情報がそのマシンに保存されるため、他のユーザーがアクセスできる環境では適切な権限管理が必要。

### アカウントの切り替え
ログイン済みの状態で別のアカウントに切り替える場合:

```bash
/login
```

対話モード内でこのコマンドを実行するとブラウザが開き、再度ログインフローを実行。Claude.ai ⇔ Anthropic Console の切り替えも同じコマンドで対応可能。

### 設定のリセット
```bash
# グローバル設定を削除
rm ~/.claude/settings.json
```
