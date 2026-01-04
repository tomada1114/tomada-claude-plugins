# 15. メモリ管理(CLAUDE.md の活用)

## CLAUDE.md の役割

CLAUDE.md は Claude がプロジェクトに関する情報を記憶するためのファイルです。セッションをまたいで情報を永続化し、毎回同じ説明を繰り返す必要をなくします。

:::message
CLAUDE.md という名前は**大文字で記述する**のがポイントです。`claude.md` や `Claude.md` ではなく、`CLAUDE.md` と指定してください。ファイル名の大文字・小文字の違いで認識されないことがあります。
:::

## CLAUDE.md があると何が変わるか

CLAUDE.md を配置すると、開発体験が大きく変わります:

- **コンテキストの共有**: プロジェクトの文脈を理解した状態で作業開始
- **説明の省略**: 毎回同じ説明をする手間がなくなる
- **規約の遵守**: コーディング規約を守らせやすくなる
- **チーム共有**: 全員が同じルールで Claude Code を使える

ただし、CLAUDE.md はあくまで「指示」であり、Claude がすべてを厳密に従うわけではないことには注意が必要です。複雑なルールや曖昧な表現は意図通りに解釈されない場合もあります。そのため、ルールは**具体的かつ簡潔**に記述することをおすすめします。

### RPGで例えると：「世界観」

RPGには「中世ファンタジー」「魔法が存在する」といった**世界観**があります。これはどのエリアにいても変わらない前提条件です。

CLAUDE.md には、この「世界観」を書きます：

| 項目 | ゲームの世界観 | CLAUDE.mdに書くこと |
|------|--------------|------------------|
| **目的** | 「モンスターを倒していくRPG」 | プロダクトの目的 |
| **前提** | 「中世ファンタジー」 | 使用技術 |
| **構成** | 「火山、海底、氷の洞窟などのエリア」 | ディレクトリ構成 |
| **設定** | 「モンスターにはエリア・HP・弱点がある」 | データ構造・命名規則 |
| **仲間** | 「魔法使いや道案内人がいる」 | 利用可能なサブエージェント |
| **スタイル** | 「主人公は勇気ある行動をする」 | コーディングスタイル |

海底エリアにいても、火山にいても、「魔法が存在する」という世界観は変わりません。**特定のエリアだけでなく、プロジェクト全体を通じて常に適用される前提条件**を CLAUDE.md に書くのです。

> **Source**: https://zenn.dev/yahsan2/articles/claude-code-game-analogy (2025-12-17 確認)

## CLAUDE.md の読み込み階層

Claude Code は以下の優先順位でメモリを読み込みます（上位が優先）:

| 優先度 | タイプ | 場所 | 用途 |
|--------|--------|------|------|
| 1（最高）| Enterprise policy | macOS: `/Library/Application Support/ClaudeCode/CLAUDE.md`<br/>Linux: `/etc/claude-code/CLAUDE.md`<br/>Windows: `C:\Program Files\ClaudeCode\CLAUDE.md` | 組織全体のルール |
| 2 | Project memory | `./CLAUDE.md` または `./.claude/CLAUDE.md` | チーム共有 |
| 3 | Project rules | `./.claude/rules/*.md` | モジュール化したルール |
| 4 | User memory | `~/.claude/CLAUDE.md` | 個人用（全プロジェクト） |
| 5（最低）| Project local | `./CLAUDE.local.md` | 個人用（このプロジェクトのみ） |

### .claude/rules/ ディレクトリ

`.claude/rules/` に配置した `.md` ファイルは自動的にプロジェクトメモリとして読み込まれます。

**パス指定による条件付き適用**:

```markdown
---
paths: src/api/**/*.ts
---

# API Development Rules
- すべてのAPIエンドポイントで入力バリデーションを実装
```

**サポートされているglobパターン**:

| パターン | マッチ |
|---------|--------|
| `**/*.ts` | 任意のディレクトリのTypeScriptファイル |
| `src/**/*` | `src/`下のすべてのファイル |
| `*.md` | プロジェクトルートのMarkdownファイル |
| `{src,lib}/**/*.ts` | 複数パターンの組み合わせ |

### @記法によるファイル参照

@記法は、CLAUDE.md内から他のファイルを参照するための仕組みです。詳細な仕様書やスタイルガイドを別ファイルに分離し、CLAUDE.md本体をシンプルに保つことができます。

**基本的な書式**:

```markdown
## API仕様
@docs/API_SPECIFICATION.md

## コーディングスタイル
@docs/CODING_STYLE.md

## データベーススキーマ
@docs/DATABASE_SCHEMA.md
```

**パスの書き方**:

パスはプロジェクトルートからの相対パスで記述します。

