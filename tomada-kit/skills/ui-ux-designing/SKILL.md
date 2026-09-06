---
name: ui-ux-designing
description: "Produces a settled UI/UX design direction for an app or web service, written out as docs/design/design-concept.md, docs/design/design-system.md and a filled tokens.css, via competitor research, batched option questions, and a measured contrast pass. Covers settling an app's visual direction, choosing a color scheme or theme policy, building a design system or design tokens, establishing UX patterns, and deciding how a new feature should look. Not for wireframes, screen layouts, or user flow diagrams — the designing-wireframes skill covers those; not for clarifying product requirements or writing a spec — the refining-requirements skill covers that."
metadata:
  platforms: claude-code, codex
---

# UI/UX Designing

アプリ/Webサービスのデザイン方向性を、要件の確認・競合調査・段階的な選択によって確定させ、`docs/design/` 配下の3ファイルに落とすスキル。決めるのは配色、テーマ方針、トークン、タイポグラフィ、モーション、状態設計、アクセシビリティの適合値。生成したドキュメントを読むのは UI を実装する別のAIセッションなので、散文ではなくそのまま使える具体値（トークン名、OKLCH値、実測コントラスト比、ブレイクポイント）を書く。理由: 「AA準拠」「モダンで清潔感のある」といった記述からは実装値が導けず、受け取ったセッションが結局その場で決め直すことになる。

## Inputs / Outputs

入力:

- プロダクト概要、または上流工程の要件ドキュメント
- 既存の `docs/design/*.md`（あれば）
- 技術スタック（フレームワーク、CSS基盤、UIライブラリ）

出力（対象プロジェクトの `docs/design/` に書く）:

| ファイル | 足場 | 中身 |
|---|---|---|
| `docs/design/design-concept.md` | `templates/design-concept-template.md` | 何をどう決めたか、なぜそう決めたか |
| `docs/design/design-system.md` | `templates/design-system-template.md` | 実装可能な値（トークン表、状態マトリクス、実測コントラスト） |
| `docs/design/tokens.css` | `templates/tokens.css` をコピーして値を差し替える | そのまま読み込める CSS カスタムプロパティ |

既存ファイルがある場合は別名で新規作成せず、同じファイルを更新する。理由: 実装側の参照先が分裂すると、古い方が読まれる。

確認ラウンドが1つ終わるごとに、design-concept.md の「決定ログ」節へ決定と理由を追記する。中断後に再開したセッションは、質問を組み立てる前にまずこの節を読む。理由: どこまで合意済みかが残っていないと、同じ質問をユーザーに投げ直すことになる。

## Workflow

1. Phase 1 要件確認 — 上流の成果物を読み、埋まっていない前提だけを確認する
2. Phase 2 競合調査 — 競合3つ以上を同じフローで比較し、調査サマリーを作る
3. Phase 3 方向性の決定 — ブランド、土台、テーマ、アクセント、密度の5点を確定する
4. Phase 4 詳細の決定 — ナビゲーション、モーション、状態設計、国際化などを確定する
5. Phase 5 ドキュメント生成 — 上記3ファイルを書く
6. Phase 6 検証 — コントラストを実測し、アクセシビリティの確認手順を実行する

1画面・1コンポーネントについての「これはどう見せるべきか」という単発の相談では、推奨する1案とそのトレードオフを答えて終える（Phase 2〜6 は実行しない）。理由: 全工程は方向性が未確定なプロダクト向けの手順で、局所的な問いに適用すると往復のコストが得られる精度を上回る。

## Phase 1 要件確認

先に上流の成果物（要件ドキュメント、既存の `docs/design/*.md`、README）を読み、そこで答えが出ている項目は確定済みとして扱い、聞き直さない。理由: 一度答えたことを再び聞かれると、ユーザーは残りの質問にも雑に答えるようになる。

埋まらなかった項目だけを、後続フェーズと同じ選択肢形式で確認する。対象はプロダクト概要、ユーザー像（状況・動機・制約）、対応プラットフォーム、既存ブランド資産（ロゴ・既定色・書体）の有無、技術スタック。

