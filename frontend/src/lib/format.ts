const relativeTime = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

export function formatRelativeTime(iso: string, now: number = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 60) return 'just now'
  if (abs < 3600) return relativeTime.format(Math.round(seconds / 60), 'minute')
  if (abs < 86400) return relativeTime.format(Math.round(seconds / 3600), 'hour')
  return relativeTime.format(Math.round(seconds / 86400), 'day')
}

export const formatPercent = (ratio: number) => `${Math.round(ratio * 100)}%`
export const formatNumber = (value: number) => value.toLocaleString('en')
