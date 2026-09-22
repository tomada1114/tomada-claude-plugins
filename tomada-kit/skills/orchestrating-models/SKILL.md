---
name: orchestrating-models
description: >-
  Playbook for choosing models and deciding what to delegate. Everything runs on
  Opus 5.5: the main session at medium executes directly by default and delegates
  only independent parallel tracks, mechanical work, context isolation, and hard
  stages that can be briefed standalone. Sub-agents come in exactly two tiers,
  the named agents `executor` (Opus 5.5 low: settled spec, mechanical work,
  judgment-free research) and `architect` (Opus 5.5 high: complex implementation,
  design judgment, review, synthesis); no medium sub-agent. Covers why other
  models are dominated, how effort reaches a spawn, delegation prompts, relay
  formations, Opus 5.5 quirks, spawn cache cost, and surfacing unknowns. The
  canonical source other skills point to for model assignment. Use when
  starting a large task, when deciding whether to delegate, when choosing an
  effort level or a sub-agent tier, or when asked to cut token cost.
metadata:
  platforms: claude-code
---

# orchestrating-models

どのモデルに何をやらせるかを決めるための運用手順。モデルは Opus 5.5 だけを使い、段は effort で分ける。安さだけで段を選ばない。難しい実装を low に渡して手戻りするほうが、最初から high に渡すより高くつく。

**使わない場面:** 会話的な質問への回答、単一ファイルの小さな編集、対話で細かく舵取りしたい作業。委譲のオーバーヘッドが本体コストを上回る。

## 1. 構成

| 役 | モデル × effort | 実現手段 |
|---|---|---|
| メインセッション | Opus 5.5 **medium** | settings.json の `model` と `modelSettings.claude-opus-5-5.effortLevel` |
| 実行役サブエージェント | Opus 5.5 **low** | 名前付きエージェント `executor`(`~/.claude/agents/executor.md`) |
| 難所担当サブエージェント | Opus 5.5 **high** | 名前付きエージェント `architect`(`~/.claude/agents/architect.md`) |

**既定の姿勢は「自分でやる」。** Opus はコーディングとエージェント作業そのものが最も強く、仕様を全部持ったまま走るときに一番よく働く。委譲するのは §3 の 4 つの理由があるときだけ。主な失敗は過剰委譲と過剰検証。

**サブエージェントは low と high の 2 段だけ。** メインが medium なので、委譲を決めた時点で「仕様確定済み・機械的なら low、複雑・設計判断を含む・レビューなら high」の二択で足りる。medium のサブを作るくらいならメインがやる。

