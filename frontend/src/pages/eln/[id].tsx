import Link from 'next/link'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { Button } from '@/components/ui/button'
import Layout from '@/components/Layout'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const STATUS_STYLES: Record<string, { className: string; label: string }> = {
  draft:     { className: 'border-transparent bg-secondary text-secondary-foreground', label: 'Draft' },
  in_review: { className: 'border-transparent bg-primary text-primary-foreground', label: 'In Review' },
  signed:    { className: 'border-border text-foreground', label: 'Signed' },
}

type AuditEvent = {
  action: string;
  actor: string;
  timestamp: string;
  detail?: string;
}

type Document = {
  doc_id: string;
  original_filename: string;
  size_bytes: number;
  uploaded_at: string;
}

type Section = {
  section_id?: string;
  section_type?: string;
  title?: string;
  content?: string;
}

type Signature = {
  signer_name: string;
  signer_title: string;
  meaning: string;
  signed_at: string;
  record_hash_at_signing?: string;
}

type ELNEntry = {
  entry_id: string;
  title: string;
  status: string;
  author: string;
  author_title?: string;
  created_at: string;
  objective?: string;
  experiment_id?: string;
  sections?: Section[];
  documents?: Document[];
  signature?: Signature;
  audit_log?: AuditEvent[];
}

