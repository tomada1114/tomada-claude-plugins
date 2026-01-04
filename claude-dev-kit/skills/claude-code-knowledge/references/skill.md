# スキル（Agent Skills）

> Claude Codeの能力を拡張するモジュール型パッケージ「スキル」の使用方法と作成方法について学びます。

## スキルとは

**Agent Skills**は、専門知識を発見可能な能力としてパッケージ化するものです。各スキルは、Claudeが関連する場合に読み込む指示を含む`SKILL.md`ファイルと、オプションのサポートファイル（スクリプト、テンプレートなど）で構成されます。

### 「必要な時だけ開くレシピ本」

Skills の仕組みを理解するには、キッチンに並んだレシピ本をイメージしてみてください。

本棚には数十冊のレシピ本が並んでいますが、普段は背表紙（タイトルと簡単な説明）だけが見えている状態です。「今日はパスタを作ろう」と決めた瞬間、初めてイタリア料理の本を手に取り、該当するページを開きます。すべての本を同時に開いて置いておく必要はありません。

Skills もこれと同じ仕組みです。普段は「この Skills は○○用です」というメタデータだけがメモリに常駐し、実際の詳細なルールやテンプレートは必要になった時だけ読み込まれます。この仕組みのおかげで、**数百の Skills を登録しておいても、コンテキストウィンドウを圧迫しない**のです。

### スキルの特徴

- **モデルが自動呼び出し**: ユーザーのリクエストとスキルの説明に基づいて、Claudeが自律的に使用を判断
- **段階的ロード（Progressive Disclosure）**: 必要な時に必要な情報だけを読み込み、コンテキストを効率的に管理
- **チーム共有**: プロジェクトスキルはgitで管理し、チーム全体で標準化されたワークフローを共有可能

## CLAUDE.mdやMCPとの違い

| 観点 | Skills | CLAUDE.md | MCP |
|------|--------|-----------|-----|
| 提供するもの | 手続き的知識（How） | 指示・文脈情報 | 外部接続（What/Where） |
| 読み込みタイミング | 必要時のみ | 常に全量 | 初期に全ツール定義 |
| トークン消費 | 少ない | 多くなりがち | 中〜多 |
| メンテナンス | 容易（ファイル編集のみ） | 容易 | 中〜高（サーバー実装） |
| チーム共有 | git で可能 | git で可能 | 設定ファイルで可能 |

**MCP** は外部のデータベースやAPIと接続するための仕組みであり、「何を」「どこから」取得するかを担当します。一方、**Skills** は「どのように」作業を進めるかという手続き的な知識を担当します。

> **注意点**: Skills は「Claude が自動的に選択する」仕組みのため、意図した Skills が読み込まれない場合もあります。これは **モデル呼び出し** と呼ばれる仕組みで、Claude がリクエストと Skills の説明（description）に基づいて自律的に使用を判断するからです。確実に特定の知識を使わせたい場合は、プロンプトで明示的に Skills の名前を含めるか、CLAUDE.md に直接書く方が確実なケースもあります。

## スキルの配置場所

### パーソナルスキル（グローバル）

```bash
mkdir -p ~/.claude/skills/skill-name
```

- **用途**: 個人のワークフローと設定
- **対象**: すべてのプロジェクト
- **共有**: しない（個人用）

### プロジェクトスキル

```bash
mkdir -p .claude/skills/skill-name
```

- **用途**: チームワークフローとプロジェクト固有の専門知識
- **対象**: このプロジェクトのみ
- **共有**: チームメンバーと自動共有（gitで管理）

### プラグインスキル

プラグインの `skills/` ディレクトリに配置すると自動検出されます。

```
my-plugin/
├── .claude-plugin/plugin.json
└── skills/
    └── my-skill/
        └── SKILL.md
```

**Skill tool での呼び出し**:
```
Skill("plugin-name:skill-name")
```

