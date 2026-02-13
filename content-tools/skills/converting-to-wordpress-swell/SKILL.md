---
name: converting-to-wordpress-swell
description: Convert HTML, Markdown, or plain text to WordPress Gutenberg block format for SWELL theme. Use PROACTIVELY when converting content to WordPress, SWELL theme formatting, Gutenberg blocks, WordPress記事変換, SWELL形式, ブログ記事変換, or working with wp:paragraph, wp:heading, wp:list, swl-marker. Examples: <example>Context: User has markdown or HTML to convert user: 'Convert this article to WordPress format' assistant: 'I will use converting-to-wordpress-swell skill' <commentary>Triggered by WordPress conversion request</commentary></example>
---

# WordPress SWELL Theme Format Converter

Convert HTML, Markdown, or plain text content to WordPress Gutenberg block format optimized for the SWELL theme.

## When to Use This Skill

- Converting Markdown articles to WordPress format
- Converting plain HTML to Gutenberg blocks
- Formatting blog posts for SWELL theme
- Adding SWELL-specific styling (icon boxes, markers)
- Preparing content for WordPress import

## Block Format Reference

### Basic Structure

All WordPress Gutenberg blocks follow this pattern:
```html
<!-- wp:blocktype {"attribute":"value"} -->
<element class="wp-block-*">Content</element>
<!-- /wp:blocktype -->
```

### Paragraph

```html
<!-- wp:paragraph -->
<p>Your paragraph text here.</p>
<!-- /wp:paragraph -->
```

With SWELL paragraph style (icon):
```html
<!-- wp:paragraph {"className":"is-style-big_icon_memo"} -->
<p class="is-style-big_icon_memo">Note content here.</p>
<!-- /wp:paragraph -->
```

### Headings

**H2 (default):**
```html
<!-- wp:heading -->
<h2 class="wp-block-heading">Heading Text</h2>
<!-- /wp:heading -->
```

**H3:**
```html
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Subheading Text</h3>
<!-- /wp:heading -->
```

**H4:**
```html
<!-- wp:heading {"level":4} -->
<h4 class="wp-block-heading">Sub-subheading Text</h4>
<!-- /wp:heading -->
```

### Lists

**Unordered List:**
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

**Ordered List:**
```html
<!-- wp:list {"ordered":true} -->
<ol class="wp-block-list"><!-- wp:list-item -->
<li>First item</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Second item</li>
<!-- /wp:list-item --></ol>
<!-- /wp:list -->
```

### Tables

```html
<!-- wp:table {"hasFixedLayout":false,"className":"is-style-simple"} -->
<figure class="wp-block-table is-style-simple"><table><tbody><tr><td><strong>Header 1</strong></td><td><strong>Header 2</strong></td></tr><tr><td>Cell 1</td><td>Cell 2</td></tr></tbody></table></figure>
<!-- /wp:table -->
```

### Code Blocks (SWELL HCB - Highlighting Code Block)

```html
<!-- wp:loos-hcb/code-block {"langType":"js","langName":"JavaScript"} -->
<div class="hcb_wrap"><pre class="prism undefined-numbers lang-js" data-lang="JavaScript"><code>const example = "code here";</code></pre></div>
<!-- /wp:loos-hcb/code-block -->
```

Common language types:
- `js` / `JavaScript`
- `python` / `Python`
- `bash` / `Bash`
- `html` / `HTML`
- `css` / `CSS`
- `json` / `JSON`
- `ts` / `TypeScript`

## SWELL-Specific Features

### Icon Boxes (Group + List)

Wrap lists in a group block with SWELL icon styles:

**Point/要点 (bullet point icon):**

**重要: 長い説明を持つリストアイテムは個別リストに分割し、間に空段落を挿入して視覚的に区切る：**

```html
<!-- wp:group {"className":"is-style-big_icon_point"} -->
<div class="wp-block-group is-style-big_icon_point"><!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li><strong>ポイント1のタイトル</strong><br>ポイント1の詳細説明文。</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p></p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li><strong>ポイント2のタイトル</strong><br>ポイント2の詳細説明文。</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p></p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li><strong>ポイント3のタイトル</strong><br>ポイント3の詳細説明文。</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:group -->
```

