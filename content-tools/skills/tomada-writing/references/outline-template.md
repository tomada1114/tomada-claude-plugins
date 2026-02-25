# 構成案（アウトライン）テンプレート

**Version**: 1.0.0
**Purpose**: outline-generator/validatorが参照する構成案の標準形式

---

## 構成案の目的

執筆前に7軸評価基準を意識した計画を立て、初稿の品質を向上させる。

---

## 標準フォーマット

```yaml
type: outline
version: 1
title: "記事タイトル"
template: "tutorial | review | comparison | til | impression"

# 冒頭構成（opening-evaluator: 10点満点）
opening:
  greeting: "こんにちは、とまだです。"
  conclusion_first: "今回伝えたいことの要点は〇〇です"
  value_proposition: "この記事で得られる価値"
  summary_points:
    - "要点1"
    - "要点2"
    - "要点3"

# セクション構成（structure-evaluator: 15点満点）
sections:
  - heading: "## 見出し"
    purpose: "セクションの目的"
    key_points: ["ポイント1", "ポイント2"]
    intro_sentence: "見出し直後の説明文（必須）"
    estimated_length: "300-500字"
    # 文体スタイル要素（saborou-style-evaluator: 15点満点）
    saborou_elements:
      - "両面提示"
      - "疑問先回り"
    # 接続詞計画（conjunction-evaluator: 20点満点）
    conjunctions: ["そのため", "また", "ただ"]
    # 共感計画（empathy-evaluator: 15点満点）
    empathy_points: ["〜ですよね"]
    # 導入フレーズ計画（intro-phrase-evaluator: 10点満点）
    intro_phrases: ["簡単に言うと", "具体的には"]

# 締め構成
closing:
  summary: "まとめの内容"
  cta: "行動促進"
  promotion: "宣伝セクション（記事タイプによる）"

# 事前チェック集計
pre_check:
  total_conjunctions: N  # 目標: 20-35%の使用率になる量
  total_empathy_points: N  # 目標: 3箇所以上
  total_brackets: N  # 目標: 2-4個
  total_intro_phrases: N  # 目標: 5-10箇所
  two_sided_locations: ["セクション名"]  # 目標: 1箇所以上
  question_anticipation_locations: ["セクション名"]  # 目標: 1箇所以上
```

---

## テンプレート別構成ガイド

### 体系的チュートリアル型（重め、3000-5000字、目標95点）

```yaml
sections:
  - heading: "## 〇〇とは"
    purpose: "概念説明"
    saborou_elements: ["疑問先回り"]
    intro_phrases: ["簡単に言うと"]
  - heading: "## 準備・環境構築"
    purpose: "セットアップ"
    saborou_elements: ["括弧補足"]
    intro_phrases: ["具体的には"]
  - heading: "## 基本的な使い方"
    purpose: "基礎操作"
    saborou_elements: ["両面提示"]
    intro_phrases: ["例えば"]
  - heading: "## 実践：〇〇を作ってみる"
    purpose: "応用"
    saborou_elements: ["控えめ断定"]
    intro_phrases: ["つまり"]
  - heading: "## よくあるエラーと対処法"
    purpose: "補足"
    saborou_elements: []
    intro_phrases: []
  - heading: "## まとめ"
    purpose: "総括"
    saborou_elements: []
    intro_phrases: ["要するに"]
```

### 検証レポート型（重め、2000-4000字、目標95点）

```yaml
sections:
  - heading: "## 検証の背景"
    purpose: "動機・問題提起"
    saborou_elements: ["疑問先回り"]
    intro_phrases: ["簡単に言うと"]
  - heading: "## 検証環境・条件"
    purpose: "前提説明"
    saborou_elements: []
    intro_phrases: ["具体的には"]
  - heading: "## 検証結果"
    purpose: "データ・結果"
    saborou_elements: ["両面提示"]
    intro_phrases: ["例えば"]
  - heading: "## 考察"
    purpose: "分析・解釈"
    saborou_elements: ["控えめ断定", "括弧補足"]
    intro_phrases: ["つまり"]
  - heading: "## まとめ"
    purpose: "結論"
    saborou_elements: []
    intro_phrases: ["要するに"]
```

### 比較分析型（中程度、1500-3000字、目標95点）

```yaml
sections:
  - heading: "## 比較の前提"
    purpose: "比較対象・観点説明"
    saborou_elements: ["疑問先回り"]
    intro_phrases: ["簡単に言うと"]
  - heading: "## Aの特徴"
    purpose: "一方の説明"
    saborou_elements: []
    intro_phrases: ["具体的には"]
  - heading: "## Bの特徴"
    purpose: "他方の説明"
    saborou_elements: []
    intro_phrases: ["具体的には"]
  - heading: "## 比較表・まとめ"
    purpose: "総合比較"
    saborou_elements: ["両面提示"]
    intro_phrases: ["つまり"]
  - heading: "## 使い分けの指針"
    purpose: "推奨"
    saborou_elements: ["控えめ断定"]
    intro_phrases: ["例えば"]
```