技術スタックからデザインシステムの土台候補を推定しておく（例: React + Tailwind なら shadcn/ui 系、ネイティブなら Material 3 / HIG）。ここでは推定に留め、確定は Phase 3 の質問で行う。理由: 土台が決まるとトークン名・部品名・命名規約が連動して決まるので、承認なしに進めると後戻りが大きい。

## Phase 2 競合調査

`references/agents/research-competitors.md` のプレースホルダを埋め、サブエージェント1体（モデル `sonnet`、上限1体）に委譲する。<!-- derived from orchestrating-models §2 --> 理由: 調査対象アプリ・評価軸・出力形式をすべて本体側で確定させて渡すため、委譲先に残るのは定型的な情報収集で判断が含まれない。

サブエージェントを起動できないホストでは、同じプロンプトを本体セッションで実行する（読む資料・観点・出力形式は変えない）。web検索が使えないホストでは、参考アプリ名・URL・スクリーンショットの提供をユーザーに依頼し、それを材料に同じ観点で比較する。

できあがった調査サマリーは、Phase 3 に進む前にユーザーへ共有する。理由: 次フェーズの選択肢はこの調査を根拠に組み立てるので、根拠が間違っていれば選択肢ごと作り直しになる。

## Phase 3 方向性の決定

`references/questions-core.md` の Phase 3 節から、次の5点を確定させる。質問データはそのファイルにあるので、選択肢と説明を作り直さない。理由: 各選択肢の説明はどのトークンに効くかまで書き分けてあり、その場で言い換えると回答が実装値に落ちなくなる。

- ブランドパーソナリティ — 形容詞ペアの軸で聞き、彩度・角丸・余白・モーション量へ写す
- デザインシステムの土台 — Phase 1 で推定した候補を提示して確定させる
- テーマ方針 — ライト/ダーク両対応か片方のみか、OS連動かアプリ内トグルか
- アクセントカラー — プロダクトが約束していることから色相の方向を選ぶ
- 情報密度 — 1画面の情報量と `--space` スケールの基準値

5点は1ラウンドに3〜4問ずつ分けて聞く。

## Phase 4 詳細の決定

`references/questions-core.md` の Phase 4 節にある汎用質問（ナビゲーションモデル、モーション量、プラットフォーム規約、デバイス優先度、状態設計（空・読み込み・エラー・オフライン・権限拒否）、UI言語と国際化、ゲスト状態とログイン前後の画面）を確定させる。

アプリタイプが `references/questions-app-type.md` の節（会話/音声アプリ、Eコマース/ショッピング、ダッシュボード/管理画面、AIアシスタント/エージェント）に一致するときだけ、そこの追加質問を足す。一致しないときは `references/app-type-ux-patterns.md` または `references/app-type-ux-patterns-verticals.md` の該当節から、選択によって実装値が変わる論点を2〜3個選び、等価な質問を組み立てる。理由: 他タイプ向けの質問を流用すると、答えても実装値が変わらない問いでラウンドを使い切る。

## Phase 5 ドキュメント生成

3つの出力を書く。design-system.md を埋めるあいだは `references/design-tokens.md`（層構造・命名・ライト/ダーク実装・サイズとモーションの値）、`references/color-systems.md`（パレット選定とトーン別パレット）、`references/accessibility.md`（適合基準と要件表）を開いて値を取る。理由: 記憶で書いたトークン名や色値はこれらのファイルの語彙とずれ、実装セッションが2つの定義を突き合わせることになる。

会話で実際に決まった節だけを埋め、決まっていない節は既定値で埋めずに削る。理由: 空欄や無難な既定値が残ると、実装セッションがそれを決定事項として扱う。長さは中身に合わせ、決定が3件しかない節を水増ししない。未決を残すときは `未決: <何が決まれば決まるか>` と書く。

`docs/design/tokens.css` は `templates/tokens.css` をコピーし、`replace` 注記の付いた行（色相・書体）を差し替える。

## Phase 6 検証

