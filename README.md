# Tomada Claude Plugins

Claude Code用のプラグイン集です。Skills、Commands、Agentsを提供します。

## Installation

```bash
# 1. マーケットプレイスとして追加
/plugin marketplace add tomada1114/tomada-claude-plugins

# 2. プラグインをインストール
/plugin install tomada-plugins@tomada-claude-plugins

# または対話的にブラウズ
/plugin
```

インストールすると、以下のすべてのSkills、Commands、Agentsが利用可能になります。

### 含まれるコンポーネント

#### Skills (6個)
- claude-skill-creator
- custom-commands-creator
- sub-agents-creator
- claude-rules-organizer
- transcription-fixer
- srt-transcription-fixer

#### Commands (2個)
- smart-commit (`/smart-commit`)
- pr-description (`/pr-description <pr-number>`)

#### Agents (1個)
- test-strategy-advisor

---

## Available Skills

### Claude Code Development

| Skill | Description |
|-------|-------------|
| **claude-skill-creator** | Skillの作成ガイド。YAML frontmatter、ディレクトリ構造、テンプレート、ベストプラクティスを提供 |
| **custom-commands-creator** | カスタムコマンド（スラッシュコマンド）の作成ガイド。引数パターン、Bash統合、ファイル参照を解説 |
| **sub-agents-creator** | サブエージェントの作成ガイド。発動率向上のためのCLAUDE.md連携パターンを含む |
| **claude-rules-organizer** | 肥大化したCLAUDE.mdを`.claude/rules/`へモジュール分割するスキル |

### Transcription (Japanese)

| Skill | Description |
|-------|-------------|
| **transcription-fixer** | 音声入力・文字起こしの誤変換を自動修正。Claude Code、AI駆動開発、プログラミング用語に特化 |
| **srt-transcription-fixer** | SRT字幕ファイル専用の文字起こし修正スキル |

---

## Available Commands

### Git Workflow

| Command | Description |
|---------|-------------|
| **smart-commit** | 変更を論理単位でグループ化し、Conventional Commits形式で自動コミット生成。機密情報を自動除外 |
| **pr-description** | PRのタイトルと説明を自動生成。コミット履歴と変更内容を分析してConventional Commits形式で出力 |

### Usage

```bash
# smart-commit: 変更を分析して自動コミット
/smart-commit

# pr-description: PR番号を指定して説明を生成
/pr-description 123
```

---

## Available Agents

### Quality & Testing

| Agent | Description |
|-------|-------------|
| **test-strategy-advisor** | テスト戦略・テストケース設計アドバイザー。Happy/Sad/Edge/Unhappy pathを網羅したテスト計画を提案 |

### test-strategy-advisor

テストを書く際に自動的に発動し、包括的なテスト戦略を提案します。

**Features:**
- Happy Path / Sad Path / Boundary Values / Invalid Inputs の網羅チェック
- Given/When/Then 形式のテスト構造ガイド
- 例外タイプとメッセージの検証要件
- 外部依存（API、DB）のモック戦略
- 100%ブランチカバレッジを目標とした計画

**Triggers:**
- "writing tests", "creating tests", "test strategy"
- "test coverage", "test cases", "unit tests"
- "what tests should I write", "how do I test this"

---

## Skill Details

### claude-skill-creator

Claude Code Skillの作成を支援します。

**Use when:**
- 新しいスキルを作成する
- 既存スキルを改善する
- スキルの発動率を上げたい
- YAML frontmatterの書き方を知りたい

### custom-commands-creator

カスタムスラッシュコマンドの作成を支援します。

**Use when:**
- `/my-command` のようなコマンドを作りたい
- 引数パターン（$ARGUMENTS vs $1/$2）を理解したい
- Bash統合（`!` prefix）を使いたい
- ファイル参照（`@` prefix）を使いたい

### sub-agents-creator

サブエージェントの作成を支援します。

**Use when:**
- 新しいサブエージェントを作成する
- エージェントが発動しない問題を解決したい（発動率~25%問題）
- CLAUDE.mdとの連携で100%発動を保証したい

### claude-rules-organizer

肥大化したCLAUDE.mdをモジュール分割します。

**Use when:**
- CLAUDE.mdが200行を超えて管理が難しい
- ルールを動的に読み込みたい
- コンテキスト使用量を最適化したい

### transcription-fixer

日本語音声入力の誤変換を修正します。

**Use when:**
- Whisper等の文字起こしを修正したい
- 「クロードコード」→「Claude Code」などの変換
- プログラミング用語の正しい表記に統一したい

### srt-transcription-fixer

SRT字幕ファイル専用の修正スキル。

**Use when:**
- SRTファイルの誤変換を修正したい
- タイムコードを維持したまま字幕を修正したい

---

## Requirements

- Claude Code CLI
- Skill tool permission enabled:

```json
// .claude/settings.json or ~/.claude/settings.json
{
  "permissions": {
    "allow": ["Skill(*)"]
  }
}
```

## Author

**とまだ (@muscle_coding)**

- AI駆動開発の実践者・教育者
- Udemy講師（Claude Code講座）
- Zenn/Qiita/note 技術記事執筆

## License

MIT
