# git-workflow

Gitワークフロー効率化ツール。コミットとPR作成を自動化します。

## Installation

```bash
# 1. マーケットプレイスを追加
/plugin marketplace add tomada1114/tomada-claude-plugins

# 2. プラグインをインストール
/plugin install git-workflow@tomada-claude-plugins
```

## Contents

### Commands

| Name | Description |
|------|-------------|
| `/smart-commit` | 変更を論理単位でグループ化し、Conventional Commits形式で自動コミット |
| `/pr-description` | PRのタイトルと説明を自動生成 |

## Usage

```bash
# 変更を分析して自動コミット
/smart-commit

# PR #123 の説明を生成
/pr-description 123
```

## Features

### smart-commit
- 変更ファイルを論理的なグループに分類
- Conventional Commits形式（feat:, fix:, docs:, etc.）でコミットメッセージを生成
- 複数の変更を適切に分割してコミット

### pr-description
- PRの変更内容を分析
- タイトルと説明文を自動生成
- テスト計画のセクションも含む

## Author

**とまだ (@muscle_coding)**

## License

MIT
