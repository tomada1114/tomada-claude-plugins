# 01. インストールガイド

## システム要件

Claude Code は以下のOSに対応しています:

- **macOS**: 10.15以上
- **Ubuntu**: 20.04以上
- **Debian**: 10以上
- **Windows**: WSL（Windows Subsystem for Linux）経由、またはネイティブ

### 前提条件
- **Node.js** 18以上（npm経由でインストールする場合のみ必要）

**Note**: 公式スクリプトでのネイティブインストールではNode.jsは不要です。npmでインストールする場合のみ、[公式サイト](https://nodejs.org/)からNode.jsをダウンロードしてください。

## インストール方法

### 方法1: 公式インストールスクリプト（推奨）

#### macOS / Linux

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

#### Windows（PowerShell）

```powershell
irm https://claude.ai/install.ps1 | iex
```

#### Windows（CMD）

```batch
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

**Note**: ネイティブインストールのインストール先は `/usr/local/bin` です。

### 方法2: Homebrew（macOS）

```bash
brew install --cask claude-code
```

### 方法3: npm（代替手段）

ネイティブインストールがうまくいかない場合の代替手段です。Node.js 18以上が必要です。

```bash
npm install -g @anthropic-ai/claude-code
```

:::message alert
`sudo npm install -g` の使用は避けてください。sudoを付けてnpmをグローバルインストールすると、権限問題やセキュリティリスクの原因になります。
:::

### バージョン指定でのインストール

特定のバージョンをインストールしたい場合:

```bash
# macOS / Linux / WSL（最新版）
curl -fsSL https://claude.ai/install.sh | bash -s latest

# 特定バージョンをインストール（例: 1.0.58）
curl -fsSL https://claude.ai/install.sh | bash -s 1.0.58
```

```powershell
# Windows PowerShell（最新版）
& ([scriptblock]::Create((irm https://claude.ai/install.ps1))) latest

# 特定バージョンをインストール
& ([scriptblock]::Create((irm https://claude.ai/install.ps1))) 1.0.58
```

### インストールの確認

```bash
claude --version
```

### 動作確認（claude doctor）

環境に問題がないか確認したい場合は、診断ツールを使用します:

```bash
claude doctor
```

インストールタイプやバージョン情報、環境設定の状態が表示されます。問題がある場合は警告やエラーメッセージも出力されるため、トラブルシューティングの第一歩として活用できます。

## Windows（WSL）での詳細セットアップ

WSLを使用する場合の詳細な手順です。

### 1. WSLのインストール

PowerShellを**管理者権限**で開き、以下を実行:

```powershell
# WSLを有効化
wsl --install

# Ubuntu（推奨）をインストール
wsl --install -d Ubuntu

# WSL2を既定のバージョンに設定
wsl --set-default-version 2
```

再起動後、Ubuntuを起動して初期設定（ユーザー名とパスワード）を行います。

### 2. Node.jsのインストール（WSL内）

Ubuntuターミナルで以下を実行:

```bash
# Node.jsの公式リポジトリを追加
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# Node.jsをインストール
sudo apt-get install -y nodejs

# バージョン確認（20以上ならOK）
node --version
```

### 3. Claude Codeのインストール（WSL内）

```bash
# 公式スクリプトでインストール（推奨）
curl -fsSL https://claude.ai/install.sh | bash

# または npm でインストール（代替手段）
npm install -g @anthropic-ai/claude-code

# インストール確認
claude --version
```

**Note**: 権限エラーが出た場合は、`sudo npm install -g` ではなく、npmのグローバルディレクトリ変更を推奨します（「トラブルシューティング > 権限エラー」を参照）。

## WSL特有の注意点

### ファイルパスについて
- Windowsのファイルは `/mnt/c/` でアクセス可能
- 例: `C:\Users\YourName\Projects` → `/mnt/c/Users/YourName/Projects`

### 推奨ツール
- **Windows Terminal**: 複数のWSLセッションを管理しやすい
- **VS Code + Remote-WSL拡張機能**: WSL環境との統合が便利

### ネイティブWindows vs WSL

**推奨**: ネイティブWindowsインストール（PowerShellスクリプト使用）
- WSLの互換性問題を回避
- より高速な起動
- シンプルなセットアップ

WSLを使用する場合:
- Linux環境が必要な場合
- 既存のLinuxベースのワークフローがある場合

## トラブルシューティング

### コマンドが見つからない場合（macOS/Linux/Windows）

インストール後に `claude` コマンドが見つからない場合は、ターミナルを再起動してください。シェルの設定ファイル（または環境変数）が再読み込みされることで、パスが通ります。

```bash
# macOS/Linux: ターミナルを再起動するか、以下を実行
source ~/.zshrc  # zshの場合
source ~/.bashrc # bashの場合
```

Windowsの場合は、PowerShellまたはコマンドプロンプトを閉じて再度開いてください。

上記で解決しない場合は、インストールが正常に完了していない可能性があります。再度インストールコマンドを実行してみてください。

### Windows: 実行ポリシーエラー

PowerShellで「スクリプトの実行が無効」というエラーが表示された場合は、実行ポリシーを変更する必要があります。

管理者としてPowerShellを起動し、以下のコマンドを実行してください:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

:::message alert
実行ポリシーの変更はセキュリティに関わる設定です。企業環境などでポリシーが制限されている場合は、IT管理者に相談してください。
:::

### Windows: ウイルス対策ソフトによるブロック

一部のウイルス対策ソフトがインストールスクリプトをブロックする場合があります。一時的にリアルタイム保護を無効にしてインストールを試みてください。インストール完了後は、リアルタイム保護を有効に戻すことを忘れないでください。

### Windows: 管理者権限について

インストール中に権限エラーが発生した場合は、管理者としてPowerShellを起動してください。スタートメニューで「PowerShell」を検索し、右クリックで「管理者として実行」を選択します。

一方で、可能な限り管理者権限なしでインストールするのがおすすめです。管理者権限が不要な場合はユーザーディレクトリにインストールされるため、システム全体に影響を与えません。

### 別バージョンがインストールされている場合

npm経由で以前インストールしていた場合は、先にアンインストールしてからネイティブインストールを実行してください。

```bash
# npm版をアンインストール
npm uninstall -g @anthropic-ai/claude-code

# ネイティブ版をインストール
curl -fsSL https://claude.ai/install.sh | bash
```

アンインストール後にターミナルを再起動してから、ネイティブインストールを実行するとスムーズです。

### WSLインストールの問題

**OS/プラットフォーム検出エラー**

インストール中にエラーが出る場合:

```bash
# インストール前に実行
npm config set os linux

# 強制インストール
npm install -g @anthropic-ai/claude-code --force --no-os-check
```

**Nodeが見つからないエラー**

`exec: node: not found` が表示される場合、WSLがWindowsのNode.jsを使っている可能性があります。

確認方法:
```bash
which npm
which node
```

これらは `/usr/` で始まるLinuxパスを指している必要があります。`/mnt/c/` で始まる場合は、WSL内にNode.jsを再インストールしてください。

### 権限エラー

**ネイティブインストールの場合:**

ネイティブインストールで権限エラーが発生した場合は、`sudo` を付けて再実行できます:

```bash
sudo curl -fsSL https://claude.ai/install.sh | bash
```

ただし、`sudo` の使用はセキュリティ上のリスクを伴います。可能であれば `/usr/local/bin` への書き込み権限を確認し、`sudo` なしでインストールできる環境を整えることをおすすめします。

**npm経由インストールの場合:**

npmのグローバルディレクトリを変更する方法が推奨されます（`sudo npm install -g` は避けてください）:

```bash
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### 認証エラー

```bash
# 再ログイン
claude logout
claude login
```

## アップデート

### 自動アップデート

Claude Codeは起動時に自動的にアップデートを確認します。

### 手動アップデート

```bash
# npm でインストールした場合
npm update -g @anthropic-ai/claude-code

# Homebrew でインストールした場合
brew upgrade --cask claude-code

# 公式スクリプトで再インストール
curl -fsSL https://claude.ai/install.sh | bash
```

## 次のステップ

インストールが完了したら、**02_initial_setup.md** で初期設定を行いましょう。

## アンインストール

### ネイティブインストールの場合（macOS/Linux/WSL）

```bash
rm -f ~/.local/bin/claude
rm -rf ~/.claude-code
```

## 参考リンク

- [Node.js公式サイト](https://nodejs.org/)
- [Claude Code公式ドキュメント](https://docs.anthropic.com/en/docs/claude-code)
- [WSL公式ドキュメント](https://docs.microsoft.com/windows/wsl/)
