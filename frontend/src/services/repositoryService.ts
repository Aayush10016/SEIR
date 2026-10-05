import type { Repository } from '@/types'
import { env } from '@/lib/env'
import { mockRepository } from '@/mock/shopapp'
import { mockResponse } from '@/mock/mockResponse'
import { apiClient } from './apiClient'

export const repositoryService = {
  async getRepository(repositoryId: string): Promise<Repository> {
    if (env.useMock) {
      if (repositoryId !== mockRepository.id) throw new Error(`Repository "${repositoryId}" was not found.`)
      return mockResponse(mockRepository)
    }
    const { data } = await apiClient.get<Repository>(`/repositories/${repositoryId}`)
    return data
  },
}