例:
```
Skill("pdf-tools:form-filler")
```

## スキルの作成方法

### ディレクトリ構造

```
skill-name/
├── SKILL.md              # 必須：メタデータと指示
├── reference.md          # オプション：詳細ドキュメント
├── examples.md           # オプション：使用例
├── scripts/              # オプション：ユーティリティスクリプト
│   └── helper.py
└── templates/            # オプション：テンプレートファイル
    └── template.txt
```

### SKILL.mdの基本構造

```yaml
---
name: skill-name
description: 何をするスキルで、いつ使うか（具体的に）
---

# Your Skill Name

## Instructions
段階的な指示をここに記載

## Examples
具体的な使用例を記載
```

### YAMLフロントマター

**必須フィールド**:

| フィールド | 説明 | 制限 |
|----------|------|------|
| `name` | スキルの識別子 | 小文字、数字、ハイフンのみ（最大64文字） |
| `description` | 何をするスキルで、いつ使うか | 最大1024文字（**極めて重要**） |

**オプションフィールド**:

| フィールド | 説明 |
|----------|------|
| `allowed-tools` | スキル実行時にClaudeが使用できるツールを制限（カンマ区切り） |

### allowed-tools の詳細

スキル実行時に使用可能なツールを制限できます。

```yaml
---
name: safe-file-reader
description: Read files without making changes
allowed-tools: Read, Grep, Glob
---
```

**メリット**:
- セキュリティ強化（読み取り専用など）
- 指定ツールは許可なしで使用可能
- 権限要求ダイアログを回避

### 説明文（description）の書き方

スキルが自動的に呼び出されるかどうかは、説明文の質に大きく依存します。

```yaml
# ❌ 弱い例：曖昧すぎる
description: ファイルを処理する
description: デザインを改善するスキル

# ✅ 強い例：具体的なキーワードを含む
description: Excelスプレッドシート、ピボットテーブル、グラフを分析。Excelファイル、スプレッドシート、.xlsxファイルで作業するときに使用

description: Apple Human Interface Guidelines に従ったUI設計を行う。
  Use when creating iOS/macOS style interfaces, Apple-like design,
  or working with SF Symbols, glassmorphism, or Apple design system.
```

**ポイント**:
- 何ができるかを具体的に記述
- いつ使うべきかを明確に示す
- 関連するキーワードを含める（iOS, macOS, Excel, .xlsx など）

## skill-creator による Skills 作成

Anthropic 公式の `skill-creator` プラグインを使えば、Skills の構造を熟知していなくてもオリジナル Skills を作成できます。

### 使用例

```
skill-creator スキルを使って、Apple風のおしゃれデザインを
作成するための新たな Claude Skills である "apple-design" を
プロジェクト内に作成してください。
```

Claude Code から Skills 使用の許可を求められたら「Yes」を選択します。

### 生成される構造

```
.claude
└── skills
    └── apple-design
        └── SKILL.md
```

:::message
skill-creator はあくまで「雛形」を作るものなので、生成された SKILL.md は確認してカスタマイズすることをおすすめします。特に description の内容は、自分のユースケースに合わせて調整した方が良いでしょう。
:::

## Progressive Disclosure（段階的ロード）

スキルは3段階で情報を公開し、コンテキストを効率的に管理します。

### トークン消費の目安

| レベル | 内容 | トークン消費 |
|--------|------|-------------|
| 第1段階 | メタデータ（名前・説明）のみ | 約100トークン/Skill |
| 第2段階 | SKILL.md 全体（指示・例・ガイドライン） | 通常は5,000トークン未満 |
| 第3段階 | 追加リソース（スクリプト・テンプレート・データ） | 必要時のみ読み込み |

普段は第1段階のメタデータだけが読み込まれているため、数百の Skills を同時に利用可能な状態にしておいても問題ありません。

### 3段階のアーキテクチャ

