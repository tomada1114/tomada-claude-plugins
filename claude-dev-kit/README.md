# claude-dev-kit

Claude Code拡張開発キット。Skill、Command、Agent、Rulesの作成を支援します。

## Installation

```bash
# 1. マーケットプレイスを追加
/plugin marketplace add tomada1114/tomada-claude-plugins

# 2. プラグインをインストール
/plugin install claude-dev-kit@tomada-claude-plugins
```

## Contents

### Skills

| Name | Description |
|------|-------------|
| **claudecode-skill-creating** | Skillの作成ガイド。YAML frontmatter、ディレクトリ構造、テンプレート |
| **creating-commands** | カスタムコマンドの作成ガイド。引数パターン、Bash統合 |
| **creating-subagents** | サブエージェントの作成ガイド。発動率向上のCLAUDE.md連携パターン |
| **claudecode-rules-organizing** | 肥大化したCLAUDE.mdを`.claude/rules/`へモジュール分割 |
| **claudecode-docs-referencing** | Claude Codeの機能・設定リファレンス。公式ドキュメントベース |
| **claudecode-headless-automating** | ヘッドレスモード（-p フラグ）でのスクリプト連携ガイド |

### Commands

| Name | Description |
|------|-------------|
| `/add-description-to-memory` | CLAUDE.mdのSkill Activation Rulesを自動同期 |

## Use Cases

- 新しいSkill/Command/Agentを作りたい
- エージェントが発動しない問題を解決したい
- CLAUDE.mdが大きくなりすぎた
- Claude Codeの機能や設定を調べたい

## Trigger Keywords

Skills are activated when you mention:
- "create skill", "skill structure", "YAML frontmatter"
- "custom command", "slash command"
- "sub-agent", "agent activation"
- "CLAUDE.md refactoring", "rules organization"
- "Claude Code features", "headless mode"

## Author

**とまだ (@muscle_coding)**

## License

MIT
