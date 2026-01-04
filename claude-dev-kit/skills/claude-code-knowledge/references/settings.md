# 12. 設定ファイルの管理

## 設定ファイルの階層

Claude Code の設定は5つのレベルで管理されます(優先度順):

1. **Managed Settings**(最優先・エンタープライズ)
   - Claude.ai admin console経由で配信、または `managed-settings.json` をシステムディレクトリに配置
2. **コマンドライン引数**(実行時)
3. **ローカルプロジェクト設定**: `.claude/settings.local.json`（個人用、gitに入れない）
4. **共有プロジェクト設定**: `.claude/settings.json`（チーム共有）
5. **ユーザー設定**: `~/.claude/settings.json`（最低優先）

## パーミッションとは

パーミッションとは、**Claude Codeがどの操作を許可されるかを制御する設定**。Claude Codeはファイルの読み書き、シェルコマンドの実行、Webアクセスなど豊富な機能を持つが、適切に管理しないと意図しないファイル削除や機密情報の漏洩リスクが生じる。パーミッション設定は**安全な操作は自動化、危険な操作はブロック**というバランスを実現する。

## パーミッションの5種類

### 1. Bash（シェルコマンド）
ターミナルでのコマンド実行を制御。最も重要なパーミッション。

```json
{
  "permissions": {
    "allow": ["Bash(npm run test:*)"],
    "deny": ["Bash(rm -rf:*)"]
  }
}
```

### 2. Read（ファイル読み取り）
ファイルの読み取りを制御。機密ファイルへのアクセス制限に有用。

```json
{
  "permissions": {
    "allow": ["Read"],
    "deny": ["Read(.env)", "Read(.env.*)"]
  }
}
```

### 3. Edit（ファイル編集）
既存ファイルの編集を制御。

```json
{
  "permissions": {
    "allow": ["Edit"]
  }
}
```

### 4. Write（ファイル作成）
新規ファイルの作成を制御。

```json
{
  "permissions": {
    "allow": ["Write"]
  }
}
```

### 5. WebFetch（Webアクセス）
外部URLへのアクセスを制御。セキュリティ重視なら無効化を検討。

```json
{
  "permissions": {
    "deny": ["WebFetch"]
  }
}
```

## 3つのルール：allow、deny、ask

### allow（許可）
指定パターンにマッチする操作は**確認なしで自動実行**。

```json
{
  "permissions": {
    "allow": ["Bash(npm:*)", "Bash(git:*)"]
  }
}
```

### deny（禁止）
指定パターンにマッチする操作は**完全にブロック**。

```json
{
  "permissions": {
    "deny": ["Bash(rm -rf:*)", "Read(.env)"]
  }
}
```

### ask（確認を強制）
指定パターンにマッチする操作は、**allowに含まれていても毎回確認プロンプトを表示**。

```json
{
  "permissions": {
    "allow": ["Bash(git:*)"],
    "ask": ["Bash(git push:*)"]
  }
}
```

## ルールの優先度

**優先度: Deny > Ask > Allow**

同じ操作が複数のルールにマッチした場合、denyが最優先、次にask、最後にallow。

```json
{
  "permissions": {
    "allow": ["Bash(echo:*)"],
    "deny": ["Bash(echo secret:*)"]
  }
}
```
→ `echo hello`は自動実行、`echo secret data`は拒否

## Bashパターンの書き方：プレフィックスマッチング

Bashパーミッションのパターンは**正規表現やglobではなく、プレフィックスマッチング**で動作。

### 正しい書き方
コマンドの末尾に`:*`を付ける。

```json
{
  "permissions": {
    "allow": ["Bash(npm run test:*)", "Bash(git:*)"]
  }
}
```

### よくある間違い（動作しない）
```json
// ❌ 正規表現は使えない
"Bash(echo .*)"

// ❌ globパターンも使えない
"Bash(rm -rf **)"

// ❌ 途中にワイルドカードは入れられない
"Bash(wget:* | bash)"
```

## Read/Editのパス記法

.gitignoreと同様の記法で記述。

```json
{
  "permissions": {
    "deny": ["Read(.env)", "Read(.env.*)", "Read(**/secrets/**)"]
  }
}
```

| 記法 | 意味 | 例 |
| --- | --- | --- |
| `//path` | ファイルシステムルートからの絶対パス | `Read(//Users/alice/secrets/**)` |
| `~/path` | ホームディレクトリからのパス | `Read(~/Documents/*.pdf)` |
| `./path` または `path` | 現在ディレクトリからの相対パス | `Read(.env)` |

