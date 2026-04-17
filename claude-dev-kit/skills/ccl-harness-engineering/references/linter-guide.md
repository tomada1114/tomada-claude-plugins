# Linter & Formatter Guide

言語別の推奨ツール、検出方法、設定保護対象ファイル一覧。2026年3月時点の推奨。

## 推奨ツール一覧

### TypeScript / JavaScript

| 用途 | 推奨ツール | 備考 |
|------|-----------|------|
| リント | Oxlint (VoidZero) | ESLintの50-100倍高速。520+ルール。PostToolUse向き |
| フォーマット | Biome | Rust製。ESLint+Prettierの10-25倍高速 |
| 型チェック | tsc | TypeScript compiler |
| 代替リント | ESLint | カスタムアーキテクチャルールが必要な場合。PostToolUseには遅いのでCI/PreCommit向き |
| 統合ツール | Biome v2 | リント+フォーマット統合。GritQLプラグインでカスタムルール対応 |

**使い分け:**
- PostToolUse Hook: Oxlint(リント) + Biome(フォーマット) — 高速
- PreCommit/CI: ESLint(カスタムルール) + tsc(型チェック) — 網羅的

**検出パターン:**
```bash
# package.json の devDependencies を確認
grep -E '"(eslint|@biomejs/biome|oxlint|prettier|typescript)"' package.json
# 設定ファイル
ls .eslintrc* eslint.config.* biome.json biome.jsonc oxlint.json tsconfig.json .prettierrc* 2>/dev/null
```

**設定保護対象:**
`.eslintrc*`, `eslint.config.*`, `biome.json`, `biome.jsonc`, `oxlint.json`, `.prettierrc*`, `tsconfig.json`

### Python

| 用途 | 推奨ツール | 備考 |
|------|-----------|------|
| リント+フォーマット | Ruff | Rust製。Flake8+isort+Black統合。900+ルール。一択 |
| 型チェック | mypy or pyright | pyright は高速、mypy は成熟 |
| アーキテクチャ | ast-grep | カスタムルール。Ruffはカスタムルール追加不可 |

**検出パターン:**
```bash
grep -E '"(ruff|flake8|black|mypy|pyright)"' pyproject.toml 2>/dev/null
grep -A5 '\[tool\.ruff\]' pyproject.toml 2>/dev/null
ls ruff.toml .flake8 mypy.ini pyrightconfig.json 2>/dev/null
```

**設定保護対象:**
`ruff.toml`, `pyproject.toml`（tool.ruff / tool.mypy セクション）, `.flake8`, `mypy.ini`, `pyrightconfig.json`

### Go

| 用途 | 推奨ツール | 備考 |
|------|-----------|------|
| リント | golangci-lint | 50+リンター並列実行。キャッシュで高速 |
| フォーマット | gofmt / gofumpt | gofumpt はより厳格 |
| セキュリティ | gosec | golangci-lint 内蔵 |

**推奨有効リンター:** staticcheck, gosec, errcheck, revive, govet, gofumpt, gci, modernize

**検出パターン:**
```bash
ls .golangci.yml .golangci.yaml 2>/dev/null
grep golangci Makefile 2>/dev/null
```

**設定保護対象:**
`.golangci.yml`, `.golangci.yaml`

### Rust

| 用途 | 推奨ツール | 備考 |
|------|-----------|------|
| リント | Clippy (pedantic) | `allow_attributes = "deny"` でAgent のリント黙殺を防止 |
| フォーマット | rustfmt | 標準 |

**推奨 Cargo.toml 設定:**
```toml
[lints.clippy]
pedantic = { level = "warn", priority = -1 }
unwrap_used = "deny"
expect_used = "deny"
allow_attributes = "deny"   # Agentが #[allow(clippy::...)] できなくする
dbg_macro = "deny"
```

WHY: `allow_attributes = "deny"` はAgentが `#[allow(clippy::...)]` でリントを黙らせることを構造的に不可能にする。

**検出パターン:**
```bash
grep -A10 '\[lints.clippy\]' Cargo.toml 2>/dev/null
ls clippy.toml rustfmt.toml .rustfmt.toml 2>/dev/null
```

**設定保護対象:**
`Cargo.toml`（lints セクション）, `clippy.toml`, `rustfmt.toml`

### Swift

| 用途 | 推奨ツール | 備考 |
|------|-----------|------|
| リント | SwiftLint | 200+ルール、`--autocorrect` 対応 |
| フォーマット | SwiftFormat | — |

**設定保護対象:** `.swiftlint.yml`, `.swiftformat`

### Kotlin

| 用途 | 推奨ツール | 備考 |
|------|-----------|------|
| 静的解析 | detekt | — |
| フォーマット | ktfmt | ktlintより40%高速 |

**設定保護対象:** `detekt.yml`, `.editorconfig`

## フィードバック速度階層と推奨配置

| チェック | 最適ティア | 理由 |
|---------|-----------|------|
| フォーマッター | T0 (PostToolUse) | 単一ファイル、ms単位で完了 |
| 単一ファイルリント | T0 (PostToolUse) | Oxlint/Ruff/golangci-lintは十分高速 |
| 型チェック | T2 (PreCommit) | プロジェクト全体の型解決が必要 |
| カスタムアーキテクチャルール | T2 (PreCommit) | ESLintカスタムルール等は低速 |

## カスタムリンターのエラーメッセージ設計

全てのカスタムリンターのエラーメッセージは以下の構造に従うべき:

```
ERROR: [何が間違っているか]
  [ファイル:行番号]
  WHY: [なぜこのルールがあるか、ADRへのリンク]
  FIX: [具体的な修正手順、コード例があれば含む]
  EXAMPLE:
    // Bad:
    import { db } from '../infra/database';
    // Good:
    import { DatabaseProvider } from '../domain/providers';
```

WHY: Agentはリンターのエラーメッセージを無視できない（CIが通らない）が、ドキュメントは無視できる。ルールのドキュメントはエラーメッセージの中に書く。

## AI生成コード固有のアンチパターン

監査時に特に注意すべきパターン:

| パターン | 対策 |
|---------|------|
| TypeScript `any` 乱用 | `@typescript-eslint/no-explicit-any` を error レベルで強制 |
| コード重複 | jscpd で検出 |
| ゴーストファイル（既存を修正せず類似名で新規作成） | ファイル命名規則のリンター強制 |
| コメント洪水 | コメント比率チェック |
| セキュリティ脆弱性（36-40%含有） | gosec(Go), Ruff Sルール(Python), eslint-plugin-security(JS/TS) |

## 多言語カスタムルールツール

プロジェクト固有のアーキテクチャルールが必要な場合:

| ツール | 対応言語 | 特徴 |
|--------|---------|------|
| ast-grep | Python, Go, Rust, TS, JS等 | コードと同型のパターンでルール定義。正規表現より信頼性が高い |
| eslint-plugin-local-rules | TS/JS | リポジトリ内にプロジェクト固有ルールを配置（npm公開不要） |
| pylint カスタムチェッカー | Python | Ruff非対応のカスタムルール用 |

AST ベースのルールは正規表現ベースより劇的に信頼性が高い。ファイル名・インポートパスの単純チェック以外は常に AST ベースを使う。
