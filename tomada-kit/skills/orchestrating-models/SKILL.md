---
name: orchestrating-models
description: >-
  Playbook for choosing models and deciding what to delegate. The default posture flips
  with the main model: when the main model is Fable, concentrate on judgment and push
  execution to Opus low (the default executor), spending Fable's separate weekly budget only on
  judgment and the tracks that would otherwise need Opus high; when it is Opus, execute
  directly by default and delegate only independent parallel tracks, mechanical work, and
  context isolation. Covers model x effort tiers (Sonnet low / Opus low / Fable medium /
  Fable high) and the dominated combinations to avoid, the required elements of a
  delegation prompt, relay formations, wording tuned to each model's quirks, the cache cost
  a sub-agent spawn pays, and techniques for surfacing unknowns. Use when starting a large
  task, when deciding whether to delegate, when choosing an effort level, or when asked to
  cut token cost.
metadata:
  platforms: claude-code
---

# orchestrating-models

どのモデルに何をやらせるかを決めるための運用手順。安さだけでモデルを選ばない。難しい実装を安いモデルに渡して手戻りするほうが、最初から Opus に渡すより高くつく。

**使わない場面:** 会話的な質問への回答、単一ファイルの小さな編集、対話で細かく舵取りしたい作業。委譲のオーバーヘッドが本体コストを上回る。

## 1. 姿勢を決める(最初にやること)

このセッションのメインモデルを確認し、既定姿勢を選ぶ。ここを間違えると以降の判断がすべてずれる。

| | メインが Fable | メインが Opus |
|---|---|---|
| 既定 | **委譲する**(枠が別で有限、価値は判断の質にある) | **自分でやる**(実行そのものが最も強い) |
| 主な失敗 | 判断役が実行に沈む | 過剰委譲・過剰検証 |
| コスト削減の第一手 | 実行を下位モデルへ流す | effort を下げる(medium まで)。high が要る段は Fable medium へ |

メインが Sonnet 以下なら、このスキルの委譲設計は基本的に不要。流す先がない。

**Fable の制約はドル単価ではなく、別枠の週次リミット。** タスク単位のコストでは Fable medium のほうが Opus high より安くて賢い(Artificial Analysis 2026-09: Index 49 / $2.98 対 48 / $3.61)。それでも Fable の実行を下位モデルへ流すのは、Fable の週次リミットが他モデルと別枠で有限だから。Fable の枠は判断と、Opus high が要るほどの難所にだけ使い、日常の実行は Opus low で回す。

**書く量でコストが決まる。** 出力トークンは入力トークンの数倍の単価なので、メインが Fable のときのコストを支配するのは読んだ量ではなく**書いた量**。読んで判断すること自体は Fable に残してよいが、まとまった量の書き出し(実装、ドキュメント、長いファイル生成、複数ファイル編集)は Opus low に書かせる。数行の修正や一言の追記のように、ブリーフを書くほうが長くなる短い書き込みはそのままメインでやる。

姿勢の根拠、各判断の理由、Fable へのエスカレーション基準は [references/delegation-triage.md](references/delegation-triage.md) を読む。

## 2. モデルの役割分担

モデルと effort は一体で選ぶ。同じ Index 帯なら安い組み合わせがあり、逆に「同じか安いコストでより賢い組み合わせ」が存在する effort は選ぶ理由がない。

| タスクの性質 | モデル × effort |
|---|---|
| 要件解釈・設計・トレードオフ判断・分解と委譲設計・最終レビュー | メイン(委譲しない) |
| 難しい実装(複数ファイル機能、大きなリファクタ、e2e)、コードレビュー/バグ発見、散在情報の統合・整理、仕様に曖昧さが残る作業 | **Fable medium**(Fable の別枠が尽きた週は Opus medium、難所だけ Opus high)。メインが Opus なら自分で実行 |
| 実行の既定: 日常の実装・調査、仕様が確定した実装、機械的作業(コミット、PR 作成、CI を通す、テスト追加、一括置換) | **Opus low**(Sonnet medium より消費 1.1 倍で Index は 28 → 39) |
| よほど単純な作業: 大量に読んで集めるだけの広範な定型調査、判断を含まない一括処理 | **Sonnet low** |
| 判断を含まない探索・整形・列挙 | Haiku |

