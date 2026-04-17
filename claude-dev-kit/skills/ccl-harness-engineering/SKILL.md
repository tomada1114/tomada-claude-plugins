---
name: ccl-harness-engineering
description: "プロジェクトのClaude Code harness設定を監査し、ハーネスエンジニアリングのベストプラクティスに基づいて改善提案を生成する。CLAUDE.md、Hooks、リンター、ADR、プリコミット設定を包括的にチェック。明示的に呼び出された場合のみ実行。Use when user mentions 'harness audit', 'harness review', 'ハーネス監査', 'harness engineering', 'ハーネスエンジニアリング', 'harness check', 'ハーネスチェック', 'プロジェクト監査', 'harness改善', 'hooks見直し', 'CLAUDE.md監査'. Examples: <example>Context: User wants to audit project harness user: 'このプロジェクトのharnessを監査して' assistant: 'I will use ccl-harness-engineering skill' <commentary>Triggered by harness audit request</commentary></example> <example>Context: User wants best practice check user: 'ハーネスエンジニアリングに沿っているか確認' assistant: 'I will use ccl-harness-engineering skill' <commentary>Triggered by best practice review</commentary></example>"
disable-model-invocation: true
---

# Harness Engineering Auditor

既存プロジェクトのClaude Code harness設定を監査し、ハーネスエンジニアリングのベストプラクティスに基づいて改善を提案するスキル。

## Core Principles

本スキルの監査・改善提案は以下の3原則に基づく:

1. **仕組みで品質を強制する** — CLAUDE.mdに「リンターを実行せよ」と書くことと、Hookでリンターを実行することの間には「ほぼ毎回」と「例外なく毎回」の差がある。プロンプトではなく決定論的ツールで品質を保証する
2. **フィードバックは速ければ速いほど良い** — PostToolUse(ms) > PreCommit(s) > CI(min) > Human Review(h)。可能な限り速いレイヤーにチェックを移動させる
3. **エラーメッセージは修正指示にする** — WHY(なぜこのルールがあるか) + FIX(具体的な修正手順)を含める。Agentはエラーメッセージを無視できないが、ドキュメントは無視できる

## Workflow

### Phase 1: Environment Detection

プロジェクト環境を検出する。

**言語検出:**
| マーカーファイル | 言語/ランタイム |
|-----------------|----------------|
| `package.json` | Node.js / TypeScript / JavaScript |
| `pyproject.toml`, `requirements.txt` | Python |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `composer.json` | PHP |
| `Gemfile` | Ruby |
| `Package.swift` | Swift |
| `build.gradle.kts` | Kotlin |

**フレームワーク検出:**
- `next.config.*` → Next.js
- `manage.py` → Django
- `app/` + `config/routes.rb` → Rails
- `nuxt.config.*` → Nuxt
- `astro.config.*` → Astro

**モノレポ検出:**
- `pnpm-workspace.yaml`, `lerna.json`, `nx.json`, `turbo.json`

**Claude Code設定の確認箇所:**

```
./CLAUDE.md                    # プロジェクトレベル
./.claude/CLAUDE.md            # プロジェクトレベル(代替)
./CLAUDE.local.md              # ローカル設定
./.claude/CLAUDE.local.md      # ローカル設定(代替)
./.claude/settings.json        # プロジェクト設定(hooks含む)
./.claude/settings.local.json  # ローカル設定
~/.claude/settings.json        # ユーザーレベル設定
~/.claude/settings.local.json  # ユーザーレベルローカル設定
./.claude/rules/               # 動的ルール
./.claude/agents/              # サブエージェント
./.claude/commands/            # カスタムコマンド
```

検出結果をプロジェクトプロファイルとしてまとめ、以降の全分析の基盤にする。

### Phase 2: Harness Audit

6つのチェックを実行し、それぞれ **Present / Partial / Missing** でスコアリングする。詳細な基準は `references/audit-checklist.md` を参照。

#### Check A: CLAUDE.md Health

