/**
 * Category Icon Component
 *
 * Renders either a Devicon or emoji based on icon type.
 *
 * For Devicon support, you need ONE of:
 * 1. CDN: <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/devicon.min.css">
 * 2. npm package: npm install devicon
 * 3. Custom Devicon component (shown below)
 *
 * Props:
 *   icon: CategoryIcon - Icon configuration from getCategoryIcon()
 *   className?: string - Additional CSS classes
 *
 * Usage:
 *   <CategoryIconComponent icon={categoryInfo.icon} />
 */

import type { CategoryIcon } from '@/lib/blog/categories'

interface CategoryIconProps {
  icon: CategoryIcon
  className?: string
}

/**
 * Simple Devicon Component
 * Replace this with your own implementation if needed
 */
function Devicon({
  slug,
  size,
  className = '',
}: {
  slug: string
  size: 'sm' | 'md' | 'lg'
  className?: string
}) {
  const sizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-xl',
  }

  return (
    <i
      className={`devicon-${slug}-plain colored ${sizeClasses[size]} ${className}`}
      aria-label={`${slug} icon`}
    />
  )
}

/**
 * Category Icon Component
 * Renders Devicon or emoji based on icon type
 */
export function CategoryIconComponent({ icon, className = '' }: CategoryIconProps) {
  if (icon.type === 'devicon') {
    return <Devicon slug={icon.value} size={icon.size} className={className} />
  }

  // Emoji icon
  return (
    <span className={`inline-block ${className}`} role="img" aria-label={`${icon.value} icon`}>
      {icon.value}
    </span>
  )
}
