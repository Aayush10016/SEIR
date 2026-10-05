import { ErrorState } from '@/components/ui/ErrorState'
import { ButtonLink } from '@/components/ui/Button'
import { PageHeader } from '@/components/ui/PageHeader'
import { DashboardSkeleton } from '@/features/repository-analysis/DashboardSkeleton'
import { RepositoryHealth } from '@/features/repository-analysis/RepositoryHealth'
import { useDashboardData } from '@/features/repository-analysis/useDashboardData'
import { EvidenceCoverage } from '@/features/evidence/EvidenceCoverage'
import { RecentAssessments } from '@/features/risk-assessment/RecentAssessments'
import { RiskOverview } from '@/features/risk-assessment/RiskOverview'
import { formatRelativeTime } from '@/lib/format'

export function DashboardPage() {
  const { data, isPending, error, refetch } = useDashboardData()

  if (isPending) return <DashboardSkeleton />
  if (error || !data) {
    return (
      <ErrorState
        title="Unable to load the dashboard."
        message={error instanceof Error ? error.message : undefined}
        onRetry={refetch}
      />
    )
  }

  const { repository } = data
  return (
    <>
      <PageHeader
        title="Dashboard"
        meta={[
          { label: 'Repository', value: repository.name },
          { label: 'Branch', value: <span className="font-mono">{repository.branch}</span> },
          { label: 'Last analysis', value: formatRelativeTime(repository.lastAnalyzedAt) },
        ]}
        actions={<ButtonLink to="/repository" variant="primary">Run analysis</ButtonLink>}
      />
      <div className="space-y-6">
        <RepositoryHealth health={data.health} />
        <div className="grid gap-6 lg:grid-cols-2">
          <RiskOverview distribution={data.riskDistribution} />
          <EvidenceCoverage coverage={repository.evidenceCoverage} />
        </div>
        <RecentAssessments rows={data.recentAssessments} />
      </div>
    </>
  )
}
