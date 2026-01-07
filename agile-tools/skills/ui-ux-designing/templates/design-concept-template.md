# デザインコンセプト テンプレート

以下のテンプレートを使用してデザインコンセプトドキュメントを作成する。
`[PLACEHOLDER]` を実際の値に置き換えて使用。

---

```markdown
# デザインコンセプト

## 概要

[PRODUCT_NAME]は、[TARGET_USER]向けの[PRODUCT_TYPE]。[DESIGN_DIRECTION]を基調とする。

---

## デザイン原則

### 1. [PRINCIPLE_1_NAME] ([PRINCIPLE_1_ENGLISH])

[PRINCIPLE_1_DESCRIPTION]

- [DETAIL_1]
- [DETAIL_2]
- [DETAIL_3]

### 2. [PRINCIPLE_2_NAME] ([PRINCIPLE_2_ENGLISH])

[PRINCIPLE_2_DESCRIPTION]

- [DETAIL_1]
- [DETAIL_2]
- [DETAIL_3]

### 3. [PRINCIPLE_3_NAME] ([PRINCIPLE_3_ENGLISH])

[PRINCIPLE_3_DESCRIPTION]

- [DETAIL_1]
- [DETAIL_2]
- [DETAIL_3]

---

## カラーシステム

### ベース: [LIGHT_OR_DARK]モード

| 用途 | カラー | 説明 |
|------|--------|------|
| Background Primary | `[HEX_CODE]` | メイン背景 |
| Background Secondary | `[HEX_CODE]` | カード・セクション背景 |
| Background Tertiary | `[HEX_CODE]` | ホバー・アクティブ状態 |
| Surface | `[HEX_CODE]` | 入力フィールド・ボタン背景 |

### テキスト

| 用途 | カラー | 説明 |
|------|--------|------|
| Text Primary | `[HEX_CODE]` | 見出し・重要テキスト |
| Text Secondary | `[HEX_CODE]` | 本文・説明テキスト |
| Text Muted | `[HEX_CODE]` | プレースホルダー・補足 |

### アクセント: [ACCENT_COLOR_NAME]系

| 用途 | カラー | 説明 |
|------|--------|------|
| Accent Primary | `[HEX_CODE]` | プライマリアクション |
| Accent Hover | `[HEX_CODE]` | ホバー状態 |
| Accent Muted | `[HEX_CODE]` | 背景アクセント |
| Accent Glow | `[RGBA_CODE]` | グロー効果 |

### セマンティック

| 用途 | カラー | 説明 |
|------|--------|------|
| Success | `[HEX_CODE]` | 高スコア・成功 |
| Warning | `[HEX_CODE]` | 中スコア・注意 |
| Error | `[HEX_CODE]` | 低スコア・エラー |

---

## タイポグラフィ

### フォント

```css
font-family: '[FONT_FAMILY]', sans-serif;
```

### スケール

| 名称 | サイズ | 用途 |
|------|--------|------|
| Display | 48px / 3rem | [USAGE] |
| Heading 1 | 32px / 2rem | [USAGE] |
| Heading 2 | 24px / 1.5rem | [USAGE] |
| Body | 16px / 1rem | [USAGE] |
| Small | 14px / 0.875rem | [USAGE] |
| Caption | 12px / 0.75rem | [USAGE] |

### ウェイト

| 名称 | Weight | 用途 |
|------|--------|------|
| Bold | 700 | 見出し・強調 |
| Semibold | 600 | ボタン・ラベル |
| Regular | 400 | 本文 |

---

## スペーシング

### 基準値: 4px

```
4px  (0.25rem) - 極小間隔
8px  (0.5rem)  - 小間隔
12px (0.75rem) - コンパクト間隔
16px (1rem)    - 標準間隔
24px (1.5rem)  - セクション間隔
32px (2rem)    - 大間隔
48px (3rem)    - 画面間隔
```

### レイアウト

- コンテンツ最大幅: [MAX_WIDTH]px
- 画面パディング: [MOBILE_PADDING]px（モバイル）/ [DESKTOP_PADDING]px（デスクトップ）
- カード内パディング: [CARD_PADDING]px

---

## コンポーネント

### ボタン

```
Primary Button:
- 背景: Accent Primary
- テキスト: White
- 角丸: [BORDER_RADIUS]px
- 高さ: [HEIGHT]px