| 項目 | 基準 |
|------|------|
| 存在 | プロジェクトレベルにCLAUDE.mdがあるか |
| 行数 | 50行以下が理想。200行超は要最適化 |
| ポインタ型 | コマンド・ファイルパス・ツールへの参照が主体か |
| 禁止コンテンツ | 冗長なシステム説明、技術スタック解説、コーディングスタイルガイドがないか |
| ビルド/テスト/リントコマンド | 記載があるか |
| CLAUDE.local.md | 存在する場合、CLAUDE.mdとの役割分担は適切か |
| 重複 | rules/ や他の設定ファイルとの内容重複がないか |

**判定:**
- Present: 50行以下、ポインタ型、コマンド記載あり
- Partial: 存在するが冗長 or コマンド未記載
- Missing: CLAUDE.mdが存在しない

#### Check B: Deterministic Guardrails

検出した言語に対応するリンター/フォーマッター/型チェッカーの有無を確認。推奨ツールは `references/linter-guide.md` を参照。

| 項目 | 確認方法 |
|------|---------|
| リンター | 言語別設定ファイルの存在確認 |
| フォーマッター | 同上 |
| 型チェッカー | tsconfig.json, mypy/pyright設定等 |
| 設定保護 | リンター設定ファイルがsettings.jsonのdenyリストまたはPreToolUse hookで保護されているか |

**重要チェック — リンター設定保護:**
AgentはリンターエラーをコードではなくリンターSettingsの変更で回避しようとする傾向がある。設定ファイル（`.eslintrc*`, `biome.json`, `ruff.toml`, `tsconfig.json`等）への書き込みがブロックされているか必ず確認する。

#### Check C: Hooks Setup

settings.json(プロジェクトレベル + ユーザーレベル)のhooksを記事の4パターンで分類:

| パターン | タイミング | 目的 | 例 |
|---------|-----------|------|-----|
| Safety Gates | PreToolUse | 破壊的操作のブロック | rm -rf防止、.env編集禁止、リンター設定保護 |
| Quality Loops | PostToolUse | 編集後の自動品質チェック | フォーマッター実行、リント、型チェック |
| Completion Gates | Stop | 完了時の最終検証 | テスト実行、未コミット確認 |
| Observability | 全イベント | 監視・ログ | プロンプトログ、セッション記録 |

各パターンの充足度を評価。特にQuality Loops（PostToolUse）の有無は最重要 — フィードバック速度階層の最速レイヤーに相当する。

hookスクリプトが外部ファイルの場合、そのスクリプトも読んでエラーメッセージの品質（WHY + FIX含有）を確認する。

#### Check D: Rules & Skills

| 項目 | 確認方法 |
|------|---------|
| `.claude/rules/` | ファイル一覧と `paths` frontmatterの有無 |
| paths活用 | pathsなしのrulesはCLAUDE.mdと同じく常時コンテキスト消費。動的ロードが適切か |
| 冗長性 | CLAUDE.mdと rules/ の内容重複 |
| スキル構成 | プロジェクト固有スキルの有無 |
| エージェント構成 | `.claude/agents/` の有無と構成 |

#### Check E: ADRs & Documentation Hygiene

| 項目 | 確認方法 |
|------|---------|
| ADR有無 | `docs/adr/`, `docs/decisions/`, `adr/` ディレクトリの存在 |
| ADRステータス | Accepted/Superseded/Deprecated が明示されているか |
| 腐敗ドキュメント | `git log` で6ヶ月以上更新されていない.mdファイル |
| テストで表現可能 | 仕様・制約が記述的ドキュメントではなくテストで表現されているか |

#### Check F: Pre-commit Integration

| 項目 | 確認方法 |
|------|---------|
| プリコミット | `.pre-commit-config.yaml`, `.husky/`, `lefthook.yml` の存在 |
| --no-verify防止 | settings.jsonのdenyリストに `git commit --no-verify` があるか |
| 速度階層の最適化 | PostToolUseで実行可能なチェックがPreCommitに留まっていないか |

