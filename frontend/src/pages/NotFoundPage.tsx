import { ButtonLink } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'

export function NotFoundPage() {
  return (
    <EmptyState
      title="Page not found"
      description="The address doesn't match any SEIR page."
      action={<ButtonLink to="/dashboard">Go to dashboard</ButtonLink>}
    />
  )
}
