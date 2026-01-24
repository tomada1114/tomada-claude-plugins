# Next.js Blog Implementation - Complete Reference

## Data Flow Diagram

```
File System (content/posts/[category]/[slug].md)
         ↓
    Frontmatter (title, excerpt, date)
    Raw markdown content
         ↓
[posts.ts] - Discovery & Parsing (gray-matter)
         ↓
    Post interface: {slug, title, date, category, excerpt, content}
         ↓
Routes:
  /blog → BlogPage (getAllPosts)
  /blog/[category] → CategoryPage (getPostsByCategory)
  /blog/[category]/[slug] → BlogPost (getPostBySlug)
         ↓
[markdown.ts] - HTML Conversion
  Remark → HTML → Rehype → Slug generation → Syntax highlighting
         ↓
[categories.ts] - Icon Resolution
  DevIcon or Emoji based on category type
         ↓
Components:
  PostCard, ArticleInfo, TableOfContents
  CategoryBadge, ShareButtons, etc.
         ↓
Rendered HTML Page with SEO
```

## Library API Reference

### posts.ts

**Post Interface:**
```typescript
interface Post {
  slug: string      // Derived from filename (without .md)
  title: string     // From frontmatter
  date: string      // From frontmatter (YYYY-MM-DD)
  category: string  // From directory name
  excerpt: string   // From frontmatter (optional)
  content: string   // Raw markdown after frontmatter
}
```

**Functions:**

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getPostsByCategory` | `category: string` | `Post[]` | Get all posts in a category, sorted by date DESC |
| `getAllCategories` | none | `string[]` | List all category directory names |
| `getPostBySlug` | `category: string, slug: string` | `Post \| null` | Get single post by category and slug |
| `getAllPosts` | none | `Post[]` | Get all posts across categories, sorted by date DESC |

### markdown.ts

**markdownToHtml(markdown: string): Promise<string>**

Processing pipeline:
1. `remark` with `remark-gfm` - Parse markdown with GitHub Flavored Markdown
2. `remark-html` - Convert to HTML
3. `rehype` with `rehype-slug` - Add IDs to headings
4. `rehype-prism-plus` - Syntax highlighting with line numbers
5. Image optimization - Add lazy loading and styling

### categories.ts

**Types:**
```typescript
type IconSize = 'sm' | 'md' | 'lg'

type CategoryIcon = {
  type: 'devicon' | 'emoji'
  value: string
  size: IconSize
}

