# Claude Code プラグイン配布の知見

このドキュメントは、Claude Code プラグインを配布する際に得た知見をまとめたものです。

## 基本構造

### マーケットプレイス形式

GitHubリポジトリをマーケットプレイスとして配布する場合の構造：

```
my-marketplace/
├── .claude-plugin/
│   └── marketplace.json      # 必須：マーケットプレイス定義
├── plugin-1/                  # 各プラグインのディレクトリ
│   ├── skills/
│   ├── commands/
│   └── agents/
├── plugin-2/
│   └── ...
└── README.md
```

### marketplace.json の書式

```json
{
  "name": "marketplace-name",
  "owner": {
    "name": "owner-name"
  },
  "plugins": [
    {
      "name": "plugin-name",
      "source": "./plugin-directory",
      "description": "プラグインの説明"
    }
  ]
}
```

**重要なポイント:**
- `source` は必ず `./` で始める必要がある
- `"."` はNG、`"./"` が正しい
- 相対パスでプラグインディレクトリを指定

## プラグイン内の構造

各プラグインディレクトリには、以下のサブディレクトリを配置可能：

```
my-plugin/
├── skills/           # Agent Skills (SKILL.md)
│   └── my-skill/
│       └── SKILL.md
├── commands/         # Custom Commands (.md)
│   └── my-command.md
├── agents/           # Sub-Agents (.md)
│   └── my-agent.md
└── hooks/            # Event Handlers (hooks.json)
    └── hooks.json
```

- `skills/` - 各スキルはサブディレクトリに `SKILL.md` を配置
- `commands/` - コマンドファイルは直接配置
- `agents/` - エージェントファイルは直接配置

## 配布設計のベストプラクティス

### 1. プラグインの分割粒度

**悪い例**: 全部入りの1プラグイン
```
my-plugins → skills(10) + commands(5) + agents(3)
```
- 不要なものも全部入る
- コンテキスト消費が増える

**良い例**: 用途別に分割
```
dev-tools       → 開発支援ツール
git-workflow    → Git関連コマンド
test-helpers    → テスト支援
```

### 2. 分割の判断基準

| 基準 | 分割すべき | まとめてOK |
|-----|----------|----------|
| 対象ユーザー | 異なる | 同じ |
| 利用シーン | 独立 | 関連 |
| 依存関係 | なし | あり |

例：
- 「文字起こしツール」と「Git効率化」→ 分割（ユーザー層が違う）
- 「Skill作成」と「Command作成」→ まとめる（Claude Code拡張者向け）

### 3. 命名規則

**プラグイン名:**
- kebab-case を使用
- 用途が分かる名前
- 例: `claude-dev-kit`, `git-workflow`, `transcription-tools`

**説明文:**
- 日本語OK
- 何ができるか1行で伝える
- 例: "Gitワークフロー効率化。smart-commit、pr-descriptionコマンド"

## インストール・アンインストール

### ユーザー側の操作

```bash
# マーケットプレイス追加
/plugin marketplace add owner/repo

# プラグインインストール
/plugin install plugin-name@marketplace-name

# 対話的にブラウズ
/plugin
```

### 開発中のローカルテスト

```bash
# ローカルディレクトリをマーケットプレイスとして追加
/plugin marketplace add ./path/to/local/marketplace
```

## トラブルシューティング

### エラー: "Marketplace file not found"

原因: `.claude-plugin/marketplace.json` が存在しない

解決:
```bash
mkdir -p .claude-plugin
# marketplace.json を作成
```

### エラー: "Invalid schema: source must start with ./"

原因: `source` フィールドが `./` で始まっていない

解決:
```json
// NG
"source": "."
"source": "plugin-dir"

// OK
"source": "./"
"source": "./plugin-dir"
```

### Skills/Commands/Agents が認識されない

確認ポイント:
1. ディレクトリ名が正しいか（`skills/`, `commands/`, `agents/`）
2. ファイル形式が正しいか（`.md`）
3. Skills は `SKILL.md` という名前か
4. frontmatter（YAML）が正しいか

## 参考リンク

- [Claude Code Plugins ドキュメント](https://code.claude.com/docs/en/plugins.md)
- [Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces.md)
- [Plugins Reference](https://code.claude.com/docs/en/plugins-reference.md)
