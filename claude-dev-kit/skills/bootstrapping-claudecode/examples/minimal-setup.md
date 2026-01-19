# Minimal Setup Example

最小限のセットアップ例。新規ユーザーにおすすめ。

## Components Installed

### User-Level (~/.claude/)

```
~/.claude/
├── CLAUDE.md           # user-level.md テンプレート
└── rules/
    ├── security.md     # 必須
    └── coding-style.md # 必須
```

### Project-Level

```
./CLAUDE.md             # project-basic.md テンプレート
```

## What This Provides

1. **基本的なセキュリティルール**
   - ハードコードされたシークレットの防止
   - 入力検証の要件

2. **コーディングスタイル**
   - 不変性の維持
   - ファイルサイズの制限
   - エラーハンドリング

3. **グローバル設定**
   - コア哲学
   - 個人的な好み

## Installation Command

```bash
# Create directories
mkdir -p ~/.claude/rules

# Copy CLAUDE.md
cp templates/claude-md/user-level.md ~/.claude/CLAUDE.md
cp templates/claude-md/project-basic.md ./CLAUDE.md

# Copy essential rules
cp templates/rules/security.md ~/.claude/rules/
cp templates/rules/coding-style.md ~/.claude/rules/
```

## Next Steps

セットアップ後、以下を検討:

1. **エージェントを追加**: `/tdd` や `/code-review` を使いたい場合
2. **フックを追加**: 自動フォーマットやconsole.log警告
3. **MCPを追加**: GitHub連携やデータベース操作

---

**この設定で十分な場合**: コーディングを始めてOK！

**もっと欲しい場合**: `custom-setup.md` または `full-setup.md` を参照。
