# Claude Code on the Web

Claude Code のWebブラウザ版。GitHubリポジトリに対してクラウド上でエージェントが作業を行う。

---

## 本質的な特徴

### 何ができるのか

- **ブラウザだけで開発可能** - ローカル環境構築不要
- **並列タスク実行** - 複数のタスクを同時に投げっぱなしにできる（Fire-and-Forget）
- **PR作成まで一貫** - コード修正→テスト実行→PR作成がWeb上で完結
- **モバイルアクセス** - スマホからでも緊急対応可能

### 本質的な制約（構造上変わらないもの）

1. **GitHubのみ対応** - GitLab/Bitbucket/Azure DevOpsは非対応
2. **サンドボックス環境** - Dockerビルド不可、ローカルリソース（DB、.env等）へのアクセス不可
3. **プライベートレジストリ問題** - 認証ヘッダーがプロキシで削除される設計上の制約
4. **コンテキストギャップ** - 「ローカルで起きていること」を知らない（エラーログ等はペースト必要）

---

## Web版 vs CLI版：使い分けの判断基準

### Web版が向いているケース

| 条件 | 理由 |
|------|------|
| GitHubにホストされている | 必須要件 |
| 独立したタスクを複数並列で回したい | 並列実行が最大の強み |
| 標準的な開発環境 | サンドボックスの制約を受けにくい |
| 軽量なビルドプロセス | メモリ制約をクリア |
| プライベートレジストリ不使用 | 認証問題を回避 |

### CLI版を選ぶべきケース

| 条件 | 理由 |
|------|------|
| GitLab/Bitbucket/Azure DevOps使用 | Web版は非対応 |
| ローカルDB/Docker/特殊環境が必要 | サンドボックスではアクセス不可 |
| 「手元の環境でのみ再現するバグ」を調査 | コンテキストギャップの問題 |
| プライベートパッケージレジストリ必須 | 認証ヘッダー問題を回避 |
| コスト重視 | API従量課金のみで済む |

---

## アクセス方法

### URL
- `https://claude.ai/code` または `https://code.claude.com`

### 必須条件
1. Anthropicアカウント
2. 有料サブスクリプション（Pro/Maxプランのみ。Team/Enterpriseプレミアムシートは近日対応予定）
3. GitHubアカウント（リポジトリアクセス権限付き）
4. 対応地域からのアクセス

### モバイルアクセス
- iOS/Android公式アプリ内の「Code」モード
- モバイルブラウザで「デスクトップ用Webサイトを表示」

---

## GitHub連携のセットアップ

### 手順概要
1. `claude.ai/code` にログイン → 「Connect GitHub」
2. GitHub OAuth認証ページでアクセス許可
3. **Claude GitHub App** をインストール
4. リポジトリへの権限付与（**「Only select repositories」を強く推奨**）

### GitHub Appが要求する権限

| 権限 | レベル | 用途 |
|------|--------|------|
| Contents | Read & Write | コードの読み取り・修正・作成 |
| Issues | Read & Write | Issue理解・コメント投稿 |
| Pull requests | Read & Write | PR作成・レビューコメント |
| Metadata | Read-only | リポジトリ基本情報取得 |

### 組織（Organization）への導入時の注意
- Owner権限がないと「管理者への承認リクエスト」状態になる
- 管理者がGitHub設定画面から承認する必要がある

---

## 基本的な使い方

### ワークフロー
1. **リポジトリ選択** - ダッシュボードから対象リポジトリをクリック
2. **タスク指示** - チャット欄にプロンプト入力
3. **プラン確認** - Claudeが提示するプランを承認
4. **差分確認** - 変更内容（Diff）を目視確認
5. **テスト実行** - 「テストを実行して」と指示
6. **PR作成** - 「PRを作成して」と指示、またはUIのボタン

### プロンプトのコツ

**悪い例：**
> バグを直して

**良い例：**
> `src/components/Button.tsx` の `onClick` イベントが発火しないバグを調査し、修正してください。修正後は関連するテストを実行してください

### 並列実行
- ブラウザのタブごとに独立したセッション
- 待ち時間（テスト実行中など）に別タブで作業可能

---

## CLI連携：Open in CLI

Webセッションをローカルに「テレポート」させる機能。

### 使い方
1. Web UIの「Open in CLI」ボタンをクリック
2. コマンドがクリップボードにコピーされる
   ```bash
   claude --teleport <session-uuid>
   ```
3. ローカルでリポジトリをチェックアウトし、作業ブランチに移動
4. コマンドをターミナルで実行

### 実行時の動作
```bash
──────────────────────────────────────────────────────────────────────────────
 Teleport to Repo

 Open Claude Code in user/repo-name:

 ❯ 1. Use ~/workspace/repo-name
   2. Cancel

 Enter to confirm · Esc to cancel
```
- 引き継いだ後はWeb版の続きとしてそのまま作業を継続可能

### 何が同期されるか
- 会話履歴（プロンプト、思考プロセス、ツール実行結果）
- Git状態（Webで作成されたブランチをフェッチ・チェックアウト）

### 注意点
- ローカルに未コミット変更があるとスタッシュまたは警告される
- クリーンな状態で実行するのが望ましい

---

## SessionStartフックによる依存関係の自動インストール

Claude Code on the Webでは、HooksのSessionStartフックを使って依存関係のインストールを自動化できる。

