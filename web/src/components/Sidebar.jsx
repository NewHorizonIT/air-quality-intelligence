import { Wind } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/',           label: 'Dashboard'       },
  { to: '/prediction', label: 'Prediction Demo' },
]

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-52 bg-white border-r border-gray-100 flex flex-col z-20">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-5 border-b border-gray-100">
        <Wind size={20} className="text-brand" />
        <span className="font-bold text-lg text-brand">AQI Delhi</span>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-1 px-3 pt-4">
        {navItems.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors
               ${isActive
                 ? 'bg-brand/10 text-brand'
                 : 'text-gray-500 hover:bg-gray-50 hover:text-gray-800'}`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Meta */}
      <div className="mt-auto px-5 pb-6 text-xs text-gray-400 space-y-1">
        <p className="font-semibold text-gray-500 uppercase tracking-wider mb-2">Data</p>
        <p>Period: 2022 – 2025</p>
        <p>Stations: 53</p>
        <p>Target: next-day PM2.5</p>
        <p>Model: LightGBM Exp3</p>
      </div>
    </aside>
  )
}
