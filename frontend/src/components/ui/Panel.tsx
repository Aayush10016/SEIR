import { useId, type ReactNode } from 'react'

interface PanelProps {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  /** Set to false for full-bleed content such as tables. */
  padded?: boolean
  className?: string
}

export function Panel({ title, description, actions, children, padded = true, className = '' }: PanelProps) {
  const headingId = useId()
  return (
    <section aria-labelledby={headingId} className={`rounded-md border border-slate-200 bg-white ${className}`}>
      <header className="flex items-start justify-between gap-4 border-b border-slate-200 px-4 py-3">
        <div>
          <h2 id={headingId} className="text-sm font-semibold text-slate-900">
            {title}
          </h2>
          {description && <p className="mt-0.5 max-w-prose text-xs text-slate-500">{description}</p>}
        </div>
        {actions}
      </header>
      <div className={padded ? 'p-4' : ''}>{children}</div>
    </section>
  )
}
