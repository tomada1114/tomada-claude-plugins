/**
 * Blog Header Component
 *
 * Sticky header for blog pages with navigation.
 * Customize the navigation links and logo for your project.
 *
 * Usage:
 *   <BlogHeader />
 *
 * Note: This is a minimal template. Replace Logo component and
 * navigation links with your own.
 */

import Link from 'next/link'

export function BlogHeader() {
  return (
    <header className="sticky top-0 z-40 flex flex-none flex-wrap items-center justify-between bg-white px-4 py-5 shadow-md shadow-slate-900/5 transition duration-500 sm:px-6 lg:px-8">
      {/* Mobile menu button */}
      <div className="mr-6 flex lg:hidden">
        <button
          type="button"
          className="relative flex h-10 w-10 items-center justify-center rounded-lg"
          aria-label="Toggle navigation"
        >
          <svg
            aria-hidden="true"
            className="h-3.5 w-3.5 overflow-visible stroke-slate-700"
            fill="none"
            strokeWidth={2}
            strokeLinecap="round"
          >
            <path d="M0 1H14M0 7H14M0 13H14" />
          </svg>
        </button>
      </div>

      {/* Logo */}
      <div className="relative flex grow basis-0 items-center">
        <Link href="/" aria-label="Home page" className="text-xl font-bold text-slate-900">
          {/* Replace with your logo component */}
          Your Logo
        </Link>
      </div>

      {/* Desktop Navigation */}
      <div className="hidden md:flex md:items-center md:gap-6">
        <Link href="/blog" className="text-sm font-medium text-slate-700 hover:text-slate-900">
          Blog
        </Link>
        {/* Add more navigation links as needed */}
      </div>

      {/* Right side actions */}
      <div className="relative flex basis-0 justify-end gap-6 sm:gap-8 md:grow">
        <div className="hidden md:flex md:items-center">
          {/* Add auth links, search, etc. */}
        </div>
      </div>
    </header>
  )
}
