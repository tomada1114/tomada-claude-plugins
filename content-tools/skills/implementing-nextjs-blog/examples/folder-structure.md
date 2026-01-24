# Blog System Folder Structure

This document shows the recommended folder structure for implementing the blog system in a Next.js 15 project.

## Sample Posts for Testing

Copy the sample posts from `examples/sample-posts/` to verify your blog setup:

```bash
# Copy sample posts to your project
cp -r ~/.claude/skills/implementing-nextjs-blog/examples/sample-posts/* content/posts/
```

Available samples:
- `javascript/getting-started-with-javascript.md` - Variables, functions, control flow
- `javascript/async-await-guide.md` - Async programming patterns
- `react/react-hooks-introduction.md` - useState, useEffect, custom hooks
- `react/nextjs-app-router-guide.md` - Server components, routing, data fetching
- `general/welcome-to-the-blog.md` - Simple welcome post

## Complete Project Structure

```
your-project/
├── package.json
├── next.config.js
├── tailwind.config.js
│
├── content/
│   └── posts/                     # Markdown content
│       ├── javascript/
│       │   ├── getting-started.md
│       │   └── advanced-tips.md
│       ├── react/
│       │   └── hooks-guide.md
│       ├── typescript/
│       │   └── type-safety.md
│       └── general/
│           └── welcome.md
│
├── public/
│   └── images/
│       └── blog/                  # Blog images
│           └── post-image.png
│
└── src/
    ├── app/
    │   ├── layout.tsx             # Root layout
    │   ├── page.tsx               # Home page
    │   │
    │   └── blog/
    │       ├── layout.tsx         # Blog layout (imports CSS)
    │       ├── blog.css           # Article styles
    │       ├── page.tsx           # /blog - Main listing
    │       │
    │       └── [category]/
    │           ├── page.tsx       # /blog/[category] - Category listing
    │           │
    │           └── [slug]/
    │               └── page.tsx   # /blog/[category]/[slug] - Article detail
    │
    ├── components/
    │   └── blog/
    │       ├── index.ts           # Barrel export (optional)
    │       ├── TableOfContents.tsx
    │       ├── PostCard.tsx
    │       ├── ArticleInfo.tsx
    │       ├── CategoryBadge.tsx
    │       ├── CategoryIcon.tsx
    │       ├── BlogSidebar.tsx
    │       ├── ShareButtons.tsx
    │       ├── BlogHeader.tsx
    │       └── BlogBreadcrumb.tsx
    │
    └── lib/
        └── blog/
            ├── posts.ts           # Post discovery & parsing
            ├── markdown.ts        # Markdown processor
            └── categories.ts      # Category configuration
```

## File Dependencies

```
layout.tsx
├── imports blog.css
├── imports prismjs/themes/prism-tomorrow.css
└── imports prismjs/plugins/line-numbers/prism-line-numbers.css

page.tsx (blog index)
├── imports from lib/blog/posts.ts
├── imports from lib/blog/categories.ts
└── imports components/blog/*

[category]/page.tsx
├── imports from lib/blog/posts.ts
├── imports from lib/blog/categories.ts
└── imports components/blog/*

[category]/[slug]/page.tsx
├── imports from lib/blog/posts.ts
├── imports from lib/blog/markdown.ts
├── imports from lib/blog/categories.ts
└── imports components/blog/*
```

## Markdown File Format

```markdown
---
title: Your Article Title
date: '2024-01-15'
excerpt: A brief description for SEO and previews
---

## Introduction

Your content here...

### Code Example

\`\`\`javascript
const greeting = 'Hello, World!';
console.log(greeting);
\`\`\`

## Another Section

More content...
```

## Required Dependencies

```json
{
  "dependencies": {
    "gray-matter": "^4.0.3",
    "remark": "^15.0.0",
    "remark-gfm": "^4.0.0",
    "remark-html": "^16.0.0",
    "rehype": "^13.0.0",
    "rehype-slug": "^6.0.0",
    "rehype-prism-plus": "^2.0.0",
    "prismjs": "^1.29.0"
  }
}
```

## Installation Steps

```bash
# 1. Install dependencies
npm install gray-matter remark remark-gfm remark-html rehype rehype-slug rehype-prism-plus prismjs

# 2. Create directories
mkdir -p src/lib/blog
mkdir -p src/components/blog
mkdir -p src/app/blog/\[category\]/\[slug\]
mkdir -p content/posts/general

# 3. Copy template files
# (Copy from templates/ directory)

# 4. Create sample post
cat > content/posts/general/welcome.md << 'EOF'
---
title: Welcome to the Blog
date: '2024-01-01'
excerpt: Welcome to our new blog!
---

## Welcome

This is your first blog post.
EOF

# 5. Start development server
npm run dev
```

## Category Setup

Edit `src/lib/blog/categories.ts` to add your categories:

```typescript
// Programming categories (use devicon icons)
const PROGRAMMING_CATEGORIES: Record<string, string> = {
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  react: 'React',
  // Add more...
}

// Non-programming categories (use emoji icons)
const NON_PROGRAMMING_CATEGORIES: Record<string, { name: string; emoji: string }> = {
  tutorial: { name: 'Tutorial', emoji: '📚' },
  news: { name: 'News', emoji: '📰' },
  // Add more...
}
```

## Devicon Setup (Optional)

For programming language icons, add to your root layout:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/devicon.min.css">
```

Or install as npm package and import in your layout.

## Tailwind CSS Configuration

Ensure your `tailwind.config.js` includes the blog paths:

```javascript
module.exports = {
  content: [
    './src/app/**/*.{js,ts,jsx,tsx}',
    './src/components/**/*.{js,ts,jsx,tsx}',
  ],
  // ...
}
```

## TypeScript Path Aliases

Ensure your `tsconfig.json` has the `@/` path alias:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

## Common Issues

### "Module not found" errors

Verify all imports use the correct path aliases (`@/lib/blog/posts`, etc.)

### Prism not highlighting

1. Check CSS imports in `layout.tsx`
2. Verify `prismjs` is installed
3. Ensure `rehype-prism-plus` is in the markdown pipeline

### Categories not showing

1. Create the category folder in `content/posts/`
2. Add at least one `.md` file
3. Update `categories.ts` with the category name

### Next.js 15 type errors

Remember to await params in page components:

```typescript
// ❌ Wrong
const { category } = params

// ✅ Correct
const { category } = await params
```