```
起動時
  ↓
┌─────────────────────────────────────────┐
│ Tier 1: メタデータ                      │
│ - スキルの名前と説明                   │
│ - システムプロンプトに常駐             │
│ - ~100トークン                         │
└─────────────────────────────────────────┘
  ↓
Claude: 「このスキルは関連があるか？」
  ↓
Yes → ┌─────────────────────────────────────────┐
      │ Tier 2: コア指示（SKILL.md）          │
      │ - スキルの詳細指示                   │
      │ - 対応方法の説明                     │
      │ - <5kトークン                        │
      └─────────────────────────────────────────┘
        ↓
      Claude: 「追加の参照が必要か？」
        ↓
      Yes → ┌─────────────────────────────────────────┐
            │ Tier 3+: 補助リソース                 │
            │ - reference.md, forms.md              │
            │ - scripts/ディレクトリ                │
            │ - 動的読み込み（Readツール等）       │
            └─────────────────────────────────────────┘
```

### 設計思想

従来のドキュメントのように：
- **目次**（メタデータ）で全体をナビゲート
- **特定の章**（SKILL.md）で詳細情報
- **詳細な付録**（追加ファイル）で深掘り

→ 各タスクに**必要な情報だけ**をコンテキストに読み込むため、トークン効率を最大化しながらスケーラビリティを実現

> Agents with a filesystem and code execution tools don't need to read the entirety of a skill into their context window when working on a particular task
> ファイルシステムとコード実行ツールを持つエージェントは、特定のタスクに取り組む際、スキル全体をコンテキストウィンドウに読み込む必要はありません。
> — Anthropic公式ブログ

## マルチファイルスキルの作成

SKILL.mdから他のファイルを参照することで、スキルを分割できます。

```markdown
詳細なAPIリファレンスは[REFERENCE.md](REFERENCE.md)を参照してください。

フォーム記入については[FORMS.md](FORMS.md)を参照。
```

**Claudeは追加ファイルを必要な時だけ読み込みます**。

### 実践例：PDF処理スキル

```
pdf-processing/
├── SKILL.md
├── FORMS.md
├── REFERENCE.md
└── scripts/
    ├── fill_form.py
    └── validate.py
```

**SKILL.md**:
```yaml
---
name: pdf-processing
description: テキスト抽出、フォーム記入、PDF結合。PDFファイル、フォーム、文書抽出で作業するときに使用。pypdfとpdfplumberパッケージが必要
allowed-tools: Bash, Read, Glob, Write
---

# PDF処理

## クイックスタート

テキスト抽出：
\`\`\`python
import pdfplumber
with pdfplumber.open("doc.pdf") as pdf:
    text = pdf.pages[0].extract_text()
\`\`\`

フォーム記入については[FORMS.md](FORMS.md)を参照。
詳細なAPIリファレンスは[REFERENCE.md](REFERENCE.md)を参照。
```

## Skills と SubAgents の使い分け

Skills と SubAgents は両方とも Claude Code の拡張機能ですが、役割が根本的に異なります。

### 比較表

| 特徴 | Skills | SubAgents |
|------|--------|-----------|
| **イメージ** | 参考書、マニュアル | アシスタント、別働隊 |
| **役割** | 知識の提供（How） | タスクの実行（Do） |
| **呼び出し方式** | モデル呼び出し（自動判断） | Taskツールで明示的に起動 |
| **コンテキスト** | メインの会話に読み込まれる | **独立**（メインを汚さない） |
| **トークン消費** | 使う時だけ消費（節約効果あり） | 別の財布で消費（メインの節約になる） |
| **主な用途** | ルール適用、知識提供 | 調査、探索、検証 |

### 料理で例えると

**Skills は「レシピ本」**:
- 必要な時だけ棚から取り出して参照
- 料理をするのは自分自身
- 「やり方」を教えてくれる

**SubAgents は「キッチンのアシスタント」**:
- 「この前菜を作っておいて」と頼めば全部やってくれる
- 作業場所が分離されているため、メインの作業台が散らからない

