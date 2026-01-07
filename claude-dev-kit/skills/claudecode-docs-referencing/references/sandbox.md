# サンドボックス機能

> Claude Codeのサンドボックス機能によるセキュリティ保護とファイルシステム・ネットワークの分離。

## サンドボックスとは

サンドボックスは、OSレベルのプリミティブを使用したファイルシステムとネットワークの分離を実現するセキュリティ機能です。従来の権限ベースのセキュリティの問題を解決します：

- **許可疲れ（Approval fatigue）**: 毎回の確認が必要だと注意散漫になる
- **生産性低下**: 常に中断が発生する
- **自律性の制限**: 許可待ちで効率が低下

サンドボックスにより：
1. 明確な境界線を事前に設定
2. 安全なコマンドは許可プロンプト不要
3. セキュリティは維持
4. Claude Codeの自律性向上

## サンドボックスの仕組み

### OS レベルの分離

Claude Codeは各OSのネイティブサンドボックス技術を使用：

| OS | 技術 |
|----|------|
| **macOS** | Seatbelt |
| **Linux** | [bubblewrap](https://github.com/containers/bubblewrap) |
| **Windows** | 今後予定 |

### 制限される操作

1. **ファイルシステム**: 現在の作業ディレクトリとその下位ディレクトリのみ書き込み可能
2. **ネットワーク**: プロキシサーバーによるドメインレベルの制限
3. **プロセス**: スクリプト、プログラム、サブプロセス全てに同じ制限を適用

## サンドボックスの有効化

### スラッシュコマンドでの有効化

```bash
/sandbox
```

メニューで2つのモードから選択できます：

1. **Auto-allow mode**: サンドボックス内のbashコマンドは自動許可。ネットワーク制限等で実行不可な場合はフォールバック。
2. **Regular permissions mode**: 全コマンドが標準許可フロー。より多くの制御が可能だが、確認が多い。

### 設定ファイルでの有効化

`settings.json`（`~/.claude/settings.json` または `.claude/settings.json`）で設定：

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "excludedCommands": ["docker"],
    "allowUnsandboxedCommands": true,
    "network": {
      "allowUnixSockets": ["~/.ssh/agent-socket"],
      "allowLocalBinding": true,
      "httpProxyPort": 8080,
      "socksProxyPort": 8081
    },
    "enableWeakerNestedSandbox": false
  }
}
```

### 設定フィールド詳細

| フィールド | デフォルト | 説明 |
|----------|---------|------|
| `enabled` | `false` | サンドボックスを有効化（macOS/Linux のみ） |
| `autoAllowBashIfSandboxed` | `true` | サンドボックス内のbashコマンドを自動許可 |
| `excludedCommands` | `[]` | サンドボックス外で実行するコマンド（例: `docker`） |
| `allowUnsandboxedCommands` | `true` | `dangerouslyDisableSandbox`フラグの使用許可 |
| `network.allowUnixSockets` | `[]` | アクセス可能なUNIXソケットパス（SSH Agent等） |
| `network.allowLocalBinding` | `false` | ローカルホストポートバインディング許可（macOSのみ） |
| `network.httpProxyPort` | 自動 | HTTPプロキシポート（カスタムプロキシ使用時） |
| `network.socksProxyPort` | 自動 | SOCKS5プロキシポート（カスタムプロキシ使用時） |
| `enableWeakerNestedSandbox` | `false` | Docker環境での弱められたサンドボックス（Linuxのみ） |

## ファイルシステム制限

### デフォルトの動作

- **書き込み**: 現在作業中ディレクトリとその下位ディレクトリのみ
- **読み取り**: コンピュータ全体（`permissions.deny`で指定されたディレクトリ除外）

### 読み取り制限のカスタマイズ

`permissions.deny`で機密ファイルへの読み取りをブロック：

```json
{
  "permissions": {
    "deny": [
      "Read(.envrc)",
      "Read(~/.aws/**)",
      "Read(.env)",
      "Read(.env.*)"
    ]
  }
}
```

## ネットワーク制限

サンドボックス外で実行されるプロキシサーバーにより制御されます：

- **ドメイン制限**: 許可されたドメインのみアクセス可能
- **ユーザー確認**: 新しいドメイン要求は許可プロンプトをトリガー
- **包括的カバレッジ**: スクリプト、プログラム、サブプロセス全てに適用

### ネットワーク設定

```json
{
  "sandbox": {
    "network": {
      "allowUnixSockets": ["~/.ssh/agent-socket"],
      "allowLocalBinding": true,
      "httpProxyPort": 8080,
      "socksProxyPort": 8081
    }
  }
}
```

### デフォルトでブロックされる操作

- `curl`、`wget`による未許可ドメインへのアクセス
- 未許可ドメインへのAPI呼び出し
- 外部サーバーへの任意データ送信

## サンドボックスの一時的な無効化

特定のコマンドでサンドボックス制限が問題になる場合：

### dangerouslyDisableSandboxフラグ

Claude Codeがサンドボックス制限でコマンド実行に失敗した場合、自動的に`dangerouslyDisableSandbox`パラメータを使用する可能性があります。この場合は標準的な権限フロー（ユーザー許可が必要）で実行されます。

このフラグを無効化するには：

```json
{
  "sandbox": {
    "allowUnsandboxedCommands": false
  }
}
```

`false`に設定すると、全コマンドはサンドボックス内で実行されるか、`excludedCommands`に明示的にリストされる必要があります。

### 特定コマンドの除外

サンドボックスと互換性のないコマンドを除外：

```json
{
  "sandbox": {
    "excludedCommands": ["docker", "watchman"]
  }
}
```

### 対話モードでの無効化

```bash
/sandbox
```

メニューから設定を変更できます。

## トラブルシューティング

### 「Operation not permitted」エラー

サンドボックスによるアクセス拒否の可能性：

```bash
# サンドボックスの状態を確認
/sandbox

