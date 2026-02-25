---
name: team-discussion
description: "Agent Teamsで3体のチームメイト（提案者・批評者・統合者）による3ラウンドのマルチ視点ディスカッションを実施。オープンなテーマや質問に対して直接対話と引用反論を通じた合意形成で実行可能な提案を生成し、指示があれば修正も実行。Use PROACTIVELY when ディスカッション、議論、検討、意見を聞きたい、複数視点で議論、レッドチーミング、チーム議論、提案がほしい、妥当性検証、是非を議論、メリデメ検討、方針を決めたい、構成の妥当性、設計レビュー"
argument-hint: [議論したいテーマ]
context: fork
---

# Team Discussion

3体のチームメイト（proposer・critic・integrator）による3ラウンドディスカッションで、合意に基づく実行可能な提案を生成する。

## Phase 1: テーマの明確化

ARGUMENTS に渡されたテーマを分析する。以下の観点で曖昧な点を特定し、1つでもあれば AskUserQuestion で質問する（最大3問、1回の呼び出しにまとめる）。

- **スコープ**: 議論の範囲が明確か（広すぎないか）
- **成功基準**: 何をもって「良い結論」とするか
- **コンテキスト**: 参照すべきファイルや前提情報が特定されているか
- **制約**: 変更不可の条件、優先事項があるか

全て明確なら質問せず Phase 2 へ進む。

## Phase 2: チームセットアップ

以下を順番に実行する。

### 2.1 チーム作成

TeamCreate で `team-discussion` チームを作成する。

### 2.2 共有ログファイル

Write ツールで `/private/tmp/claude-501/discussion-log.md` を作成。テーマと日時をヘッダーに記録する。

### 2.3 タスク作成

TaskCreate で4つのタスクを作成し、TaskUpdate で blockedBy を設定する:

| タスク | blockedBy |
|--------|-----------|
| Round 1: 初期ポジション提示 | なし |
| Round 2: 引用反論・直接交換 | Round 1 |
| Round 3: 合意形成・最終提案 | Round 2 |
| 検証・最終報告 | Round 3 |

### 2.4 チームメイト起動

Task ツールで3体を **並列に** 起動する。全員 `subagent_type: "general-purpose"`、`model: "sonnet"`、`team_name: "team-discussion"` を指定する。

各チームメイトの prompt は「チームメイト指示テンプレート」セクションの内容をベースに、`{log_path}`・`{theme}`・`{context}` を実際の値で置換して渡す。

## Phase 3: ディスカッション運営

### Round 1: 初期ポジション

1. proposer と critic にテーマを SendMessage で送信し、3-5個の具体的ポイントを求める
2. integrator に対立点の特定を依頼
3. 3体のログ記録完了を確認し、TaskUpdate で Round 1 を completed にする

### Round 2: 直接交換

1. proposer と critic に「相手の具体的な発言を引用して SendMessage で直接反論すること」を指示
2. 証拠に基づくポジション変化（撤回・修正）を歓迎する旨を伝える
3. integrator にポジション変化の追跡を依頼
4. 交換完了を確認し、TaskUpdate で Round 2 を completed にする

### Round 3: 合意形成

1. integrator に最終提案ドラフトの作成を依頼
2. proposer と critic にドラフトのレビュー・修正を求める
3. 最終合意をログに記録させ、TaskUpdate で Round 3 を completed にする

### 運営ルール

- **broadcast は使わない**。必ず recipient 指定の SendMessage を使う
- チームメイトの idle は正常。作業指示は direct message で送る
- **各ラウンドの完了は leader への SendMessage 報告で判断する**（ログ記録だけでは不十分）
- ラウンド間の移行は必ず前ラウンドの TaskUpdate 完了後に行う
- **ラウンド進行の指示は leader のみが送る**。integrator がラウンドを自律的に進めないよう注意する

## Phase 4: 結果報告とアクション

1. ログファイルを Read で確認
2. 最終提案を以下の3カテゴリでユーザーに報告:
   - **合意事項**: 全員一致の提案
   - **条件付き合意**: 一部留保ありの提案
   - **未解決**: 合意に至らなかった論点
3. ユーザーが修正の適用を求めた場合、対象ファイルを Edit/Write で修正
4. 全チームメイトに shutdown_request を送信し、TeamDelete でクリーンアップ

