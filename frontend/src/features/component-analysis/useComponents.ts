import { useQuery } from '@tanstack/react-query'
import { componentService } from '@/services/componentService'
import { dependencyService } from '@/services/dependencyService'

export function useComponents(repositoryId: string) {
  return useQuery({
    queryKey: ['components', repositoryId],
    queryFn: () => componentService.listComponents(repositoryId),
  })
}

export function useDependencies(repositoryId: string) {
  return useQuery({
    queryKey: ['dependencies', repositoryId],
    queryFn: () => dependencyService.listDependencies(repositoryId),
  })
}
