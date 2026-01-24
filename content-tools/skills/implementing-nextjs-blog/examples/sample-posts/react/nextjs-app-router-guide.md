---
title: Next.js 15 App Router Guide
date: '2024-02-15'
excerpt: Master the Next.js App Router with server components, routing patterns, and data fetching.
---

## Introduction to App Router

Next.js 13+ introduced the App Router, a new paradigm for building React applications with:

- Server Components by default
- Nested layouts
- Streaming and Suspense
- Simplified data fetching

## File-Based Routing

### Basic Routes

```
app/
├── page.tsx          → /
├── about/
│   └── page.tsx      → /about
├── blog/
│   ├── page.tsx      → /blog
│   └── [slug]/
│       └── page.tsx  → /blog/:slug
```

### Dynamic Routes

```tsx
// app/blog/[slug]/page.tsx
export default async function BlogPost({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params;

  return <h1>Post: {slug}</h1>;
}
```

> **Important:** In Next.js 15, `params` is a Promise and must be awaited.

## Server vs Client Components

### Server Components (Default)

```tsx
// This is a Server Component by default
async function ProductList() {
  // Can directly fetch data
  const products = await fetch('https://api.example.com/products')
    .then(r => r.json());

  return (
    <ul>
      {products.map(p => <li key={p.id}>{p.name}</li>)}
    </ul>
  );
}
```

### Client Components

```tsx
'use client';

import { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);

  return (
    <button onClick={() => setCount(c => c + 1)}>
      Count: {count}
    </button>
  );
}
```

| Feature | Server Component | Client Component |
|---------|------------------|------------------|
| Data fetching | Direct async | useEffect or SWR |
| useState/useEffect | ❌ | ✅ |
| Event handlers | ❌ | ✅ |
| Browser APIs | ❌ | ✅ |
| Bundle size | Not included | Included |

## Layouts and Templates

### Root Layout

```tsx
// app/layout.tsx
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header>Site Header</header>
        <main>{children}</main>
        <footer>Site Footer</footer>
      </body>
    </html>
  );
}
```

### Nested Layouts

```tsx
// app/blog/layout.tsx
export default function BlogLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="blog-container">
      <nav>Blog Navigation</nav>
      {children}
    </div>
  );
}
```

## Data Fetching Patterns

### Static Data (Default)

```tsx
// Cached and revalidated at build time
async function getProducts() {
  const res = await fetch('https://api.example.com/products');
  return res.json();
}
```

### Revalidation

```tsx
// Revalidate every hour
async function getProducts() {
  const res = await fetch('https://api.example.com/products', {
    next: { revalidate: 3600 }
  });
  return res.json();
}
```

### Dynamic Data

```tsx
// Always fresh data
async function getUser() {
  const res = await fetch('https://api.example.com/user', {
    cache: 'no-store'
  });
  return res.json();
}
```

## Loading and Error States

### Loading UI

```tsx
// app/blog/loading.tsx
export default function Loading() {
  return <div className="skeleton">Loading...</div>;
}
```

### Error Handling

```tsx
'use client';

// app/blog/error.tsx
export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

## Metadata

```tsx
// Static metadata
export const metadata = {
  title: 'My Blog',
  description: 'A blog about web development',
};

// Dynamic metadata
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params;
  const post = await getPost(slug);

  return {
    title: post.title,
    description: post.excerpt,
  };
}
```

## Static Generation

```tsx
// Generate all paths at build time
export async function generateStaticParams() {
  const posts = await getAllPosts();

  return posts.map(post => ({
    slug: post.slug,
  }));
}

// Force static generation
export const dynamic = 'force-static';
```

## Conclusion

The App Router brings powerful features for building modern web applications. Start with server components, add client interactivity where needed, and leverage the built-in caching and streaming capabilities.
