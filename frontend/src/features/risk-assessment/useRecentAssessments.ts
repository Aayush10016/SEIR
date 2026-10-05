import { useQuery } from '@tanstack/react-query'
import { riskService } from '@/services/riskService'

export function useRecentAssessments(repositoryId: string, limit = 5) {
  return useQuery({
    queryKey: ['risk-assessments', repositoryId, 'recent', limit],
    queryFn: () => riskService.listRecentAssessments(repositoryId, limit),
  })
}
