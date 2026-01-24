/**
 * Blog Sidebar Component
 *
 * Client-side sidebar displaying:
 * - Categories list with active highlighting
 * - Recent posts (5 most recent)
 *
 * Props:
 *   categories: string[] - List of category slugs
 *   recentPosts: Post[] - All posts (will show 5 most recent)
 *   currentCategory?: string - Currently active category
 *
 * Usage:
 *   <BlogSidebar
 *     categories={['javascript', 'react']}
 *     recentPosts={allPosts}
 *     currentCategory="javascript"
 *   />
 */

'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { getCategoryInfo } from '@/lib/blog/categories'
import { CategoryIconComponent } from './CategoryIcon'
import type { Post } from '@/lib/blog/posts'

interface BlogSidebarProps {
  categories: string[]
  recentPosts: Post[]
  currentCategory?: string
}

export function BlogSidebar({ categories, recentPosts, currentCategory }: BlogSidebarProps) {
  const pathname = usePathname()

  // Check if we're on an article page (3 path segments: /blog/category/slug)
  const isArticlePage = pathname.includes('/blog/') && pathname.split('/').length === 4

  return (
    <aside className={`w-full ${isArticlePage ? 'grid gap-8 lg:grid-cols-2' : 'space-y-8'}`}>
      {/* Categories List */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 flex items-center gap-2 text-lg font-bold">
          <span className="text-xl">📁</span>
          Categories
        </h3>
        <nav className="space-y-2">
          <Link
            href="/blog"
            className={`block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              pathname === '/blog' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-50'
            }`}
          >
            All Posts
          </Link>
          {categories.map(category => (
            <Link
              key={category}
              href={`/blog/${category}`}
              className={`block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                currentCategory === category
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <div className="inline-flex items-center gap-2">
                <CategoryIconComponent icon={getCategoryInfo(category, 'sm').icon} />
                <span>{getCategoryInfo(category).name}</span>
              </div>
            </Link>
          ))}
        </nav>
      </div>

      {/* Recent Posts */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 flex items-center gap-2 text-lg font-bold">
          <span className="text-xl">🆕</span>
          Recent Posts
        </h3>
        <div className="space-y-3">
          {recentPosts.slice(0, 5).map(post => (
            <Link
              key={`${post.category}-${post.slug}`}
              href={`/blog/${post.category}/${post.slug}`}
              className="group block"
            >
              <h4 className="line-clamp-2 text-sm font-medium text-gray-900 transition-colors group-hover:text-blue-600">
                {post.title}
              </h4>
            </Link>
          ))}
        </div>
      </div>
    </aside>
  )
}
