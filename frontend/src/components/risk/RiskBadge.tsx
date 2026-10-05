import type { RiskLevel } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { riskStyles } from './riskStyles'

export function RiskBadge({ level }: { level: RiskLevel }) {
  const style = riskStyles[level]
  return (
    <Badge className={style.badge} dotClassName={style.dot}>
      {level}
    </Badge>
  )
}
