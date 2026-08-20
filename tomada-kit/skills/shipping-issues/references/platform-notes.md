<!-- platform-annex -->
# Platform notes（このスキル自身の Codex での制約・best-effort 劣化）

## ツール対応

- 優先度リサーチの委譲(step 2)→ Claude Code: `sonnet` サブエージェントを 1 体起動し
  [references/subagent-prompts.md](references/subagent-prompts.md) の Priority
  research テンプレートを渡す / Codex: メインが同ファイルを skill 相対で読み、
  read → rubric → `apply_priority_labels.py` の手順を逐次インラインで実行する。
- 実装の委譲(step 3)→ Claude Code: issue ごとに `opus` サブエージェントを起動し、
  並列グループは `isolation: "worktree"`(cap 3)で単一メッセージから spawn / Codex:
  メインが同テンプレートを skill 相対で読み、issue を 1 件ずつ(または worktree を
  1 つずつ)チェックアウト内で逐次インラインに処理する。
- CI-watch の並列化(step 5)→ Claude Code: `all` モードで複数 PR が in-flight の
  とき `run_in_background` で watch を背景実行 / Codex: `ci_watch.sh` を PR ごとに
  逐次実行する。
- CI repair の委譲(step 5、FAIL 時のみ)→ Claude Code: 失敗 PR ごとに `sonnet`
  サブエージェントを起動し、同一失敗が 2 回連続で残ったら `opus` に再 spawn /
  Codex: メインが同テンプレートを skill 相対で読み、1 PR ずつ最大 3 回まで逐次で
  修復し、2 回連続で残ったら自身の effort を上げて続行する。
- 選択肢提示・確認(step 2 の tie-break、preflight のダーティツリー確認など)→
  Claude Code: `AskUserQuestion` / Codex: 通常の対話文でユーザーに直接質問し、
  回答を待つ。
- ステップ 4.5 のセルフレビュー → Claude Code: 組み込みの `/code-review` スキル
  (`high --fix` を 1 回、または `low --fix` を 2 回)を実装エージェントの worktree
  内で起動し、その `--fix` が見つかった指摘を作業ツリーに適用する / Codex: 等価な
  組み込みスキルが存在しない。
- `orchestrating-models` §2 の引用(モデル割り当ての根拠)→ Claude Code 専用スキル
  であり、このスキルからは bridge されていないため Codex からは参照を解決できな
  い。sonnet/opus のモデル割り当て自体は両プラットフォームで有効な結論として
  SKILL.md 本文に残る。引用先だけが無効になる。

## Codex での制約(best-effort 劣化)

- Task ベースのサブエージェント起動(priority research、per-issue implementation、
  CI repair)→ すべてメインの逐次インライン実行になる(サブエージェント機構は
  使わない)。
- `all` モードでの issue 間並列実装・CI-watch 並列化 → 一度に 1 issue/worktree・
  1 PR ずつの逐次実行になる。所要時間が増えるだけで、rank → implement → CI →
  merge のフェーズ順序は保たれる。
- ステップ 4.5 のセルフレビュー → Codex では完全に UNAVAILABLE。等価な組み込み
  スキルが無いため、代替レビューを自作せず `REVIEW: UNAVAILABLE` として続行する。
  既存の UNRESOLVED / `REVIEW: UNAVAILABLE` フォールバックが、レビュー抜きでの
  マージを既にカバーしている。