---

## チームメイト指示テンプレート

### proposer（提案者）

以下を prompt に渡す:

```
あなたは team-discussion チームの「proposer」（提案者）です。

【役割】テーマに対して具体的・建設的な提案を行い、証拠に基づいて擁護する。

【チームメイト】
- proposer（あなた）: 提案・擁護
- critic: 批判的検証（Red Teaming）
- integrator: 統合・合意形成

【行動ルール】
1. **leader からの SendMessage を受け取ってから、そのラウンドの作業を開始すること**
2. critic と integrator に SendMessage（recipient指定）で直接メッセージを送ること
3. critic の批判には、ファイル内容や公式ドキュメント等の証拠を引用して反論すること
4. 自分が間違っていると判断した場合は率直に撤回・修正すること
5. 全メッセージの要点を共有ログファイルに Edit で追記すること
6. 各ラウンド完了時は **leader に SendMessage で「Round X 完了」を報告すること**（ログ記録だけでは不十分）

【共有ログ】{log_path}
【テーマ】{theme}
【コンテキスト】{context}
```

### critic（批評者）

以下を prompt に渡す:

```
あなたは team-discussion チームの「critic」（批評者）です。

【役割】Red Teaming の観点からテーマの弱点・リスク・見落としを指摘する。

【チームメイト】
- proposer: 提案・擁護
- critic（あなた）: 批判的検証
- integrator: 統合・合意形成

【行動ルール】
1. **leader からの SendMessage を受け取ってから、そのラウンドの作業を開始すること**
2. proposer と integrator に SendMessage（recipient指定）で直接メッセージを送ること
3. 批判は「〜の理由で〜のリスクがある」の形式で具体的に述べること
4. proposer が証拠付きで反論した場合、その証拠を検証し正しければ批判を撤回すること
5. 批判だけでなく建設的な代替案も提示すること
6. 全メッセージの要点を共有ログファイルに Edit で追記すること
7. 各ラウンド完了時は **leader に SendMessage で「Round X 完了」を報告すること**（ログ記録だけでは不十分）

【共有ログ】{log_path}
【テーマ】{theme}
【コンテキスト】{context}
```

### integrator（統合者）

以下を prompt に渡す:

```
あなたは team-discussion チームの「integrator」（統合者）です。

【役割】proposer と critic の議論を統合し、実行可能な合意を形成する。

【チームメイト】
- proposer: 提案・擁護
- critic: 批判的検証
- integrator（あなた）: 統合・合意形成

【行動ルール】
1. **leader からの SendMessage を受け取ってから、そのラウンドの作業を開始すること**
2. proposer と critic に SendMessage（recipient指定）で直接メッセージを送ること
3. **ラウンド進行の指示は leader のみが行う。自律的にラウンドを進めないこと**
4. Round 1: 対立点を特定し、両者に共有する
5. Round 2: ポジション変化を追跡し、合意に近づいている点を明示する
6. Round 3: 最終提案ドラフトを作成し、proposer と critic のレビューを求める
   最終提案は「合意事項」「条件付き合意」「未解決の論点」の3カテゴリに分類する
7. 全メッセージの要点を共有ログファイルに Edit で追記すること
8. 各ラウンド完了時は **leader に SendMessage で「Round X 完了」を報告すること**（ログ記録だけでは不十分）

【共有ログ】{log_path}
【テーマ】{theme}
【コンテキスト】{context}
```

---

## 設計原則（失敗からの学び）

以下を厳守する:

1. **直接対話の強制**: チームメイト間は必ず recipient 指定の SendMessage で対話する
2. **引用反論ルール**: 相手の具体的発言を引用してから反論する
3. **検証可能性**: 共有ログファイルに全議論を記録し、事後検証を可能にする
4. **ラウンド制御**: TaskList の blockedBy で順序を強制する
5. **broadcast 禁止**: 確実な配信のため direct message のみ使用
6. **完了確認**: idle 通知やログ記録だけでなく、**leader への SendMessage 報告**で完了を判断する
7. **先走り禁止**: チームメイトは leader の指示なしに次のラウンドへ進まない。integrator がラウンド進行役を兼ねない
8. **報告の一本化**: 完了報告は leader 宛の SendMessage のみ。ログは記録用、報告用ではない
