import Link from 'next/link'
import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/router'
import { useAuth } from '../_app'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import Layout from '@/components/Layout'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const SECTION_TYPES = [
  { value: 'procedure',   label: 'Procedure' },
  { value: 'observation', label: 'Observation' },
  { value: 'result',      label: 'Result' },
  { value: 'conclusion',  label: 'Conclusion' },
  { value: 'note',        label: 'Note' },
]

const SIGNATURE_MEANINGS = [
  'I am the author of this record and attest to its accuracy',
  'I reviewed this record and approve its content',
  'I witnessed the described procedures and confirm their accuracy',
  'I am the principal investigator responsible for this study',
]

type Section = {
  section_id: string;
  section_type: string;
  title: string;
  content: string;
}

type UploadedDoc = {
  doc_id: string;
  original_filename: string;
  size_bytes: number;
}

type SignatureData = {
  signer_name: string;
  signer_title: string;
  meaning: string;
  signed_at: string;
  record_hash_at_signing?: string;
}

// Shared class for textarea elements (Input component handles <input> tags)
const textareaClass = "flex min-h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"

export default function NewELNEntry() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { user } = useAuth()

  const [title, setTitle]         = useState('')
  const [objective, setObjective] = useState('')

  const [sections, setSections] = useState<Section[]>([
    { section_id: crypto.randomUUID(), section_type: 'procedure', title: 'Procedure', content: '' },
  ])

  const [pendingFiles, setPendingFiles]   = useState<File[]>([])
  const [uploadedDocs, setUploadedDocs]   = useState<UploadedDoc[]>([])

  const [entryId, setEntryId]   = useState<string | null>(null)
  const [saving, setSaving]     = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved]       = useState(false)

  const [showSigPanel, setShowSigPanel] = useState(false)
  const [sigName, setSigName]           = useState('')
  const [sigTitle, setSigTitle]         = useState('')
  const [sigMeaning, setSigMeaning]     = useState(SIGNATURE_MEANINGS[0])
  const [signing, setSigning]           = useState(false)
  const [sigError, setSigError]         = useState<string | null>(null)
  const [signedData, setSignedData]     = useState<SignatureData | null>(null)

  useEffect(() => {
    if (user) {
      setSigName(user.full_name || user.username)
      setSigTitle(user.title || '')
    }
  }, [user])

  useEffect(() => {
    const { resume } = router.query
    if (resume && typeof resume === 'string') {
      setEntryId(resume)
      setSaved(true)
      setShowSigPanel(true)
    }
  }, [router.query])

  const addSection = () => setSections(prev => [
    ...prev,
    { section_id: crypto.randomUUID(), section_type: 'note', title: '', content: '' },
  ])

  const removeSection = (id: string) =>
    setSections(prev => prev.filter(s => s.section_id !== id))

  const updateSection = (id: string, field: string, value: string) =>
    setSections(prev => prev.map(s => s.section_id === id ? { ...s, [field]: value } : s))

  const handleFileDrop = (e: React.DragEvent | React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    let files: File[] = []
    if ('dataTransfer' in e) {
      files = Array.from(e.dataTransfer.files)
    } else if (e.target.files) {
      files = Array.from(e.target.files)
    }
    if (files.length > 0) setPendingFiles(prev => [...prev, ...files])
  }

  const removePendingFile = (name: string) =>
    setPendingFiles(prev => prev.filter(f => f.name !== name))

  const saveEntry = async () => {
    if (!title.trim()) { setSaveError('Title is required.'); return }
    setSaving(true)
    setSaveError(null)

    try {
      const res = await fetch(`${API}/eln/`, {
        credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          author:       user ? (user.full_name || user.username) : '',
          author_title: user ? (user.title || '') : '',
          objective,
          sections,
        })
      })
      if (!res.ok) throw new Error(await res.text())
      const { entry } = await res.json()
      const id = entry.entry_id
      setEntryId(id)

      const uploaded: UploadedDoc[] = []
      for (const file of pendingFiles) {
        const fd = new FormData()
        fd.append('file', file)
        const dr = await fetch(`${API}/eln/${id}/documents`, { credentials: 'include', method: 'POST', body: fd })
        if (dr.ok) {
          const { document } = await dr.json()
          uploaded.push(document)
        }
      }
      setUploadedDocs(uploaded)
      setPendingFiles([])
      setSaved(true)
    } catch (err: any) {
      setSaveError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const signEntry = async () => {
    if (!sigName.trim() || !sigTitle.trim()) {
      setSigError('Full legal name and title are required to sign.')
      return
    }
    setSigning(true)
    setSigError(null)

    try {
      const res = await fetch(`${API}/eln/${entryId}/sign`, {
        credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signer_name: sigName, signer_title: sigTitle, meaning: sigMeaning })
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Signing failed')
      }
      const data = await res.json()
      setSignedData(data.entry?.signature || data.signature)
    } catch (err: any) {
      setSigError(err.message)
    } finally {
      setSigning(false)
    }
  }

  return (
    <Layout>
      {/* Success view shown after signing */}
      {signedData ? (
        <div className="flex items-center justify-center py-20 px-6">
          <div className="max-w-xl w-full text-center space-y-8">
            <div className="inline-flex h-20 w-20 items-center justify-center rounded-full bg-primary/10 mb-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            </div>
            <h1 className="text-3xl font-bold tracking-tight">Entry Signed Successfully</h1>

            <div className="rounded-xl border bg-card text-left shadow-sm overflow-hidden">
              <div className="bg-muted/50 px-6 py-4 border-b">
                <h3 className="font-semibold text-sm">21 CFR Part 11 Signature Record</h3>
              </div>
              <table className="w-full text-sm">
                <tbody className="divide-y">
                  {[
                    ['Signer Name', signedData.signer_name],
                    ['Title / Role', signedData.signer_title],
                    ['Meaning', signedData.meaning],
                    ['Date & Time (UTC)', new Date(signedData.signed_at).toLocaleString('en-US', { timeZone: 'UTC', timeZoneName: 'short' })],
                    ['Record Hash', signedData.record_hash_at_signing ? signedData.record_hash_at_signing.slice(0, 32) + '...' : '-'],
                  ].map(([k, v]) => (
                    <tr key={k} className="hover:bg-muted/30">
                      <td className="px-6 py-3 font-medium text-muted-foreground w-1/3">{k}</td>
                      <td className="px-6 py-3 font-mono">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex gap-4 justify-center mt-8">
              <Link href="/eln" passHref>
                <Button variant="outline">&larr; Back to ELN</Button>
              </Link>
              {entryId && (
                <Link href={`/eln/${entryId}`} passHref>
                  <Button>View Entry</Button>
                </Link>
              )}
            </div>
          </div>
        </div>
      ) : (
        <main className="container mx-auto px-6 pt-10 max-w-3xl pb-20">
          <div className="mb-8 border-b pb-6">
            <h1 className="text-3xl font-bold tracking-tight mb-2">New ELN Entry</h1>
            <p className="text-muted-foreground text-sm">Create a 21 CFR Part 11 compliant electronic record.</p>
          </div>

          {/* ── Entry Metadata ── */}
          <section className="space-y-6 mb-12">
            <h2 className="text-lg font-semibold border-b pb-2">Entry Metadata</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="md:col-span-2 space-y-2">
                <label className="text-sm font-medium leading-none">Entry Title <span className="text-destructive">*</span></label>
                <Input
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  placeholder="e.g., IC50 Determination — Compound 42 vs. EGFR"
                  disabled={saved}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium leading-none">Author <span className="text-muted-foreground font-normal text-xs ml-1">(from login)</span></label>
                <Input
                  value={user ? (user.full_name || user.username) : ''}
                  readOnly
                  disabled
                  className="bg-muted/50"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium leading-none">Title / Role <span className="text-muted-foreground font-normal text-xs ml-1">(from login)</span></label>
                <Input
                  value={user ? (user.title || '') : ''}
                  readOnly
                  disabled
                  className="bg-muted/50"
                />
              </div>
              <div className="md:col-span-2 space-y-2">
                <label className="text-sm font-medium leading-none">Objective / Purpose</label>
                <textarea
                  className={`${textareaClass} min-h-[80px] resize-y py-2`}
                  value={objective}
                  onChange={e => setObjective(e.target.value)}
                  placeholder="Briefly describe the purpose of this experiment..."
                  disabled={saved}
                />
              </div>
            </div>
          </section>

          {/* ── Content Sections ── */}
          <section className="mb-12">
            <div className="flex items-center justify-between mb-6 border-b pb-2">
              <h2 className="text-lg font-semibold">Content Sections</h2>
              {!saved && (
                <Button onClick={addSection} variant="outline" size="sm">+ Add Section</Button>
              )}
            </div>

            <div className="space-y-6">
              {sections.map((sec) => (
                <div key={sec.section_id} className="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden">
                  <div className="bg-muted/30 p-4 border-b flex flex-col sm:flex-row gap-4 items-start sm:items-center">
                    <div className="w-full sm:w-1/3 space-y-1.5">
                      <label className="text-xs font-semibold uppercase text-muted-foreground">Type</label>
                      <select
                        className={textareaClass}
                        value={sec.section_type}
                        onChange={e => updateSection(sec.section_id, 'section_type', e.target.value)}
                        disabled={saved}
                      >
                        {SECTION_TYPES.map(t => (
                          <option key={t.value} value={t.value}>{t.label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="w-full sm:flex-1 space-y-1.5">
                      <label className="text-xs font-semibold uppercase text-muted-foreground">Heading</label>
                      <Input
                        value={sec.title}
                        onChange={e => updateSection(sec.section_id, 'title', e.target.value)}
                        placeholder="Section Title..."
                        disabled={saved}
                      />
                    </div>
                    {!saved && sections.length > 1 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:bg-destructive/10 hover:text-destructive sm:mt-5 self-end sm:self-auto"
                        onClick={() => removeSection(sec.section_id)}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                      </Button>
                    )}
                  </div>
                  <div className="p-0">
                    <textarea
                      className="w-full font-mono text-sm leading-relaxed p-4 min-h-[160px] resize-y border-0 focus-visible:ring-0 bg-transparent outline-none"
                      value={sec.content}
                      onChange={e => updateSection(sec.section_id, 'content', e.target.value)}
                      placeholder="Enter your observations, methods, data, or notes here..."
                      disabled={saved}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* ── Attachments ── */}
          <section className="mb-12">
            <h2 className="text-lg font-semibold border-b pb-2 mb-6">Attachments</h2>

            {!saved && (
              <div
                onDrop={handleFileDrop}
                onDragOver={e => e.preventDefault()}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed rounded-xl p-10 text-center cursor-pointer bg-muted/20 hover:bg-muted/40 transition-colors mb-6"
              >
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted mb-4">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-muted-foreground"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>
                </div>
                <p className="font-medium text-sm">Drag & drop files here, or click to browse</p>
                <p className="text-xs text-muted-foreground mt-1">Supports PDF, CSV, Excel, Images, etc.</p>
                <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFileDrop} />
              </div>
            )}

            <div className="space-y-4">
              {pendingFiles.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase text-muted-foreground mb-2 tracking-wider">
                    Pending Upload ({pendingFiles.length})
                  </p>
                  <div className="grid gap-2">
                    {pendingFiles.map(f => (
                      <div key={f.name} className="flex justify-between items-center p-3 rounded-md bg-secondary/50 border text-sm">
                        <span className="font-medium truncate">
                          {f.name} <span className="text-muted-foreground font-normal ml-2">{(f.size / 1024).toFixed(1)} KB</span>
                        </span>
                        <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full" onClick={() => removePendingFile(f.name)}>
                          &times;
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {uploadedDocs.length > 0 && (
                <div className={pendingFiles.length > 0 ? 'pt-4' : ''}>
                  <p className="text-xs font-semibold uppercase text-muted-foreground mb-2 tracking-wider">
                    Uploaded ({uploadedDocs.length})
                  </p>
                  <div className="grid gap-2">
                    {uploadedDocs.map(d => (
                      <div key={d.doc_id} className="flex items-center gap-3 p-3 rounded-md border bg-card text-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                        <span className="font-medium">{d.original_filename}</span>
                        <span className="text-muted-foreground">{(d.size_bytes / 1024).toFixed(1)} KB</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!saved && pendingFiles.length === 0 && uploadedDocs.length === 0 && (
                <p className="text-sm text-muted-foreground italic">No attachments added.</p>
              )}
            </div>
          </section>

          {/* ── Save / Proceed ── */}
          {!saved ? (
            <div className="pt-6 border-t">
              {saveError && (
                <div className="rounded-md border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive mb-4">
                  {saveError}
                </div>
              )}
              <Button onClick={saveEntry} disabled={saving} className="w-full sm:w-auto h-11 px-8">
                {saving ? 'Saving...' : 'Save Draft Entry'}
              </Button>
            </div>
          ) : !signedData ? (
            <div className="pt-6 border-t">
              <div className="flex flex-col sm:flex-row items-center justify-between p-4 rounded-xl border bg-muted/30 gap-4 mb-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                  </div>
                  <div>
                    <p className="font-medium text-sm">Entry Saved (Draft)</p>
                    <p className="text-xs text-muted-foreground font-mono mt-0.5">ID: {entryId}</p>
                  </div>
                </div>
                <Button onClick={() => setShowSigPanel(p => !p)} variant={showSigPanel ? 'secondary' : 'default'}>
                  {showSigPanel ? 'Cancel Signing' : 'Sign Entry'}
                </Button>
              </div>
            </div>
          ) : null}

          {/* ── Signature Panel ── */}
          {saved && showSigPanel && !signedData && (
            <div className="rounded-xl border-2 border-primary overflow-hidden shadow-sm mt-8">
              <div className="bg-primary/5 px-6 py-4 border-b-2 border-primary/10">
                <h3 className="font-semibold text-primary uppercase text-sm tracking-wider">21 CFR Part 11 Electronic Signature</h3>
                <p className="text-xs text-muted-foreground mt-1 max-w-xl">
                  This signature is the legally binding equivalent of a handwritten signature (§11.1(b)). Once signed, the entry is locked against further editing (§11.10(c)).
                </p>
              </div>

              <div className="p-6 bg-card">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none">
                      Full Legal Name{' '}
                      <span className="text-muted-foreground font-normal text-xs ml-1">
                        {sigName && user?.full_name ? '(from login)' : '* required'}
                      </span>
                    </label>
                    <Input
                      value={sigName}
                      onChange={e => setSigName(e.target.value)}
                      readOnly={!!(sigName && user?.full_name)}
                      className={sigName && user?.full_name ? 'bg-muted/50' : ''}
                      placeholder="As it appears on official records"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none">
                      Title / Role{' '}
                      <span className="text-muted-foreground font-normal text-xs ml-1">
                        {sigTitle && user?.title ? '(from login)' : '* required'}
                      </span>
                    </label>
                    <Input
                      value={sigTitle}
                      onChange={e => setSigTitle(e.target.value)}
                      readOnly={!!(sigTitle && user?.title)}
                      className={sigTitle && user?.title ? 'bg-muted/50' : ''}
                      placeholder="e.g., Senior Research Scientist"
                    />
                  </div>
                  <div className="md:col-span-2 space-y-2">
                    <label className="text-sm font-medium leading-none">
                      Meaning of Signature <span className="text-destructive">*</span>{' '}
                      <span className="text-muted-foreground font-normal text-xs ml-1">(§11.50(a)(3))</span>
                    </label>
                    <select className={textareaClass} value={sigMeaning} onChange={e => setSigMeaning(e.target.value)}>
                      {SIGNATURE_MEANINGS.map(m => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {sigError && (
                  <div className="rounded-md border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive mb-6">
                    {sigError}
                  </div>
                )}

                <Button onClick={signEntry} disabled={signing} className="w-full h-12 text-base">
                  {signing ? 'Applying Signature...' : 'Apply Electronic Signature'}
                </Button>

                <p className="text-[10px] text-muted-foreground text-center uppercase tracking-widest mt-4 opacity-50">
                  Identity verified via JWT session token
                </p>
              </div>
            </div>
          )}
        </main>
      )}
    </Layout>
  )
}
