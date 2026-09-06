---
name: refining-prompts
description: "Polish a rough instruction (often dictated by voice) into a precise prompt that can be handed straight to another agentic coding session (Claude Code, Codex CLI, etc.), and print it in the CLI as a single code block (no file is saved). Runs a light scouting pass with a Sonnet sub-agent only when needed, and questions the user only when needed; the investigating and the thinking are deliberately left as work for the receiving session. When the user wants a /goal prompt for an unattended run, use authoring-goal-prompts instead. Use when the user asks to write a prompt for Claude Code or Codex CLI, turn something into a prompt, tidy up or sharpen an instruction, produce a prompt to hand to another session, or dictates a rough wish or problem and wants a polished instruction. Examples: <example>user: 'Make me a prompt for another session about this design' assistant: 'I will build it with the refining-prompts skill'</example>"
allowed-tools: Read, Grep, Glob, Bash, Agent, AskUserQuestion
argument-hint: "[rough instruction, thing to talk through, or problem to solve]"
metadata:
  platforms: claude-code, codex
---
<!-- prompt-lint-ignore-file: P004 -->

# Prompt Refiner

雑多な口述指示を、別のエージェント型コーディングセッション（Claude Code や Codex CLI 等）に渡す
1 個の完成プロンプトに磨き上げる。
成果物は **CLI に出力するコードブロックだけ**。ファイルは作らない。タスク自体も実行しない。

**このスキルを使わない場面:** 無人自走させる `/goal` 用プロンプト（→ `authoring-goal-prompts`）、
このセッション内でそのまま作業した方が早いタスク。

## 前提

1. **入力は音声認識由来** — 誤変換・言い淀みを含みうる。意図を好意的に補って解釈する。
2. **渡し先は文脈ゼロの新しいセッション** — この会話でだけ存在する情報（ユーザーの決定、制約、
   経緯、却下された案）は、プロンプトに書かない限り失われる。
3. **渡し先は同格の「考える相手」** — 調べること・設計を決めること・検証することは渡し先の仕事。
   ここで結論まで出して手順書を渡すのではなく、良い問いと正しい入口を渡す。
   （`authoring-goal-prompts` は逆の設計思想。無人・弱いモデル向けに判断を前倒しして潰す。混同しない）
4. **調査は「当たり付け」であって前倒しではない** — 受け手が同じ場所を調べ直すのは正常で歓迎。
   トークンや時間の節約はこのスキルの目的ではない。目的はプロンプトが的を外さないこと
   （正しい語彙・正しい入口・見落としやすい注意点）と、受け手が実際に調べて考えるよう仕向けること。
5. **渡し先は現行世代のモデル** — 旧世代向けの定型句（再検証の強制、重要度フィルタ、思考過程の要求、
   `CRITICAL: MUST` 系の強調）は現在は逆効果。→ [references/prompt-patterns.md](references/prompt-patterns.md)

プロンプトの言語は入力に合わせる（日本語の指示なら日本語のプロンプト）。

## ワークフロー

### 1. 意図の把握

指示をどの型として磨くかをまず判定する。型が違うと重心も、受け手に許す行動も変わる。

| 型 | ユーザーの状態 | プロンプトの重心 | 受け手の行動 |
|---|---|---|---|
| 作業依頼 | やってほしいことが決まっている（例: CI を直して） | 目的・現状の観測・完了の目安 | 実装まで |
| 設計・計画 | 作りたいが設計から考えてほしい | 背景・要件・制約。設計判断は委ねる | 案と推奨（実装前に合意） |
| 調査・原因究明 | 症状はあるが原因が不明 | 症状・再現手順・調査済みの範囲・成功条件 | 複数仮説と確信度 |
| 相談・壁打ち | 具体像はなく、課題や悩みがある | 問題の状況説明、期待する関わり方 | 提案 → 議論（編集しない） |

### 2. 当たり付けの調査（必要なときだけ）

対象プロジェクトの実態でプロンプトの**向き**が変わるときだけ調査する。汎用的な相談はスキップ。

