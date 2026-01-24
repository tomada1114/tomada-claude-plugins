/**
 * Blog Detail Page (/blog/[category]/[slug])
 *
 * Individual article page with:
 * - Full article content with markdown rendering
 * - Table of Contents (sidebar)
 * - Share buttons
 * - Related posts
 * - JSON-LD structured data for SEO
 *
 * File location: src/app/blog/[category]/[slug]/page.tsx
 *
 * Security Note: This template uses dangerouslySetInnerHTML for markdown content.
 * This is safe because:
 * 1. Content comes from trusted markdown files in your repo (not user input)
 * 2. Content is processed server-side at build time
 * 3. This is the standard pattern for static blog generators
 *
 * If you accept user-generated markdown, add sanitization with DOMPurify.
 */

import Link from 'next/link'
import Script from 'next/script'
import { notFound } from 'next/navigation'
import { getPostBySlug, getAllCategories, getPostsByCategory, getAllPosts } from '@/lib/blog/posts'
import { markdownToHtml } from '@/lib/blog/markdown'
import { CategoryBadge } from '@/components/blog/CategoryBadge'
import { PostCard } from '@/components/blog/PostCard'
import { ArticleInfo } from '@/components/blog/ArticleInfo'
import { TableOfContents } from '@/components/blog/TableOfContents'
import { ShareButtons } from '@/components/blog/ShareButtons'
import { BlogSidebar } from '@/components/blog/BlogSidebar'
import { getCategoryInfo } from '@/lib/blog/categories'
import { BlogBreadcrumb, generateBlogBreadcrumb } from '@/components/blog/BlogBreadcrumb'
import type { Metadata } from 'next'

// Force static generation
export const dynamic = 'force-static'

// Generate routes for all posts at build time
export async function generateStaticParams() {
  const categories = getAllCategories()
  const params = []

  for (const category of categories) {
    const posts = getPostsByCategory(category)
    for (const post of posts) {
      params.push({
        category,
        slug: post.slug,
      })
    }
  }

  return params
}

// Dynamic metadata
export async function generateMetadata({
  params,
}: {
  params: Promise<{ category: string; slug: string }>
}): Promise<Metadata> {
  const { category, slug } = await params
  const post = getPostBySlug(category, slug)

  if (!post) {
    return {
      title: 'Post Not Found | Your Site Name',
    }
  }

  return {
    title: `${post.title} | Your Site Name`,
    description: post.excerpt,
    openGraph: {
      title: `${post.title} | Your Site Name`,
      description: post.excerpt,
      type: 'article',
      publishedTime: post.date,
    },
    twitter: {
      card: 'summary_large_image',
      title: `${post.title} | Your Site Name`,
      description: post.excerpt,
    },
  }
}

/**
 * Article Content Component
 * Renders sanitized HTML from markdown processing
 */
function ArticleContent({ html }: { html: string }) {
  // Content is from trusted markdown files, processed at build time
  // For user-generated content, add DOMPurify sanitization here
  return <div className="blog-article" dangerouslySetInnerHTML={{ __html: html }} />
}

export default async function BlogPost({
  params,
}: {
  params: Promise<{ category: string; slug: string }>
}) {
  const { category, slug } = await params
  const post = getPostBySlug(category, slug)

  if (!post) {
    notFound()
  }

  const content = await markdownToHtml(post.content)

  // Related posts (same category, excluding current)
  const relatedPosts = getPostsByCategory(category)
    .filter(p => p.slug !== slug)
    .slice(0, 3)

  const categoryInfo = getCategoryInfo(category)
  const allPosts = getAllPosts()
  const categories = getAllCategories()

  // JSON-LD structured data for SEO
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: post.title,
    description: post.excerpt,
    datePublished: post.date,
    dateModified: post.date,
    author: {
      '@type': 'Organization',
      name: 'Your Site Name',
    },
    publisher: {
      '@type': 'Organization',
      name: 'Your Site Name',
      logo: {
        '@type': 'ImageObject',
        url: `${process.env.NEXT_PUBLIC_SITE_URL || ''}/logo.png`,
      },
    },
  }

  const breadcrumbs = generateBlogBreadcrumb(categoryInfo.name, category, post.title)
  const articleUrl = `${process.env.NEXT_PUBLIC_SITE_URL || ''}/blog/${category}/${slug}`

  return (
    <>
      {/* Structured Data for SEO */}
      <Script id="json-ld" type="application/ld+json" strategy="afterInteractive">
        {JSON.stringify(jsonLd)}
      </Script>

      <div className="mx-auto max-w-7xl min-w-0 px-4 py-8 sm:px-6 lg:px-8">
        {/* Breadcrumb Navigation */}
        <BlogBreadcrumb items={breadcrumbs} className="mb-6" />

        <div className="flex flex-col gap-8 lg:flex-row">
          {/* Main Content */}
          <div className="flex-1">
            <article className="max-w-4xl">
              <h1 className="mb-4 text-2xl font-bold">{post.title}</h1>

              <ArticleInfo
                date={post.date}
                category={post.category}
                categoryDisplay={categoryInfo.name}
              />

              {/* Article Content - Uses blog.css styles */}
              <ArticleContent html={content} />

              {/* Share Buttons */}
              <div className="mt-8 rounded-lg bg-gray-50 p-6">
                <ShareButtons title={post.title} url={articleUrl} />
              </div>

              {/* Footer with category and back link */}
              <div className="mt-8 border-t border-gray-200 pt-8">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-600">Category:</span>
                    <CategoryBadge category={post.category} />
                  </div>
                  <Link
                    href="/blog"
                    className="text-sm font-medium text-blue-600 hover:text-blue-700"
                  >
                    ← Back to all posts
                  </Link>
                </div>
              </div>
            </article>
          </div>

          {/* Table of Contents (Desktop) */}
          <aside className="hidden lg:block lg:w-64">
            <TableOfContents />
          </aside>
        </div>

        {/* Related Posts */}
        {relatedPosts.length > 0 && (
          <div className="mt-16">
            <div className="mb-6">
              <h2 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
                <span className="text-xl">📚</span>
                Related Posts
              </h2>
              <p className="mt-1 text-gray-600">More from {categoryInfo.name}</p>
            </div>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {relatedPosts.map(relatedPost => (
                <PostCard key={relatedPost.slug} post={relatedPost} showCategory={false} />
              ))}
            </div>
            <div className="mt-8 text-center">
              <Link
                href={`/blog/${category}`}
                className="inline-flex items-center gap-2 font-medium text-blue-600 hover:text-blue-700"
              >
                <span>View all {categoryInfo.name} posts</span>
                <span>→</span>
              </Link>
            </div>
          </div>
        )}

        {/* Sidebar (bottom on mobile, categories and recent posts) */}
        <div className="mt-16">
          <BlogSidebar categories={categories} recentPosts={allPosts} currentCategory={category} />
        </div>
      </div>
    </>
  )
}
