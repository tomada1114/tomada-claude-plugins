# MCP（Model Context Protocol）

> Claude Codeを外部ツールやデータソースに接続するためのMCPサーバーの設定と使用方法。

## MCPとは

MCP（Model Context Protocol）は、Anthropicが策定したオープンな標準プロトコルで、Claude Codeを外部システムに接続するための仕組みです。GitHub、Notion、PostgreSQL、Sentryなどのツールとの統合を可能にします。

イメージとしては「USB-C」に近く、様々な外部ツールを1つのプロトコルで統合する役割を果たしています。

## なぜMCPが必要なのか

Claude Code単体では以下のような操作には対応していません：

- データベースへの直接アクセス
- GitHubのIssueやPRの操作
- Slackへのメッセージ送信
- 外部APIの呼び出し
- ブラウザの自動操作

MCPサーバーを追加することで、これらの操作がClaude Code上で可能になります。

> **Note**: 一部の操作はCLIツール（GitHub CLIなど）でも可能ですが、MCPを使うことでClaude Codeが利用可能な機能を把握しやすく、より簡潔に操作できます。

## サーバータイプ

MCPは3つのトランスポートタイプをサポートしています：

| タイプ | 説明 | 用途 |
|--------|------|------|
| **HTTP** | HTTPベースの通信（推奨） | リモートサーバー |
| **SSE** | Server-Sent Events（非推奨） | リアルタイム通信 |
| **Stdio** | 標準入出力 | ローカルプロセス |

## MCPサーバーの追加

### HTTP サーバー（推奨）

```bash
claude mcp add --transport http <name> <url>

# 例: GitHub MCP
claude mcp add --transport http github https://mcp-server.example.com/github
```

### Stdio サーバー（ローカル）

```bash
claude mcp add --transport stdio <name> -- <command>

# 例: ローカルのNode.jsサーバー
claude mcp add --transport stdio my-server -- node /path/to/server.js
```

### SSE サーバー（非推奨）

```bash
claude mcp add --transport sse <name> <url>
```

## スコープ

MCPサーバーには3つのスコープがあります：

| スコープ | 設定ファイル | 用途 |
|----------|--------------|------|
| **local** (デフォルト) | `~/.claude.json` | 個人のプロジェクト設定（Git管理外） |
| **project** | `.mcp.json` | チーム共有のプロジェクト設定 |
| **user** | `~/.claude.json` | 全プロジェクト共通（クロスプロジェクト） |
| **enterprise** | `/Library/Application Support/ClaudeCode/managed-mcp.json` (macOS) | 企業管理ポリシー |

### スコープの指定

```bash
# プロジェクトスコープ（チーム共有）
claude mcp add --scope project github -- npx @anthropic-ai/mcp-server-github

# ユーザースコープ（個人用、全プロジェクト共通）
claude mcp add --scope user my-tools -- node ~/tools/mcp-server.js

# ローカルスコープ（個人用、このプロジェクトのみ）
claude mcp add --scope local dev-tools -- node ./dev-tools.js
```

## MCPサーバーの管理

### サーバー一覧の確認

```bash
# インタラクティブメニュー
/mcp

# またはCLIで
claude mcp list
```

### サーバーの削除

```bash
claude mcp remove <name>
```

### サーバーの設定確認

```bash
claude mcp get <name>
```

### その他のコマンド

```bash
# Claude Desktopから設定をインポート
claude mcp add-from-claude-desktop

# JSON設定で直接追加
claude mcp add-json <name> '<json>'

# Claude Code自体をMCPサーバーとして起動
claude mcp serve

# プロジェクトスコープの承認をリセット
claude mcp reset-project-choices
```

### 追加オプション

```bash
--scope local|project|user  # 設定スコープ指定（デフォルト: local）
--header "Key: Value"       # HTTP認証ヘッダー
--env KEY=value             # 環境変数設定
```

## 設定ファイルの形式

