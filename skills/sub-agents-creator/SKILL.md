---
name: sub-agents-creator
description: Create effective Claude Code sub-agents for project-level workflows. Use PROACTIVELY when creating new sub-agents, improving existing agents, understanding YAML frontmatter structure (name, description, tools, model, color), designing agent activation strategies with CLAUDE.md integration, writing effective descriptions with PROACTIVELY/MUST BE USED/<example> patterns, or troubleshooting agent activation issues (~25% activation rate problem).
---

# Sub-Agents Creator

このスキルは、プロジェクト固有のワークフローを自動化するための効果的なサブエージェントを作成する方法を提供します。

## このスキルを使うべき時

- 新しいサブエージェントをゼロから作成する
- 既存のサブエージェントを改善・更新する
- YAML frontmatter（name, description, tools, model, color）の構造を理解する
- 積極的呼び出し（PROACTIVELY/MUST BE USED）パターンの description を書く
- **`<example>` タグを使った発動率向上**
- **CLAUDE.md との連携による100%発動保証**
- サブエージェントが起動しない問題をデバッグする（**発動率~25%問題の解決**）
- プロジェクトチームで共有可能なエージェントを設計する

## サブエージェントとは

サブエージェントは、特定のタスクやドメインに特化したClaude Codeの専門化インスタンスです。Markdownファイル（YAML frontmatter付き）として定義され、適切なコンテキストで自動的に、または明示的に呼び出されます。

### スキルとの違い

| 特徴 | スキル | サブエージェント |
|------|-------|-----------------|
| ファイル形式 | SKILL.md (YAML frontmatter) | agent-name.md (YAML frontmatter) |
| 配置場所 | `.claude/skills/` | `.claude/agents/` |
| 主な目的 | 知識・ガイドラインの提供 | タスク実行の自動化 |
| ツール制限 | `allowed-tools` | `tools` |
| 呼び出し | コンテキストマッチング | コンテキスト + 明示的 |

## ファイル配置と優先順位

### プロジェクトレベル（推奨）
```
your-project/.claude/agents/
├── code-reviewer.md
├── mobile-developer.md
└── expo-mcp-specialist.md
```

**メリット**:
- チーム全体で共有される（git commit可能）
- プロジェクト固有のコンテキストに最適化
- CI/CDパイプラインでも利用可能

### ユーザーレベル
```
~/.claude/agents/
├── personal-note-taker.md
└── documentation-writer.md
```

**メリット**:
- 全プロジェクトで利用可能
- 個人的なワークフローに最適

**優先順位**: プロジェクトレベル > ユーザーレベル（同名の場合、プロジェクトレベルが優先）

## 重要: 発動率の課題と解決策

### 問題: サブエージェントの発動率は約25%

description のキーワードマッチングに依存するため、ユーザーの質問が説明文と完全に一致しない場合、エージェントが起動されません。

### 解決策: CLAUDE.md で起動条件を明示

**推奨ディレクトリ構成**:
```
your-project/
├── CLAUDE.md                    # 全体ルール + エージェント起動条件
├── .claude/
│   ├── settings.json            # 権限設定
│   ├── agents/                  # タスク専用エージェント
│   │   ├── code-reviewer.md
│   │   └── mobile-developer.md
│   └── skills/                  # エージェント間の共有知識
│       └── domain-knowledge/
│           └── SKILL.md
```

**CLAUDE.md への起動条件記述**（発動率100%）:

```markdown
# CLAUDE.md

## Sub-Agent Activation Rules

ユーザーが以下を尋ねた場合、必ず Task ツールで指定のエージェントを使用：

- **コードレビュー、品質チェック、セキュリティ** → `code-reviewer` エージェント
- **React Native、Expo、モバイル開発** → `mobile-developer` エージェント
- **Expo MCP、スクリーンショット、UI検証** → `expo-mcp-specialist` エージェント
```

この方法により、description のマッチングに依存せず、確実にエージェントが起動されます。

## YAML Frontmatter 完全ガイド

### 必須フィールド

#### name（必須）
エージェントの一意な識別子。

**規則**:
- 小文字のみ
- ハイフン（`-`）で単語を区切る
- 数字も使用可能
- 最大64文字
- スペース、アンダースコア、大文字は不可

**例**:
```yaml
name: code-reviewer          # ✅ 良い
name: mobile-developer       # ✅ 良い
name: expo-mcp-specialist    # ✅ 良い
name: Code_Reviewer          # ❌ 大文字とアンダースコア
name: code reviewer          # ❌ スペース
```

#### description（必須）
エージェントがいつ、なぜ呼び出されるべきかを説明。

