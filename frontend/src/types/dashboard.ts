import type { ChangeType, Repository, RiskAssessment, RiskLevel } from './domain'

export type RiskDistribution = Record<RiskLevel, number>

export interface RepositoryHealthMetrics {
  componentCount: number
  dependencyCount: number
  configReferenceCount: number
  commitCount: number
  contributorCount: number
  highRiskCount: number
}

/** The subset of RiskAssessment shown in lists; the full object (factors, recommendation) loads on demand. */
export type RiskAssessmentSummary = Pick<
  RiskAssessment,
  'id' | 'componentId' | 'changeType' | 'level' | 'confidence' | 'assessedAt'
>

export interface RecentAssessmentRow extends RiskAssessmentSummary {
  componentName: string
  changeType: ChangeType
}

export interface DashboardModel {
  repository: Repository
  health: RepositoryHealthMetrics
  riskDistribution: RiskDistribution
  recentAssessments: RecentAssessmentRow[]
}
