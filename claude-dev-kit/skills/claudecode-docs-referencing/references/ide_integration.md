# 06. IDE との連携

## サポートされている IDE

Claude Code は以下の IDE と統合できます:

### VS Code 系
- **Visual Studio Code**（公式拡張機能対応）
- **Cursor**（拡張機能対応）
- **Windsurf**

### JetBrains IDE
- **IntelliJ IDEA** - Java/Kotlin 開発
- **PyCharm** - Python 開発
- **WebStorm** - JavaScript/TypeScript 開発
- **GoLand** - Go 開発
- **PhpStorm** - PHP 開発
- **Android Studio** - Android 開発

## IDE 連携の主要機能

### 1. クイック起動
キーボードショートカットで Claude Code を素早く起動

- **Mac**: `Cmd+Esc`
- **Windows/Linux**: `Ctrl+Esc`

### 2. ファイル参照ショートカット
現在開いているファイルをClaudeに素早く共有

- **Mac**: `Cmd+Option+K`
- **Windows/Linux**: `Alt+Ctrl+K`

### VS Code 拡張機能専用ショートカット

| 機能 | Mac | Windows/Linux |
|------|-----|---------------|
| 新規タブで開く | `Cmd+Shift+Esc` | `Ctrl+Shift+Esc` |
| 新規会話 | `Cmd+N` | `Ctrl+N` |
| @メンション参照を挿入 | `Alt+K` | `Alt+K` |

### 3. IDE差分ビュー
ファイル変更をIDE の差分ビューアーで確認

### 4. 診断エラーの自動共有
lint エラーや構文エラーを自動的に Claude と共有（JetBrains IDEのみ）

## VS Code 拡張機能

### 特徴

VS Code向けの公式拡張機能が提供されています:

- **ネイティブサイドバーUI**: VS Code内でClaude Codeを操作
- **インライン差分表示**: 変更箇所を直接確認
- **プランモード編集**: 計画モードでの編集サポート
- **会話履歴共有**: CLIと拡張機能で履歴を共有、`claude --resume`で再開可能
- **要件**: VS Code 1.98.0以上

### インストール

#### 自動インストール

1. VS Code を開く
2. 統合ターミナルを開く (`` Ctrl+` `` or `` Cmd+` ``)
3. ターミナルで `claude` を実行
4. 拡張機能が自動的にインストールされる

#### 手動インストール

1. 拡張機能タブを開く（`Cmd+Shift+X` / `Ctrl+Shift+X`）
2. "Claude Code" を検索
3. インストールをクリック

### セキュリティ考慮事項

- **制限モード推奨**: 信頼されていないワークスペースでは制限モードを使用
- **オート承認に注意**: IDE統合でオート承認を有効にすると、IDE設定ファイルの自動実行による脆弱性があります。信頼できないコードを扱う場合は手動承認を推奨
- 拡張機能は承認されたアクションのみ実行

### 設定

VS Code の設定（`Cmd+,` / `Ctrl+,`）で以下のオプションを調整できます:

| 設定項目 | 説明 |
|---------|------|
| Selected Model | デフォルトモデル |
| Use Terminal | ターミナルモード使用（グラフィカルパネルの代わり） |
| Initial Permission Mode | パーミッション確認モード |
| Preferred Location | パネルの位置（サイドバー/新規タブ） |
| Autosave | ファイル自動保存 |
| Use Ctrl+Enter to Send | Enter代わりにCtrl/Cmd+Enterで送信 |
| Respect Git Ignore | .gitignoreを尊重 |

### CLIとの機能比較

| 機能 | CLI | 拡張機能 |
|------|-----|---------|
| スラッシュコマンド | 完全対応 | 一部のみ |
| MCP設定 | サポート | CLIで設定、拡張機能で利用 |
| チェックポイント | サポート | Coming soon |
| `!` bash短縮 | サポート | 未実装 |
| タブ補完 | サポート | 未実装 |

## Cursor / Windsurf のセットアップ

### 自動インストール

1. IDE を開く
2. 統合ターミナルを開く
3. ターミナルで `claude` を実行
4. 自動的に設定される

### 手動セットアップ

外部ターミナルから接続する場合:

```bash
claude
> /ide
```

これで現在の IDE に接続されます。

## JetBrains IDE のセットアップ

### 対応IDE

- IntelliJ IDEA
- PyCharm
- WebStorm
- GoLand
- PhpStorm
- Android Studio

### インストール方法

