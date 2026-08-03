import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-full px-4 py-2 text-sm transition ${isActive ? 'bg-white text-slate-950' : 'text-slate-300 hover:bg-white/10 hover:text-white'}`

export function Navbar() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 lg:px-8">
        <Link to="/dashboard" className="text-lg font-black tracking-tight text-white">
          AI Lost & Found
        </Link>
        <nav className="hidden items-center gap-2 md:flex">
          <NavLink to="/dashboard" className={navClass}>Dashboard</NavLink>
          <NavLink to="/browse-lost" className={navClass}>Browse Lost Items</NavLink>
          <NavLink to="/report-lost" className={navClass}>Lost Item</NavLink>
          <NavLink to="/report-found" className={navClass}>Found Item</NavLink>
        </nav>
        <div className="flex items-center gap-3 text-sm">
          {user ? <span className="hidden text-slate-400 sm:block">{user.name}</span> : null}
          {user ? (
            <button
              className="btn-secondary"
              onClick={() => {
                signOut()
                navigate('/login')
              }}
            >
              Sign out
            </button>
          ) : null}
        </div>
      </div>
    </header>
  )
}
