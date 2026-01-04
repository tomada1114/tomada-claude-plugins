# Claude Codeで便利なMCPサーバー

MCPはLLMと外部ツールを接続するプロトコル。Claude Codeの能力を拡張できる。

---

## MCPの基本

### MCPとは

MCP（Model Context Protocol）は、Anthropicが2024年11月に発表したオープンスタンダード。AIモデルと外部ツール・データソースを安全に接続するための「共通言語」として機能する。

イメージとしては「USB-C」のようなもの。様々なデバイスを1つの規格で接続できるように、MCPは様々なツールを1つのプロトコルで統合できる。

### 何ができるか

- **データ読み取り**: ファイル、DB、API等からコンテキスト取得
- **ツール実行**: ファイル書き込み、コマンド実行、外部サービス操作
- **1つのプロトコルで複数サービス対応**: 個別API統合が不要

### Claude Codeへの追加方法

```bash
claude mcp add [サーバー名] -s [scope] --env KEY=VALUE -- [実行コマンド]
```

**スコープの種類**:
- `-s local`（デフォルト）: 現在のプロジェクトのみ、自分専用
- `-s project`: チームで共有（.mcp.jsonに保存）
- `-s user`: 全プロジェクト共通（旧 global）

**その他のコマンド**:
```bash
claude mcp list          # 設定済みサーバー一覧
claude mcp get [名前]    # 特定サーバーの詳細
claude mcp remove [名前] # サーバー削除
/mcp                     # Claude Code内でステータス確認・OAuth認証
```

### 2種類のMCPサーバー

**ローカル（stdio）サーバー**: 自分のマシンで実行。npxやDockerで起動。
```bash
claude mcp add [名前] -- npx -y @modelcontextprotocol/server-[名前]
```

**リモート（HTTP）サーバー**: ベンダーがホスト。URLを追加するだけ。
```bash
claude mcp add --transport http [名前] [URL]
```

リモートサーバーは設定が簡単でメンテナンス不要。ベンダーがアップデートを管理する。

---

## おすすめサーバー

### 開発基盤

| サーバー | 何ができるか |
|----------|-------------|
| **Filesystem** | 特定ディレクトリへのファイルアクセス許可 |
| **Git** | diff, log, commit。変更の文脈を理解させる |
| **Memory** | 会話をまたいだ記憶の永続化（ナレッジグラフベース） |
| **GitHub** | PR、Issue、リポジトリ管理。CI/CDトリガーも可能 |

#### Filesystem

Claude Codeのデフォルトアクセス範囲外のディレクトリを許可する。

```bash
# 複数ディレクトリを指定可能
claude mcp add filesystem -s user -- npx -y @modelcontextprotocol/server-filesystem ~/Documents ~/Projects /path/to/data
```

**ユースケース**:
- 「~/Dataフォルダ内のCSVを分析して」
- 「別プロジェクトの設定ファイルを参照して」

#### Git

ローカルリポジトリのGit操作を可能にする。

```bash
claude mcp add git -s user -- npx -y @modelcontextprotocol/server-git
```

**ユースケース**:
- 「最近のコミット履歴を見せて」
- 「mainブランチとの差分を確認して」

#### Memory

セッションをまたいで情報を記憶する。

```bash
claude mcp add memory -s user -- npx -y @modelcontextprotocol/server-memory
```

**ユースケース**:
- 「このプロジェクトの技術スタックを覚えておいて」
- 「前回話した設計方針を思い出して」

#### GitHub（公式）

GitHubのPR、Issue、リポジトリ管理。公式サーバーはGoで書き直され、信頼性が高い。

**リモートサーバー（推奨）**:
```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
# OAuth認証が必要: /mcp で認証フローを開始
```

**ローカルサーバー（Docker）**:
```bash
claude mcp add github -- docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server
```

**ユースケース**:
- 「PR #456をレビューして改善点を提案して」
- 「見つけたバグについてIssueを作成して」
- 「自分に割り当てられたPRを一覧表示」

### データベース

| サーバー | 何ができるか |
|----------|-------------|
| **PostgreSQL** | スキーマ確認しながらコーディング |
| **Supabase** | DB + 認証 + Storage。バックエンド一括管理 |

#### PostgreSQL

```bash
claude mcp add postgres -s project --env POSTGRES_URL=postgresql://user:pass@localhost:5432/dbname \
  -- npx -y @modelcontextprotocol/server-postgres
```

