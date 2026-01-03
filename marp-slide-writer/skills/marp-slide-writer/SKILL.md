---
name: marp-slide-writer
description: YouTube収録用Marpスライドを作成・検証するスキル。テック系コンテンツ（AI駆動開発、プログラミング、ツール解説）に最適化。Use PROACTIVELY when creating slides, writing Marp markdown, スライド作成, プレゼン資料, 収録用スライド, Marp, presentation. Examples: <example>Context: User wants slides user: 'このエピソード用のスライドを作って' assistant: 'I will use marp-slide-writer skill' <commentary>Triggered by slide creation request</commentary></example>
---

# Marp Slide Writer

YouTube収録用のMarpスライドを作成するスキル。レイアウト制約を遵守し、視認性の高いスライドを生成する。

## When to Use This Skill

- スライドの新規作成
- 既存スライドの改善・リファクタリング
- スライドのレイアウト検証
- テック系プレゼンテーション資料の作成

## Quick Reference: Layout Constraints

| 構成 | 上限 | 推奨 |
|------|------|------|
| h1 + 箇条書き | 8行 | 6行 |
| h1 + コード | 12行 | 10行 |
| h1 + 説明文 + 箇条書き | 6行 | 5行 |
| h1 + 説明文 + コード | 10行 | 8行 |
| h1 + 箇条書き + コード | 箇条3 + コード5 | 箇条2 + コード4 |
| h1 + テーブル | 8行(ヘッダ含む) | 6行 |
| no-header + コード | 17行 | 14行 |
| small-text + 箇条書き | 10行 | 8行 |
| subtitle-safe + 箇条書き | 5行 | 4行 |

**詳細は [reference.md](reference.md) を参照**

## Workflow

### 1. Create Slide File

```bash
mkdir -p slides
# テンプレートをコピー
cp skills/marp-slide-writer/templates/basic-template.md slides/slides.md
```

### 2. Edit Slides

テンプレートを参考にスライドを作成:
- [basic-template.md](templates/basic-template.md) - 基本構成
- [code-heavy-template.md](templates/code-heavy-template.md) - コード多めの解説

### 3. Validate Layout

```bash
python skills/marp-slide-writer/scripts/validate_slides.py <path/to/slides.md>
```

**Example:**
```bash
python skills/marp-slide-writer/scripts/validate_slides.py slides/slides.md
```

### 4. Preview

```bash
# Live preview (auto-reload)
npx @marp-team/marp-cli@latest <path/to/slides.md> --preview --watch --bespoke.osc false
```

**Example:**
```bash
npx @marp-team/marp-cli@latest slides/slides.md --preview --watch --bespoke.osc false
```

## Theme

テーマはGitHub Pages経由で配信:

```yaml
---
marp: true
theme: https://tomada1114.github.io/marp-theme/youtube-theme.css
paginate: false
---
```

## Slide Structure Guidelines

### Title Slide

```markdown
<!-- _class: title -->
<!-- _paginate: false -->

# メインタイトル

## サブタイトル・トピック
```

### Section Divider

```markdown
<!-- _class: section -->

## セクション名
```

### Content Slide (Standard)

```markdown
# スライドタイトル

- ポイント1（短く簡潔に）
- ポイント2
- ポイント3
```

### Code Slide

```markdown
# コード例のタイトル

説明文は1行で。

```python
def example():
    # 10行以内に収める
    return result
```
```

### Ending Slide

```markdown
<!-- _class: align-center text-center -->

# ご視聴ありがとうございました

チャンネル登録・高評価お願いします
```

## Available CSS Classes

| クラス | 効果 |
|--------|------|
| `title` | タイトルスライド（中央揃え） |
| `section` | セクション区切り（グラデーション背景） |
| `no-header` | 上部パディング縮小（コードメイン時） |
| `align-center` | 垂直中央揃え |
| `text-center` | 水平中央揃え |
| `subtitle-safe` | 字幕スペース拡大（180px） |
| `small-text` | フォント縮小 |
| `col2` | 2カラムグリッド |
| `col3` | 3カラムグリッド |

## Best Practices

### DO

- 1スライド1メッセージ
- 箇条書きは6行以内を目標
- コードは10行以内を目標
- 重要キーワードは**太字**で強調
- セクション区切りで構造化

### DON'T

- 長文を詰め込まない
- コードブロックを2つ以上配置しない
- ネストを3階層以上にしない
- 1行を50文字以上にしない

## AI Assistant Instructions

### スライド作成時

1. **構成を確認**: 内容・目的を把握
2. **制約を遵守**: 必ずレイアウト制約内で作成
3. **検証を実行**: 作成後に `validate_slides.py` で検証
4. **エラー修正**: 違反があれば即座に修正

### 検証で違反が見つかった場合

1. 違反内容を確認（行数オーバー、長すぎる行など）
2. 以下の方法で修正:
   - 内容を分割して複数スライドに
   - `small-text` クラスを適用
   - 説明文を箇条書きに変換
   - コードを短縮・分割

### Never

- 制約を無視してスライドを作成
- 検証をスキップ
- 1スライドに情報を詰め込みすぎる
- 視認性を犠牲にする

## Examples

完全な使用例は [examples/](examples/) を参照:
- [ai-tool-intro.md](examples/ai-tool-intro.md) - AI開発ツール紹介
- [code-tutorial.md](examples/code-tutorial.md) - コードチュートリアル

## Additional Resources

- [reference.md](reference.md) - レイアウト制約の詳細・計算根拠
- [templates/](templates/) - すぐ使えるテンプレート
- [scripts/validate_slides.py](scripts/validate_slides.py) - 検証スクリプト
