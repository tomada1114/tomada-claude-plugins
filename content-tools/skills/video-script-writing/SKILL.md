---
name: video-script-writing
description: "YouTube台本作成スキル。AI駆動開発・プログラミング系テック動画に特化。Markdown記事やメモから台本を生成。Use PROACTIVELY when creating YouTube scripts, converting articles to scripts, writing video scripts, or when user mentions 台本, スクリプト, YouTube動画, 動画制作, 記事を台本に. Examples: <example>Context: User provides article user: 'この記事を台本にして' assistant: 'I will use video-script-writing skill' <commentary>Triggered by script conversion request</commentary></example>"
---

# Video Script Writing

AI駆動開発・プログラミング系テック動画に特化した台本作成スキル。
Markdown記事、メモ、アウトラインから視聴者を惹きつける台本を生成する。

---

## When to Use This Skill

- Markdown記事を動画台本に変換するとき
- YouTube動画の台本を新規作成するとき
- 既存の台本を改善するとき
- 動画の構成を設計するとき

---

## Input Requirements

以下のいずれかを入力として受け取る:

1. **Markdown記事** - Zenn/Qiita/ブログ記事など
2. **メモ・アウトライン** - 箇条書きのアイデア
3. **トピック説明** - 話したい内容の概要

---

## Output Format

```markdown
# [動画タイトル]

## 台本情報
- 想定尺: XX分
- 文字数: X,XXX字
- 対象: [初心者/中級者/上級者]

---

## 冒頭（0:00-X:XX）

[問題提起]
[価値提示]
[目次予告]

---

## 本編

### セクション1: [トピック]（X:XX-X:XX）

[用語説明]
[具体例]
[メリット/注意点]

### セクション2: ...

---

## 締め（X:XX-X:XX）

[要約]
[実践誘導]
[CTA]
```

---

## Workflow

```
入力（Markdown/メモ）
    ↓
[Step 1] 入力分析
    - トピック特定
    - 対象レベル判断
    - 動画尺推定
    ↓
[Step 2] 構成設計
    - 3部構成（冒頭-本編-締め）
    - セクション分割
    - 時間配分決定
    ↓
[Step 3] 台本生成
    - パターン辞書を参照
    - 語尾・強調語を配置
    - CTA挿入
    ↓
[Step 4] 評価・改善
    - 7軸で評価（90点以上まで）
    - NGワードチェック
    - 改善ループ
```

---

## Reference Documents

### 評価基準（必読）
- [evaluation-criteria.md](references/evaluation-criteria.md) - 7軸100点満点の評価基準
- [ng-expressions.md](references/ng-expressions.md) - 禁止表現リスト

### パターン辞書
- [ai-saborou-patterns.md](references/ai-saborou-patterns.md) - AI Saborou式パターン辞書
- [speech-patterns.md](references/speech-patterns.md) - 話し方パターンガイド

### テンプレート
- [script-structure.md](templates/script-structure.md) - 台本構造テンプレート
- [section-templates.md](templates/section-templates.md) - 動画タイプ別テンプレート
- [duration-guide.md](templates/duration-guide.md) - 動画尺別ガイド

### 具体例
- [good-example-feature.md](examples/good-example-feature.md) - 良い例：新機能紹介
- [good-example-tool.md](examples/good-example-tool.md) - 良い例：ツール紹介
- [bad-example.md](examples/bad-example.md) - 悪い例：アンチパターン集

---

## AI Assistant Instructions

### 1. 入力の分析

```
1. トピックを特定（何についての動画か）
2. 対象レベルを判断（初心者/中級者/上級者）
3. 動画タイプを分類（新機能紹介/ツール紹介/概念解説/チュートリアル/比較）
4. 動画尺を推定（内容の深さに応じて5-20分）
```

### 2. 構成設計

```
1. templates/script-structure.md を参照して3部構成を設計
2. templates/section-templates.md から適切なテンプレートを選択
3. templates/duration-guide.md で時間配分を決定
```

### 3. 台本生成

```
1. 冒頭は挨拶なし、いきなり問題提起から開始
2. references/ai-saborou-patterns.md の語尾・強調語を使用
3. references/speech-patterns.md の距離感調整を適用
4. 本編は用語→例→メリットの3段階で説明
5. 必ずセキュリティ・リスクへの言及を含める
6. 締めにCTA（チャンネル登録・高評価）を含める
```

### 4. 評価・改善（自動化）

**CRITICAL**: 台本生成後、`validate_script.py` を実行して自動評価を行う。

```bash
# 評価スクリプトの実行（スキルディレクトリからの相対パス）
python scripts/validate_script.py <script_path>
```

**Note**: スクリプトは本スキルの `scripts/` ディレクトリに配置されています。

**評価フロー:**
```
1. validate_script.py を実行
2. 結果を確認:
   - 合格（90点以上 + 全軸閾値以上）→ 完了
   - 不合格 → 改善提案を確認して修正
3. 最大3回まで改善ループ
```

**スクリプトが自動チェックする項目:**
- NGワード検出（1件でも0点）
- 冒頭-本編-締めの3部構成
- 語尾パターンの多様性（3種類以上）
- 親近感表現の数（2個以上）
- リスク言及の有無
- 短文率（40字以内が80%以上）
- CTA（チャンネル登録・高評価）

**手動確認が必要な項目:**
- 用語の正確性（Technical Accuracy の一部）
- 音読リズム（Readability の一部）

---

## Always

- いきなり本題から始める（挨拶なし）
- 1文40字以内を意識する
- 語尾を多様にする（ですね/になります/でしょう など）
- 「私も〜」「皆さんも〜」で親近感を出す
- 注意点・リスクへの言及を含める
- 締めにCTAを含める

---

## Never

- 「ヤバい」「神」「最強」などの誇大表現を使う
- 「絶対」「必ず」などの過度な断定をする
- 「簡単です」「誰でもできます」などの安易な約束をする
- 挨拶や天気の話から始める
- 長い文（60字以上）を書く
- リスクへの言及を省略する

---

## Evaluation Criteria Summary

| 軸 | 配点 | 閾値 |
|----|------|------|
| Structure | 20pt | 16pt |
| Speech Pattern | 20pt | 16pt |
| Engagement | 15pt | 12pt |
| Technical Accuracy | 15pt | 12pt |
| Readability | 15pt | 12pt |
| NG Word | 10pt | 10pt |
| CTA | 5pt | 4pt |

**合格基準**: 総合90点以上 + 全軸が閾値以上

