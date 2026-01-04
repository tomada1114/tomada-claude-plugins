
# 13. トラブルシューティング

## インストール関連

### Windows WSL で npm が動作しない

**症状**: `exec: node: not found`

**解決法**:
```bash
# パスを確認
which npm
which node

# /mnt/c/ で始まる場合、WSL 内に Node.js をインストール
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### グローバルインストールの権限エラー

**解決法**:
```bash
# sudo を使用
sudo npm install -g @anthropic-ai/claude-code

# または npm のグローバルディレクトリを変更
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

## 接続・認証関連

### API 接続エラー

**症状**: `API Error: Connection error`

**解決法**:
1. VPN を無効化して再試行
2. インターネット接続を確認
3. 時間をおいて再度実行
4. `/status` でステータス確認

### 認証が切れる

**解決法**:
```bash
/logout
/login
```

## パフォーマンス関連

### 応答が遅い・止まる

**原因と対処**:
- **正常**: 複雑なタスクは30-60秒かかる → 待つ
- **コンテキスト過多**: `/clear` でクリア
- **長時間応答なし**: Ctrl+C で中断して再試行

### コンテキストウィンドウがいっぱい

**解決法**:
```bash
# 不要な履歴をクリア
/clear

# または圧縮
/compact

# 新しいセッション
exit
claude
```

## 権限関連

### ツール実行が毎回ブロックされる

**解決法**:
```bash
/permissions

# defaultMode を変更
# default → acceptEdits または bypassPermissions
```

### 間違って "Always Deny" してしまった

**解決法**:
```bash
/permissions

# deny リストから削除
```

## IDE 連携関連

### ショートカットが動作しない

**解決法**:
1. IDE のキーバインド設定を確認
2. 競合するショートカットを無効化
3. カスタムショートカットを設定

### 差分ビューが表示されない

**解決法**:
1. `/config` で Settings UI を開く
2. 差分表示設定を確認
3. IDE 連携が有効か確認（VS Code / JetBrains）

## ファイル操作関連

### ファイルの変更が保存されない

**確認事項**:
1. 変更を承認したか?
2. 権限設定は適切か?
3. ファイルパスは正しいか?

**解決法**:
```bash
# 権限を確認
/permissions

# または手動で承認モードに
/config
# defaultMode を "acceptEdits" または "bypassPermissions" に
```

### WSL でファイルパスエラー

**Windows パスの場合**:
```
C:\Users\Name\project
↓
/mnt/c/Users/Name/project
```

## プラグイン・フック関連

### フックが実行されない

**確認事項**:
1. JSON 文法が正しいか?
2. マッチャーパターンが適切か?
3. スクリプトに実行権限があるか?

**解決法**:
```bash
# デバッグモードで確認
claude --debug

# スクリプト権限を付与
chmod +x script.sh
```

### プラグインがインストールできない

**解決法**:
```bash
# マーケットプレイスが正しく追加されているか確認
/plugin
# → "Manage marketplaces"

# 再度インストール
/plugin install plugin-name@marketplace
```

## その他

### Claude が混乱している

**解決法**:
```bash
# コンテキストをリセット
/clear

# 新しいセッション
exit
claude

# より具体的な指示を出す
```

### 期待と違う結果

**改善方法**:
1. より具体的な指示
2. 例を示す
3. 段階的に確認
4. `/rewind` で巻き戻し

### ログを確認したい

```bash
# 詳細ログモード
claude --verbose

# デバッグモード
claude --debug
```

## サポート

### 公式サポート
- ドキュメント: https://docs.anthropic.com/en/docs/claude-code
- バグ報告: `/bug` コマンド（Anthropic に直接送信）
- GitHub Issues: https://github.com/anthropics/claude-code/issues

### インストール状況の確認
```bash
# 環境チェック
/doctor
```

### よくある質問の確認
公式ドキュメントの FAQ セクションを参照
