import type { ReactNode } from 'react'

interface MetaItem {
  label: string
  value: ReactNode
}

interface PageHeaderProps {
  title: string
  description?: string
  meta?: MetaItem[]
  actions?: ReactNode
}

export function PageHeader({ title, description, meta, actions }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
        {description && <p className="mt-1 max-w-prose text-slate-600">{description}</p>}
        {meta && (
          <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1">
            {meta.map((item) => (
              <div key={item.label} className="flex gap-1.5">
                <dt className="text-slate-500">{item.label}</dt>
                <dd className="font-medium text-slate-900">{item.value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
      {actions}
    </div>
  )
}
