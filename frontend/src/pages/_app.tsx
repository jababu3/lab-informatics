// ============================================================================
// FILE: frontend/src/pages/_app.tsx
// Auth context — wraps the entire app and manages JWT state
// ============================================================================

import type { AppProps } from 'next/app'
import { createContext, useContext, useState, useEffect } from 'react'
import '../styles/globals.css'

export type User = {
  username: string;
  role: string;
  full_name?: string;
  title?: string;
}

type AuthContextType = {
  user: User | null;
  login: (userData: User) => void;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null)

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default function App({ Component, pageProps }: AppProps) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Attempt to restore session using httpOnly cookie
    const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    fetch(`${API}/auth/me`, { credentials: 'include' })
      .then(r => {
        if (r.ok) return r.json()
        throw new Error('Not authenticated')
      })
      .then(userData => {
        setUser(userData)
        setLoading(false)
      })
      .catch(() => {
        setUser(null)
        setLoading(false)
      })
  }, [])

  const login = (userData: User) => {
    setUser(userData)
  }

  const logout = () => {
    const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' })
      .then(() => {
        setUser(null)
      })
      .catch(console.error)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      <Component {...pageProps} />
    </AuthContext.Provider>
  )
}