export default function ELNViewer() {
  const router = useRouter()
  const { id } = router.query

  const [entry, setEntry]     = useState<ELNEntry | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)
  const [printMode, setPrintMode] = useState(false)

  useEffect(() => {
    if (!id) return
    fetch(`${API}/eln/${id}`, { credentials: 'include' })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(data => { setEntry(data); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [id])

  const handlePrint = () => {
    setPrintMode(true)
    setTimeout(() => { window.print(); setPrintMode(false) }, 100)
  }

  // Layout's hideHeader prop hides the nav during print.
  return (
    <Layout hideHeader={printMode}>
      {loading ? (
        <div className="flex justify-center p-12">
          <p className="text-sm text-muted-foreground animate-pulse">Loading entry...</p>
        </div>
      ) : error || !entry ? (
        <div className="flex min-h-[300px] flex-col items-center justify-center p-12 text-center">
          <p className="mb-4 text-destructive font-medium">
            {error === 'HTTP 404' ? 'ELN entry not found.' : `Error loading entry: ${error}`}
          </p>
          <Link href="/eln" passHref>
            <Button variant="outline">&larr; Back to ELN</Button>
          </Link>
        </div>
      ) : (() => {
        const status = STATUS_STYLES[entry.status] || STATUS_STYLES.draft
        const isSigned = entry.status === 'signed' && entry.signature

        return (
          <main className="container mx-auto px-6 py-8 max-w-4xl border-x min-h-screen">
            {!printMode && (
              <div className="mb-6 flex justify-between items-start">
                <Link href="/eln" className="text-sm text-muted-foreground hover:underline font-medium">
                  &larr; Back to ELN
                </Link>
                <div className="flex items-center gap-3">
                  <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${status.className}`}>
                    {status.label}
                  </span>
                  <Button variant="outline" size="sm" onClick={handlePrint}>
                    Print / Export
                  </Button>
                </div>
              </div>
            )}

            {/* ── Header ── */}
            <div className="mb-8 border-b pb-6">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">
                ELN Entry {printMode && `— ${status.label}`}
              </p>
              <h1 className="text-3xl font-bold tracking-tight mb-6">{entry.title}</h1>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
                <div>
                  <p className="text-muted-foreground text-xs font-medium uppercase tracking-wider mb-1">Author</p>
                  <p className="font-medium">{entry.author}</p>
                </div>
                {entry.author_title && (
                  <div>
                    <p className="text-muted-foreground text-xs font-medium uppercase tracking-wider mb-1">Title / Role</p>
                    <p className="font-medium">{entry.author_title}</p>
                  </div>
                )}
                <div>
                  <p className="text-muted-foreground text-xs font-medium uppercase tracking-wider mb-1">Date Created</p>
                  <p className="font-medium">{new Date(entry.created_at).toLocaleString()}</p>
                </div>
                {entry.experiment_id && (
                  <div>
                    <p className="text-muted-foreground text-xs font-medium uppercase tracking-wider mb-1">Linked Experiment</p>
                    <p className="font-medium font-mono">{entry.experiment_id}</p>
                  </div>
                )}
              </div>

              {entry.objective && (
                <div className="mt-6 pt-6 border-t">
                  <p className="text-muted-foreground text-xs font-medium uppercase tracking-wider mb-2">Objective</p>
                  <p className="text-sm leading-relaxed">{entry.objective}</p>
                </div>
              )}
            </div>

            {/* ── Content Sections ── */}
            {entry.sections && entry.sections.length > 0 && (
              <div className="mb-10 space-y-6">
                <h2 className="text-lg font-semibold tracking-tight border-b pb-2">Content</h2>
                {entry.sections.map((sec, idx) => (
                  <div key={sec.section_id || idx} className="rounded-lg border bg-card text-card-foreground shadow-sm">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b px-6 py-4 bg-muted/20 gap-2">
                      <h3 className="font-medium text-base">{sec.title || `Section ${idx + 1}`}</h3>
                      <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium bg-secondary/50 text-secondary-foreground capitalize">
                        {sec.section_type || 'Note'}
                      </span>
                    </div>
                    <div className="p-6">
                      <pre className="whitespace-pre-wrap break-words font-mono text-sm leading-relaxed bg-muted/30 p-4 rounded-md border">
                        {sec.content || <span className="text-muted-foreground italic">No content</span>}
                      </pre>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── Attachments ── */}
            {entry.documents && entry.documents.length > 0 && (
              <div className="mb-10 space-y-4">
                <h2 className="text-lg font-semibold tracking-tight border-b pb-2">
                  Attachments ({entry.documents.length})
                </h2>
                <div className="grid gap-3">
                  {entry.documents.map((doc) => (
                    <div key={doc.doc_id} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-lg border bg-card shadow-sm gap-4">
                      <div>
                        <p className="font-medium text-sm">{doc.original_filename}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {(doc.size_bytes / 1024).toFixed(1)} KB &middot; {new Date(doc.uploaded_at).toLocaleString()}
                        </p>
                      </div>
                      <a href={`${API}/eln/${entry.entry_id}/documents/${doc.doc_id}`} target="_blank" rel="noopener noreferrer">
                        <Button variant="secondary" size="sm">Download</Button>
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Signature Block ── */}
            {isSigned && entry.signature ? (
              <div className="mb-10 rounded-lg border-2 border-primary bg-primary/5 shadow-sm overflow-hidden">
                <div className="border-b-2 border-primary/20 bg-primary/10 px-6 py-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                  <h2 className="font-semibold text-primary uppercase tracking-wider text-sm flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    Electronic Signature (21 CFR Part 11)
                  </h2>
                  <span className="text-xs font-bold text-primary px-2 py-1 rounded bg-primary/20">LEGALLY BINDING</span>
                </div>
                <div className="p-6">
                  <div className="grid gap-4 text-sm max-w-2xl">
                    {([
                      ['Printed Name',      entry.signature.signer_name,  '§11.50(a)(1)'],
                      ['Title / Role',      entry.signature.signer_title, ''],
                      ['Meaning',           entry.signature.meaning,      '§11.50(a)(3)'],
                      ['Date & Time (UTC)', new Date(entry.signature.signed_at).toLocaleString('en-US', { timeZone: 'UTC', timeZoneName: 'short' }), '§11.50(a)(2)'],
                      ['Record Hash at Signing', entry.signature.record_hash_at_signing ? entry.signature.record_hash_at_signing.slice(0, 32) + '...' : '-', '§11.10(a)'],
                    ] as [string, string, string][]).map(([k, v, ref]) => (
                      <div key={k} className="grid grid-cols-1 sm:grid-cols-3 gap-1 sm:gap-4 py-2 border-b last:border-0 hover:bg-muted/10">
                        <span className="font-medium text-muted-foreground">{k}</span>
                        <span className="font-mono text-foreground sm:col-span-2 flex justify-between">
                          {v}
                          {ref && <span className="text-xs text-muted-foreground/60 ml-4 hidden sm:inline-block">{ref}</span>}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="mb-10 rounded-lg border border-dashed p-8 text-center bg-muted/30">
                <h3 className="font-semibold text-lg mb-2">Signature Pending</h3>
                <p className="text-muted-foreground text-sm max-w-md mx-auto mb-6">
                  This record has not yet been electronically signed. Signing locks the record against further edits and complies with 21 CFR Part 11.
                </p>
                <Link href={`/eln/new?resume=${entry.entry_id}`} passHref>
                  <Button>Sign Entry &rarr;</Button>
                </Link>
              </div>
            )}

            {/* ── Audit Trail ── */}
            {!printMode && entry.audit_log && entry.audit_log.length > 0 && (
              <div className="mb-10">
                <h2 className="text-lg font-semibold tracking-tight border-b pb-2 mb-6">Audit Trail (§11.10(e))</h2>
                <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-muted before:to-transparent">
                  {entry.audit_log.map((event, idx) => (
                    <div key={idx} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                      <div className={`flex items-center justify-center w-10 h-10 rounded-full border-4 border-background bg-secondary shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow-sm ${event.action === 'signed' ? 'bg-primary text-primary-foreground' : 'text-secondary-foreground'}`}>
                        {event.action === 'signed' ? (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                        ) : event.action === 'document_uploaded' ? (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                        ) : (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="16 3 21 8 8 21 3 21 3 16 16 3"/></svg>
                        )}
                      </div>
                      <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-lg border bg-card shadow-sm">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-semibold text-sm">{event.actor}</span>
                          <span className="font-mono text-[10px] text-muted-foreground">
                            {new Date(event.timestamp).toLocaleString('en-US', { timeZone: 'UTC', timeZoneName: 'short' })}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">{event.detail || event.action}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </main>
        )
      })()}
    </Layout>
  )
}