interface CategoryInfo {
  name: string
  icon: CategoryIcon
}
```

**Functions:**

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `isDeviconCategory` | `category: string` | `boolean` | Check if category uses devicon |
| `getCategoryIcon` | `category: string, size?: IconSize` | `CategoryIcon` | Get icon configuration |
| `getCategoryInfo` | `category: string, iconSize?: IconSize` | `CategoryInfo` | Get display name and icon |

## Component API Reference

### TableOfContents

Client component that extracts H2 headings and tracks scroll position.

**Features:**
- Extracts headings from `.blog-article h2` elements
- Generates safe IDs for Japanese/special characters
- IntersectionObserver with `-80px 0px -80% 0px` margins
- Smooth scroll with -80px offset for sticky header
- Sticky positioning at `top-20`

**Customization:**
- Change heading selector: `.blog-article h2` → your selector
- Adjust scroll offset: `-80px` → your header height
- Modify IntersectionObserver margins for activation timing

### PostCard

**Props:**
```typescript
interface PostCardProps {
  post: Post
  showCategory?: boolean  // Default: true
}
```

**Features:**
- Title with `line-clamp-2`
- Excerpt with `line-clamp-3`
- Category badge (optional)
- Hover effects with shadow

### ArticleInfo

**Props:**
```typescript
interface ArticleInfoProps {
  date: string
  category: string
  categoryDisplay: string
}
```

**Features:**
- Formats date to Japanese format (YYYY年M月D日)
- Shows calendar icon and category icon
- Dot separator between elements

### CategoryBadge

**Props:**
```typescript
interface CategoryBadgeProps {
  category: string
  clickable?: boolean  // Default: true
  size?: IconSize      // Default: 'md'
}
```

**Size classes:**
- `sm`: `text-xs px-2 py-0.5`
- `md`: `text-sm px-2.5 py-1`
- `lg`: `text-base px-3 py-1.5`

### CategoryIcon

**Props:**
```typescript
interface CategoryIconProps {
  icon: CategoryIcon
  className?: string
}
```

Renders either Devicon component or emoji span based on icon type.

### BlogSidebar

**Props:**
```typescript
interface BlogSidebarProps {
  categories: string[]
  recentPosts: Post[]
  currentCategory?: string
}
```

**Features:**
- Categories list with active highlighting
- Recent 5 posts
- Responsive grid on article pages

### ShareButtons

**Props:**
```typescript
interface ShareButtonsProps {
  title: string
  url: string
}
```

**Platforms:**
- Twitter
- Facebook
- Hatena Bookmark
- LINE
- Copy link

### BlogBreadcrumb

**Props:**
```typescript
interface BlogBreadcrumbProps {
  items: BreadcrumbItem[]
  className?: string
}
```

Wrapper for breadcrumb with structured data (JSON-LD).

## Page Templates Reference

### blog-index.tsx (Main Listing)

**Features:**
- Pagination (10 items per page)
- Category filter badges (mobile)
- Sidebar with categories and recent posts
- Static generation with `force-static`

**URL Pattern:** `/blog?page=N`

### blog-category.tsx (Category Listing)

**Features:**
- Category header with icon
- Pagination per category
- `generateStaticParams` for all categories
- Dynamic metadata generation

**URL Pattern:** `/blog/[category]?page=N`

### blog-detail.tsx (Article)

**Features:**
- Full article with markdown rendering
- Table of Contents (sidebar)
- Share buttons
- Related posts (same category)
- JSON-LD structured data
- Author info section

**URL Pattern:** `/blog/[category]/[slug]`

### layout.tsx

Imports CSS files:
- `blog.css` - Article styles
- `prism-tomorrow.css` - Syntax theme
- `prism-line-numbers.css` - Line numbers

## Styling Reference

### Typography

```css
.blog-article {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #2c3e50;
  line-height: 1.8;
  font-size: 16px;
}
```

**Heading hierarchy:**
| Element | Size | Weight | Special |
|---------|------|--------|---------|
| h1 | 2.5rem | 800 | 3px bottom border |
| h2 | 2rem | 700 | 1px bottom border |
| h3 | 1.5rem | 600 | Blue color (#3182ce) |
| h4 | 1.25rem | 600 | - |

### Code Blocks

```css
.blog-article pre {
  background-color: #2d2d2d;
  color: #e2e8f0;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  line-height: 1.6;
}
```

**Inline code:**
- Background: `#f1f5f9`
- Color: `#e11d48`
- Border radius: `0.25rem`

### Responsive Breakpoints

```css
@media (max-width: 768px) {
  .blog-article h1 { font-size: 2rem; }
  .blog-article h2 { font-size: 1.5rem; }
  .blog-article pre { font-size: 0.8rem; }
}
```

## Customization Guide

### Adding New Categories

1. Add category directory: `content/posts/[new-category]/`
2. Update `categories.ts`:

```typescript
// For programming languages (with devicon)
const PROGRAMMING_CATEGORIES: Record<string, string> = {
  // ... existing
  newlang: 'New Language',
}

// For non-programming (with emoji)
const NON_PROGRAMMING_CATEGORIES: Record<string, { name: string; emoji: string }> = {
  // ... existing
  newcat: { name: 'New Category', emoji: '🆕' },
}
```

### Custom Syntax Highlighting Theme

Replace Prism theme in `layout.tsx`:
```typescript
import 'prismjs/themes/prism-okaidia.css'  // or other theme
```

Available themes: `prism`, `prism-coy`, `prism-dark`, `prism-funky`, `prism-okaidia`, `prism-solarizedlight`, `prism-tomorrow`, `prism-twilight`

### Adding Frontmatter Fields

