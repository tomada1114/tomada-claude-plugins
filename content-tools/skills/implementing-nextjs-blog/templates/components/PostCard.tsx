/**
 * Post Card Component
 *
 * Displays a blog post preview with title, excerpt, and category.
 *
 * Props:
 *   post: Post - The post data to display
 *   showCategory?: boolean - Whether to show category badge (default: true)
 *
 * Usage:
 *   <PostCard post={post} showCategory={true} />
 */

import Link from 'next/link'
import type { Post } from '@/lib/blog/posts'
import { getCategoryInfo } from '@/lib/blog/categories'
import { CategoryIconComponent } from './CategoryIcon'

interface PostCardProps {
  post: Post
  showCategory?: boolean
}

export function PostCard({ post, showCategory = true }: PostCardProps) {
  const categoryInfo = getCategoryInfo(post.category)

  return (
    <article className="rounded-lg border border-gray-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      <Link href={`/blog/${post.category}/${post.slug}`} className="block p-6">
        <div className="mb-3">
          {showCategory && (
            <div className="mb-2">
              <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
                <CategoryIconComponent icon={categoryInfo.icon} />
                <span>{categoryInfo.name}</span>
              </span>
            </div>
          )}
          <h2 className="line-clamp-2 text-xl font-bold text-gray-900 transition-colors hover:text-blue-600">
            {post.title}
          </h2>
        </div>

        <p className="line-clamp-3 text-sm leading-relaxed text-gray-600">{post.excerpt}</p>

        <div className="mt-4">
          <span className="text-sm font-medium text-blue-600 hover:text-blue-700">
            Read more →
          </span>
        </div>
      </Link>
    </article>
  )
}
