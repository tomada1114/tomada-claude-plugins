# MCP Server Reference

Model Context Protocol (MCP) サーバーの詳細リファレンス。

## MCP Configuration Format

### Command-based (npx)

```json
{
  "server-name": {
    "command": "npx",
    "args": ["-y", "@package/server"],
    "env": {
      "API_KEY": "YOUR_KEY_HERE"
    },
    "description": "What this server does"
  }
}
```

### HTTP-based

```json
{
  "server-name": {
    "type": "http",
    "url": "https://api.example.com/mcp",
    "description": "What this server does"
  }
}
```

## Configuration File

`~/.claude.json`:

```json
{
  "mcpServers": {
    "github": { ... },
    "memory": { ... }
  }
}
```

## Context Window Warning

**重要**: MCPが多すぎるとコンテキストウィンドウが縮小します。

| MCPs Enabled | Context Window |
|--------------|----------------|
| 0-5 | ~200k |
| 5-10 | ~150k |
| 10-15 | ~100k |
| 15+ | ~70k or less |

**推奨**:
- 10個未満/プロジェクト
- 80ツール未満をアクティブに

## Disabling MCPs per Project

```json
{
  "projects": {
    "/path/to/project": {
      "disabledMcpServers": ["cloudflare", "railway", "supabase"]
    }
  }
}
```

## Available MCP Servers

### github

**Type**: npx command

**Purpose**: GitHub操作 - PR、Issue、リポジトリ

**Configuration**:
```json
{
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_TOKEN"
    }
  }
}
```

**Required**: `GITHUB_PERSONAL_ACCESS_TOKEN`

**Capabilities**:
- PR作成/更新/レビュー
- Issue管理
- リポジトリ情報取得
- ファイル操作

---

### memory

**Type**: npx command

**Purpose**: セッション間の永続メモリ

**Configuration**:
```json
{
  "memory": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-memory"]
  }
}
```

**Required**: なし

**Capabilities**:
- キー/バリュー保存
- セッション間でのデータ保持
- コンテキストの継続

---

### sequential-thinking

**Type**: npx command

**Purpose**: 連鎖思考（Chain-of-Thought）推論

**Configuration**:
```json
{
  "sequential-thinking": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
  }
}
```

**Required**: なし

**Capabilities**:
- 段階的な推論
- 複雑な問題の分解
- 思考プロセスの可視化

---

### supabase

**Type**: npx command

**Purpose**: Supabaseデータベース操作

**Configuration**:
```json
{
  "supabase": {
    "command": "npx",
    "args": ["-y", "@supabase/mcp-server-supabase@latest", "--project-ref=YOUR_PROJECT_REF"]
  }
}
```

**Required**: `--project-ref`

**Capabilities**:
- データベースクエリ
- テーブル操作
- RLS確認
- スキーマ情報

---

### vercel

**Type**: HTTP

**Purpose**: Vercelデプロイメントとプロジェクト管理

**Configuration**:
```json
{
  "vercel": {
    "type": "http",
    "url": "https://mcp.vercel.com"
  }
}
```

**Required**: なし（ブラウザ認証）

**Capabilities**:
- デプロイメント状態
- プロジェクト管理
- 環境変数
- ログ確認

---

### railway

**Type**: npx command

**Purpose**: Railwayデプロイメント

**Configuration**:
```json
{
  "railway": {
    "command": "npx",
    "args": ["-y", "@railway/mcp-server"]
  }
}
```

**Required**: なし（CLI認証）

**Capabilities**:
- サービス管理
- デプロイメント
- 環境変数
- ログ確認

---

### cloudflare

**Type**: HTTP (multiple endpoints)

**Purpose**: Cloudflareサービス

**Configuration**:
```json
{
  "cloudflare-docs": {
    "type": "http",
    "url": "https://docs.mcp.cloudflare.com/mcp"
  },
  "cloudflare-workers-builds": {
    "type": "http",
    "url": "https://builds.mcp.cloudflare.com/mcp"
  },
  "cloudflare-workers-bindings": {
    "type": "http",
    "url": "https://bindings.mcp.cloudflare.com/mcp"
  },
  "cloudflare-observability": {
    "type": "http",
    "url": "https://observability.mcp.cloudflare.com/mcp"
  }
}
```

**Note**: 4つのエンドポイントがあり、必要なものだけ有効化

---

### context7

**Type**: npx command

**Purpose**: ライブドキュメント検索

**Configuration**:
```json
{
  "context7": {
    "command": "npx",
    "args": ["-y", "@context7/mcp-server"]
  }
}
```

**Required**: なし

**Capabilities**:
- ライブラリドキュメント検索
- 最新API情報
- コード例の取得

---

### filesystem

**Type**: npx command

**Purpose**: ファイルシステム操作

**Configuration**:
```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/your/projects"]
  }
}
```

**Required**: パス指定

**Capabilities**:
- ファイル読み書き
- ディレクトリ操作
- 検索

---

## Recommended Configurations

### Minimal (3 MCPs)

```json
{
  "mcpServers": {
    "github": { ... },
    "memory": { ... },
    "sequential-thinking": { ... }
  }
}
```

### Frontend Development (5 MCPs)

```json
{
  "mcpServers": {
    "github": { ... },
    "memory": { ... },
    "vercel": { ... },
    "context7": { ... },
    "sequential-thinking": { ... }
  }
}
```

### Backend Development (5 MCPs)

```json
{
  "mcpServers": {
    "github": { ... },
    "memory": { ... },
    "supabase": { ... },
    "railway": { ... },
    "sequential-thinking": { ... }
  }
}
```

## Troubleshooting

### MCP Server Not Starting

1. Node.js 18+ がインストールされているか確認
2. `npx` が動作するか確認
3. API キーが正しいか確認
4. ネットワーク接続を確認

### Too Many Tools Error

1. 未使用のMCPを無効化
2. プロジェクトごとに `disabledMcpServers` を設定
3. 10個未満に制限

### Authentication Issues

1. トークンの有効期限を確認
2. 必要な権限があるか確認
3. 再認証を試す