1. Update `Post` interface in `posts.ts`
2. Parse new field in post functions
3. Update components to display new field

Example (adding tags):
```typescript
interface Post {
  // ... existing fields
  tags: string[]
}

// In getPostBySlug:
return {
  // ... existing
  tags: data.tags || [],
}
```

### Custom Date Format

Modify `formatDate` in `ArticleInfo.tsx`:
```typescript
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  // Customize format here
  return date.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}
```

## Troubleshooting

### Prism Not Highlighting

**Symptoms:** Code blocks show plain text without colors

**Solution:**
1. Verify CSS imports in `layout.tsx`:
```typescript
import 'prismjs/themes/prism-tomorrow.css'
import 'prismjs/plugins/line-numbers/prism-line-numbers.css'
```
2. Check `rehype-prism-plus` is in dependencies

### Table of Contents Not Tracking

**Symptoms:** TOC doesn't highlight active section on scroll

**Solution:**
1. Verify heading selector matches your HTML structure
2. Check IntersectionObserver is supported (use polyfill if needed)
3. Ensure headings have IDs (rehype-slug should add them)

### Categories Not Showing

**Symptoms:** Empty category list or 404 on category pages

**Solution:**
1. Verify folder structure: `content/posts/[category]/`
2. Check category name matches folder name exactly
3. Ensure `.md` files exist in category folders

### Next.js 15 Params Error

**Symptoms:** `params.category` type error or undefined

**Solution:**
Next.js 15 requires awaiting params:
```typescript
// ❌ Wrong
export default function Page({ params }) {
  const { category } = params  // Error!
}

// ✅ Correct
export default async function Page({
  params,
}: {
  params: Promise<{ category: string }>
}) {
  const { category } = await params
}
```

### Japanese Headings Not Generating IDs

**Symptoms:** TOC links don't work for Japanese headings

**Solution:**
The `generateSafeId` function in `TableOfContents.tsx` handles this by creating index-based IDs when text contains only Japanese characters.

### rehype/remark Type Error

**Symptoms:** TypeScript error `Cannot find module 'rehype'` or runtime error with rehype-slug

**Solution:**
Install `rehype` as an explicit dependency:
```bash
npm install rehype
```

The `rehype-slug` and `rehype-prism-plus` packages require `rehype` as a peer dependency.

## Performance Optimization

### Static Generation

All blog pages use `force-static`:
```typescript
export const dynamic = 'force-static'
```

Generate all routes at build time:
```typescript
export async function generateStaticParams() {
  const categories = getAllCategories()
  return categories.map(category => ({ category }))
}
```

### Image Optimization

The markdown processor adds lazy loading:
```html
<img src="..." loading="lazy" decoding="async" />
```

For further optimization, consider using Next.js `<Image>` component.

### Bundle Size

To reduce bundle size:
1. Import only needed Prism languages
2. Use dynamic imports for heavy components
3. Consider code splitting for large pages

## Testing Reference

### Test Patterns

All tests follow the **Given/When/Then** format:

```typescript
test("存在しないカテゴリでは空配列が返される", () => {
  // Given: nonexistent-category フォルダが存在しない
  // When: getPostsByCategory('nonexistent') を呼び出す
  const posts = getPostsByCategory("nonexistent-category")

  // Then: 空配列 [] が返される
  expect(posts).toEqual([])
})
```

### Test Categories

| Category | Description | Example |
|----------|-------------|---------|
| **Happy Path** | Normal successful operation | Valid category returns posts |
| **Sad Path** | Expected failure scenarios | Non-existent category returns `[]` |
| **Edge Cases** | Boundary conditions | Empty string, null-like values |
| **Invalid Input** | Type errors, malformed data | Category name with special chars |

### posts.ts Test Cases