**ユースケース**:
- 「このテーブル構造を見て、CRUDのAPIを実装して」
- 「usersテーブルから最近登録した10人を取得するクエリを書いて」
- 「既存のスキーマに合わせてマイグレーションを作成して」

### Web検索・ドキュメント

| サーバー | 何ができるか |
|----------|-------------|
| **Brave Search** | 最新情報の検索（無料枠あり） |
| **Exa** | ニューラル検索、コード検索 |
| **Context7** | 最新のライブラリドキュメント取得 |

#### Brave Search

```bash
# APIキーは https://brave.com/search/api/ で取得（無料枠あり）
claude mcp add brave-search -s user --env BRAVE_API_KEY=YOUR_KEY \
  -- npx -y @modelcontextprotocol/server-brave-search
```

**ユースケース**:
- 「React 19の最新の変更点を調べて」
- 「このエラーメッセージの解決策を検索して」

#### Context7（超おすすめ）

LLMの学習データは古いため、最新ライブラリの情報が不正確なことがある。Context7は最新のドキュメントとコード例を直接プロンプトに注入する。

```bash
claude mcp add context7 -s user -- npx -y @upstash/context7-mcp@latest
```

**使い方**: プロンプトに `use context7` を追加するだけ。
```
Next.js 15のApp Routerでミドルウェアを作って。use context7
```

**ユースケース**:
- 「Zodの最新APIでバリデーションスキーマを書いて use context7」
- 「Tailwind v4の新しいユーティリティクラスを教えて use context7」

**Tips**: Claude Codeのルール設定で自動呼び出しを設定すると便利:
```
Always use context7 when I need code generation, setup or configuration steps, or library/API documentation.
```

### 思考・問題解決

| サーバー | 何ができるか |
|----------|-------------|
| **Sequential Thinking** | 複雑な問題を段階的に分解して思考 |

#### Sequential Thinking

複雑なリファクタリングや設計判断で、段階的・反省的な思考プロセスを可能にする。

```bash
claude mcp add sequential-thinking -s user -- npx -y @modelcontextprotocol/server-sequential-thinking
```

**ユースケース**:
- 「このアーキテクチャの問題点を段階的に分析して」
- 「このバグの原因を順を追って特定して」

### ブラウザ自動化

| サーバー | 何ができるか |
|----------|-------------|
| **Playwright** | E2Eテスト生成、SPA対応 |
| **Puppeteer** | Chrome操作、スクレイピング |

#### Puppeteer

```bash
claude mcp add puppeteer -s user -- npx -y @modelcontextprotocol/server-puppeteer
```

**ユースケース**:
- 「このページのスクリーンショットを撮って」
- 「ログインフォームを自動入力するスクリプトを作って」
- 「E2Eテストを生成して」

### プロジェクト管理

| サーバー | 何ができるか |
|----------|-------------|
| **Linear** | イシュー管理。IDEから離れず完結 |
| **Sentry** | エラー監視。本番のバグをターミナルからデバッグ |
| **Slack** | メッセージ送信・履歴取得 |
| **Asana** | タスク・プロジェクト管理 |
| **Notion** | ページ・データベース操作 |

#### Linear（リモート）

```bash
claude mcp add --transport http linear https://mcp.linear.app/mcp
# /mcp で OAuth認証
```

**ユースケース**:
- 「現在のスプリントのIssueを一覧表示」
- 「このバグ修正が完了したらチケットをDoneにして」
- 「新機能のIssueを作成して」

#### Sentry（リモート）

```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
# /mcp で OAuth認証
```

**ユースケース**:
- 「過去24時間で最も多いエラーは？」
- 「エラーID abc123 のスタックトレースを表示」
- 「どのデプロイでこのエラーが増えた？」

#### Slack

```bash
# Bot TokenはSlack Appから取得
claude mcp add slack -s user --env SLACK_BOT_TOKEN=xoxb-xxx \
  -- npx -y @modelcontextprotocol/server-slack
```

**ユースケース**:
- 「#generalチャンネルの今日のメッセージを要約して」
- 「チームに進捗報告を投稿して」

### クラウド

| サーバー | 何ができるか |
|----------|-------------|
| **AWS Suite** | 料金確認、Lambda管理、ドキュメント検索 |
| **Docker** | コンテナ操作（起動・停止・ログ） |

