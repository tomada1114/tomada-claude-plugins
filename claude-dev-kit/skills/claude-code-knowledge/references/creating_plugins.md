# 11. プラグインの作成

## プラグインとは

以下の5つの機能をパッケージ化して配布できる仕組みです:
- カスタムコマンド（`commands/`）
- カスタムエージェント（`agents/`）
- スキル（`skills/`）
- フック（`hooks/`）
- MCPサーバー（`.mcp.json`）

## 基本構造

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json       # 必須: プラグインマニフェスト
├── commands/              # オプション: カスタムコマンド
│   └── hello.md
├── agents/                # オプション: サブエージェント
│   └── helper.md
├── skills/                # オプション: スキル
│   └── my-skill/
│       └── SKILL.md
├── hooks/                 # オプション: フック設定
│   └── hooks.json
├── .mcp.json              # オプション: MCPサーバー定義
├── scripts/               # オプション: フック用スクリプト
│   └── format-code.sh
└── README.md              # 推奨: 使い方の説明
```

**重要**: `.claude-plugin/` 内には `plugin.json` のみ。他のディレクトリはすべてプラグインルートに配置。

## 簡単なプラグインを作成

### 1. ディレクトリ構造を作成

```bash
mkdir my-first-plugin
cd my-first-plugin
mkdir .claude-plugin commands
```

### 2. plugin.json を作成

```json
{
  "name": "my-first-plugin",
  "description": "My first test plugin",
  "version": "1.0.0",
  "author": {
    "name": "Your Name",
    "email": "you@example.com"
  },
  "homepage": "https://example.com/docs",
  "repository": "https://github.com/you/my-first-plugin",
  "license": "MIT",
  "keywords": ["utility", "productivity"]
}
```

**コンポーネントパスフィールド（オプション）**:
```json
{
  "name": "my-plugin",
  "commands": ["./custom/commands/special.md"],
  "agents": "./custom/agents/",
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json"
}
```

デフォルトディレクトリ（`commands/`, `agents/` 等）が存在すれば自動的にロードされます。

### 3. コマンドを追加

**commands/hello.md**:
```markdown
---
description: Greet the user
---

# Hello Command

Greet the user warmly and ask how you can help them today.
```

## マーケットプレイスの作成

プラグインをインストール可能にするため、マーケットプレイスを作成:

### 1. マーケットプレイス構造

```
test-marketplace/
├── .claude-plugin/
│   └── marketplace.json
└── my-first-plugin/
    └── (プラグインファイル)
```

### 2. marketplace.json を作成

```json
{
  "name": "test-marketplace",
  "owner": {
    "name": "Your Name"
  },
  "plugins": [
    {
      "name": "my-first-plugin",
      "source": "./my-first-plugin",
      "description": "My first test plugin"
    }
  ]
}
```

## プラグインのテスト

### 1. ローカルマーケットプレイスを追加

```bash
claude
/plugin marketplace add /path/to/test-marketplace
```

### 2. プラグインをインストール

```bash
/plugin install my-first-plugin@test-marketplace
```

### 3. Claude を再起動して確認

```bash
exit
claude
/hello
```

## スキルを提供する

**skills/code-reviewer/SKILL.md**:
```markdown
---
name: code-reviewer
description: Use PROACTIVELY when reviewing code for best practices and potential issues
allowed-tools: Read, Grep, Glob
---

# Code Reviewer Skill

コードレビューを実行し、ベストプラクティスと潜在的な問題をチェックします。
```

**SKILL.md のフィールド**:
| フィールド | 必須 | 説明 |
|-----------|------|------|
| `name` | はい | 小文字、数字、ハイフンのみ |
| `description` | はい | 用途と使用タイミング（最大1024文字） |
| `allowed-tools` | いいえ | カンマ区切りのツール名 |

## MCPサーバーを提供する

**.mcp.json**（プラグインルートに配置）:
```json
{
  "mcpServers": {
    "plugin-database": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": {
        "DB_PATH": "${CLAUDE_PLUGIN_ROOT}/data"
      }
    }
  }
}
```

**環境変数**: `${CLAUDE_PLUGIN_ROOT}` でプラグインディレクトリの絶対パスを参照。

## 実用的なプラグインの例

### コード品質チェックプラグイン

**agents/quality-checker.md**:
```markdown
---
name: quality-checker
description: Use PROACTIVELY when reviewing code quality, checking naming conventions, complexity, and duplication
tools: Read, Grep, Glob
model: sonnet
permissionMode: default
---

# Quality Checker

コードの品質をチェックします:
- 命名規則
- 複雑度
- 重複コード
- コメントの質
```

**エージェントのYAMLフロントマターフィールド**:
| フィールド | 必須 | 説明 |
|-----------|------|------|
| `name` | はい | 小文字とハイフンのみ |
| `description` | はい | 「use PROACTIVELY」を含めると自動起動 |
| `tools` | いいえ | カンマ区切りのツール名（省略時は全ツール継承） |
| `model` | いいえ | `sonnet`, `opus`, `haiku`, `inherit` |
| `permissionMode` | いいえ | `default`, `acceptEdits`, `bypassPermissions`, `plan` |
| `skills` | いいえ | カンマ区切りのスキル名

**hooks/hooks.json**:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "eslint $file && echo 'Quality check passed'"
          }
        ]
      }
    ]
  }
}
```

## プラグインの配布

### GitHub で配布

1. GitHub リポジトリを作成
2. プラグインをプッシュ
3. ユーザーに共有:

```bash
/plugin marketplace add username/repo-name
/plugin install plugin-name@username
```

### ローカルで配布

チーム内のローカルパスで共有:

```bash
/plugin marketplace add /shared/plugins/marketplace
```

## ベストプラクティス

### 1. 明確な説明を書く
- plugin.json の description
- コマンドの description
- README.md の作成

### 2. バージョン管理
```json
{
  "version": "1.0.0"  // セマンティックバージョニング
}
```

### 3. 依存関係を明記
README.md に必要なツールを記載:
```markdown
## Requirements
- Node.js 18+
- ESLint
- Prettier
```

### 4. 例を提供
README.md に使用例を含める

### 5. 小さく始める
最初はシンプルなコマンド1つから

## デバッグ

```bash
claude --debug
```

出力内容:
- プラグインの読み込み状況
- マニフェストエラー
- コマンド・エージェント・フック登録状況
- MCPサーバー初期化状況

**よくある問題**:
| 問題 | 原因 | 解決策 |
|------|------|--------|
| プラグインが読み込まれない | 無効な plugin.json | JSON シンタックスを検証 |
| コマンドが表示されない | 間違ったディレクトリ構造 | `commands/` がプラグインルート配下に存在することを確認 |
| フックが動作しない | スクリプトが実行可能でない | `chmod +x script.sh` |
| MCPサーバーが失敗 | 絶対パス使用 | `${CLAUDE_PLUGIN_ROOT}` を使用 |

## 注意事項

⚠️ **セキュリティ**:
- フックは自動実行されるため、信頼できるコードのみ
- スクリプトの内容を必ず確認
- 機密情報を含めない

**コマンド名の衝突**: 複数プラグインで同名コマンドがある場合は `/plugin-name:command-name` で参照可能。

## 参考リンク

詳細は公式ドキュメント:
- プラグインリファレンス
- プラグインマーケットプレイス
- コマンド作成ガイド
- サブエージェント作成ガイド
- フック作成ガイド
