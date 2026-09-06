# デザイントークン

トークンの構造・記法・テーマ実装・サイズ/モーションの値を定義する。
色の具体的なパレットは `color-systems.md`、適合基準は `accessibility.md` を参照する。

## 目次

- [トークンの3層構造](#トークンの3層構造)
- [OKLCH でスケールを組む](#oklch-でスケールを組む)
- [セマンティックトークンの一覧](#セマンティックトークンの一覧)
- [ライト/ダーク両対応の実装](#ライトダーク両対応の実装)
- [Tailwind v4 の `@theme` への写像](#tailwind-v4-の-theme-への写像)
- [サイズ系トークン](#サイズ系トークン)
- [モーショントークン](#モーショントークン)
- [状態オーバーレイと無効状態](#状態オーバーレイと無効状態)

---

## トークンの3層構造

1. **Primitive（原始値）** — `--blue-600: oklch(0.545 0.140 248)`。用途を持たない色見本。
2. **Semantic（意味）** — `--color-accent: var(--blue-600)`。用途で命名する。テーマ切替はこの層だけを差し替える。
3. **Component（部品）** — `--button-primary-bg: var(--color-accent)`。

原則: 各層は必ず1つ下の層だけを参照する。理由: 層を飛ばすと（Component が Primitive を直接参照すると）テーマを切り替えたときにその箇所だけ取り残され、ダークモードで壊れる。

```css
:root {
  /* 1. Primitive: 値そのもの。用途名を混ぜない */
  --blue-600: oklch(0.545 0.140 248);
  --blue-700: oklch(0.495 0.130 248);
  /* 2. Semantic: 用途で命名。Primitive だけを参照する */
  --color-accent: var(--blue-600);
  --color-accent-hover: var(--blue-700);
  /* 3. Component: Semantic だけを参照する */
  --button-primary-bg: var(--color-accent);
  --button-primary-text: var(--color-text-on-accent);
  --input-bg: var(--color-bg-elevated);
  --input-border: var(--color-border);
  --card-bg: var(--color-bg-elevated);
}
```

生成ドキュメントには Semantic 層の一覧を必ず載せる。理由: Primitive の羅列だけでは実装するセッションが「どの色をボタンに使うか」を判断できず、勝手な割り当てが発生する。Component 層は実装時に増えるので、ドキュメントでは代表的な数個だけ示す。

---

## OKLCH でスケールを組む

新規の色はすべて `oklch(L C H)` で定義する。理由: L（明度）が知覚的に均一なので、ステップを等間隔に刻むだけで見た目の間隔が揃い、ダーク派生とコントラスト調整が計算で導ける。HEX は既存資産との互換表記としてコメントに併記する。

### ステップの刻み方（50〜950）

| ステップ | L の目安 | C の扱い | 主な用途 |
|---|---|---|---|
| 50 / 100 | 0.985 / 0.950 | 基準 C の 10〜20% | `-subtle` 背景、選択中の行 |
| 200 / 300 | 0.905 / 0.835 | 基準 C の 40〜70% | 境界線、無効状態の面 |
| 400 / 500 | 0.740 / 0.660 | 基準 C の 90〜100% | 暗背景上のアクセント、図表 |
| 600 / 700 | 0.545 / 0.495 | 基準 C の 90〜100% | 明背景上のアクセント、ボタン |
| 800 / 900 | 0.425 / 0.340 | 基準 C の 70〜85% | 押下状態、`-subtle` 上の文字 |
| 950 | 0.230 | 基準 C の 40〜55% | 明るいアクセント上の文字色 |

L は等間隔に近く刻み、C は両端で落とす。理由: 明度が極端な領域では sRGB が表現できる彩度が急に狭まるため、C を保つと色域外に出る。H は全ステップで固定する（変えると同じ色の系列に見えなくなる）。

### 色域チェック

sRGB で表現できる最大 C は L と H に依存する。指定した C がそれを超えるとブラウザがクリップし、記載した OKLCH 値と実際の描画色がずれる。以下は sRGB の上限の実測値。

| H | L=0.45 | L=0.55 | L=0.65 | L=0.75 | L=0.95 |
|---|---|---|---|---|---|
| 38（オレンジ） | 0.147 | 0.180 | 0.213 | 0.155 | 0.026 |
| 75（アンバー） | 0.095 | 0.116 | 0.137 | 0.158 | 0.041 |
| 158（グリーン） | 0.105 | 0.129 | 0.152 | 0.175 | 0.078 |
| 196（ティール） | 0.077 | 0.094 | 0.111 | 0.128 | 0.076 |
| 248（ブルー） | 0.121 | 0.148 | 0.175 | 0.135 | 0.025 |
| 305（パープル） | 0.234 | 0.286 | 0.236 | 0.162 | 0.030 |

確認手順: 決めた `oklch(L C H)` を DevTools のカラーピッカーに入れ、色域外警告が出るか、または `oklch()` と変換後の HEX を並べて描画差を見る。広色域（Display P3）を前提にしないなら、上表の値を超えないところで C を止める。

---

## セマンティックトークンの一覧

生成する design-system ドキュメントは、この名前の集合をライト/ダーク両方の値付きで必ず埋める。

| トークン | 役割 | 満たすべき条件 |
|---|---|---|
| `--color-bg` | ページの基底面 | — |
| `--color-bg-subtle` | 一段沈んだ帯・セクション背景 | — |
| `--color-bg-elevated` | カード・シートなど浮いた面 | — |
| `--color-surface` | 入力欄・チップなど部品の面 | — |
| `--color-surface-hover` | 部品面のホバー | — |
| `--color-text` | 本文・見出し | 各面に対し 4.5:1 以上 |
| `--color-text-muted` | 補足・ラベル | 7:1 前後を目標に 4.5:1 以上 |
| `--color-text-subtle` | プレースホルダ・注記 | 4.5:1 以上（プレースホルダも本文扱い） |
| `--color-text-on-accent` | アクセント面上の文字・アイコン | アクセントの全状態に対し 4.5:1 以上 |
| `--color-border` | 入力欄・コントロールの境界 | 隣接面に対し 3:1 以上 |
| `--color-border-strong` | 強調境界・区切り | 4.5:1 前後 |
| `--color-focus` | フォーカスリング | 部品と背景の両方に対し 3:1 以上 |
| `--color-overlay` | モーダル背面のスクリム | 半透明の黒（例 `rgb(0 0 0 / 0.55)`） |
| `--color-accent` / `-hover` / `-active` | 主要アクション | 面として使うなら背景に 3:1 以上 |
| `--color-accent-subtle` | アクセントの淡い背景 | 上に載せる文字と 4.5:1 以上 |
| `--color-success` / `-subtle` | 成功・完了 | 色以外の手掛かりと併用 |
| `--color-warning` / `-subtle` | 注意 | 同上 |
| `--color-danger` / `-subtle` | エラー・破壊的操作 | 同上 |
| `--color-info` / `-subtle` | 情報 | 同上 |
| `--color-disabled-bg` / `--color-disabled-text` | 無効状態 | コントラスト免除だが判別可能に保つ |

装飾的な区切り線だけは 3:1 を下回ってよい。理由: 1.4.11 が求めるのは「部品を識別するために必要な境界」であり、単なる装飾は免除される。ただし入力欄の枠のように、それが無いと部品の範囲が分からないものは必ず 3:1 を満たす。

---

## ライト/ダーク両対応の実装

`color-scheme` と `light-dark()` で1箇所に両モードの値を書く。理由: セマンティック名ごとに2つの値が隣り合うので、片方のモードだけ定義し忘れる事故が構造的に起きない。

```css
:root {
  color-scheme: light dark;        /* フォーム部品とスクロールバーも OS 設定に追従する */

  --color-bg:             light-dark(#FAFCFE, #0E1113);
  --color-bg-elevated:    light-dark(#FFFFFF, #171A1D);
  --color-text:           light-dark(#1B242C, #F1F4F6);
  --color-text-muted:     light-dark(#515961, #97A0A8);
  --color-border:         light-dark(#8C9197, #5D6267);
  --color-accent:         light-dark(#1274BD, #65A9E7);
  --color-text-on-accent: light-dark(#FFFFFF, #051320);
  --color-overlay:        light-dark(rgb(0 0 0 / 0.45), rgb(0 0 0 / 0.65));
}

/* ユーザーによる明示切替を残す場合はここだけ上書きする。
   light-dark() は prefers-color-scheme ではなく計算後の color-scheme を見るので、
   color-scheme の1行を差し替えるだけで全トークンが切り替わる */
:root[data-theme="light"] { color-scheme: light; }
:root[data-theme="dark"]  { color-scheme: dark; }
```

パリティ規則:

- 片方のモードにしか存在しない色を作らない。理由: 実装セッションがもう一方で代替色を勝手に選び、意味が崩れる。
- 同じセマンティック名は両モードで同じ意味を持たせる。`--color-bg-elevated` はライトでは白、ダークでは基底より明るい面、というように役割を保つ。
- コントラストは両モードで個別に測る。ライトで通った比率がダークで通る保証はない。

---

## Tailwind v4 の `@theme` への写像

Tailwind v4 は CSS ファースト設定なので、JS の config ファイルは作らない。セマンティック層をそのまま `@theme` に置くと `bg-accent` / `text-on-accent` のようなユーティリティが生える。

```css
@import "tailwindcss";

@theme {
  --color-bg:             light-dark(oklch(0.990 0.003 248), oklch(0.175 0.006 248));
  --color-surface:        light-dark(oklch(0.945 0.008 248), oklch(0.250 0.010 248));
  --color-text:           light-dark(oklch(0.255 0.020 248), oklch(0.965 0.004 248));
  --color-border:         light-dark(oklch(0.655 0.010 248), oklch(0.495 0.010 248));
  --color-accent:         light-dark(oklch(0.545 0.140 248), oklch(0.715 0.115 248));
  --color-text-on-accent: light-dark(#FFFFFF, oklch(0.180 0.035 248));
  /* 残りのセマンティックトークンも同じ形で並べる（一覧は上表） */
}
```

透明度が要るところは `color-mix()` か `/` 記法で足りるので、`rgb(var(--x) / 0.2)` のようにチャンネルを分解して変数に入れる必要はない。

```css
.badge { background: color-mix(in oklab, var(--color-accent) 14%, transparent); }
.scrim { background: oklch(from var(--color-accent) 0.2 c h / 0.6); }
```

---

## サイズ系トークン

```css
:root {
  /* スペーシング: 4px 基点。--space-N = N * 4px */
  --space-1: 0.25rem; --space-2: 0.5rem; --space-3: 0.75rem; --space-4: 1rem;
  --space-5: 1.25rem; --space-6: 1.5rem; --space-8: 2rem; --space-10: 2.5rem;
  --space-12: 3rem;

  /* 角丸: sm タグ・チップ / md ボタン・入力欄 / lg カード / xl モーダル・シート */
  --radius-sm: 4px; --radius-md: 8px; --radius-lg: 12px;
  --radius-xl: 16px; --radius-full: 9999px;

  /* エレベーション: 1 カード / 2 ドロップダウン / 3 モーダル */
  --shadow-1: 0 1px 2px rgb(0 0 0 / 0.06);
  --shadow-2: 0 4px 12px rgb(0 0 0 / 0.08);
  --shadow-3: 0 12px 32px rgb(0 0 0 / 0.12);

  /* 重ね順 */
  --z-base: 0; --z-dropdown: 1000; --z-sticky: 1100;
  --z-overlay: 1200; --z-modal: 1300; --z-toast: 1400;
}
```

ダークモードでは影ではなく背景明度で階層を表す（`--color-bg` → `--color-bg-elevated` → `--color-surface`）。理由: 暗い面に落とした影はほとんど見えず、階層が伝わらない。影を使う要素には `border` も併記する。理由: `forced-colors: active` では `box-shadow` が無効化され、境界が消える。

`--z-*` に無い数値を実装で直接書かない。理由: 999 や 99999 が混ざると重なり順の意図が読めなくなり、モーダルの上にトーストが出ない等の不具合になる。

---

## モーショントークン

```css
:root {
  --motion-duration-fast: 100ms;  /* 色・不透明度の変化、ホバー、トグル */
  --motion-duration-base: 200ms;  /* 展開・折りたたみ、ポップオーバー、モーダル */
  --motion-duration-slow: 400ms;  /* 画面遷移、大きな領域の変化 */

  --motion-ease-standard:   cubic-bezier(0.2, 0, 0, 1);   /* 標準の入退場 */
  --motion-ease-emphasized: cubic-bezier(0.3, 0, 0, 1);   /* 強調したい遷移 */
  --motion-ease-exit:       cubic-bezier(0.4, 0, 1, 1);   /* 消える方向 */
}
```

原則:

1. 動きは意味を持つときだけ使う（状態の連続性、操作へのフィードバック、注意誘導）。
2. 画面を跨ぐ動きより、その場の変化を優先する。理由: 遷移アニメーションは待ち時間として体感され、繰り返すほど不快になる。
3. 動きが無くても情報は完全に伝わるように作る。動きは伝達手段ではなく補強である。
4. アニメーションさせるのは `transform` と `opacity` だけにする。理由: レイアウトと描画を再計算させないので、低性能端末でもフレームを落とさない。

`prefers-reduced-motion: reduce` は全アニメーションに対して用意する。一律に消すより、移動・拡大縮小・回転・視差をフェードや色変化に置き換えるほうが状態変化が伝わる。

```css
@media (prefers-reduced-motion: reduce) {
  /* 位置の移動をやめ、フェードだけ残す */
  .sheet { transition: opacity var(--motion-duration-fast) var(--motion-ease-standard); transform: none; }
  /* 自動再生カルーセル・視差・大きなスケール変化は止める */
  .carousel { animation: none; }
  html { scroll-behavior: auto; }
}
```

---

## 状態オーバーレイと無効状態

ホバーと押下は色を個別に定義せず、面の上に半透明の層を重ねて表現する。理由: アクセントにも中立面にも同じ規則が使え、状態ごとに色を増やさずに済む。

```css
:root {
  --state-hover-opacity: 0.08;
  --state-pressed-opacity: 0.12;
}

.button-ghost:hover {
  background: color-mix(in oklab, currentColor var(--state-hover-opacity), transparent);
}
.button-ghost:active {
  background: color-mix(in oklab, currentColor var(--state-pressed-opacity), transparent);
}
```

塗りつぶしボタンのように専用の色を持つ部品は `--color-accent-hover` / `--color-accent-active` を使う。どちらの方式でも、`--color-text-on-accent` は base / hover / active の3つすべてに対して 4.5:1 を満たすことを確認する。理由: 最も暗い（または最も明るい）状態だけ通っても、他の状態で読めなくなる。

無効状態は `--color-disabled-bg` / `--color-disabled-text` を使い、コントラストは免除されるが判別可能な水準（背景に対して 2.5:1 前後）に保つ。`opacity` を要素全体に掛けて無効を表現しない。理由: 入れ子の文字やアイコンにも掛かって想定外の薄さになり、値が測れなくなる。

ホバーは必ず `:focus-visible` と対で定義する。ホバーでしか出ない情報を作らない。理由: キーボードとタッチではホバーが発生せず、その情報に到達できない。