---

## サーバーの探し方

| ソース | 特徴 |
|--------|------|
| **[modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)** | 公式。最も信頼性高い |
| **[Smithery](https://smithery.ai)** | カタログサイト。ワンラインインストール |
| **[Glama](https://glama.ai/mcp/servers)** | 検証済みサーバーのディレクトリ |
| **[MCP Index](https://mcpindex.net)** | 検索しやすいサーバー一覧 |
| **[Docker MCP Catalog](https://hub.docker.com/mcp)** | Docker公式のMCPカタログ |

---

## 導入例まとめ

### ローカルサーバー（stdio）

**Brave Search（Web検索）**:
```bash
claude mcp add brave-search -s user --env BRAVE_API_KEY=xxx \
  -- npx -y @modelcontextprotocol/server-brave-search
```

**Filesystem（ディレクトリ限定アクセス）**:
```bash
claude mcp add filesystem -s user \
  -- npx -y @modelcontextprotocol/server-filesystem ~/Documents ~/Projects
```

**PostgreSQL**:
```bash
claude mcp add postgres -s project --env POSTGRES_URL=postgresql://user:pass@localhost/db \
  -- npx -y @modelcontextprotocol/server-postgres
```

**Context7（最新ドキュメント）**:
```bash
claude mcp add context7 -s user -- npx -y @upstash/context7-mcp@latest
```

**Sequential Thinking（段階的思考）**:
```bash
claude mcp add sequential-thinking -s user \
  -- npx -y @modelcontextprotocol/server-sequential-thinking
```

### リモートサーバー（HTTP）

リモートサーバーはメンテナンス不要で、OAuth認証でセキュア。

```bash
# GitHub（公式リモート）
claude mcp add --transport http github https://api.githubcopilot.com/mcp/

# Sentry（エラー監視）
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp

# Linear（イシュー管理）
claude mcp add --transport http linear https://mcp.linear.app/mcp

# Notion（ドキュメント）
claude mcp add --transport http notion https://mcp.notion.com/mcp

# Asana（タスク管理）
claude mcp add --transport sse asana https://mcp.asana.com/sse
```

追加後、`/mcp` コマンドでOAuth認証を完了させる。

---

## 実践的なユースケース

### 開発フロー統合

「JIRAのチケットENG-4521の機能を実装して、GitHubにPRを作成して」
→ Atlassian MCP + GitHub MCPが連携して、コンテキストを維持したまま作業完了

### デバッグワークフロー

「Sentryで過去24時間のエラーを確認して、最も多いエラーの原因を特定して」
→ Sentry MCPがエラー情報を取得し、Claude Codeがコードを分析

### データ分析

「PostgreSQLのusersテーブルから、先週登録したユーザーの傾向を分析して」
→ PostgreSQL MCPがスキーマとデータを取得し、分析クエリを生成・実行

### ドキュメント参照

「Supabaseの最新認証APIを使ってログイン機能を実装して use context7」
→ Context7が最新ドキュメントを取得し、正確なコード生成

---

## トラブルシューティング

### サーバーが起動しない

```bash
# ログを確認
cat ~/.claude/logs/mcp-server-[名前].log

# 設定を確認
claude mcp get [名前]
```

### Windows での注意点

Windowsでは `cmd /c` ラッパーが必要:
```bash
claude mcp add [名前] -- cmd /c npx -y @modelcontextprotocol/server-[名前]
```

### 認証エラー（リモートサーバー）

```bash
# 認証情報をクリア
rm -rf ~/.mcp-auth

# 再認証
/mcp
```

---

## MCPの価値まとめ

- **Claude Code単体でできないことを可能に**: DB接続、Web検索、外部サービス連携
- **コンテキストスイッチの削減**: ターミナル、ブラウザ、IDEを行き来しない
- **設定ファイルで再現性あり**: .mcp.jsonでチーム共有可能
- **リモートサーバーでメンテナンス不要**: ベンダーがアップデートを管理

### おすすめの始め方

1. **Context7**: 最新ドキュメント取得（学習データの古さを解消）
2. **GitHub**: PR・Issue管理（開発ワークフロー統合）
3. **Sequential Thinking**: 複雑な問題の段階的分析

この3つから始めて、必要に応じて追加していくのがおすすめ。
