import { Boxes, FolderGit2, LayoutDashboard, Network, ShieldAlert, type LucideIcon } from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

export const primaryNav: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/repository', label: 'Repositories', icon: FolderGit2 },
  { to: '/components', label: 'Components', icon: Boxes },
  { to: '/impact', label: 'Impact Analysis', icon: Network },
  { to: '/risk', label: 'Risk Assessment', icon: ShieldAlert },
]