**規則**:
- 最大1024文字
- 「何をするか」+「いつ使うか」を含む
- トリガーワードを豊富に含める
- `Use PROACTIVELY` で自動呼び出しを促す
- `MUST BE USED` でより強い義務化

**詳細**: `references/description-writing-guide.md` を参照

**基本例**:
```yaml
description: Expert code review specialist for quality, security, and maintainability. Use PROACTIVELY after writing or modifying code to ensure high development standards.
```

**`<example>` タグによる発動率向上**:

```yaml
description: Expert code review specialist. Use PROACTIVELY after writing or modifying code. Examples: <example>Context: User finished writing code user: 'このコードをレビューして' assistant: 'I will use code-reviewer agent' <commentary>Triggered by code review request</commentary></example>
```

`<example>` タグを含めることで、Claude がどのような状況でエージェントを使うべきかを具体例で学習し、発動率が向上します。

### オプションフィールド

#### tools（オプション）
エージェントがアクセスできるツールを制限。

**指定方法**:
- カンマ区切りのリスト
- ワイルドカード（`*`）使用可能
- 省略時は全ツール利用可能

**例**:
```yaml
# 読み取り専用エージェント
tools: Read, Grep, Glob

# Bash系のみ
tools: Bash, BashOutput

# MCP統合エージェント
tools: Read, Write, Edit, Bash, mcp__expo-mcp__*

# 全ツール（デフォルト）
# tools フィールドを省略
```

**ベストプラクティス**:
- セキュリティのため、必要最小限のツールのみ付与
- 読み取り専用タスクは `Read, Grep, Glob` のみ
- コード変更タスクは `Read, Edit, Write` を追加
- MCPツールは `mcp__service-name__*` でワイルドカード指定

#### model（オプション）
使用するClaude モデル。

**選択肢**:
- `sonnet`（デフォルト）: バランスの取れた性能
- `opus`: 最高品質、複雑なタスク向け
- `haiku`: 高速、シンプルなタスク向け
- `inherit`: 親セッションのモデルを継承

**例**:
```yaml
model: sonnet    # 一般的な用途
model: opus      # アーキテクチャレビュー、複雑な分析
model: haiku     # 高速レビュー、簡単なチェック
```

#### color（オプション）
UI表示用の色指定。

**利用可能な色**:
- `gray`, `blue`, `green`, `red`, `yellow`, `purple`

**例**:
```yaml
color: gray    # ニュートラル
color: blue    # 技術系
color: green   # 成功・承認系
color: red     # 警告・セキュリティ
```

**用途**:
- チーム内でエージェントタイプを視覚的に区別
- 重要度・カテゴリの表現

## サブエージェント作成のステップ

### ステップ1: 目的とスコープの定義

**問い**:
1. このエージェントは何をするのか？（単一責任）
2. いつ呼び出されるべきか？（トリガーシナリオ）
3. どのツールが必要か？（最小権限）
4. 誰が使うか？（個人 or チーム）

**例**:
- **目的**: コミット前のコードレビューを自動化
- **スコープ**: git diffを分析し、品質・セキュリティ問題を検出
- **ツール**: `Read, Grep, Bash`
- **対象**: チーム全員（プロジェクトレベル）

### ステップ2: ファイルの作成

**プロジェクトレベル**:
```bash
# プロジェクトディレクトリで実行
mkdir -p .claude/agents
touch .claude/agents/your-agent-name.md
```

**ユーザーレベル**:
```bash
mkdir -p ~/.claude/agents
touch ~/.claude/agents/your-agent-name.md
```

### ステップ3: YAML Frontmatter の記述

**テンプレート**:
```yaml
---
name: your-agent-name
description: [What it does]. Use PROACTIVELY for [when to use], [specific scenarios].
tools: Read, Write, Edit, Bash
model: sonnet
color: blue
---
```

**重要**: `description` の書き方で呼び出し頻度が大きく変わります。詳細は `references/description-writing-guide.md` を参照してください。

### ステップ4: プロンプトの記述

**構造**:
```markdown
---
[YAML frontmatter]
---

You are a [role description].

## Core Expertise
[List of specialized knowledge areas]

## When to Use
[Specific scenarios when this agent should be invoked]

## Workflow
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Output Format
[Expected output structure]

## Best Practices
- [Practice 1]
- [Practice 2]
```

**テンプレート集**: `references/agent-templates.md` に複数のパターンを用意しています。

### ステップ5: テストと反復

**テスト方法**:
1. **明示的呼び出し**: `> Use the [agent-name] agent to [task]`
2. **自動呼び出し**: descriptionに含まれるキーワードを使ってタスクを依頼
3. **期待動作の確認**: 適切なツールを使い、期待される出力を生成するか

**改善ポイント**:
- descriptionにトリガーワードを追加
- ワークフローを明確化
- 不要なツールを削除

