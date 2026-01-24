/**
 * Table of Contents Component
 *
 * Client-side component that:
 * - Extracts H2 headings from article content
 * - Tracks scroll position with IntersectionObserver
 * - Highlights active section
 * - Supports Japanese characters and special symbols
 *
 * Usage:
 *   <TableOfContents />
 *
 * Requirements:
 *   - Article content must have class "blog-article"
 *   - H2 headings will be extracted for TOC
 */

'use client'

import { useEffect, useState } from 'react'

interface TocItem {
  id: string
  text: string
  level: number
}

/**
 * Generate a safe ID from heading text
 * Handles Japanese characters and special symbols
 */
function generateSafeId(text: string, index: number): string {
  // If already a valid ID, use it
  if (text.match(/^[a-zA-Z0-9-_]+$/)) {
    return text
  }

  // Convert text to a URL-safe ID
  const baseId = text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '') // Remove non-alphanumeric except space and hyphen
    .replace(/\s+/g, '-') // Replace spaces with hyphens
    .replace(/-+/g, '-') // Collapse multiple hyphens
    .replace(/^-+|-+$/g, '') // Trim leading/trailing hyphens

  // If baseId is empty (all Japanese/symbols), use index-based ID
  return baseId || `heading-${index}`
}

export function TableOfContents() {
  const [toc, setToc] = useState<TocItem[]>([])
  const [activeId, setActiveId] = useState<string>('')

  // Extract headings on mount
  useEffect(() => {
    // Customize selector here: '.blog-article h2' for H2 only
    // Use '.blog-article h2, .blog-article h3' for H2 and H3
    const headings = document.querySelectorAll('.blog-article h2')
    const items: TocItem[] = []
    const idMap = new Map<string, number>()

    headings.forEach((heading, index) => {
      let id = heading.id

      if (!id) {
        // Generate ID if not set by rehype-slug
        const baseId = generateSafeId(heading.textContent || '', index)

        // Handle duplicates
        const count = idMap.get(baseId) || 0
        id = count > 0 ? `${baseId}-${count}` : baseId
        idMap.set(baseId, count + 1)

        heading.id = id
      }

      items.push({
        id,
        text: heading.textContent || '',
        level: parseInt(heading.tagName[1]),
      })
    })

    setToc(items)
  }, [])

  // Set up scroll tracking
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id)
          }
        })
      },
      {
        // Customize margins for activation timing
        // -80px: Offset for sticky header
        // -80%: Activate when heading is in top 20% of viewport
        rootMargin: '-80px 0px -80% 0px',
      }
    )

    const headings = document.querySelectorAll('.blog-article h2')
    headings.forEach(heading => observer.observe(heading))

    return () => {
      headings.forEach(heading => observer.unobserve(heading))
    }
  }, [toc])

  if (toc.length === 0) return null

  return (
    <div className="sticky top-20 w-full">
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 flex items-center gap-2 text-lg font-bold">
          <span className="text-xl">📑</span>
          Table of Contents
        </h3>
        <ul className="space-y-2">
          {toc.map(item => (
            <li key={item.id} style={{ paddingLeft: `${(item.level - 2) * 16}px` }}>
              <a
                href={`#${item.id}`}
                className={`block py-1 text-sm transition-colors ${
                  activeId === item.id
                    ? 'font-medium text-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                } `}
                onClick={e => {
                  e.preventDefault()
                  const element = document.getElementById(item.id)
                  if (element) {
                    // Offset for sticky header height
                    const yOffset = -80
                    const y = element.getBoundingClientRect().top + window.scrollY + yOffset
                    window.scrollTo({ top: y, behavior: 'smooth' })
                  }
                }}
              >
                {item.text}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
