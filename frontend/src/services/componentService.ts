import type { Component } from '@/types'
import { env } from '@/lib/env'
import { mockComponents } from '@/mock/shopapp'
import { mockResponse } from '@/mock/mockResponse'
import { apiClient } from './apiClient'

export const componentService = {
  async listComponents(repositoryId: string): Promise<Component[]> {
    if (env.useMock) return mockResponse(mockComponents)
    const { data } = await apiClient.get<Component[]>(`/repositories/${repositoryId}/components`)
    return data
  },
}