### 使い分けの判断基準

| 状況 | 選択 | 理由 |
|------|------|------|
| デザインガイドに従わせたい | Skills | ルール・知識の提供 |
| プロジェクト全体で使用箇所を調査 | SubAgents | 大量のファイル読み込み |
| 命名規則をチェック | Skills | ルールの適用 |
| ドキュメントを読み込んで要約 | SubAgents | 独立した調査タスク |
| テスト規約に従わせたい | Skills | 規約・知識の提供 |

**シンプルにまとめると:**
- 「**やり方**を教えたい」→ **Skills**
- 「**仕事**を任せたい」→ **SubAgents**

### Skills と SubAgents の連携

SubAgent の `skills` フィールドで、特定の SubAgent に Skills をロードさせることが可能です:

```yaml
---
name: code-reviewer
description: PRの差分をレビューし、コーディング規約違反を指摘
tools: Read, Grep, Glob, Bash
model: sonnet
skills: team-coding-standards
---
```

この構成により:
- **専門性の付与**: SubAgent に特定分野の知識を持たせられる
- **コンテキスト効率**: メインのコンテキストを消費せずに専門知識を活用
- **役割分担の明確化**: 各 SubAgent の責務が明確になる

複数の Skills を指定する場合はカンマ区切り:
```yaml
skills: ts-programming, aws-best-practices
```

## スキルとスラッシュコマンドの違い

| 特性 | スラッシュコマンド | スキル |
|-----|-----------------|-------|
| **呼び出し方** | 明示的（`/command`と入力） | 自動（コンテキストから自動判定） |
| **ファイル数** | 単一ファイルのみ | 複数ファイル可 |
| **構造** | シンプルなプロンプト | ディレクトリ + SKILL.md + リソース |
| **使い道** | 頻繁な単純プロンプト | 複雑なワークフロー・チーム標準 |

### 使い分け

**スラッシュコマンドを使う**:
- 同じプロンプトを繰り返し実行
- プロンプトが1ファイルに収まる
- ユーザーが明示的に実行を制御したい

**スキルを使う**:
- Claudeが自動的に発見・実行すべき
- 複数ファイルやスクリプトが必要
- 複雑なワークフローと検証ステップ
- チームが標準化した詳細なガイダンスが必要

## Tool / Skills / MCPの役割整理

| 概念 | 本質 | 役割 |
|-----|------|------|
| **Tool** | 能力拡張（Capability Extension） | 環境に作用するための手段。APIを叩く、DBに接続するなど |
| **Skills** | オーケストレーション | 複数のToolをどう組み合わせるか。順序・判断基準・ワークフローを定義 |
| **MCP** | コネクティビティ（接続レイヤー） | Tool（特に外部APIやサービス向け）を汎用的につなぐための接続方式 |

> MCPはClaudeを外部のサービスやデータソースに接続します。スキルは、特定のタスクを完了するための手順、つまり手続き的な知識を提供します。この2つを組み合わせて使用できます。MCP接続によってClaudeはツールにアクセスできるようになり、スキルによってClaudeはそれらのツールを効果的に使用する方法を習得します。
> — Anthropic公式サポート

スキルは**「業務マニュアル付きの道具箱」**と表現できます。Toolが「ドリルを渡す行為」だとすれば、Skillsは「日曜大工の入門書とドリル」を渡す行為に等しいです。

## スキルの共有（チーム全体）

### ステップ1：プロジェクトに追加
```bash
mkdir -p .claude/skills/team-skill
# SKILL.mdを作成
```

### ステップ2：gitにコミット
```bash
git add .claude/skills/
git commit -m "Add team Skill for PDF processing"
git push
```

### ステップ3：チームメンバーが自動取得
```bash
git pull
claude  # スキルが即座に利用可能
```

## ベストプラクティス

