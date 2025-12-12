# Smart Commit Command

変更内容を自動的に分析し、関連する変更ごとにグループ化して適切なコミットを作成します。

## タスク

1. **変更状況の確認**
   - `git status` で変更ファイルを確認
   - `git diff` で staged/unstaged の変更内容を確認
   - すでに staged されているファイルがあれば、それを優先的に処理
   - **機密情報ファイルのみ除外し、それ以外はすべてコミット対象として扱う**

2. **変更のグループ化**
   変更内容とファイルタイプに基づいて、以下のルールでグループ化:

   - **テスト関連** (`__tests__/`, `.test.ts`, `.test.tsx`):
     - プレフィックス: `test:`
     - 新規テスト → "test: add ..."
     - テスト修正 → "test: fix ..."
     - テスト改善 → "test: improve ..."

   - **ドキュメント** (`.md`, `docs/`, `CLAUDE.md`, `README.md`):
     - プレフィックス: `docs:`
     - 新規 → "docs: add ..."
     - 更新 → "docs: update ..."

   - **設定ファイル** (`.json`, `.config.js`, `tailwind.config.js`, `.claude/`):
     - プレフィックス: `chore:`
     - "chore: update ..." または "chore: configure ..."

   - **UI/コンポーネント** (`src/components/`, `src/app/`, `.tsx`):
     - 新機能 → `feat:` (add, implement)
     - 既存修正 → `refactor:` (update, improve, refactor)
     - バグ修正 → `fix:` (fix)

   - **ビジネスロジック** (`src/domain/`, `src/application/`, `src/infrastructure/`):
     - 新機能 → `feat:`
     - リファクタリング → `refactor:`
     - バグ修正 → `fix:`

   - **スタイル/デザイン** (`src/ui/`, `tokens.ts`, スタイル関連の変更):
     - `style:` または `feat:` (デザインシステム更新の場合)

3. **コミット・プッシュの実行**
   各グループごとに:
   - 関連ファイルを `git add` でステージング
   - 簡潔で明確なコミットメッセージを生成 (日本語、1行)
   - 変更の「なぜ」ではなく「何を」を記述
   - `git commit -m "メッセージ"` で一行形式でコミット（HEREDOC不使用）
   - `git push` 実行

4. **最終確認**
   - 全コミット完了後に `git status` で残りの変更を確認
   - 未コミットのファイルが残っている場合は理由を説明 (機密情報ファイルのみが除外される想定)

## 重要な注意事項

- **1グループ = 1コミット**: 関連する変更をまとめて単一のコミットに
- **atomic commits**: 各コミットは独立して意味を持つこと
- **機密情報チェック**: 以下のファイルは絶対にコミットしない
  - `.env`、`.env.local`、`.env.production` などの環境変数ファイル
  - `**/credentials.json`、`**/secrets.json`、`**/private-key.json` などの明示的な機密情報ファイル
  - `**/*password*`、`**/*secret*`、`**/*key*.pem` などの機密情報を含むファイル名パターン
- **基本方針**: 上記の機密情報ファイル以外は、**すべてコミット対象とする**
  - 設定ファイル (`.claude/`, `*.json`, `*.md`)
  - ドキュメント (`*.md`, `CLAUDE.md`, `README.md`)
  - ソースコード (`*.ts`, `*.tsx`, `*.js`, `*.jsx`)
  - テストファイル (`*.test.*`, `__tests__/`)
  - すべての作業中ファイルを積極的にコミット
- **実行前の状態確認**: 最初に現在のブランチと変更状況を表示
- **エラーハンドリング**: コミットが失敗した場合は理由を説明し、次のグループに進む

## 使用例

```bash
# 使い方
/smart-commit

# 実行例:
# グループ1: test: デザインシステムコンポーネントのテスト追加
#   - src/components/ui/list-item/__tests__/list-item.test.tsx
#   - src/components/ui/typography/__tests__/typography.test.tsx
#
# グループ2: feat: デザインシステムコンポーネントの改善
#   - src/components/ui/list-item/index.tsx
#   - src/components/ui/typography/index.tsx
#
# グループ3: chore: デザイントークンとTailwind設定を更新
#   - src/ui/tokens.ts
#   - tailwind.config.js
```

## 実装の開始

上記のルールに従って、変更内容を分析し、適切にグループ化してコミットを実行してください。
