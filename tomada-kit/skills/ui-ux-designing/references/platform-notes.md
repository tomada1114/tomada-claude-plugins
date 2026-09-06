<!-- platform-annex -->
# Platform notes

SKILL.md が使う機能と、ホストごとの実現手段の対応表。使えない機能があるホストでは、右側の代替に落として同じ手順を続ける。

- **選択肢を提示して確認する**（Phase 1・3・4）
  Claude Code: `AskUserQuestion` に `questions-core.md` / `questions-app-type.md` の JSON をそのまま渡す。
  Codex: 通常の対話で番号付きの選択肢として提示する。変換の書き方は `questions-core.md` の `## 平文で提示する場合` にある例に従う。
  どちらでも SKILL.md の「質問設計の原則」（選択肢2〜4個、トレードオフ、`（推奨）`は1つ、1ラウンド3〜4問）は変えない。

- **web検索**（Phase 2 の競合調査）
  Claude Code: `WebSearch`。
  Codex: 同等の web 検索ツールがあれば使用する。
  どちらも使えない場合: 参考アプリ名・URL・スクリーンショットをユーザーに提供してもらい、それを材料に同じ観点で比較する。

- **サブエージェントへの委譲**（Phase 2）
  Claude Code: `Task` で `model: sonnet` のサブエージェント1体に `agents/research-competitors.md` のプロンプトを渡す。
  Codex: 同じプロンプトを本体セッションでそのまま実行する。読む資料・観点・出力形式は変えない。

- **スクリプト実行**（Phase 6 のコントラスト実測）
  両ホスト共通: スキルディレクトリから `python3 scripts/check_contrast.py` を実行する。

参照先はすべてスキル相対パスで書いてあるので、Claude Code でも Codex（`~/.codex/skills/` の symlink 経由）でも同じ位置に解決する。
