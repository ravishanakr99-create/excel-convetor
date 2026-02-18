import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-2 rounded-lg transition-colors ${
      isActive ? 'bg-primary-500/20 text-primary-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
    }`

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          <NavLink to="/" className="text-xl font-semibold text-primary-400">
            PDF Extractor
          </NavLink>
          <nav className="flex flex-wrap items-center gap-1 sm:gap-2">
            <NavLink to="/" end className={navClass}>
              Dashboard
            </NavLink>
            <NavLink to="/upload" className={navClass}>
              Upload
            </NavLink>
            <NavLink to="/history" className={navClass}>
              History
            </NavLink>
            <div className="ml-2 sm:ml-4 flex items-center gap-2 sm:gap-3">
              <span className="text-xs sm:text-sm text-slate-400 truncate max-w-[120px] sm:max-w-none">{user?.email}</span>
              <button
                onClick={logout}
                className="px-3 py-1.5 text-sm rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
              >
                Logout
              </button>
            </div>
          </nav>
        </div>
      </header>
      <main className="flex-1 p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  )
}
