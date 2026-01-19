---
name: fixing-transcriptions
description: とまだの文字起こし・音声入力（Whisper等）の誤変換・誤字脱字を自動修正するスキル。AI駆動開発、Claude Code、MCP、プログラミング用語の誤変換を専門的に修正。「文字起こしを修正」「誤変換を直して」「誤字脱字を修正」「音声入力を整理」「テキストをクリーンアップ」「変換ミスを直して」と言われたときに使用。Obsidianノートの文字起こし整理、技術用語の表記統一に最適。Use PROACTIVELY when fixing transcriptions, correcting voice input errors, or cleaning up Whisper output.
---

# Transcription Fixer（文字起こし修正スキル）

音声入力（Whisper等）で生成されたテキストの誤変換を**2段階方式**で自動修正するスキルです。

## 概要

**Phase 1（機械的置換）** + **Phase 2（LLM判断）** の2段階で処理します。

```
Phase 1: Python スクリプトで辞書ベースの確実な置換（高速・コストゼロ）
    ↓
Phase 2: LLM で文脈依存の微妙な判断（高品質）
```

## 処理フロー

### Phase 1: 機械的置換

Pythonスクリプトで辞書ベースの置換を実行：

```bash
python3 ~/.claude/skills/fixing-transcriptions/scripts/fix_transcription.py <path>
```

**オプション**:
- `--dry-run`: 変更を適用せずプレビュー
- `--json`: JSON形式で出力（LLM連携用）

**出力例**:
```
Phase 1: 機械的置換 完了
処理ファイル数: 30件
修正あり: 22件
総修正件数: 150件

修正内容:
  - file1.txt: 5件 (クロードコード→Claude Code, cloud.md→CLAUDE.md)
  - file2.txt: 3件 (アンソロピック→Anthropic, フックス→Hooks)
```

### Phase 2: LLM判断

Phase 1で処理できない文脈依存のパターンをLLMで判断：

- 「クラウド」→ Claude or クラウド？
- 「カーソル」→ Cursor or カーソル？
- 「ノート」→ note or ノート？

## 辞書ファイル

`~/.claude/skills/fixing-transcriptions/dictionaries/misconversion-dict.json`

### 構造

```json
{
  "exact_match": {
    "ai_services": { "クロードコード": "Claude Code", ... },
    "claude_code_files": { "cloud.md": "CLAUDE.md", ... },
    "claude_code_features": { "フックス": "Hooks", ... },
    ...
  },
  "regex_patterns": [
    { "pattern": "...", "replacement": "..." }
  ],
  "context_dependent": [
    { "pattern": "クラウド", "candidates": ["Claude", "クラウド"], "hint": "..." }
  ]
}
```

### カテゴリ

| カテゴリ | 内容 |
|----------|------|
| `ai_services` | Claude Code, Anthropic, ChatGPT等 |
| `claude_code_files` | CLAUDE.md, settings.json, .claude/rules/ |
| `claude_code_features` | Hooks, Skills, サブエージェント等 |
| `claude_code_commands` | /init, /clear, /compact等 |
| `claude_code_tools` | Read, Write, Edit, Bash等 |
| `mcp_related` | MCP, Playwright MCP, Context7等 |
| `programming_languages` | TypeScript, Python, Node.js等 |
| `dev_tools` | npm, Git, Prettier, VS Code等 |
| `common_errors` | 過読性→可読性, エラー形→エラー系等 |

## 使い方

### コマンドから（推奨）

```
/fix-transcriptions /path/to/file.txt
/fix-transcriptions /path/to/directory/
```

### 直接スキルを使う

```
このテキストの誤変換を修正してください：
[テキストを貼り付け]
```

## 文脈依存パターン

以下のパターンはLLM（Phase 2）で判断：

| パターン | AI文脈 | 一般文脈 |
|----------|--------|----------|
| クラウド | Claude | クラウド（雲/サービス） |
| カーソル | Cursor | カーソル（矢印） |
| ノート | note（プラットフォーム） | ノート（メモ） |
| 俳句 | Haiku（モデル） | 俳句（詩） |
| ソネット | Sonnet（モデル） | ソネット（詩） |
| 禅/ゼン | Zenn（ブログ） | 禅（仏教） |

## 辞書への追加

新しいパターンを追加する場合：

1. JSON辞書を編集: `~/.claude/skills/fixing-transcriptions/dictionaries/misconversion-dict.json`
2. 適切なカテゴリに追加
3. `context_dependent` は文脈判断が必要なもののみ

## スキルの役割分担

### fixing-transcriptions（このスキル）
- **対象**: 全ての文字起こしテキスト
- **役割**: Phase 1 + Phase 2 で誤変換修正

### fixing-srt-subtitles
- **対象**: SRT字幕ファイル専用
- **役割**: SRTフォーマット固有の処理 + このスキルの辞書を使用

## 関連ファイル

```
~/.claude/skills/fixing-transcriptions/
├── SKILL.md                    # このファイル
├── dictionaries/
│   └── misconversion-dict.json # 誤変換辞書（300+パターン）
└── scripts/
    └── fix_transcription.py    # Phase 1 スクリプト
```

## 更新履歴

- **2025-01-16**: Phase 1（機械的置換）+ Phase 2（LLM判断）の2段階方式に改善
  - Pythonスクリプトによる高速な機械的置換を追加
  - JSON辞書形式に移行（misconversion-note.md → misconversion-dict.json）
  - 300+パターンをカテゴリ別に整理