判断基準: **実行は Opus low が既定。判断が一切なく、読んで集める・並べるだけなら Sonnet low。仕様に穴が残る・レビュー・統合なら Fable medium**。Sonnet medium は Opus low とほぼ同コストで大きく劣るので使わない。「安いモデルに投げたが仕様が足りず聞き返された」は一段上に投げるべきだった合図。本当に難しいときだけ Fable high。

**選ばない組み合わせ**(2026-09 の Artificial Analysis Intelligence Index v4.3.2 × Cost per Task で、同じか安いコストにより賢い選択肢がある): Sonnet medium 以上(Opus low が +$0.10 で Index +11。Sonnet は low だけ)、Opus high / xhigh / max(Fable medium / high に負ける。Fable 枠切れ時の難所向け Opus high だけ例外)、Fable max(xhigh と同 Index で高いだけ)。Fable xhigh は high から Index +2 で約 $2 増える崖なので、通常は使わない。出典と数値の詳細は `~/ghq/github.com/tomada1114/iobsidian/Content/_material/claude-model-effort-cost-performance.md`。

**effort の指定先:** Agent ツールは `model` しか取らず、サブエージェントの effort は settings.json の `modelSettings`(opus low / sonnet low / fable medium)が既定になる。この既定がそのまま上の表の段になっている。Workflow の `agent()` は段ごとに `effort` を取る。Fable high はメインの `/effort` か Workflow でしか指定できない。

**この表と判断基準が正本。** creating-agent-skills(スキル作成時に新スキルへ焼き込む表)と各ワークフロースキル(shipping-issues、refining-prompts 等)のモデル割当は、ここからの派生コピー。改訂はまずここで行い、`grep -rl 'derived from orchestrating-models' ~/.claude/skills` で派生先を洗い出して追随させる。

**ワークフロースキルへの焼き込み:** 実行のたびに結論が同じになる静的な割当(段ごとのモデル指定)は、対象スキルからこのスキルを実行時に参照させない。結論と分水嶺の 1 行(仕様確定度)を対象スキルへベタ書きし、由来を `<!-- derived from orchestrating-models §2 -->` で示す。実行時参照が見合うのは、結論が実行時の状況でしか決まらない判断だけ。

モデルごとの癖に合わせた委譲プロンプトの調整は [references/model-playbooks.md](references/model-playbooks.md) を読む。

## 3. 委譲トリアージ

| 状況 | 判断 |
|---|---|
| 数回のツール呼び出しで終わる | 自分でやる |
| 手順が直列で並列化の余地がない | 自分でやる |
| 読んだ内容を後の判断で使う | 自分でやる(委譲すると要約しか戻らない) |
| 仕様がまだ固まっていない | 自分で固める(固めるのがメインの仕事) |
| 自分の成果の検証 | 自分でやる(指示しなくても既定でやる) |
| 読む量は多いが、書くのは短い判断・指示だけ | 自分でやる(入力トークンは相対的に安い) |
| 数行の修正・一言の追記など、ブリーフより短い書き込み | 自分でやる |
| 独立した大きめのトラックが複数本 | 並列に委譲 |
| 大量に読むが読んだ内容自体は後で使わない | 委譲(コンテキスト隔離) |
| 仕様が確定した機械的作業(テスト追加、CI、コミット、PR、一括置換) | Opus low |
| 判断を含まない広範な定型調査・列挙・整形 | Sonnet low(さらに単純なら Haiku) |
| まとまった量の書き出し(実装、ドキュメント、長いファイル生成、複数ファイル編集) | メインが Fable なら下位に書かせる(既定は Opus low、穴が残るなら Fable medium) / メインが Opus なら自分でやる |
| 難しい実装・レビュー・散在情報の統合 | メインが Fable なら Fable medium のサブへ(枠切れ時は Opus medium) / メインが Opus なら自分でやる |
| Opus なら high に上げたくなる段(難所の実装・検証・判断) | Fable medium に振り替える。Opus high は Fable 枠切れ時だけ |
| 「何を作るべきか」自体が未確定 / 数時間以上の無人走行 | メインが Opus なら Fable medium へ |