### 今日の発見（TIL）型（軽め、500-1000字、目標80点）

```yaml
opening:
  # 要約セクションは省略可
  summary_points: null

sections:
  - heading: "## 発見したこと"
    purpose: "本題"
    saborou_elements: ["両面提示"]
    intro_phrases: ["具体的には"]
  - heading: "## 試してみた結果"
    purpose: "検証"
    saborou_elements: []
    intro_phrases: ["例えば"]
  - heading: "## 学び"
    purpose: "まとめ"
    saborou_elements: ["控えめ断定"]
    intro_phrases: []
```

### 使ってみた感想型（軽め、300-800字、目標80点）

```yaml
opening:
  # 要約セクションは省略可
  summary_points: null

sections:
  - heading: "## 使ってみた"
    purpose: "体験報告"
    saborou_elements: ["両面提示"]
    intro_phrases: ["具体的には"]
  - heading: "## 感想"
    purpose: "所感"
    saborou_elements: ["控えめ断定", "括弧補足"]
    intro_phrases: []
```

---

## 7軸評価基準との対応

| 評価軸 | 配点 | 構成案での計画項目 | 目標 |
|--------|------|------------------|------|
| conjunction | 20点 | `sections[].conjunctions` | 各セクション2-3個、使用率20-35% |
| ng-words | 15点 | 自動チェック | NGワード計画しない |
| structure | 15点 | `sections[].intro_sentence` | 全セクション必須 |
| saborou-style | 15点 | `sections[].saborou_elements` | 6要素のうち4以上配置 |
| empathy | 15点 | `sections[].empathy_points` | 合計3箇所以上 |
| opening | 10点 | `opening.*` | 5要素すべて |
| intro-phrase | 10点 | `sections[].intro_phrases` | 合計5-10箇所 |

---

## 予測スコアの計算基準

### 接続詞計画 (20点)

| 条件 | 予測スコア |
|------|-----------|
| 各セクションに2-3個の接続詞計画あり | 18-20 |
| 大半のセクションに計画あり | 14-17 |
| 計画が不十分 | 10-13 |
| 計画なし | 0-9 |

### NGワード (15点)

| 条件 | 予測スコア |
|------|-----------|
| 構成案にNGワード計画なし | 15 |
| NGワード的表現が1箇所 | 12 |
| 複数のNGワード計画 | 0-10 |

### 構造 (15点)

| 条件 | 予測スコア |
|------|-----------|
| 全見出しに intro_sentence 計画あり | 14-15 |
| 大半に計画あり | 11-13 |
| 計画不足 | 7-10 |
| 計画なし | 0-6 |

### 文体スタイル (15点)

| 要素 | 配点 |
|------|------|
| 結論先出し計画あり | 3 |
| 両面提示計画あり（1箇所以上） | 3 |
| 疑問先回り計画あり（1箇所以上） | 3 |
| 括弧補足計画あり（2-4個） | 2 |
| 控えめ断定計画あり | 2 |
| 余談セクション計画あり | 2 |

### 共感・トーン (15点)

| 条件 | 予測スコア |
|------|-----------|
| empathy_points 3箇所以上 | 14-15 |
| empathy_points 2箇所 | 11-13 |
| empathy_points 1箇所 | 7-10 |
| empathy_points なし | 0-6 |

### 冒頭構成 (10点)

| 要素 | 配点 |
|------|------|
| greeting あり | 2 |
| conclusion_first あり | 3 |
| value_proposition あり | 2 |
| summary_points あり（3-5個） | 3 |

### 導入フレーズ (10点)

| 条件 | 予測スコア |
|------|-----------|
| intro_phrases 5-10箇所 | 9-10 |
| intro_phrases 3-4箇所 | 7-8 |
| intro_phrases 1-2箇所 | 5-6 |
| intro_phrases なし | 0-4 |

---

## 文体スタイル6要素チェックリスト

構成案に以下の要素を計画すること:

| # | 要素 | 配置場所 | 表現例 |
|---|------|---------|--------|
| 1 | 結論先出し | 冒頭（必須） | 「今回伝えたいことの要点は〇〇です」 |
| 2 | 両面提示 | 本文1箇所以上 | 「一方で」「ただ」でデメリット・限界も正直に |
| 3 | 疑問先回り | 本文1箇所以上 | 「『〇〇では？』と思った方も〜」 |
| 4 | 括弧補足 | 本文2-4個 | （これは個人的な意見ですが〜） |
| 5 | 控えめ断定 | 意見部分 | 「〜ではないでしょうか」「〜と考えています」 |
| 6 | 余談セクション | 適宜 | 補足的な情報を「余談」として |

---

## メンテナンス

この定義の更新は **tomada-writing スキル更新時** に同期します。

**Last Updated**: 2025-12-22
