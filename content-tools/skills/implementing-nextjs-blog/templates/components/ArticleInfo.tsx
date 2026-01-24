/**
 * Article Info Component
 *
 * Displays article metadata: publication date and category.
 *
 * Props:
 *   date: string - Publication date in YYYY-MM-DD format
 *   category: string - Category slug
 *   categoryDisplay: string - Category display name
 *
 * Usage:
 *   <ArticleInfo date="2024-01-15" category="javascript" categoryDisplay="JavaScript" />
 */

import { getCategoryInfo } from '@/lib/blog/categories'
import { CategoryIconComponent } from './CategoryIcon'

interface ArticleInfoProps {
  date: string
  category: string
  categoryDisplay: string
}

/**
 * Format date string to display format
 * Customize this function for your locale
 */
function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString)
    // Default: "January 15, 2024" format
    // For Japanese: `${year}年${month}月${day}日`
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return dateString
  }
}

export function ArticleInfo({ date, category, categoryDisplay }: ArticleInfoProps) {
  const categoryInfo = getCategoryInfo(category, 'sm')

  return (
    <div className="mb-6 flex flex-wrap items-center gap-3 text-sm text-gray-600">
      {/* Date with calendar icon */}
      <div className="flex items-center gap-1">
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        <time dateTime={date}>{formatDate(date)}</time>
      </div>

      <span className="text-gray-400">•</span>

      {/* Category with icon */}
      <div className="flex items-center gap-1">
        <CategoryIconComponent icon={categoryInfo.icon} />
        <span>{categoryDisplay}</span>
      </div>
    </div>
  )
}
