# Audit Checklist Reference

各チェックの詳細基準、確認コマンド、スコアリングルーブリック。

## Check A: CLAUDE.md Health

### 確認手順

1. ファイル存在確認:
   ```bash
   ls -la ./CLAUDE.md ./.claude/CLAUDE.md ./CLAUDE.local.md ./.claude/CLAUDE.local.md 2>/dev/null
   ```

2. 行数計測:
   ```bash
   wc -l ./CLAUDE.md ./.claude/CLAUDE.md 2>/dev/null
   ```

3. ポインタ型チェック — 以下のパターンが多いほど良い:
   ```bash
   # コマンド参照
   grep -cE '(npm |pnpm |yarn |bun |python |go |cargo |make )' CLAUDE.md
   # ファイルパス参照
   grep -cE '(src/|lib/|test/|docs/|\.claude/)' CLAUDE.md
   # ツール参照
   grep -cE '(eslint|prettier|biome|ruff|golangci|clippy|tsc|mypy)' CLAUDE.md
   ```

4. アンチパターン検出 — 以下が多いほど悪い:
   ```bash
   # 冗長な説明文（3行以上連続するテキストブロック）
   # 技術スタック解説
   grep -cE '(このプロジェクトは|This project is|We use|技術スタック|Architecture)' CLAUDE.md
   # コーディングスタイルの詳細記述（リンターに委ねるべき）
   grep -cE '(インデント|indent|naming convention|命名規則|camelCase|snake_case)' CLAUDE.md
   ```

### スコアリング

| Score | 基準 |
|-------|------|
| **Present** | 存在 + 50行以下 + ポインタ型（コマンド・パス参照3+） + 冗長説明なし |
| **Partial** | 存在するが: 50-200行 or コマンド未記載 or 冗長説明あり |
| **Missing** | CLAUDE.mdが存在しない or 200行超 |

### CLAUDE.local.md チェック

存在する場合:
- CLAUDE.mdとの役割分担: local.mdは個人的な設定・環境固有情報のみが理想
- 重複: 両ファイルに同じ内容がある場合は統合を提案

## Check B: Deterministic Guardrails

### 言語別設定ファイル検出

| 言語 | リンター設定 | フォーマッター設定 | 型チェック設定 |
|------|-------------|------------------|---------------|
| TypeScript/JS | `.eslintrc*`, `eslint.config.*`, `biome.json`, `biome.jsonc`, `oxlint.json` | `.prettierrc*`, `biome.json` | `tsconfig.json` |
| Python | `ruff.toml`, `pyproject.toml [tool.ruff]`, `.flake8`, `setup.cfg [flake8]` | `ruff.toml [format]`, `pyproject.toml [tool.black]` | `mypy.ini`, `pyrightconfig.json`, `pyproject.toml [tool.mypy]` |
| Go | `.golangci.yml`, `.golangci.yaml` | (gofmt built-in) | (built-in) |
| Rust | `clippy.toml`, `Cargo.toml [lints.clippy]` | `rustfmt.toml`, `.rustfmt.toml` | (built-in) |
| Swift | `.swiftlint.yml` | `.swiftformat` | — |
| Kotlin | `detekt.yml` | `.editorconfig [ktfmt]` | — |

### 確認コマンド

```bash
# TypeScript/JS
ls .eslintrc* eslint.config.* biome.json oxlint.json 2>/dev/null
cat package.json | grep -E '"(eslint|biome|oxlint|prettier)"' 2>/dev/null

# Python
ls ruff.toml .flake8 mypy.ini pyrightconfig.json 2>/dev/null
grep -A5 '\[tool\.ruff\]' pyproject.toml 2>/dev/null
grep -A5 '\[tool\.mypy\]' pyproject.toml 2>/dev/null

# Go
ls .golangci.yml .golangci.yaml 2>/dev/null

# Rust
ls clippy.toml rustfmt.toml .rustfmt.toml 2>/dev/null
grep -A10 '\[lints.clippy\]' Cargo.toml 2>/dev/null
```

### リンター設定保護の確認

```bash
# settings.json の deny リストを確認
cat .claude/settings.json 2>/dev/null | grep -A50 '"deny"'
# PreToolUse hooks で設定ファイルへの書き込みブロックを確認
cat .claude/settings.json 2>/dev/null | grep -A20 '"PreToolUse"'
```

保護すべきファイル（言語別）:
- **TS/JS**: `.eslintrc*`, `eslint.config.*`, `biome.json`, `.prettierrc*`, `tsconfig.json`
- **Python**: `ruff.toml`, `pyproject.toml` (tool.ruff/tool.mypy セクション)
- **Go**: `.golangci.yml`
- **Rust**: `clippy.toml`, `Cargo.toml` (lints セクション), `rustfmt.toml`

### スコアリング

