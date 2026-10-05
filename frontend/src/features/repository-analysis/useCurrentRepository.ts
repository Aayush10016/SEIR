import { useQuery } from '@tanstack/react-query'
import { CURRENT_REPOSITORY_ID } from '@/lib/currentRepository'
import { repositoryService } from '@/services/repositoryService'

export function useCurrentRepository() {
  return useQuery({
    queryKey: ['repository', CURRENT_REPOSITORY_ID],
    queryFn: () => repositoryService.getRepository(CURRENT_REPOSITORY_ID),
  })
}
