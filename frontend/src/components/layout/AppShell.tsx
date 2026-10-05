import { Outlet } from 'react-router-dom'
import { Sidebar } from '@/components/navigation/Sidebar'
import { Topbar } from './Topbar'

export function AppShell() {
  return (
    <div className="flex h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-1.5"
      >
        Skip to content
      </a>
      <Topbar />
      <div className="flex min-h-0 flex-1">
        <Sidebar />
        <main id="main" tabIndex={-1} className="min-w-0 flex-1 overflow-y-auto focus:outline-none">
          <div className="mx-auto max-w-6xl px-6 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
