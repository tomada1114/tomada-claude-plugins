/**
 * Blog Layout
 *
 * Layout wrapper for all blog pages.
 * Imports CSS files for blog styling and syntax highlighting.
 *
 * File location: src/app/blog/layout.tsx
 *
 * Required CSS files:
 * - blog.css: Article typography and layout styles
 * - prism-tomorrow.css: Code block dark theme
 * - prism-line-numbers.css: Line number styling
 *
 * To use a different Prism theme, replace prism-tomorrow.css with:
 * - prism.css (default light theme)
 * - prism-okaidia.css
 * - prism-solarizedlight.css
 * - prism-twilight.css
 * etc.
 */

import './blog.css'
import 'prismjs/themes/prism-tomorrow.css'
import 'prismjs/plugins/line-numbers/prism-line-numbers.css'

export default function BlogLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
