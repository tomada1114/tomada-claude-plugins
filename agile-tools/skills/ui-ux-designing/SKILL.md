---
name: ui-ux-designing
description: Design UI/UX concepts for apps and web services through systematic research and questioning. Use PROACTIVELY when designing app interfaces, determining visual direction, creating design systems, choosing color schemes, or establishing UX patterns. Examples: <example>Context: User wants to design an app user: 'UI/UXのデザインコンセプトを決めたい' assistant: 'I will use ui-ux-designing skill' <commentary>Triggered by design concept request</commentary></example> <example>Context: User building new feature user: 'この機能の見た目どうしよう' assistant: 'I will use ui-ux-designing skill' <commentary>Triggered by visual design question</commentary></example>
---

# UI/UX Designing

アプリ/Webサービスのデザインコンセプトを体系的に決定するスキル。人気アプリのUX調査、段階的な質問による意思決定、デザインシステムドキュメント生成を行う。

## When to Use This Skill

Use PROACTIVELY when:
- 新規アプリ/機能のデザインコンセプトを決定する
- UI/UXの方向性（トーン、カラー、レイアウト）を決める
- 競合/人気アプリのUXを調査・分析する
- デザインシステムドキュメントを作成する
- User mentions: UI, UX, デザイン, 見た目, カラー, レイアウト, トーン, デザインコンセプト

## Workflow Overview

```
Phase 1: 要件確認
    ↓
Phase 2: 競合/人気アプリのUX調査 (WebSearch)
    ↓
Phase 3: デザイン方向性の決定 (AskUserQuestion)
    ↓
Phase 4: 詳細要素の決定 (AskUserQuestion)
    ↓
Phase 5: デザインコンセプトドキュメント生成
```

## Phase 1: 要件確認

1. プロダクトの概要を理解
2. ターゲットユーザーを特定
3. 既存のデザイン資産を確認
4. 技術的制約（フレームワーク等）を把握

## Phase 2: 競合/人気アプリのUX調査

WebSearchを使用して関連アプリのUXを調査する。

**調査クエリ例:**
```
"[App Name] UI UX design review 2025"
"best [app type] app UX design patterns"
"[competitor] interface design mobile app"
```

**調査観点:**
- 強み: 何が優れているか
- 弱み: 何が問題か
- 避けるべき点: ユーザーから批判されているパターン

**詳細**: `references/research-methods.md` を参照

## Phase 3: デザイン方向性の決定

AskUserQuestionを使用して、大きな方向性を決定する。

### 質問カテゴリ

1. **全体トーン**
   - プロフェッショナル / フレンドリー / モダン・クリーン

2. **カラースキーム**
   - ダークモード基調 / ライトモード基調 / システム連動

3. **アクセントカラー**
   - ブルー系（信頼感）/ グリーン系（成長）/ パープル系（創造性）

4. **会話/コンテンツUI**（該当する場合）
   - ミニマル / チャットバブル / ハイブリッド

**詳細**: `references/question-patterns.md` を参照

## Phase 4: 詳細要素の決定

方向性が決まったら、詳細を詰める。

### 質問カテゴリ

1. **スコア/フィードバック表示**
   - 円形ゲージ / バーチャート / 数値のみ

2. **導入UI**
   - シンプル / ブリーフィング / ウォームアップ

3. **アニメーション**
   - 最小限 / 適度に使用 / 積極的に使用

4. **デバイス優先度**
   - モバイルファースト / デスクトップファースト / 同等

**詳細**: `references/question-patterns.md` を参照

## Phase 5: デザインコンセプトドキュメント生成

決定事項をドキュメントにまとめる。

**テンプレート**: `templates/design-concept-template.md` を使用

### ドキュメント構成

1. **概要** - プロダクトとデザインの方向性
2. **デザイン原則** - 3つの核となる原則
3. **カラーシステム** - ベース、テキスト、アクセント、セマンティック
4. **タイポグラフィ** - フォント、スケール、ウェイト
5. **スペーシング** - 基準値、レイアウト
6. **コンポーネント** - ボタン、入力、カード等
7. **画面別UI仕様** - 各画面の詳細
8. **アニメーション** - 使用場面、パフォーマンス指針
9. **レスポンシブ設計** - ブレイクポイント、原則
10. **アクセシビリティ** - 必須対応事項

## 質問設計の原則

### 1. 具体的な選択肢を提示

```
❌ 悪い: "色はどうしますか？"
✅ 良い: "カラースキームはどれが良いですか？"
         - ダークモード基調（集中力向上、目に優しい）
         - ライトモード基調（明るく開放的）
         - システム連動（OS設定に追従）
```

### 2. トレードオフを説明

各選択肢の意味や影響を簡潔に説明する。

### 3. 推奨を明示

専門家として推奨する選択肢がある場合、`（推奨）`を付ける。

### 4. 質問をバッチ化

関連する質問を3-4個まとめて聞く。

## アプリタイプ別の注意点

**詳細**: `references/app-type-ux-patterns.md` を参照

### 会話/音声アプリ

- 会話中UIはミニマルに（波形アニメーション等）
- フィードバックはセッション後にまとめて
- 避けるべき: 毎回質問で終わるパターン（尋問感）

### Eコマース

- 商品画像を大きく、情報は段階的開示
- CTAボタンは明確に
- 避けるべき: 情報過多のリスト表示

### ダッシュボード

- 重要指標を上部に配置
- 詳細はドリルダウン形式
- 避けるべき: 一画面に全情報を詰め込む

## カラーシステムガイド

**詳細**: `references/color-systems.md` を参照

### プロフェッショナル向け

- ダーク背景 + ブルー系アクセント
- 落ち着いた色調、装飾控えめ

### フレンドリー向け

- ライト背景 + グリーン/オレンジ系
- 明るい色調、イラストやアイコン多め

## Best Practices

### 調査

- 3つ以上の競合/類似アプリを調査
- 強み・弱み・避けるべき点を整理
- 調査結果をユーザーに共有

### 質問

- 1ラウンド3-4問まで
- 必ず具体的選択肢を提示
- 専門家として推奨を明示

### ドキュメント

- テンプレートに沿って作成
- カラーコードは具体的に記載
- 画面別に詳細仕様を記述

## AI Assistant Instructions

When this skill is activated:

### DO:

1. **まず調査**: WebSearchで競合/人気アプリのUXを調査
2. **調査結果を共有**: 強み・弱み・避けるべき点をまとめて提示
3. **AskUserQuestion使用**: 段階的に方向性を決定
4. **推奨を明示**: 専門家として「（推奨）」を付けて提案
5. **トレードオフ説明**: 各選択肢の意味を簡潔に説明
6. **テンプレート使用**: `templates/design-concept-template.md` を参照
7. **リファレンス参照**: 詳細は `references/` のファイルを読む

### DON'T:

1. 調査なしでデザインを決定
2. 曖昧な質問（「どうしますか？」）
3. 選択肢なしの質問
4. 1度に5問以上の質問
5. トレードオフの説明なし
6. ドキュメントなしで終了

### When Uncertain:

- 必ずユーザーに確認
- 2-4個の選択肢を提示
- 各選択肢の影響を説明

## References

- [question-patterns.md](references/question-patterns.md) - 質問パターン集
- [app-type-ux-patterns.md](references/app-type-ux-patterns.md) - アプリタイプ別UX
- [color-systems.md](references/color-systems.md) - カラーシステムガイド
- [research-methods.md](references/research-methods.md) - 調査手法

## Templates

- [design-concept-template.md](templates/design-concept-template.md) - デザインコンセプトテンプレート
