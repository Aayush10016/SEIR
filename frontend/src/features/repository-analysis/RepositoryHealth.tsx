import type { RepositoryHealthMetrics } from '@/types'
import { Panel } from '@/components/ui/Panel'
import { formatNumber } from '@/lib/format'

export function RepositoryHealth({ health }: { health: RepositoryHealthMetrics }) {
  const cells = [
    { label: 'Components', value: formatNumber(health.componentCount) },
    { label: 'Dependencies', value: formatNumber(health.dependencyCount) },
    { label: 'Configuration references', value: formatNumber(health.configReferenceCount) },
    { label: 'Git commits', value: formatNumber(health.commitCount) },
    { label: 'Contributors', value: formatNumber(health.contributorCount) },
    { label: 'High-risk components', value: formatNumber(health.highRiskCount) },
  ]
  return (
    <Panel title="Repository health" padded={false}>
      <dl className="grid grid-cols-2 gap-px bg-slate-200 md:grid-cols-3 xl:grid-cols-6">
        {cells.map((cell) => (
          <div key={cell.label} className="bg-white px-4 py-3">
            <dt className="text-xs text-slate-500">{cell.label}</dt>
            <dd className="mt-1 text-xl font-semibold tabular-nums text-slate-900">{cell.value}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  )
}
