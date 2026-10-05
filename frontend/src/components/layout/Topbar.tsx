import { GitBranch } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Skeleton } from '@/components/ui/Skeleton'
import { useCurrentRepository } from '@/features/repository-analysis/useCurrentRepository'

export function Topbar() {
  const { data, isPending } = useCurrentRepository()

  return (
    <header className="flex h-12 shrink-0 items-center gap-4 border-b border-slate-200 bg-white px-4">
      <Link to="/dashboard" className="flex items-baseline gap-3">
        <span className="font-semibold tracking-tight text-slate-900">SEIR</span>
        <span className="hidden text-xs text-slate-500 xl:inline">
          Understanding the consequences of change before changing the system.
        </span>
      </Link>

      <div className="ml-auto">
        {isPending && <Skeleton className="h-5 w-40" />}
        {data && (
          <Link
            to="/repository"
            className="flex items-center gap-2 rounded border border-slate-200 px-2.5 py-1 hover:bg-slate-50"
            aria-label={`Repository ${data.name}, branch ${data.branch}`}
          >
            <span className="font-medium text-slate-900">{data.name}</span>
            <GitBranch aria-hidden="true" size={13} className="text-slate-400" />
            <span className="font-mono text-xs text-slate-600">{data.branch}</span>
          </Link>
        )}
        {!isPending && !data && <span className="text-xs text-slate-500">Repository unavailable</span>}
      </div>
    </header>
  )
}