## 主要な設定ファイル

### グローバル設定
**場所**: `~/.claude/settings.json`
**スコープ**: すべてのプロジェクト

```json
{
  "model": "sonnet",
  "cleanupPeriodDays": 30,
  "permissions": {
    "allow": ["Bash(npm run test:*)"],
    "deny": ["Read(./.env)"]
  }
}
```

**注意**: `theme`、`autoUpdates`、`verbose`、`preferredNotifChannel` は settings.json には存在しません。テーマは `/config` コマンドで設定、自動更新は `DISABLE_AUTOUPDATER` 環境変数で制御します。

### プロジェクト設定
**場所**: `.claude/settings.json`
**スコープ**: 現在のプロジェクト(Git で共有)

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "permissions": {
    "allow": [
      "Bash(npm run test:*)",
      "Read(~/.zshrc)"
    ],
    "deny": [
      "Bash(rm -rf *)"
    ],
    "defaultMode": "acceptEdits"
  }
}
```

### ローカル設定
**場所**: `.claude/settings.local.json`
**スコープ**: 現在のプロジェクト(個人用、Git で無視)

```json
{
  "permissions": {
    "defaultMode": "acceptAll"
  }
}
```

## 設定管理方法

### インタラクティブ設定（推奨）

```bash
# セッション中に /config コマンドを実行
/config
```

タブ付きUIで設定を視覚的に管理できます。

### ファイル直接編集

```bash
# ユーザー設定を編集
nano ~/.claude/settings.json

# プロジェクト設定を編集
nano .claude/settings.json
```

### MCP設定

```bash
# MCPサーバー管理
claude mcp              # 一覧表示
claude mcp add <name>   # 追加
claude mcp remove <name> # 削除
```

## 重要な設定項目

### モデル設定

```json
{
  "model": "claude-sonnet-4-5-20250929"
}
```

利用可能なモデル（エイリアス推奨）:
- `sonnet` または `claude-sonnet-4-5-20250929` - Sonnet 4.5（推奨）
- `opus` または `claude-opus-4-5-20251101` - Opus 4.5
- `haiku` または `claude-haiku-4-5-20251001` - Haiku 4.5
- `opusplan` - Plan時Opus、実行時Sonnet
- `sonnet[1m]` - 100万トークンコンテキスト

### 権限設定

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run test:*)",
      "Read(~/.zshrc)"
    ],
    "deny": [
      "Bash(curl:*)",
      "WebFetch"
    ],
    "ask": [
      "Bash(git push:*)"
    ],
    "additionalDirectories": ["../docs/"],
    "defaultMode": "default"
  }
}
```

### defaultModeの選択肢

| モード | 動作 | 用途 |
| --- | --- | --- |
| `default` | すべての操作に確認プロンプトを表示 | 最も安全、セキュリティ最優先 |
| `acceptEdits` | ファイルの読み取りと編集を自動承認 | バランス型 |
| `bypassPermissions` | すべての権限チェックをスキップ | 危険、sandboxモードと併用推奨 |

**注意**: `bypassPermissions`は`--dangerously-skip-permissions`フラグと同等。ただし、**denyルールは有効なまま**（askのみスキップ）。

### その他の設定

```json
{
  "includeCoAuthoredBy": true,  // Co-authored-by を追加
  "cleanupPeriodDays": 30,       // セッション履歴の保持期間
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1"
  }
}
```

## バランスの良い基本設定

多くのプロジェクトで使える汎用的な設定例。`rm -rf`の悲劇を防ぎつつ、開発効率も確保。

```json
{
  "permissions": {
    "allow": [
      "Bash(ls:*)",
      "Bash(cat:*)",
      "Bash(echo:*)",
      "Bash(touch:*)",
      "Bash(mkdir:*)",
      "Bash(cp:*)",
      "Read",
      "Edit",
      "Write"
    ],
    "deny": [
      "Bash(sudo:*)",
      "Bash(rm -rf:*)",
      "Bash(git reset:*)",
      "Bash(git rebase:*)",
      "Bash(wget:*)",
      "Read(**/.env*)",
      "Read(id_rsa)",
      "Read(id_ed25519)",
      "Read(**/*token*)",
      "Read(**/*key*)",
      "Write(**/.env*)",
      "Write(**/secrets/**)"
    ],
    "ask": [
      "Bash(rm:*)",
      "Bash(mv:*)",
      "Bash(curl:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git push:*)",
      "Bash(git merge:*)"
    ]
  }
}
```

