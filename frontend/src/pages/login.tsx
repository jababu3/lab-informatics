import { useState } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import { useAuth } from './_app'
import { Button } from '@/components/ui/button'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Login() {
  const { login } = useAuth()
  const router = useRouter()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const body = new URLSearchParams()
      body.set('username', form.username)
      body.set('password', form.password)
      const res = await fetch(`${API}/auth/login`, { credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Login failed')
      }
      const data = await res.json()
      login({
        username: data.username,
        role: data.role,
        full_name: data.full_name,
        title: data.title,
      })
      router.push('/')
    } catch (err: any) {
      if (err.message === 'Failed to fetch') {
        setError('Cannot reach the API server. Ensure the backend is running at ' + API)
      } else {
        setError(err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground font-sans flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-tight mb-1">Lab Informatics</h1>
          <p className="text-sm text-muted-foreground">Sign in to your account</p>
        </div>

        <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label htmlFor="login-username" className="text-sm font-medium leading-none">
                Username
              </label>
              <input
                id="login-username"
                type="text"
                autoComplete="username"
                required
                value={form.username}
                onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="login-password" className="text-sm font-medium leading-none">
                Password
              </label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                required
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            {error && (
              <div className="rounded-md border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <Button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="w-full"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          No account?{' '}
          <Link href="/register" className="font-medium underline underline-offset-4 text-foreground">
            Create the first admin account
          </Link>
        </p>
      </div>
    </div>
  )
}
