import { useMemo } from 'react'
import { CURRENT_REPOSITORY_ID } from '@/lib/currentRepository'
import { buildDashboardModel } from '@/lib/dashboard'
import { useComponents, useDependencies } from '@/features/component-analysis/useComponents'
import { useRecentAssessments } from '@/features/risk-assessment/useRecentAssessments'
import { useCurrentRepository } from './useCurrentRepository'

export function useDashboardData() {
  const repository = useCurrentRepository()
  const components = useComponents(CURRENT_REPOSITORY_ID)
  const dependencies = useDependencies(CURRENT_REPOSITORY_ID)
  const assessments = useRecentAssessments(CURRENT_REPOSITORY_ID)

  const queries = [repository, components, dependencies, assessments]
  const failed = queries.find((q) => q.isError)
  const error = failed ? failed.error : null
  const isPending = !failed && queries.some((q) => q.isPending)

  const data = useMemo(
    () =>
      repository.data && components.data && dependencies.data && assessments.data
        ? buildDashboardModel({
            repository: repository.data,
            components: components.data,
            dependencies: dependencies.data,
            assessments: assessments.data,
          })
        : undefined,
    [repository.data, components.data, dependencies.data, assessments.data],
  )

  const refetch = () => {
    if (repository.isError) void repository.refetch()
    if (components.isError) void components.refetch()
    if (dependencies.isError) void dependencies.refetch()
    if (assessments.isError) void assessments.refetch()
  }

  return { data, isPending, error, refetch }
}
