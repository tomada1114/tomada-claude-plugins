---
name: transcription-fixer
description: とまだの文字起こし・音声入力（Whisper等）の誤変換・誤字脱字を自動修正するスキル。AI駆動開発、Claude Code、MCP、プログラミング用語の誤変換を専門的に修正。「文字起こしを修正」「誤変換を直して」「誤字脱字を修正」「音声入力を整理」「テキストをクリーンアップ」「変換ミスを直して」と言われたときに使用。Obsidianノートの文字起こし整理、技術用語の表記統一に最適。Use PROACTIVELY when fixing transcriptions, correcting voice input errors, or cleaning up Whisper output.
---

# Transcription Fixer（文字起こし修正スキル）

音声入力（Whisper等）で生成されたテキストの誤変換を自動修正するスキルです。

## 概要

とまだ（@muscle_coding）がよく使う専門用語を網羅した誤変換修正ルールを適用し、文字起こしテキストを正確な表記に変換します。

**得意分野**:
- Claude Code 関連用語（CLAUDE.md、サブエージェント、スキル、MCP等）
- AI駆動開発・Vibe Coding 関連
- プログラミング言語・フレームワーク名
- クラウドサービス・ツール名
- とまだ特有の文脈理解

## 使い方

### 基本的な使用

```
文字起こしテキストを修正してください：

[ここに文字起こしテキストを貼り付け]
```

### Obsidianノートの修正

```
このノートの誤変換を修正してください：
@path/to/note.md
```

## 修正ルール

### 1. 文脈優先の判断

同じ読みでも文脈によって正しい変換が異なります：

| 誤変換 | AI文脈 | 一般文脈 |
|--------|--------|----------|
| クラウド | Claude | クラウド（雲/サービス） |
| カーソル | Cursor | カーソル（矢印） |
| ノート | note（プラットフォーム） | ノート（メモ） |
| 俳句 | Haiku（モデル） | 俳句（詩） |

### 2. 主要な変換パターン

#### Claude Code 関連（最重要）
- クラウドコード → Claude Code
- cloud.md / クロード.md → CLAUDE.md
- クラウドルールズ / クロードルールズ → .claude/rules/
- グローブパターンズ → paths（Globパターン）
- サブージェント / サブ・エージェント → サブエージェント
- スキール / スキイル → Skills / スキル
- カスタム命令 → カスタムコマンド
- クラウドエムディー → CLAUDE.md
- ルールズ → .claude/rules/
- エムシーピー → MCP
- フロントマタ → frontmatter
- リードツール → Readツール
- オーパスプラン → opusplan
- プランモード → Plan mode
- コンテキストウィンドウ → Context Window
- コンパクティング / コンパクト化 → Compacting
- アウトプットスタイル → Output Style
- ツールユース → Tool Use
- ガードレール → Guardrail
- ハンドオフ → Handoff
- ランナー → Runner
- トレース → Trace
- ヘッドレス → Headless
- サンドボックス → Sandbox
- アローウドツールズ → allowed-tools
- ディセイブルモデルインボケーション → disable-model-invocation
- アーギュメントヒント → argument-hint
- ドルアーギュメンツ → $ARGUMENTS

