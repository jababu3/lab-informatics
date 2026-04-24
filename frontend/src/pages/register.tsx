import { useState } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import { useAuth } from './_app'
import { Button } from '@/components/ui/button'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Register() {
  const { login } = useAuth()
  const router = useRouter()
  const [form, setForm] = useState({
    username: '', email: '', password: '', confirm_password: '',
    full_name: '', title: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm_password) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`${API}/auth/register`, { credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: form.username,
          email: form.email,
          password: form.password,
          full_name: form.full_name,
          title: form.title,
        })
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Registration failed')
      }
      // Auto-login after registration
      const loginBody = new URLSearchParams()
      loginBody.set('username', form.username)
      loginBody.set('password', form.password)
      const loginRes = await fetch(`${API}/auth/login`, { credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: loginBody,
      })
      if (loginRes.ok) {
        const data = await loginRes.json()
        login({
          username: data.username,
          role: data.role,
          full_name: data.full_name,
          title: data.title,
        })
      }
      router.push('/')
    } catch (err: any) {
      if (err.message === 'Failed to fetch') {
        setError('Cannot reach the API server at ' + API + '. Make sure the backend is running.')
      } else {
        setError(err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  const inputClass = "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"

  return (
    <div className="min-h-screen bg-background text-foreground font-sans flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-tight mb-1">Create Account</h1>
          <p className="text-sm text-muted-foreground">First registered user becomes the system administrator</p>
        </div>

        <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium leading-none">Full Name</label>
                <input
                  id="full_name"
                  type="text"
                  placeholder="Dr. Jane Smith"
                  value={form.full_name}
                  onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium leading-none">Title</label>
                <input
                  id="title"
                  type="text"
                  placeholder="Principal Investigator"
                  value={form.title}
                  onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  className={inputClass}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium leading-none">Username <span className="text-destructive">*</span></label>
              <input
                id="username"
                type="text"
                required
                placeholder="jsmith"
                value={form.username}
                onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                className={inputClass}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium leading-none">Email <span className="text-destructive">*</span></label>
              <input
                id="email"
                type="email"
                required
                placeholder="jane@lab.example.com"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className={inputClass}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium leading-none">Password <span className="text-destructive">*</span></label>
              <input
                id="password"
                type="password"
                required
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                className={inputClass}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium leading-none">Confirm Password <span className="text-destructive">*</span></label>
              <input
                id="confirm_password"
                type="password"
                required
                value={form.confirm_password}
                onChange={e => setForm(f => ({ ...f, confirm_password: e.target.value }))}
                className={inputClass}
              />
            </div>

            {error && (
              <div className="rounded-md border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <Button
              id="register-submit"
              type="submit"
              disabled={loading}
              className="w-full mt-2"
            >
              {loading ? 'Creating account...' : 'Create Account & Sign In'}
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link href="/login" className="font-medium underline underline-offset-4 text-foreground">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
