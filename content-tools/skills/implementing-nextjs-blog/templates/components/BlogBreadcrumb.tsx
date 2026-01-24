/**
 * Blog Breadcrumb Component
 *
 * Breadcrumb navigation with structured data for SEO.
 * Uses schema.org BreadcrumbList for rich search results.
 *
 * Props:
 *   items: BreadcrumbItem[] - Breadcrumb trail
 *   className?: string - Additional CSS classes
 *
 * Usage:
 *   const items = [
 *     { label: 'Home', href: '/' },
 *     { label: 'Blog', href: '/blog' },
 *     { label: 'JavaScript', href: '/blog/javascript' },
 *   ]
 *   <BlogBreadcrumb items={items} />
 */

import Link from 'next/link'
import Script from 'next/script'

export interface BreadcrumbItem {
  label: string
  href?: string
}

interface BlogBreadcrumbProps {
  items: BreadcrumbItem[]
  className?: string
}

export function BlogBreadcrumb({ items, className = '' }: BlogBreadcrumbProps) {
  // Generate structured data for SEO
  // Note: This is safe as data comes from controlled server-side sources, not user input
  const structuredData = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.label,
      item: item.href ? `${process.env.NEXT_PUBLIC_SITE_URL || ''}${item.href}` : undefined,
    })),
  }

  return (
    <>
      {/* Structured Data for SEO */}
      <Script
        id="breadcrumb-structured-data"
        type="application/ld+json"
        strategy="afterInteractive"
      >
        {JSON.stringify(structuredData)}
      </Script>

      {/* Visual Breadcrumb */}
      <nav aria-label="Breadcrumb" className={className}>
        <ol className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
          {items.map((item, index) => (
            <li key={index} className="flex items-center gap-2">
              {index > 0 && (
                <span className="text-gray-400" aria-hidden="true">
                  /
                </span>
              )}
              {item.href ? (
                <Link href={item.href} className="hover:text-gray-900 hover:underline">
                  {item.label}
                </Link>
              ) : (
                <span className="text-gray-900">{item.label}</span>
              )}
            </li>
          ))}
        </ol>
      </nav>
    </>
  )
}

/**
 * Helper function to generate blog breadcrumbs
 *
 * @param categoryName - Display name of category (optional)
 * @param categorySlug - Category slug (optional)
 * @param postTitle - Post title (optional)
 * @returns Array of breadcrumb items
 */
export function generateBlogBreadcrumb(
  categoryName?: string,
  categorySlug?: string,
  postTitle?: string
): BreadcrumbItem[] {
  const items: BreadcrumbItem[] = [
    { label: 'Home', href: '/' },
    { label: 'Blog', href: '/blog' },
  ]

  if (categoryName && categorySlug) {
    items.push({
      label: categoryName,
      href: postTitle ? `/blog/${categorySlug}` : undefined,
    })
  }

  if (postTitle) {
    items.push({ label: postTitle })
  }

  return items
}
