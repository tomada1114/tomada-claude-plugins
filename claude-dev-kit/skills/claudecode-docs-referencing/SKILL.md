---
name: claudecode-docs-referencing
description: Claude Codeの公式ドキュメントをまとめた包括的なレファレンス集。インストール、基本操作、カスタマイズ、トラブルシューティング、実践的なTipsまでの情報を体系的に提供。Use PROACTIVELY when answering questions about Claude Code features, installation, configuration, hooks, MCP, sandbox, plugins, subagents, custom commands, or troubleshooting. Examples: <example>Context: User asks about feature user: 'Claude Codeのhooksってどう使うの？' assistant: 'I will use claudecode-docs-referencing skill' <commentary>Triggered by hooks question</commentary></example> <example>Context: User asks about setup user: 'MCPサーバーの設定方法を教えて' assistant: 'I will use claudecode-docs-referencing skill' <commentary>Triggered by MCP setup question</commentary></example>
---

# Claude Code Knowledge

## Overview

このスキルは、Claude Codeの公式ドキュメントの内容を体系的にまとめたレファレンス集です。Claude Codeに関する質問や、機能の使い方を知りたい場合に、関連するリファレンスファイルを読み込んで回答を提供します。

公式ドキュメントの正確な情報をベースとし、実践的なユースケースや開発現場での活用方法も含めて解説します。

## When to Use This Skill

以下のような場合にこのスキルを使用する：

- ユーザーがClaude Codeの機能について質問した時
- Claude Codeのインストールや設定方法を知りたい時
- スラッシュコマンド、フック、カスタムコマンドなどの使い方を確認したい時
- IDE連携やプラグインについて知りたい時
- MCP（Model Context Protocol）の設定を知りたい時
- サンドボックスやセキュリティ機能について確認したい時
- トラブルシューティングやベストプラクティスを確認したい時
- 実践的な開発ワークフローを構築したい時

## Reference Structure

このスキルには27個のリファレンスファイルが含まれています。ユーザーの質問内容に応じて、適切なリファレンスファイルを読み込んで情報を提供します。

### 概要
- **overview.md** - Claude Codeとは（概要、5つの主要能力、エージェント型の特徴）

### ツール比較
- **claude_code_vs_cursor.md** - Claude Code vs Cursor：使い分けガイド（CLIエージェント vs IDE統合の違い）
- **claude_code_vs_codex.md** - Claude Code vs Codex CLI：使い分けガイド（Anthropic vs OpenAIの比較）

### セットアップ関連
- **installation.md** - インストール方法（macOS/Ubuntu/Windows WSL/ネイティブWindows）
- **initial_setup.md** - 初期設定とAPI認証
- **pricing.md** - 料金体系（Pro/Max 5x/Max 20x、API従量課金との比較）

### 基本操作
- **basic_usage.md** - 基本的な使い方とコマンド
- **project_initialization.md** - プロジェクトの初期化（/init）
- **slash_commands.md** - スラッシュコマンド一覧と使い方

### カスタマイズ
- **custom_commands.md** - カスタムコマンドの作成（コンビニアナロジー解説付き）
- **subagents.md** - サブエージェントの活用（コンビニアナロジー解説付き）
- **hooks.md** - フックによる自動化
- **rules.md** - パス別ルールの定義（コンビニアナロジー解説付き）
- **skill.md** - スキルの使用方法と作成（Progressive Disclosure、Tool/Skills/MCP役割整理を含む）

### 外部連携
- **ide_integration.md** - IDEとの連携（VS Code/JetBrains）
- **mcp.md** - MCP（Model Context Protocol）サーバーの設定と使用
- **popular_mcp.md** - 人気MCPサーバー一覧（Context7、GitHub、PostgreSQL等）

### プラグインシステム
- **plugins.md** - プラグインの使い方
- **creating_plugins.md** - プラグインの作成方法

### 設定・セキュリティ
- **settings.md** - 設定ファイルの管理
- **sandbox.md** - サンドボックス機能によるセキュリティ保護

### モデル・パフォーマンス
- **model_setting.md** - モデル設定の管理と選択（opusplan等）
- **memory_management.md** - CLAUDE.mdの活用（コンビニアナロジー解説付き）

### トラブルシューティング・ベストプラクティス
- **troubleshooting.md** - よくある問題と解決法
- **best_practices.md** - 効率的な使い方のヒント

### 新機能（2025年）
- **new_features.md** - 最新機能（チェックポイント/リウインド、Slack連携）
- **on_the_web.md** - Claude Code on the Web（GitHub連携、並列実行、制限事項）

## How to Use References

When answering user questions about Claude Code:

1. Identify which aspect of Claude Code the user is asking about
2. Read the relevant reference file(s) from the `references/` directory
3. Provide a clear answer based on the information in the reference files
4. If multiple references are relevant, read them all to provide comprehensive guidance
5. Add practical tips and examples based on real-world usage when helpful

