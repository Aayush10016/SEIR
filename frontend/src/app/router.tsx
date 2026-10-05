import { Navigate, createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { DashboardPage } from '@/pages/DashboardPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { PlaceholderPage } from '@/pages/PlaceholderPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      {
        path: 'repository',
        element: <PlaceholderPage phase={2} title="Repositories" description="Choose a repository and start an analysis." />,
      },
      {
        path: 'analysis',
        element: <PlaceholderPage phase={2} title="Analysis" description="Results of the latest repository analysis." />,
      },
      {
        path: 'components',
        element: <PlaceholderPage phase={3} title="Components" description="Search and filter the components found in the repository." />,
      },
      {
        path: 'components/:componentId',
        element: <PlaceholderPage phase={3} title="Component details" description="Evidence, risk and impact for a single component." />,
      },
      {
        path: 'impact',
        element: <PlaceholderPage phase={5} title="Impact Analysis" description="What could be affected if a component changes." />,
      },
      {
        path: 'risk',
        element: <PlaceholderPage phase={5} title="Risk Assessment" description="Change risk, evidence and recommendation." />,
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
