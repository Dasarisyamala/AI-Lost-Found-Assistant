import { Navigate } from 'react-router-dom'
import type { ReactElement } from 'react'
import { useAuth } from '../lib/auth'

export function ProtectedRoute({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-slate-300">Loading…</div>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return children
}
