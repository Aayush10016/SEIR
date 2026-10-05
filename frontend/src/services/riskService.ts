import type { RiskAssessmentSummary } from '@/types'
import { env } from '@/lib/env'
import { mockRecentAssessments } from '@/mock/shopapp'
import { mockResponse } from '@/mock/mockResponse'
import { apiClient } from './apiClient'

export const riskService = {
  async listRecentAssessments(repositoryId: string, limit: number): Promise<RiskAssessmentSummary[]> {
    if (env.useMock) return mockResponse(mockRecentAssessments.slice(0, limit))
    const { data } = await apiClient.get<RiskAssessmentSummary[]>(`/repositories/${repositoryId}/risk-assessments`, {
      params: { limit },
    })
    return data
  },
}
