---
marp: true
theme: https://tomada1114.github.io/marp-theme/youtube-theme.css
paginate: false
title: Claude Code完全入門
---

<!-- _class: title -->
<!-- _paginate: false -->

# Claude Code完全入門

## AI駆動開発の新しいスタンダード

---

<!-- _class: section -->

## Claude Codeとは？

---

# Claude Codeの特徴

- **ターミナルで動作**するAIアシスタント
- コードの読み書き・実行が可能
- プロジェクト全体を理解して作業
- 自律的にタスクを完了

---

# 従来のAIツールとの違い

| 項目 | 従来ツール | Claude Code |
|------|-----------|-------------|
| 操作 | コピペ | 直接編集 |
| 範囲 | 1ファイル | プロジェクト全体 |
| 実行 | 手動 | 自動 |

---

<!-- _class: section -->

## セットアップ

---

# インストール

```bash
# npmでインストール
npm install -g @anthropic-ai/claude-code

# 起動
claude
```

これだけで使い始められます。

---

# 初回設定

```bash
# APIキーを設定（初回のみ）
claude config set api_key YOUR_KEY

# プロジェクトで起動
cd your-project
claude
```

---

<!-- _class: section -->

## 基本的な使い方

---

# タスクの依頼方法

- 自然言語で指示するだけ
- 具体的に伝えるほど精度が上がる
- ファイルパスを指定すると確実

```
> src/utils.tsにログ関数を追加して
```

---

# 便利なスラッシュコマンド

- `/help` - ヘルプを表示
- `/clear` - 会話をクリア
- `/compact` - コンテキストを圧縮
- `/cost` - 利用コストを確認

---

<!-- _class: section -->

## まとめ

---

# 今日のポイント

- Claude Codeは**ターミナルで動くAI**
- npmで簡単インストール
- 自然言語で指示するだけ

---

<!-- _class: align-center text-center -->

# ご視聴ありがとうございました

チャンネル登録・高評価お願いします
