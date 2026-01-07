# transcription-tools

日本語文字起こし修正ツール。Whisper等の誤変換を自動修正します。

## Installation

```bash
# 1. マーケットプレイスを追加
/plugin marketplace add tomada1114/tomada-claude-plugins

# 2. プラグインをインストール
/plugin install transcription-tools@tomada-claude-plugins
```

## Contents

### Skills

| Name | Description |
|------|-------------|
| **transcription-fixer** | 音声入力・文字起こしの誤変換を自動修正。Claude Code、AI駆動開発用語に特化 |
| **srt-transcription-fixer** | SRT字幕ファイル専用の修正。改行位置の最適化、誤変換修正 |

### Commands

| Name | Description |
|------|-------------|
| `/srt-transcription-fixer:fix-srt <directory>` | 指定ディレクトリのSRTファイルを修正 |
| `/srt-transcription-fixer:split-long-subtitles <srt_file>` | 長い字幕テキストを分割 |

## Use Cases

- Whisper等の文字起こしを修正したい
- 「クロードコード」→「Claude Code」などの技術用語変換
- SRT字幕ファイルの誤変換・改行位置を修正したい
- Obsidianノートの音声入力テキストを整理したい

## Conversion Examples

| Before | After |
|--------|-------|
| クロードコード | Claude Code |
| MCP サーバー | MCPサーバー |
| AI 駆動開発 | AI駆動開発 |
| プロンプトインジェクション | プロンプトインジェクション |

## Trigger Keywords

Skills are activated when you mention:
- "文字起こしを修正", "誤変換を直して"
- "誤字脱字を修正", "音声入力を整理"
- "SRT", "字幕", "subtitle"

## Author

**とまだ (@muscle_coding)**

## License

MIT
