---
name: orchestrating-models
description: >-
  Decide which model and effort runs a piece of work, and whether to delegate it
  at all. The canonical source for model assignment — the main session, the
  named sub-agents (executor, architect, scout, worker), and Workflow agent()
  stages. Use when starting a large task, deciding whether to delegate, picking
  a sub-agent tier or a Workflow stage's model and effort, or cutting token cost.
metadata:
  platforms: claude-code
---

# orchestrating-models

どのモデルに何をやらせるかを決めるための運用手順。メインセッションは Opus 5.5 high で、計画・判断・実行を自分で持つ。委譲先は仕事の形で 4 段に分かれる。確定仕様の機械的作業は Opus 5.5 medium の `executor`、ブリーフに書き出せる難所とレビューは Fable 5.2 high の `architect`、ファイルを書き換えない調べ物は Haiku 5.5 xhigh の `scout`、ツールを使わない一発の文章仕事は Sonnet 5.5 high の `worker`。安さだけで段を選ばない。難しい実装を low に渡して手戻りするほうが、最初から自分でやるより高くつく。

**使わない場面:** 会話的な質問への回答、単一ファイルの小さな編集、対話で細かく舵取りしたい作業。委譲のオーバーヘッドが本体コストを上回る。

## 1. 構成

| 役 | モデル × effort | 実現手段 |
|---|---|---|
| メインセッション | Opus 5.5 **high** | settings.json の `model` と `modelSettings.claude-opus-5-5.effortLevel` |
| 実行役サブエージェント | Opus 5.5 **medium** | 名前付きエージェント `executor`(`~/.claude/agents/executor.md`) |
| 難所担当サブエージェント | Fable 5.2 **high** | 名前付きエージェント `architect`(`~/.claude/agents/architect.md`) |
| 調べ物サブエージェント | Haiku 5.5 **xhigh** | 名前付きエージェント `scout`(`~/.claude/agents/scout.md`) |
| 文章仕事サブエージェント | Sonnet 5.5 **high** | 名前付きエージェント `worker`(`~/.claude/agents/worker.md`) |

**既定の姿勢は「自分でやる」。** Opus 5.5 は完全な仕様を最初に全部持ったまま走るときに一番よく働く。公式ガイドも、委譲の量はハーネスの文言しだいで増え、サブエージェントがセッション費用の大きな割合を占めうるとしている。委譲するのは §3 の理由があるときだけ。主な失敗は過剰委譲と過剰検証。

**大事な場面は Fable 5.2 high。** 文脈と切り離せるなら `architect` に渡し、切り離せないならメインのまま進める。会話の途中でメインの effort は変えない(プロンプトキャッシュが切れて、会話全体を入れ直す費用がかかるおそれがある)。

**委譲する価値があるのは、メインより安い段か、メインより賢い段だけ。** `executor`(Opus 5.5 medium)はメインの約 7 割の費用で済む段、`architect`(Fable 5.2 high)はメインより賢い段。メインと同格の段(Opus 5.5 high)は作らない。メインがやっても同じ品質で、委譲の固定費だけが余分にかかる。

**`architect` は高い。** 1 タスクあたりメイン(Opus 5.5 high)の約 2.6 倍かかる。渡すのは、メインでは落ちそうな難所、レビュー・バグ発見、散在情報の統合に限る。仕様が固まった複数ファイルの実装は、まとまった量なら `executor`、判断が残るならメインが自分で持つ。

**`scout` と `worker` は、仕事の形で選ぶ段で、賢さの段ではない。**

- **`scout`(Haiku 5.5 xhigh、いちばん安い段)** は、ファイルを書き換えない、判断を含まない調査・収集・列挙・要約。読むだけで成否が決まり、間違えても何も壊れない仕事。Anthropic 自身が Haiku 5.5 の用途に「狭い範囲のサブエージェント・要約・分類」を挙げ、複雑なエージェント型コーディングには Sonnet / Opus を勧めている。xhigh はユーザーの指定で、公式ガイドが low で早期停止や検索の省略を挙げていることとも整合する。プロンプトが 100k トークンを超えるとリクエスト全体の単価が 5 倍になるので、ブリーフは読む範囲を絞る
- **`worker`(Sonnet 5.5 high、メインの半分ほど)** は、完全なブリーフに 1 回の返答で答え、ツールを使わない仕事。仕様どおりの項目の書き出しや、書かれた基準での判定で、出力を後段の検査(lint・別レビュー・人)が受け止めるもの

