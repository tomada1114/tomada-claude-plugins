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
/plugin install transcription-tools@tomada-claude-plugins
/plugin install agile-tools@tomada-claude-plugins
/plugin install content-tools@tomada-claude-plugins

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
| Skill | **claude-skill-creator** | Skillの作成ガイド。YAML frontmatter、ディレクトリ構造、テンプレート |
| Skill | **custom-commands-creator** | カスタムコマンドの作成ガイド。引数パターン、Bash統合 |
| Skill | **sub-agents-creator** | サブエージェントの作成ガイド。発動率向上のCLAUDE.md連携パターン |
| Skill | **claude-rules-organizer** | 肥大化したCLAUDE.mdを`.claude/rules/`へモジュール分割 |
| Skill | **claude-code-knowledge** | Claude Codeの機能・設定リファレンス。公式ドキュメントベース |
| Skill | **claude-code-headless** | ヘッドレスモード（-p フラグ）でのスクリプト連携ガイド |
| Command | **add-description-to-memory** | CLAUDE.mdのSkill Activation Rulesを自動同期 |

**Use when:**
- 新しいSkill/Command/Agentを作りたい
- エージェントが発動しない問題を解決したい
- CLAUDE.mdが大きくなりすぎた
- Claude Codeの機能や設定を調べたい

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

### 4. transcription-tools

日本語文字起こし修正ツール。Whisper等の誤変換を自動修正します。

```bash
/plugin install transcription-tools@tomada-claude-plugins
```

| Type | Name | Description |
|------|------|-------------|
| Skill | **transcription-fixer** | 音声入力・文字起こしの誤変換を自動修正。Claude Code、AI駆動開発用語に特化 |
| Skill | **srt-transcription-fixer** | SRT字幕ファイル専用の修正。改行位置の最適化、誤変換修正 |
| Command | **/srt-transcription-fixer:fix-srt** | SRTファイルを修正するコマンド |

**Use when:**
- Whisper等の文字起こしを修正したい
- 「クロードコード」→「Claude Code」などの変換
- SRT字幕ファイルの誤変換・改行位置を修正したい

---

### 5. agile-tools

アジャイル開発ツール。要件設計とGitHub Issue作成を支援します。

```bash
/plugin install agile-tools@tomada-claude-plugins
```

| Skill | Description |
|-------|-------------|
| **agile-ticket-planner** | GitHub Issue作成。並列作業の特定、依存関係管理、git worktree戦略 |
| **product-requirements-designer** | 曖昧な要件を詳細化。PdM視点の質問→ワイヤーフレーム→チケット分割 |

**Use when:**
- 要件からGitHub Issueを作成したい
- 曖昧なアイデアを詳細な仕様に落としたい
- 並列作業できるチケットを特定したい

---

### 6. content-tools

コンテンツ制作ツール。YouTube台本作成などを支援します。

```bash
/plugin install content-tools@tomada-claude-plugins
```

| Skill | Description |
|-------|-------------|
| **video-script-writing** | YouTube台本作成。テック動画（AI駆動開発・プログラミング）向け7軸評価システム |

**Use when:**
- 記事やメモからYouTube台本を作成したい
- テック系動画のスクリプトを書きたい

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

## License

MIT
