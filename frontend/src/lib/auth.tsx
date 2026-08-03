import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { clearToken, getToken, login, me, register, saveToken } from './api'
import type { User } from './types'

type AuthContextValue = {
  user: User | null
  loading: boolean
  signIn: (payload: { email: string; password: string }) => Promise<void>
  signUp: (payload: { name: string; email: string; password: string }) => Promise<void>
  signOut: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  async function refreshUser() {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      setLoading(true)
      setUser(await me())
    } catch {
      clearToken()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refreshUser()
  }, [])

  async function signIn(payload: { email: string; password: string }) {
    const response = await login(payload)
    saveToken(response.access_token)
    setUser(response.user)
  }

  async function signUp(payload: { name: string; email: string; password: string }) {
    await register(payload)
    await signIn({ email: payload.email, password: payload.password })
  }

  function signOut() {
    clearToken()
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, signIn, signUp, signOut, refreshUser }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return value
}
