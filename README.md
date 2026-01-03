# Tomada Claude Plugins

Claude Code用のプラグイン集です。用途別に5つのプラグインを提供します。

## Installation

```bash
# 1. マーケットプレイスとして追加
/plugin marketplace add tomada1114/tomada-claude-plugins

# 2. 必要なプラグインをインストール
/plugin install claude-dev-kit@tomada-claude-plugins
/plugin install git-workflow@tomada-claude-plugins
/plugin install test-advisor@tomada-claude-plugins
/plugin install transcription-tools@tomada-claude-plugins
/plugin install marp-slide-writer@tomada-claude-plugins

# または対話的にブラウズ
/plugin
```

---

## Available Plugins

### 1. claude-dev-kit

Claude Code拡張開発キット。Skill、Command、Agent、Rulesの作成を支援します。

```bash
/plugin install claude-dev-kit@tomada-claude-plugins
```

| Skill | Description |
|-------|-------------|
| **claude-skill-creator** | Skillの作成ガイド。YAML frontmatter、ディレクトリ構造、テンプレート |
| **custom-commands-creator** | カスタムコマンドの作成ガイド。引数パターン、Bash統合 |
| **sub-agents-creator** | サブエージェントの作成ガイド。発動率向上のCLAUDE.md連携パターン |
| **claude-rules-organizer** | 肥大化したCLAUDE.mdを`.claude/rules/`へモジュール分割 |

**Use when:**
- 新しいSkill/Command/Agentを作りたい
- エージェントが発動しない問題を解決したい
- CLAUDE.mdが大きくなりすぎた

---

### 2. git-workflow

Gitワークフロー効率化ツール。コミットとPR作成を自動化します。

```bash
/plugin install git-workflow@tomada-claude-plugins
```

| Command | Description |
|---------|-------------|
| **smart-commit** | 変更を論理単位でグループ化し、Conventional Commits形式で自動コミット |
| **pr-description** | PRのタイトルと説明を自動生成 |

**Usage:**
```bash
/smart-commit              # 変更を分析して自動コミット
/pr-description 123        # PR #123 の説明を生成
```

---

### 3. test-advisor

テスト戦略アドバイザー。包括的なテスト計画を提案します。

```bash
/plugin install test-advisor@tomada-claude-plugins
```

| Agent | Description |
|-------|-------------|
| **test-strategy-advisor** | Happy/Sad/Edge/Unhappy pathを網羅したテスト計画を提案 |

**Features:**
- Given/When/Then 形式のテスト構造ガイド
- 境界値テスト、例外テストの設計
- 外部依存（API、DB）のモック戦略
- 100%ブランチカバレッジを目標とした計画

**Triggers:**
- "writing tests", "test strategy", "test coverage"
- "what tests should I write", "how do I test this"

---

### 4. transcription-tools

日本語文字起こし修正ツール。Whisper等の誤変換を自動修正します。

```bash
/plugin install transcription-tools@tomada-claude-plugins
```

| Skill | Description |
|-------|-------------|
| **transcription-fixer** | 音声入力・文字起こしの誤変換を自動修正。Claude Code、AI駆動開発用語に特化 |
| **srt-transcription-fixer** | SRT字幕ファイル専用の文字起こし修正 |

**Use when:**
- Whisper等の文字起こしを修正したい
- 「クロードコード」→「Claude Code」などの変換
- SRTファイルの誤変換を修正したい

---

### 5. marp-slide-writer

YouTube収録用Marpスライド作成ツール。レイアウト制約を遵守した視認性の高いスライドを生成します。

```bash
/plugin install marp-slide-writer@tomada-claude-plugins
```

| Skill | Description |
|-------|-------------|
| **marp-slide-writer** | Marpスライドの作成・検証。レイアウト制約に基づく自動バリデーション |

**Features:**
- YouTube 16:9形式に最適化されたレイアウト制約
- 箇条書き・コード・テーブルの行数上限チェック
- 検証スクリプト（validate_slides.py）による自動検証
- 基本・コード多めの2種類のテンプレート

**Use when:**
- スライド作成、プレゼン資料作成
- 「スライドを作って」「Marpで資料作成」

---

## Requirements

- Claude Code CLI

## Author

**とまだ (@muscle_coding)**

- AI駆動開発の実践者・教育者
- Udemy講師（Claude Code講座）
- Zenn/Qiita/note 技術記事執筆

## License

MIT
