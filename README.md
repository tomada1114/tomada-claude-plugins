# Tomada Claude Plugins

Claude Code用のプラグイン集です。用途別に6つのプラグインを提供します。

## Installation

```bash
# 1. マーケットプレイスとして追加
/plugin marketplace add tomada1114/tomada-claude-plugins

# 2. 必要なプラグインをインストール
/plugin install claude-dev-kit@tomada-claude-plugins
/plugin install git-workflow@tomada-claude-plugins
/plugin install test-advisor@tomada-claude-plugins
/plugin install agile-tools@tomada-claude-plugins
/plugin install content-tools@tomada-claude-plugins
/plugin install openai-agents-guides@tomada-claude-plugins

# または対話的にブラウズ
/plugin
```

---

## Available Plugins

### 1. claude-dev-kit

Claude Code拡張開発キット。Skill、Command、Agent、Rulesの作成を支援します。

```bash
/plugin install claude-dev-kit@tomada-claude-plugins
```

| Type | Name | Description |
|------|------|-------------|
| Skill | **claudecode-skill-creating** | Skillの作成ガイド。YAML frontmatter、ディレクトリ構造、テンプレート |
| Skill | **creating-commands** | カスタムコマンドの作成ガイド。引数パターン、Bash統合 |
| Skill | **creating-subagents** | サブエージェントの作成ガイド。発動率向上のCLAUDE.md連携パターン |
| Skill | **claudecode-rules-organizing** | 肥大化したCLAUDE.mdを`.claude/rules/`へモジュール分割 |
| Skill | **claudecode-docs-referencing** | Claude Codeの機能・設定リファレンス。公式ドキュメントベース |
| Skill | **claudecode-headless-automating** | ヘッドレスモード（-p フラグ）でのスクリプト連携ガイド |
| Skill | **bootstrapping-claudecode** | 新規プロジェクト向けClaude Codeセットアップウィザード。Rules、Hooks、MCP、CLAUDE.mdのテンプレート提供 |
| Skill | **capturing-claudecode** | tmux経由でClaude Codeのターミナル出力・UI画面をキャプチャ |
| Skill | **tmux-orchestrating** | tmuxで複数のClaude Codeセッションをオーケストレーション。並列タスク実行 |
| Skill | **team-discussion** | 3体のエージェント（提案者・批評者・統合者）による3ラウンドのマルチ視点ディスカッション。合意形成と実行可能な提案を生成 |
| Command | **add-description-to-memory** | CLAUDE.mdのSkill Activation Rulesを自動同期 |

**Use when:**
- 新しいSkill/Command/Agentを作りたい
- エージェントが発動しない問題を解決したい
- CLAUDE.mdが大きくなりすぎた
- Claude Codeの機能や設定を調べたい
- 新規プロジェクトでClaude Codeをセットアップしたい
- 複数セッションを並列実行したい
- Claude Codeの出力をキャプチャしたい
- 複雑な意思決定でマルチ視点ディスカッションを行いたい

---

### 2. git-workflow

Gitワークフロー効率化ツール。コミットとPR作成を自動化します。

```bash
/plugin install git-workflow@tomada-claude-plugins
```

| Command | Description |
|---------|-------------|
| **smart-commit** | 変更を論理単位でグループ化し、Conventional Commits形式で自動コミット |
| **pr-description** | PRのタイトルと説明を自動生成 |

**Usage:**
```bash
/smart-commit              # 変更を分析して自動コミット
/pr-description 123        # PR #123 の説明を生成
```

---

### 3. test-advisor

テスト戦略アドバイザー。包括的なテスト計画を提案します。

```bash
/plugin install test-advisor@tomada-claude-plugins
```

| Agent | Description |
|-------|-------------|
| **test-strategy-advisor** | Happy/Sad/Edge/Unhappy pathを網羅したテスト計画を提案 |

**Features:**
- Given/When/Then 形式のテスト構造ガイド
- 境界値テスト、例外テストの設計
- 外部依存（API、DB）のモック戦略
- 100%ブランチカバレッジを目標とした計画

**Triggers:**
- "writing tests", "test strategy", "test coverage"
- "what tests should I write", "how do I test this"

---

### 4. agile-tools

アジャイル開発ツール。要件設計とGitHub Issue作成を支援します。

```bash
/plugin install agile-tools@tomada-claude-plugins
```

| Skill | Description |
|-------|-------------|
| **planning-tickets** | GitHub Issue作成。並列作業の特定、依存関係管理、git worktree戦略 |
| **refining-requirements** | 曖昧な要件を質問形式で詳細化。PdM視点でモバイルUX・アクセシビリティを網羅 |
| **designing-wireframes** | ASCIIワイヤーフレーム・ユーザーフロー・横断的仕様を設計 |
| **ui-ux-designing** | UI/UXデザインコンセプトの策定。デザイン原則、カラー、タイポグラフィ |

