import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { useAuth } from './_app'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import Layout from '@/components/Layout'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type ProfileData = {
  username: string;
  email: string;
  full_name?: string;
  title?: string;
  role: string;
}

type ProfileForm = {
  full_name: string;
  title: string;
  email: string;
}

type PasswordForm = {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export default function Profile() {
  const { user, loading: authLoading } = useAuth()
  const router = useRouter()

  const [profile, setProfile]     = useState<ProfileData | null>(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const [form, setForm]             = useState<ProfileForm>({ full_name: '', title: '', email: '' })
  const [savingProfile, setSavingProfile] = useState(false)

  const [passForm, setPassForm]     = useState<PasswordForm>({ current_password: '', new_password: '', confirm_password: '' })
  const [savingPass, setSavingPass] = useState(false)
  const [passError, setPassError]   = useState<string | null>(null)
  const [passSuccess, setPassSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (authLoading) return
    if (!user) { router.push('/login'); return }
    fetchProfile()
  }, [user, authLoading])

  const fetchProfile = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' })
      if (!res.ok) throw new Error('Failed to fetch profile info')
      const data = await res.json()
      setProfile(data)
      setForm({ full_name: data.full_name || '', title: data.title || '', email: data.email || '' })
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setSavingProfile(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await fetch(`${API_BASE}/auth/profile`, {
        credentials: 'include',
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: form.full_name, title: form.title, email: form.email })
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to update profile')
      }
      setSuccessMsg('Profile updated successfully')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSavingProfile(false)
    }
  }

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setSavingPass(true)
    setPassError(null)
    setPassSuccess(null)

    if (passForm.new_password !== passForm.confirm_password) {
      setPassError('New passwords do not match')
      setSavingPass(false)
      return
    }

    try {
      const res = await fetch(`${API_BASE}/auth/profile`, {
        credentials: 'include',
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: passForm.current_password, new_password: passForm.new_password })
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to update password')
      }
      setPassSuccess('Password changed successfully')
      setPassForm({ current_password: '', new_password: '', confirm_password: '' })
    } catch (err: any) {
      setPassError(err.message)
    } finally {
      setSavingPass(false)
    }
  }

  if (authLoading || loading) return (
    <Layout>
      <div className="p-8 text-muted-foreground text-center">Loading...</div>
    </Layout>
  )
  if (!user || !profile) return null

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold tracking-tight mb-10">Your Profile</h1>

        <div className="grid gap-10">
          {/* ── Account Information ── */}
          <section className="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b bg-muted/30">
              <h2 className="text-lg font-semibold">Account Information</h2>
              <p className="text-sm text-muted-foreground mt-1">Update your personal details and contact information.</p>
            </div>

            <div className="p-6">
              {error && (
                <div className="rounded-md border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive mb-6">
                  {error}
                </div>
              )}
              {successMsg && (
                <div className="rounded-md border border-emerald-200 bg-emerald-100 px-4 py-3 text-sm text-emerald-800 mb-6">
                  {successMsg}
                </div>
              )}

              <form onSubmit={handleUpdateProfile} className="space-y-6">
                <div>
                  <label className="text-sm font-medium leading-none mb-2 block">Username</label>
                  <Input
                    value={profile.username}
                    readOnly
                    disabled
                    className="bg-muted/50"
                  />
                  <p className="text-[0.8rem] text-muted-foreground mt-2">
                    Username cannot be changed as it is the permanent identity anchor for 21 CFR Part 11 signatures.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="text-sm font-medium leading-none mb-2 block">Full Legal Name</label>
                    <Input
                      value={form.full_name}
                      onChange={e => setForm({ ...form, full_name: e.target.value })}
                      placeholder="e.g. Dr. Jane Smith"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium leading-none mb-2 block">Title / Role</label>
                    <Input
                      value={form.title}
                      onChange={e => setForm({ ...form, title: e.target.value })}
                      placeholder="e.g. Principal Investigator"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium leading-none mb-2 block">Email Address</label>
                  <Input
                    type="email"
                    value={form.email}
                    onChange={e => setForm({ ...form, email: e.target.value })}
                  />
                </div>

                <div className="flex justify-end pt-2">
                  <Button type="submit" disabled={savingProfile}>
                    {savingProfile ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              </form>
            </div>
          </section>

          {/* ── Security ── */}
          <section className="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b bg-muted/30">
              <h2 className="text-lg font-semibold">Security</h2>
              <p className="text-sm text-muted-foreground mt-1">Manage your password to secure your account.</p>
            </div>

            <div className="p-6">
              {passError && (
                <div className="rounded-md border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive mb-6">
                  {passError}
                </div>
              )}
              {passSuccess && (
                <div className="rounded-md border border-emerald-200 bg-emerald-100 px-4 py-3 text-sm text-emerald-800 mb-6">
                  {passSuccess}
                </div>
              )}

              <form onSubmit={handleUpdatePassword} className="space-y-6 max-w-md">
                <div>
                  <label className="text-sm font-medium leading-none mb-2 block">Current Password</label>
                  <Input
                    type="password"
                    required
                    value={passForm.current_password}
                    onChange={e => setPassForm({ ...passForm, current_password: e.target.value })}
                  />
                </div>

                <div>
                  <label className="text-sm font-medium leading-none mb-2 block">New Password</label>
                  <Input
                    type="password"
                    required
                    minLength={12}
                    value={passForm.new_password}
                    onChange={e => setPassForm({ ...passForm, new_password: e.target.value })}
                  />
                  <p className="text-[0.75rem] text-muted-foreground mt-1">Must be at least 12 characters.</p>
                </div>

                <div>
                  <label className="text-sm font-medium leading-none mb-2 block">Confirm New Password</label>
                  <Input
                    type="password"
                    required
                    minLength={12}
                    value={passForm.confirm_password}
                    onChange={e => setPassForm({ ...passForm, confirm_password: e.target.value })}
                  />
                </div>

                <div className="pt-2">
                  <Button type="submit" variant="secondary" disabled={savingPass}>
                    {savingPass ? 'Updating...' : 'Change Password'}
                  </Button>
                </div>
              </form>
            </div>
          </section>
        </div>
      </div>
    </Layout>
  )
}
