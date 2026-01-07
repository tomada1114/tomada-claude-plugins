# 新機能（2025年）

> Claude Codeの最新機能：チェックポイント/リウインド、Web版、Slack連携、デスクトップアプリ統合。

## チェックポイントとリウインド

### 概要

チェックポイント機能は、Claude Codeのセッション状態を自動的に保存し、必要に応じて過去の状態に戻ることができる機能です。「さっきの方がよかった」「別のアプローチを試したい」という場面で、好きなポイントまで戻って再出発できます。

https://docs.claude.com/ja/docs/claude-code/checkpointing

### 自動チェックポイント

Claude Codeは**各ユーザープロンプト時**に自動的にチェックポイントを作成します。

- 各プロンプト送信時に新しいチェックポイントを自動作成
- セッション間で永続化（中断したセッション再開時にも利用可能）
- 30日後に自動クリーンアップ（設定で変更可能）

### リウインド（巻き戻し）

#### 方法1: Escキー2回（直前に戻る）

```
Esc Esc
```

直前のやりとりをすぐにキャンセルしたい場合に最適。Claudeの最新の応答が気に入らなかった場合に便利。

#### 方法2: /rewindコマンド（任意のポイントに戻る）

```bash
/rewind
```

複数のチェックポイントから選んで戻りたい場合に使用。矢印キーで戻りたいポイントに移動し、Enterで確認画面に進む。

まだ何も変更していない場合は「Nothing to rewind to yet.」と表示される。

### 3つの復元方法

`/rewind`で巻き戻す際、以下の3つの復元方法から選択できます。

#### 1. Restore code and conversation（推奨）

**コードと会話の両方を復元**。デフォルトで選択されており、基本的にはこれを選ぶのがおすすめ。

- **Claude Codeの認識**：選択した時点までの内容のみ
- **実際のファイル**：選択した時点の状態

両方が一致するため、最もわかりやすい復元方法。プロンプトを修正して再実行したい場合に最適。

#### 2. Restore conversation

**会話のみを復元**し、コードの変更は維持。

Claude Codeが複数ファイルを編集して、一部の変更だけ残したい場合に使用。ただし、Claude Codeの認識とファイルの状態にズレが生じるため、次の指示で予期しない動作をする可能性がある。

#### 3. Restore code

**コードのみを復元**し、会話履歴は維持。

変更は気に入らなかったが、会話履歴を見返したい場合に使用。どこで判断を誤ったのかを確認しながら、別のアプローチを試せる。次の指示を出す際は「先ほどの変更を巻き戻した」ことを明示的に伝える必要がある。

### ユースケース

1. **Claudeの提案が期待と違ったとき**: `/rewind`で戻ってから、別の指示を出し直す
2. **別のアプローチを試したいとき**: 異なる実装方法を比較検討
3. **誤った指示を出してしまったとき**: 正しい指示を出し直してリカバリー
4. **複数の実装を比較したいとき**: Git stashと組み合わせて変更を退避・比較
5. **実験的な変更を試すとき**: 失敗してもすぐに戻せるので大胆に挑戦できる

### 巻き戻せる範囲

巻き戻せるのは以下の条件を満たす範囲内に限定：

- **現在のセッション内**のポイントのみ
- **`/clear`を実行した地点**より後
- **`/compact`で圧縮されていない部分**

### 分岐の概念

巻き戻した後に新しい指示を出すと、別の分岐として会話が進行する（**元の未来には戻れない**）。

```
A → B → C → D（元の流れ）
        ↓
        C'（/rewindで戻ってから別の指示）→ D'（新しい流れ）
```

Gitのブランチに似た仕組み。

### 注意点

- チェックポイントはローカルに保存される
- セッション終了後も30日間保持される
- Bashコマンドで変更されたファイル（`rm`, `mv`, `cp`等）は追跡されない
- 外部で変更されたファイル（エディタでの直接編集等）は追跡されない
- Gitの完全な履歴の代替ではなく、セッションレベルのアンドゥ機能
- `/clear`や`/compact`を実行すると、それより前のポイントには戻れなくなる

### /rewindと他のコマンドの比較