**損益分岐:** 委譲のブリーフを書く時間が自分で実行する時間を上回るなら、委譲しない。メインが Fable のときはこの分岐点が委譲側に寄る(自分の実行コストが高いため)。分岐点を測る物差しは**書く量**。ブリーフより長いものを書くなら委譲、ブリーフより短いなら自分で書く。

メインが Fable のときは、この表で「自分でやる」に落ちたもの以外は原則すべて委譲する。1 タスクを「設計 → 実装 → 仕上げ」に割ったほうが、全部を 1 つの高性能モデルに投げるより安く速いことが多い。ただし本数は次で決める。

**サブエージェントはキャッシュを共有しない。** 入力が安いのはキャッシュの効いた**このセッション**の中だけで、新しいサブエージェントは文脈をゼロから作る。システムプロンプト・スキル本文・ブリーフを毎回キャッシュ**書き込み**価格(読み取りより高い)で払うので、同じ資料を 3 本に読ませれば資料代を割高な単価で 3 回払うことになる。メインなら 1 回の読み取りで済んだものだ。

**並列化が買うのは壁時計時間であって、トークンではない。** 本数を決める軸は「分けたら速いか」ではなく「読むものが重ならないか」。

| 状況 | 判断 |
|---|---|
| 読む対象が互いに素(別のファイル群・リポジトリ・調査対象) | 分ける |
| 全員が同じ資料を読む | 分けない。1 本に順でやらせるほうが安い |
| 段を重ねる(設計 → 実装 → 仕上げ) | 前段の**成果だけ**を次段に渡せるなら分ける。後段が同じ資料を読み直すなら分けた意味がない |

## 4. ワークフロー

### 未知を潰す(計画前)

不慣れなコードベース・新領域なら、計画の前に unknowns を洗い出す。手法(Blind Spot Pass / Interview / Brainstorm / implementation-notes.md)は [references/unknowns-discovery.md](references/unknowns-discovery.md) を読む。ここで書き下ろした仕様が、そのまま実行計画にも委譲ブリーフにもなる。仕様に穴が残ったまま先へ進めない。

### 分解して走らせる

タスクを自己完結する単位に分解し、単位ごとにモデルと実行手段を選ぶ。委譲プロンプトの必須要素、リレー編成、実行手段の選択は [references/delegation-patterns.md](references/delegation-patterns.md) を読む。

- 独立な単位は 1 レスポンスで並列起動する。ブロックせず走らせたまま次の設計(メインが Opus なら自分の担当作業)を進める
- `model` パラメータでモデルを明示する。Workflow の `agent()` なら `effort` も指定する
- 大規模・分解可能・検証重視なら Dynamic Workflow、無人完走型なら /goal(`authoring-goal-prompts`)へ

### 統合とレビュー

- サブエージェントからは要約(結論・変更点・未解決事項)だけ受け取り、生ログや全文 diff をメインのコンテキストへ戻さない
- 複数の調査結果を突き合わせて整理する作業自体を Opus に委譲してよい(メインが Fable のとき)
- 自分で実行した分と委譲分の整合を取り、報告の整合性・設計判断・逸脱(implementation-notes.md の Deviations)をレビューする
- 検証はサブエージェント側で完結させ、実行したコマンドと結果を報告させる。ただし Opus には検証手順そのものを指示しない(過剰検証になる)
- ユーザー向けの最終要約は結論から。作業中の略語を持ち込まず、長さは中身に見合わせる

## Critical Rules

- 委譲プロンプトに前提知識と**依頼の意図**を含め、サブエージェントに会話内容の再調査をさせない
- ユーザーとの要件確認・最終判断を委譲しない
- サブエージェントに「検証ステップを入れよ」「ダブルチェックせよ」と書かない。過剰検証になる <!-- audit-ignore: A006 -->
- 検出・レビューを委譲するとき「重大なものだけ」「保守的に」と書かない <!-- audit-ignore: A006 -->。忠実に絞られて取りこぼす。全件報告 + confidence/severity を付けさせ、選別は別段に置く
- 頼まれた範囲を、頼まれた粒度で。より良い方法があるなら一言添えたうえで依頼どおり進める
- 委譲先が Opus / Fable なら、その委譲先にもサブエージェント生成の上限を書く。放っておくと同じように乱発する
- 進捗を報告する前に、各主張をこのセッションのツール結果と突き合わせる。サブエージェントの報告を検証せずに転記しない
