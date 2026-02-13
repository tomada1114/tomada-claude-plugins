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
    "allow": ["Bash(npm run test *)"],
    "deny": ["Bash(rm -rf *)"]
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
    "allow": ["Bash(npm *)", "Bash(git *)"]
  }
}
```

### deny（禁止）
指定パターンにマッチする操作は**完全にブロック**。

```json
{
  "permissions": {
    "deny": ["Bash(rm -rf *)", "Read(.env)"]
  }
}
```

### ask（確認を強制）
指定パターンにマッチする操作は、**allowに含まれていても毎回確認プロンプトを表示**。

```json
{
  "permissions": {
    "allow": ["Bash(git *)"],
    "ask": ["Bash(git push *)"]
  }
}
```

## ルールの優先度

**優先度: Deny > Ask > Allow**

同じ操作が複数のルールにマッチした場合、denyが最優先、次にask、最後にallow。

```json
{
  "permissions": {
    "allow": ["Bash(echo *)"],
    "deny": ["Bash(echo secret *)"]
  }
}
```
→ `echo hello`は自動実行、`echo secret data`は拒否

## Bashパターンの書き方：ワイルドカードマッチング

Bashパーミッションのパターンは**globスタイルのワイルドカード`*`**で動作。`*`はコマンドの**任意の位置**（先頭・中間・末尾）に配置可能。

### 基本的な書き方

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(git commit *)",
      "Bash(git * main)",
      "Bash(* --version)",
      "Bash(* --help *)"
    ],
    "deny": [
      "Bash(git push *)"
    ]
  }
}
```

### スペースの有無による挙動の違い

`*`の前にスペースがあるかないかで**ワードバウンダリ**の扱いが変わる:

| パターン | マッチ | 不一致 |
| --- | --- | --- |
| `Bash(ls *)` | `ls -la`, `ls` | `lsof` |
| `Bash(ls*)` | `ls -la`, `ls`, `lsof` | - |

スペース+`*`（`ls *`）はプレフィクスの後にスペースまたは文字列末尾を要求する。スペースなし`*`（`ls*`）はそのような制約がない。

### `Bash(*)`について

`Bash(*)`は`Bash`（括弧なし）と同等で、**すべてのBashコマンド**にマッチする。

### シェル演算子の認識

Claude Codeは`&&`などのシェル演算子を認識する。`Bash(safe-cmd *)`というルールは`safe-cmd && other-cmd`の実行を許可**しない**。

### `:*`は非推奨

旧来の`:*`サフィックス構文（例: `Bash(npm:*)`）は` *`と同等だが、**deprecated（非推奨）**。新しい設定では`*`を使用すること。

### よくある間違い（動作しない）
```json
// ❌ 正規表現は使えない
"Bash(echo .*)"

// ❌ **（再帰glob）は使えない
"Bash(rm -rf **)"
```

### Bashパターンの脆弱性に関する注意

コマンド引数を制約するBashパターンは**脆弱**である。例えば`Bash(curl http://github.com/ *)`はGitHub URLに制限するつもりでも、以下のバリエーションにはマッチしない:

- オプションがURL前: `curl -X GET http://github.com/...`
- プロトコル違い: `curl https://github.com/...`
- リダイレクト: `curl -L http://bit.ly/xyz`（GitHubにリダイレクト）
- 変数展開: `URL=http://github.com && curl $URL`

**より確実な代替手段:**
- Bashのネットワークツール（`curl`, `wget`等）をdenyし、`WebFetch(domain:github.com)`で許可ドメインを制御
- PreToolUseフックでURLバリデーションを実装
- CLAUDE.mdで許可パターンを指示

## Read/Editのパス記法

