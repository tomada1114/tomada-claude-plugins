---
name: dual-platform-skills
description: "Convert one existing skill (Claude Code origin or Codex origin) into a layout that works on both Claude Code and OpenAI Codex CLI. Uses Topology A: the real files live in .claude/skills/ and the Codex side symlinks them. Features Codex lacks (parallel Task, Skill-to-Skill calls, AskUserQuestion, context fork, /batch, tmux) are inlined as best-effort sequential steps, and knowledge held by dependent sub-agents is extracted into references/agents/. Orchestrates the phases with Python scripts and bundled sub-agents. Use when making a skill work in Codex, dual-platforming a skill, porting a skill to Codex, bridging a skill to Codex, or sharing one skill across both platforms."
argument-hint: "<skill-name or path> [--scope user|repo]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Task, Skill
---

# dual-platform-skills

1 つのスキルを Claude Code と Codex CLI の**両対応**にするオーケストレーター。Python スクリプト（決定的処理）と**封入サブエージェント**（推論処理）を多段で使う。

**このスキルを使わない場面**: 新規スキルのゼロ作成・監査・トラブルシュートは `claudecode-skill-creating` を使う。本スキルは「既存スキルの両対応化」専用。

## 設計の核（3 つの確定方針）

1. **Topology A**: 実体は `.claude/skills/<name>/`（Claude がネイティブに読む唯一の正本）。Codex 側（`~/.codex/skills/` or `<repo>/.agents/skills/`）は**そこへの symlink**。Claude は symlink をたどらず、Codex だけが公式サポート済みの追従をする。→ [references/topology.md](references/topology.md)
2. **ベストエフォート劣化**: Codex に無い機能は「Claude Code: …／Codex: 逐次インライン …」の**条件分岐表現**に書き換え、失う機能を明記。→ [references/transformation-rules.md](references/transformation-rules.md)
3. **封入サブエージェント**: 外部 `~/.claude/agents/` に依存せず、サブエージェントの指示を本スキルの [references/agents/](references/agents/) に封入し、`Task`（`subagent_type: general-purpose`/`Explore`）に渡して使う。完全自己完結。

差分の根拠はすべて [references/platform-diff.md](references/platform-diff.md)。

## Contract

- **入力**: 変換対象スキル名（`~/.claude/skills/<name>` に展開）または絶対パス。`--scope user|repo`（省略時は実体位置から自動判定）。
- **出力**: 両対応化された `.claude/skills/<name>/`（正本）＋ Codex symlink。適用編集・劣化リスト・検証結果のレポート。
- **不可侵**: 事実・手順・コード・固有名詞・意味は変えない。変えるのは配置とプラットフォーム依存表現のみ。

## オーケストレーション（フェーズ）

> 構造規律: **並列はフェーズ内のみ／フェーズは直列／サブエージェントは互いに会話しない／メインが各フェーズ間で統合**。
> パス変数: `RULES_DIR` = 本スキルの `references/` の絶対パス。`TARGET` = 変換対象スキルの実体ディレクトリ。サブエージェント起動時は `references/agents/*.md` 内の `{{…}}` を実値で埋める。

### P0. Intake & Classify（メイン・決定的）
1. 対象を解決し **origin** を判定（`.claude/skills/` = Claude 由来／`~/.codex/skills/`・`.agents/skills/` = Codex 由来）。
2. 分類スクリプトを実行（スキルディレクトリ基準）:
   ```bash
   python3 scripts/classify_skill.py <TARGET> --json
   ```
   → tier(A/B/C)・構文・dependent_subagents・cross_skill_refs を得る。
3. **Topology A の正本確定**: 実体が `.claude/skills/<name>/` に無ければ移動（Codex 由来スキルは Claude 側へ移す。[topology.md](references/topology.md) の双方向ルール）。
4. **cross_skill_refs があれば依存順序を決める**: 純データ hub → 被呼び出しスキル → オーケストレーターの順（hub 優先）。データ参照する依存スキルは P3 で**同じ codex dir へまとめて bridge** する前提でプランする（[topology.md](references/topology.md) 相互依存）。
5. tier A で構文が空なら P1/P2 を簡略化（frontmatter 確認＋相対パス化のみ）してよい。

### P1. Analyze（サブエージェント 1・読取専用）
変換プランを作る。
- **Claude Code**: `Task`（`subagent_type: Explore`）を 1 つ起動。プロンプト = [references/agents/skill-analyzer.md](references/agents/skill-analyzer.md) の本文に `{{TARGET_SKILL_DIR}}`/`{{RULES_DIR}}`/`{{CLASSIFY_JSON}}` を埋めたもの。返り値の JSON（変換プラン）を受け取る。
- **Codex / Task 無し**: メインが同ファイルを読み、その手順を**逐次インライン**実行して同じ JSON を自分で作る。

