# 10. プラグインの使い方

## プラグインとは

プラグインは、以下の5つの機能をパッケージ化して配布・共有できる仕組みです:
- カスタムコマンド（`commands/`）
- カスタムエージェント（`agents/`）
- スキル（`skills/`）
- フック（`hooks/`）
- MCPサーバー（`.mcp.json`）

## 公式マーケットプレイス

Claude Code には2つの公式マーケットプレイスがあります:

| マーケットプレイス | 説明 | 追加方法 |
|------------------|------|---------|
| `claude-plugins-official` | 起動時に自動で利用可能 | 追加不要 |
| `anthropics/claude-code` | Anthropicのデモ・サンプルプラグイン | `/plugin marketplace add anthropics/claude-code` |

## プラグインの管理

```bash
/plugin
```

インタラクティブUIが開き、**Tab** / **Shift+Tab** でタブ間を移動:

| タブ | 機能 |
|-----|------|
| **Discover** | 利用可能なプラグインを閲覧・検索 |
| **Installed** | インストール済みプラグインの管理 |
| **Marketplaces** | マーケットプレイスの追加・更新・削除 |
| **Errors** | プラグイン読み込みエラーの確認 |

## マーケットプレイスの管理

### マーケットプレイスの追加

```bash
# GitHub リポジトリから追加（推奨）
/plugin marketplace add owner/repo

# 任意のGitリポジトリ
/plugin marketplace add https://gitlab.com/company/plugins.git

# ローカルパスから追加（開発用）
/plugin marketplace add ./my-marketplace

# リモートマーケットプレイスURL
/plugin marketplace add https://url.of/marketplace.json
```

例:
```bash
# Anthropic公式マーケットプレイス
/plugin marketplace add anthropics/claude-code
```

### マーケットプレイスの一覧・更新・削除

```bash
# 設定済みマーケットプレイスを一覧表示
/plugin marketplace list

# マーケットプレイスメタデータを更新
/plugin marketplace update marketplace-name

# マーケットプレイスを削除
/plugin marketplace remove marketplace-name
```

## プラグインのインストール

### インタラクティブメニューから

```bash
/plugin
# → "Browse plugins" を選択
# → インストールしたいプラグインを選択
# → "Install now" を選択
```

### コマンドで直接インストール

```bash
/plugin install plugin-name@marketplace-name
```

### CLI からインストール（スコープ指定可能）

```bash
# ユーザースコープ（全プロジェクトで利用可能、デフォルト）
claude plugin install plugin-name@marketplace-name

# プロジェクトスコープ（チームで共有、.claude/settings.json）
claude plugin install plugin-name@marketplace-name --scope project

# ローカルスコープ（このプロジェクトのみ、gitignore）
claude plugin install plugin-name@marketplace-name --scope local
```

## プラグインの管理

### 有効化/無効化

```bash
# 無効化(アンインストールせず一時的に無効)
/plugin disable plugin-name@marketplace-name

# 再度有効化
/plugin enable plugin-name@marketplace-name
```

### アンインストール

```bash
/plugin uninstall plugin-name@marketplace-name

# エイリアス（remove, rm も使用可能）
/plugin remove plugin-name@marketplace-name
/plugin rm plugin-name@marketplace-name

# CLI からスコープ指定で削除
claude plugin uninstall plugin-name@marketplace-name --scope project
```

### インストール済みプラグインの確認

```bash
/plugin
# → "Manage installed plugins" を選択
```

## プラグインの内容確認

インストール後、プラグインが提供する機能を確認:

### コマンド
```bash
/help
# プラグインのコマンドが表示される
```

### サブエージェント
```bash
/agents
# プラグインのエージェントが表示される
```

### フック
プラグインのフックは自動的に有効化されます。

### スキル（Skill tool での呼び出し）

プラグインが提供するスキルは、Claudeが自動的に検出・使用します。
明示的に呼び出す場合:
```bash
Skill("plugin-name:skill-name")
```

例:
```bash
Skill("code-formatter:format-python")
Skill("security-tools:analyze-dependencies")
```

## 利用可能なプラグイン一覧

### コードインテリジェンス（LSP）

言語サーバープロトコルを使用したコード補完・型チェック:

