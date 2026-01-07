# Practical Tips & Best Practices

Claude Codeを効率的に活用するための実践的なTipsとベストプラクティス集です。

## コンテキスト管理の実践

### コンテキストウィンドウの確認
- `/context` コマンドで現在のコンテキスト占有率を可視化できる
- コンテキストが肥大化すると回答の精度が下がるため、適切なタイミングでの管理が重要

### コンテキストのリセットと圧縮
- `/clear`: 会話履歴をクリアし、新しい実装フェーズに移る時に使用
- `/compact`: 過去のやりとりを要約して保持。「/compact APIの仕様についてフォーカスして」のように指示可能
- タイミング: 「ところで」と言いたくなったら `/clear` のサイン

## ファイル参照とインポート

### @記法でのファイル指定
- 対話モード中に `@` を入力すると、プロジェクト内のファイルをサジェスト
- 複数ファイルを同時に参照可能
- CLAUDE.md内でも `@docs/SPECIFICATION.md` のように他ファイルを参照できる（コードスパン ` で囲むと評価されないので注意）

## デバッグとUI確認

### 画面キャプチャの活用
- Windows: `Windows + Shift + S`
- Mac: `Command + Shift + Control + 4`
- キャプチャをVS Codeに貼り付けて、Claude Codeに「このように修正して」と指示可能
- エラー画面をそのまま見せることで、問題の原因を特定させやすい

## ショートカットと便利機能

### 実行内容の確認
- `Ctrl + R`: 省略された読み込み内容を展開表示
- `Ctrl + T`: 実行プランの進捗状況を表示（TODOリスト）
- `Esc` 2回: チェックポイント一覧を表示し、過去の状態から再開可能

### 編集モードの切り替え
- `Shift + Tab`: Accept Edits Mode（自動編集許可モード）のオン/オフ
- 初回編集時に「Yes, and don't ask again this session」を選択すると同様の効果

## バックグラウンド実行

### 開発サーバーの管理
- 開発サーバー起動後も会話を継続できる
- `/bashes`: バックグラウンドで実行中のBashコマンドを確認・管理
- `Ctrl + B`: 実行中のBashをバックグラウンドに移動（`ENABLE_BACKGROUND_TASKS=1` 設定時）

## セッション管理

### セッションの再開と管理
- `claude --continue` または `claude -c`: 前回の会話から再開
- `/resume`: 過去のセッション一覧から選択して再開（メッセージ数も確認可能）
- セッションごとにGitブランチと紐付けて管理すると整理しやすい

## 拡張思考モード

### Extended Thinking Modeの活用
- 複雑な問題に対してより深い分析を行うモード
- キーワードで発動:
  - 大予算（31,999トークン）: 「熟考」「深く考えて」「ultrathink」「think harder」
  - 中予算（10,000トークン）: 「考えて」「think deeply」
  - 小予算（4,000トークン）: 「think」
- トークンを消費するため、解決困難な問題に限定して使用

## ガードレールの設定

### コード品質を保つ仕組み
- ESLint/Biome: コーディング規約の統一
- Husky: コミット前のlint/test/type-check実行
- CI/CD: GitHub Actionsでの自動テスト・デプロイ
- 早期にこれらを設定することで、Claude Codeの実装ミスを防ぐ

## プロジェクト構造の活用

### CLAUDE.mdの階層的配置
- プロジェクトルート: 全体の設定
- サブディレクトリ: 各モジュール固有の設定
- ユーザールート（~/.claude/CLAUDE.md）: 全プロジェクト共通の設定

## パーミッション管理

### セキュリティと利便性のバランス
- 初回コマンド実行時に許可設定
- `.claude/settings.local.json` で管理（個人設定、Git管理外）
- パターン例: `"Bash(npm:_)"` - npmで始まるコマンドすべて許可
- 外部通信コマンド（curl, wget）は常に確認が入る

## 動作モード

### 4つのモードの使い分け
- `default`: 各ツールの初回使用時に権限確認
- `acceptEdits`: ファイル編集を自動承認（`Shift+Tab`で切り替え）
- `plan`: 分析と計画のみ、実装は行わない
- `bypassPermissions`: すべての権限を自動承認（`claude --dangerously-skip-permissions`、要注意）

## ヘッドレスモード

### 非対話的な利用
```bash
# 単発処理
claude -p "プロンプト" --allowedTools "Edit,Read"

# ログ監視
tail -f app.log | claude -p "異常があれば教えて"
```

## 参照

- [basic_usage.md](basic_usage.md) - 基本的な使い方
- [slash_commands.md](slash_commands.md) - スラッシュコマンド一覧
- [settings.md](settings.md) - 設定ファイルの管理
- [memory_management.md](memory_management.md) - CLAUDE.mdの活用
