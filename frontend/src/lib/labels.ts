import type { ChangeType, EvidenceSource, EvidenceStatus, RiskLevel } from '@/types'

export const RISK_LEVELS: RiskLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'UNKNOWN']

export const changeTypeLabels: Record<ChangeType, string> = {
  REMOVE: 'Removal',
  MODIFY: 'Modification',
  REFACTOR: 'Refactor',
  DEPRECATE: 'Deprecation',
  API_CHANGE: 'API change',
}

export const evidenceSourceLabels: Record<EvidenceSource, string> = {
  STATIC: 'Static analysis',
  GIT: 'Git history',
  CONFIGURATION: 'Configuration',
  RUNTIME: 'Runtime evidence',
  EXTERNAL: 'External references',
}

export const evidenceStatusLabels: Record<EvidenceStatus, string> = {
  AVAILABLE: 'Available',
  UNAVAILABLE: 'Unavailable',
  UNKNOWN: 'Unknown',
}
