import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { useAuth } from '../_app'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import Layout from '@/components/Layout'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type AppUser = {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  title?: string;
  role: string;
  is_active: boolean;
}

type EditForm = {
  full_name: string;
  title: string;
  email: string;
  role: string;
}

export default function UserManagement() {
  const { user, loading: authLoading } = useAuth()
  const router = useRouter()

  const [users, setUsers]   = useState<AppUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  // Create user form
  const [showCreate, setShowCreate] = useState(false)
  const [newUsername, setNewUsername] = useState('')
  const [newEmail, setNewEmail]       = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newFullName, setNewFullName] = useState('')
  const [newTitle, setNewTitle]       = useState('')
  const [newRole, setNewRole]         = useState('scientist')
  const [createError, setCreateError] = useState<string | null>(null)

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm]   = useState<EditForm>({ full_name: '', title: '', email: '', role: '' })

  useEffect(() => {
    if (authLoading) return
    if (!user || user.role !== 'admin') { router.push('/'); return }
    fetchUsers()
  }, [user, authLoading])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/auth/users`, { credentials: 'include' })
      if (!res.ok) throw new Error('Failed to fetch users')
      setUsers(await res.json())
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleStatusChange = async (userId: string, isActive: boolean) => {
    setActionError(null)
    try {
      const res = await fetch(`${API_BASE}/auth/users/${userId}/status`, {
        credentials: 'include',
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: isActive })
      })
      if (!res.ok) throw new Error(await res.text())
      fetchUsers()
    } catch (err: any) {
      setActionError(`Error updating status: ${err.message}`)
    }
  }

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreateError(null)
    try {
      const res = await fetch(`${API_BASE}/auth/admin/create-user`, {
        credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: newUsername, email: newEmail, password: newPassword,
          full_name: newFullName, title: newTitle, role: newRole
        })
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to create user')
      }
      setNewUsername(''); setNewEmail(''); setNewPassword('')
      setNewFullName(''); setNewTitle(''); setNewRole('scientist')
      setShowCreate(false)
      fetchUsers()
    } catch (err: any) {
      setCreateError(err.message)
    }
  }

  const startEditing = (u: AppUser) => {
    setEditingId(u.id)
    setEditForm({ full_name: u.full_name || '', title: u.title || '', email: u.email || '', role: u.role })
  }

  const cancelEditing = () => setEditingId(null)

  const saveEdit = async (userId: string, originalRole: string) => {
    setActionError(null)
    try {
      const putRes = await fetch(`${API_BASE}/auth/users/${userId}`, {
        credentials: 'include',
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: editForm.full_name, title: editForm.title, email: editForm.email })
      })
      if (!putRes.ok) {
        const errData = await putRes.json()
        throw new Error(errData.detail || 'Failed to update user profile')
      }

      if (editForm.role !== originalRole) {
        const roleRes = await fetch(`${API_BASE}/auth/users/${userId}/role`, {
          credentials: 'include',
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role: editForm.role })
        })
        if (!roleRes.ok) {
          const errData = await roleRes.json()
          throw new Error(errData.detail || 'Failed to update user role')
        }
      }

      setEditingId(null)
      fetchUsers()
    } catch (err: any) {
      setActionError(err.message)
    }
  }

  if (authLoading || loading) return (
    <Layout>
      <div className="p-8 text-muted-foreground text-center">Loading...</div>
    </Layout>
  )
  if (!user || user.role !== 'admin') return null

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold tracking-tight mb-8">User Management</h1>

        {error && (
          <div className="rounded-md border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive mb-4">
            {error}
          </div>
        )}
        {actionError && (
          <div className="rounded-md border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive mb-4">
            {actionError}
          </div>
        )}

        <div className="flex justify-end mb-4">
          <Button onClick={() => setShowCreate(!showCreate)} variant={showCreate ? 'secondary' : 'default'}>
            {showCreate ? 'Cancel' : '+ Create New User'}
          </Button>
        </div>

        {/* ── Create User Form ── */}
        {showCreate && (
          <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 mb-8">
            <h2 className="text-lg font-semibold mb-4">Create User</h2>
            {createError && (
              <div className="rounded-md border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive mb-4">
                {createError}
              </div>
            )}
            <form onSubmit={handleCreateUser} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium leading-none">Username *</label>
                <Input value={newUsername} onChange={e => setNewUsername(e.target.value)} required />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium leading-none">Email *</label>
                <Input type="email" value={newEmail} onChange={e => setNewEmail(e.target.value)} required />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium leading-none">Password *</label>
                <Input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium leading-none">Role</label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={newRole}
                  onChange={e => setNewRole(e.target.value)}
                >
                  <option value="admin">Admin</option>
                  <option value="scientist">Scientist</option>
                  <option value="reviewer">Reviewer</option>
                  <option value="read-only">Read-Only</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium leading-none">Full Legal Name</label>
                <Input value={newFullName} onChange={e => setNewFullName(e.target.value)} placeholder="e.g. Jane Doe" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium leading-none">Title / Role</label>
                <Input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="e.g. Senior Chemist" />
              </div>
              <div className="md:col-span-2 pt-2">
                <Button type="submit">Create Account</Button>
              </div>
            </form>
          </div>
        )}

        {/* ── Users Table ── */}
        <div className="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b">
                <tr>
                  <th className="px-6 py-4 font-medium">Username</th>
                  <th className="px-6 py-4 font-medium">Email</th>
                  <th className="px-6 py-4 font-medium">Full Name & Title</th>
                  <th className="px-6 py-4 font-medium">Role</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {users.map(u => {
                  const isEditing = editingId === u.id
                  return (
                    <tr key={u.id} className={`hover:bg-muted/30 transition-colors ${!u.is_active ? 'opacity-50' : ''}`}>
                      <td className="px-6 py-4 font-medium">{u.username}</td>
                      <td className="px-6 py-4">
                        {isEditing ? (
                          <Input value={editForm.email} onChange={e => setEditForm({ ...editForm, email: e.target.value })} />
                        ) : (
                          <span className="text-muted-foreground">{u.email}</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {isEditing ? (
                          <div className="space-y-2">
                            <Input placeholder="Full Name" value={editForm.full_name} onChange={e => setEditForm({ ...editForm, full_name: e.target.value })} />
                            <Input placeholder="Title" value={editForm.title} onChange={e => setEditForm({ ...editForm, title: e.target.value })} />
                          </div>
                        ) : (
                          <div>
                            <div>{u.full_name || '-'}</div>
                            <div className="text-xs text-muted-foreground">{u.title || '-'}</div>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {isEditing && u.id !== user.id ? (
                          <select
                            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                            value={editForm.role}
                            onChange={e => setEditForm({ ...editForm, role: e.target.value })}
                          >
                            <option value="admin">Admin</option>
                            <option value="scientist">Scientist</option>
                            <option value="reviewer">Reviewer</option>
                            <option value="read-only">Read-Only</option>
                          </select>
                        ) : (
                          <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-secondary/50 text-secondary-foreground">
                            {u.role}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                          u.is_active
                            ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                            : 'bg-destructive/10 text-destructive border-destructive/20'
                        }`}>
                          {u.is_active ? 'Active' : 'Deactivated'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right space-x-2">
                        {isEditing ? (
                          <>
                            <Button size="sm" onClick={() => saveEdit(u.id, u.role)}>Save</Button>
                            <Button size="sm" variant="ghost" onClick={cancelEditing}>Cancel</Button>
                          </>
                        ) : (
                          <>
                            <Button size="sm" variant="outline" onClick={() => startEditing(u)}>Edit</Button>
                            <Button
                              size="sm"
                              variant={u.is_active ? 'destructive' : 'secondary'}
                              onClick={() => handleStatusChange(u.id, !u.is_active)}
                              disabled={u.username === user.username}
                            >
                              {u.is_active ? 'Deactivate' : 'Activate'}
                            </Button>
                          </>
                        )}
                      </td>
                    </tr>
                  )
                })}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-muted-foreground">
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  )
}
