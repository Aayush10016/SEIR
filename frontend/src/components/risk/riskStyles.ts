import type { RiskLevel } from '@/types'

export const riskStyles: Record<RiskLevel, { badge: string; dot: string }> = {
  LOW: { badge: 'border-risk-low-border bg-risk-low-bg text-risk-low-fg', dot: 'bg-risk-low-dot' },
  MEDIUM: { badge: 'border-risk-medium-border bg-risk-medium-bg text-risk-medium-fg', dot: 'bg-risk-medium-dot' },
  HIGH: { badge: 'border-risk-high-border bg-risk-high-bg text-risk-high-fg', dot: 'bg-risk-high-dot' },
  UNKNOWN: { badge: 'border-risk-unknown-border bg-risk-unknown-bg text-risk-unknown-fg', dot: 'bg-risk-unknown-dot' },
}
