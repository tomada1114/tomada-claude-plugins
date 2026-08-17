# カラーシステムガイド

デザインコンセプトに合わせたカラーシステムの選択と構築ガイド。

---

## カラーシステムの構成要素

### 1. ベースカラー（Background）

画面の基盤となる色。

```
- Primary: メイン背景
- Secondary: カード/セクション背景
- Tertiary: ホバー/アクティブ状態
- Surface: 入力フィールド/ボタン背景
```

### 2. テキストカラー

```
- Primary: 見出し/重要テキスト
- Secondary: 本文/説明テキスト
- Muted: プレースホルダー/補足
```

### 3. アクセントカラー

```
- Primary: プライマリアクション
- Hover: ホバー状態
- Muted: 背景アクセント
- Glow: グロー効果（オプション）
```

### 4. セマンティックカラー

```
- Success: 成功/高スコア
- Warning: 注意/中スコア
- Error: エラー/低スコア
- Info: 情報
```

---

## トーン別カラーシステム

### プロフェッショナル（ダークモード + ブルー）

**特徴:**
- 落ち着いた印象
- 長時間使用でも目が疲れにくい
- テック企業/ビジネスツール向け

**カラーパレット:**

```css
/* ベース */
--bg-primary: #0A0A0B;
--bg-secondary: #141416;
--bg-tertiary: #1C1C1F;
--surface: #242428;

/* テキスト */
--text-primary: #FAFAFA;
--text-secondary: #A1A1AA;
--text-muted: #71717A;

/* アクセント（ブルー） */
--accent-primary: #3B82F6;
--accent-hover: #2563EB;
--accent-muted: #1E3A5F;
--accent-glow: rgba(59, 130, 246, 0.2);

/* セマンティック */
--success: #22C55E;
--warning: #F59E0B;
--error: #EF4444;
--info: #3B82F6;
```

**使用例:**
- 開発者ツール
- ダッシュボード
- 音声/会話アプリ
- 金融アプリ

---

### プロフェッショナル（ダークモード + パープル）

**特徴:**
- AI/テック感
- 創造性を感じさせる
- 差別化しやすい

**カラーパレット:**

```css
/* ベース */
--bg-primary: #0A0A0C;
--bg-secondary: #13131A;
--bg-tertiary: #1A1A24;
--surface: #232330;

/* テキスト */
--text-primary: #FAFAFA;
--text-secondary: #A1A1AA;
--text-muted: #71717A;

/* アクセント（パープル） */
--accent-primary: #8B5CF6;
--accent-hover: #7C3AED;
--accent-muted: #4C1D95;
--accent-glow: rgba(139, 92, 246, 0.2);

/* セマンティック */
--success: #22C55E;
--warning: #F59E0B;
--error: #EF4444;
--info: #8B5CF6;
```

**使用例:**
- AIアシスタント
- クリエイティブツール
- 音楽/メディアアプリ

---

### モダン・クリーン（ライトモード）

**特徴:**
- 明るく開放的
- Apple風のミニマル
- 幅広い層に受け入れられやすい

**カラーパレット:**

```css
/* ベース */
--bg-primary: #FFFFFF;
--bg-secondary: #F9FAFB;
--bg-tertiary: #F3F4F6;
--surface: #E5E7EB;

/* テキスト */
--text-primary: #111827;
--text-secondary: #4B5563;
--text-muted: #9CA3AF;

/* アクセント（ブルー） */
--accent-primary: #2563EB;
--accent-hover: #1D4ED8;
--accent-muted: #DBEAFE;

/* セマンティック */
--success: #16A34A;
--warning: #D97706;
--error: #DC2626;
--info: #2563EB;
```

**使用例:**
- 一般消費者向けアプリ
- ドキュメント/ノートアプリ
- ヘルスケアアプリ

---

### フレンドリー（ライトモード + グリーン）

**特徴:**
- 親しみやすい
- 成長/学習を連想
- Duolingo風

**カラーパレット:**

```css
/* ベース */
--bg-primary: #FFFFFF;
--bg-secondary: #F0FDF4;
--bg-tertiary: #DCFCE7;
--surface: #E5E7EB;

/* テキスト */
--text-primary: #14532D;
--text-secondary: #166534;
--text-muted: #6B7280;

/* アクセント（グリーン） */
--accent-primary: #22C55E;
--accent-hover: #16A34A;
--accent-muted: #BBF7D0;

/* セマンティック */
--success: #22C55E;
--warning: #F59E0B;
--error: #EF4444;
--info: #3B82F6;
```