# excludedCommandsにコマンドを追加するか、許可プロンプトで承認
```

### 特定のツールとの互換性問題

一部のツールはサンドボックスと互換性がない場合があります：

```json
{
  "sandbox": {
    "excludedCommands": ["docker", "watchman"]
  }
}
```

**互換性のヒント**:
- `watchman`: Jestで使用する場合は`jest --no-watchman`を推奨
- `docker`: サンドボックス非互換のため除外が必要

### ネットワーク接続の失敗

新しいドメインへのアクセス要求は許可プロンプトが表示されます。許可すると、そのドメインへのアクセスが可能になります。

## ベストプラクティス

### 1. 制限的に開始

最小限の権限から始め、必要に応じて緩和：

```json
{
  "sandbox": {
    "enabled": true,
    "allowUnsandboxedCommands": false
  }
}
```

### 2. 機密ファイルの保護

`permissions.deny`で機密ファイルを保護：

```json
{
  "permissions": {
    "deny": [
      "Read(.envrc)",
      "Read(~/.aws/**)",
      "Read(.env)",
      "Read(.env.*)",
      "Read(**/credentials*)",
      "Read(**/secrets*)"
    ]
  }
}
```

### 3. 環境別設定

開発環境とプロダクション環境で異なるルールを使用。

### 4. チーム設定の共有

`.claude/settings.json`でサンドボックス設定を共有し、チーム全体で一貫したセキュリティを確保。

### 5. 設定テスト

正規ワークフローをブロックしないか確認してから本番適用。

## セキュリティの制限事項

公式ドキュメントで明記されている既知の制限：

1. **ネットワークフィルタリングの限界**: ドメインレベルでのみ機能（トラフィック検査なし）
2. **Unix Socketによる権限昇格**: `allowUnixSockets`の過度な許可は危険（例：`/var/run/docker.sock`許可）
3. **ファイルシステム権限昇格**: `$PATH`内の実行可能ファイルを含むディレクトリへの広すぎる書き込み許可は危険
4. **Linuxサンドボックス強度**: `enableWeakerNestedSandbox`はDockerで使用可能だが、セキュリティが大幅に低下

## 子プロセスの継承

サンドボックス内で実行されるコマンドが子プロセスを生成する場合、その子プロセスも同じサンドボックス制限を継承します。

例：`npm install`が`node`を呼び出す場合、`node`も同じ制限下で動作します。

## オープンソース

サンドボックスランタイムはNPMパッケージとして提供されています：

```bash
npx @anthropic-ai/sandbox-runtime <command-to-sandbox>
```

[GitHub リポジトリ](https://github.com/anthropic-experimental/sandbox-runtime)で実装詳細を確認できます。

## 参考リンク

- [Claude Code Sandboxing Guide](https://docs.anthropic.com/en/docs/claude-code/sandboxing)
- [Claude Code Settings Reference](https://docs.anthropic.com/en/docs/claude-code/settings)
