/**
 * Category Configuration
 *
 * Manages category display names and icons.
 * Supports two icon types:
 * - Devicon: For programming languages (requires devicon CSS)
 * - Emoji: For non-programming categories
 *
 * Customize the category mappings below to match your project.
 */

/**
 * Icon size options
 */
export type IconSize = 'sm' | 'md' | 'lg'

/**
 * Category icon configuration
 */
export type CategoryIcon = {
  type: 'devicon' | 'emoji'
  value: string
  size: IconSize
}

/**
 * Category display information
 */
export interface CategoryInfo {
  name: string
  icon: CategoryIcon
}

/**
 * Programming language categories with devicon support
 * Key: folder name, Value: display name
 *
 * For devicon to work, you need:
 * 1. Install devicon: Add <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/devicon.min.css">
 * 2. Or use a Devicon component that renders: <i className={`devicon-${slug}-plain`} />
 */
const PROGRAMMING_CATEGORIES: Record<string, string> = {
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  react: 'React',
  vue: 'Vue.js',
  angular: 'Angular',
  svelte: 'Svelte',
  nextjs: 'Next.js',
  python: 'Python',
  java: 'Java',
  ruby: 'Ruby',
  rails: 'Ruby on Rails',
  php: 'PHP',
  csharp: 'C#',
  html: 'HTML',
  css: 'CSS',
  nodejs: 'Node.js',
  git: 'Git',
  docker: 'Docker',
}

/**
 * Devicon slug mapping
 * Some categories need different slugs for devicon
 */
const DEVICON_MAPPING: Record<string, string> = {
  javascript: 'javascript',
  typescript: 'typescript',
  react: 'react',
  vue: 'vuejs',
  angular: 'angularjs',
  svelte: 'svelte',
  nextjs: 'nextjs',
  python: 'python',
  java: 'java',
  ruby: 'ruby',
  rails: 'rails',
  php: 'php',
  csharp: 'csharp',
  html: 'html5',
  css: 'css3',
  nodejs: 'nodejs',
  git: 'git',
  docker: 'docker',
}

/**
 * Non-programming categories with emoji icons
 * Key: folder name, Value: { name: display name, emoji: icon }
 */
const NON_PROGRAMMING_CATEGORIES: Record<string, { name: string; emoji: string }> = {
  programming: { name: 'Programming', emoji: '💻' },
  tutorial: { name: 'Tutorial', emoji: '📚' },
  news: { name: 'News', emoji: '📰' },
  tips: { name: 'Tips', emoji: '💡' },
  career: { name: 'Career', emoji: '👔' },
  design: { name: 'Design', emoji: '🎨' },
  tools: { name: 'Tools', emoji: '🔧' },
  webdev: { name: 'Web Dev', emoji: '🌐' },
  database: { name: 'Database', emoji: '🗄️' },
  security: { name: 'Security', emoji: '🔒' },
  general: { name: 'General', emoji: '💻' },
}

/**
 * Check if a category uses devicon for its icon
 *
 * @param category - Category folder name
 * @returns true if category has devicon support
 */
export function isDeviconCategory(category: string): boolean {
  return category in PROGRAMMING_CATEGORIES && category in DEVICON_MAPPING
}

/**
 * Get the devicon slug for a category
 *
 * @param category - Category folder name
 * @returns Devicon slug or undefined
 */
export function getDeviconSlug(category: string): string | undefined {
  return DEVICON_MAPPING[category]
}

/**
 * Get icon configuration for a category
 *
 * @param category - Category folder name
 * @param size - Icon size (sm, md, lg)
 * @returns Icon configuration
 */
export function getCategoryIcon(category: string, size: IconSize = 'sm'): CategoryIcon {
  if (isDeviconCategory(category)) {
    return {
      type: 'devicon',
      value: DEVICON_MAPPING[category],
      size,
    }
  }

  const categoryInfo = NON_PROGRAMMING_CATEGORIES[category]
  return {
    type: 'emoji',
    value: categoryInfo?.emoji || '📌',
    size,
  }
}

/**
 * Get display information for a category
 *
 * @param category - Category folder name
 * @param iconSize - Icon size (sm, md, lg)
 * @returns Category display info (name and icon)
 */
export function getCategoryInfo(category: string, iconSize: IconSize = 'sm'): CategoryInfo {
  const icon = getCategoryIcon(category, iconSize)

  let name: string
  if (isDeviconCategory(category)) {
    name = PROGRAMMING_CATEGORIES[category] || category
  } else {
    const categoryInfo = NON_PROGRAMMING_CATEGORIES[category]
    name = categoryInfo?.name || category
  }

  return {
    name,
    icon,
  }
}