**短いシンプルなリストの場合は従来通り1つのリストにまとめてOK：**
```html
<!-- wp:group {"className":"is-style-big_icon_point"} -->
<div class="wp-block-group is-style-big_icon_point"><!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>Key point 1</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Key point 2</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:group -->
```

**Good/メリット (checkmark icon):**
```html
<!-- wp:group {"className":"is-style-big_icon_good"} -->
<div class="wp-block-group is-style-big_icon_good"><!-- wp:list -->
...
<!-- /wp:list --></div>
<!-- /wp:group -->
```

**Hatena/疑問 (question mark icon):**
```html
<!-- wp:paragraph {"className":"is-style-big_icon_hatena"} -->
<p class="is-style-big_icon_hatena">Question or consideration text.</p>
<!-- /wp:paragraph -->
```

**Memo/メモ (note icon):**
```html
<!-- wp:paragraph {"className":"is-style-big_icon_memo"} -->
<p class="is-style-big_icon_memo">Additional note or memo.</p>
<!-- /wp:paragraph -->
```

### Available Icon Styles

| Style Class | Use Case | Icon |
|-------------|----------|------|
| `is-style-big_icon_point` | Key points, summary | Bullet |
| `is-style-big_icon_good` | Benefits, pros, recommendations | Checkmark |
| `is-style-big_icon_hatena` | Questions, considerations | Question mark |
| `is-style-big_icon_memo` | Notes, additional info | Memo |

### Text Markers (Inline Highlighting)

**IMPORTANT: Use all 4 marker colors strategically based on meaning:**

**Blue marker - 重要ポイント・キーコンセプト:**
```html
<span class="swl-marker mark_blue">行動追跡を防ぎやすく</span>
```

**Green marker - ポジティブ・推奨・メリット:**
```html
<span class="swl-marker mark_green">返金保証のあるサービス</span>
```

**Yellow marker - 注意・警告・考慮事項:**
```html
<span class="swl-marker mark_yellow">一部の国やサービスでは規制や制限</span>
```

**Orange marker - 禁止事項・強い警告:**
```html
<span class="swl-marker mark_orange">無料サービスには注意が必要</span>
```

### Inline Formatting

**Bold:**
```html
<strong>bold text</strong>
```

**Links (通常):**
```html
<a href="https://example.com" target="_blank" rel="noreferrer noopener">Link text</a>
```

**Links (スポンサード/Dofollow用 - rel属性とtarget属性を削除):**
```html
<a href="https://example.com">Link text</a>
```

**Line break:**
```html
<br>
```

### PR表記（スポンサード記事用）

記事の最初に配置：
```html
<!-- wp:paragraph {"className":"is-style-alert"} -->
<p class="is-style-alert">※本記事はPRを含みます。</p>
<!-- /wp:paragraph -->
```

### Images with Caption (引用元表記)

画像には引用元をキャプションとして追加：
```html
<!-- wp:image {"sizeSlug":"large","linkDestination":"none"} -->
<figure class="wp-block-image size-large"><img src="images/image.jpg" alt=""/><figcaption class="wp-element-caption">引用元：<a href="https://www.pexels.com/ja-jp/photo/123456/">https://www.pexels.com/ja-jp/photo/123456/</a></figcaption></figure>
<!-- /wp:image -->
```

### Reusable Blocks

Reference a reusable block by ID:
```html
<!-- wp:block {"ref":3345} /-->
```

## Conversion Rules

### From Markdown

| Markdown | WordPress SWELL |
|----------|-----------------|
| `# Heading` | `<!-- wp:heading -->` (H2 by default) |
| `## Heading` | `<!-- wp:heading -->` (H2) |
| `### Heading` | `<!-- wp:heading {"level":3} -->` (H3) |
| `**bold**` | `<strong>bold</strong>` |
| `- item` | `<!-- wp:list -->` + `<!-- wp:list-item -->` |
| `1. item` | `<!-- wp:list {"ordered":true} -->` |
| `` `code` `` | Use HCB code block for blocks |
| `[text](url)` | `<a href="url">text</a>` |

### From Plain HTML