**使用例:**
- 学習アプリ
- フィットネス/健康アプリ
- 環境/サステナビリティアプリ

---

### フレンドリー（ライトモード + オレンジ）

**特徴:**
- エネルギッシュ
- 注意を引きやすい
- 活動的な印象

**カラーパレット:**

```css
/* ベース */
--bg-primary: #FFFFFF;
--bg-secondary: #FFF7ED;
--bg-tertiary: #FFEDD5;
--surface: #E5E7EB;

/* テキスト */
--text-primary: #7C2D12;
--text-secondary: #9A3412;
--text-muted: #6B7280;

/* アクセント（オレンジ） */
--accent-primary: #F97316;
--accent-hover: #EA580C;
--accent-muted: #FED7AA;

/* セマンティック */
--success: #22C55E;
--warning: #F97316;
--error: #EF4444;
--info: #3B82F6;
```

**使用例:**
- フードデリバリー
- スポーツ/アクティビティ
- キッズ向けアプリ

---

## アクセントカラーの心理効果

| カラー | 心理効果 | 適したアプリ |
|--------|---------|-------------|
| **ブルー** | 信頼、安定、プロフェッショナル | ビジネス、金融、ヘルスケア |
| **グリーン** | 成長、健康、自然 | 学習、フィットネス、環境 |
| **パープル** | 創造性、高級感、AI感 | クリエイティブ、AI、メディア |
| **オレンジ** | エネルギー、楽しさ、注意 | フード、スポーツ、ゲーム |
| **レッド** | 緊急性、情熱、エネルギー | セール、緊急通知、ゲーム |
| **ティール** | 落ち着き、信頼、独自性 | ウェルネス、テック、環境 |

---

## ダークモード設計ガイド

### 原則

1. **純黒(#000000)は避ける**
   - 目が疲れやすい
   - 深いグレー(#0A0A0B等)を使用

2. **コントラスト比を確保**
   - テキスト: 4.5:1以上
   - 大きなテキスト: 3:1以上

3. **彩度を下げる**
   - ライトモードより彩度を下げたアクセントカラーを使用

4. **エレベーション表現**
   - 明るさで階層を表現（上のレイヤーほど明るく）
   - シャドウは控えめに

### ダークモードでの色の調整

```css
/* ライトモードのブルー */
--accent-light: #2563EB;

/* ダークモードでは彩度を下げ、明度を上げる */
--accent-dark: #3B82F6;
```

---

## カラーコントラストチェック

### WCAG基準

| レベル | 通常テキスト | 大きなテキスト |
|--------|-------------|---------------|
| AA | 4.5:1 | 3:1 |
| AAA | 7:1 | 4.5:1 |

### チェックツール

- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Coolors Contrast Checker](https://coolors.co/contrast-checker)

### 推奨コントラスト比

```
背景 #0A0A0B に対して:
- #FAFAFA (Primary Text): 19.3:1 ✅
- #A1A1AA (Secondary Text): 7.4:1 ✅
- #71717A (Muted Text): 4.6:1 ✅

背景 #FFFFFF に対して:
- #111827 (Primary Text): 16.7:1 ✅
- #4B5563 (Secondary Text): 7.5:1 ✅
- #9CA3AF (Muted Text): 3.0:1 ⚠️ (大きなテキストのみ)
```

---

## Tailwind CSS互換カラー

### ダークモード（ブルーアクセント）

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        background: {
          primary: '#0A0A0B',
          secondary: '#141416',
          tertiary: '#1C1C1F',
        },
        surface: '#242428',
        accent: {
          DEFAULT: '#3B82F6',
          hover: '#2563EB',
          muted: '#1E3A5F',
        },
      },
    },
  },
};
```

### CSS変数形式

```css
:root {
  /* ダークモード */
  --color-bg-primary: 10 10 11;
  --color-bg-secondary: 20 20 22;
  --color-accent: 59 130 246;
}

/* 使用例 */
.bg-primary {
  background-color: rgb(var(--color-bg-primary));
}

.bg-accent {
  background-color: rgb(var(--color-accent));
}

.bg-accent-20 {
  background-color: rgb(var(--color-accent) / 0.2);
}
```

---

## カラー選択のチェックリスト

- [ ] ターゲットユーザーに適したトーンか
- [ ] ブランドイメージと一致しているか
- [ ] アクセシビリティ基準を満たしているか
- [ ] ダークモード対応が必要か
- [ ] セマンティックカラーが明確か
- [ ] アクセントカラーが目立ちすぎないか
- [ ] 色覚多様性に配慮しているか