### Phase 3: Report & Interactive Consultation

監査結果を簡潔に表示した上で、AskUserQuestion による対話的な改善プロセスに入る。

**まず現状を共有:**

```
=== Harness Engineering Audit ===
Project: [name] | Language: [lang] | Framework: [fw]

| Category | Status | Key Findings |
|----------|--------|-------------|
| A. CLAUDE.md Health | Present/Partial/Missing | [summary] |
| B. Deterministic Guardrails | ... | ... |
| C. Hooks Setup | ... | ... |
| D. Rules & Skills | ... | ... |
| E. ADRs & Doc Hygiene | ... | ... |
| F. Pre-commit | ... | ... |
```

**次に対話で方針を決める:**

AskUserQuestion を使い、以下を順番に確認する。ユーザーの回答はスコアや分析結果より常に優先される。

1. **関心領域の選択** — 「どのカテゴリに興味がありますか？全部見ますか、それとも特定の領域に絞りますか？」
2. **選択された領域ごとの掘り下げ** — 現状の詳細と改善案を提示し、「この方向で進めますか？別のアプローチがいいですか？」と確認
3. **優先順位の確認** — 複数の改善案がある場合、「どれから着手しますか？」

ユーザーが「不要」と判断した項目は、スコアがMissingであっても提案しない。逆にスコアがPresentでも、ユーザーが改善を望めば対応する。

### Phase 4: Recommendations

対話で合意した改善項目について、具体的な提案を提示する:

```
### [R-XX] タイトル
- Speed Tier: T0(PostToolUse) / T1(PreToolUse) / T2(PreCommit)
- Effort: Low(設定変更) / Medium(新規hookスクリプト) / High(ツール導入)
- WHY: [ハーネスエンジニアリング原則への参照]
- WHAT: [具体的な変更内容]
- HOW: [設定例 or references/への参照]
```

具体的なhook設定テンプレートは `references/hook-patterns.md` を参照して提示する。

### Phase 5: Apply

ユーザーが承認した改善項目を一つずつ適用する:

1. 変更内容の詳細を表示し、AskUserQuestion で最終確認
2. 変更を適用
3. 適用後に動作確認（hookの場合はテスト実行）
4. 次の項目へ進むか確認

## AI Assistant Instructions

### Always

- Phase 1で環境検出を完了してから監査を開始する
- 6つのチェック全てを実行してからレポートを生成する
- `references/audit-checklist.md` で詳細基準を確認する
- 検出した言語に合わせて `references/linter-guide.md` と `references/hook-patterns.md` を参照する
- CLAUDE.local.md が存在する場合も必ず確認する
- **レポート提示後は必ずAskUserQuestionで対話に入る** — 何を採用するか、どう改善するかはユーザーが決める
- **ユーザーの判断はスコアより常に優先される** — Missingでもユーザーが不要と言えば提案しない、Presentでもユーザーが改善を望めば対応する
- 各推奨にはWHY(原則) + WHAT(変更) + HOW(設定例)を含める
- 変更適用前にAskUserQuestionで最終確認する
- settings.jsonの hooks 設定は `hookSpecificOutput.additionalContext` を使うdocs準拠JSONで返すパターンを推奨する
- プロジェクトレベル設定(./.claude/)とユーザーレベル設定(~/.claude/)の両方を確認する

### Never

- ユーザー確認なしに変更を適用しない
- スコアだけを根拠に改善を押し付けない — 対話で合意した項目のみ提案・適用する
- 既存のセキュリティhookやdenyルールの削除を提案しない
- bootstrapping-claudecodeと重複する「ゼロからのセットアップ」は行わない（本スキルは監査と改善）
- プロジェクトで使われていない言語のツールを推奨しない
- リンター/フォーマッター設定そのものの変更は提案しない（設定の「保護」のみ提案する）
- フィードバックループを遅くするような複雑なhookは推奨しない
- CLAUDE.mdの内容を勝手に書き換えない（提案のみ行い適用はユーザー判断）
