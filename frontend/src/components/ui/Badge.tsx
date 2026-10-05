import type { ReactNode } from 'react'

interface BadgeProps {
  className: string
  /** Optional colored dot; the text label always carries the meaning, never the color alone. */
  dotClassName?: string
  children: ReactNode
}

export function Badge({ className, dotClassName, children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 text-xs font-medium ${className}`}>
      {dotClassName && <span aria-hidden="true" className={`h-2 w-2 rounded-full ${dotClassName}`} />}
      {children}
    </span>
  )
}
