# デザインシステム テンプレート

`docs/design/design-system.md` の雛形。読み手は UI を実装する別のセッションなので、散文ではなく
「そのまま使える値」を置く。決めた理由は対になる `design-concept-template.md` 側に書く。

## 目次

- 使い方
- コンポーネントインベントリ
- カラートークン
- タイポグラフィ
- サイズ系トークン
- モーション
- 状態マトリクス
- レスポンシブ
- アクセシビリティ
- 国際化
- パフォーマンス予算
- 実装セッションへの指示

## 使い方

- 決まった節だけを書き、決まっていない節は削る。理由: 埋まっていない表を残すと、実装セッション
  が空欄を「自由に決めてよい」と解釈して発散する。
- 値はトークン名で書き、生の色・px を直接書かない。名前は `../templates/tokens.css` の語彙に揃える。
- コントラスト比は計算した値だけを載せる。記憶や他ドキュメントからの転記はしない。
- `## コンポーネントインベントリ` 以降をコピーして `docs/design/design-system.md` にする。

## コンポーネントインベントリ

実装対象の部品をここで確定させる。この表に無い部品は新規に作らず、必要になった時点で表に足す。
理由: 一覧が無いと、同じ役割の部品が画面ごとに別実装で増える。

| コンポーネント | 由来（基盤ライブラリの部品名） | バリアント | サイズ | 状態 |
|---------------|------------------------------|-----------|--------|------|
| Button | [例: shadcn/ui `button`] | primary / secondary / ghost / destructive | sm / md / lg | 状態マトリクス参照 |
| Input | [例: shadcn/ui `input`] | default / with-icon | md | default / focus / error / disabled |
| Card | 独自 | flat / elevated | — | default / hover（クリック可能時のみ） |
| List item | | | | |
| Nav item | | | | |
| | | | | |

由来が「独自」の部品は、基盤ライブラリに同等品が無いことを1行で書く。理由: 見落としで独自実装が
増えると、アクセシビリティ対応をゼロから作り直すことになる。

## カラートークン

`../templates/tokens.css` をコピーし、primitive 層の値だけを差し替える。この節には semantic 層の
一覧だけを載せる。理由: 実装セッションが参照してよいのは semantic 層だけで、primitive を直接
読ませるとテーマ切替が壊れる。

| トークン | ライト | ダーク | 用途 |
|---------|--------|--------|------|
| `--color-bg` | | | ページ最背面 |
| `--color-bg-subtle` | | | 一段沈んだ帯・セクション背景 |
| `--color-bg-elevated` | | | カード・シートなど浮いた面 |
| `--color-surface` | | | 入力欄・チップなど部品の面 |
| `--color-surface-hover` | | | 上記のポインタ滞在時 |
| `--color-text` | | | 見出し・本文 |
| `--color-text-muted` | | | 補足・キャプション |
| `--color-text-subtle` | | | プレースホルダ・無効に近い情報 |
| `--color-text-on-accent` | | | アクセント面の上の文字 |
| `--color-border` | | | 通常の枠線・区切り |
| `--color-border-strong` | | | 強調枠線・入力欄の枠（非テキスト 3:1） |
| `--color-focus` | | | フォーカスリング（背景と 3:1 以上） |
| `--color-overlay` | | | モーダル背面のスクリム |
| `--color-accent` / `-hover` / `-active` / `-subtle` | | | 主アクションと、その状態・薄い背景 |
| `--color-success` / `-subtle` | | | 完了・肯定 |
| `--color-warning` / `-subtle` | | | 注意・可逆な失敗 |
| `--color-danger` / `-subtle` | | | 破壊的操作・エラー |
| `--color-info` / `-subtle` | | | 中立の通知 |
| `--color-disabled-bg` / `--color-disabled-text` | | | 無効状態 |

状態オーバーレイは `--state-hover-opacity: 0.08` / `--state-pressed-opacity: 0.12`。hover と pressed は
新しい色を足さず面の上に不透明度で重ねる。理由: 色を増やすとテーマごとの調整点が倍になる。
アクセント面に白文字を置く前に比率を測る。緑・橙・黄・ライムは白文字が 4.5:1 を通らないことが
多く、その場合は濃色文字に変えるか、アクセントの明度を下げる。

## タイポグラフィ

### スケール

`base` 以下は rem 固定、`lg` 以上のみ `clamp()` で流体にする。理由: 本文を vw で伸縮させると
400% 拡大時に行長と行間が破綻し、リフローの要件を満たせなくなる。