### .mcp.json（プロジェクト共有）

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["@anthropic-ai/mcp-server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["@anthropic-ai/mcp-server-postgres"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}"
      }
    }
  }
}
```

### 環境変数の参照

設定ファイル内で`${ENV_VAR}`形式で環境変数を参照できます。デフォルト値の指定も可能です：

```json
{
  "mcpServers": {
    "api-server": {
      "type": "http",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

**サポートされる構文**:
- `${VAR}` - 環境変数VARを参照
- `${VAR:-default}` - 未設定時はデフォルト値を使用

**環境変数展開の適用場所**: `command`, `args`, `env`, `url`, `headers`

## 人気のMCPサーバー

### GitHub

```bash
claude mcp add github -- npx @anthropic-ai/mcp-server-github
```

提供ツール：
- リポジトリの閲覧・管理
- Issue/PRの操作
- ファイルの読み書き

### PostgreSQL

```bash
claude mcp add postgres -- npx @anthropic-ai/mcp-server-postgres
```

提供ツール：
- SQLクエリの実行
- スキーマの確認
- データの操作

> **注意**: データベースに対して直接クエリを実行すると、破壊的な変更を加えてしまう可能性があります。MCPを使ったデータベース操作はローカルでの検証程度にとどめましょう。

### Notion

```bash
claude mcp add notion -- npx @anthropic-ai/mcp-server-notion
```

提供ツール：
- ページの読み書き
- データベースのクエリ
- ブロックの操作

### Sentry

```bash
claude mcp add sentry -- npx @anthropic-ai/mcp-server-sentry
```

提供ツール：
- エラー情報の取得
- イベントの分析
- パフォーマンス監視

### Playwright（ブラウザ自動操作）

```bash
claude mcp add playwright -- npx @anthropic-ai/mcp-server-playwright
```

提供ツール：
- Webスクレイピング
- スクリーンショット撮影
- E2Eテスト実行
- フォーム自動入力

> **Note**: Claude Codeの「Claude in Chrome」機能でもChromeを操作できますが、クロスブラウザでの操作が必要な場合はPlaywright MCPが必要です。

### Context7（最新ドキュメント取得）

```bash
# APIキーなしで追加（レート制限あり）
claude mcp add context7 -- npx -y @upstash/context7-mcp

# APIキーありで追加（推奨）
claude mcp add context7 -- npx -y @upstash/context7-mcp --api-key YOUR_API_KEY

# 環境変数を使用する場合
claude mcp add context7 -- npx -y @upstash/context7-mcp --api-key $CONTEXT7_API_KEY
```

APIキーは [context7.com/dashboard](https://context7.com/dashboard) で無料取得可能。

提供ツール：
- 最新のライブラリドキュメントを取得
- LLMの学習データにない最新APIや使い方を補完

使用例：
```
> Next.js のApp Routerでミドルウェアを作って。use context7
> Context7 MCPを使ってReact 19の新機能を調べて
```

> **Note**: プロンプトの末尾に`use context7`を付けるか、「Context7 MCPを使って〜」と明示的に指示することで、最新ドキュメントを参照できます。

## MCPツールの使用

MCPサーバーが接続されると、Claude Codeは自動的にそのツールを使用できます：

```
> GitHubのissue #123の内容を確認して

> PostgreSQLデータベースからユーザー一覧を取得して

> Notionのページを更新して
```

## サブエージェントでのMCP使用

サブエージェントはメインスレッドのMCPツールを継承できます：

```markdown
---
name: github-reviewer
description: GitHubのPRをレビュー
# tools を省略すると、MCPツールを含むすべてのツールを継承
---
```

特定のMCPツールのみを許可する場合：

```markdown
---
name: db-analyst
tools: Read, mcp__postgres__query, mcp__postgres__schema
---
```

## トラブルシューティング

### サーバーが接続できない（disconnected）

```bash
# サーバーの状態を確認
/mcp

# 詳細ログを確認
claude --debug
```

起動コマンドをターミナルで直接実行して、エラー内容を確認：

```bash
# 例：Context7 MCPの場合
npx -y @upstash/context7-mcp
```

具体的なエラーメッセージが表示されるため、原因の特定が容易になります。

### npxが見つからない

Node.jsがインストールされているか確認：

```bash
node --version
which npx
```

Node.jsがインストールされていない場合は、[公式サイト](https://nodejs.org/)からインストールしてください。

### Claude Codeの再起動

設定変更後や原因不明の問題は、Claude Codeの再起動で解決することが多いです：

```bash
exit
claude
```

### MCPサーバーの再追加

それでも解決しない場合は、MCPサーバーを削除して再追加：

```bash
# 削除
claude mcp remove <サーバー名>

# 再追加
claude mcp add <サーバー名> -- <コマンド>
```

### 環境変数が読み込まれない

```bash
# 環境変数が設定されているか確認
echo $MY_API_KEY

# シェルの設定ファイルを再読み込み
source ~/.zshrc
```

### 権限エラー

MCPツールの使用には権限確認が必要な場合があります。初回利用時にツール使用を承認すると、`.claude/settings.local.json`に自動的に記録されます：

```json
{
  "permissions": {
    "allow": [
      "mcp__context7__resolve-library-id",
      "mcp__context7__query-docs",
      "mcp__github__*",
      "mcp__postgres__query"
    ]
  }
}
```

> **Tip**: 承認ダイアログで「Yes, and don't ask again for...」を選択すると、同じツールの再利用時に確認をスキップできます。新しいプロジェクトで最初から自動承認したい場合は、この設定をコピーして使い回せます。

## MCPプロンプトとリソース

### MCPプロンプト（スラッシュコマンドとして使用）

MCPサーバーが提供するプロンプトはスラッシュコマンドとして実行できます：

```
/mcp__github__list_prs           # 引数なし実行
/mcp__github__pr_review 456      # 引数付き実行
```

### MCPリソース（@メンションで参照）

MCPリソースは`@`メンションで参照できます：

```
> @github:issue://123 の分析結果を教えて
> @postgres:schema://users を @docs:file://database/user-model と比較
```

## 高度な設定

### MCP出力制限

```bash
# デフォルト: 最大25,000トークン
# 制限値の変更
export MAX_MCP_OUTPUT_TOKENS=50000
claude
```

### MCP接続タイムアウト

```bash
# タイムアウトを10秒に変更
MCP_TIMEOUT=10000 claude
```

### Windows対応（WSL不使用時）

```bash
# cmd /c ラッパーが必須
claude mcp add --transport stdio my-server -- cmd /c npx -y @some/package
```

## セキュリティ考慮事項

1. **認証情報の管理**: APIキーは環境変数で管理、設定ファイルにハードコードしない
2. **最小権限の原則**: 必要なMCPツールのみを許可
3. **プロジェクト設定のレビュー**: `.mcp.json`をコミットする前に内容を確認
4. **ローカル設定の活用**: 機密情報は`~/.claude.json`（Git管理外）に配置

## 参考リンク

- [MCP公式ドキュメント](https://modelcontextprotocol.io/introduction)
- [Claude Code MCPドキュメント](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [公式MCPサーバー一覧](https://github.com/modelcontextprotocol/servers)
- [Smithery（MCPレジストリ）](https://smithery.ai)
- [Docker MCP Catalog](https://hub.docker.com/mcp)
