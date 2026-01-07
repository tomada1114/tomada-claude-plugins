---
description: Split long SRT subtitles (over 24 chars) with timeline adjustment
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Task
  - Grep
argument-hint: <srt_file> [--max-chars N]
---

# Split Long Subtitles

SRTファイルの長文字幕（24文字超）を検出し、自然な位置で分割してタイムラインを按分調整します。

**引数:**
- `$1`: SRTファイルパス（必須）
- `--max-chars N`: 最大文字数（デフォルト: 24）

---

## Step 1: Validate Input

1. SRTファイルパスを取得: `$1`
2. ファイルが存在することを確認
3. `.srt` 拡張子であることを確認

**エラー時:**
```
❌ SRTファイルが見つかりません: $1
処理を中止します。
```

---

## Step 2: Detect Long Subtitles

検出スクリプトを実行:

```bash
python ~/.claude/skills/fixing-srt-subtitles/scripts/detect_long_subtitles.py $1 --max-chars 24
```

結果をJSON形式で取得し、`count`が0なら完了メッセージを表示して終了。

---

## Step 3: Get Split Suggestions

長文字幕がある場合、**srt-splitter サブエージェント**を呼び出して分割提案を取得。

Taskツールで以下のプロンプトを送信:

```
以下の長文字幕を自然な位置で分割してください。

ルール:
- 助詞（の、が、を、に、で、は、と、も）が行頭に来ないようにする
- 単語を途中で切らない
- 意味のまとまりを保つ
- 1行24文字以内を厳守

分割対象:
[検出された長文字幕のリスト]

出力フォーマット:
番号X:
分割案: 「テキスト1」「テキスト2」
```

---

## Step 4: Apply Splits

サブエージェントの提案をもとに:

### 4.1 字幕ブロックを分割

各長文字幕に対して:

1. 元のタイムコードを取得（開始時間、終了時間）
2. 総時間を計算
3. 分割後の各テキストの文字数を計算
4. 文字数比でタイムコードを按分

**タイムコード按分の計算:**
```
例: 00:05:26,000 --> 00:05:30,000 (4秒)
    分割: 11文字 + 13文字 = 24文字

    1つ目: 11/24 × 4秒 = 1.833秒 → 00:05:26,000 --> 00:05:27,833
    2つ目: 13/24 × 4秒 = 2.167秒 → 00:05:27,833 --> 00:05:30,000
```

### 4.2 字幕番号を再採番

分割後、SRT全体の字幕番号を1から連番で再採番。

**再採番スクリプト:**
```python
import re

with open('output.srt', 'r', encoding='utf-8') as f:
    content = f.read()

blocks = re.split(r'\n\n+', content.strip())
result = []
new_num = 1

for block in blocks:
    lines = block.strip().split('\n')
    if len(lines) >= 2 and lines[0].isdigit():
        lines[0] = str(new_num)
        new_num += 1
    result.append('\n'.join(lines))

with open('output.srt', 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(result) + '\n')
```

---

## Step 5: Verify and Report

### 5.1 再検出

分割後に再度長文字幕を検出:

```bash
python ~/.claude/skills/fixing-srt-subtitles/scripts/detect_long_subtitles.py $1 --max-chars 24
```

### 5.2 完了レポート

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 長文字幕分割完了
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 修正ファイル:
- $1

📊 分割サマリー:
- 修正前: XX字幕中YY個が24文字超
- 修正後: ZZ字幕中0個が24文字超
- 分割数: YY → AA（+BB字幕）

🔍 分割内容:
- [具体的な分割例を列挙]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 5.3 残存チェック

24文字超の字幕が残っている場合は**エラー**として報告し、手動確認を促す。

```
❌ 24文字超の字幕が残っています:
- 番号XX: 「テキスト」(YY文字)

手動で確認・修正してください。
```

---

## Error Handling

- SRTファイルが見つからない → エラー終了
- 検出スクリプトが見つからない → エラー終了
- 分割後も24文字超が残る → エラー報告（ゼロ許容なし）

---

## Usage Examples

```bash
# 基本的な使用
/fixing-srt-subtitles:split-long-subtitles path/to/subtitle.srt

# 最大文字数を指定
/fixing-srt-subtitles:split-long-subtitles path/to/subtitle.srt --max-chars 20
```
