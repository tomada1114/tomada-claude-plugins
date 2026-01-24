---
name: implementing-nextjs-blog
description: Implement a production-ready markdown blog system in Next.js 15 App Router with static generation, syntax highlighting, scroll-tracking TOC, categories, and SEO. Use PROACTIVELY when adding blog, markdown blog, Next.js blog, article system, blog feature, blog pages, blog implementation, or working with gray-matter, remark, rehype, prism syntax highlighting, TableOfContents, blog categories. Examples: <example>Context: User wants to add blog user: 'Add a blog to my Next.js project' assistant: 'I will use implementing-nextjs-blog skill' <commentary>Triggered by blog implementation request</commentary></example> <example>Context: User asks about markdown blog user: 'How do I implement markdown-based blog?' assistant: 'I will use implementing-nextjs-blog skill' <commentary>Triggered by markdown blog question</commentary></example>
---

# Next.js Blog Implementation Guide

A comprehensive skill for implementing production-ready markdown blog systems in Next.js 15 App Router projects. Based on a battle-tested implementation with 197+ blog posts.

## When to Use This Skill

**Use this skill when:**
- Adding a blog or article system to a Next.js project
- Implementing markdown-based content with syntax highlighting
- Creating a Table of Contents with scroll tracking
- Setting up category-based content organization
- Implementing SEO for blog posts (JSON-LD, OpenGraph)

**Don't use this skill for:**
- CMS-based blogs (use headless CMS integration instead)
- Simple single-page markdown rendering
- Non-Next.js projects

## Quick Start (5 Steps)

### Step 1: Install Dependencies

```bash
npm install gray-matter remark remark-gfm remark-html rehype rehype-slug rehype-prism-plus prismjs
```

> **Note:** `rehype` is required as a core dependency for `rehype-slug` and `rehype-prism-plus` to work properly.

### Step 2: Create Directory Structure

```
src/
├── lib/blog/
│   ├── posts.ts         # Post discovery & parsing
│   ├── markdown.ts      # Markdown processor
│   └── categories.ts    # Category configuration
├── components/blog/
│   ├── TableOfContents.tsx
│   ├── PostCard.tsx
│   └── ... (more components)
├── app/blog/
│   ├── page.tsx         # /blog
│   ├── [category]/
│   │   ├── page.tsx     # /blog/[category]
│   │   └── [slug]/
│   │       └── page.tsx # /blog/[category]/[slug]
│   └── blog.css
└── content/posts/       # Markdown content
    ├── javascript/
    ├── react/
    └── ...
```

### Step 3: Copy Templates

Use templates from `templates/` directory:
- `lib/posts.ts` → `src/lib/blog/posts.ts`
- `lib/markdown.ts` → `src/lib/blog/markdown.ts`
- `lib/categories.ts` → `src/lib/blog/categories.ts`
- Components → `src/components/blog/`
- Pages → `src/app/blog/`
- `styles/blog.css` → `src/app/blog/blog.css`

### Step 4: Add Prism CSS

Import in your blog detail page:
```typescript
import 'prismjs/themes/prism-tomorrow.css'
import 'prismjs/plugins/line-numbers/prism-line-numbers.css'
```

### Step 5: Create Sample Post

```markdown
// content/posts/javascript/getting-started.md
---
title: Getting Started with JavaScript
date: '2024-01-15'
excerpt: Learn the basics of JavaScript programming.
---

## Introduction

Your content here...
```

## Features

### 1. Markdown Processing Pipeline

- **remark**: Markdown to HTML conversion
- **remark-gfm**: GitHub Flavored Markdown (tables, strikethrough)
- **rehype-slug**: Auto-generates heading IDs
- **rehype-prism-plus**: Syntax highlighting with line numbers

### 2. Table of Contents

- Extracts H2 headings from article content
- IntersectionObserver for scroll tracking
- Highlights active section
- Supports Japanese characters and special symbols
- Sticky positioning with smooth scroll

### 3. Category System

- Folder-based organization (`content/posts/[category]/`)
- Icon support: Devicon for programming languages, emoji for others
- Category badges with links
- Category filtering pages

### 4. Static Generation

- `force-static` for full static pre-rendering
- `generateStaticParams()` for all routes
- Pagination support (default 10 per page)
- ISR-ready architecture

### 5. SEO

- JSON-LD structured data (BlogPosting schema)
- OpenGraph and Twitter cards
- Breadcrumb navigation with schema.org
- Dynamic metadata generation

## Customization Points

### Categories

Edit `categories.ts` to add/modify categories:
```typescript
const DEVICON_MAPPING: Record<string, string> = {
  javascript: 'javascript',
  typescript: 'typescript',
  // Add your categories...
}
```

### Styling

Modify `blog.css` for:
- Typography (fonts, sizes, line heights)
- Code block theme (uses Prism Tomorrow)
- Image styling
- Responsive breakpoints

