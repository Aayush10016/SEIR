import type { EvidenceCoverage as Coverage } from '@/types'
import { Panel } from '@/components/ui/Panel'
import { EvidenceStatusBadge } from '@/components/evidence/EvidenceStatusBadge'
import { evidenceSourceLabels } from '@/lib/labels'

export function EvidenceCoverage({ coverage }: { coverage: Coverage[] }) {
  const hasGaps = coverage.some((item) => item.status !== 'AVAILABLE')
  return (
    <Panel title="Evidence coverage" description="Which evidence sources contributed to the latest analysis.">
      <ul className="divide-y divide-slate-100">
        {coverage.map((item) => (
          <li key={item.source} className="flex items-start justify-between gap-4 py-2 first:pt-0 last:pb-0">
            <div>
              <p className="font-medium text-slate-900">{evidenceSourceLabels[item.source]}</p>
              <p className="text-xs text-slate-500">{item.detail}</p>
            </div>
            <EvidenceStatusBadge status={item.status} />
          </li>
        ))}
      </ul>
      {hasGaps && (
        <p className="mt-3 border-t border-slate-100 pt-3 text-xs text-slate-600">
          Missing evidence is reported as unknown. It is never treated as proof of low risk.
        </p>
      )}
    </Panel>
  )
}