1. Wrap each `<p>` in `<!-- wp:paragraph -->` blocks
2. Convert `<h2>`, `<h3>` to heading blocks with appropriate level
3. Convert `<ul>`, `<ol>` to list blocks with nested list-items
4. Convert `<table>` to table blocks with figure wrapper
5. Convert `<pre><code>` to SWELL HCB code blocks

## Conversion Workflow

1. **Analyze source content** - Identify structure (headings, lists, code, tables)
2. **Convert basic blocks** - Transform to Gutenberg block format
3. **Add SWELL enhancements** - Apply icon boxes and markers where appropriate
4. **Validate output** - Ensure all blocks are properly closed

## Best Practices

### When to Use Icon Boxes

- `is-style-big_icon_point` - For key takeaways, summaries, "what you'll learn"
- `is-style-big_icon_good` - For benefits, pros, recommended actions
- `is-style-big_icon_hatena` - For FAQ-style content, considerations, "did you know"
- `is-style-big_icon_memo` - For supplementary notes, tips, warnings

### When to Use Markers (CRITICAL: Use all 4 colors)

- `mark_blue` - 重要ポイント、キーコンセプト（例：「暗号化される」「追跡を防ぐ」）
- `mark_green` - ポジティブな内容、推奨事項、メリット（例：「返金保証」「速度低下を最小限」）
- `mark_yellow` - 注意事項、警告、考慮点（例：「規制や制限」「有名だから安いから」）
- `mark_orange` - 禁止・強い警告（例：「無料サービスには注意」「アクセスを禁止」）

**Goal: 各セクションに1-2個のマーカーを配置し、4色をバランスよく使用**

### Content Structure Tips

1. **導入部分（リード文）は必須** - PR表記の後、最初のH2の前に3-5段落の導入文を配置
   - 読者の課題・疑問を提示
   - 記事で学べることの概要
   - 最後に商品/サービスへのリンクを自然に配置
2. Use H2 for main sections, H3 for subsections
3. Include a summary box early (icon_point)
4. Use tables for comparison data
5. End with a summary/conclusion section
6. **アイコンボックスの前には必ず導入文を追加**（例：「以下のような特徴も兼ね備えています」）

### Bold（`<strong>`）の積極的な使用

以下の要素には必ず太字を適用：
- **専門用語・キーワード**：「<strong>VPN</strong>」「<strong>ジオブロック</strong>」
- **数字・価格**：「<strong>月540円から</strong>」「<strong>世界178ヵ所</strong>」
- **重要なフレーズ**：「<strong>通常より通信速度が低下</strong>」
- **記事内の要点**：「<strong>特に注意すべき3つのポイント</strong>」

## AI Assistant Instructions

When converting content to WordPress SWELL format:

1. **Always use proper block structure** - Every element must have opening and closing block comments
2. **Preserve semantic meaning** - Match source structure to appropriate blocks
3. **Apply SWELL styles appropriately** - Use icon boxes for lists that deserve emphasis
4. **Use all 4 marker colors strategically** - blue/green/yellow/orange を意味に応じて使い分け
5. **Maintain readability** - Add blank lines between blocks for easier editing
6. **Escape special characters** - Use `&quot;` for quotes in code blocks
7. **導入文を追加** - PR表記の後・H2の前、アイコンボックスの前など
8. **太字を積極的に使用** - キーワード、数字、重要フレーズに`<strong>`
9. **長いリストアイテムは分割** - 個別リスト+空段落で視覚的に区切る

### Output Format

- Output complete, valid WordPress HTML
- Include all block comments
- Format code blocks with appropriate language hints
- Preserve original content meaning while enhancing presentation
- 画像には引用元キャプションを追加

### Sponsored/PR記事の場合

- PR表記を記事冒頭に追加（`is-style-alert`）
- クライアントリンクはdofollow（`rel`属性を削除）
- `target="_blank"`も削除可

### Never

- Skip closing block comments
- Mix Markdown and WordPress block syntax
- Use only `mark_blue` (4色をバランスよく使う)
- Apply icon boxes to every list
- Remove meaningful content during conversion
- アイコンボックスを導入文なしで唐突に配置
- 重要なキーワードや数字を太字にしない
