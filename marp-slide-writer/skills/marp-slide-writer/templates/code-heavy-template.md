---
marp: true
theme: https://tomada1114.github.io/marp-theme/youtube-theme.css
paginate: false
title: [コードチュートリアル タイトル]
---

<!-- _class: title -->
<!-- _paginate: false -->

# コードで学ぶ〇〇

## 実践的なサンプルで理解する

---

<!-- _class: section -->

## セクション1: 基本

---

# 基本的な使い方

シンプルな例から始めます。

```python
def hello():
    print("Hello, World!")

hello()
```

<!-- h1 + 説明文 + コード = 8行推奨 -->

---

# ステップバイステップ

1. まず〇〇を準備
2. 次に〇〇を実行
3. 結果を確認

```python
result = process(data)
print(result)
```

<!-- 箇条書き3行 + コード4行以内 -->

---

<!-- _class: section -->

## セクション2: 実践

---

# 実践的なコード例

```python
def process_data(items):
    results = []
    for item in items:
        if item.is_valid():
            results.append(item.transform())
    return results
```

<!-- h1 + コードのみ = 10行推奨 -->

---

<!-- _class: no-header -->

```python
# 長めのコード例（ヘッダーなし）
class DataProcessor:
    def __init__(self, config):
        self.config = config

    def process(self, data):
        validated = self.validate(data)
        transformed = self.transform(validated)
        return self.output(transformed)

    def validate(self, data):
        return [d for d in data if d.is_valid()]
```

<!-- no-header = 14行推奨、17行上限 -->

---

# Before / After

**Before:**
```python
result = []
for x in data:
    result.append(x * 2)
```

<!-- 複数コードブロックは非推奨。分割するか、1つにまとめる -->

---

# 改善後のコード

**After:**
```python
result = [x * 2 for x in data]
```

簡潔で読みやすくなりました。

---

<!-- _class: section -->

## セクション3: Tips

---

<!-- _class: small-text -->

# よくあるパターン

- **パターン1**: 説明テキスト
- **パターン2**: 説明テキスト
- **パターン3**: 説明テキスト
- **パターン4**: 説明テキスト
- **パターン5**: 説明テキスト
- **パターン6**: 説明テキスト

<!-- small-text = 8行推奨、10行上限 -->

---

# まとめ

- 基本: シンプルに始める
- 実践: 段階的に複雑化
- Tips: パターンを覚える

---

<!-- _class: align-center text-center -->

# ご視聴ありがとうございました

サンプルコードはGitHubで公開中
