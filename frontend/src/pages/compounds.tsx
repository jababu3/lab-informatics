import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import Layout from '@/components/Layout'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type LipinskiResult = {
  compliant: boolean;
}

type Compound = {
  _id: string;
  name: string;
  smiles: string;
  tags: string[];
  svg_structure?: string;
  molecular_weight?: number;
  logp?: number;
  lipinski?: LipinskiResult;
}

type CompoundFormData = {
  name: string;
  smiles: string;
  tags: string;
}

export default function Compounds() {
  const [compounds, setCompounds] = useState<Compound[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState<CompoundFormData>({ name: '', smiles: '', tags: '' })
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    loadCompounds()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadCompounds = () => {
    setLoading(true)
    fetch(`${API}/compounds/`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        setCompounds(data.compounds || [])
        setLoading(false)
      })
      .catch(e => {
        console.error(e)
        setLoading(false)
      })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    const compound = {
      name: formData.name,
      smiles: formData.smiles,
      tags: formData.tags.split(',').map(t => t.trim()).filter(t => t)
    }

    try {
      const response = await fetch(`${API}/compounds/`, {
        credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(compound)
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Failed to add compound')
      }

      setFormData({ name: '', smiles: '', tags: '' })
      setShowForm(false)
      loadCompounds()
    } catch (e: any) {
      setFormError(e.message)
    }
  }

  return (
    <Layout>
      <main className="container mx-auto px-6 py-12 max-w-7xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight mb-2">Compound Library</h1>
            <p className="text-muted-foreground text-sm">Manage chemical assets and descriptors.</p>
          </div>
          <Button onClick={() => { setShowForm(!showForm); setFormError(null) }}>
            {showForm ? 'Cancel' : 'Add Compound'}
          </Button>
        </div>

        {/* Add Form */}
        {showForm && (
          <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 mb-8 max-w-2xl">
            <h3 className="font-semibold text-lg tracking-tight mb-4">New Compound</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium leading-none">Name</label>
                <Input
                  type="text"
                  required
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Aspirin"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium leading-none">SMILES string</label>
                <Input
                  type="text"
                  required
                  value={formData.smiles}
                  onChange={e => setFormData({ ...formData, smiles: e.target.value })}
                  className="font-mono"
                  placeholder="e.g., CC(=O)OC1=CC=CC=C1C(=O)O"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium leading-none">Tags (comma-separated)</label>
                <Input
                  type="text"
                  value={formData.tags}
                  onChange={e => setFormData({ ...formData, tags: e.target.value })}
                  placeholder="e.g., NSAID, analgesic"
                />
              </div>

              {formError && (
                <div className="rounded-md border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                  {formError}
                </div>
              )}

              <Button type="submit" className="w-full">
                Add to Library
              </Button>
            </form>
          </div>
        )}

        {/* Compounds List */}
        {loading ? (
          <div className="flex justify-center p-12">
            <p className="text-sm text-muted-foreground animate-pulse">Loading compounds...</p>
          </div>
        ) : compounds.length === 0 ? (
          <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed text-center">
            <div className="mx-auto flex max-w-[420px] flex-col items-center justify-center text-center">
              <h2 className="mt-6 text-xl font-semibold">No compounds yet</h2>
              <p className="mb-8 mt-2 text-center text-sm font-normal leading-6 text-muted-foreground">
                Add your first compound using the button above or run `make seed` to load samples.
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {compounds.map(compound => (
              <div
                key={compound._id || compound.smiles}
                className="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden flex flex-col"
              >
                <div className="p-6 pb-4">
                  <h3 className="font-semibold text-lg tracking-tight mb-4">{compound.name}</h3>

                  {/* Structure visualization */}
                  {compound.svg_structure ? (
                    <div className="mb-4 rounded-md border bg-white p-2 flex items-center justify-center min-h-[160px]">
                      <img
                        src={`data:image/svg+xml,${encodeURIComponent(compound.svg_structure)}`}
                        alt={`Structure of ${compound.name}`}
                        className="max-w-full max-h-[150px] object-contain"
                      />
                    </div>
                  ) : (
                    <div className="mb-4 rounded-md bg-muted p-4 flex items-center justify-center min-h-[160px] text-xs text-muted-foreground break-all text-center">
                      <span className="font-mono">
                        {compound.smiles?.substring(0, 40)}{compound.smiles?.length > 40 ? '...' : ''}
                      </span>
                    </div>
                  )}

                  {/* Properties */}
                  <div className="space-y-1.5 text-sm text-muted-foreground mb-4">
                    {compound.molecular_weight && (
                      <div className="flex justify-between">
                        <span className="font-medium">MW</span>
                        <span>{compound.molecular_weight.toFixed(2)}</span>
                      </div>
                    )}
                    {compound.logp !== undefined && (
                      <div className="flex justify-between">
                        <span className="font-medium">LogP</span>
                        <span>{compound.logp.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-auto px-6 pb-6 pt-0">
                  <div className="flex flex-col gap-3">
                    {compound.lipinski && (
                      <div className="flex w-full">
                        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          compound.lipinski.compliant
                            ? 'bg-secondary text-secondary-foreground'
                            : 'bg-destructive/10 text-destructive border border-destructive/20'
                        }`}>
                          {compound.lipinski.compliant ? 'Compliant (Lipinski)' : 'Violates Lipinski'}
                        </span>
                      </div>
                    )}

                    {compound.tags && compound.tags.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-1 border-t">
                        {compound.tags.map((tag, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </Layout>
  )
}