この調査は、委譲できる環境では Sonnet の worker（読むだけなら Explore）に委譲する
<!-- derived from orchestrating-models §2 -->。委譲できない環境では逐次インラインで行う
（[references/platform-notes.md](references/platform-notes.md)）。

いずれの場合も、受け取る（残す）のは要約だけ: 関連パス、現状の挙動・エラー、既存の慣習。
ログ全文や全文 diff は戻させない（該当するエラー文の原文は数行なら可）。
- **拾うもの**（受け手を正しい入口に立たせるもの）: 実ファイルパスと `path:line`、エラー文の原文、
  そのプロジェクト固有の語彙・命名、既存の慣習、既に存在する類似実装、そして
  「ここは自明でない／罠がある」という気づき。最後のものが一番価値が高い。
- **拾わないもの**: 網羅的な現状説明、設計案、原因の断定。受け手の仕事を先取りすると質が落ちる。
- 得た事実は**観測として**書く（「調査時点ではこうだった」）。裏取りは受け手に任せる。
  当たりが外れていても、受け手が自力で調べ直せる形なら害は小さい。

### 3. ヒアリング（必要なときだけ）

調査と推測で埋まらない本質的な分岐（目的そのもの、スコープ境界、成果物の形）だけ確認する。

本質的な分岐だけ、選択肢と推奨を添えて聞く。相談系は数ラウンドの対話も可。
推測で足りる細部は聞かない。

**ユーザーが実際に決めたことは「決定事項」、こちらの推測は「仮説」として書き分ける。**
推測を決定として書くと、受け手はそこを検討しなくなる。

### 4. 起草

**長すぎず、限定しすぎず。** 目的・制約・完了の形を固定し、手段と判断は受け手に委ねる。
ステップバイステップの手順書やマイクロマネジメントはしない。

初回起草の前に [references/prompt-patterns.md](references/prompt-patterns.md) を読む
（効く書き方・入れてはいけない定型句・受け手に調べさせる書き方・完成例）。

次の要素から **信号があるものだけ** を使って組み立てる（全部使う必要はない）:

- **目的** — 何を達成したいか・なぜ。1〜3 文。理由を書くと受け手が状況に合わせて判断できる。
- **背景・現状** — 調査で得た観測（パス、エラー、既存慣習）と、会話でしか知り得ない文脈。
- **依頼内容** — やってほしいことを**動詞で明示**する。実装させたいなら「実装して」、
  提案止まりなら「案と推奨を出して、ファイルは編集しないで」。「改善できる?」は提案で止まる。
- **受け手にやらせる調査・検討** — この会話で結論が出ていない部分は、答えではなく問いとして残す。
  事実関係が結論を左右する依頼には「開いていないコードについて推測せず、関連ファイルを読んでから
  答えて」を入れる。原因不明の調査依頼なら「対立する仮説を複数立て、確信度を付けて報告して」。
- **制約・スコープ** — 触らない範囲、守る慣習、明確な NG。少数精鋭。適用範囲は明示的に書く
  （受け手は文字通り読む。「全セクションに適用、最初だけではない」は冗長ではない）。
- **成果物・完了の目安** — 何が出てきたら成功か。作業依頼では検証方法も一言。
- **不明時の挙動** — 「不明点や大きな分岐は進める前にユーザーに確認して」を入れる。確認手段の
  書き分けは [references/platform-notes.md](references/platform-notes.md) を参照。

貼り付ける長い材料（エラーログ、コード抜粋、仕様の断片）があるならプロンプトの**上部**に置き、
依頼を末尾にする。材料と指示が混ざるなら見出しか XML タグ（`<error_log>` 等）で区切る。

長さの目安は 15〜40 行。超えて膨らむなら、細部を固定しすぎているか、受け手が自分で調べれば
済む事実を詰め込んでいるサイン。

### 5. 出力

プロンプト全体を **1 個の markdown コードブロック** で出力する（そのままコピペできる形）。
出力はコードブロック 1 個で完結させる。伝えたい留意点はプロンプト本文に入れる。
コピペした新セッションが、追加の前提なしで動き出せる形にする。

## Platform notes

詳細は [references/platform-notes.md](references/platform-notes.md) を参照。
