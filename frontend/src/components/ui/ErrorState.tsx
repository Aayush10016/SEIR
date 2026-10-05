import { Button } from './Button'

interface ErrorStateProps {
  title: string
  message?: string
  onRetry?: () => void
}

export function ErrorState({ title, message, onRetry }: ErrorStateProps) {
  return (
    <div role="alert" className="rounded-md border border-risk-high-border bg-risk-high-bg px-6 py-8 text-center">
      <p className="font-medium text-risk-high-fg">{title}</p>
      {message && <p className="mx-auto mt-1 max-w-md text-slate-700">{message}</p>}
      {onRetry && (
        <div className="mt-4 flex justify-center">
          <Button onClick={onRetry}>Retry</Button>
        </div>
      )}
    </div>
  )
}
