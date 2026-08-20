---
name: ui-ux-designing
description: "Design UI/UX concepts for apps and web services through systematic research and questioning (UI/UXデザイン、デザインコンセプト決定、配色・カラースキーム、デザインシステム設計). Use PROACTIVELY when designing app interfaces, determining visual direction, creating design systems, choosing color schemes, or establishing UX patterns. Examples: <example>Context: User wants to design an app user: 'I want to settle the UI/UX design concept' assistant: 'I will use ui-ux-designing skill' <commentary>Triggered by design concept request</commentary></example> <example>Context: User building new feature user: 'How should this feature look?' assistant: 'I will use ui-ux-designing skill' <commentary>Triggered by visual design question</commentary></example>"
---

# UI/UX Designing

アプリ/Webサービスのデザインコンセプトを体系的に決定するスキル。人気アプリのUX調査、段階的な質問による意思決定、デザインシステムドキュメント生成を行う。

## Workflow

```
Phase 1: 要件確認
    ↓
Phase 2: 競合/人気アプリのUX調査 (WebSearch / 同等の調査手段)
    ↓
Phase 3: デザイン方向性の決定 (AskUserQuestion / 対話で確認)
    ↓
Phase 4: 詳細要素の決定 (AskUserQuestion / 対話で確認)
    ↓
Phase 5: デザインコンセプトドキュメント生成
```

## Phase 1: 要件確認

プロダクト概要・ターゲットユーザー・既存デザイン資産・技術的制約（フレームワーク等）を把握する。

## Phase 2: 競合/人気アプリのUX調査

> **Claude Code**: `WebSearch` で関連アプリのUXを調査する（3つ以上）。
> **Codex / WebSearch が無い環境**: 同等の web 検索ツールがあれば使用する。無ければユーザーに参考アプリ名・URL・スクリーンショットの提供を依頼して調査する（調査観点・3アプリ以上の原則は維持）。

**調査クエリ例:**
```
"[App Name] UI UX design review 2025"
"best [app type] app UX design patterns"
"[competitor] interface design mobile app"
```

**調査観点:** 強み（何が優れているか）/ 弱み（何が問題か）/ 避けるべき点（ユーザーから批判されているパターン）。調査結果はユーザーに共有する。

**詳細**: `references/research-methods.md` を参照

## Phase 3: デザイン方向性の決定

> **Claude Code**: `AskUserQuestion` で選択肢を提示し、大きな方向性を決める（このバッチ確認の原則はPhase 4にも適用）。
> **Codex / AskUserQuestion が無い環境**: 同じ選択肢を通常の文章でユーザーに提示し、回答を待つ（バッチ確認の原則はPhase 4にも適用）。

### 質問カテゴリ

1. **全体トーン** — プロフェッショナル / フレンドリー / モダン・クリーン
2. **カラースキーム** — ダークモード基調 / ライトモード基調 / システム連動
3. **アクセントカラー** — ブルー系（信頼感）/ グリーン系（成長）/ パープル系（創造性）
4. **会話/コンテンツUI**（該当する場合）— ミニマル / チャットバブル / ハイブリッド

**詳細**: `references/question-patterns.md` を参照

## Phase 4: 詳細要素の決定

> **Claude Code**: 方向性が決まったら、`AskUserQuestion` で詳細を詰める。
> **Codex / AskUserQuestion が無い環境**: 方向性が決まったら、同じ要領で通常の文章でユーザーに詳細を確認する。

### 質問カテゴリ

1. **スコア/フィードバック表示** — 円形ゲージ / バーチャート / 数値のみ
2. **導入UI** — シンプル / ブリーフィング / ウォームアップ
3. **アニメーション** — 最小限 / 適度に使用 / 積極的に使用
4. **デバイス優先度** — モバイルファースト / デスクトップファースト / 同等

**詳細**: `references/question-patterns.md` を参照

## Phase 5: デザインコンセプトドキュメント生成

決定事項を `templates/design-concept-template.md` に沿ってまとめる。

### ドキュメント構成

1. 概要 — プロダクトとデザインの方向性
2. デザイン原則 — 3つの核となる原則
3. カラーシステム — ベース、テキスト、アクセント、セマンティック
4. タイポグラフィ — フォント、スケール、ウェイト
5. スペーシング — 基準値、レイアウト
6. コンポーネント — ボタン、入力、カード等
7. 画面別UI仕様 — 各画面の詳細
8. アニメーション — 使用場面、パフォーマンス指針
9. レスポンシブ設計 — ブレイクポイント、原則
10. アクセシビリティ — 必須対応事項

## 質問設計の原則

- **具体的な選択肢を2〜4個提示する**（❌「色はどうしますか？」→ ✅「カラースキームはどれが良いですか？ダークモード基調（集中力向上、目に優しい）/ ライトモード基調（明るく開放的）/ システム連動（OS設定に追従）」）
- 各選択肢の**トレードオフを簡潔に説明**する
- 専門家として推奨する選択肢には**`（推奨）`を明示**する
- 関連する質問は**3-4個ずつバッチ化**して聞く（1ラウンド5問以上にしない）
- ドキュメントはテンプレートに沿って作成し、カラーコードは具体的に、画面別に詳細仕様を記述する

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

- **プロフェッショナル向け**: ダーク背景 + ブルー系アクセント、落ち着いた色調、装飾控えめ
- **フレンドリー向け**: ライト背景 + グリーン/オレンジ系、明るい色調、イラストやアイコン多め

## References

- [question-patterns.md](references/question-patterns.md) - 質問パターン集
- [app-type-ux-patterns.md](references/app-type-ux-patterns.md) - アプリタイプ別UX
- [color-systems.md](references/color-systems.md) - カラーシステムガイド
- [research-methods.md](references/research-methods.md) - 調査手法

## Templates

- [design-concept-template.md](templates/design-concept-template.md) - デザインコンセプトテンプレート

## Codex での制約（best-effort 劣化）

- `AskUserQuestion`（Phase 1・3・4 の各確認）→ Codex では通常対話で同じ選択肢を提示して確認する。「質問設計の原則」（選択肢2〜4個・トレードオフ説明・`（推奨）`明示・3-4個ずつバッチ化）はそのまま適用する。
- `WebSearch`（Phase 2）→ Codex では同等の web 検索ツールがあれば使用し、無ければユーザー提供の参考情報（アプリ名・URL・スクリーンショット）で調査する（調査観点・3アプリ以上の原則は維持）。

詳細は `references/codex-notes.md` を参照。