**Fable 5.1・Opus 5・Sonnet 5・Haiku は使わない。** Artificial Analysis Intelligence Index v4.3.2 × Cost per Task(2026-09-22 取得)でパレート最適なのは Sonnet 5 low と Opus 5.5 の low / medium / high / xhigh / max の 6 つだけで、Fable 5.1 と Opus 5 は全段が劣位。Sonnet 5 low は Opus 5.5 low より $0.04 安いだけで Index が 24 対 42 なので、残す理由がない。Fable の利用枠は Max プランの同一リミットの内数で、別枠ではない。数値の詳細は [references/model-playbooks.md](references/model-playbooks.md#effort-とコスト) と出典ノート `~/ghq/github.com/tomada1114/iobsidian/Content/_material/claude-model-effort-cost-performance.md`。

姿勢の根拠、委譲する理由ごとの判断、executor と architect の分水嶺は [references/delegation-triage.md](references/delegation-triage.md) を読む。

## 2. 役割分担

| タスクの性質 | 担当 |
|---|---|
| 要件解釈・設計・トレードオフ判断・分解と委譲設計・ユーザーとの確認・最終レビュー | メイン(委譲しない) |
| 複雑な実装(複数ファイルにまたがる機能、大きなリファクタ、e2e、非自明なアルゴリズム)、設計判断を含む作業、コードレビュー/バグ発見、散在情報の統合、仕様に穴が残る作業 | **`architect`**(Opus 5.5 high) |
| 仕様が確定した実装、機械的作業(テスト追加、CI を通す、コミット、PR 作成、一括置換・整形)、判断を含まない調査・収集・列挙 | **`executor`**(Opus 5.5 low) |

判断基準は**仕様の確定度であって作業の大きさではない**。委譲先が「どういう意味か」と聞き返してきそうなら、それは architect に渡すべきだった合図。実装だからといって一律に executor ではない。既存パターンの反復なら executor、どこかで設計判断が要るなら architect。

**選ばない組み合わせ:**

- Fable 5.1 の全段、Opus 5 の全段: 同じか安いコストで Opus 5.5 がより賢い(例: Fable xhigh 53 / $5.98 は Opus 5.5 max 58 / $5.98 と同額で Index が 5 低く、Opus 5.5 high 54 / $1.82 にも負ける)
- Sonnet 5 の全段: low も含めて使わない(上記)。Haiku も同様に使わない
- サブエージェントの medium: 2 段構成の設計上作らない
- サブエージェントの xhigh / max: high → xhigh は +2pt に +$1.64、xhigh → max は +2pt に +$2.52 の崖。high までの限界コスト($0.16/pt)の 5〜8 倍になる

**effort の届け方:** Agent ツールは `model` しか取らず effort を取らない。**`model: opus` だけで起動すると、サブエージェントは `modelSettings` の Opus 5.5 = medium で走る**(2 段構成が崩れる)。段は必ず `subagent_type: executor` / `architect` で指定する。定義の frontmatter が `model: claude-opus-5-5` と `effort: low` / `high` を持っている。組み込みの `Explore`・`Plan`・`general-purpose` は effort を持たずメインから引き継ぐので、委譲先には選ばない。Workflow の `agent()` は `model` と `effort` を段ごとに取るので、`model: 'opus'` に `effort: 'low'` か `'high'` を必ず添える。

**他スキルからの参照:** このスキルがモデル割当の正本。

- **グローバルスキル**(`~/.claude/skills`)と `~/.claude/CLAUDE.md` は割当をコピーしない。段をエージェント名(`executor` / `architect`)で指し、選び方はこのスキルへのポインタで済ませる。モデルや effort を変えるときは、エージェント定義とこのスキルだけを直せばよい
- **リポジトリ内のスキル**で単体で動く必要があるもの(公開リポジトリ、他人も使うもの)は、結論と分水嶺をベタ書きして `<!-- derived from orchestrating-models §2 -->` を付け、同じ 2 本のエージェント定義を `.claude/agents/` に同梱する

改訂したら `grep -rln 'orchestrating-models' ~/.claude/skills ~/.claude/CLAUDE.md` でポインタ側、`grep -rl 'derived from orchestrating-models' ~/ghq/github.com/tomada1114` でベタ書き側を洗い出して追随させる。

Opus 5.5 の癖に合わせた委譲プロンプトの書き方は [references/model-playbooks.md](references/model-playbooks.md) を読む。

## 3. 委譲トリアージ

| 状況 | 判断 |
|---|---|
| 数回のツール呼び出しで終わる | 自分でやる |
| 手順が直列で並列化の余地がない | 自分でやる |
| 読んだ内容を後の判断で使う | 自分でやる(委譲すると要約しか戻らない) |
| 仕様がまだ固まっていない / 「何を作るべきか」自体が未確定 | 自分で固める(固めるのがメインの仕事) |
| 自分の成果の検証 | 自分でやる(指示しなくても既定でやる) |
| 数行の修正・一言の追記など、ブリーフより短い書き込み | 自分でやる |
| 独立した大きめのトラックが複数本 | 並列に委譲。各トラックを下の 2 行で executor / architect に振る |
| 仕様が確定した機械的作業、まとまった量の書き出し(確定仕様の実装、ドキュメント、長いファイル生成、複数ファイル編集) | `executor`(low は medium の半額以下: $0.55 対 $1.34/task) |
| 大量に読むが読んだ内容自体は後で使わない | `executor`(コンテキスト隔離) |
| 難しい実装・レビュー・散在情報の統合で、ブリーフに書き出せるもの | `architect` |
| 難所だが会話の文脈と切り離せない | 委譲せず、メインの `/effort` を一時的に high へ上げる |
| 数時間以上の無人走行 | /goal(`authoring-goal-prompts`)へ |

**損益分岐:** 委譲のブリーフを書く時間が自分で実行する時間を上回るなら、委譲しない。物差しは**書く量**。出力トークンは入力の数倍の単価なので、ブリーフより長いものを書くなら executor に書かせ、ブリーフより短いなら自分で書く。

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

タスクを自己完結する単位に分解し、単位ごとに段と実行手段を選ぶ。委譲プロンプトの必須要素、リレー編成、実行手段の選択は [references/delegation-patterns.md](references/delegation-patterns.md) を読む。

- 独立な単位は 1 レスポンスで並列起動する。ブロックせず走らせたまま自分の担当作業を進める
- Agent ツールでは `subagent_type` で段を指定する。Workflow の `agent()` なら `model` と `effort` を指定する
- 大規模・分解可能・検証重視なら Dynamic Workflow、無人完走型なら /goal(`authoring-goal-prompts`)へ

### 統合とレビュー

- サブエージェントからは要約(結論・変更点・未解決事項)だけ受け取り、生ログや全文 diff をメインのコンテキストへ戻さない
- 複数の調査結果を突き合わせて整理する作業は、読んだ中身を自分の判断で使わないなら architect に委譲してよい
- 自分で実行した分と委譲分の整合を取り、報告の整合性・設計判断・逸脱(implementation-notes.md の Deviations)をレビューする
- 検証はサブエージェント側で完結させ、実行したコマンドと結果を報告させる。ただし検証手順そのものは指示しない(過剰検証になる)
- ユーザー向けの最終要約は結論から。作業中の略語を持ち込まず、長さは中身に見合わせる

## Critical Rules

- 委譲プロンプトに前提知識と**依頼の意図**を含め、サブエージェントに会話内容の再調査をさせない
- ユーザーとの要件確認・最終判断を委譲しない
- 段は `subagent_type` で指定する。`model` だけの起動は medium で走る
- サブエージェントに「検証ステップを入れよ」「ダブルチェックせよ」と書かない。過剰検証になる <!-- audit-ignore: A006 -->
- 検出・レビューを委譲するとき「重大なものだけ」「保守的に」と書かない <!-- audit-ignore: A006 -->。忠実に絞られて取りこぼす。全件報告 + confidence/severity を付けさせ、選別は別段に置く
- 頼まれた範囲を、頼まれた粒度で。より良い方法があるなら一言添えたうえで依頼どおり進める
- 委譲先にもサブエージェント生成の上限を書く。executor / architect の定義本文にも入れてあるが、ブリーフで本数を指定する
- 進捗を報告する前に、各主張をこのセッションのツール結果と突き合わせる。サブエージェントの報告を検証せずに転記しない