#### スラッシュコマンド（読み上げ → 正式表記）
- スラッシュイニット → `/init`
- スラッシュクリア → `/clear`
- スラッシュコンパクト → `/compact`
- スラッシュコンテキスト → `/context`
- スラッシュメモリ / スラッシュメモリー → `/memory`
- スラッシュモデル → `/model`
- スラッシュコンフィグ → `/config`
- スラッシュパーミッションズ → `/permissions`
- スラッシュフックス → `/hooks`
- スラッシュエムシーピー → `/mcp`
- スラッシュエージェンツ → `/agents`
- スラッシュリジューム → `/resume`
- スラッシュリワインド → `/rewind`
- スラッシュビム → `/vim`
- スラッシュドクター → `/doctor`
- スラッシュスタッツ → `/stats`
- スラッシュコスト → `/cost`
- スラッシュユーセージ → `/usage`
- スラッシュエクスポート → `/export`
- スラッシュヘルプ → `/help`
- スラッシュエグジット → `/exit`
- スラッシュトゥードゥーズ / スラッシュトゥードゥー → `/todos`
- スラッシュステータス → `/status`
- スラッシュサンドボックス → `/sandbox`
- スラッシュログイン → `/login`
- スラッシュログアウト → `/logout`
- スラッシュバグ → `/bug`
- スラッシュアイディーイー / スラッシュアイディイー → `/ide`
- スラッシュプラグイン → `/plugin`
- スラッシュレビュー → `/review`
- スラッシュピーアールコメンツ → `/pr-comments`
- スラッシュセキュリティレビュー → `/security-review`
- スラッシュアドディル / スラッシュアッドディル → `/add-dir`
- スラッシュバッシーズ → `/bashes`
- スラッシュリリースノーツ → `/release-notes`
- スラッシュプライバシーセッティングス → `/privacy-settings`
- スラッシュターミナルセットアップ → `/terminal-setup`
- スラッシュステータスライン → `/statusline`
- スラッシュインストールギットハブアップ → `/install-github-app`

#### ディレクトリ・ファイル名
- ドットクロード → `.claude/`
- ドットクロードルールズ → `.claude/rules/`
- ドットクロードコマンズ / ドットクロードコマンド → `.claude/commands/`
- ドットクロードスキルズ → `.claude/skills/`
- ドットクロードエージェンツ → `.claude/agents/`
- ドットクロードイグノア → `.claudeignore`
- ドットエムシーピージェイソン → `.mcp.json`
- クロードデスクトップコンフィグ → `claude_desktop_config.json`
- セッティングスジェイソン → `settings.json`
- スキルエムディー → `SKILL.md`

#### フック関連
- プリツールユース → PreToolUse
- ポストツールユース → PostToolUse
- パーミッションリクエスト → PermissionRequest
- ユーザープロンプトサブミット → UserPromptSubmit
- セッションスタート → SessionStart
- セッションエンド → SessionEnd
- プリコンパクト → PreCompact
- サブエージェントストップ → SubagentStop

#### AIサービス・モデル名
- 苦労度 / 苦労ど → Claude
- クラウドソネット → Claude Sonnet
- クラウドオーパス → Claude Opus
- ハイク / 俳句 → Claude Haiku（AI文脈）
- チャットGPT → ChatGPT
- コーデックス → Codex CLI
- ジェミニ → Gemini
- クロードオーパスフォーポイントファイブ → claude-opus-4-5
- クロードソネットフォーポイントファイブ → claude-sonnet-4-5
- クロードハイクフォーポイントファイブ → claude-haiku-4-5
- クロードオーパスフォーポイントワン → claude-opus-4-1
- クロードソネットフォー → claude-sonnet-4
- ワンミリオントークンズ / 1ミリオントークン → 1M tokens
- ツーハンドレッドケートークンズ → 200K tokens
- エムトック → MTok
- メッセージズエーピーアイ → Messages API
- エージェントエスディーケー → Agent SDK
- エムシーピーコネクター → MCP Connector
- プロンプトキャッシング → Prompt Caching
- バッチプロセシング → Batch Processing
- ストラクチャードアウトプット / ストラクチャードアウトプッツ → Structured Outputs
- エクステンデッドシンキング → Extended Thinking

#### MCP関連
- プレイライトエムシーピー → Playwright MCP
- コンテキストセブン → Context7
- セレナ / セリーナ → Serena
- デスクトップコマンダー → Desktop Commander

#### フレームワーク・言語
- タイプスクリプト / TS → TypeScript
- HypeScript → TypeScript
- ネクストジェイエス → Next.js
- テイルウィンド → Tailwind CSS
- シャドシーエヌ → shadcn/ui

#### サービス・ツール
- スパベース → Supabase
- ベルセル / バーセル → Vercel
- プリズマ → Prisma
- ヴィート / バイト → Vite
- ギットハブ → GitHub
- ギットラブ → GitLab
- ビットバケット → Bitbucket
- ドッカー → Docker
- クーバネティス / クーベルネティス → Kubernetes
- テラフォーム → Terraform