| 記述例 | 参照先 |
|-------|--------|
| `@docs/spec.md` | プロジェクトルートの `docs/spec.md` |
| `@src/types/README.md` | `src/types/README.md` |
| `@CONTRIBUTING.md` | プロジェクトルートの `CONTRIBUTING.md` |

**複数ファイルの参照**:

カテゴリ別に整理して記述:

```markdown
### API関連
@docs/api/endpoints.md
@docs/api/authentication.md

### 設計ドキュメント
@docs/architecture/overview.md
@docs/architecture/database.md
```

**コードスパン（バッククォート）で囲むと評価されない**:

```markdown
❌ `@docs/spec.md`     → 評価されない（ただの文字列）
✅ @docs/spec.md       → 評価される（ファイルが読み込まれる）
```

Markdown内で@記法の例を示したい場合は、意図的にバッククォートで囲むと便利です。

**@記法と.claude/rules/の使い分け**:

| 項目 | @記法 | .claude/rules/ |
|-----|-------|----------------|
| 配置場所 | 任意（プロジェクト内のどこでも） | `.claude/rules/`ディレクトリ固定 |
| 参照方法 | CLAUDE.md内で明示的に記述 | 自動的に読み込まれる |
| 条件付き適用 | なし | pathsフロントマターで可能 |
| 用途 | 既存ドキュメントの参照 | プロジェクトルール |

**注意点**:

- **コンテキストの消費**: 参照先ファイルが大きいとコンテキストを消費する。本当に必要なファイルだけを参照すること
- **相対パスの起点**: 常にプロジェクトルート。`../docs/spec.md` のような親ディレクトリ参照は使えない
- **更新の反映**: 参照先ファイルを更新した場合、次回のClaude Code起動時に反映される

### CLAUDE.local.md

個人的なプロジェクト固有設定用のファイル。**自動的に`.gitignore`に追加**されます。

**用途**:
- サンドボックスURL
- テストデータのパス
- 環境固有の設定
- チームと共有したくない個人設定

### グローバルルール（User memory）の設定方法

`~/.claude/CLAUDE.md` に配置すると、どのプロジェクトで Claude Code を起動しても、そのルールが自動的に読み込まれます。

**プロジェクト単位とグローバルの使い分け**:

| 種類 | 配置場所 | 用途 |
|------|---------|------|
| プロジェクト単位 | プロジェクトルート | そのプロジェクト固有のルール（技術スタック、ディレクトリ構造など） |
| グローバル | `~/.claude/CLAUDE.md` | 全プロジェクト共通のルール（コード品質の基準、エラーハンドリング方針など） |

たとえば、「エラーを握りつぶさない」「セキュリティを意識する」「テストをスキップしない」といった普遍的なルールはグローバルに、「このプロジェクトでは React を使う」「コンポーネントは src/components/ に配置する」といった固有のルールはプロジェクト単位で設定するのがおすすめです。

**macOS / Linux での設定手順**:

```bash
# フォルダを作成（すでにあれば不要）
mkdir -p ~/.claude

# ファイルを作成
touch ~/.claude/CLAUDE.md

# VS Code で開いて編集
code ~/.claude/CLAUDE.md

# または vim で開いて編集
vim ~/.claude/CLAUDE.md
```

**Windows (PowerShell) での設定手順**:

```powershell
# フォルダを作成
New-Item -Path "$HOME\.claude" -ItemType Directory -Force

# ファイルを作成
New-Item -Path "$HOME\.claude\CLAUDE.md" -ItemType File -Force
```

## CLAUDE.md の構造

### 推奨セクション

```markdown
# プロジェクト名

## 概要
プロジェクトの目的と主要機能の簡潔な説明

## 技術スタック
使用している言語、フレームワーク、ライブラリ

## ディレクトリ構造
主要なディレクトリとその役割

## アーキテクチャ
システムの設計思想とパターン

## コーディング規約
チームで守るべきルール

## 開発ワークフロー
よく使うコマンドと手順

## 注意事項
特に気をつけるべきポイント
```

## 効果的な CLAUDE.md の作成

### 1. /init で自動生成

最も簡単な方法:

```bash
claude
/init
```

`/init` を実行すると、Claude Code は以下の4つの処理を順番に行います:

1. まず、プロジェクト構造を分析して、ファイルとディレクトリの構成、使用言語・フレームワークを検出する
2. 次に、README.md、package.json、requirements.txt などの重要なファイルを読み取る
3. 続いて、プロジェクト概要、技術スタック、ディレクトリ構造、開発ガイドラインを含む CLAUDE.md を生成する
4. 最後に、生成された内容の確認を求める

生成された内容がすべて適切とは限りませんが、ゼロから書くよりはるかに効率的なので、生成後に手動で調整していくのがおすすめです。

### 2. 段階的に育てる

プロジェクトの進化に合わせて更新:

