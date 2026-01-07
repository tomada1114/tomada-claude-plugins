# モデル設定

> Claude Codeのモデル設定について学びます。`opusplan`などのモデルエイリアスを含みます。

## 利用可能なモデル

Claude Codeの`model`設定では、以下のいずれかを設定できます：

* **モデルエイリアス**
* 完全な\*\*[モデル名](/ja/docs/about-claude/models/overview#model-names)\*\*
* Bedrockの場合、ARN

### モデルエイリアス

モデルエイリアスは、正確なバージョン番号を覚えることなく、モデル設定を選択する便利な方法を提供します：

| モデルエイリアス         | 動作                                                                                                               |
| ---------------- | ---------------------------------------------------------------------------------------------------------------- |
| **`default`**    | アカウントタイプに応じた推奨モデル設定                                                                                              |
| **`sonnet`**     | 日常的なコーディングタスクに最新のSonnetモデル（現在はSonnet 4.5）を使用                                                                     |
| **`opus`**       | 専門的な複雑な推論タスクにOpusモデル（現在はOpus 4.5）を使用                                                                             |
| **`haiku`**      | シンプルなタスクに高速で効率的なHaikuモデルを使用                                                                                      |
| **`sonnet[1m]`** | 長時間のセッション用に[100万トークンコンテキストウィンドウ](/ja/docs/build-with-claude/context-windows#1m-token-context-window)を持つSonnetを使用 |
| **`opusplan`**   | プランモード中は`opus`を使用し、実行時に`sonnet`に切り替える特別なモード                                                                      |

### モデル料金比較

| モデル | 入力（/1M tokens） | 出力（/1M tokens） | 特徴 |
|--------|-------------------|-------------------|------|
| Sonnet | $3 | $15 | バランス型、日常使い |
| Opus | $5 | $25 | 最高性能、複雑なタスク |
| Haiku | $1 | $5 | 高速・低コスト |

※料金は変更される可能性があるため、最新の料金は[Anthropic公式の料金ページ](https://www.anthropic.com/pricing)で確認してください。

### モデルの設定

モデルは優先順位順に以下の複数の方法で設定できます：

1. **セッション中** - `/model <alias|name>`を使用してセッション中にモデルを切り替え
2. **起動時** - `claude --model <alias|name>`で起動
3. **環境変数** - `ANTHROPIC_MODEL=<alias|name>`を設定
4. **設定** - `model`フィールドを使用して設定ファイルで永続的に設定

使用例：

```bash  theme={null}
# Opusで開始
claude --model opus

# セッション中にSonnetに切り替え
/model sonnet
```

設定ファイルの例：

```
{
    "permissions": {
        ...
    },
    "model": "opus"
}
```

## 特別なモデル動作

### `default`モデル設定

`default`の動作はアカウントタイプによって異なります。

特定のMaxユーザーの場合、Claude CodeはOpusで使用量の閾値に達した場合、自動的にSonnetにフォールバックします。

### `opusplan`モデル設定

`opusplan`モデルエイリアスは自動化されたハイブリッドアプローチを提供します：

* **プランモード中** - 複雑な推論とアーキテクチャの決定に`opus`を使用
* **実行モード中** - コード生成と実装のために自動的に`sonnet`に切り替え

これにより両方の長所を得られます：計画のためのOpusの優れた推論能力と、実行のためのSonnetの効率性です。

### \[1m]による拡張コンテキスト

Console/APIユーザーの場合、完全なモデル名に`[1m]`サフィックスを追加して[100万トークンコンテキストウィンドウ](/ja/docs/build-with-claude/context-windows#1m-token-context-window)を有効にできます。

```bash  theme={null}
# [1m]サフィックス付きの完全なモデル名を使用する例
/model anthropic.claude-sonnet-4-5-20250929-v1:0[1m]
```

注意：拡張コンテキストモデルには[異なる価格設定](/ja/docs/about-claude/pricing#long-context-pricing)があります。

## 現在のモデルの確認

現在使用しているモデルは以下の複数の方法で確認できます：

### /modelコマンド

モデル名の引数をつけずに`/model`を実行すると、モデル選択画面が表示され、チェックマーク（✔）で現在のモデルを確認できます：

```
───────────────────────────────────────────────────────────────────────────────
 Select model
 Switch between Claude models. Applies to this session and future Claude Code sessions.

 ❯ 1. Default (recommended)   Opus 4.5 · Most capable for complex work ✔
   2. Sonnet                  Sonnet 4.5 · Best for everyday tasks
   3. Haiku                   Haiku 4.5 · Fastest for quick answers
```

### /statusコマンド

`/status`コマンドでは、現在のモデルに加えてアカウント情報も一覧表示されます：

```
> /status
────────────────────────────────────────────────────────────────────────
 Settings:  Status   Config   Usage   (tab to cycle)

 Version: 2.0.74
 Session ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
 cwd: /Users/user/workspace/project
 Login method: Claude Max Account
 Organization: user@example.com's Organization
 Email: user@example.com

 Model: Default Opus 4.5 · Most capable for complex work
```

### ステータスライン

[ステータスライン](/ja/docs/claude-code/statusline)を設定している場合、常に現在のモデルを画面上で確認できます。

## 環境変数

以下の環境変数を使用できます。これらは完全な**モデル名**である必要があり、エイリアスがマップするモデル名を制御します。

| 環境変数                             | 説明                                                                                |
| -------------------------------- | --------------------------------------------------------------------------------- |
| `ANTHROPIC_DEFAULT_OPUS_MODEL`   | `opus`に使用するモデル、またはプランモードがアクティブな場合の`opusplan`用                                     |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `sonnet`に使用するモデル、またはプランモードがアクティブでない場合の`opusplan`用                                 |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL`  | `haiku`または[バックグラウンド機能](/ja/docs/claude-code/costs#background-token-usage)に使用するモデル |
| `CLAUDE_CODE_SUBAGENT_MODEL`     | [サブエージェント](/ja/docs/claude-code/sub-agents)に使用するモデル                               |

注意：`ANTHROPIC_SMALL_FAST_MODEL`は`ANTHROPIC_DEFAULT_HAIKU_MODEL`に置き換えられ、非推奨となりました。

### プロンプトキャッシュ設定

Claude Codeは自動的に[プロンプトキャッシュ](/ja/docs/build-with-claude/prompt-caching)を使用してパフォーマンスを最適化し、コストを削減します。プロンプトキャッシュをグローバルに、または特定のモデル層で無効にできます：

| 環境変数                            | 説明                                           |
| ------------------------------- | -------------------------------------------- |
| `DISABLE_PROMPT_CACHING`        | すべてのモデルでプロンプトキャッシュを無効にするには`1`に設定（モデル別設定より優先） |
| `DISABLE_PROMPT_CACHING_HAIKU`  | Haikuモデルのみでプロンプトキャッシュを無効にするには`1`に設定          |
| `DISABLE_PROMPT_CACHING_SONNET` | Sonnetモデルのみでプロンプトキャッシュを無効にするには`1`に設定         |
| `DISABLE_PROMPT_CACHING_OPUS`   | Opusモデルのみでプロンプトキャッシュを無効にするには`1`に設定           |

これらの環境変数により、プロンプトキャッシュ動作をきめ細かく制御できます。グローバルな`DISABLE_PROMPT_CACHING`設定はモデル固有の設定より優先され、必要に応じてすべてのキャッシュを迅速に無効にできます。モデル別設定は、特定のモデルのデバッグや、異なるキャッシュ実装を持つ可能性のあるクラウドプロバイダーとの作業など、選択的な制御に便利です。

## タスク別モデル選択ガイド

どのモデルを使うべきか迷ったときの参考として、タスク別の推奨モデルを整理します。

### Opusを使うべきタスク

**Opus**は複雑な思考が必要なタスクに適しています：

- **新機能の設計・要件整理**
- **アーキテクチャの検討**（判断を誤ると手戻りが発生するため慎重に）
- **大規模リファクタリング**
- **難しいバグの調査**

### Sonnetを使うべきタスク

**Sonnet**は日常的な開発作業に最適なモデルです：

- **通常の実装**（機能追加やコード修正）
- **バグ修正**（原因が特定できているもの）
- **テストコード生成**
- **コードレビュー**
- **ドキュメント作成**

### Haikuを使うべきタスク

**Haiku**はシンプルで高速な処理が求められる場面で活躍します：

- **ファイル検索・確認**（「〇〇の処理はどこ？」といった質問）
- **簡単な質問**（「このエラーの意味は？」など）
- **コードの説明**

### タスク途中での切り替え例

```bash
# 調査フェーズ
/model → Haikuを選択
「このプロジェクトのディレクトリ構成を教えて」

# 実装フェーズ
/model → Opusを選択
「認証機能を実装して」

# テスト
/model → Sonnetを選択
「テストコードを生成して」
```

タスクの性質に応じて柔軟に切り替えることで、コストを最適化できます。

## モデル選択のベストプラクティス

モデル選択で迷ったときの2つの基本方針を紹介します。

### まずはSonnetから始める

多くのタスクはSonnetで十分対応できます。まずはSonnetで試し、品質に満足できない場合のみOpusに切り替えるのが効率的です。

### コストを意識する

Opusは高品質ですが、API使用料も高くなります。日常的な開発ではSonnetを使用し、重要な設計判断やレビュー時にのみOpusを使うことで、コストを最適化できます。

## 拡張思考モード（Extended Thinking）

Claude Codeには「拡張思考モード」が搭載されています。出力トークン予算の一部を確保して、複雑な問題を段階的に推論させる仕組みです。

### ultrathinkキーワード

拡張思考を有効にするには、プロンプトに`ultrathink`キーワードを含めます：

```
> システム全体のアーキテクチャを見直して ultrathink
```

正しく認識されると、`ultrathink`が虹色で表示されます。

### 思考トークンの仕組み

- **最大31,999トークン**が思考用に確保される
- 出力トークン予算から割り当てられる（追加ではない）
- 思考トークンは次のターンに引き継がれないが、課金対象

### 重要な注意点

| 項目 | 説明 |
|------|------|
| キーワード | `think`、`think harder`、`think more`では拡張思考モードは有効にならない。`ultrathink`が必要 |
| 環境変数 | `MAX_THINKING_TOKENS`が設定されている場合、`ultrathink`キーワードは機能しない |
| 過剰な思考 | `ultrathink`は意味的にも深い推論を促すため、必要以上に深く考えすぎる場合がある |

### 効果的な使いどころ

拡張思考モードはトークン消費が増えるため、本当に必要な場面を見極めることが重要です：

- **設計の意思決定**: アーキテクチャ選択、技術スタックの決定
- **バグの根本原因分析**: 表面的な症状だけでなく問題の本質を探る
- **パフォーマンス最適化**: ボトルネックの特定と最適化戦略の検討
- **セキュリティレビュー**: 脆弱性の多角的な洗い出し

### グローバル設定

毎回`ultrathink`と入力するのが面倒な場合、`/config`で常時有効化できます：

```
/config
```

設定画面で`Thinking mode`を`true`に変更すると、すべてのプロンプトで自動的に拡張思考が適用されます。

**注意**: 常時有効化はトークン消費の大幅増加を招きます。Max 20xプランなら問題ありませんが、ProプランやMax 5xプランではリミットに達しやすくなります。

### デフォルト動作

Sonnet 4.5やOpus 4.5では、デフォルトで拡張思考が有効になっています（2025年1月時点）。
