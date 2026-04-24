import Link from 'next/link'
import { useState, useEffect } from 'react'
import { useAuth } from './_app'
import { Button } from '@/components/ui/button'
import Layout from '@/components/Layout'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type HealthStatus = {
  status: string;
  rdkit: boolean;
  // NOTE: field name comes from the API health endpoint.
  // If the backend is refactored to PostgreSQL-only, update this key.
  database: boolean;
} | null

type SummaryStats = {
  compounds?: { total: number };
  experiments?: { total: number };
} | null

export default function Home() {
  const { user } = useAuth()
  const [health, setHealth] = useState<HealthStatus>(null)
  const [summary, setSummary] = useState<SummaryStats>(null)

  useEffect(() => {
    fetch(`${API_BASE}/health`, { credentials: 'include' })
      .then(r => r.json())
      // Normalize the field name from the API response.
      .then(data => setHealth({ ...data, database: data.database ?? data.mongodb ?? false }))
      .catch(e => console.error(e))

    fetch(`${API_BASE}/analytics/summary`, { credentials: 'include' })
      .then(r => r.json())
      .then(setSummary)
      .catch(e => console.error(e))
  }, [])

  return (
    <Layout>
      <main className="container mx-auto px-6 py-16 md:py-24">

        {/* Hero Section */}
        <div className="mx-auto max-w-[800px] text-center mb-16">
          <div className="inline-flex items-center rounded-lg bg-muted px-3 py-1 text-sm font-medium mb-6">
            Version 1.0
          </div>
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight mb-6">
            Lab Informatics System
          </h1>
          <p className="max-w-[600px] mx-auto text-lg text-muted-foreground mb-8">
            A comprehensive, compliant framework for managing compounds, tracking experiments, and running analytics. Custom-built for precision and scale.
          </p>
          <div className="flex justify-center gap-4">
            <Link href="/eln" passHref>
              <Button className="h-10 px-8">Open Notebook</Button>
            </Link>
            <Link href="/compounds" passHref>
              <Button variant="outline" className="h-10 px-8">Browse Compounds</Button>
            </Link>
          </div>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">

          {/* Status Card */}
          <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 flex flex-col justify-between h-full">
            <div className="space-y-1">
              <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">System Status</h3>
              <p className="text-3xl font-bold tracking-tight">
                {health?.status === 'healthy' ? 'Online' : 'Offline'}
              </p>
            </div>
            {health && (
              <div className="mt-4 pt-4 border-t flex flex-col gap-2 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>RDKit Engine</span>
                  <span className={health.rdkit ? 'text-foreground font-medium' : ''}>
                    {health.rdkit ? 'Connected' : 'Unavailable'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Database</span>
                  <span className={health.database ? 'text-foreground font-medium' : ''}>
                    {health.database ? 'Connected' : 'Unavailable'}
                  </span>
                </div>
              </div>
            )}
          </div>

          <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 flex flex-col justify-between h-full">
            <div className="space-y-1">
              <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">Total Compounds</h3>
              <p className="text-4xl font-bold tracking-tight">
                {summary?.compounds?.total || 0}
              </p>
            </div>
            <div className="mt-4 pt-4 border-t flex items-center justify-between">
              <p className="text-xs text-muted-foreground">Registered standard molecules</p>
              <Link href="/compounds" className="text-xs font-medium underline underline-offset-4">View All</Link>
            </div>
          </div>

          <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 flex flex-col justify-between h-full">
            <div className="space-y-1">
              <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">Total Experiments</h3>
              <p className="text-4xl font-bold tracking-tight">
                {summary?.experiments?.total || 0}
              </p>
            </div>
            <div className="mt-4 pt-4 border-t flex items-center justify-between">
              <p className="text-xs text-muted-foreground">Active assay instances</p>
              <Link href="/experiments" className="text-xs font-medium underline underline-offset-4">View All</Link>
            </div>
          </div>
        </div>

        {/* Feature List */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="rounded-xl border bg-card text-card-foreground p-8">
            <h3 className="font-semibold text-lg tracking-tight mb-4">Quick Start</h3>
            <ul className="space-y-3 text-sm text-muted-foreground">
              <li>1. View and add molecules in Compounds.</li>
              <li>2. Record raw observations in ELN.</li>
              <li>3. Create and track assays in Experiments.</li>
              <li>4. Run QSAR models in Analytics.</li>
            </ul>
          </div>

          <div className="rounded-xl border bg-card text-card-foreground p-8">
            <h3 className="font-semibold text-lg tracking-tight mb-4">Compound Management</h3>
            <ul className="space-y-3 text-sm text-muted-foreground">
              <li>Add compounds using SMILES strings</li>
              <li>Auto-calculate chemical descriptors</li>
              <li>Verify Lipinski rule compliance</li>
              <li>Execute chemical similarity searches</li>
            </ul>
          </div>

          <div className="rounded-xl border bg-card text-card-foreground p-8">
            <h3 className="font-semibold text-lg tracking-tight mb-4">Deep Analytics</h3>
            <ul className="space-y-3 text-sm text-muted-foreground">
              <li>Deploy robust QSAR modeling pipelines</li>
              <li>Calculate dose-response curves</li>
              <li>Perform statistical analysis on trials</li>
              <li>Visualize complex property distributions</li>
            </ul>
          </div>
        </div>

      </main>
    </Layout>
  )
}