```
> CLAUDE.md を更新して、新しい認証システムの情報を追加して

> コーディング規約セクションに TypeScript のルールを追加して
```

### 3. 具体的な情報を含める

❌ **曖昧**:
```markdown
## コーディング規約
良いコードを書くこと
```

✅ **具体的**:
```markdown
## コーディング規約
- 関数は50行以内
- ネストは3段階まで
- 早期 return を活用
- Magic number は定数化
- TypeScript の strict モード必須
```

### 4. 効果的な指示の書き方パターン

CLAUDE.md に記述する指示は、**具体的かつ簡潔であること**がポイントです。

**やってほしいこと（推奨事項）**

推奨事項は「〜してください」「〜を使ってください」という形式で記述します:

- エラーハンドリングを考慮して実装してください
- import は src/ からの絶対パスを使用してください
- 実装前にテストコードを作成し、テストをパスさせるよう実装してください

**やってほしくないこと（禁止事項）**

禁止事項は「〜しないでください」「〜は避けてください」という形式で記述します:

- 型定義として any 型を使用しないでください
- マジックナンバーを直接書くことは避けてください
- 既存の API 仕様を勝手に変更しないでください

## CLAUDE.md の最適なサイズ

### 推奨: フォーカスを絞った要点

公式ドキュメントに明確な行数制限はありませんが、以下のベストプラクティスが推奨されています:

- **CLAUDE.md本体**: 重要な情報に集中
- **`.claude/rules/`**: トピック別に分割（code-style.md、testing.md、security.mdなど）
- **インポート機能**: `@path/to/file` で外部ファイルを参照

### 大きくなりすぎた場合

詳細情報は `.claude/rules/` に分離:

```
.claude/
├── CLAUDE.md              # メインのプロジェクト説明
└── rules/
    ├── code-style.md      # コードスタイル
    ├── testing.md         # テスト規約
    └── security.md        # セキュリティ要件
```

または `@` でインポート（詳細は「@記法によるファイル参照」セクションを参照）:

```markdown
## API 仕様
@docs/api-reference.md

## データベーススキーマ
@docs/schema.md
```

## 実践的な CLAUDE.md の例

### Web アプリケーション

```markdown
# MyApp - タスク管理アプリ

## 概要
チーム向けのシンプルなタスク管理Webアプリケーション

## 技術スタック
- Frontend: React 18 + TypeScript 5 + Vite
- Backend: Node.js 20 + Express + PostgreSQL
- CSS: Tailwind CSS
- テスト: Vitest + React Testing Library

## ディレクトリ構造
```
src/
├── components/  # React コンポーネント
│   ├── ui/      # 再利用可能な UI パーツ
│   └── features/ # 機能別コンポーネント
├── hooks/       # カスタムフック
├── lib/         # ユーティリティ関数
├── api/         # API クライアント
└── types/       # TypeScript 型定義
```

## アーキテクチャ
- **フロントエンド**: コンポーネントベース、状態管理に React Query
- **バックエンド**: RESTful API、JWT 認証
- **データベース**: PostgreSQL、Prisma ORM

## コーディング規約
### TypeScript
- strict モード必須
- any 型の使用は最小限
- 型エイリアスは interface より type を優先

### React
- 関数コンポーネントのみ
- Props は destructuring
- useEffect の依存配列を必ず指定

### CSS
- Tailwind のユーティリティクラスを使用
- カスタム CSS は最小限

### 命名規則
- コンポーネント: PascalCase
- 関数/変数: camelCase
- 定数: UPPER_SNAKE_CASE
- ファイル: kebab-case

## 開発コマンド
```bash
npm run dev      # 開発サーバー起動
npm test         # テスト実行
npm run build    # プロダクションビルド
npm run lint     # lint チェック
npm run format   # コード整形
```

## API エンドポイント
- `POST /api/auth/login` - ログイン
- `GET /api/tasks` - タスク一覧取得
- `POST /api/tasks` - タスク作成
- `PATCH /api/tasks/:id` - タスク更新
- `DELETE /api/tasks/:id` - タスク削除

## 環境変数
```.env
VITE_API_URL=http://localhost:3000/api
DATABASE_URL=postgresql://user:pass@localhost:5432/myapp
JWT_SECRET=(本番環境のみ)
```

## 注意事項
- API キーは必ず環境変数から取得
- ユーザー入力は必ずサニタイズ
- エラーは必ずログに記録
- 本番デプロイ前に `npm run build` でビルドエラーがないか確認
```

### Python プロジェクト

