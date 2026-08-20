<!-- platform-annex -->
# Platform notes（このスキル自身の Codex での制約・best-effort 劣化）

## ツール対応
- Phase 1 の並列調査（項目 1「Project rules」と項目 3「Existing patterns」）→ Claude Code: 広い/不確実なスコープでは `Task`（`subagent_type: Explore`）を並列起動 / Codex: `Task` 相当の並列委譲機構が無いため、メインが同じ調査を逐次インライン実行（結果は同じ、所要時間が増える）。
- Phase 4 の選択肢確認 → Claude Code: `AskUserQuestion` / Codex: 通常の文章で選択肢とトレードオフ・推奨を提示し回答を待つ。確認する軸（done-state / scope boundary / verify method / stop ceiling / design fork）と「1 ラウンド最大 4 問」の制約は不変。

## Codex での制約（best-effort 劣化）
- 並列 `Task` fan-out → Codex では逐次実行（所要時間増、結果は同じ）。
- `AskUserQuestion` → Codex では通常対話で確認（代替表現は SKILL.md Phase 4 本文に直接インライン済み）。
- **バンドル出力先はホスト非依存**: `${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/goal-prompts/<slug>/` という状態ディレクトリ規約自体は Claude Code / Codex 共通で、どちらのホストで本スキルを実行してもこの規約に従って support files を書き出す。
- **`/goal` コマンドは Claude Code 固有**: 出力先の規約が中立化された一方、生成したプロンプトを実行する `/goal` コマンド自体には Codex 側の相当機能が存在しない。したがって本スキルの成果物（goal プロンプト本文＋サポートファイル）は両ホストで同一の手順・同一の置き場所で作成できるが、それを「貼り付けて起動する」対象は Claude Code の `/goal` に限られる——この非対称性が本スキルで唯一 Claude 専用のまま残る部分。
- ≤4000 文字の上限と `wc -m` による計測は両対応で有効（成果物そのもののポータビリティは保たれる）。
