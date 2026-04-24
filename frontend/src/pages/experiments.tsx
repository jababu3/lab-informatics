import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import Layout from '@/components/Layout'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Experiment = {
  _id: string;
  title: string;
  description: string;
  status: string;
  assay_type: string;
  target?: string;
  compound_ids?: string[];
}

export default function Experiments() {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/experiments/`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        setExperiments(data.experiments || [])
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
            <h1 className="text-3xl font-bold tracking-tight mb-2">Experiments</h1>
            <p className="text-muted-foreground text-sm">Track active assays and view experiment status.</p>
          </div>
          <Button variant="outline">New Experiment</Button>
        </div>

        {loading ? (
          <div className="flex justify-center p-12">
            <p className="text-sm text-muted-foreground animate-pulse">Loading experiments...</p>
          </div>
        ) : experiments.length === 0 ? (
          <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed text-center mt-8">
            <div className="mx-auto flex max-w-[420px] flex-col items-center justify-center text-center">
              <h2 className="mt-6 text-xl font-semibold">No experiments created</h2>
              <p className="mb-8 mt-2 text-center text-sm font-normal leading-6 text-muted-foreground">
                You don't have any experiments logged yet. Use the API or the button below to initialize an assay.
              </p>
              <a href={`${API}/docs`} target="_blank" rel="noopener noreferrer">
                <Button>View API Docs</Button>
              </a>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6">
            {experiments.map(exp => (
              <div
                key={exp._id}
                className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 flex flex-col justify-between"
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-semibold text-xl tracking-tight mb-1">{exp.title}</h3>
                    <p className="text-muted-foreground text-sm">{exp.description}</p>
                  </div>
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    exp.status === 'complete'
                      ? 'bg-secondary text-secondary-foreground'
                      : 'border border-border text-muted-foreground'
                  }`}>
                    {exp.status.toUpperCase()}
                  </span>
                </div>

                <div className="mt-4 pt-4 border-t flex flex-wrap gap-x-8 gap-y-4 text-sm text-muted-foreground">
                  <div className="flex flex-col">
                    <span className="font-medium text-foreground">Assay Type</span>
                    <span>{exp.assay_type}</span>
                  </div>
                  {exp.target && (
                    <div className="flex flex-col">
                      <span className="font-medium text-foreground">Target</span>
                      <span>{exp.target}</span>
                    </div>
                  )}
                  <div className="flex flex-col">
                    <span className="font-medium text-foreground">Compounds</span>
                    <span>{exp.compound_ids?.length || 0} tested</span>
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