```typescript
describe("getPostsByCategory()", () => {
  // Happy Path
  test("有効なカテゴリで投稿を取得できる")
  test("投稿は日付降順でソートされる")

  // Sad Path
  test("存在しないカテゴリでは空配列が返される")

  // Edge Case
  test("各投稿にcategoryプロパティが設定される")
})

describe("getAllCategories()", () => {
  test("すべてのカテゴリフォルダを取得できる")
  test("カテゴリはディレクトリのみ")
})

describe("getPostBySlug()", () => {
  test("特定の投稿を取得できる")
  test("存在しないスラッグではnullが返される")
  test("空文字列のカテゴリではnullが返される")
})

describe("getAllPosts()", () => {
  test("全カテゴリの全投稿を取得できる")
  test("投稿は日付降順でソートされる")
})
```

### categories.ts Test Cases

```typescript
describe("isDeviconCategory()", () => {
  test("プログラミングカテゴリはtrueを返す")
  test("非プログラミングカテゴリはfalseを返す")
  test("大文字のカテゴリ名はfalseを返す") // 厳密マッチング
})

describe("getCategoryIcon()", () => {
  test("Deviconカテゴリで正しいアイコンが返される")
  test("絵文字カテゴリで正しいアイコンが返される")
  test("未定義カテゴリでデフォルト絵文字📌が返される")
  test("サイズ指定なしでデフォルト'sm'が適用される")
})

describe("getCategoryInfo()", () => {
  test("プログラミングカテゴリで正しい情報が返される")
  test("非プログラミングカテゴリで正しい情報が返される")
  test("未定義カテゴリでカテゴリ名がそのまま返される")
})

// 全カテゴリ網羅テスト
describe("全プログラミングカテゴリの網羅テスト", () => {
  test.each(programmingCategories)("$key カテゴリで正しい情報が返される")
})
```

### Component Test Cases

```typescript
// CategoryIcon
describe("CategoryIconComponent", () => {
  test("Deviconアイコンが正しくレンダリングされる")
  test("絵文字アイコンが正しくレンダリングされる")
  test("aria-label属性が付与される")
  test("カスタムclassNameが適用される")
})

// CategoryBadge
describe("CategoryBadge", () => {
  test("クリック可能なバッジがLinkでラップされる")
  test("クリック不可のバッジはLinkでラップされない")
  test("カテゴリ名が正しく表示される")
  test("バッジにアイコンが含まれる")
  test("異なるサイズでレンダリングできる")
})

// PostCard
describe("PostCard", () => {
  test("投稿カードが正しくレンダリングされる")
  test("正しいリンクURLが生成される")
  test("カテゴリバッジが表示/非表示できる")
  test("長いタイトル/excerptでもレンダリングされる")
})
```

### ESM Module Issue

**Problem:** Jest cannot transform ES modules from `rehype`, `remark`, etc.

```
SyntaxError: Cannot use import statement outside a module
  at node_modules/rehype/index.js:2
```

**Root cause:** These packages are ESM-only and Jest's default CommonJS transformation doesn't handle them.

**Solutions:**

1. **Skip markdown.ts tests** (Recommended)
   - Verify markdown conversion via browser
   - Focus unit tests on synchronous functions

2. **Configure transformIgnorePatterns**
   ```javascript
   // jest.config.js
   transformIgnorePatterns: [
     'node_modules/(?!(rehype|remark|unified|unist|vfile|bail|trough)/)',
   ],
   ```

3. **Use Vitest**
   - Native ESM support
   - Drop-in Jest replacement

### Browser Verification

When unit tests aren't possible, verify via browser:

```typescript
// Using chrome-devtools MCP
await mcp__chrome-devtools__navigate_page({ url: 'http://localhost:3000/blog' })
await mcp__chrome-devtools__take_screenshot()
await mcp__chrome-devtools__list_console_messages()
```

**Verification points:**
- Page loads without errors
- Content renders correctly
- Interactive elements work (TOC, buttons)
- No console errors
- Server returns 200

## SEO Checklist

- [ ] Unique title and description per page
- [ ] OpenGraph and Twitter card metadata
- [ ] JSON-LD structured data (BlogPosting schema)
- [ ] Breadcrumb navigation with schema.org
- [ ] Canonical URLs
- [ ] Sitemap integration
- [ ] Proper heading hierarchy (single H1)
- [ ] Alt text for images
- [ ] Fast page load (static generation)
