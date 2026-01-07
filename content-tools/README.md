# content-tools

コンテンツ制作ツール。YouTube台本作成、文字起こし修正、SRT字幕修正を支援します。

## Installation

```bash
# 1. マーケットプレイスを追加
/plugin marketplace add tomada1114/tomada-claude-plugins

# 2. プラグインをインストール
/plugin install content-tools@tomada-claude-plugins
```

## Contents

### Skills

| Name | Description |
|------|-------------|
| **video-script-writing** | YouTube台本作成。テック動画（AI駆動開発・プログラミング）向け7軸評価システム |
| **fixing-transcriptions** | 音声入力・文字起こしの誤変換を自動修正。Claude Code、AI駆動開発用語に特化 |
| **fixing-srt-subtitles** | SRT字幕ファイル専用の修正。改行位置の最適化、誤変換修正 |

### Commands

| Name | Description |
|------|-------------|
| `/video-script-writing:generate <source_file> <output_dir>` | ソースファイルからYouTube台本を生成 |
| `/fixing-srt-subtitles:fix-srt <directory>` | 指定ディレクトリのSRTファイルを修正 |
| `/fixing-srt-subtitles:split-long-subtitles <srt_file>` | 長い字幕テキストを分割 |

## Use Cases

- 記事やメモからYouTube台本を作成したい
- テック系動画のスクリプトを書きたい
- AI駆動開発・プログラミング解説動画を作りたい
- Whisper等の文字起こしを修正したい
- 「クロードコード」→「Claude Code」などの技術用語変換
- SRT字幕ファイルの誤変換・改行位置を修正したい
- Obsidianノートの音声入力テキストを整理したい

## Features

### video-script-writing

7軸評価システムで高品質な台本を生成：

1. **構成の論理性** - 導入→本編→まとめの流れ
2. **技術的正確性** - 用語・概念の正しさ
3. **視聴者への配慮** - 難易度の適切さ
4. **エンゲージメント** - 視聴継続のフック
5. **実用性** - 視聴後のアクション
6. **オリジナリティ** - 独自の視点・価値
7. **時間配分** - 各セクションの適切な長さ

### fixing-transcriptions / fixing-srt-subtitles

| Before | After |
|--------|-------|
| クロードコード | Claude Code |
| MCP サーバー | MCPサーバー |
| AI 駆動開発 | AI駆動開発 |
| プロンプトインジェクション | プロンプトインジェクション |

## Trigger Keywords

Skills are activated when you mention:
- "台本", "スクリプト", "YouTube動画"
- "記事を台本に", "動画制作"
- "video script", "YouTube script"
- "文字起こしを修正", "誤変換を直して"
- "誤字脱字を修正", "音声入力を整理"
- "SRT", "字幕", "subtitle"

## Author

**とまだ (@muscle_coding)**

## License

MIT
