<!-- platform-annex -->
# Platform notes（このスキル自身の Codex での制約・best-effort 劣化）

- [Codex ランタイムへの委譲](#codex-ランタイムへの委譲step-3--45--5-の主経路)
- [ツール対応](#ツール対応)
- [Codex での制約(best-effort 劣化)](#codex-での制約best-effort-劣化)

**前提: 「Codex だから使えない」ではなく「その実行ランタイムに公開されているか」で
判断する。** Codex 製品として複数エージェントの並列実行機能があっても、スキルを
起動したセッションからその spawn API が呼べるとは限らない（実測: agent 起動 API が
一切公開されていないランタイムがあった）。以下の「Codex:」列は *委譲能力が公開されて
いないランタイム* での劣化パスであって、Codex 製品の機能一覧ではない。委譲できるなら
Claude Code 側と同じ経路を使ってよい。

## Codex ランタイムへの委譲（step 3 / 4.5 / 5 の主経路）

実装・レビュー・CI 修復は `scripts/codex_run.sh` 経由で Codex に渡す。
このスクリプトが 2 つの起動口を自動で選ぶ:

- `codex_mode: companion` — Claude Code に openai-codex プラグインが入っている場合。
  `~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs`
  （バージョン番号がパスに入るため、最新版を `sort -V` で解決している）を叩く。
  ジョブ追跡・`--resume-last`・構造化レビュー出力が使える。
- `codex_mode: exec` — プラグインは無いが `codex` CLI はある場合。`codex exec` を
  直接叩く。`review` は構造化 JSON を返せず `review_verdict: UNSTRUCTURED` になり、
  `--resume` も使えない。
- `codex_mode: NONE`（exit 3）— `codex` CLI が無い。SKILL.md の各ステップに書いた
  従来の委譲パス（`opus`/`sonnet` サブエージェント、または逐次インライン）に落ちる。

**モデルと effort は渡さない。** 未指定にすることで `~/.codex/config.toml` の
`model` / `model_reasoning_effort` が効く。これが唯一 `max` を使える経路でもある
（companion 側は `--effort max` を明示的に拒否する）。新しいモデルに乗り換えるときは
config.toml の 1 行だけを変える。一時的に上書きしたいときだけ
`CODEX_RUN_MODEL` / `CODEX_RUN_EFFORT` を export する。

**`gh` は Codex サンドボックス内で認証できない**（`git` での github.com 到達は可能、
`gh auth status` は失敗する）。したがって GitHub API に触る作業 — 優先度リサーチ、
PR 作成、`link_check.sh`、`ci_watch.sh`、`land_pr.sh` — はすべて親側に残る。
Codex 側は worktree の中のコードだけを扱う。

**`codex_touched:` は patch 経由の編集しか拾わない。** シェルのリダイレクトで
書いたファイルは出てこないので、実際に何が変わったかは
`git -C <worktree> status --short` を正とする。

**Codex は聞き返せない。** 非対話・承認オフで走るため、プロンプトの穴は質問として
返らず「勝手に決めた結果」として返る。テンプレートの `{brace}` を全部埋めてから
起動する。

## ツール対応

- 優先度リサーチの委譲(step 2)→ Claude Code: `sonnet` サブエージェントを 1 体起動し
  [references/subagent-prompts.md](references/subagent-prompts.md) の Priority
  research テンプレートを渡す / Codex: メインが同ファイルを skill 相対で読み、
  read → rubric → `apply_priority_labels.py` の手順を逐次インラインで実行する。
  このステップだけは Codex ランタイムに委譲しない — 全工程が `gh` 呼び出しであり、
  サンドボックス内では認証が通らないため。
- 実装(step 3)→ 両プラットフォーム共通で `codex_run.sh task --write --cwd <worktree>`。
  `codex_mode: NONE` のときのみ従来パス（Claude Code: issue ごとに `opus` サブ
  エージェント、並列グループは `isolation: "worktree"` で cap 3 / Codex: メインが
  worktree を 1 つずつ逐次処理）。スコープは経路によらず「ブランチ作成 → 実装 →
  テスト → コミット → push」まで。PR 作成は常に親。
- レビュー(step 4.5)→ 両プラットフォーム共通で `codex_run.sh task --cwd <worktree>`
  （`--write` なし = read-only）。実装とは**別 run** にすることが要件で、`--cwd` で
  worktree を直接指せるため、worktree の中へ委譲を差し込む必要が無くなった。
  heavy diff のときだけ `codex_run.sh review` を追加する。`codex_mode: NONE` の
  ときのみ従来の梯子（委譲できるなら独立レビュアー 1 体 = `DELEGATED`、無ければ
  `UNAVAILABLE`）に落ちる。
- CI-watch の並列化(step 5)→ Claude Code: `all` モードで複数 PR が in-flight の
  とき `run_in_background` で watch を背景実行 / Codex: `ci_watch.sh` を PR ごとに
  逐次実行する。watch 自体は常に親側（`gh` を使うため）。
- CI repair(step 5、FAIL 時のみ)→ 両プラットフォーム共通で
  `ci_watch.sh > <worktree>/.ci-failure.log` に落としてから
  `codex_run.sh task --write --cwd <worktree>`。再 watch と 3 回までのループは親が
  回す。`codex_mode: NONE` のときのみ従来パス（Claude Code: 失敗 PR ごとに `sonnet`
  サブエージェント、同一失敗が 2 回連続で残ったら `opus` に再 spawn / Codex: メインが
  1 PR ずつ逐次で最大 3 回、2 回連続で残ったら自身の effort を上げて続行）。
- 選択肢提示・確認(step 2 の tie-break、preflight のダーティツリー確認など)→
  Claude Code: `AskUserQuestion` / Codex: 通常の対話文でユーザーに直接質問し、
  回答を待つ。
- `orchestrating-models` §2 の引用(モデル割り当ての根拠)→ Claude Code 専用スキル
  であり、このスキルからは bridge されていないため Codex からは参照を解決できな
  い。sonnet/opus の割り当て自体は両プラットフォームで有効な結論として SKILL.md
  本文に残る。引用先だけが無効になる。
- `gh` CLI(Issue/PR/Actions 操作、認証)→ 親側では両プラットフォーム共通で素の `gh`
  がそのまま通る。追加の connector や plugin は不要。Codex サンドボックス内だけが
  例外（上記）。

## Codex での制約(best-effort 劣化)

- サブエージェント起動(priority research、`codex_mode: NONE` 時の各フォールバック)→
  spawn 能力が公開されていないランタイムでは、すべてメインの逐次インライン実行に
  なる。能力の有無はランタイムに対して判定し、製品名から推測しない。
- `all` モードでの issue 間並列実装・CI-watch 並列化 → 一度に 1 issue/worktree・
  1 PR ずつの逐次実行になる。rank → implement → CI → merge のフェーズ順序は
  保たれるが、**コストは所要時間だけではない**: 委譲が担っていた issue ごとの
  コンテキスト隔離も失われ、diff・リポジトリ探索・CI ログが 1 つのコンテキストに
  run 全体ぶん積み上がる。逐次パスの `all` は少数ずつに区切って回し、残りは
  deferred として報告する。
- ステップ 4.5 のレビュー → `codex_mode: NONE` のときは能力の梯子を上から取る:
  ①委譲できるなら独立レビュアーを 1 体(`REVIEW: DELEGATED`。diff を書いていない
  文脈が読む点でレビューとして成立する) ②無ければ UNAVAILABLE。②では自分の diff を
  読み直して「レビューした」ことにせず、`REVIEW: UNAVAILABLE` として続行するが、
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
