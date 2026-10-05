import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
      <p className="font-medium text-slate-900">{title}</p>
      {description && <p className="mx-auto mt-1 max-w-md text-slate-600">{description}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  )
}