| トークン | 値 | 行間 | 用途 |
|---------|-----|------|------|
| `--text-xs` | 0.75rem | `--leading-tight` | 補助ラベル、バッジ |
| `--text-sm` | 0.875rem | `--leading-normal` | キャプション、副次テキスト |
| `--text-base` | 1rem | `--leading-normal` | 本文 |
| `--text-lg` | `clamp(1.125rem, 1.09rem + 0.17vw, 1.25rem)` | `--leading-normal` | リード文、小見出し |
| `--text-xl` | `clamp(1.25rem, 1.16rem + 0.45vw, 1.5rem)` | `--leading-tight` | 見出し3 |
| `--text-2xl` | `clamp(1.5rem, 1.33rem + 0.85vw, 2rem)` | `--leading-tight` | 見出し2 |
| `--text-3xl` | `clamp(1.875rem, 1.52rem + 1.78vw, 3rem)` | `--leading-tight` | 見出し1、表示用 |

行間トークン: `--leading-tight: 1.3` / `--leading-normal: 1.7` / `--leading-relaxed: 1.9`。

行長は欧文 45〜75文字（`max-width: 65ch`）、和文 35〜45文字。理由: 超えると次の行の先頭を見失い、
下回ると視線の折り返しが増えて読速が落ちる。

### 和文組版

- 本文の行間は 1.7〜1.8。理由: 仮名と漢字は欧文より字面が大きく、欧文と同じ行間だと行が詰まって見える
- 見出しに `font-feature-settings: "palt" 1` を掛けて約物のアキを詰める。本文には掛けない。
  理由: 本文で詰めると字間が不均一になり、長文の可読性が落ちる
- 和文に italic を使わない。合成斜体になり字形が崩れるため、強調は太さ・色・サイズで行う
- 太字は 700 ではなく 600 を使う。理由: 和文書体は画数が多く、700 だと小サイズで potrace が潰れる
- `word-break: normal; overflow-wrap: anywhere; line-break: strict;` で禁則を効かせる

### フォント読み込み

書体は `--font-sans` / `--font-mono` の2つに固定し、部品ごとに足さない。`font-display: swap` と
可変フォントを使いサブセット化する（和文は全字種で数MBに達し、そのままでは LCP を押し上げる）。
self-host する。理由: 外部CDNへの直リンクは閲覧者のIPを第三者に渡すため。

## サイズ系トークン

### スペース（4px 基準）

`--space-1` 0.25rem / `--space-2` 0.5rem / `--space-3` 0.75rem / `--space-4` 1rem /
`--space-5` 1.25rem / `--space-6` 1.5rem / `--space-7` 1.75rem / `--space-8` 2rem /
`--space-9` 2.5rem / `--space-10` 3rem / `--space-11` 4rem / `--space-12` 6rem

### 角丸

`--radius-sm` 0.25rem（タグ、チップ）/ `--radius-md` 0.5rem（ボタン、入力欄）/
`--radius-lg` 0.75rem（カード）/ `--radius-xl` 1rem（モーダル、シート）/ `--radius-full` 9999px

### 影と階層

`--shadow-1` カード / `--shadow-2` ドロップダウン・ポップオーバー / `--shadow-3` モーダル・シート。
ダークでは影が沈むため、`--color-bg-elevated` の明度差と `--color-border` で階層を作る。
強制配色モード（`forced-colors: active`）では影が描画されないので、影だけで境界を作っている要素
には `border` も併せて指定する。

### z-index

`--z-base` 0 / `--z-dropdown` 1000 / `--z-sticky` 1100 / `--z-overlay` 1200 /
`--z-modal` 1300 / `--z-toast` 1400。この6段以外の値を使わない。理由: 中間値を足し始めると、
重なり順の根拠がコードから読めなくなる。

## モーション

### 原則

1. 動きは意味を持つときだけ使う（状態の連続性、操作へのフィードバック、注意の誘導）
2. 画面をまたぐ動きより、その場での変化を優先する。理由: 遷移アニメーションは待ち時間として体感される
3. 動きが無くても情報は完全に伝わるようにする。動きは伝達手段ではなく補強

### トークン

