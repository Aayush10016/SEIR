export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'UNKNOWN'
export type ChangeType = 'REMOVE' | 'MODIFY' | 'REFACTOR' | 'DEPRECATE' | 'API_CHANGE'
export type EvidenceSource = 'STATIC' | 'GIT' | 'CONFIGURATION' | 'RUNTIME' | 'EXTERNAL'
export type EvidenceStatus = 'AVAILABLE' | 'UNAVAILABLE' | 'UNKNOWN'
export type ComponentType = 'CONTROLLER' | 'SERVICE' | 'JOB'
export type DependencyKind = 'CALLS' | 'IMPORTS' | 'INJECTS' | 'CONFIG_REFERENCE'

/** Which evidence sources were available for a repository analysis, and why not if missing. */
export interface EvidenceCoverage {
  source: EvidenceSource
  status: EvidenceStatus
  detail: string
}

export interface Repository {
  id: string
  name: string
  url: string
  branch: string
  lastAnalyzedAt: string // ISO 8601
  commitCount: number
  contributorCount: number
  evidenceCoverage: EvidenceCoverage[]
}

export interface Component {
  id: string
  name: string
  path: string
  type: ComponentType
  packageName: string
  /** Current baseline risk of the component, independent of any specific change. */
  riskLevel: RiskLevel
  dependencyCount: number // components this one depends on
  dependentCount: number // components that depend on this one
}

/** `sourceId` depends on `targetId`. */
export interface Dependency {
  id: string
  sourceId: string
  targetId: string
  kind: DependencyKind
}

export interface Evidence {
  id: string
  componentId: string
  source: EvidenceSource
  status: EvidenceStatus
  title: string
  summary: string
  severity?: Exclude<RiskLevel, 'UNKNOWN'>
  timestamp?: string // ISO 8601
}

export type RiskFactorKind =
  | 'DEPENDENCY_IMPACT'
  | 'GIT_ACTIVITY'
  | 'RUNTIME_USAGE'
  | 'CONFIGURATION'
  | 'EXTERNAL_REFERENCE'

export interface RiskFactor {
  id: string
  kind: RiskFactorKind
  level: RiskLevel
  summary: string
  evidenceIds: string[]
}

export interface Recommendation {
  summary: string
  reasoning: string
  uncertainty: string
  suggestedInvestigation: string[]
}

export interface RiskAssessment {
  id: string
  componentId: string
  changeType: ChangeType
  level: RiskLevel
  /** 0-1. Strength of the evidence supporting the assessment. NOT the probability that the change is safe. */
  confidence: number
  assessedAt: string // ISO 8601
  factors: RiskFactor[]
  recommendation: Recommendation
}

export type ImpactRelationship =
  | 'DIRECT_DEPENDENCY'
  | 'INDIRECT_DEPENDENCY'
  | 'CONFIGURATION_REFERENCE'
  | 'EXTERNAL_REFERENCE'

export interface AffectedComponent {
  componentId: string
  relationship: ImpactRelationship
  impactLevel: RiskLevel
  evidenceIds: string[]
}

export interface ImpactAnalysis {
  componentId: string
  changeType: ChangeType
  directlyAffected: number
  indirectlyAffected: number
  configurationReferences: number
  externalReferences: number
  affected: AffectedComponent[]
}

export type AnalysisStageStatus =
  | 'COMPLETED'
  | 'RUNNING'
  | 'PENDING'
  | 'UNAVAILABLE'
  | 'NOT_CONFIGURED'
  | 'FAILED'

export interface AnalysisStage {
  key: string
  label: string
  status: AnalysisStageStatus
  detail?: string
}

export interface AnalysisStatus {
  id: string
  repositoryId: string
  state: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  startedAt: string // ISO 8601
  completedAt?: string // ISO 8601
  stages: AnalysisStage[]
}
