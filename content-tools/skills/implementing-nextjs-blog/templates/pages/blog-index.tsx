/**
 * Blog Index Page (/blog)
 *
 * Main blog listing page with:
 * - Paginated post list
 * - Category filter badges (mobile)
 * - Sidebar with categories and recent posts
 *
 * File location: src/app/blog/page.tsx
 *
 * Note: This template uses a simple pagination approach.
 * Customize the pagination component for your UI library.
 */

import Link from 'next/link'
import { getAllPosts, getAllCategories } from '@/lib/blog/posts'
import { BlogSidebar } from '@/components/blog/BlogSidebar'
import { PostCard } from '@/components/blog/PostCard'
import { CategoryBadge } from '@/components/blog/CategoryBadge'
import { BlogBreadcrumb, generateBlogBreadcrumb } from '@/components/blog/BlogBreadcrumb'
import type { Metadata } from 'next'

// Force static generation at build time
export const dynamic = 'force-static'

// SEO metadata
export const metadata: Metadata = {
  title: 'Blog | Your Site Name',
  description: 'Read our latest articles and tutorials.',
  openGraph: {
    title: 'Blog | Your Site Name',
    description: 'Read our latest articles and tutorials.',
  },
}

// Pagination config
const ITEMS_PER_PAGE = 10

export default async function BlogPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>
}) {
  const params = await searchParams
  const currentPage = params.page ? parseInt(params.page, 10) : 1

  const allPosts = getAllPosts()
  const categories = getAllCategories()

  // Calculate pagination
  const totalPages = Math.ceil(allPosts.length / ITEMS_PER_PAGE)
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
  const posts = allPosts.slice(startIndex, startIndex + ITEMS_PER_PAGE)

  const breadcrumbs = generateBlogBreadcrumb()

  return (
    <div className="mx-auto max-w-7xl min-w-0 px-4 py-8 sm:px-6 lg:px-8">
      {/* Breadcrumb Navigation */}
      <BlogBreadcrumb items={breadcrumbs} className="mb-6" />

      {/* Page Header */}
      <div className="mb-8">
        <h1 className="mb-4 text-3xl font-bold text-gray-900">Blog</h1>
        <p className="text-gray-600">Read our latest articles and tutorials</p>
      </div>

      <div className="flex flex-col gap-8 lg:flex-row">
        {/* Main Content */}
        <main className="flex-1">
          {/* Category Filter (Mobile) */}
          <div className="mb-6 flex flex-wrap gap-2 lg:hidden">
            {categories.map(category => (
              <CategoryBadge key={category} category={category} />
            ))}
          </div>

          {/* Post List */}
          <div className="grid gap-6">
            {posts.map(post => (
              <PostCard key={`${post.category}-${post.slug}`} post={post} showCategory={true} />
            ))}
          </div>

          {/* Empty State */}
          {posts.length === 0 && (
            <div className="py-12 text-center">
              <p className="text-gray-500">No posts yet</p>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              {/* Previous */}
              {currentPage > 1 ? (
                <Link
                  href={`/blog?page=${currentPage - 1}`}
                  className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-gray-50"
                >
                  Previous
                </Link>
              ) : (
                <span className="rounded-md border px-4 py-2 text-sm font-medium text-gray-400">
                  Previous
                </span>
              )}

              {/* Page Numbers */}
              <span className="px-4 py-2 text-sm">
                Page {currentPage} of {totalPages}
              </span>

              {/* Next */}
              {currentPage < totalPages ? (
                <Link
                  href={`/blog?page=${currentPage + 1}`}
                  className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-gray-50"
                >
                  Next
                </Link>
              ) : (
                <span className="rounded-md border px-4 py-2 text-sm font-medium text-gray-400">
                  Next
                </span>
              )}
            </div>
          )}
        </main>

        {/* Sidebar (Desktop) */}
        <div className="hidden lg:block lg:w-64">
          <BlogSidebar categories={categories} recentPosts={allPosts} />
        </div>
      </div>
    </div>
  )
}
