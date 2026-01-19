# User-Level CLAUDE.md

グローバル設定用。`~/.claude/CLAUDE.md` に配置。

---

## Core Philosophy

あなたは Claude Code です。複雑なタスクには専門のエージェントとスキルを使用します。

**Key Principles:**
1. **Agent-First**: 複雑な作業は専門エージェントに委譲
2. **Parallel Execution**: 可能な場合は Task tool で複数エージェントを並列実行
3. **Plan Before Execute**: 複雑な操作は Plan Mode で計画
4. **Test-Driven**: テストを先に書く
5. **Security-First**: セキュリティは妥協しない

---

## Modular Rules

詳細なガイドラインは `~/.claude/rules/` に:

| Rule File | Contents |
|-----------|----------|
| security.md | セキュリティチェック、シークレット管理 |
| coding-style.md | 不変性、ファイル構成、エラーハンドリング |
| testing.md | TDDワークフロー、80%カバレッジ要件 |
| git-workflow.md | コミット形式、PRワークフロー |
| agents.md | エージェント調整、どのエージェントをいつ使うか |
| patterns.md | APIレスポンス、リポジトリパターン |
| performance.md | モデル選択、コンテキスト管理 |

---

## Available Agents

`~/.claude/agents/` に配置:

| Agent | Purpose |
|-------|---------|
| planner | 機能実装計画 |
| architect | システム設計とアーキテクチャ |
| tdd-guide | テスト駆動開発 |
| code-reviewer | 品質・セキュリティレビュー |
| security-reviewer | セキュリティ脆弱性分析 |
| build-error-resolver | ビルドエラー解決 |
| e2e-runner | Playwright E2Eテスト |
| refactor-cleaner | デッドコード削除 |
| doc-updater | ドキュメント更新 |

---

## Personal Preferences

### Code Style
- コードやドキュメントに絵文字を使用しない
- 不変性を優先 - オブジェクトや配列をミューテートしない
- 大きなファイルより小さなファイルを多く
- 通常 200-400 行、最大 800 行/ファイル

### Git
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
- コミット前にローカルでテスト
- 小さく、集中したコミット

### Testing
- TDD: テストを先に書く
- 最低 80% カバレッジ
- クリティカルなフローには Unit + Integration + E2E

---

## Success Metrics

以下を達成したら成功:
- すべてのテストがパス (80%+ カバレッジ)
- セキュリティ脆弱性なし
- コードが読みやすく保守可能
- ユーザー要件を満たしている

---

**Philosophy**: Agent-first design, parallel execution, plan before action, test before code, security always.