### 設定方法

`.claude/settings.json` に以下のように記述：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/scripts/install_pkgs.sh"
          }
        ]
      }
    ]
  }
}
```

### セットアップスクリプト例（Node.js）

`scripts/install_pkgs.sh`:

```bash
#!/bin/bash

echo "📦 Installing dependencies..."

if [ -f "package.json" ]; then
  echo "Installing npm packages..."
  npm install
else
  echo "⚠️  No package.json found"
fi

exit 0
```

Pythonプロジェクトの場合は `pip install -r requirements.txt` に置き換え。

---

## クラウド環境の設定

チャット入力欄近くの「Default」から環境を追加・設定可能。

### ネットワークアクセスレベル

| レベル | 説明 |
|--------|------|
| なし | ネットワークアクセスを全く許可しない |
| Trusted | 検証済みのソース（github.com, npmjs.com等）のみ許可 |
| Full | すべてのネットワークアクセスを許可 |
| カスタム | 許可するドメインを自由に指定 |

カスタムでは、npmなどの一般的なパッケージマネージャーをチェックマークで簡単に許可可能。

### 環境変数の設定

クラウド環境の設定画面内「環境変数」欄で設定。`.env`と同様の`KEY=VALUE`形式。

### デフォルト許可ドメイン

| カテゴリ | 許可ドメイン例 |
|---------|--------------|
| バージョン管理 | github.com, gitlab.com, bitbucket.org |
| パッケージレジストリ | registry.npmjs.org, pypi.org, crates.io |
| クラウドプラットフォーム | *.googleapis.com, *.microsoftonline.com |
| コンテナレジストリ | ghcr.io, mcr.microsoft.com |

---

## 技術的制約の詳細

### サンドボックス環境

セキュリティのため、gVisor等によるカーネルレベルの隔離環境で動作。

**ブロックされる操作：**
- `ptrace` - デバッガ・トレーシングツール
- `mount` - ファイルシステムマウント（Docker in Docker不可）
- システムレベル制御全般

### ⚠️ リソース制限（要確認：変更される可能性あり）

| リソース | 制限値 | 影響 |
|----------|--------|------|
| vCPU | 2コア | 重いコンパイル（Rust, C++）で速度低下 |
| RAM | 4GB | **最もクリティカル**。Webpack/Next.js/JVMでOOM発生リスク |
| ストレージ | 10GB | 一時的。セッション終了で破棄 |
| ネットワーク | 1Gbps | 帯域は十分だがファイアウォール制限あり |

### セッション寿命
- アイドル状態や一定時間経過でセッション破棄
- 長時間バックグラウンド処理（データ移行、ML学習など）は非対応
- セッションリセット時、インストールしたパッケージや環境変数は消失

### プリインストール環境（Ubuntu 22.04ベース）

**言語：** Python, Node.js, Ruby, PHP, Java, Go, Rust, C++
**DB（開発用）：** PostgreSQL, Redis（データ永続化なし）
**ツール：** git, curl, wget, jq, zip/unzip等

### ネットワーク制限

**デフォルト許可：**
- Anthropic API
- github.com
- 主要パブリックパッケージレジストリ（npm, PyPI, Maven等）

**制限：**
- WebFetchは評判分析サービスによる事前チェックあり
- 未承認ドメインはブロックされる可能性

---

## ⚠️ 変更可能性の高い情報（執筆時は公式確認推奨）

### 料金体系
- 個人向け：Pro / Max
- 組織向け：Team Standard（CC-Web非対応）/ Team Premium / Enterprise
- 詳細な価格は公式サイトで確認

### 並列実行数
- プランによって異なる（Pro < Max）
- 具体的な数は変更される可能性あり

### Research Preview状態
- 現在はプレビュー段階
- GA（正式リリース）時期は未確定
- プラットフォーム対応拡大（GitLab等）のロードマップあり

---

## 運用回避策（ワークアラウンド）

| 問題 | 回避策 |
|------|--------|
| GitLab/Bitbucket使用 | GitHubミラーリング or CLI版使用 |
| メモリ不足（OOM） | 分割ビルド or CLI版使用 |
| プライベートパッケージ不可 | Vendoring（.tgzコミット） or CLI版使用 |
| Localhost接続不可 | ngrok/Cloudflare Tunnelでトンネリング |
| Docker不可 | Docker非依存のテスト設計 or GitHub Actions委譲 |
| 作業ブランチ以外へのpush不可 | PRフロー準拠の運用 |

---

## 執筆時の参照ポイント

### 強調すべき強み
1. 環境構築不要の手軽さ
2. 並列タスク実行による生産性向上
3. モバイルアクセス可能
4. CLI連携（Open in CLI）によるハイブリッドワークフロー
5. SessionStartフックによる依存関係の自動インストール
6. クラウド環境の柔軟な設定（ネットワークアクセスレベル、環境変数）

### 注意喚起すべき点
1. GitHubのみ対応（他プラットフォーム非対応）
2. サンドボックス制約（Docker不可、ローカルリソース不可）
3. メモリ・リソース制限
4. プライベートレジストリ問題

### 使い分けの推奨
- **Web版向き**: 軽量タスク、並列実行、標準環境
- **CLI版向き**: 複雑な環境依存、GitHub以外、コスト重視