## ベストプラクティス

### 1. 単一責任の原則

**✅ 良い例**:
```yaml
name: code-reviewer
description: Expert code review specialist for quality, security, and maintainability.
```

**❌ 悪い例**:
```yaml
name: developer-helper
description: Helps with coding, testing, documentation, and deployment.
# 範囲が広すぎる - 複数のエージェントに分割すべき
```

### 2. 明確なトリガーワード

**✅ 良い例**:
```yaml
description: Cross-platform mobile development specialist for React Native and Flutter. Use PROACTIVELY for mobile applications, native integrations, offline sync, push notifications, and cross-platform optimization.
# "React Native", "Flutter", "mobile", "native", "push notifications" などのキーワード
```

**❌ 悪い例**:
```yaml
description: Helps with app development.
# 曖昧すぎる
```

### 3. 積極的呼び出しパターン

**レベル1: 通常**
```yaml
description: Code review specialist. Use when reviewing code changes.
```

**レベル2: 積極的**
```yaml
description: Code review specialist. Use PROACTIVELY after writing or modifying code.
```

**レベル3: 強制的**
```yaml
description: Expo MCP specialist. MUST BE USED for all Expo MCP-related tasks.
```

**レベル4: CLAUDE.md 連携（発動率100%保証）**
```yaml
# エージェントファイルの description
description: Expo MCP specialist for screenshot capture and UI verification.

# CLAUDE.md に追記
## Agent Activation
Expo MCP、スクリーンショット、UI検証 → `expo-mcp-specialist` を必ず使用
```

詳細: `references/description-writing-guide.md`

### 4. 最小権限の原則

```yaml
# ✅ 読み取り専用タスク
tools: Read, Grep, Glob

# ✅ レビュー＋提案タスク
tools: Read, Grep, Glob, Write

# ❌ 不要なツールまで付与
tools: Read, Write, Edit, Bash, Grep, Glob, WebFetch, WebSearch
```

### 5. プロジェクトコンテキストの活用

```markdown
## Integration with This Project

### Project Context
- Clean Architecture with DDD
- Uses expo-dev-client (not Expo Go)
- NativeWind + GlueStack UI

### When to Use in This Project
1. **Feature Implementation**: After domain layer changes
2. **UI Verification**: Before PR submission
```

## トラブルシューティング

### 問題: エージェントが呼び出されない（発動率~25%問題）

**原因1: descriptionが不十分**

```yaml
# ❌ 悪い
description: Helps with code review

# ✅ 良い
description: Expert code review specialist. Use PROACTIVELY after writing or modifying code for quality, security, and maintainability checks.

# ✅ さらに良い（<example>タグ付き）
description: Expert code review specialist. Use PROACTIVELY after writing or modifying code. Examples: <example>Context: User finished code user: 'レビューして' assistant: 'I will use code-reviewer' <commentary>Code review trigger</commentary></example>

# ✅ 最も確実（CLAUDE.md連携）
# → CLAUDE.mdに起動条件を明記
```

**原因2: nameに無効な文字**

```yaml
# ❌ 悪い
name: Code_Reviewer    # アンダースコア
name: code reviewer    # スペース

# ✅ 良い
name: code-reviewer
```

**原因3: YAMLシンタックスエラー**

```yaml
# ❌ 悪い（タブ文字使用）
---
name:	code-reviewer

# ✅ 良い（スペース使用）
---
name: code-reviewer
```

### 問題: 間違ったタイミングで呼び出される

**原因: descriptionが広すぎる**

```yaml
# ❌ 悪い - あらゆるファイル操作で呼ばれる
description: Helps with files

# ✅ 良い - 特定のシナリオに限定
description: Analyze CSV files and generate statistical reports. Use when working with data analysis, spreadsheets, or CSV processing tasks.
```

### 問題: ツール制限が効かない

**原因: tools指定ミス**

```yaml
# ❌ 悪い - スペースなし
tools: Read,Write,Edit

# ✅ 良い - カンマ+スペース
tools: Read, Write, Edit
```

## 実例とテンプレート

### 参照ドキュメント

1. **description-writing-guide.md**:
   - 積極的呼び出しパターン
   - `<example>` タグの使い方
   - トリガーワード戦略

2. **agent-templates.md**:
   - シンプルレビュアー型
   - ドメイン専門家型
   - MCP統合型
   - アーキテクチャレビュアー型

3. **official-docs-summary.md**:
   - Claude Code 公式ドキュメント要約
   - ファイル配置と優先順位
   - 呼び出しメカニズム

4. **real-world-examples.md**:
   - 実プロジェクトからの実例
   - code-reviewer, mobile-developer, expo-mcp-specialist, architect-reviewer
   - 各実例の解説と学べるポイント

