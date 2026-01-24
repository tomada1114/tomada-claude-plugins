/**
 * Blog Category Page (/blog/[category])
 *
 * Category-filtered blog listing with:
 * - Category header with icon
 * - Pagination
 * - Static generation for all categories
 *
 * File location: src/app/blog/[category]/page.tsx
 */

import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getPostsByCategory, getAllCategories, getAllPosts } from '@/lib/blog/posts'
import { BlogSidebar } from '@/components/blog/BlogSidebar'
import { PostCard } from '@/components/blog/PostCard'
import { CategoryBadge } from '@/components/blog/CategoryBadge'
import { getCategoryInfo } from '@/lib/blog/categories'
import { CategoryIconComponent } from '@/components/blog/CategoryIcon'
import { BlogBreadcrumb, generateBlogBreadcrumb } from '@/components/blog/BlogBreadcrumb'
import type { Metadata } from 'next'

// Force static generation
export const dynamic = 'force-static'

// Generate routes for all categories at build time
export async function generateStaticParams() {
  const categories = getAllCategories()
  return categories.map(category => ({ category }))
}

// Dynamic metadata based on category
export async function generateMetadata({
  params,
}: {
  params: Promise<{ category: string }>
}): Promise<Metadata> {
  const { category } = await params
  const categoryInfo = getCategoryInfo(category)

  return {
    title: `${categoryInfo.name} | Blog | Your Site Name`,
    description: `Browse ${categoryInfo.name} articles and tutorials.`,
    openGraph: {
      title: `${categoryInfo.name} | Blog | Your Site Name`,
      description: `Browse ${categoryInfo.name} articles and tutorials.`,
    },
  }
}

const ITEMS_PER_PAGE = 10

export default async function CategoryPage({
  params,
  searchParams,
}: {
  params: Promise<{ category: string }>
  searchParams: Promise<{ page?: string }>
}) {
  const { category } = await params
  const { page } = await searchParams
  const currentPage = page ? parseInt(page, 10) : 1

  const allCategoryPosts = getPostsByCategory(category)
  const allPosts = getAllPosts()
  const categories = getAllCategories()

  // 404 if category has no posts
  if (allCategoryPosts.length === 0) {
    notFound()
  }

  const categoryInfo = getCategoryInfo(category, 'lg')

  // Pagination
  const totalPages = Math.ceil(allCategoryPosts.length / ITEMS_PER_PAGE)
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
  const posts = allCategoryPosts.slice(startIndex, startIndex + ITEMS_PER_PAGE)

  const breadcrumbs = generateBlogBreadcrumb(categoryInfo.name, category)

  return (
    <div className="mx-auto max-w-7xl min-w-0 px-4 py-8 sm:px-6 lg:px-8">
      {/* Breadcrumb Navigation */}
      <BlogBreadcrumb items={breadcrumbs} className="mb-6" />

      {/* Category Header */}
      <div className="mb-8">
        <div className="mb-4 flex items-center gap-3">
          <div className="text-4xl">
            <CategoryIconComponent icon={{ ...categoryInfo.icon, size: 'lg' }} />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{categoryInfo.name}</h1>
            <p className="mt-1 text-gray-600">{allCategoryPosts.length} posts</p>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-8 lg:flex-row">
        {/* Main Content */}
        <main className="flex-1">
          {/* Other Categories (Mobile) */}
          <div className="mb-6 flex flex-wrap gap-2 lg:hidden">
            {categories.map(cat => (
              <CategoryBadge key={cat} category={cat} size={cat === category ? 'md' : 'sm'} />
            ))}
          </div>

          {/* Post List */}
          <div className="grid gap-6">
            {posts.map(post => (
              <PostCard key={post.slug} post={post} showCategory={false} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              {currentPage > 1 ? (
                <Link
                  href={`/blog/${category}?page=${currentPage - 1}`}
                  className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-gray-50"
                >
                  Previous
                </Link>
              ) : (
                <span className="rounded-md border px-4 py-2 text-sm font-medium text-gray-400">
                  Previous
                </span>
              )}

              <span className="px-4 py-2 text-sm">
                Page {currentPage} of {totalPages}
              </span>

              {currentPage < totalPages ? (
                <Link
                  href={`/blog/${category}?page=${currentPage + 1}`}
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
          <BlogSidebar categories={categories} recentPosts={allPosts} currentCategory={category} />
        </div>
      </div>
    </div>
  )
}