```markdown
# DataAnalyzer - データ分析ツール

## 概要
CSV/Excel ファイルのデータ分析と可視化ツール

## 技術スタック
- Python 3.11
- Pandas, NumPy - データ処理
- Matplotlib, Seaborn - 可視化
- FastAPI - Web API
- pytest - テスト

## ディレクトリ構造
```
src/
├── analyzers/   # 分析ロジック
├── visualizers/ # 可視化モジュール
├── api/         # FastAPI エンドポイント
├── utils/       # ユーティリティ
└── tests/       # テストコード
```

## コーディング規約
### スタイル
- PEP 8 準拠
- Black でフォーマット
- isort で import 整理
- mypy で型チェック

### ドキュメント
- Google Style Docstring
- すべての public 関数にdocstring
- 型ヒント必須

### テスト
- カバレッジ 80% 以上
- pytest-cov で測定

## 開発コマンド
```bash
poetry run dev           # 開発サーバー
poetry run test          # テスト実行
poetry run test --cov    # カバレッジ付きテスト
poetry run lint          # lint チェック
poetry run format        # コード整形
```

## 注意事項
- 大きなデータセットは chunk で処理
- メモリ使用量に注意
- エラーハンドリングを必ず実装
```

## メモリ管理のベストプラクティス

### 1. 重要な情報を優先

含めるべき:
- プロジェクトの目的
- 技術スタック
- コーディング規約
- よく使うコマンド
- 重要な制約

含めなくていい:
- 詳細な実装手順
- すべてのファイルの説明
- 歴史的経緯

### 2. 定期的に更新

プロジェクトの変更に合わせて更新:

```
> CLAUDE.md を最新の状態に更新して

> 新しい認証システムの情報を CLAUDE.md に追加して
```

### 3. チームで共有

```bash
git add CLAUDE.md
git commit -m "Update project context"
git push
```

### 4. 簡潔に保つ

- フォーカスを絞った要点
- 詳細は `.claude/rules/` や別ファイルへ
- 箇条書きを活用
- 冗長な説明は避ける

## 設定の確認方法

### /memory コマンド

現在のメモリ（CLAUDE.md）の内容を確認・編集できます:

```bash
/memory
```

このコマンドを実行すると、配置場所ごとに分かれた選択画面が表示されます:

```
╭──────────────────────────────────────────────────────────────────╮
│ Select memory to edit:                                           │
│                                                                  │
│    1. User memory                Saved in ~/.claude/CLAUDE.md    │
│    2. Project memory             Saved in ./CLAUDE.md            │
│    3. Local memory               Saved in ./CLAUDE.local.md      │
╰──────────────────────────────────────────────────────────────────╯
```

### /context コマンド

コンテキストに展開されている（セッションで読み込まれている）ファイルの内容を確認:

```bash
/context
```

出力の中に `Memory files` という欄があり、読み込まれているメモリファイルを確認できます:

```bash
  ⎿  Memory files · /memory
  ⎿  └ User (/Users/your-name/.claude/CLAUDE.md): 1.5k tokens
  ⎿  └ Project (/Users/your-name/workspace/project/CLAUDE.md): 663 tokens
```

## CLAUDE.md と settings.json の違い

「配置場所による優先順位」という点では、settings.json も似た仕組みを持っています。それぞれの役割を整理:

| 設定ファイル | 内容 | 記述形式 |
|------------|------|---------|
| CLAUDE.md | AIへの指示（ルール、コーディング規約など） | Markdown（自然言語） |
| settings.json | ツールの設定（権限、フック、MCPなど） | JSON |

**CLAUDE.mdに書くべき内容**
- プロジェクトの概要・目的
- コーディング規約・スタイルガイド
- やってほしいこと・やってほしくないこと

**settings.jsonに書くべき内容**
- パーミッション設定（許可するBashコマンドなど）
- フック（Hooks）の設定
- MCPサーバーの設定

両者は**補完関係**にあり、用途に応じて使い分けてください。

## メモリ編集

### Claude に依頼

```
> CLAUDE.md を編集して、新しいセクションを追加:
  ## デプロイ手順
  1. ビルド
  2. テスト
  3. 本番環境へデプロイ
```

## トラブルシューティング

### CLAUDE.md が認識されない

```bash
# 新しいセッションで起動
exit
claude

# または /init で再生成
/init
```

### 情報が多すぎる

```
> CLAUDE.md を簡潔にして、重要な情報のみ残して
```

### 古い情報が残っている

```
> CLAUDE.md から古い○○の情報を削除して
```

## まとめ

効果的な CLAUDE.md:
1. **簡潔**: フォーカスを絞った要点
2. **具体的**: 曖昧な表現を避ける
3. **最新**: 定期的に更新
4. **構造化**: セクションで整理、`.claude/rules/` でモジュール化
5. **共有**: チームで活用

CLAUDE.md はプロジェクトの「記憶」です。適切に管理することで、Claude との協働がより効率的になります。

## 次のステップ

- **subagents.md** - サブエージェントの詳細
- **hooks.md** - 自動化のためのフック
- **custom_commands.md** - カスタムコマンドの作成
