# Claude Code Sub-Agents: Official Documentation Summary

このドキュメントは、Claude Code 公式ドキュメント (https://docs.claude.com/en/docs/claude-code/sub-agents) からの重要情報をまとめたものです。

## サブエージェントとは

サブエージェントは、Markdown ファイル（YAML frontmatter付き）として定義される、Claude Code の専門化されたインスタンスです。特定のタスクやドメインに最適化され、適切なコンテキストで自動的に、または明示的に呼び出されます。

### 基本構造

```markdown
---
name: your-sub-agent-name
description: Description of when this subagent should be invoked
tools: tool1, tool2, tool3  # Optional
model: sonnet  # Optional
---

Your subagent's system prompt goes here.
```

## YAML Frontmatter フィールド

### 必須フィールド

| フィールド | 必須 | 詳細 |
|-----------|------|------|
| `name` | ✅ Yes | 小文字とハイフンのみ。識別子として使用 |
| `description` | ✅ Yes | 自然言語での目的説明 |

### オプションフィールド

| フィールド | 必須 | 詳細 |
|-----------|------|------|
| `tools` | ❌ No | カンマ区切りのツールリスト。省略時は全ツール継承 |
| `model` | ❌ No | `sonnet`, `opus`, `haiku`, `'inherit'` |

**公式からの重要な引用**:
> "You should only grant tools that are necessary for the subagent's purpose to improve security and focus."

## ファイル配置と優先順位

### 配置場所

1. **プロジェクトレベル**: `.claude/agents/` （最高優先度）
2. **ユーザーレベル**: `~/.claude/agents/` （低優先度）
3. **CLI定義**: `--agents` フラグ経由 （中優先度）

**優先順位**:
- 同名のサブエージェントが複数の場所に存在する場合、プロジェクトレベルが優先されます
- これにより、チーム全体でプロジェクト固有の設定を共有しつつ、個人的なカスタマイズも可能

### プロジェクトレベルのメリット

```
your-project/
└── .claude/
    └── agents/
        ├── code-reviewer.md
        ├── mobile-developer.md
        └── expo-mcp-specialist.md
```

**利点**:
- ✅ バージョン管理システム（git）でチーム全員と共有
- ✅ プロジェクト固有のコンテキストに最適化
- ✅ CI/CD パイプラインでも利用可能
- ✅ チーム全体で一貫したワークフロー

## ツール設定

### ツールの継承

`tools` フィールドを省略すると、サブエージェントは親セッションの全ツールにアクセスできます。これには MCP サーバーツールも含まれます。

```yaml
# すべてのツールにアクセス可能
---
name: full-access-agent
description: Has access to all available tools
---
```

### ツール制限

セキュリティと集中のため、必要なツールのみを指定することを推奨します。

```yaml
# 読み取り専用
---
name: read-only-agent
description: Can only read and search files
tools: Read, Grep, Glob
---

# コード変更可能
---
name: code-modifier
description: Can read and modify code
tools: Read, Write, Edit, Bash
---

# MCP統合
---
name: mcp-agent
description: Integrates with Expo MCP
tools: Read, Write, Edit, Bash, mcp__expo-mcp__*
---
```

**ワイルドカード**:
- `mcp__service-name__*` で特定MCPサービスの全ツールにアクセス
- 例: `mcp__expo-mcp__*` は expo-mcp の全ツールを許可

## 呼び出しメカニズム

### 自動呼び出し

Claude は、ユーザーのリクエストとサブエージェントの `description` をマッチングし、適切なエージェントを自動的に選択・呼び出します。

**公式ガイダンス**:
> "Claude delegates tasks matching agent descriptions proactively"

**効果的な自動呼び出しのポイント**:
1. Description に豊富なトリガーワードを含める
2. `Use PROACTIVELY` パターンで積極性を示す
3. 具体的なユースケースを列挙
4. ユーザーが自然に使う言葉を含める

### 明示的呼び出し

ユーザーが直接エージェント名を指定して呼び出すことも可能です。

```
> Use the code-reviewer subagent to check my changes
```

### 管理コマンド

`/agents` コマンドで、サブエージェントの作成・編集・管理を行う包括的なインターフェースが提供されます。

## ベストプラクティス（公式推奨）

### 1. Claude に生成させる

**公式推奨**:
> "Start with Claude generation: Generate initial configurations with Claude, then customize for your needs"

最初の設定ファイルは Claude に生成させ、その後プロジェクト固有のニーズに合わせてカスタマイズします。

### 2. 単一責任

**公式推奨**:
> "Single responsibility: Design focused agents rather than multipurpose ones"

1つのエージェントに1つの明確な責任を持たせます。複雑な機能は複数のエージェントに分割します。

### 3. 詳細なプロンプト

**公式推奨**:
> "Detailed prompts: Include specific instructions, examples, and constraints in system prompts"

システムプロンプトには以下を含めます:
- 具体的な指示
- 実例
- 制約事項

### 4. アクセス制御

**公式推奨**:
> "Controlled access: Limit tool permissions to necessary capabilities only"

必要最小限のツールのみを付与し、セキュリティを確保します。

### 5. バージョン管理

**公式推奨**:
> "Version control: Store project subagents in repositories for team collaboration"

プロジェクトレベルのサブエージェントは git などのバージョン管理システムで管理し、チーム全体で共有します。

## モデル選択

### 利用可能なモデル

| モデル | 特徴 | 推奨用途 |
|--------|------|---------|
| `sonnet` | バランスの取れた性能 | 一般的なタスク（デフォルト） |
| `opus` | 最高品質、最も高度 | 複雑な分析、アーキテクチャレビュー |
| `haiku` | 最速、軽量 | シンプルなチェック、高速レビュー |
| `'inherit'` | 親セッションから継承 | セッション全体で統一したい場合 |

### 選択ガイドライン

```yaml
# 一般的なコードレビュー
model: sonnet

# 複雑なアーキテクチャ分析
model: opus

# 高速な構文チェック
model: haiku

# 親セッションのモデルを使用
model: inherit
```

## ファイル構造の例

### シンプルな構成

```
project/
└── .claude/
    └── agents/
        └── code-reviewer.md
```

### 複雑な構成

```
project/
└── .claude/
    └── agents/
        ├── code-reviewer.md
        ├── mobile-developer.md
        ├── expo-mcp-specialist.md
        ├── architect-reviewer.md
        ├── test-engineer.md
        ├── security-auditor.md
        ├── performance-profiler.md
        └── documentation-expert.md
```

## セキュリティ考慮事項

### ツール権限の原則

1. **最小権限**: 必要最小限のツールのみ付与
2. **読み取り専用タスク**: `Read, Grep, Glob` のみ
3. **変更タスク**: `Read, Write, Edit` を追加
4. **実行タスク**: 慎重に `Bash` を追加
5. **MCP統合**: 必要なMCPツールのみ指定

### 危険なパターン（避けるべき）

```yaml
# ❌ 悪い例: すべてのツールを無制限に付与
---
name: dangerous-agent
description: Can do anything
# tools フィールドを省略 → 全ツールにアクセス可能
---

# ✅ 良い例: 必要なツールのみ
---
name: safe-agent
description: Reviews code without modifications
tools: Read, Grep, Glob
---
```

## パフォーマンス最適化

### モデル選択による最適化

```yaml
# コスト重視: haiku
model: haiku

# 品質重視: opus
model: opus

# バランス: sonnet（デフォルト）
model: sonnet
```

### ツール制限による最適化

不要なツールへのアクセスを制限することで:
- ✅ エージェントが適切なツールに集中
- ✅ 誤ったツール使用を防止
- ✅ セキュリティリスク低減

## チーム協業のベストプラクティス

### 1. プロジェクトレベルで管理

```bash
# サブエージェントをプロジェクトに追加
git add .claude/agents/new-agent.md
git commit -m "feat: add new-agent for [purpose]"
git push
```

### 2. ドキュメント化

README.md やプロジェクトドキュメントに、利用可能なサブエージェントと使い方を記載します。

### 3. 命名規則

チーム内で一貫した命名規則を採用:
- `[domain]-[role]`: `mobile-developer`, `backend-architect`
- `[task]-[action]`: `code-reviewer`, `test-runner`

### 4. レビュープロセス

新しいサブエージェントはコードと同様にレビューします:
- Description の明確さ
- ツール権限の適切性
- プロンプトの品質

## 公式リソース

- **公式ドキュメント**: https://docs.claude.com/en/docs/claude-code/sub-agents
- **Claude Code CLI**: `claude --help` でヘルプ表示
- **エージェント管理**: `/agents` コマンド

---

この要約は公式ドキュメントの重要ポイントを抽出したものです。最新情報は公式ドキュメントを参照してください。
