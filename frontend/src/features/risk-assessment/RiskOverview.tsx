import type { RiskDistribution } from '@/types'
import { Panel } from '@/components/ui/Panel'
import { RiskBadge } from '@/components/risk/RiskBadge'
import { riskStyles } from '@/components/risk/riskStyles'
import { RISK_LEVELS } from '@/lib/labels'

export function RiskOverview({ distribution }: { distribution: RiskDistribution }) {
  const total = RISK_LEVELS.reduce((sum, level) => sum + distribution[level], 0)
  const summary = RISK_LEVELS.map((level) => `${distribution[level]} ${level.toLowerCase()}`).join(', ')

  return (
    <Panel
      title="Risk overview"
      description="Baseline risk of each analyzed component. This is not the risk of a specific change."
    >
      <div role="img" aria-label={`Risk distribution across ${total} components: ${summary}`} className="flex h-3 gap-0.5 overflow-hidden rounded-sm bg-slate-100">
        {RISK_LEVELS.filter((level) => distribution[level] > 0).map((level) => (
          <div key={level} className={riskStyles[level].dot} style={{ width: `${(distribution[level] / total) * 100}%` }} />
        ))}
      </div>
      <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {RISK_LEVELS.map((level) => (
          <li key={level} className="flex flex-col items-start gap-1">
            <RiskBadge level={level} />
            <span className="text-lg font-semibold tabular-nums text-slate-900">{distribution[level]}</span>
          </li>
        ))}
      </ul>
    </Panel>
  )
}
