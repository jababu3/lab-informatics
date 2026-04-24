import Link from 'next/link'
import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import Layout from '@/components/Layout'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const STATUS_STYLES: Record<string, { className: string; label: string }> = {
  draft:     { className: 'border-transparent bg-secondary text-secondary-foreground', label: 'Draft' },
  in_review: { className: 'border-transparent bg-primary text-primary-foreground', label: 'In Review' },
  signed:    { className: 'border-border text-foreground', label: 'Signed' },
}

type ELNEntry = {
  entry_id: string;
  title: string;
  status: string;
  author: string;
  author_title?: string;
  created_at: string;
  sections: any[];
  documents: any[];
  signature?: { signer_name: string; signed_at: string };
}

export default function ELNList() {
  const [entries, setEntries] = useState<ELNEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/eln/`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        setEntries(data.entries || [])
        setLoading(false)
      })
      .catch(e => {
        console.error(e)
        setLoading(false)
      })
  }, [])

  return (
    <Layout>
      <main className="container mx-auto px-6 py-12 max-w-5xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight mb-2">Electronic Lab Notebook</h1>
            <p className="text-muted-foreground text-sm">21 CFR Part 11 compliant records</p>
          </div>
          <Link href="/eln/new" passHref>
            <Button>New Entry</Button>
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center p-12">
            <p className="text-sm text-muted-foreground animate-pulse">Loading entries...</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed text-center mt-8">
            <div className="mx-auto flex max-w-[420px] flex-col items-center justify-center text-center">
              <h2 className="mt-6 text-xl font-semibold">No entries created</h2>
              <p className="mb-8 mt-2 text-center text-sm font-normal leading-6 text-muted-foreground">
                You don't have any ELN entries yet. Create an entry to start tracking your experiments.
              </p>
              <Link href="/eln/new" passHref>
                <Button>Create Entry</Button>
              </Link>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden">
            <div className="divide-y">
              {entries.map(entry => {
                const s = STATUS_STYLES[entry.status] || STATUS_STYLES.draft
                return (
                  <div key={entry.entry_id} className="p-6 flex flex-col sm:flex-row justify-between items-start gap-6 hover:bg-muted/50 transition-colors">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-3">
                        <Link href={`/eln/${entry.entry_id}`}>
                          <h3 className="font-semibold text-lg tracking-tight hover:underline cursor-pointer">
                            {entry.title}
                          </h3>
                        </Link>
                        <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors ${s.className}`}>
                          {s.label}
                        </span>
                      </div>

                      <div className="text-sm text-muted-foreground">
                        <span className="font-medium text-foreground">{entry.author}</span>
                        {entry.author_title && ` (${entry.author_title})`}
                        {' · '}{new Date(entry.created_at).toLocaleDateString()}
                      </div>

                      {((entry.sections?.length > 0) || (entry.documents?.length > 0)) && (
                        <div className="flex gap-3 text-xs text-muted-foreground pt-1">
                          {entry.sections?.length > 0 && (
                            <span>{entry.sections.length} Section{entry.sections.length !== 1 ? 's' : ''}</span>
                          )}
                          {entry.documents?.length > 0 && (
                            <span>{entry.documents.length} Attachment{entry.documents.length !== 1 ? 's' : ''}</span>
                          )}
                        </div>
                      )}

                      {entry.signature && (
                        <div className="inline-flex items-center gap-2 pt-2 text-xs font-medium text-foreground">
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                          Signed by {entry.signature.signer_name} on {new Date(entry.signature.signed_at).toLocaleDateString()}
                        </div>
                      )}
                    </div>

                    <div className="shrink-0 mt-2 sm:mt-0">
                      <Link href={`/eln/${entry.entry_id}`} passHref>
                        <Button variant="outline" size="sm" className="h-8">View details</Button>
                      </Link>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </main>
    </Layout>
  )
}
