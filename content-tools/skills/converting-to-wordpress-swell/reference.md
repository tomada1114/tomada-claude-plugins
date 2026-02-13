# WordPress SWELL Format Reference

## Complete Conversion Examples

### Example 1: Markdown to WordPress SWELL

**Source Markdown:**
```markdown
## 記事の概要

この記事では、以下のことを学べます。

- ポイント1
- ポイント2
- ポイント3

### 詳細説明

**重要な概念**について説明します。

これは`コード`の例です。
```

**Converted WordPress SWELL:**
```html
<!-- wp:heading -->
<h2 class="wp-block-heading">記事の概要</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>この記事では、以下のことを学べます。</p>
<!-- /wp:paragraph -->

<!-- wp:group {"className":"is-style-big_icon_point"} -->
<div class="wp-block-group is-style-big_icon_point"><!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>ポイント1</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>ポイント2</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>ポイント3</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:group -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">詳細説明</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p><strong>重要な概念</strong>について説明します。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>これは<code>コード</code>の例です。</p>
<!-- /wp:paragraph -->
```

### Example 2: Plain HTML to WordPress SWELL

**Source HTML:**
```html
<h2>機能一覧</h2>
<p>以下の機能が利用できます。</p>
<ul>
  <li>機能A - 基本機能</li>
  <li>機能B - 拡張機能</li>
</ul>
<table>
  <tr><th>項目</th><th>説明</th></tr>
  <tr><td>項目1</td><td>説明1</td></tr>
</table>
```

**Converted WordPress SWELL:**
```html
<!-- wp:heading -->
<h2 class="wp-block-heading">機能一覧</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>以下の機能が利用できます。</p>
<!-- /wp:paragraph -->

<!-- wp:group {"className":"is-style-big_icon_good"} -->
<div class="wp-block-group is-style-big_icon_good"><!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>機能A - 基本機能</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>機能B - 拡張機能</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:group -->

<!-- wp:table {"hasFixedLayout":false,"className":"is-style-simple"} -->
<figure class="wp-block-table is-style-simple"><table><tbody><tr><td><strong>項目</strong></td><td><strong>説明</strong></td></tr><tr><td>項目1</td><td>説明1</td></tr></tbody></table></figure>
<!-- /wp:table -->
```

### Example 3: Code Block with Syntax Highlighting

**Source:**
```javascript
function greet(name) {
  return `Hello, ${name}!`;
}
```

**WordPress SWELL HCB Format:**
```html
<!-- wp:loos-hcb/code-block {"langType":"js","langName":"JavaScript"} -->
<div class="hcb_wrap"><pre class="prism undefined-numbers lang-js" data-lang="JavaScript"><code>function greet(name) {
  return `Hello, ${name}!`;
}</code></pre></div>
<!-- /wp:loos-hcb/code-block -->
```

## Block Attribute Reference

### Paragraph Attributes

```json
{
  "className": "is-style-big_icon_memo"  // Optional: SWELL icon style
}
```

### Heading Attributes

```json
{
  "level": 3  // 2 (default), 3, 4, 5, 6
}
```

### List Attributes

```json
{
  "ordered": true  // false (default) for <ul>, true for <ol>
}
```

### Table Attributes

```json
{
  "hasFixedLayout": false,
  "className": "is-style-simple"  // SWELL table style
}
```

### Group Attributes

```json
{
  "className": "is-style-big_icon_point"  // SWELL icon box style
}
```

### Code Block Attributes (SWELL HCB)

```json
{
  "langType": "js",        // Language identifier
  "langName": "JavaScript" // Display name
}
```

## Common Language Identifiers for Code Blocks

| Language | langType | langName |
|----------|----------|----------|
| JavaScript | `js` | `JavaScript` |
| TypeScript | `ts` | `TypeScript` |
| Python | `python` | `Python` |
| Bash/Shell | `bash` | `Bash` |
| HTML | `html` | `HTML` |
| CSS | `css` | `CSS` |
| JSON | `json` | `JSON` |
| YAML | `yaml` | `YAML` |
| SQL | `sql` | `SQL` |
| PHP | `php` | `PHP` |
| Ruby | `ruby` | `Ruby` |
| Go | `go` | `Go` |
| Rust | `rust` | `Rust` |
| HCL/Terraform | `js` | `HCL` |

## SWELL Theme Style Classes

### Icon Box Styles (for group blocks)