### P2. Transform（並列サブエージェント・書込）
変換プランを実装する。**SKILL.md の書き換えと各サブエージェント抽出は別ファイルなので並列安全**。
- **Claude Code**: 次を**並列**起動（各 `subagent_type: general-purpose`）:
  - rewriter ×1: [references/agents/skillmd-rewriter.md](references/agents/skillmd-rewriter.md)（`{{CONVERSION_PLAN}}` を渡す）→ `TARGET/SKILL.md` を両対応化。
  - extractor ×N: [references/agents/subagent-extractor.md](references/agents/subagent-extractor.md) を `subagents_to_extract` の各要素で 1 起動ずつ → `TARGET/references/agents/<name>.md` を生成。
- **Codex / Task 無し**: メインが rewriter→extractor の順に**逐次インライン**実行（並列性は失われる）。
- 完了後、メインが結果を統合（重複サブエージェントの共有化を確認）。

### P3. Bridge & Verify（メイン決定的 ＋ 敵対的サブエージェント 1）
1. Codex symlink を作成（冪等・実フォルダ上書き拒否）。**データ参照する依存スキルにも同じ codex dir へ bridge** し、`../<other>/...` を両対応に解決させる:
   ```bash
   bash scripts/bridge_symlink.sh <TARGET> [--scope user|repo]
   # 依存があれば各依存にも: bash scripts/bridge_symlink.sh <DEP> [--scope ...]
   ```
2. 両対応検証:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/claudecode-skill-creating/scripts/validate_skill.py <TARGET>   # Claude 妥当性
   python3 scripts/verify_bridge.py <TARGET> --json                                        # 両対応・symlink・残存 .claude パス
   ```
3. 敵対的検証:
   - **Claude Code**: `Task`（`subagent_type: Explore`）で [references/agents/bridge-verifier.md](references/agents/bridge-verifier.md) を起動（`{{VERIFY_JSON}}` を渡す）。`codex_runnable=false` や blockers が出たら P2 に戻して修正。
   - **Codex / Task 無し**: メインが同ファイルの観点で自己レビュー。
4. validate/verify のエラーは**ゼロにしてから**完了。

### P4. Report（メイン）
tier ／適用編集（rule→location）／Codex 劣化リスト／作成した symlink ／ validate・verify・bridge-verifier 結果を要約。Claude 専用として隔離した節があれば明示。

## 封入サブエージェント

| role | type | 用途 | prompt |
|---|---|---|---|
| skill-analyzer | Explore | 深読み→変換プラン JSON | [references/agents/skill-analyzer.md](references/agents/skill-analyzer.md) |
| skillmd-rewriter | general-purpose | SKILL.md 本文の両対応書き換え | [references/agents/skillmd-rewriter.md](references/agents/skillmd-rewriter.md) |
| subagent-extractor | general-purpose | 依存サブエージェント知識の抽出 | [references/agents/subagent-extractor.md](references/agents/subagent-extractor.md) |
| bridge-verifier | Explore | Codex 視点の敵対的検証 | [references/agents/bridge-verifier.md](references/agents/bridge-verifier.md) |

## スクリプト（スキルディレクトリ基準・相対起動）

| script | 役割 |
|---|---|
| `scripts/classify_skill.py <dir> [--json]` | 構文検出＋Tier(A/B/C)＋依存サブエージェント＋cross-skill |
| `scripts/bridge_symlink.sh <dir> [--scope user\|repo] [--codex-dir D] [--relative] [--dry-run]` | Codex symlink を冪等・安全に作成/検証 |
| `scripts/verify_bridge.py <dir> [--codex-link P] [--json]` | symlink 解決・相対リンク・Codex frontmatter・残存 .claude パス検査 |

## Hard rules
- **正本は常に `.claude/skills/`**。Codex 由来でも実体を Claude 側へ移し、Codex は symlink。
- **事実・手順・コード・意味を変えない。** 変えるのは配置とプラットフォーム依存表現だけ。
- ハードコード `.claude/` 絶対パスは**スキル内部参照のみ相対化**。cross-skill は **データ参照=相対化（依存も同じ codex dir へまとめて bridge）／実行=抽出・inline・claude-only**（[transformation-rules.md](references/transformation-rules.md) R5）。
- サブエージェント定義は `<skill>/agents/`・`.claude/agents/`・`~/.claude/agents/` の 3 系統＋種類(登録済み/プロンプト同梱)を判定。定義が無い名前参照は claude-only にしユーザー報告。
- **`Task` サブエージェントには skill 相対パスを渡さない**（cwd=repo root のため解決しない）。**内容をインライン**か**絶対パス**で渡す（[transformation-rules.md](references/transformation-rules.md) R10）。canonical は `references/agents/<name>.md` 1 つ（ミラー禁止＝drift 防止）。
- **実行オーケストレーター（他スキルを `Skill` で回す）は最後に変換**。依存（hub→被呼び出し）を全部先に両対応化＋bridge してから着手（R5/L10）。
- symlink は **Codex 側だけ**（`~/.claude/skills/` は実フォルダのまま＝マーケットプレイスへの配布同期に無影響）。
- 完了前に `validate_skill.py` と `verify_bridge.py` をエラーゼロに。

> Codex で実行する場合の制約と代替手順は `references/codex-notes.md` を参照。