## チームでの共有

### プロジェクトレベルエージェントの作成

```bash
# 1. エージェントファイルを作成
.claude/agents/your-agent.md

# 2. gitにコミット
git add .claude/agents/your-agent.md
git commit -m "feat: add your-agent sub-agent for [purpose]"
git push

# 3. チームメンバーがpull
git pull
# → 自動的に全員が利用可能に
```

### ドキュメント化

```markdown
# プロジェクトのREADME.mdに追加

## Claude Code Sub-Agents

このプロジェクトでは以下のサブエージェントを提供しています：

- **code-reviewer**: コード品質・セキュリティレビュー（コード変更後に自動起動）
- **mobile-developer**: React Native/Expo開発支援
- **expo-mcp-specialist**: Expo MCP連携タスク（MUST BE USED）
```

## AI Assistant 向け指示

このスキルが起動された場合：

1. **新規作成の場合**:
   - 目的とスコープを確認
   - `references/agent-templates.md` から適切なテンプレートを選択
   - `references/description-writing-guide.md` を参照して効果的なdescriptionを作成
   - **`<example>` タグを含むdescriptionを提案**
   - プロジェクトコンテキストを考慮した具体的なワークフローを提供
   - **CLAUDE.md への起動条件追記を提案（発動率100%保証のため）**

2. **改善の場合**:
   - 現在のエージェントファイルを読み取る
   - トラブルシューティングセクションと照合
   - `references/description-writing-guide.md` でdescriptionを最適化
   - **`<example>` タグの追加を検討**
   - `references/real-world-examples.md` の成功例と比較
   - **CLAUDE.md連携の提案（発動率問題の根本解決）**

3. **デバッグの場合**:
   - YAML frontmatterのシンタックスチェック
   - name, description, tools フィールドの検証
   - トラブルシューティングセクションの該当項目を確認
   - **発動率~25%問題への対策提案（CLAUDE.md連携）**

常に：
- プロジェクトレベル（`.claude/agents/`）への配置を推奨
- 単一責任の原則を強調
- 最小権限のツール設定を推奨
- 具体的なトリガーワードと積極的呼び出しパターンを提案
- **重要なエージェントには CLAUDE.md 連携を推奨（発動率100%）**
- **`<example>` タグの活用を推奨（発動率向上）**

## クイックリファレンス

### 最小構成
```yaml
---
name: simple-agent
description: Does X. Use when Y.
---

You are a specialist in X.

When invoked:
1. Do A
2. Do B
3. Do C
```

### 推奨構成
```yaml
---
name: recommended-agent
description: Expert in X for Y and Z. Use PROACTIVELY when working with A, B, or C scenarios.
tools: Read, Write, Edit
model: sonnet
---

You are an expert in X.

## Core Expertise
- Area 1
- Area 2

## Workflow
1. Step 1
2. Step 2

## Best Practices
- Practice 1
- Practice 2
```

### 完全構成
```yaml
---
name: complete-agent
description: Specialist in X. MUST BE USED for all X-related tasks including A, B, C. Use PROACTIVELY when working with Y, Z. Examples: <example>Context: ... user: '...' assistant: '...' <commentary>...</commentary></example>
tools: Read, Write, Edit, Bash, mcp__service__*
model: sonnet
color: blue
---

[詳細なプロンプト - real-world-examples.md の expo-mcp-specialist を参照]
```

### 発動率100%保証構成

エージェントファイル + CLAUDE.md の組み合わせ:

```yaml
# .claude/agents/critical-agent.md
---
name: critical-agent
description: Critical task handler. Use PROACTIVELY for critical tasks.
tools: Read, Write, Edit
model: sonnet
---

[プロンプト内容]
```

```markdown
# CLAUDE.md（プロジェクトルート）

## Sub-Agent Activation Rules

以下の場合、必ず Task ツールで指定のエージェントを使用：

- **重要タスク、クリティカル処理** → `critical-agent` エージェント
```

---

このスキルを使って、プロジェクトに最適化された効果的なサブエージェントを作成してください！

## Version

**Current Version:** 1.1.0

### Version History

- **1.1.0** (2025-11-29): 発動率向上のベストプラクティス追加
  - 発動率~25%問題と解決策セクション追加
  - CLAUDE.md連携による100%発動保証の説明追加
  - `<example>` タグによる発動率向上の説明追加
  - レベル4（CLAUDE.md連携）パターン追加
  - AI Assistant指示に発動率関連の推奨事項追加
  - 発動率100%保証構成のクイックリファレンス追加

- **1.0.0** (Previous): 初回リリース
  - サブエージェント作成ガイド
  - YAML frontmatter ドキュメント
  - ベストプラクティス
