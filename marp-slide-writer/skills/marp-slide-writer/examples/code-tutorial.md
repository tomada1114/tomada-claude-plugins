---
marp: true
theme: https://tomada1114.github.io/marp-theme/youtube-theme.css
paginate: false
title: Pythonデコレータ入門
---

<!-- _class: title -->
<!-- _paginate: false -->

# Pythonデコレータ入門

## 関数を拡張する魔法のテクニック

---

<!-- _class: section -->

## デコレータとは？

---

# デコレータの基本

**関数を包んで機能を追加**する仕組み。

```python
@my_decorator
def hello():
    print("Hello!")
```

`@`記号で関数の前に付けるだけ。

---

# なぜデコレータを使う？

- ログ出力の共通化
- 認証チェックの共通化
- 実行時間の計測
- キャッシュの実装

**コードの重複を減らせる！**

---

<!-- _class: section -->

## 実装してみよう

---

# 最もシンプルなデコレータ

```python
def my_decorator(func):
    def wrapper():
        print("Before")
        func()
        print("After")
    return wrapper
```

---

# 使ってみる

```python
@my_decorator
def say_hello():
    print("Hello!")

say_hello()
# Before
# Hello!
# After
```

---

<!-- _class: no-header -->

```python
# 引数を受け取るデコレータ
def log_calls(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Returned {result}")
        return result
    return wrapper

@log_calls
def add(a, b):
    return a + b
```

---

# 実行時間を計測する

```python
import time

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{elapsed:.2f}秒")
        return result
    return wrapper
```

---

<!-- _class: section -->

## 実践的なパターン

---

<!-- _class: small-text -->

# よく使うデコレータパターン

- **@functools.wraps**: メタデータを保持
- **@staticmethod**: インスタンス不要のメソッド
- **@classmethod**: クラスメソッド
- **@property**: getterの定義
- **@lru_cache**: 結果のキャッシュ
- **@dataclass**: データクラスの定義

---

# @functools.wrapsの重要性

```python
from functools import wraps

def my_decorator(func):
    @wraps(func)  # これを忘れずに！
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

元の関数名やdocstringを保持。

---

<!-- _class: section -->

## まとめ

---

# 今日学んだこと

- デコレータは**関数を包む関数**
- `@`記号で簡単に適用
- `@wraps`でメタデータを保持
- 共通処理の抽出に便利

---

<!-- _class: align-center text-center -->

# ご視聴ありがとうございました

サンプルコードはGitHubで公開中