Example workflow:
- User asks: "How do I install Claude Code?" → Read `references/installation.md`
- User asks: "How do I create a custom command?" → Read `references/custom_commands.md`
- User asks: "What are hooks and how do I use them?" → Read `references/hooks.md`
- User asks: "How do I connect MCP servers?" → Read `references/mcp.md`
- User asks: "How does sandbox work?" → Read `references/sandbox.md`
- User asks: "My Claude Code isn't working" → Read `references/troubleshooting.md`
- User asks: "What's new in Claude Code?" → Read `references/new_features.md`

## Quick Reference: Key Features

### インストール
```bash
# macOS/Linux
curl -fsSL https://claude.ai/install.sh | bash

# Homebrew
brew install --cask claude-code

# Windows (PowerShell)
irm https://claude.ai/install.ps1 | iex
```

### 主要コマンド
- `/model` - モデル切り替え
- `/config` - 設定
- `/mcp` - MCPサーバー管理
- `/agents` - サブエージェント管理
- `/hooks` - フック設定
- `/sandbox` - サンドボックス設定
- `/clear` - コンテキストクリア
- `/compact` - 履歴圧縮
- `/rewind` - チェックポイントに戻る

### モデルエイリアス
- `default` - アカウントに応じた推奨設定
- `sonnet` - 日常的なコーディング
- `opus` - 複雑な推論
- `haiku` - 高速・効率的
- `opusplan` - プランモードでOpus、実行時Sonnet

### ショートカット
- `Cmd+Esc` / `Ctrl+Esc` - IDE連携起動
- `Cmd+Option+K` / `Alt+Ctrl+K` - ファイル参照
- `Esc Esc` - リウインド（チェックポイント選択）
- `Ctrl+R` - 省略内容展開
- `Ctrl+T` - TODOリスト表示

## Practical Tips & Best Practices

詳細な実践Tipsは [references/practical_tips.md](references/practical_tips.md) を参照してください。

### 主要なTips

- **コンテキスト管理**: `/clear`（完全クリア）、`/compact`（要約保持）を使い分け
- **ファイル参照**: `@`記法でプロジェクト内ファイルを参照
- **ショートカット**: `Ctrl+R`（展開）、`Ctrl+T`（TODO）、`Esc×2`（リウインド）
- **拡張思考**: 「熟考」「ultrathink」で深い分析モード
- **セッション継続**: `claude -c` で前回の会話から再開

## AI Assistant Instructions

このスキルが活性化された際の動作指針：

### 基本動作

1. **質問内容を分析**: ユーザーがClaude Codeのどの機能について質問しているか特定
2. **適切なリファレンスを読み込む**: `references/` ディレクトリから関連ファイルを読む
3. **公式情報を優先**: リファレンス内の情報を基に回答し、必要に応じて実践Tipsを補足

### リファレンス選択ガイド

| 質問のキーワード | 読むべきリファレンス |
|-----------------|---------------------|
| Claude Codeとは、概要、特徴、何ができる | `overview.md` |
| インストール、セットアップ | `installation.md`, `initial_setup.md` |
| hooks、フック、自動化 | `hooks.md` |
| MCP、サーバー接続 | `mcp.md`, `popular_mcp.md` |
| カスタムコマンド、コマンド作成 | `custom_commands.md` |
| サブエージェント、Agent | `subagents.md` |
| スキル | `skill.md` |
| プラグイン | `plugins.md`, `creating_plugins.md` |
| 設定、settings | `settings.md` |
| サンドボックス、セキュリティ | `sandbox.md` |
| トラブル、エラー、動かない | `troubleshooting.md` |
| 新機能、最新 | `new_features.md` |
| 料金、価格、課金 | `pricing.md` |
| IDE、VS Code、JetBrains | `ide_integration.md` |
| Cursor比較 | `claude_code_vs_cursor.md` |
| Codex比較 | `claude_code_vs_codex.md` |

### 常に行うこと

- 質問に関連するすべてのリファレンスを読み込む
- 公式ドキュメントの情報を正確に伝える
- 実践的なコード例を含めて回答する
- 複数トピックにまたがる場合は、関連する全ファイルを参照

### 行わないこと

- リファレンスを読まずに一般知識だけで回答する
- 古い情報や非公式の情報を提供する
- ユーザーの質問と無関係な機能を長々と説明する

## Important Notes

- Always read the relevant reference file(s) before answering questions about Claude Code
- The reference files contain official documentation content - prioritize this information over general knowledge
- If the user's question spans multiple topics, read all relevant reference files
- For complex questions, combine information from multiple reference files as needed
- When providing practical tips, clearly distinguish between official documentation and practical advice