| コマンド | 動作 | 用途 |
|---------|------|------|
| `/rewind` | 過去のポイントに巻き戻す | 試行錯誤（別のアプローチを試す） |
| `/clear` | 会話履歴を完全リセット | タスクを完全に切り替えたい |
| `/compact` | 会話を要約して圧縮 | 文脈を維持しつつトークン節約 |

`/rewind`は「試行錯誤」、`/clear`は「リセット」、`/compact`は「整理」のためのコマンド。

## Claude Code on the Web（Research Preview）

### 概要

ブラウザからClaude Codeにタスクを委譲し、クラウド上で実行できる機能です。

### ステータス

**Research Preview** として公開中。

### 利用可能なユーザー

- Pro ユーザー
- Max ユーザー
- Team Premium Seat ユーザー
- Enterprise Premium Seat ユーザー

### 特徴

- **ブラウザから直接タスク委譲**: CLIを使わずにタスクを開始
- **クラウド実行**: Anthropicが管理するVMで実行
- **複数タスク並列実行**: 同時に複数のタスクを処理
- **GitHub自動連携**: リポジトリへの直接アクセス
- **プリインストール環境**: Python、Node.js、Ruby、PostgreSQL、Redis、Docker等

### 使用方法

1. [claude.ai/code](https://claude.ai/code) にアクセス
2. GitHubアカウントを接続
3. リポジトリにClaude GitHub Appをインストール
4. タスクを入力して実行
5. 結果を確認・PRを作成

### Web→ターミナルへの移行

"Open in CLI"ボタンでコマンドを取得し、ローカルで続行可能。

### 制限事項

- インターネット接続が必要
- 一部の機能はローカル実行のみ
- 大規模なリポジトリでは時間がかかる場合がある

## Claude Code in Slack（2025年12月、GA）

### 概要

Slack内から`@Claude`をメンションしてClaude Codeタスクを実行できる機能です。

### ステータス

**一般利用可能（GA）**

### 必要条件

| 要件 | 詳細 |
|------|------|
| **Claude プラン** | Pro、Max、Team、または Enterprise（Claude Code アクセス付き） |
| **Claude Code on the web** | アクセス有効化が必須 |
| **GitHub アカウント** | 少なくとも1つのリポジトリを認証 |
| **Slack 認証** | Claude アプリ経由で Slack アカウントをリンク |

### 特徴

- **Slackから直接起動**: `@Claude`でメンション
- **スレッドコンテキスト自動解析**: 会話の文脈を理解
- **リポジトリ自動判定**: 認証済みリポジトリから推測
- **PR作成・進捗共有**: 結果をスレッドに投稿
- **ルーティングモード**: Code only / Code + Chat から選択

### 使用例

```
@Claude このバグを修正して: https://github.com/org/repo/issues/123
```

```
@Claude 昨日のPR #456 にテストを追加して
```

### セットアップ

1. [Slack App Marketplace](https://slack.com/marketplace/A08SF47R6P4)からClaude アプリをインストール
2. Slack内で「Claude」アプリを開き、「App Home」タブで「Connect」をクリック
3. [claude.ai/code](https://claude.ai/code)でGitHubアカウントを接続
4. `@Claude`でタスクを依頼

### 制限事項

- **DMでは使用不可**: Slackチャネル（public/private）のみ対応
- **GitHubのみ対応**: 他のGitホスティングサービスは未サポート
- **1セッション1 PR**: 各セッションで作成可能なPRは1つのみ

## デスクトップアプリ統合（Claude Code on Desktop）

### 概要

Claudeデスクトップアプリを通じてClaude Codeを使用し、複数セッションの同時実行やリモートセッションの起動が可能です。

### 特徴

- **ローカルセッションの並列実行**: Git worktreeを使用して、同じリポジトリで複数のClaude Codeセッションを同時に実行
- **`.gitignore`内のファイル含有**: `.worktreeinclude`ファイルで`.env`等を新しいworktreeに自動コピー
- **クラウドセッションの起動**: デスクトップアプリから直接リモートセッションを起動可能

### インストール

公式サイトからダウンロード:

```
https://claude.ai/download
```

### Git Worktree設定

デフォルトworktree場所: `~/.claude-worktrees`

`.worktreeinclude`ファイル設定例:
```
.env
.env.local
.env.*
**/.claude/settings.local.json
```

### 注意点

- ローカルセッションはWindows arm64アーキテクチャでは利用不可

## ステータスライン

### 概要

Claude Codeの状態をリアルタイムで表示するカスタマイズ可能なステータスライン。

### 設定方法

```bash
# インタラクティブ設定
/statusline
```

または `.claude/settings.json` に直接記述:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh",
    "padding": 0
  }
}
```

### 利用可能な情報（JSONで受け取れる）

- `model.id` / `model.display_name` - 現在のモデル名
- `workspace.current_dir` / `workspace.project_dir` - ディレクトリ情報
- `cwd` - 現在の作業ディレクトリ
- `version` - Claude Codeバージョン
- `cost.total_cost_usd` - セッションコスト
- `cost.total_duration_ms` - 実行時間
- `cost.total_lines_added` / `total_lines_removed` - コード変更量
- `context_window` - トークン使用状況（入力/出力/キャッシュ）
- `output_style.name` - 現在のアウトプットスタイル

## 出力スタイルのカスタマイズ

### outputStyle設定

```bash
# メニューから選択
/output-style

# 直接指定
/output-style explanatory
```

### ビルトインオプション

- `default`: 標準的な開発用（既定値）
- `explanatory`: 教育的な「インサイト」を追加
- `learning`: 協調学習モード（TODO(human)マーカーを含む）

### カスタムスタイル

`~/.claude/output-styles/` または `.claude/output-styles/` にMarkdownファイルを作成:

```markdown
---
name: my-style
description: カスタム出力スタイル
keep-coding-instructions: true
---

出力スタイルの指示をここに記述...
```

## バックグラウンドタスク

### 概要

長時間実行されるタスクをバックグラウンドで処理し、他の作業を続けられます。

### 使用方法

```bash
# 実行中のコマンドをバックグラウンドに移動
Ctrl+B

# Tmuxユーザーの場合
Ctrl+B Ctrl+B  # 2回押す
```

Claudeに「バックグラウンドで実行」と指示することも可能。

### バックグラウンドタスクの確認

```bash
/tasks
```

### ユースケース

- 開発サーバーの起動（npm、yarn）
- テストスイートの実行（jest、pytest）
- ビルドプロセス（webpack、vite、make）
- 長時間実行プロセス（docker、terraform）

### 特徴

- 非同期実行で後続プロンプトに対応
- セッション終了時に自動クリーンアップ

## 拡張コンテキストウィンドウ

### 100万トークンコンテキスト

長時間のセッションや大規模なコードベースを扱う場合に有用。

### 設定方法

**フルモデル名に`[1m]`サフィックスを追加**:

```bash
# モデル切り替え時
/model anthropic.claude-sonnet-4-5-20250929-v1:0[1m]

# 起動時
claude --model anthropic.claude-sonnet-4-5-20250929-v1:0[1m]
```

設定ファイルで:

```json
{
  "model": "anthropic.claude-sonnet-4-5-20250929-v1:0[1m]"
}
```

### 注意点

- **フルモデル名が必要**: `sonnet[1m]`のようなエイリアスは対応していない可能性あり
- 異なる価格設定が適用される（[Long Context Pricing](https://docs.claude.com/en/docs/about-claude/pricing#long-context-pricing)）
- Console/APIユーザー向け機能
- すべてのモデルで利用可能ではない

## キーボードショートカット一覧

| ショートカット | 機能 |
|---------------|------|
| `Esc Esc` | チェックポイント/リウインド |
| `Ctrl+C` | 入力/生成キャンセル |
| `Ctrl+B` | バックグラウンド化（Tmuxは2回） |
| `Ctrl+O` | 詳細出力トグル |
| `Ctrl+R` | コマンド履歴の逆向き検索 |
| `Option+P` (macOS) / `Alt+P` | モデル切り替え |

## 今後の予定

Anthropicは継続的にClaude Codeを改善しています。最新情報は以下で確認：

- [Claude Code Docs](https://code.claude.com/docs/)
- [Anthropic Blog](https://www.anthropic.com/blog)
