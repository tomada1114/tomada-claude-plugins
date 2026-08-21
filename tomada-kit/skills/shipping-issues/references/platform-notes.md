<!-- platform-annex -->
# Platform notes（このスキル自身の Codex での制約・best-effort 劣化）

**前提: 「Codex だから使えない」ではなく「その実行ランタイムに公開されているか」で
判断する。** Codex 製品として複数エージェントの並列実行機能があっても、スキルを
起動したセッションからその spawn API が呼べるとは限らない（実測: agent 起動 API が
一切公開されていないランタイムがあった）。以下の「Codex:」列は *委譲能力が公開されて
いないランタイム* での劣化パスであって、Codex 製品の機能一覧ではない。委譲できるなら
Claude Code 側と同じ経路を使ってよい。

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
  内で起動し、その `--fix` が見つかった指摘を作業ツリーに適用する / レビュー能力が
  公開されていないランタイム: 等価な起動口が無い。委譲能力があるなら
  `subagent-prompts.md` の Self-review テンプレート(SKILL.md ステップ 4.5 から
  たどる)で独立レビュアーを 1 体だけ立て、返ってきた指摘を branch を持つ側が
  自分で直す(`REVIEW: DELEGATED`)。委譲も無ければ `REVIEW: UNAVAILABLE`(下記)。
- `orchestrating-models` §2 の引用(モデル割り当ての根拠)→ Claude Code 専用スキル
  であり、このスキルからは bridge されていないため Codex からは参照を解決できな
  い。sonnet/opus のモデル割り当て自体は両プラットフォームで有効な結論として
  SKILL.md 本文に残る。引用先だけが無効になる。
- `gh` CLI(Issue/PR/Actions 操作、認証)→ 両プラットフォーム共通。Codex 側でも
  追加の connector や plugin は不要で、素の `gh` がそのまま通る。

## Codex での制約(best-effort 劣化)

- サブエージェント起動(priority research、per-issue implementation、CI repair)→
  spawn 能力が公開されていないランタイムでは、すべてメインの逐次インライン実行に
  なる。能力の有無はランタイムに対して判定し、製品名から推測しない。
- `all` モードでの issue 間並列実装・CI-watch 並列化 → 一度に 1 issue/worktree・
  1 PR ずつの逐次実行になる。rank → implement → CI → merge のフェーズ順序は
  保たれるが、**コストは所要時間だけではない**: 委譲が担っていた issue ごとの
  コンテキスト隔離も失われ、diff・リポジトリ探索・CI ログが 1 つのコンテキストに
  run 全体ぶん積み上がる。逐次パスの `all` は少数ずつに区切って回し、残りは
  deferred として報告する。
- ステップ 4.5 のセルフレビュー → 能力の梯子を上から取る: ①組み込みレビュー
  ②組み込みが無くても委譲できるなら独立レビュアーを 1 体(`REVIEW: DELEGATED`。
  diff を書いていない文脈が読む点でレビューとして成立する) ③どちらも無ければ
  UNAVAILABLE。③では自分の diff を読み直して「レビューした」ことにせず、
  `REVIEW: UNAVAILABLE` として続行するが、
  これは**明示された低保証モード**であって黙って飛ばす状態ではない: run record に
  `--event review --field status=UNAVAILABLE` として残し、ステップ 8 のレポートの
  当該 issue 行にも `REVIEW: UNAVAILABLE` を付ける。lint・型・テスト・CI は通って
  いるが、不要な複雑性・issue の意図とのずれ・保守性は誰も見ていない、という
  保証レベルの差をユーザーが読み取れるようにするため。
- Git 操作の sandbox 制限 → `git status`/`commit`/`push`/`switch` は通っても、
  `.git/index.lock` や `FETCH_HEAD` の書き込みを伴う操作(`git fetch`、
  `git pull`、branch/ref 削除、worktree 操作、`cleanup_run.sh` 全体)が
  `Operation not permitted` で失敗することがある。スキル側に分岐は設けない —
  その Git 操作だけ権限を昇格して再実行する。
- ツールキャッシュの書き込み制限 → パッケージマネージャやテストランナーが既定の
  ユーザーキャッシュ(`~/.cache/...` 等)に書けず、初回の依存解決やテスト実行が
  失敗することがある。そのツールのキャッシュ用環境変数を書き込み可能な一時
  ディレクトリへ向けて(`<TOOL>_CACHE_DIR=<writable tmp>` の形で)再実行する。