#### IDE・開発環境
- ブイエスコード / ビジュアルスタジオコード → VS Code
- ジェットブレインズ → JetBrains
- インテリジェイ / インテリジェイアイデア → IntelliJ IDEA
- パイチャーム → PyCharm
- ウェブストーム → WebStorm
- ダブリューエスエル → WSL / WSL2
- デブコンテナ / デベロップメントコンテナ → Devcontainer
- ターミナル → Terminal
- アイターム → iTerm2

#### テスト・品質関連
- ハッピーパス → Happy path
- サッドパス → Sad path
- エッジケース → Edge case
- アンハッピーパス → Unhappy path
- レースコンディション → Race condition
- インテグレーションテスト → Integration test
- ユニットテスト → Unit test
- イーツーイー / エンドツーエンド → E2E / End-to-End

#### アーキテクチャ・設計
- ディーディーディー / ドメインドリブンデザイン → DDD (Domain Driven Design)
- オニオンアーキテクチャ → Onion Architecture
- クリーンアーキテクチャ → Clean Architecture
- ボーイスカウトルール → Boy Scout Rule
- ドライ → DRY (Don't Repeat Yourself)
- ソリッド → SOLID
- シーアイシーディー → CI/CD

#### よくある誤変換（一般的）
- ソース → src（ディレクトリ名の文脈）
- APIルース → api-rules
- コンセントマーク → コンセント（🔌）マーク
- 拡張紙 → 拡張子
- フォルダペース → フォルダベース
- トマダ → とまだ

### 3. 表記の統一ルール

- **大文字/小文字**: 公式表記に準拠（Claude Code, npm, YouTube）
- **スラッシュ**: shadcn/ui のように公式表記に準拠
- **ドット**: .claude, .env のように先頭ドットを保持
- **全角/半角**: 英数字は半角に統一
- **ファイル名**: typescript.md, general.md など小文字で統一

## 出力形式

**修正後のテキストのみを出力**します。

- 説明や注釈は付けない
- 修正箇所のハイライトは不要
- 元のテキスト構造（改行、箇条書き等）は保持

## 詳細な変換ルール

上記の変換パターンに加え、文脈に応じて適切な変換を行います。
新しい用語や誤変換パターンが見つかった場合は、このスキルファイルに追加してください。

## 対応する文脈

このスキルは以下の文脈を理解して修正を行います：

1. **Claude Code開発** - サブエージェント、スキル、カスタムコマンド、MCP
2. **AI駆動開発** - Vibe Coding、仕様駆動開発、コンテキストエンジニアリング
3. **コンテンツ制作** - Udemy講座、YouTube動画、Qiita/Zenn/note記事
4. **個人開発・フリーランス** - とまだの活動全般

## 注意事項

- 文脈から判断できない場合は、元のテキストを保持
- 過剰な修正は避ける
- 固有名詞は慎重に判断

## スキルの役割分担

### transcription-fixer（このスキル）
- **対象**: 全ての文字起こしテキスト（Markdown, テキスト, SRT等）
- **役割**: 誤変換の修正辞書・ルールを提供
- **やること**:
  - 「クロードコード」→「Claude Code」などの誤変換修正
  - 専門用語の正しい表記への変換
  - 句読点の追加

### srt-transcription-fixer
- **対象**: SRT字幕ファイル専用
- **役割**: SRTフォーマット固有の処理
- **やること**:
  - このスキル（transcription-fixer）の辞書を使って誤変換修正
  - SRT形式の構造（番号、タイムコード、空行）を維持
  - **タイムコードは変更しない**（発話タイミングに同期しているため）

### 使い分け
- **SRTファイル以外**: transcription-fixerのみ使用
- **SRTファイル**: srt-transcription-fixerを使用（内部でtranscription-fixerの辞書を参照）

## 更新履歴

- **2025-12-11**: 今回の動画文字起こしで発見した誤変換パターンを追加
  - cloud.md → CLAUDE.md
  - クラウドルールズ → .claude/rules/
  - グローブパターンズ → paths
  - HypeScript → TypeScript
  - APIルース → api-rules
  - 拡張紙 → 拡張子
  - フォルダペース → フォルダベース
