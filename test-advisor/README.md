# test-advisor

テスト戦略アドバイザー。包括的なテスト計画を提案します。

## Installation

```bash
# 1. マーケットプレイスを追加
/plugin marketplace add tomada1114/tomada-claude-plugins

# 2. プラグインをインストール
/plugin install test-advisor@tomada-claude-plugins
```

## Contents

### Agents

| Name | Description |
|------|-------------|
| **test-strategy-advisor** | Happy/Sad/Edge/Unhappy pathを網羅したテスト計画を提案 |

## Features

- **Given/When/Then** 形式のテスト構造ガイド
- **境界値テスト** の設計支援
- **例外テスト** のカバレッジ確認
- 外部依存（API、DB）の **モック戦略**
- **100%ブランチカバレッジ** を目標とした計画

## Test Perspectives

このエージェントは以下の4つの観点でテストを設計します：

| Path | Description |
|------|-------------|
| **Happy path** | 正常系。期待通りの入力で成功するケース |
| **Sad path** | 準正常系。バリデーションエラー、Not Found等の想定内エラー |
| **Edge cases** | 境界値。空配列、null、undefined、最大値/最小値 |
| **Unhappy path** | 異常系。ネットワーク障害、DBタイムアウト等の予期せぬエラー |

## Trigger Keywords

Agent is activated when you mention:
- "writing tests", "creating tests", "adding tests"
- "test strategy", "test coverage", "test cases"
- "what tests should I write", "how do I test this"

## Author

**とまだ (@muscle_coding)**

## License

MIT
