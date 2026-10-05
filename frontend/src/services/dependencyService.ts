import type { Dependency } from '@/types'
import { env } from '@/lib/env'
import { mockDependencies } from '@/mock/shopapp'
import { mockResponse } from '@/mock/mockResponse'
import { apiClient } from './apiClient'

export const dependencyService = {
  async listDependencies(repositoryId: string): Promise<Dependency[]> {
    if (env.useMock) return mockResponse(mockDependencies)
    const { data } = await apiClient.get<Dependency[]>(`/repositories/${repositoryId}/dependencies`)
    return data
  },
}
