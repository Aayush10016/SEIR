import { Link } from 'react-router-dom'
import type { RecentAssessmentRow } from '@/types'
import { Panel } from '@/components/ui/Panel'
import { Table, Td, Th } from '@/components/ui/Table'
import { EmptyState } from '@/components/ui/EmptyState'
import { ButtonLink } from '@/components/ui/Button'
import { RiskBadge } from '@/components/risk/RiskBadge'
import { changeTypeLabels } from '@/lib/labels'
import { formatPercent, formatRelativeTime } from '@/lib/format'

export function RecentAssessments({ rows }: { rows: RecentAssessmentRow[] }) {
  return (
    <Panel
      title="Recent risk assessments"
      description="Evidence support is how strongly the available evidence backs an assessment. It is not the probability that a change is safe."
      padded={false}
    >
      {rows.length === 0 ? (
        <div className="p-4">
          <EmptyState
            title="No risk assessments yet"
            description="Analyze a repository to generate component risk assessments."
            action={<ButtonLink to="/repository" variant="primary">Go to Repositories</ButtonLink>}
          />
        </div>
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Component</Th>
              <Th>Change</Th>
              <Th>Risk</Th>
              <Th>Evidence support</Th>
              <Th>Updated</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <Td>
                  <Link to={`/components/${row.componentId}`} className="font-mono text-accent hover:underline">
                    {row.componentName}
                  </Link>
                </Td>
                <Td>{changeTypeLabels[row.changeType]}</Td>
                <Td>
                  <RiskBadge level={row.level} />
                </Td>
                <Td className="tabular-nums">{formatPercent(row.confidence)}</Td>
                <Td className="whitespace-nowrap text-slate-600">{formatRelativeTime(row.assessedAt)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Panel>
  )
}