| Class | Japanese Name | Use Case |
|-------|---------------|----------|
| `is-style-big_icon_point` | ポイント | Key points, summaries |
| `is-style-big_icon_good` | グッド | Benefits, pros, recommendations |
| `is-style-big_icon_bad` | バッド | Drawbacks, cons, warnings |
| `is-style-big_icon_hatena` | はてな | Questions, FAQ |
| `is-style-big_icon_memo` | メモ | Notes, tips |
| `is-style-big_icon_check` | チェック | Checklists |

### Marker Classes (for inline spans) - CRITICAL: Use all 4 colors

| Class | Color | Use Case | 日本語 |
|-------|-------|----------|--------|
| `swl-marker mark_blue` | Blue | Important terms, key concepts | 重要ポイント |
| `swl-marker mark_green` | Green | Positive emphasis, recommendations, benefits | ポジティブ・推奨 |
| `swl-marker mark_yellow` | Yellow | Warnings, cautions, considerations | 注意・警告 |
| `swl-marker mark_orange` | Orange | Prohibitions, strong warnings | 禁止・強い警告 |

### Table Styles

| Class | Description |
|-------|-------------|
| `is-style-simple` | Simple bordered table |
| `is-style-stripes` | Striped rows |

## Whitespace and Formatting

### Block Separation

Always include a blank line between blocks for readability:

```html
<!-- wp:paragraph -->
<p>First paragraph.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Second paragraph.</p>
<!-- /wp:paragraph -->
```

### List Item Formatting

List items should have blank lines between them:

```html
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>Item 1</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Item 2</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
```

## Special Characters

When content contains special characters, escape them appropriately:

| Character | Escaped |
|-----------|---------|
| `"` | `&quot;` (in attributes) |
| `<` | `&lt;` (in code) |
| `>` | `&gt;` (in code) |
| `&` | `&amp;` |

## PR/Sponsored Article Format

### PR表記（記事冒頭に配置）
```html
<!-- wp:paragraph {"className":"is-style-alert"} -->
<p class="is-style-alert">※本記事はPRを含みます。</p>
<!-- /wp:paragraph -->
```

### Dofollow Links（rel属性とtarget属性を削除）
```html
<a href="https://example.com">Link text</a>
```

## Image with Caption（引用元表記）

```html
<!-- wp:image {"sizeSlug":"large","linkDestination":"none"} -->
<figure class="wp-block-image size-large"><img src="images/image.jpg" alt=""/><figcaption class="wp-element-caption">引用元：<a href="https://www.pexels.com/ja-jp/photo/123456/">https://www.pexels.com/ja-jp/photo/123456/</a></figcaption></figure>
<!-- /wp:image -->
```

## Bold（`<strong>`）の使用箇所

以下には必ず太字を適用：
- 専門用語・キーワード：`<strong>VPN</strong>`
- 数字・価格：`<strong>月540円から</strong>`
- 重要なフレーズ：`<strong>通常より通信速度が低下</strong>`
- 記事の要点：`<strong>特に注意すべき3つのポイント</strong>`

## 導入文パターン

### 記事冒頭（PR表記とH2の間）
```html
<!-- wp:paragraph -->
<p>課題や疑問を提示する導入文。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>記事で学べることの概要。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>最後に商品/サービスへのリンクを自然に配置。</p>
<!-- /wp:paragraph -->
```

### アイコンボックス前
```html
<!-- wp:paragraph -->
<p>さらに以下のような特徴も兼ね備えているため、安心して利用できます。</p>
<!-- /wp:paragraph -->

<!-- wp:group {"className":"is-style-big_icon_good"} -->
...
```

## 長いリストアイテムの分割構造

各アイテムを個別リストに分割し、空段落で区切る：
```html
<!-- wp:group {"className":"is-style-big_icon_point"} -->
<div class="wp-block-group is-style-big_icon_point"><!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li><strong>ポイント1</strong><br>説明文。</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p></p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li><strong>ポイント2</strong><br>説明文。</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:group -->
```

## Validation Checklist

Before finalizing converted content:

- [ ] All blocks have opening AND closing comments
- [ ] Heading levels match source hierarchy
- [ ] Lists have proper list-item wrappers
- [ ] Tables have figure wrapper
- [ ] Code blocks have language attributes
- [ ] Special characters are escaped
- [ ] Icon boxes are applied appropriately (not overused)
- [ ] **All 4 marker colors used (blue/green/yellow/orange)**
- [ ] **Important keywords and numbers are bold**
- [ ] **Introduction paragraphs before first H2**
- [ ] **Lead-in text before icon boxes**
- [ ] **Image captions with source attribution**
- [ ] **PR表記 at article start (for sponsored)**
- [ ] **Dofollow links (no rel attribute) for sponsor**