| 言語 | プラグイン | 必要なバイナリ |
|-----|-----------|---------------|
| C/C++ | `clangd-lsp` | `clangd` |
| C# | `csharp-lsp` | `csharp-ls` |
| Go | `gopls-lsp` | `gopls` |
| Java | `jdtls-lsp` | `jdtls` |
| Lua | `lua-lsp` | `lua-language-server` |
| PHP | `php-lsp` | `intelephense` |
| Python | `pyright-lsp` | `pyright-langserver` |
| Rust | `rust-analyzer-lsp` | `rust-analyzer` |
| Swift | `swift-lsp` | `sourcekit-lsp` |
| TypeScript | `typescript-lsp` | `typescript-language-server` |

### 外部統合（MCP サーバー）

| カテゴリ | プラグイン |
|---------|-----------|
| バージョン管理 | `github`, `gitlab` |
| プロジェクト管理 | `atlassian` (Jira/Confluence), `asana`, `linear`, `notion` |
| デザイン | `figma` |
| インフラ | `vercel`, `firebase`, `supabase` |
| コミュニケーション | `slack` |
| 監視 | `sentry` |

### 開発ワークフロー

| プラグイン | 説明 |
|-----------|------|
| `commit-commands` | Git コミットワークフロー |
| `pr-review-toolkit` | PR レビュー専用エージェント |
| `agent-sdk-dev` | Claude Agent SDK 開発ツール |
| `plugin-dev` | プラグイン作成ツールキット |

### 出力スタイル

| プラグイン | 説明 |
|-----------|------|
| `explanatory-output-style` | 実装の選択について教育的インサイト |
| `learning-output-style` | スキル習得用インタラクティブモード |

## インストールスコープ

| スコープ | 保存場所 | 共有範囲 | 用途 |
|---------|---------|---------|------|
| `user` | `~/.claude/settings.json` | 全プロジェクト | 個人用プラグイン（デフォルト） |
| `project` | `.claude/settings.json` | チーム全員（Gitで共有） | チーム標準ツール |
| `local` | `.claude/settings.local.json` | この機械のみ（gitignore） | 個人的な実験 |
| `managed` | `managed-settings.json` | エンタープライズ管理 | 企業ポリシー適用 |

優先順位: `local` > `project` > `user`

## デバッグ

```bash
claude --debug
# プラグインの読み込み詳細を表示
```

## 自動更新の設定

マーケットプレイスとプラグインの自動更新を設定:

1. `/plugin` を実行
2. **Marketplaces** タブを選択
3. マーケットプレイスを選択
4. **Enable auto-update** または **Disable auto-update** を選択

| マーケットプレイス | デフォルト設定 |
|------------------|---------------|
| 公式 Anthropic | 自動更新 **有効** |
| サードパーティ・ローカル | 自動更新 **無効** |

すべての自動更新を無効化:
```bash
export DISABLE_AUTOUPDATER=1
```

## チーム向け設定

`.claude/settings.json` でマーケットプレイスとプラグインを事前設定:

```json
{
  "extraKnownMarketplaces": {
    "company-tools": {
      "source": {
        "source": "github",
        "repo": "your-org/claude-plugins"
      }
    }
  },
  "enabledPlugins": {
    "code-formatter@company-tools": true,
    "deployment-tools@company-tools": true
  }
}
```

チームメンバーがリポジトリを信頼すると、これらのプラグインが自動的にインストールされます。

## トラブルシューティング

### `/plugin` コマンドが認識されない

Claude Code バージョン **1.0.33 以上** が必要:

```bash
# Homebrew
brew upgrade claude-code

# npm
npm update -g @anthropic-ai/claude-code
```

### よくある問題

| 問題 | 原因 | 解決策 |
|------|------|--------|
| マーケットプレイスが読み込まれない | URL へのアクセス不可 | `.claude-plugin/marketplace.json` が存在するか確認 |
| プラグインインストール失敗 | ソース URL へのアクセス不可 | リポジトリが公開かアクセス権確認 |
| プラグイン Skills が表示されない | キャッシュの問題 | `rm -rf ~/.claude/plugins/cache` で再インストール |
| 「Executable not found」エラー | 言語サーバー未インストール | 必要なバイナリをインストール（LSP表参照） |

## 注意事項

⚠️ **セキュリティ**: プラグインは自動的にコードを実行するため:
- 信頼できるソースからのみインストール
- インストール前にプラグインの内容を確認
- 不要なプラグインは無効化

**コマンド名の衝突**: 複数プラグインで同名コマンドがある場合は `/plugin-name:command-name` で参照可能

## 次のステップ

- **11_creating_plugins.md** - 自分でプラグインを作成
- **12_settings.md** - プラグインの詳細設定
