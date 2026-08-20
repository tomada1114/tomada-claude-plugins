<!-- platform-annex -->
# Claude Code ↔ Codex CLI 差分マトリクス

両プラットフォームで同一スキルを動かすために必要な「確定した違い」。変換判断の根拠はすべてここを参照する。

## 目次
- [1. スキル探索パス](#1-スキル探索パス)
- [2. SKILL.md frontmatter](#2-skillmd-frontmatter)
- [3. symlink 対応（非対称・最重要）](#3-symlink-対応非対称最重要)
- [4. 機能・ツール対応表](#4-機能ツール対応表)
- [5. サブエージェント](#5-サブエージェント)
- [6. スラッシュコマンド](#6-スラッシュコマンド)
- [7. 出典](#7-出典)

## 1. スキル探索パス

| | Claude Code | Codex CLI |
|---|---|---|
| user スコープ | `~/.claude/skills/<name>/` | `~/.codex/skills/<name>/`（`$CODEX_HOME/skills`、本機で確認） |
| repo スコープ | `<repo>/.claude/skills/<name>/` | `<repo>/.agents/skills/<name>/`（公式）／親・cwd の `.agents/skills/` |
| system | plugin の `skills/` | `/etc/codex/skills`・bundled |

両者とも **Agent Skills 標準**（`SKILL.md` + 任意の `references/` `scripts/` `assets/`）。**Claude は `.agents/skills/` を読まない。Codex は `.claude/skills/` を読まない。** → 同じ実体を両者に見せるには配置の工夫（[topology.md](topology.md)）が要る。

## 2. SKILL.md frontmatter

- **共通必須**: `name`, `description`。
- **Codex が読むのは `name` / `description` / `metadata`（`metadata.short-description` 等）のみ。** Codex の skill-creator は「それ以外を書くな」と指導するが、パーサが追加フィールドを**拒否する記述はない**（無視＝低リスク）。UI 用途は `agents/openai.yaml`。
- **Claude 専用フィールド**（Codex は無視）: `allowed-tools`, `disallowed-tools`, `argument-hint`, `arguments`, `model`, `effort`, `context`(=fork), `agent`, `hooks`, `paths`, `shell`, `disable-model-invocation`, `user-invocable`, `when_to_use`。
- 結論: **1 本の SKILL.md に Claude 専用フィールドを残しても両対応可**（Codex は無視）。ただし `description` には**両プラットフォーム分のトリガー語**を入れる。

## 3. symlink 対応（非対称・最重要）

| | symlink 追従 |
|---|---|
| **Codex** | **公式サポート**: 「Codex supports symlinked skill folders and follows the symlink target」 |
| **Claude Code** | **未文書化＝保証なし**（要・実体フォルダ運用） |

→ **この非対称性が配置設計を決める**。実体を `.claude/skills/` に置き、Codex 側からだけ symlink を張れば、**Claude は symlink を一切たどらない**（自分の実フォルダを読む）。Codex だけが公式サポート済みの追従をする。詳細は [topology.md](topology.md)。

## 4. 機能・ツール対応表

| 機能 | Claude Code | Codex CLI | 変換時の扱い（ベストエフォート劣化） |
|---|---|---|---|
| `Task`（サブエージェント並列） | あり | サブエージェント機構あり（TOML 定義・別物） | 既定: Codex 版では**逐次インライン**化。注記必須 |
| `Skill`（他スキル呼び出し） | あり | **なし** | 必要内容を `references/` に**インライン**／相対参照／Claude専用節 |
| `AskUserQuestion` | あり | **なし**（通常対話） | 「質問→ユーザー回答待ち」を**通常の対話文**に変換 |
| `context: fork` | あり | **なし** | フォーク前提を外し**メインコンテキストで逐次実行** |
| hooks / plan mode | あり | 別機構／なし | スキル本文からは依存しない設計に |
| MCP ツール（`mcp__*`） | セッション依存 | 別 config（`[mcp_servers]`） | サーバ名が一致すれば可。無ければ**フォールバック明記** |
| `/batch` | あり | **なし** | 逐次実行＋結果集約に |
| tmux オーケストレーション | スクリプト依存（ローカル） | 同左だが非ポータブル | Codex 版は逐次フォールバック |
| `model` / `effort` 指定 | frontmatter で可 | config 既定 | frontmatter に残置（Codex 無視）。本文で前提にしない |

## 5. サブエージェント

| | Claude Code | Codex CLI |
|---|---|---|
| 定義場所 | `.claude/agents/*.md`（user/project）／**`<skill>/agents/*.md`（skill-local）**／plugin | `.codex/agents/*.toml`（本機の `iobsidian/.codex/agents/transcription-fixer.toml` が実例）／skill の `agents/openai.yaml`（UI） |
| 形式 | Markdown + YAML frontmatter | TOML |
| 互換 | **なし**（相互変換不可） | 同左 |

本スキルの既定方針: 外部エージェント定義に依存させず、**サブエージェントの知識を対象スキルの `references/agents/<name>.md` に抽出**して両プラットフォーム共有にする（Claude は `Task` で、Codex は逐次インラインで同じ reference を使う）。将来オプション: `Task`→Codex TOML サブエージェント・マッピング。

## 6. スラッシュコマンド

| | Claude Code | Codex CLI |
|---|---|---|
| 場所 | `.claude/commands/*.md` | `~/.codex/prompts/*.md` |
| 呼び出し | `/name` | `/name`（prompts） |

本スキルの主対象は**スキル**。スラッシュコマンド変換は対象外（必要時は別途）。

## 7. 出典

- Codex Agent Skills（探索パス・symlink・frontmatter）: https://developers.openai.com/codex/skills
- Codex Subagents: https://developers.openai.com/codex/subagents
- 本機実測: `~/.codex/skills/.system/skill-installer/SKILL.md`（`$CODEX_HOME/skills` 既定 = `~/.codex/skills`）、`iobsidian/.codex/agents/*.toml`
- Claude Code 側（探索パス・frontmatter・symlink 未文書化）: claude-code-guide エージェント照会（2026-06）
