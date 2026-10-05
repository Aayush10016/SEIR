import type {
  Component, DashboardModel, Dependency, Repository, RiskAssessmentSummary, RiskDistribution,
} from '@/types'

interface DashboardInput {
  repository: Repository
  components: Component[]
  dependencies: Dependency[]
  assessments: RiskAssessmentSummary[]
}

/** Derives every dashboard figure from the same component/dependency lists the other pages use. */
export function buildDashboardModel({ repository, components, dependencies, assessments }: DashboardInput): DashboardModel {
  const riskDistribution: RiskDistribution = { LOW: 0, MEDIUM: 0, HIGH: 0, UNKNOWN: 0 }
  for (const component of components) riskDistribution[component.riskLevel] += 1

  const configReferenceCount = dependencies.filter((d) => d.kind === 'CONFIG_REFERENCE').length
  const namesById = new Map(components.map((c) => [c.id, c.name]))

  return {
    repository,
    riskDistribution,
    health: {
      componentCount: components.length,
      dependencyCount: dependencies.length - configReferenceCount,
      configReferenceCount,
      commitCount: repository.commitCount,
      contributorCount: repository.contributorCount,
      highRiskCount: riskDistribution.HIGH,
    },
    recentAssessments: assessments.map((a) => ({ ...a, componentName: namesById.get(a.componentId) ?? a.componentId })),
  }
}
