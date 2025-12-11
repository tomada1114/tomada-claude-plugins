# Tomada Claude Plugins

Claude Code用のスキルプラグイン集です。

## Installation

```bash
claude mcp add-skill-plugin tomada@github:tomada1114/tomada-claude-plugins
```

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

## Usage

インストール後、Claude Codeが自動的にスキルを認識します。

```
# スキルを明示的に呼び出す
> Use the claude-skill-creator skill to help me create a new skill

# または自然な会話で（キーワードマッチング）
> 新しいスキルを作りたい
> カスタムコマンドの書き方を教えて
> サブエージェントが発動しない問題を解決したい
```

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