1. **1つのスキル = 1つの機能**
   - 「PDF処理」ではなく「PDFテキスト抽出」と「フォーム記入」で分割

2. **説明文は具体的に**
   - いつ使うのか、何ができるのかを明確に記述

3. **SKILL.mdは軽量に保つ**
   - 詳細は`reference.md`など別ファイルに切り出す
   - Progressive Disclosureを活用

4. **チームでテスト**
   - スキルが想定通り自動検出されるか確認

5. **バージョン管理を記録**
   - SKILL.md内にバージョン履歴セクションを追加

## 状態確認

### /skills コマンド

`/skills` コマンドを実行すると、現在読み込まれている Skills を確認できます。

```bash
> /skills
─────────────────────────────────────────────────────────────────────
 Skills
 4 skills

 User skills (/Users/username/.claude/skills)
 agile-ticket-planner · ~2.1k tokens
 claude-code-headless · ~1.7k tokens
 product-requirements-designer · ~2.7k tokens
 Project skills (.claude/skills)
 test-planning · ~1.1k tokens

 Esc to close
```

ユーザーレベルにインストールした Skills と、プロジェクトレベルにインストールした Skills が表示されます。それぞれを読み込んだときに消費されるトークン数も表示されます。

### ファイルシステムで確認

```bash
# パーソナルスキル
ls ~/.claude/skills/

# プロジェクトスキル
ls .claude/skills/

# 特定スキルの内容確認
cat .claude/skills/skill-name/SKILL.md
```

## プラグインからの Skills 取得

公式の Skills（frontend-design、skill-creator 等）は、プラグインとしてマーケットプレイスからインストールできます。

### マーケットプレイスの追加

```bash
/plugin marketplace add anthropics/skills
```

成功すると `Successfully added marketplace: anthropic-agent-skills` と表示されます。

### プラグインのインストール

**example-skills プラグイン（skill-creator含む）**:
```bash
/plugin install example-skills@anthropic-agent-skills
```

このプラグインには以下の Skills が含まれます：
- `skill-creator`: オリジナル Skills 作成支援
- `frontend-design`: フロントエンドデザイン支援
- `pdf`, `docx`, `xlsx`, `pptx`: 各種ドキュメント処理
- その他多数

インストール先は以下から選択可能：
- **User scope**: ユーザーレベル（すべてのプロジェクトで使用可能）
- **Project scope**: プロジェクトレベル（チームメンバーと共有）
- **Local scope**: このリポジトリのみ（git管理外）

### インストール済みプラグインの確認

```bash
/plugin
# → Installed タブで確認
```

詳細は [プラグイン](plugins.md) を参照。

## デバッグ

スキルが使われない場合のトラブルシューティング：

```bash
claude --debug
```

**よくある問題**:

| 問題 | 原因 | 解決策 |
|------|------|--------|
| スキルが検出されない | パスが間違っている | `~/.claude/skills/` または `.claude/skills/` を確認 |
| スキルが検出されない | ファイル名が違う | `SKILL.md`（大文字）になっているか確認 |
| 自動呼び出しされない | description が曖昧 | トリガーワードを具体的に含める |
| YAML エラー | フロントマター構文エラー | `---` の開始/終了を確認、タブではなくスペースを使用 |

**description のチェック**:
```bash
# フロントマターの確認
head -n 10 .claude/skills/my-skill/SKILL.md
```

## Sources

- [Claude Code Skills Documentation](https://docs.anthropic.com/ja/docs/claude-code/skills)
- [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) (2025-12-17確認)
- [Anthropic SkillsからAIプロダクト開発者が学べること](https://zenn.dev/r_kaga/articles/810cc2e8326ca5) (2025-12-17)
- [Claude Code Skillsの作り方！SKILL.mdの書き方から references フォルダの活用まで](https://zenn.dev/tomada/books/claude_code_basic/viewer/skills-creation) (2025-12-31確認)