1. **プラグインマーケットプレイスからインストール**:
   - Settings → Plugins → Marketplace
   - "Claude Code" を検索
   - インストールをクリック
   - IDE を完全再起動

2. **外部ターミナルから接続**:
   - 外部ターミナルで `claude` を起動
   - `/ide` コマンドを実行

### ショートカット

- **起動**: `Cmd+Esc` (Mac) / `Ctrl+Esc` (Windows/Linux)
- **ファイル参照**: `Cmd+Option+K` (Mac) / `Alt+Ctrl+K` (Windows/Linux)

### 自動IDE検出

Claude Codeは実行中のJetBrains IDEを自動検出します。複数のIDEが開いている場合は選択プロンプトが表示されます。

### JetBrains IDE設定

Settings → Tools → Claude Code で以下を設定できます:

- **Claude command**: カスタムパス指定可能（WSL利用時は`wsl -d Ubuntu -- bash -lic "claude"`）
- **ESC キー設定**: ターミナル割り当て競合時に調整

## 実践的な使い方

### ワークフロー例 1: コードレビュー

1. IDE でファイルを開く
2. `Cmd+Esc` (Mac) で Claude Code を起動
3. Claude にコードレビューを依頼
   ```
   > このファイルをレビューして、改善点を教えて
   ```
4. 変更提案が IDE の差分ビューで表示される
5. 変更を承認または却下

### ワークフロー例 2: バグ修正

1. IDE でエラーが表示される
2. エラーは自動的に Claude に共有される
3. Claude がエラーを分析
4. 修正案が IDE に表示される
5. 差分ビューで変更を確認して適用

### ワークフロー例 3: リファクタリング

1. リファクタリングしたいコードを開く
2. `Cmd+Option+K` でファイルを Claude に共有
3. リファクタリングを依頼
   ```
   > この関数をクリーンアーキテクチャに従ってリファクタリングして
   ```
4. 変更を差分ビューで確認
5. テストを実行して動作確認

## IDE 統合のメリット

### 1. シームレスな体験
- IDE から離れる必要がない
- ファイル参照が簡単
- 変更確認が直感的

### 2. 効率的な開発
- キーボードショートカットで素早くアクセス
- エラーの自動共有
- 差分ビューで変更を視覚的に確認

### 3. コンテキストの維持
- 現在の作業コンテキストを保持
- ファイル間の移動がスムーズ
- コードベース全体を把握しやすい

## 差分ビューの設定

```bash
# Claude Code 内で
/config

# diffTool を "auto" に設定
```

これにより、ファイル変更が IDE の差分ビューアーで表示されます。

## トラブルシューティング

### IDE 拡張機能がインストールされない

**VS Code の場合:**

コマンドパレット (`Cmd+Shift+P`) で:
```
> Extensions: Install Extensions
> "Claude Code" を検索してインストール
```

### /ide コマンドが動作しない

1. IDE が実行されているか確認
2. IDE を完全に再起動
3. IDE のターミナルから claude を起動

```bash
# 設定を確認
/config
```

### ショートカットが機能しない

**キーバインドの競合を確認:**

VS Code:
1. `Cmd+K Cmd+S` でキーボードショートカット設定を開く
2. "Claude" で検索
3. 競合しているショートカットを変更

JetBrains:
1. 設定 → キーマップ
2. "Claude" で検索
3. カスタムショートカットを設定

### 差分ビューが表示されない

```bash
# 設定を確認
/config

# diffTool が "auto" になっているか確認
# なっていない場合は変更して保存
```

### IDEが検出されない

```bash
# IDE を完全に再起動
# Claude Code を再起動して再接続
/ide
```

### JetBrains IDE が WSL2 で検出されない

WSL2環境でJetBrains IDEを使用する場合、追加設定が必要です:

1. Settings → Tools → Claude Code を開く
2. Claude command に `wsl -d Ubuntu -- bash -lic "claude"` を設定
3. IDE を再起動

## 推奨拡張機能

Claude Code と相性の良い拡張機能:

### VS Code
- **GitLens** - Git 履歴の可視化
- **Error Lens** - エラーのインライン表示
- **Prettier** - コードフォーマット
- **ESLint** - JavaScript/TypeScript の lint

### JetBrains
- 標準搭載のGit統合
- コードフォーマッター
- Lintツール

## 次のステップ

IDE 連携を理解したら:
- **07_custom_commands.md** - よく使う操作をコマンド化
- **09_hooks.md** - ファイル保存時の自動処理
- **14_best_practices.md** - IDE と Claude の効率的な使い分け