パレットが決まったら、text/bg、on-accent/accent、border/bg、focus/bg の各組を、ライトとダークの両方で実測する。スキルディレクトリからの相対実行でよい。

```bash
python3 scripts/check_contrast.py --pair "#FFFFFF" "#2563EB" --kind text
python3 scripts/check_contrast.py pairs.json
```

JSON ファイル形式は `{"name", "fg", "bg", "kind"}` の配列で、組が増えるほどこちらが読みやすい。`--kind` は本文が `text`、大きな文字が `large`、境界とアイコンが `ui`。終了コードは 0（全件通過）、1（1件以上 FAIL）、2（入力エラー）。

出力はそのまま design-system.md の「コントラスト実測」表に貼る。理由: 記憶や他ドキュメントから転記した比率は外れることが多く、外れた値に適合の印が付くと、不適合な UI がそのまま実装される。FAIL が出たら色を調整し、終了コードが 0 になるまで再実行する。

続けて `references/accessibility.md` の「色覚多様性の確認手順」と「キーボードと支援技術」を上から実行し、そこでまだ決めていない項目（フォーカスリングの太さとオフセット、最小タップ領域、ライブリージョンの方針）を確定させる。

## 質問設計の原則

Phase 1・3・4 の確認はすべてこの形式に従う。原則はここにしか書かず、各参照ファイルはこの節を指している。

- 選択肢は2〜4個、それぞれに具体的な内容と何を捨てることになるかを添える。理由: 「色はどうしますか」のような開いた問いはユーザーに設計を代行させることになり、返ってきた答えが実装値に落ちない
- 推奨できる案がある場合に限り、1つだけ `（推奨）` を付ける。理由: 推奨が複数あるのは推奨が無いのと同じで、根拠なく付ければ判断を歪める
- 1ラウンドは3〜4問、5問を超えない。理由: 後半の設問ほど回答が雑になり、雑に決まった値がそのまま実装される
- 選択肢提示の仕組みを持たないホストでは、`references/questions-core.md` の「平文で提示する場合」の変換例に従って番号付きの平文にする。選択肢の数と内容は変えない
- 1ラウンド終わるごとに、決定と選んだ理由を design-concept.md の「決定ログ」へ追記する。理由: 理由が残っていないと、後から出た異論に対して再検討すべきかどうかを判断できない

## 参照の使い分け

- [references/questions-core.md](references/questions-core.md) — Phase 3・4 の質問を出すときに読む
- [references/questions-app-type.md](references/questions-app-type.md) — アプリタイプがその4節のいずれかに一致したときに読む
- [references/research-methods.md](references/research-methods.md) — 調査を自分で実行するとき、調査サマリーの節構成を確認するときに読む
- [references/agents/research-competitors.md](references/agents/research-competitors.md) — 調査をサブエージェントに委譲するときに読む
- [references/app-type-ux-patterns.md](references/app-type-ux-patterns.md) — 汎用5タイプ（会話/音声、Eコマース、ダッシュボード、SNS、学習/教育）の設計判断が要るときに読む
- [references/app-type-ux-patterns-verticals.md](references/app-type-ux-patterns-verticals.md) — 業種寄りのタイプ（AIアシスタント、生産性、フィンテック、ヘルスケア、開発者ツール、予約/マーケットプレイス）に当たるときに読む
- [references/color-systems.md](references/color-systems.md) — パレットとアクセントを決めるとき、色相を動かしたときに読む
- [references/design-tokens.md](references/design-tokens.md) — トークンを書き出すとき、Tailwind や既存基盤へ写像するときに読む
- [references/accessibility.md](references/accessibility.md) — 適合基準の値を決めるとき、Phase 6 の確認手順を実行するときに読む
- [references/platform-notes.md](references/platform-notes.md) — 使いたい機能がこのホストで使えるか確認するときに読む

## Platform notes

ホストごとの機能対応（選択肢の提示、web検索、サブエージェントへの委譲、スクリプト実行）は [references/platform-notes.md](references/platform-notes.md) を参照。