| トークン | 値 | 用途 |
|---------|-----|------|
| `--motion-duration-fast` | 100ms | 色・不透明度の変化、ホバー |
| `--motion-duration-base` | 200ms | トグル、小要素の出現、展開 |
| `--motion-duration-slow` | 400ms | モーダル、ドロワー、画面遷移 |
| `--motion-ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | 標準の出入り |
| `--motion-ease-emphasized` | `cubic-bezier(0.3, 0, 0, 1)` | 強調したい遷移 |
| `--motion-ease-exit` | `cubic-bezier(0.4, 0, 1, 1)` | 消える方向 |

### 実装の制約

- `transform` と `opacity` だけをアニメーションさせる。理由: レイアウトや描画を伴う属性を動かすと
  フレーム落ちし、INP を悪化させる
- `will-change` は動く直前に付け、終わったら外す。常時指定はメモリを確保し続ける
- `prefers-reduced-motion: reduce` では移動・回転・拡大・視差を止め、フェードに置き換える（全消し
  より状態の連続性が残る）。自動再生カルーセルと視差は完全に停止する。停止の土台は `tokens.css` の
  `@media (prefers-reduced-motion: reduce)` に入っている

## 状態マトリクス

hover は `:focus-visible` と対で定義する。理由: hover だけに情報を載せると、キーボード操作と
タッチ環境でその情報に到達できない。

### 記入例: Button (primary)

| 状態 | 背景 | テキスト | 境界 | 補足 |
|------|------|---------|------|------|
| Default | `--color-accent` | `--color-text-on-accent` | none | |
| Hover | `--color-accent-hover` | 同上 | none | `@media (hover: hover)` の中だけで適用 |
| Focus-visible | Default のまま | 同上 | `--color-focus` 2px / offset 2px | 背景と 3:1 以上 |
| Active | `--color-accent-active` | 同上 | none | |
| Disabled | `--color-disabled-bg` | `--color-disabled-text` | none | `aria-disabled` を付け、フォーカスは残す |
| Loading | Default のまま | 同上 | none | ラベルを保持し幅を固定してレイアウトシフトを防ぐ |
| Error | — | — | — | ボタン自体では表さず、対象の入力欄側に出す |
| Selected | `--color-accent-subtle` | `--color-accent` | `--color-accent` 1px | `aria-pressed` |

### 他のコンポーネント

| 状態 | Input | Card | List item | Nav item |
|------|-------|------|-----------|----------|
| Default | `--input-bg` / `--input-border` | `--card-bg` / `--shadow-1` | `--color-bg` | `--color-text-muted` |
| Hover | `--color-border-strong` | `--color-surface-hover` | `--color-surface-hover` | `--color-text` |
| Focus-visible | `--color-focus` 2px | `--color-focus` 2px | `--color-focus` 2px | `--color-focus` 2px |
| Active | — | `--shadow-1` に戻す | `--state-pressed-opacity` を重ねる | — |
| Disabled | `--color-disabled-bg` / `--color-disabled-text` | 不透明度は下げず操作だけ無効化 | `--color-text-subtle` | `--color-disabled-text` |
| Loading | 値をスケルトンに置換 | スケルトン（高さを実物と揃える） | スケルトン | — |
| Error | `--color-danger` 境界 + 説明文 | — | `--color-danger-subtle` | — |
| Selected | — | `--color-accent` 1px 境界 | `--color-accent-subtle` | `--color-accent` + `aria-current="page"` |

エラーはアイコンと文言を伴わせて伝える。理由: 色覚特性や強制配色モードでは色差が失われるため、
色だけに載せた情報は届かない。

## レスポンシブ

### 手段の使い分け

| 対象 | 手段 | 理由 |
|------|------|------|
| ページ全体の構造（サイドバーの有無、段組数） | メディアクエリ | 判断材料がビューポート幅そのもの |
| 再利用コンポーネント（カード、リスト項目） | コンテナクエリ `@container` | 同じ部品が幅の違う場所に置かれるため、親の幅で決める |
| 文字サイズ・余白の連続的な変化 | `clamp()` | ブレイクポイントでの段差を無くす |
| 折り返しだけのグリッド | `repeat(auto-fit, minmax(16rem, 1fr))` | 列数を宣言しないので、幅が変わっても破綻しない |

### ブレイクポイント（ページ構造用）

| 名称 | 幅 | ここで変わること |
|------|-----|----------------|
| sm | 640px | |
| lg | 1024px | |
| xl | 1280px | |

幅は端末名ではなくコンテンツが破綻する位置で決める。理由: 端末の画面サイズは世代ごとに動く。
必要なら md 768px を足す。

### 入力モダリティ（画面幅とは別軸）

- `@media (hover: hover) and (pointer: fine)` — hover 前提の表現はこの中だけに閉じる
- `(pointer: coarse)` — ターゲットを 44px 以上に広げる
- `:focus-visible` を使い、ポインタ操作ではリングを出さない

検証条件: 320px 幅で横スクロールが出ない / 400% 拡大で情報が失われない / `safe-area-inset` を
考慮する / 高さは `vh` でなく `dvh` を使う（モバイルのURLバーで `vh` がずれるため）。

## アクセシビリティ

WCAG 2.2 レベルAA を最低ラインとする。EU 向けに提供する場合は欧州アクセシビリティ法の観点でも
実質的な要件になる（調和規格の基準は WCAG 2.1 AA だが、2.2 AA を満たせば適合が推定される）。

| 項目 | 基準 | 本プロダクトでの値 |
|------|------|-------------------|
| テキストコントラスト (1.4.3) | 通常 4.5:1 / 大 3:1 | |
| 非テキストコントラスト (1.4.11) | UI境界・アイコン 3:1 | |
| ターゲットサイズ (2.5.8 / AA) | 24×24 CSS px 以上、または間隔で確保 | |
| ターゲットサイズ（設計値） | iOS 44×44pt / Android 48×48dp | |
| フォーカスの外観 (2.4.13) | 2px 以上・背景と 3:1・要素を囲む | |
| フォーカスが隠れない (2.4.11) | 固定ヘッダー/フッターに隠されない | `scroll-margin` の値 |
| ドラッグの代替 (2.5.7) | ドラッグ操作に単一ポインタの代替がある | |
| 再入力の回避 (3.3.7) | 同一フロー内で同じ情報を再入力させない | |
| アクセシブルな認証 (3.3.8) | 記憶・パズルを必須にしない | |
| リフロー (1.4.10) | 320px 幅 / 400% 拡大で横スクロールなし | |
| テキスト間隔 (1.4.12) | 行間1.5倍などの上書きで破綻しない | |

24px は適合の下限であって設計値ではない。実際のターゲットは 44/48 で置く。理由: 24px は指の
接地面より小さく、誤タップが増える。

### ユーザー設定の尊重

- `prefers-reduced-motion: reduce` — 移動・拡大・回転・視差を止め、フェードに置き換える
- `prefers-contrast: more` — 境界と文字のコントラストを上げる
- `forced-colors: active` — `box-shadow` が無効になるため、影で作っていた境界とフォーカスリングを
  `border` / `outline` に置き換え、背景画像で伝えている情報が消えないか確認する
- OS の文字サイズ設定（Dynamic Type / フォントスケール）で 200% まで破綻しないこと

### キーボードと支援技術

全機能がキーボードだけで到達・操作できること / フォーカス順序が視覚順序と一致すること /
非同期更新・ストリーミング表示・トーストの読み上げ方針を決めること / 見出しとランドマークで
構造を表すこと。

### コントラスト実測

この表の行は `../scripts/check_contrast.py` の出力をそのまま貼る。理由: 記憶で書いた比率は外れる
ことが多く、外れた値に適合の印が付くと、そのまま実装されて不適合な UI が量産される。

```
name  fg  bg  kind  ratio  required  result
----  --  --  ----  -----  --------  ------
（ここにスクリプトの標準出力を貼る）
```

パレットを変更したら、ライトとダークの両方でこの表を作り直す。

## 国際化

- 対応言語 と RTL の要否。RTL がある場合は `margin-inline-start` などの論理プロパティで書く。
  理由: 物理方向で書いた余白は RTL で左右が入れ替わらない
- 文字列の伸長に余裕を持たせる（ドイツ語 +35%、日本語→英語 +50% を見込む）。ボタン幅を固定しない
- 数値・日付・通貨は `Intl` に委ね、UI に書式を直書きしない。理由: 桁区切りと日付順がロケールで違う
- 和欧混植時の行間と約物処理は「タイポグラフィ > 和文組版」に従う

## パフォーマンス予算

| 指標 | 目標 | 主な担保手段 |
|------|------|-------------|
| INP | 200ms 以下 | 長いタスクを分割し、入力に対する応答を先に返す |
| CLS | 0.1 以下 | 画像・埋め込みに `aspect-ratio` で領域を予約する |
| LCP | 2.5s 以下 | 主画像の先読み、フォントのサブセット化 |

フォント読み込みは `font-display: swap` に加え、`size-adjust` / `ascent-override` で代替フォントの
字面を合わせ、切り替わり時の行送りのずれを抑える。アニメーションは `transform` と `opacity` に
限り、60fps（120Hz 端末では 120fps）を維持できない表現は静的な表示に置き換える。

## 実装セッションへの指示

- `../templates/tokens.css` を `src/styles/tokens.css` にそのままコピーし、primitive 層の値だけを
  この文書の値に差し替える。構造とトークン名は変えない
- UI コードからは semantic 層（`--color-*`, `--space-*`, `--text-*`, `--motion-*`）だけを参照する。
  primitive 層を直接読むとテーマ切替が効かなくなる
- 色・角丸・余白・所要時間を新しく発明しない。必要な値が無い場合は、トークンを足す提案を出して
  から実装する
- コンポーネントは「コンポーネントインベントリ」の由来列にあるライブラリの部品から作る。
  同等品があるのに独自実装しない
- 状態は「状態マトリクス」の8状態をすべて実装する。default だけの実装で止めない
