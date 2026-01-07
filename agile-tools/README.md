# agile-tools

アジャイル開発ツール。要件設計とGitHub Issue作成を支援します。

## Installation

```bash
# 1. マーケットプレイスを追加
/plugin marketplace add tomada1114/tomada-claude-plugins

# 2. プラグインをインストール
/plugin install agile-tools@tomada-claude-plugins
```

## Contents

### Skills

| Name | Description |
|------|-------------|
| **planning-tickets** | GitHub Issue作成。並列作業の特定、依存関係管理、git worktree戦略 |
| **designing-requirements** | 曖昧な要件を詳細化。PdM視点の質問→ワイヤーフレーム→チケット分割 |
| **ui-ux-designing** | UI/UXデザインコンセプト決定。競合調査→段階的質問→デザインシステムドキュメント生成 |

## Use Cases

- 要件からGitHub Issueを作成したい
- 曖昧なアイデアを詳細な仕様に落としたい
- 並列作業できるチケットを特定したい
- スプリント計画を立てたい
- UI/UXのデザインコンセプトを決めたい
- デザインシステムドキュメントを作成したい

## Features

### planning-tickets
- **並列作業の特定**: 依存関係のないタスクを並列実行可能と判定
- **依存関係管理**: タスク間の前後関係を明確化
- **git worktree戦略**: 並列開発のためのブランチ戦略を提案

### designing-requirements
- **PdM視点の質問**: 曖昧なポイントを洗い出し
- **ワイヤーフレーム設計**: UI/UXの具体化
- **チケット分割**: 実装可能な粒度への分解

### ui-ux-designing
- **競合UX調査**: WebSearchで人気アプリのUXを調査・分析
- **段階的質問**: AskUserQuestionでトーン、カラー、レイアウト方針を決定
- **デザインドキュメント**: テンプレートベースのデザインコンセプト文書生成

## Trigger Keywords

Skills are activated when you mention:
- "チケットを作って", "Issueを分割して"
- "要件を詳細化", "specs", "PRD"
- "ワイヤーフレーム", "UI design"
- "並列作業", "worktree"
- "デザインコンセプト", "UI/UX", "カラースキーム"
- "デザインシステム", "見た目"

## Author

**とまだ (@muscle_coding)**

## License

MIT
