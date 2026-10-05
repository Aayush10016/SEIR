import { ButtonLink } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'

interface PlaceholderPageProps {
  title: string
  description: string
  phase: number
}

/** Honest stand-in for routes whose screens belong to a later build phase. */
export function PlaceholderPage({ title, description, phase }: PlaceholderPageProps) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <EmptyState
        title="Not implemented yet"
        description={`This screen is planned for phase ${phase} of the frontend build.`}
        action={<ButtonLink to="/dashboard">Back to dashboard</ButtonLink>}
      />
    </>
  )
}
