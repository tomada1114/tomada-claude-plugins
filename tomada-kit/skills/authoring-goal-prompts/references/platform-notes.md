<!-- platform-annex -->
# Platform notes（Codex での best-effort 劣化）

- Phase 1 の並列調査 → Claude Code: `Agent`（`subagent_type: Explore`）を並列起動 / Codex: メインが逐次インライン実行（結果は同じ、所要時間が増える）。
- Phase 4 の確認 → Claude Code: `AskUserQuestion` / Codex: 通常の文章で選択肢・トレードオフ・推奨を示して回答を待つ。
- 出力先の状態ディレクトリ規約（`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/goal-prompts/<slug>/`）は両ホスト共通。
- `/goal` コマンド自体は Claude Code 固有。Codex で作成したプロンプトも、貼り付けて実行する先は Claude Code。