| Score | 基準 |
|-------|------|
| **Present** | リンター + フォーマッター + 型チェッカー全て存在 + 設定保護あり |
| **Partial** | 一部ツール不足 or 設定保護なし |
| **Missing** | リンター/フォーマッターが存在しない |

## Check C: Hooks Setup

### 確認手順

1. settings.json からhooks設定を読む:
   ```bash
   # プロジェクトレベル
   cat .claude/settings.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('hooks',{}), indent=2))" 2>/dev/null
   # ユーザーレベル
   cat ~/.claude/settings.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('hooks',{}), indent=2))" 2>/dev/null
   ```

2. 外部hookスクリプトの確認:
   ```bash
   ls .claude/hooks/ 2>/dev/null
   ls ~/.claude/hooks/ 2>/dev/null
   ```

### 4パターン分類基準

**Safety Gates (PreToolUse):**
- `rm -rf`, `drop table` 等の破壊的コマンドブロック
- `.env`, シークレットファイルの編集禁止
- リンター設定ファイルの書き込みブロック
- `git commit --no-verify` の禁止
- exit 2 でブロック + stderr に理由

**Quality Loops (PostToolUse):**
- Write/Edit/MultiEdit マッチャーで発火
- ファイル拡張子による言語判定
- 自動フォーマット (biome format, prettier, ruff format)
- 自動リント (oxlint --fix, ruff check --fix)
- 残った違反を `hookSpecificOutput.additionalContext` として JSON で返却

**Completion Gates (Stop):**
- テスト実行 (npm test, pytest, go test)
- リント全体実行
- 未コミット変更の警告
- stop_hook_active フラグによる無限ループ防止

**Observability:**
- プロンプトログ
- セッション記録
- PreCompact での重要情報保護

### スコアリング

| Score | 基準 |
|-------|------|
| **Present** | 4パターン中3つ以上が設定されている + Quality Loops必須 |
| **Partial** | 1-2パターンのみ or Quality Loopsなし |
| **Missing** | hooks設定が存在しない |

## Check D: Rules & Skills

### 確認手順

```bash
# rules ディレクトリ
ls .claude/rules/ 2>/dev/null
# paths frontmatter の確認
grep -l "^paths:" .claude/rules/*.md 2>/dev/null
# paths なしの rules（常時コンテキスト消費）
for f in .claude/rules/*.md; do grep -L "^paths:" "$f" 2>/dev/null; done
# エージェント
ls .claude/agents/ 2>/dev/null
# スキル
ls .claude/skills/ 2>/dev/null
# コマンド
ls .claude/commands/ 2>/dev/null
```

### スコアリング

| Score | 基準 |
|-------|------|
| **Present** | rules/が存在 + paths活用 + CLAUDE.mdとの重複なし |
| **Partial** | rules/はあるがpathsなし or 重複あり |
| **Missing** | rules/が存在しない（全てCLAUDE.mdに記述） |

## Check E: ADRs & Documentation Hygiene

### 確認手順

```bash
# ADR ディレクトリ
ls docs/adr/ docs/decisions/ adr/ 2>/dev/null
# ADR のステータス確認
grep -r "Status:" docs/adr/ 2>/dev/null
# 6ヶ月以上更新されていない .md ファイル
find . -name "*.md" -not -path "./.claude/*" -not -path "./node_modules/*" -not -path "./.git/*" | while read f; do
  last_mod=$(git log -1 --format="%at" -- "$f" 2>/dev/null)
  if [ -n "$last_mod" ]; then
    six_months_ago=$(date -v-6m +%s 2>/dev/null || date -d "6 months ago" +%s 2>/dev/null)
    if [ "$last_mod" -lt "$six_months_ago" ] 2>/dev/null; then
      echo "STALE: $f (last modified: $(git log -1 --format='%ci' -- "$f"))"
    fi
  fi
done
```

### スコアリング

| Score | 基準 |
|-------|------|
| **Present** | ADRあり + ステータス管理 + 腐敗ドキュメントなし |
| **Partial** | ADRあり but ステータス不明 or 腐敗ドキュメント存在 |
| **Missing** | ADRなし + 記述的ドキュメントが主体 |

## Check F: Pre-commit Integration

### 確認手順

```bash
# プリコミットツール
ls .pre-commit-config.yaml .husky/ lefthook.yml lefthook-local.yml 2>/dev/null
# --no-verify 防止
grep -r "no-verify" .claude/settings.json ~/.claude/settings.json 2>/dev/null
```

### 速度階層最適化チェック

以下がPreCommitにしかない場合、PostToolUseへの移動を提案:
- フォーマッター → PostToolUse(T0)へ移動可能
- 単一ファイルリント → PostToolUse(T0)へ移動可能

### スコアリング

| Score | 基準 |
|-------|------|
| **Present** | プリコミット設定あり + --no-verify防止 + 速度階層最適化済み |
| **Partial** | 一部のみ設定 or 速度階層が最適でない |
| **Missing** | プリコミット設定が存在しない |
