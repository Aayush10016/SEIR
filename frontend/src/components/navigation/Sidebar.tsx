import { NavLink } from 'react-router-dom'
import { primaryNav } from './navItems'

export function Sidebar() {
  return (
    <nav aria-label="Primary" className="w-14 shrink-0 overflow-y-auto border-r border-slate-200 bg-white py-3 lg:w-56">
      <ul className="space-y-0.5">
        {primaryNav.map(({ to, label, icon: Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              title={label}
              className={({ isActive }) =>
                `flex items-center gap-3 border-l-2 px-4 py-2 ${
                  isActive
                    ? 'border-accent bg-accent-soft font-medium text-accent'
                    : 'border-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <Icon aria-hidden="true" size={16} className="shrink-0" />
              <span className="sr-only lg:not-sr-only">{label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
