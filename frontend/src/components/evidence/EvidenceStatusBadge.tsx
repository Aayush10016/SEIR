import { Check, CircleHelp, Minus } from 'lucide-react'
import type { EvidenceStatus } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { evidenceStatusLabels } from '@/lib/labels'

const styles: Record<EvidenceStatus, { className: string; Icon: typeof Check }> = {
  AVAILABLE: { className: 'border-accent-border bg-accent-soft text-accent', Icon: Check },
  UNAVAILABLE: { className: 'border-dashed border-slate-400 bg-white text-slate-700', Icon: Minus },
  UNKNOWN: { className: 'border-risk-unknown-border bg-risk-unknown-bg text-risk-unknown-fg', Icon: CircleHelp },
}

export function EvidenceStatusBadge({ status }: { status: EvidenceStatus }) {
  const { className, Icon } = styles[status]
  return (
    <Badge className={className}>
      <Icon aria-hidden="true" size={12} />
      {evidenceStatusLabels[status]}
    </Badge>
  )
}