Secondary Button:
- 背景: Surface
- ボーダー: 1px solid [BORDER_COLOR]
- テキスト: Text Primary
- 角丸: [BORDER_RADIUS]px
```

### 入力フィールド

```
- 背景: Surface
- ボーダー: 1px solid [BORDER_COLOR]
- フォーカス: ボーダー Accent Primary + グロー
- 角丸: [BORDER_RADIUS]px
- 高さ: [HEIGHT]px
```

### カード

```
- 背景: Background Secondary
- ボーダー: 1px solid [BORDER_COLOR]
- 角丸: [BORDER_RADIUS]px
- シャドウ: [SHADOW_OR_NONE]
```

---

## 画面別UI仕様

### 1. [SCREEN_NAME_1]

```
構成:
- [ELEMENT_1]
- [ELEMENT_2]
- [ELEMENT_3]

特徴:
- [FEATURE_1]
- [FEATURE_2]
```

### 2. [SCREEN_NAME_2]

```
構成:
- [ELEMENT_1]
- [ELEMENT_2]
- [ELEMENT_3]

特徴:
- [FEATURE_1]
- [FEATURE_2]
```

### 3. [SCREEN_NAME_3]

```
構成:
- [ELEMENT_1]
- [ELEMENT_2]
- [ELEMENT_3]

特徴:
- [FEATURE_1]
- [FEATURE_2]
```

---

## アニメーション

### 使用する場面

1. **[ANIMATION_1]**: [DESCRIPTION]
2. **[ANIMATION_2]**: [DESCRIPTION]
3. **[ANIMATION_3]**: [DESCRIPTION]

### 使用しない場面

- [AVOID_1]
- [AVOID_2]
- [AVOID_3]

### パフォーマンス指針

```
- transform と opacity のみ使用
- will-change は必要箇所のみ
- 60fps を維持
```

---

## レスポンシブ設計

### ブレイクポイント

```
Mobile:  < 640px  ([PRIORITY])
Tablet:  640px - 1024px
Desktop: > 1024px
```

### [MOBILE_OR_DESKTOP]ファースト原則

- [PRINCIPLE_1]
- [PRINCIPLE_2]
- [PRINCIPLE_3]

---

## アクセシビリティ

### 必須対応

- カラーコントラスト比 4.5:1 以上
- タッチターゲット 44px × 44px 以上
- フォーカス状態の視覚的表示
- スクリーンリーダー対応（aria-label）

### [APP_TYPE]特有の配慮

- [CONSIDERATION_1]
- [CONSIDERATION_2]
- [CONSIDERATION_3]

---

## 参考にしたアプリ・リソース

### UXパターン

- [App 1](URL) - [WHAT_WE_LEARNED]
- [App 2](URL) - [WHAT_WE_LEARNED]
- [App 3](URL) - [WHAT_WE_LEARNED]

### デザイントレンド

- [Resource 1](URL)
- [Resource 2](URL)

### 意識的に避けた要素

- [AVOIDED_1] - [REASON]
- [AVOIDED_2] - [REASON]
- [AVOIDED_3] - [REASON]

---

## 変更履歴

| 日付 | 内容 |
|------|------|
| [DATE] | [CHANGE_DESCRIPTION] |
```

---

## テンプレート使用のヒント

### 1. デザイン原則

3つの原則を設定する。例:

- **会話への没入** - 視覚的ノイズを排除
- **情報の段階的開示** - 必要な時に必要な情報
- **プロフェッショナルな信頼感** - ゲーミフィケーションなし

### 2. カラーシステム

`references/color-systems.md` を参照して選択。

### 3. 画面別UI仕様

プロダクトの主要画面を列挙する。例:

- ログイン画面
- ホーム画面
- メイン機能画面
- フィードバック画面
- 設定画面

### 4. アニメーション

最小限の場合の例:
- 波形と画面遷移のみ
- ボタンホバーの過度な動きは使用しない
- ローディングスピナーは波形で代用

### 5. 参考アプリ

調査で得た知見を記載する。避けた要素も重要。
