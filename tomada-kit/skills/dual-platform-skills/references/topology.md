<!-- platform-annex -->
# Topology A — 配置設計

採用する唯一の配置方式。**実体は `.claude/skills/<name>/`、Codex 側はそこへの symlink**。

## 目次
- [なぜ Topology A か](#なぜ-topology-a-か)
- [レイアウト](#レイアウト)
- [スコープと Codex ディレクトリ解決](#スコープと-codex-ディレクトリ解決)
- [双方向ルール（Codex 由来スキル）](#双方向ルールcodex-由来スキル)
- [相互依存スキルの扱い（hub 優先）](#相互依存スキルの扱いhub-優先)
- [安全性・相互運用](#安全性相互運用)

## なぜ Topology A か
- Claude のスキル symlink 追従は**未保証**、Codex は**公式サポート**（[platform-diff.md](platform-diff.md) §3）。
- 実体を Claude 側に置けば **Claude は symlink を一切たどらない**（自分の実フォルダを読むだけ）。Codex だけが公式追従する。
- → Codex 提案の `.shared/` 方式（Claude 側も references/scripts の symlink 追従が必要）より**低リスク**。`.shared/` は不要、SKILL.md も 1 本で済む。
- 決定的利点: Codex は同一実体を symlink 経由で読むので、**スキル内部の相対パスが両者で同一に解決**される。

## レイアウト
```
.claude/skills/<name>/        ← 実体（正本・唯一）。Claude がネイティブに読む
├── SKILL.md                  ← 1 本。name+description 両対応／本文は条件分岐表現
├── references/
│   └── agents/<sub>.md       ← 依存サブエージェント知識（両プラットフォーム共有）
└── scripts/

<codex-skills-dir>/<name>  ──symlink──▶ .claude/skills/<name>
```

## スコープと Codex ディレクトリ解決
| スコープ | 実体 | Codex symlink 先 |
|---|---|---|
| user（global） | `~/.claude/skills/<name>/` | `~/.codex/skills/<name>`（`$CODEX_HOME/skills`） |
| repo（project） | `<repo>/.claude/skills/<name>/` | `<repo>/.agents/skills/<name>`（公式） |

`scripts/bridge_symlink.sh` が自動判定（実体が `~/.claude/skills` 配下→user、`<repo>/.claude/skills` 配下→repo）。`--scope` / `--codex-dir` で上書き可。

## 双方向ルール（Codex 由来スキル）
- 由来が Codex（実体が `~/.codex/skills/` 等）のスキルでも、**実体を `.claude/skills/` へ移動**し、Codex 側を symlink に置換する。
- 理由: 正本は常に Claude 側でなければならない（Claude の symlink 非対応のため、Claude に実体が要る）。Codex は symlink で読めるので問題ない。

## 相互依存スキルの扱い（hub 優先）
cc-book 系のように**スキル群が互いを参照**する場合:
- **データ参照**（他スキルの `references/`・`scripts/` を読む）は、相互依存スキルを**同じ codex dir へまとめて bridge** すれば相対パス `../<other>/...` で両対応に解決する。`~/.codex/skills/` に `cc-book-context` も `cc-book-score-check` も並ぶ、という状態を作る。
- **変換順序**: 純データ hub（`cc-book-context`）→ 被呼び出しスキル（`cc-book-score-check` 等）→ オーケストレーター（`cc-book-review`）の順。下流を先に両対応化する。
- **実行依存**（`Skill` ツールで他スキルを起動）は symlink では解決しない → [transformation-rules.md](transformation-rules.md) R5(b)。**実行オーケストレーターは最後に変換**し、推移的な依存スキルを全部先に両対応化＋bridge する（ハード前提・R5/L10）。
- **スコープ越え**: repo スキル → user スキル（`~/.claude/skills/`、例 `orchestrating-models`）の参照は別ツリーで相対不可 → inline か claude-only。

## 安全性・相互運用
- **マーケットプレイス配布への影響なし**: symlink は `~/.codex/skills/`（または `<repo>/.agents/skills/`）側のみ。`~/.claude/skills/` は実フォルダのまま → 配布同期スクリプトは無傷。
- `bridge_symlink.sh` は**実フォルダの上書きを拒否**（symlink のみ repoint）、冪等。
- **生成 symlink だけを gitignore**: repo 内で bridge した場合、`bridge_symlink.sh` は生成した symlink 名を `<codex-dir>/.gitignore`（例 `.agents/skills/.gitignore`）に**自動登録**する。これにより「生成物の symlink は無視／ユーザーが直接置く Codex 専用の実スキルは追跡可能」を両立する。`.agents/` を丸ごと ignore しないこと。
- 検証: `ls -lL <codex-skills-dir>/<name>` が実体に解決され、`<codex>/<name>/SKILL.md` が読めること（`verify_bridge.py` が自動チェック）。