[gitignore](https://git-scm.com/docs/gitignore)仕様に準拠した4種類のパターンで記述。

```json
{
  "permissions": {
    "deny": ["Read(.env)", "Read(.env.*)", "Read(**/secrets/**)"]
  }
}
```

| 記法 | 意味 | 例 | マッチ対象 |
| --- | --- | --- | --- |
| `//path` | ファイルシステムルートからの**絶対パス** | `Read(//Users/alice/secrets/**)` | `/Users/alice/secrets/**` |
| `~/path` | **ホームディレクトリ**からのパス | `Read(~/Documents/*.pdf)` | `/Users/alice/Documents/*.pdf` |
| `/path` | **設定ファイルからの相対パス** | `Edit(/src/**/*.ts)` | `<settings file path>/src/**/*.ts` |
| `path` または `./path` | **現在ディレクトリ**からの相対パス | `Read(*.env)` | `<cwd>/*.env` |

**⚠️ 注意**: `/Users/alice/file` は絶対パスではない。設定ファイルからの相対パスとして解釈される。絶対パスには `//Users/alice/file` を使用すること。

**globパターンの違い**: `*`は単一ディレクトリ内のファイルにマッチ、`**`はディレクトリを再帰的にマッチ。すべてのファイルアクセスを許可するには括弧なしのツール名（`Read`, `Edit`, `Write`）を使用。

## 主要な設定ファイル

### グローバル設定
**場所**: `~/.claude/settings.json`
**スコープ**: すべてのプロジェクト

```json
{
  "model": "sonnet",
  "cleanupPeriodDays": 30,
  "permissions": {
    "allow": ["Bash(npm run test *)"],
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
      "Bash(npm run test *)",
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
      "Bash(npm run test *)",
      "Read(~/.zshrc)"
    ],
    "deny": [
      "Bash(curl *)",
      "WebFetch"
    ],
    "ask": [
      "Bash(git push *)"
    ],
    "additionalDirectories": ["../docs/"],
    "defaultMode": "default"
  }
}
```

### defaultModeの選択肢

| モード | 動作 | 用途 |
| --- | --- | --- |
| `default` | 各ツールの初回使用時に確認プロンプトを表示 | 標準動作 |
| `acceptEdits` | ファイル編集権限をセッション中自動承認 | バランス型 |
| `plan` | 分析のみ可能、ファイル変更やコマンド実行は不可 | 計画・レビュー |
| `dontAsk` | `/permissions`やallowルールで事前承認されたツール以外は自動拒否 | 厳格制御 |
| `bypassPermissions` | すべての権限チェックをスキップ | 危険、sandbox併用推奨 |

**⚠️ 注意**:
- `bypassPermissions`は`--dangerously-skip-permissions`フラグと同等。**denyルールは有効なまま**（askのみスキップ）
- `bypassPermissions`は管理者が`disableBypassPermissionsMode`で無効化可能

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
      "Bash(ls *)",
      "Bash(cat *)",
      "Bash(echo *)",
      "Bash(touch *)",
      "Bash(mkdir *)",
      "Bash(cp *)",
      "Read",
      "Edit",
      "Write"
    ],
    "deny": [
      "Bash(sudo *)",
      "Bash(rm -rf *)",
      "Bash(git reset *)",
      "Bash(git rebase *)",
      "Bash(wget *)",
      "Read(**/.env*)",
      "Read(id_rsa)",
      "Read(id_ed25519)",
      "Read(**/*token*)",
      "Read(**/*key*)",
      "Write(**/.env*)",
      "Write(**/secrets/**)"
    ],
    "ask": [
      "Bash(rm *)",
      "Bash(mv *)",
      "Bash(curl *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(git push *)",
      "Bash(git merge *)"
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
      "Bash(npm run *)",
      "Bash(npm test *)",
      "Bash(npx tsc *)",
      "Bash(npx prettier *)",
      "Bash(npx eslint *)"
    ],
    "ask": [
      "Bash(npm install *)",
      "Bash(npm uninstall *)"
    ]
  }
}
```

### Python プロジェクト

```json
{
  "permissions": {
    "allow": [
      "Bash(python *)",
      "Bash(python3 *)",
      "Bash(pytest *)",
      "Bash(ruff *)",
      "Bash(mypy *)"
    ],
    "ask": [
      "Bash(pip install *)",
      "Bash(pip uninstall *)",
      "Bash(uv add *)",
      "Bash(uv remove *)"
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

不正なパターンがあると警告が表示される。

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

## ツール別パーミッションルール

### WebFetch

ドメイン指定でアクセスを制御:

```json
{
  "permissions": {
    "allow": ["WebFetch(domain:example.com)"],
    "deny": ["WebFetch"]
  }
}
```

**注意**: WebFetchをdenyしてもBashが許可されていれば`curl`や`wget`でネットワークアクセスが可能。

### MCP（Model Context Protocol）

MCPサーバーのツールを制御:

| ルール | 効果 |
| --- | --- |
| `mcp__puppeteer` | puppeteerサーバーの全ツールにマッチ |
| `mcp__puppeteer__*` | 同上（ワイルドカード構文） |
| `mcp__puppeteer__puppeteer_navigate` | 特定ツールのみにマッチ |

```json
{
  "permissions": {
    "allow": ["mcp__github__*"],
    "deny": ["mcp__puppeteer__puppeteer_navigate"]
  }
}
```

### Task（サブエージェント）

サブエージェントの使用を制御:

| ルール | 効果 |
| --- | --- |
| `Task(Explore)` | Exploreサブエージェントにマッチ |
| `Task(Plan)` | Planサブエージェントにマッチ |
| `Task(Verify)` | Verifyサブエージェントにマッチ |

```json
{
  "permissions": {
    "deny": ["Task(Explore)"]
  }
}
```

CLI引数`--disallowedTools`でも制御可能。

## パーミッションとサンドボックスの相互作用

パーミッションとサンドボックスは**補完的なセキュリティレイヤー**:

| レイヤー | 対象 | 制御方法 |
| --- | --- | --- |
| **パーミッション** | すべてのツール（Bash, Read, Edit, WebFetch, MCP等） | ルールベースで許可/拒否 |
| **サンドボックス** | Bashツールのみ（とその子プロセス） | OSレベルでファイルシステム・ネットワークを制限 |

**防御の深層化（Defense in Depth）:**
- パーミッションのdenyルール → Claude Codeが制限リソースへのアクセスを試みること自体をブロック
- サンドボックス → プロンプトインジェクションがClaudeの判断をバイパスしても、Bashコマンドが境界外のリソースに到達するのを防止
- ファイルシステム制限 → サンドボックスはRead/Editのdenyルールを使用（個別のサンドボックス設定ではない）
- ネットワーク制限 → WebFetchパーミッションルール + サンドボックスの`allowedDomains`リストの組み合わせ

## マネージド設定（エンタープライズ）

組織でClaude Code設定を集中管理するための機能。管理者がシステムディレクトリに`managed-settings.json`を配置し、ユーザーやプロジェクト設定でオーバーライドできないポリシーを強制する。

### 配置場所

| OS | パス |
| --- | --- |
| **macOS** | `/Library/Application Support/ClaudeCode/managed-settings.json` |
| **Linux/WSL** | `/etc/claude-code/managed-settings.json` |
| **Windows** | `C:\Program Files\ClaudeCode\managed-settings.json` |

**注意**: システムワイドのパス（`~/Library/...`ではない）。管理者権限が必要。

### マネージド設定専用の項目

| 設定 | 説明 |
| --- | --- |
| `disableBypassPermissionsMode` | `"disable"`で`bypassPermissions`モードと`--dangerously-skip-permissions`フラグを無効化 |
| `allowManagedPermissionRulesOnly` | `true`でユーザー/プロジェクトのallow/ask/denyルールを無効化。マネージド設定のルールのみ適用 |
| `allowManagedHooksOnly` | `true`でユーザー/プロジェクト/プラグインのフックを無効化。マネージドフックとSDKフックのみ許可 |
| `strictKnownMarketplaces` | ユーザーが追加できるプラグインマーケットプレイスを制御 |

## 検証結果と注意点

### denyの制限

特定のツールをdenyしても、**別のツールで同じ目的を達成される可能性がある**。例えば`Bash(cat *)`をdenyしても、Readツールやechoでファイル読み取りが可能。完全なブロックには関連するすべてのツールをdenyする必要がある。

### 正規表現パターンは非サポート

`Bash(echo .*)`のような正規表現パターンは予期せぬ動作が発生。`/permissions`でも表示されず、ブロックも許可も意図通りに機能しない。**`*`によるワイルドカードマッチングのみを使用すること**。

### --dangerously-skip-permissionsの挙動

- `deny`に設定したルールは**有効なまま**
- `ask`に設定したルールは**スキップされる**

確認を絶対に強制したい操作は`deny`に設定しておくのが確実。

## 設定例リポジトリ

公式の設定例が[GitHubリポジトリ](https://github.com/anthropics/claude-code/tree/main/examples/settings)で公開されている。一般的なデプロイシナリオ向けのスターター設定として活用可能。
