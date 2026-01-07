# content-tools

コンテンツ制作ツール。YouTube台本作成などを支援します。

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

### Commands

| Name | Description |
|------|-------------|
| `/video-script-writing:generate <source_file> <output_dir>` | ソースファイルからYouTube台本を生成 |

## Use Cases

- 記事やメモからYouTube台本を作成したい
- テック系動画のスクリプトを書きたい
- AI駆動開発・プログラミング解説動画を作りたい

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

## Trigger Keywords

Skill is activated when you mention:
- "台本", "スクリプト", "YouTube動画"
- "記事を台本に", "動画制作"
- "video script", "YouTube script"

## Author

**とまだ (@muscle_coding)**

## License

MIT