費用と賢さの比は Artificial Analysis Intelligence Index × Cost per Task から(Fable 5.2 は v5.0.1・2026-11-10 取得、ほかは v5.0・2026-11-03 取得)。Fable の利用枠は Max プランの同一リミットの内数で、トークン単価は Opus 5.5 より高い。段ごとの数値と根拠は [references/model-playbooks.md](references/model-playbooks.md#effort-とコスト)、姿勢の根拠と分水嶺は [references/delegation-triage.md](references/delegation-triage.md) を読む。

## 2. 役割分担

| タスクの性質 | 担当 |
|---|---|
| 要件解釈・設計・トレードオフ判断・分解と委譲設計・ユーザーとの確認・最終レビュー、判断が残る実装 | メイン(委譲しない) |
| ブリーフに書き出せる難所(多段の推論が要る実装・原因究明)、コードレビュー/バグ発見、散在情報の統合 | **`architect`**(Fable 5.2 high) |
| 仕様が確定した実装、機械的作業(テスト追加、CI を通す、コミット、PR 作成、一括置換・整形) | **`executor`**(Opus 5.5 medium) |
| ファイルを書き換えない、判断を含まない調査・収集・列挙・要約(コード検索、条件に合う箇所の全件列挙、大量に読んで結論だけ返す、Web で事実を集める) | **`scout`**(Haiku 5.5 xhigh) |
| ツールを使わない一発の文章仕事: ブリーフだけから項目を書き出す、書かれた基準で項目を判定して決まった形式(JSON など)で返す。後段に検査があるもの | **`worker`**(Sonnet 5.5 high) |

判断基準は**仕様の確定度であって作業の大きさではない**。`executor` が「どういう意味か」と聞き返してきそうなら、仕様がまだ固まっていない合図で、メインが固めるか自分で実装する。難所だから一律に `architect` でもない。会話の文脈が要るなら、メインの effort を上げて自分でやる。

**選ばない組み合わせ:**

- Fable 5.2 の xhigh / max: xhigh は high と賢さが変わらず費用だけ増え、max はわずかな上積みに high の約 3 倍の費用がかかる。公式も「上積みを測って確かめたときだけ」としている
- Fable 5.2 の low / medium のサブエージェント: メインより少し賢いだけで、トークン単価が高く architect(high)ほどの差もないので作らない
- Opus 5.5 の xhigh / max: 使わない。Opus 5.5 high は名前付きサブには使わない(メインと同格)が、Workflow で多数並列に回す検出段の `'opus'` + `'high'` には使う([references/delegation-patterns.md](references/delegation-patterns.md#workflow-の段の割当))
- Sonnet 5.5 の high 以外、Fable 5.1・Opus 5・Sonnet 5 の全段
- ファイルを書き換えるエージェント作業に `worker` や `scout`: `scout` は書き込みツールを持たない。`worker` はツールなしの一発仕事に限る
- Haiku 5.5 の max: xhigh は `scout` に固定(ユーザー指定)。xhigh では複数ターンで本文が空のまま終わることがあるので、空の返答は再依頼する

**effort の届け方:** Agent ツールは `model` しか取らず effort を取らない。**`model: fable` や `model: opus` だけで起動すると、effort は `modelSettings` から決まり、段が崩れる。** 段は必ず `subagent_type: executor` / `architect` / `scout` / `worker` で指定する。定義の frontmatter が `model` と `effort` を持っている(`architect` は `claude-fable-5-2` + `high`、`executor` は `claude-opus-5-5` + `medium`、`scout` は `claude-haiku-5-5` + `xhigh`、`worker` は `claude-sonnet-5-5` + `high`)。組み込みの `Explore`・`Plan`・`general-purpose` は effort を持たずメインから引き継ぐので、委譲先には選ばない。Workflow の `agent()` は `model` と `effort` を段ごとに取るので、どちらも必ず添える。省くとメインのモデルと effort(Opus 5.5 high)を引き継ぐ。段ごとの当て方は [references/delegation-patterns.md](references/delegation-patterns.md#workflow-の段の割当) を読む。

**他スキルからの参照:** このスキルがモデル割当の正本。

- **グローバルスキル**(`~/.claude/skills`)は割当をコピーしない。段をエージェント名(`executor` / `architect` / `scout` / `worker`)で指し、選び方はこのスキルへのポインタで済ませる。`~/.claude/CLAUDE.md` の Model Roles も段を名前で指すだけで、モデル名と effort は書かない
- **リポジトリ**(公開リポジトリ、テンプレート、他人も使うもの)は、クラウドセッションと Codex がリポジトリ内の定義しか読まないので、段の定義ファイルを `.claude/agents/`(と `.codex/agents/`)に持つ。ただしそれは `syncing-agent-tiers` が正本 `assets/tiers.json` から生成して PR で配るコピーで、手で直さない。リポジトリの文章(AGENTS.md・CLAUDE.md・スキル)は段を名前と役割で指し、モデル名と effort を書かない。Workflow の `agent()` でモデルが要るなら、スキル内の 1 か所の定数にまとめる

モデルや effort を変えるときは、エージェント定義(`~/.claude/agents`)、このスキル、settings.json の `modelSettings`、`syncing-agent-tiers` の `tiers.json` を直し、`syncing-agent-tiers` で配る。取り残しは `grep -rln 'orchestrating-models' ~/.claude/skills ~/.claude/CLAUDE.md` と `grep -rlE 'model: *.?(sonnet|haiku|opus|fable)' ~/ghq/github.com/tomada1114/*/.claude/skills` で洗い出す。

段ごとの癖に合わせた委譲プロンプトの書き方は [references/model-playbooks.md](references/model-playbooks.md) を読む。

## 3. 委譲トリアージ

| 状況 | 判断 |
|---|---|
| 数回のツール呼び出しで終わる | 自分でやる |
| 手順が直列で並列化の余地がない | 自分でやる |
| 読んだ内容を後の判断で使う | 自分でやる(委譲すると要約しか戻らない) |
| 仕様がまだ固まっていない / 「何を作るべきか」自体が未確定 | 自分で固める(固めるのがメインの仕事) |
| 自分の成果の検証 | 自分でやる。検証用のサブエージェントを足さない |
| 数行の修正・一言の追記など、ブリーフより短い書き込み | 自分でやる |
| 独立した大きめのトラックが複数本 | 並列に委譲。各トラックを下の行で段に振る |
| 仕様が確定した機械的作業、まとまった量の書き出し(確定仕様の実装、ドキュメント、長いファイル生成、複数ファイル編集) | `executor`(メインの約 7 割の費用。文章を書かせる仕事は `worker` へ) |
| 大量に読むが読んだ内容自体は後で使わない | `scout`(コンテキスト隔離。書き換えが要るなら `executor`) |
| メインでは落ちそうな難所・レビュー・散在情報の統合で、ブリーフに書き出せるもの | `architect`(メインの約 2.6 倍。本数は最小限) |
| ファイルを書き換えない調査・収集・列挙・要約 | `scout`(100k トークン超で単価 5 倍) |
| ツールを使わず、1 回の返答で済む書き出し・判定を大量にこなす(後段に検査あり) | `worker` |
| 難所だが会話の文脈と切り離せない | 委譲せず、メインのまま進める(effort は変えない) |
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

タスクを自己完結する単位に分解し、単位ごとに段と実行手段を選ぶ。委譲プロンプトの必須要素、リレー編成、実行手段の選択、協調の形(結果だけ返すサブエージェントか、担当どうしが途中でやり取りする Agent Teams や共有ファイルか)の選び方は [references/delegation-patterns.md](references/delegation-patterns.md) を読む。

- 独立な単位は 1 レスポンスで並列起動する。ブロックせず走らせたまま自分の担当作業を進める
- Agent ツールでは `subagent_type` で段を指定する。Workflow の `agent()` なら `model` と `effort` を指定する
- 大規模・分解可能・検証重視なら Dynamic Workflow、無人完走型なら /goal(`authoring-goal-prompts`)へ

### 統合とレビュー

- サブエージェントからは要約(結論・変更点・未解決事項)だけ受け取り、生ログや全文 diff をメインのコンテキストへ戻さない
- 複数の調査結果を突き合わせて整理する作業は、読んだ中身を自分の判断で使わず、量が多いときに限って architect に委譲する
- 自分で実行した分と委譲分の整合を取り、報告の整合性・設計判断・逸脱(implementation-notes.md の Deviations)をレビューする
- 検証はサブエージェント側で完結させ、実行したコマンドと結果を報告させる。ただし検証手順そのものは指示しない(過剰検証になる)
- `architect` の要約は大きな変更を挙げるが小さな変更を落としやすい。コードを書き換えさせたら要約だけでなく diff を見る
- ユーザー向けの最終要約は結論から。作業中の略語を持ち込まず、長さは中身に見合わせる

## Critical Rules

- 委譲プロンプトに前提知識と**依頼の意図**を含め、サブエージェントに会話内容の再調査をさせない
- ユーザーとの要件確認・最終判断を委譲しない
- 段は `subagent_type` で指定する。`model` だけの起動は effort が `modelSettings` から決まり、段が崩れる
- サブエージェントに「検証ステップを入れよ」「ダブルチェックせよ」と書かない。過剰検証になる <!-- audit-ignore: A006 -->
- 検出・レビューを委譲するとき「重大なものだけ」「保守的に」と書かない <!-- audit-ignore: A006 -->。忠実に絞られて取りこぼす。全件報告 + confidence/severity を付けさせ、選別は別段に置く
- 頼まれた範囲を、頼まれた粒度で。より良い方法があるなら一言添えたうえで依頼どおり進める
- 委譲先にもサブエージェント生成の上限を書く。executor / architect の定義本文にも入れてあるが、ブリーフで本数を指定する
- ブリーフに慎重さを積まない。Fable 5.2 は「絶対に〜するな」「最初のエラーで止まれ」を書かれたとおりに守り、必要のない確認待ちや手控えになる。禁止を書くなら対象の操作を名指しし、理由と例外(「〜の前に確認を取る」)を同じ文に入れる。再試行してよい操作は再試行してよいと書く
- 続行や承認を伝えるときは中身を言う。「続けて」ではなく「ステージングで migration を実行して」
- 進捗を報告する前に、各主張をこのセッションのツール結果と突き合わせる。サブエージェントの報告を検証せずに転記しない
