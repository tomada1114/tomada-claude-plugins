<!-- platform-annex -->
# Platform notes（Claude Code と Codex）

`/goal` は Claude Code と Codex のどちらでも実行される。作る側（このスキルを動かすホスト）と実行する側は別に考え、実行する側が分からなければ両方で動く書き方にする。

## 作る側

- Phase 1 の並列調査 → Claude Code: `executor` サブエージェントを並列起動 / Codex: メインが逐次インライン実行（結果は同じ、所要時間が増える）。
- Phase 4 の確認 → Claude Code: `AskUserQuestion` / Codex: 通常の文章で選択肢・トレードオフ・推奨を示して回答を待つ。
- 出力先の状態ディレクトリ規約（`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/goal-prompts/<slug>/`）は両ホスト共通。

## 実行する側が Codex のとき

- **書き込めるのは起動したワークスペース（対象のリポジトリ）の中だけ。** 状態ディレクトリのバンドルは読むだけにし、進み具合・一時ファイル・報告は SKILL.md の「The bundle is read-only to the executor」に従ってワークスペースの中か最後のメッセージに置く。ネストした別リポジトリ（vault の中の `Site/` など）はワークスペースの中なので書ける。
- **一時ファイルはワークスペース内の gitignore された場所**（例: `<repo>/.drafts/<slug>/`）。スクラッチパッドはない。
- **名前付きのサブエージェント（`executor`・`architect`・`scout`・`.claude/agents/` の各レンズ）はない。** 汎用のサブエージェント（書き換えは `worker`、読むだけは `explorer`）に指示を渡す。レンズは「`.claude/agents/<name>.md` の本文を指示として読む」と書けば使える。推論の強さは、指定できる場合だけ役割ごとに書く。
- **同時に動かすサブエージェントは6つまで**を目安にする。混雑で起動に失敗したら同じ指示で送り直し、作業の失敗には数えない。
- **GitHub の読み書きは GitHub MCP で行う**（`gh` は使わない）。課題やPRへの書き込みは、goal がもともとそれを扱うときだけ。
- フックの設定（`core.hooksPath`・`.git/hooks`）を読むと、フックの無効化として拒否されることがある。普通にコミットするよう書く。
