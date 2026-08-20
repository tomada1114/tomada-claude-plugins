---
name: orchestrating-models
description: "Playbook for choosing models and deciding what to delegate. The default posture flips with the main model: when the main model is Fable, concentrate on judgment and push execution to Opus/Sonnet/Haiku; when it is Opus, execute directly by default and delegate only independent parallel tracks, mechanical work, and context isolation. Covers per-model role assignment, the required elements of a delegation prompt, relay formations, wording tuned to each model's quirks, and techniques for surfacing unknowns. Use PROACTIVELY when starting a large task, a multi-file implementation, or broad research, or when the user asks to work efficiently, save tokens, cut cost, orchestrate, delegate, use sub-agents, or wonders whether to do the work directly or hand it off. Examples: <example>user: 'Should I hand this to a sub-agent?' assistant: 'I will decide with the delegation triage in orchestrating-models'</example>"
---

# orchestrating-models

どのモデルに何をやらせるかを決めるための運用手順。安さだけでモデルを選ばない。難しい実装を安いモデルに渡して手戻りするほうが、最初から Opus に渡すより高くつく。

**使わない場面:** 会話的な質問への回答、単一ファイルの小さな編集、対話で細かく舵取りしたい作業。委譲のオーバーヘッドが本体コストを上回る。

## 1. 姿勢を決める(最初にやること)

このセッションのメインモデルを確認し、既定姿勢を選ぶ。ここを間違えると以降の判断がすべてずれる。

| | メインが Fable | メインが Opus |
|---|---|---|
| 既定 | **委譲する**(単価が高く、価値は判断の質にある) | **自分でやる**(実行そのものが最も強い) |
| 主な失敗 | 判断役が実行に沈む | 過剰委譲・過剰検証 |
| コスト削減の第一手 | 実行を下位モデルへ流す | effort を下げる |

メインが Sonnet 以下なら、このスキルの委譲設計は基本的に不要。流す先がない。

姿勢の根拠、各判断の理由、Fable へのエスカレーション基準は [references/delegation-triage.md](references/delegation-triage.md) を読む。

## 2. モデルの役割分担

| タスクの性質 | モデル |
|---|---|
| 要件解釈・設計・トレードオフ判断・分解と委譲設計・最終レビュー | メイン(委譲しない) |
| 難しい実装(複数ファイル機能、大きなリファクタ、e2e)、コードレビュー/バグ発見、散在情報の統合・整理、仕様に曖昧さが残る作業 | Opus(メインが Opus なら自分で実行) |
| 仕様が確定した実装、成否が明確な機械的作業(コミット、PR 作成、CI を通す、テスト追加、一括置換)、定型的な情報収集 | Sonnet |
| 判断を含まない探索・整形・列挙 | Haiku |

判断基準: **仕様が確定していれば Sonnet、仕様に穴が残るなら Opus**。「安いモデルに投げたが仕様が足りず聞き返された」は Opus に投げるべきだった合図。

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
| 独立した大きめのトラックが複数本 | 並列に委譲 |
| 大量に読むが読んだ内容自体は後で使わない | 委譲(コンテキスト隔離) |
| 仕様が確定した機械的作業(テスト追加、CI、コミット、PR、一括置換) | Sonnet |
| 判断を含まない列挙・整形 | Haiku |
| 難しい実装・レビュー・散在情報の統合 | メインが Fable なら Opus へ委譲 / メインが Opus なら自分でやる |
| 「何を作るべきか」自体が未確定 / 数時間以上の無人走行 | メインが Opus なら Fable へエスカレーション(まれ) |

**損益分岐:** 委譲のブリーフを書く時間が自分で実行する時間を上回るなら、委譲しない。メインが Fable のときはこの分岐点が委譲側に寄る(自分の実行コストが高いため)。

メインが Fable のときは、この表で「自分でやる」に落ちたもの以外は原則すべて委譲する。サブエージェントの数を惜しまない。1 タスクを「設計 → 実装 → 仕上げ」に割ったほうが、全部を 1 つの高性能モデルに投げるより安く速いことが多い。

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
- 委譲先が Opus なら、その Opus にもサブエージェント生成の上限を書く。放っておくと同じように乱発する
- 進捗を報告する前に、各主張をこのセッションのツール結果と突き合わせる。サブエージェントの報告を検証せずに転記しない
