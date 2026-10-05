import type { ReactNode } from 'react'

/** Horizontally scrollable table wrapper; rows stay rows, not cards. */
export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse text-left">{children}</table>
    </div>
  )
}

export function Th({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <th scope="col" className={`border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-medium text-slate-500 ${className}`}>
      {children}
    </th>
  )
}

export function Td({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <td className={`border-b border-slate-100 px-4 py-2.5 ${className}`}>{children}</td>
}