**Use when:**
- 要件からGitHub Issueを作成したい
- 曖昧なアイデアを詳細な仕様に落としたい
- 並列作業できるチケットを特定したい
- 画面設計やワイヤーフレームを作成したい

---

### 5. content-tools

コンテンツ制作ツール。YouTube台本作成、文字起こし修正、SRT字幕修正を支援します。

```bash
/plugin install content-tools@tomada-claude-plugins
```

| Type | Name | Description |
|------|------|-------------|
| Skill | **video-script-writing** | YouTube台本作成。テック動画（AI駆動開発・プログラミング）向け7軸評価システム |
| Skill | **fixing-transcriptions** | 音声入力・文字起こしの誤変換を自動修正。Claude Code、AI駆動開発用語に特化 |
| Skill | **fixing-srt-subtitles** | SRT字幕ファイル専用の修正。24文字ルール、タイムコード按分による長文分割 |
| Skill | **implementing-nextjs-blog** | Next.js 15 App Routerでのマークダウンブログ実装ガイド。静的生成、シンタックスハイライト、スクロール追従TOC、カテゴリ、SEO対応 |
| Skill | **converting-to-wordpress-swell** | HTML/Markdown/テキストをWordPress Gutenbergブロック形式（SWELLテーマ）に変換 |
| Agent | **srt-splitter** | 長い字幕テキスト（24文字超）を文法的に自然な位置で分割提案 |
| Command | **/video-script-writing:generate** | ソースファイルからYouTube台本を生成 |
| Command | **/fixing-srt-subtitles:fix-srt** | 指定ディレクトリのSRTファイルを修正 |
| Command | **/fixing-srt-subtitles:split-long-subtitles** | 長い字幕テキストを分割 |

**Use when:**
- 記事やメモからYouTube台本を作成したい
- テック系動画のスクリプトを書きたい
- Whisper等の文字起こしを修正したい
- SRT字幕ファイルの誤変換・改行位置を修正したい
- Next.jsプロジェクトにマークダウンブログを追加したい
- 記事をWordPress（SWELLテーマ）に変換したい

---

### 6. openai-agents-guides

OpenAI Agents SDKリファレンスガイド。エージェント作成からマルチエージェントオーケストレーションまで。

```bash
/plugin install openai-agents-guides@tomada-claude-plugins
```

| Agent | Description |
|-------|-------------|
| **openai-agent-basics-guide** | エージェント作成と基本設定ガイド。Agent class、instructions、output types |
| **openai-runner-workflow-guide** | エージェント実行とワークフロー管理。Runner API、run_sync、run_streamed |
| **openai-handoff-coordinator** | エージェント間委譲とマルチエージェント調整。input_filter、handoff callbacks |
| **openai-tools-specialist** | ツール定義と実装。@function_tool、hosted tools、agents as tools |
| **openai-multi-agent-orchestrator** | 高度なマルチエージェントパターン。階層型、ルーティング、並列実行 |
| **openai-session-memory-expert** | セッション管理と会話履歴。SQLiteSession、RedisSession |
| **openai-version-specialist** | 最新バージョン情報、外部ライブラリドキュメント、トラブルシューティング |

**Use when:**
- OpenAI Agents SDKでエージェントを構築したい
- ハンドオフパターンを実装したい
- マルチエージェントシステムを設計したい
- セッション管理を実装したい

---

## Requirements

- Claude Code CLI

## Author

**とまだ (@muscle_coding)**

AI駆動開発の実践者・教育者

### Links

| Platform | URL |
|----------|-----|
| X (Twitter) | https://x.com/muscle_coding |
| Zenn | https://zenn.dev/tmasuyama1114 |
| YouTube | https://www.youtube.com/@vibe-coding-studio |
| Udemy クーポン | https://www.vibecodingstudio.dev/coupons?topic=claude-code |
| コミュニティ | https://www.vibecodingstudio.dev/community |

仕事の依頼、執筆の依頼、その他相談などは X の DM へお気軽にどうぞ。

## Acknowledgments

### bootstrapping-claudecode

`bootstrapping-claudecode` スキルは [everything-claude-code](https://github.com/affaan-m/everything-claude-code) by [Affaan M](https://github.com/affaan-m) を参考に作成しました。Claude Code のベストプラクティス集として非常に優れたリポジトリです。このスキルでは、そのエッセンスを対話形式のセットアップウィザードとして再構成し、独自のカスタマイズを加えています。

## License

MIT
