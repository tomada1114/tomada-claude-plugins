# Tomada Claude Plugins

Claude Code用のプラグイン集です。用途別に4つのプラグインを提供します。

## Installation

```bash
# 1. マーケットプレイスとして追加
/plugin marketplace add tomada1114/tomada-claude-plugins

# 2. 必要なプラグインをインストール
/plugin install claude-dev-kit@tomada-claude-plugins
/plugin install git-workflow@tomada-claude-plugins
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
| Skill | **claudecode-skill-creating** | Skillの作成・監査・リファクタ・トラブルシュートを統合的に支援。new/audit/convert/troubleshoot/add-subagentsモード |
| Skill | **bootstrapping-claudecode** | 新規プロジェクト向けClaude Codeセットアップウィザード。Rules、Hooks、MCP、CLAUDE.mdのテンプレート提供 |
| Skill | **capturing-claudecode** | tmux経由でClaude Codeのターミナル出力・UI画面をキャプチャ |
| Skill | **tmux-orchestrating** | tmuxで複数のClaude Codeセッションをオーケストレーション。並列タスク実行 |
| Skill | **team-discussion** | 3体のエージェント（提案者・批評者・統合者）による3ラウンドのマルチ視点ディスカッション。合意形成と実行可能な提案を生成 |
| Skill | **ccl-harness-engineering** | プロジェクトのClaude Code harness設定を監査。CLAUDE.md、Hooks、リンター、ADR、プリコミット設定を包括的にチェック |

**Use when:**
- 新しいSkillを作りたい・既存Skillを改善したい
- 新規プロジェクトでClaude Codeをセットアップしたい
- 複数セッションを並列実行したい
- Claude Codeの出力をキャプチャしたい
- 複雑な意思決定でマルチ視点ディスカッションを行いたい
- プロジェクトのharness設定をベストプラクティスに沿って監査したい

---

### 2. git-workflow

Gitワークフロー効率化ツール。コミットを自動化します。

```bash
/plugin install git-workflow@tomada-claude-plugins
```

| Command | Description |
|---------|-------------|
| **smart-commit** | 変更を論理単位でグループ化し、Conventional Commits形式で自動コミット |

**Usage:**
```bash
/smart-commit              # 変更を分析して自動コミット
```

---

### 3. agile-tools

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

### 4. content-tools

コンテンツ制作ツール。技術記事執筆とWordPress変換を支援します。

```bash
/plugin install content-tools@tomada-claude-plugins
```

| Type | Name | Description |
|------|------|-------------|
| Skill | **tomada-writing** | とまだ式技術記事執筆・改善スキル。構成ヒアリング→7軸並列評価で95点以上を目指すZenn記事作成 |
| Skill | **converting-to-wordpress-swell** | HTML/Markdown/テキストをWordPress Gutenbergブロック形式（SWELLテーマ）に変換 |

**Use when:**
- とまだ式のZenn技術記事を書きたい・リライトしたい
- 記事をWordPress（SWELLテーマ）に変換したい

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
