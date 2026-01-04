# 04. プロジェクトの初期化

## CLAUDE.md とは

CLAUDE.md は、Claude がプロジェクトに関する情報を記憶するためのファイルです。プロジェクトの構造、規約、重要な情報を保存します。

### CLAUDE.md の役割
- プロジェクトの概要と目的を記憶
- アーキテクチャやデザインパターンを記録
- コーディング規約やスタイルガイドを保存
- 依存関係や環境設定を記録
- セッション間で情報を永続化

### CLAUDE.md の階層構造

Claude Codeは5階層のメモリ構造をサポートしています:

| 階層 | 配置場所 | 対象範囲 | 用途 |
|-----|---------|---------|------|
| Enterprise policy | `/Library/Application Support/ClaudeCode/CLAUDE.md`（macOS） | 組織全体 | 企業規約・セキュリティポリシー |
| User memory | `~/.claude/CLAUDE.md` | 個人・全プロジェクト | 個人設定・ツールショートカット |
| Project memory | `./CLAUDE.md` または `./.claude/CLAUDE.md` | チーム共有 | プロジェクト規約 |
| Project rules | `./.claude/rules/*.md` | チーム共有 | モジュール化された規則 |
| Project local | `./CLAUDE.local.md` | 個人・現プロジェクト | プライベート設定（自動gitignore） |

**重要**: ファイル検索は再帰的に行われ、現在のディレクトリから上位へ走査します。

## /init コマンド

`/init` コマンドを使用すると、Claude がプロジェクトを分析して自動的に CLAUDE.md を生成します。

### 基本的な使い方

```bash
# プロジェクトディレクトリで Claude を起動
cd your-project
claude

# 初期化コマンドを実行
/init
```

### /init が行うこと

1. **プロジェクト構造を分析**
   - ファイルとディレクトリの構成を確認
   - 使用されている言語やフレームワークを検出

2. **重要なファイルを読み取る**
   - README.md
   - package.json / requirements.txt
   - 設定ファイル

3. **CLAUDE.md を生成**
   - プロジェクトの概要
   - 技術スタック
   - ディレクトリ構造
   - 開発ガイドライン

4. **確認を求める**
   - 生成された内容を確認
   - 必要に応じて編集

## 生成される CLAUDE.md の例

```markdown
# プロジェクト名

## 概要
このプロジェクトは...

## 技術スタック
- Node.js v18
- React 18
- TypeScript 5
- Tailwind CSS

## ディレクトリ構造
```
src/
  ├── components/  # React コンポーネント
  ├── hooks/       # カスタムフック
  ├── utils/       # ユーティリティ関数
  └── App.tsx      # メインアプリ
```

## コーディング規約
- TypeScript の strict モードを使用
- コンポーネントは関数コンポーネントで作成
- CSS は Tailwind のユーティリティクラスを使用

## 開発コマンド
- `npm run dev` - 開発サーバー起動
- `npm test` - テスト実行
- `npm run build` - 本番ビルド
```

## CLAUDE.md のカスタマイズ

### 手動で編集

```bash
/memory
```

このコマンドで CLAUDE.md を直接編集できます。

### カスタマイズの例

#### 1. コーディングスタイルの追加
```markdown
## コーディングスタイル
- インデントは2スペース
- セミコロンは必須
- シングルクォートを使用
- 関数名はキャメルケース
```

#### 2. 禁止事項の記載
```markdown
## 禁止事項
- グローバル変数の使用禁止
- console.log のコミット禁止
- any 型の使用は最小限に
```

#### 3. API情報の追加
```markdown
## API エンドポイント
- ベースURL: https://api.example.com
- 認証: Bearer トークン
- レート制限: 100リクエスト/分
```

#### 4. デプロイ情報
```markdown
## デプロイ
- 本番環境: Vercel
- ステージング: Netlify
- デプロイコマンド: `npm run deploy`
```

## CLAUDE.md の活用方法

### プロジェクト固有のルールを守らせる

CLAUDE.md に記載された規約は、Claude が自動的に従います:

```markdown
## ファイル命名規則
- React コンポーネント: PascalCase (例: UserProfile.tsx)
- ユーティリティ: camelCase (例: formatDate.ts)
- 定数ファイル: UPPER_SNAKE_CASE (例: API_KEYS.ts)
```

Claude はこの規約に従ってファイルを作成します。

### チーム開発での活用

CLAUDE.md をGitにコミットすることで、チームメンバー全員が同じコンテキストを共有できます:

```bash
# CLAUDE.md をコミット
git add CLAUDE.md
git commit -m "Add project context for Claude"
git push
```

チームメンバーがプロジェクトをクローンすると、同じコンテキストで Claude を使用できます。

## サブエージェントとの連携

サブエージェントは `.claude/agents/` ディレクトリ（または `~/.claude/agents/`）に個別のマークダウンファイルとして定義します:

```
.claude/agents/
├── code-reviewer.md
├── debugger.md
└── test-writer.md
```

CLAUDE.md からサブエージェントを参照する場合:

```markdown
## サブエージェント
詳細は @.claude/agents/ を参照
```

これにより、CLAUDE.md をシンプルに保ちつつ、エージェント設定を分離できます。

**注意**: AGENTS.md という単一ファイルは存在しません。代わりに `.claude/agents/` ディレクトリに各エージェントを個別ファイルとして配置します。

## ベストプラクティス

### 1. 初回は /init を使う
手動で書くより、Claude に生成させてから編集する方が効率的です。

### 2. 定期的に更新
プロジェクトが進化したら CLAUDE.md も更新:
```
> CLAUDE.md を最新の状態に更新して
```

### 3. 重要な情報を優先
- 必須の規約
- 重要なアーキテクチャ決定
- よく使うコマンド

### 4. 簡潔に保つ
長すぎる CLAUDE.md はコンテキストを圧迫します。詳細は別ファイルに分離しましょう。

## よくある質問

### Q: CLAUDE.md を削除したらどうなる?
A: Claude はプロジェクトのコンテキストを失いますが、動作は継続します。ただし、毎回プロジェクト情報を説明する必要があります。

### Q: 複数のプロジェクトで同じ CLAUDE.md を使える?
A: 各プロジェクトに固有の CLAUDE.md を作成することを推奨します。

### Q: CLAUDE.md の最適なサイズは?
A: 公式には固定のサイズ制限はありませんが、大きくなりすぎた場合は `.claude/rules/` ディレクトリでモジュール化することを推奨します。言語別、機能別などに分割できます。

## トラブルシューティング

### /init が失敗する
```bash
# プロジェクトを手動で要約させてから再試行
> このプロジェクトの構造を分析して要約して
/init
```

### CLAUDE.md が適用されない
```bash
# 新しいセッションで起動
claude
```

## 次のステップ

プロジェクトの初期化ができたら:
- **05_slash_commands.md** - 便利なコマンドを学ぶ
- **08_subagents.md** - サブエージェントでタスクを委任
- **15_memory_management.md** - メモリ管理の詳細
