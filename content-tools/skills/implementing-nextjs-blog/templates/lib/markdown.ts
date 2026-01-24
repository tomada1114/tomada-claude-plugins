/**
 * Markdown to HTML Processor
 *
 * Converts markdown content to HTML with:
 * - GitHub Flavored Markdown (tables, strikethrough, etc.)
 * - Auto-generated heading IDs for TOC
 * - Syntax highlighting with line numbers (Prism)
 * - Image optimization (lazy loading)
 *
 * Dependencies:
 *   npm install remark remark-gfm remark-html rehype rehype-slug rehype-prism-plus
 */

import { remark } from 'remark'
import html from 'remark-html'
import gfm from 'remark-gfm'
import { rehype } from 'rehype'
import rehypePrismPlus from 'rehype-prism-plus'
import rehypeSlug from 'rehype-slug'

/**
 * Convert markdown string to HTML with syntax highlighting and heading IDs
 *
 * @param markdown - Raw markdown content
 * @returns Processed HTML string
 */
export async function markdownToHtml(markdown: string): Promise<string> {
  // Step 1: Convert markdown to HTML with GFM support
  const result = await remark().use(gfm).use(html).process(markdown)

  let htmlContent = result.toString()

  // Step 2: Apply syntax highlighting and generate heading IDs
  const highlightedResult = await rehype()
    .use(rehypeSlug) // Auto-generate IDs for headings (h1-h6)
    .use(rehypePrismPlus, {
      defaultLanguage: 'plaintext', // Default language for code blocks without specification
      showLineNumbers: true, // Show line numbers in code blocks
    })
    .process(htmlContent)

  htmlContent = highlightedResult.toString()

  // Step 3: Optimize images with lazy loading
  // Matches: <img src="/images/blog/..." alt="...">
  htmlContent = htmlContent.replace(
    /<img\s+src="([^"]+)"\s+alt="([^"]*)"\s*\/?>/g,
    (match, src, alt) => {
      return `<img src="${src}" alt="${alt}" loading="lazy" decoding="async" style="max-width: 100%; height: auto; display: block; margin: 2rem auto; border-radius: 0.5rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">`
    }
  )

  return htmlContent
}