### Frontmatter Schema

Default fields:
```yaml
---
title: string      # Required
date: string       # Required (YYYY-MM-DD)
excerpt: string    # Recommended for SEO
---
```

## Templates Reference

See `templates/` directory for all source files:

| Template | Purpose |
|----------|---------|
| `lib/posts.ts` | Post discovery, parsing, sorting |
| `lib/markdown.ts` | Markdown → HTML with Prism |
| `lib/categories.ts` | Category config with icons |
| `components/TableOfContents.tsx` | Scroll-tracking TOC |
| `components/PostCard.tsx` | Post preview cards |
| `components/ArticleInfo.tsx` | Date/category display |
| `components/CategoryBadge.tsx` | Category pills |
| `components/CategoryIcon.tsx` | Icon renderer |
| `components/BlogSidebar.tsx` | Sidebar navigation |
| `components/ShareButtons.tsx` | Social sharing |
| `pages/blog-index.tsx` | Main listing |
| `pages/blog-category.tsx` | Category page |
| `pages/blog-detail.tsx` | Article detail |
| `styles/blog.css` | Article styles |

## AI Assistant Instructions

### When Implementing a Blog

1. **Check Prerequisites**:
   - Is Next.js 15 with App Router?
   - Is TypeScript available?
   - Is Tailwind CSS configured?

2. **Install Dependencies First**:
   ```bash
   npm install gray-matter remark remark-gfm remark-html rehype-slug rehype-prism-plus prismjs
   ```

3. **Create Files in Order**:
   1. Library utilities (`lib/blog/`)
   2. Components (`components/blog/`)
   3. Pages (`app/blog/`)
   4. CSS (`app/blog/blog.css`)
   5. Content directory (`content/posts/`)

4. **Adapt Templates**:
   - Adjust import paths to match project structure
   - Replace pagination component if project uses different UI library
   - Customize category list to match project needs

5. **Test**:
   - Create sample markdown file
   - Run dev server and verify rendering
   - Check TOC scroll tracking
   - Verify syntax highlighting

6. **Write Unit Tests** (see Testing section below)

### When Customizing

- Read [reference.md](reference.md) for detailed component APIs
- Check examples in `examples/folder-structure.md`
- Start with minimal changes, expand as needed

### Common Issues

1. **Prism not highlighting**: Import CSS files in page
2. **TOC not tracking**: Check heading selector (`.blog-article h2`)
3. **Categories not showing**: Verify folder structure matches config
4. **Next.js 15 params error**: Must `await params` in async pages
5. **rehype/remark type error**: Install `rehype` package explicitly (not just `rehype-slug`)

See [reference.md](reference.md) for detailed troubleshooting.

## Testing Strategy

### Test File Structure

```
src/lib/blog/__tests__/
├── posts.test.ts        # Post discovery & parsing
├── categories.test.ts   # Category configuration
└── (markdown.test.ts)   # ⚠️ ESM compatibility issues

src/components/blog/__tests__/
├── CategoryIcon.test.tsx
├── CategoryBadge.test.tsx
└── PostCard.test.tsx
```

### Recommended Test Coverage

| Module | Test Count | Focus Areas |
|--------|-----------|-------------|
| `posts.ts` | 14+ | File reading, sorting, edge cases (empty/missing) |
| `categories.ts` | 48+ | All category mappings, fallback behavior |
| `CategoryIcon` | 7+ | Devicon/emoji rendering, sizes, aria-labels |
| `CategoryBadge` | 10+ | Clickable states, sizes, link generation |
| `PostCard` | 11+ | Content display, truncation, category display |

### Important: ESM Module Compatibility

**⚠️ `markdown.ts` cannot be tested with Jest** due to ESM module issues with `rehype`, `remark`, and related packages.

```
SyntaxError: Cannot use import statement outside a module
```

**Workarounds:**
1. Skip `markdown.test.ts` - verify via browser testing instead
2. Configure `transformIgnorePatterns` in Jest (complex setup)
3. Use Vitest (supports ESM natively)

**Recommended approach:** Skip unit tests for `markdown.ts` and verify markdown conversion through browser inspection.

### Browser Verification Checklist

Use browser DevTools or chrome-devtools MCP to verify:

- [ ] **Blog index page**: Posts display, pagination works
- [ ] **Article detail page**: Content renders, syntax highlighting works
- [ ] **TOC scroll tracking**: Active section highlights on scroll
- [ ] **Category page**: Filtering works, correct posts shown
- [ ] **Share buttons**: Links generate correctly
- [ ] **Console**: No JavaScript errors
- [ ] **Server**: All pages return 200 status

## Additional Resources

- [reference.md](reference.md): Complete API documentation
- [examples/folder-structure.md](examples/folder-structure.md): Project structure guide
- [templates/](templates/): All source templates