**denyで絶対に防ぐもの**: sudo、rm -rf、git reset/rebase、wget、機密ファイル
**askで確認を挟むもの**: rm、mv、curl、git push/commit/merge
**allowで自動化するもの**: ls、cat、echo、touch、mkdir、cp、Read/Edit/Write

## プロジェクト設定の例

### TypeScript プロジェクト

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run:*)",
      "Bash(npm test:*)",
      "Bash(npx tsc:*)",
      "Bash(npx prettier:*)",
      "Bash(npx eslint:*)"
    ],
    "ask": [
      "Bash(npm install:*)",
      "Bash(npm uninstall:*)"
    ]
  }
}
```

### Python プロジェクト

```json
{
  "permissions": {
    "allow": [
      "Bash(python:*)",
      "Bash(python3:*)",
      "Bash(pytest:*)",
      "Bash(ruff:*)",
      "Bash(mypy:*)"
    ],
    "ask": [
      "Bash(pip install:*)",
      "Bash(pip uninstall:*)",
      "Bash(uv add:*)",
      "Bash(uv remove:*)"
    ]
  }
}
```

### 高セキュリティプロジェクト

```json
{
  "permissions": {
    "allow": ["Read", "Edit"],
    "deny": ["Bash(*)", "WebFetch"]
  }
}
```

## ベストプラクティス

### 1. プロジェクト設定を Git で共有

チーム全員が同じ設定を使用:

```bash
git add .claude/settings.json
git commit -m "Add Claude Code project settings"
```

### 2. 個人設定は local に

個人の好みは `.claude/settings.local.json`:

```bash
# .gitignore に追加
echo ".claude/settings.local.json" >> .gitignore
```

### 3. 最小権限の原則

必要最小限の権限のみ許可:

```json
{
  "permissions": {
    "allow": [
      "Bash(npm test)",
      "Bash(npm run build)"
    ],
    "deny": [
      "Bash(rm *)",
      "Bash(sudo *)"
    ]
  }
}
```

## additionalDirectoriesの活用

プロジェクトディレクトリ外のファイルにアクセスを許可する設定。モノレポ構成や共有ライブラリがある場合に便利。

```json
{
  "permissions": {
    "additionalDirectories": [
      "../shared-libs/",
      "~/dotfiles/"
    ]
  }
}
```

セッション中は`/add-dir`コマンドでも追加可能。必要最小限のディレクトリのみ指定すること。

## トラブルシューティング

### /doctorコマンドで設定を検証

設定ファイルの問題点を指摘してくれる。

```bash
# Claude Code内で実行
/doctor
```

不正なパターンがあると警告が表示される:
```
Invalid Settings
 /Users/username/.claude/settings.json
  └ permissions
    └ allow
      └ "Bash(echo
        └ *)": Use ":*" for prefix matching, not just "*".
```

### /permissionsコマンドで設定確認

現在の設定をインタラクティブに確認できる。

```bash
/permissions
```

Allow/Ask/Denyのルールをタブで切り替えて確認可能。

### 設定変更が反映されない

設定ファイル変更後は**Claude Codeの再起動が必要**。

```bash
# セッションを終了して再起動
exit
claude
```

### 設定ファイルの破損

```bash
# バックアップから復元、または削除して再作成
mv ~/.claude/settings.json ~/.claude/settings.json.bak
claude
```

## 検証結果と注意点

### denyの制限

特定のツールをdenyしても、**別のツールで同じ目的を達成される可能性がある**。例えば`Bash(cat:*)`をdenyしても、ReadツールやechoでファイルReadが可能。完全なブロックには関連するすべてのツールをdenyする必要がある。

### 正規表現パターンは非推奨

`Bash(echo .*)`のような正規表現パターンは予期せぬ動作が発生。`/permissions`でも表示されず、ブロックも許可も意図通りに機能しない。**素直に`:*`によるプレフィックスマッチングのみを使用すること**。

### --dangerously-skip-permissionsの挙動

- `deny`に設定したルールは**有効なまま**
- `ask`に設定したルールは**スキップされる**

確認を絶対に強制したい操作は`deny`に設定しておくのが確実。
