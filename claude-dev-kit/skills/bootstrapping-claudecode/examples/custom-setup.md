# Custom Setup Example

必要なものだけを選択するカスタムセットアップ例。

## Scenario: Frontend Developer

フロントエンド開発者向けの選択例。

### Selected Components

**Agents (4)**:
- code-reviewer
- tdd-guide
- build-error-resolver
- refactor-cleaner

**Rules (4)**:
- security
- coding-style
- testing
- git-workflow

**Hooks (4)**:
- posttool-prettier (自動フォーマット)
- posttool-typescript (型チェック)
- posttool-console-warn (console.log警告)
- stop-console-audit (最終監査)

**Commands (4)**:
- /tdd
- /code-review
- /build-fix
- /refactor-clean

**MCP (2)**:
- github
- context7

**CLAUDE.md**:
- user-level
- project-nextjs

### Installation

```bash
# Directories
mkdir -p ~/.claude/{agents,rules,commands}

# Agents (selected)
cp templates/agents/code-reviewer.md ~/.claude/agents/
cp templates/agents/tdd-guide.md ~/.claude/agents/
cp templates/agents/build-error-resolver.md ~/.claude/agents/
cp templates/agents/refactor-cleaner.md ~/.claude/agents/

# Rules (selected)
cp templates/rules/security.md ~/.claude/rules/
cp templates/rules/coding-style.md ~/.claude/rules/
cp templates/rules/testing.md ~/.claude/rules/
cp templates/rules/git-workflow.md ~/.claude/rules/

# Commands (selected)
cp templates/commands/tdd.md ~/.claude/commands/
cp templates/commands/code-review.md ~/.claude/commands/
cp templates/commands/build-fix.md ~/.claude/commands/
cp templates/commands/refactor-clean.md ~/.claude/commands/

# CLAUDE.md
cp templates/claude-md/user-level.md ~/.claude/CLAUDE.md
cp templates/claude-md/project-nextjs.md ./CLAUDE.md
```

---

## Scenario: Backend Developer (Python)

バックエンド開発者向けの選択例。

### Selected Components

**Agents (5)**:
- architect
- planner
- tdd-guide
- code-reviewer
- security-reviewer

**Rules (5)**:
- security
- coding-style
- testing
- patterns
- performance

**Hooks (2)**:
- pretool-git-push (push前確認)
- stop-console-audit (最終監査)

**Commands (5)**:
- /plan
- /tdd
- /code-review
- /test-coverage
- /update-docs

**MCP (3)**:
- github
- supabase
- memory

**CLAUDE.md**:
- user-level
- project-python

### Installation

```bash
# Directories
mkdir -p ~/.claude/{agents,rules,commands}

# Agents (selected)
cp templates/agents/architect.md ~/.claude/agents/
cp templates/agents/planner.md ~/.claude/agents/
cp templates/agents/tdd-guide.md ~/.claude/agents/
cp templates/agents/code-reviewer.md ~/.claude/agents/
cp templates/agents/security-reviewer.md ~/.claude/agents/

# Rules (selected)
cp templates/rules/security.md ~/.claude/rules/
cp templates/rules/coding-style.md ~/.claude/rules/
cp templates/rules/testing.md ~/.claude/rules/
cp templates/rules/patterns.md ~/.claude/rules/
cp templates/rules/performance.md ~/.claude/rules/

# Commands (selected)
cp templates/commands/plan.md ~/.claude/commands/
cp templates/commands/tdd.md ~/.claude/commands/
cp templates/commands/code-review.md ~/.claude/commands/
cp templates/commands/test-coverage.md ~/.claude/commands/
cp templates/commands/update-docs.md ~/.claude/commands/

# CLAUDE.md
cp templates/claude-md/user-level.md ~/.claude/CLAUDE.md
cp templates/claude-md/project-python.md ./CLAUDE.md
```

---

## How to Choose

### Must-Have (推奨)

- **security.md**: 常に必要
- **coding-style.md**: 常に必要
- **code-reviewer**: コード変更後のレビュー

### Nice-to-Have (状況に応じて)

- **tdd-guide**: テストを先に書く場合
- **architect**: 大きな設計決定がある場合
- **e2e-runner**: E2Eテストが必要な場合
- **posttool-prettier**: JS/TS を使用する場合
- **posttool-typescript**: TypeScript を使用する場合

### Optional (好みに応じて)

- **pretool-dev-server**: tmux を使用する場合
- **MCP servers**: 外部サービス連携が必要な場合

---

## Decision Matrix

| 開発タイプ | 推奨エージェント | 推奨ルール | 推奨フック |
|-----------|----------------|-----------|-----------|
| Frontend | code-reviewer, tdd-guide, build-error-resolver | security, coding-style, testing | prettier, typescript, console-warn |
| Backend | architect, planner, tdd-guide, security-reviewer | security, coding-style, testing, patterns | git-push, console-audit |
| Full-Stack | 全て | 全て | 全て |
| Script/CLI | code-reviewer, tdd-guide | security, coding-style | console-warn |

---

**Tip**: 少なく始めて、必要に応じて追加するのがベスト。
