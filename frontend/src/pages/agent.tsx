import Link from 'next/link'
import { useState, useEffect } from 'react'
import { useAuth } from './_app'
import { Button } from '@/components/ui/button'
import Layout from '@/components/Layout'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const EXP_TYPES = [
  { value: 'dose_response', label: 'Dose-Response',  desc: 'IC50 via PHERAstar plate reader' },
  { value: 'spr',           label: 'SPR Binding',    desc: 'KD / kon / koff kinetics' },
  { value: 'purity',        label: 'Purity Analysis', desc: 'HPLC-UV compound purity' },
  { value: 'flow',          label: 'Flow Cytometry',  desc: 'Cell viability & apoptosis' },
]

type AgentHealth = {
  simulator_available: boolean;
  ollama_available: boolean;
  ollama_model?: string;
}

type IC50Results  = Record<string, number>
type KDResults    = Record<string, { KD_nM: number }>
type PurityResult = Record<string, number>
type FlowResult   = Record<string, { live_pct?: number }>

type AgentRun = {
  status: 'success' | 'error' | 'running';
  experiment_type: string;
  started_at?: string;
  error?: string;
  posted?: boolean;
  entry_id?: string;
  analysis?: {
    ic50_results?:      IC50Results;
    kd_results?:        KDResults;
    purity_results?:    PurityResult;
    population_results?: FlowResult;
  };
}

function AnalysisCard({ result }: { result: AgentRun }) {
  const [expanded, setExpanded] = useState(false)

  const statusString = result.status === 'success' ? 'Success' : result.status === 'error' ? 'Error' : 'Running'

  const ic50   = result.analysis?.ic50_results      || {}
  const kd     = result.analysis?.kd_results         || {}
  const purity = result.analysis?.purity_results     || {}
  const flow   = result.analysis?.population_results || {}

  return (
    <div className="rounded-xl border bg-card text-card-foreground shadow-sm mb-4 overflow-hidden">
      {/* Header */}
      <div className="bg-muted/50 p-4 flex justify-between items-center border-b">
        <div>
          <span className="font-semibold text-sm tracking-tight text-foreground">
            {result.experiment_type?.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
          </span>
          <span className={`ml-3 inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
            result.status === 'success' ? 'border-transparent bg-secondary text-secondary-foreground'
            : result.status === 'error' ? 'border-destructive/20 bg-destructive/10 text-destructive'
            : 'border-border text-muted-foreground'
          }`}>
            {statusString}
          </span>
          <span className="ml-3 text-xs text-muted-foreground">
            {result.started_at ? new Date(result.started_at).toLocaleTimeString() : ''}
          </span>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setExpanded(x => !x)} className="h-8">
          {expanded ? 'Collapse' : 'Details'}
        </Button>
      </div>

      {/* Quick stats */}
      <div className="p-4 flex gap-8 flex-wrap">
        {result.status === 'error' && (
          <div className="text-sm font-medium text-destructive">Error: {result.error}</div>
        )}
        {Object.entries(ic50).map(([k, v]) => (
          <div key={k} className="flex flex-col">
            <strong className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">{k}</strong>
            <span className="font-mono text-lg font-bold text-foreground">IC50 {v.toFixed(3)} µM</span>
          </div>
        ))}
        {Object.entries(kd).map(([k, v]) => (
          <div key={k} className="flex flex-col">
            <strong className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">{k}</strong>
            <span className="font-mono text-lg font-bold text-foreground">KD {v.KD_nM.toFixed(1)} nM</span>
          </div>
        ))}
        {Object.entries(purity).map(([k, v]) => (
          <div key={k} className="flex flex-col">
            <strong className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">{k}</strong>
            <span className="font-mono text-lg font-bold text-foreground">{v.toFixed(1)}% purity</span>
          </div>
        ))}
        {Object.entries(flow).map(([k, v]) => (
          <div key={k} className="flex flex-col">
            <strong className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">{k}</strong>
            <span className="font-mono text-lg font-bold text-foreground">{v.live_pct?.toFixed(1)}% viable</span>
          </div>
        ))}
        {(!Object.keys(ic50).length && !Object.keys(kd).length && !Object.keys(purity).length && !Object.keys(flow).length && result.status !== 'error') && (
          <div className="text-sm text-muted-foreground">Standard trace completed.</div>
        )}
      </div>

      {/* ELN link */}
      {result.posted && result.entry_id && (
        <div className="px-4 pb-4">
          <Link href={`/eln/${result.entry_id}`} passHref>
            <Button variant="secondary" size="sm">
              View automatically generated ELN Entry
            </Button>
          </Link>
        </div>
      )}

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t p-4 bg-muted/20">
          <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap break-all m-0 max-h-[300px] overflow-y-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

export default function AgentPage() {
  const { user } = useAuth()
  const [agentHealth, setAgentHealth] = useState<AgentHealth | null>(null)
  const [selectedType, setSelectedType] = useState('dose_response')
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [running, setRunning] = useState(false)
  const [lastStatus, setLastStatus] = useState<AgentRun | null>(null)

  useEffect(() => {
    fetch(`${API}/agent/health`, { credentials: 'include' })
      .then(r => r.json())
      .then(setAgentHealth)
      .catch(console.error)
    fetch(`${API}/agent/status`, { credentials: 'include' })
      .then(r => r.json())
      .then(s => { if (s.status !== 'never_run') setLastStatus(s) })
      .catch(console.error)
  }, [])

  const triggerRun = async () => {
    if (running) return
    setRunning(true)
    try {
      const res = await fetch(`${API}/agent/run`, {
        credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          experiment_type: selectedType,
          author_name:  user?.username || 'agent_scientist',
          author_title: user?.title    || 'AI Research Scientist',
        })
      })
      const result = await res.json()
      setRuns(prev => [result, ...prev])
    } catch (e: any) {
      setRuns(prev => [{
        status: 'error',
        error: e.message,
        experiment_type: selectedType,
        started_at: new Date().toISOString()
      }, ...prev])
    } finally {
      setRunning(false)
    }
  }

  return (
    <Layout>
      <main className="container mx-auto px-6 py-12 max-w-5xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">AI Scientist Framework</h1>
          <p className="text-muted-foreground text-sm">
            Autonomous simulation, analysis, and ELN pipeline integration.
          </p>
        </div>

        {/* Status cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {[
            {
              label:  'Simulator Engine',
              status: agentHealth?.simulator_available,
              ok:     'lab-data-simulator verified',
              fail:   'Not installed'
            },
            {
              label:  'Ollama Integration',
              status: agentHealth?.ollama_available,
              ok:     agentHealth?.ollama_model || 'Connected',
              fail:   'Not reachable'
            },
            {
              label:  'Authentication Link',
              status: !!user,
              ok:     user?.role || 'Verified identity',
              fail:   'Not logged in'
            },
          ].map(card => (
            <div key={card.label} className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 flex flex-col justify-between">
              <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider mb-4">
                {card.label}
              </h3>
              <div className="flex items-center gap-2">
                <span className={`h-2.5 w-2.5 rounded-full ${card.status ? 'bg-secondary' : 'bg-destructive/60'}`} />
                <span className={`text-sm font-medium ${card.status ? 'text-foreground' : 'text-destructive'}`}>
                  {card.status ? card.ok : card.fail}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Trigger panel */}
        <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-8 mb-8">
          <h2 className="text-xl font-semibold tracking-tight mb-6">Initialize Hardware Simulation</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            {EXP_TYPES.map(t => (
              <button
                key={t.value}
                onClick={() => setSelectedType(t.value)}
                className={`flex flex-col text-left px-5 py-4 rounded-lg border transition-all ${
                  selectedType === t.value
                    ? 'border-foreground bg-foreground/5 shadow-md'
                    : 'border-border bg-transparent hover:border-muted-foreground/30 hover:bg-muted/30'
                }`}
              >
                <span className="font-semibold mb-1">{t.label}</span>
                <span className="text-xs text-muted-foreground">{t.desc}</span>
              </button>
            ))}
          </div>

          {!user && (
            <div className="rounded-md border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive mb-6 flex gap-3 items-center">
              <span className="font-bold">Authorization Warning:</span>
              <span>
                Must{' '}
                <Link href="/login"><span className="underline font-semibold cursor-pointer">Log in</span></Link>
                {' '}so the agent can post ELN entries securely. Unverified runs will not be saved.
              </span>
            </div>
          )}

          <Button onClick={triggerRun} disabled={running} className="h-10 px-8 w-full sm:w-auto">
            {running
              ? 'Processing Data Pipeline...'
              : `Run ${EXP_TYPES.find(t => t.value === selectedType)?.label} Pipeline`
            }
          </Button>
        </div>

        {/* Results */}
        {runs.length > 0 && (
          <div>
            <h2 className="text-xl font-semibold tracking-tight mb-4 border-b pb-4">
              Pipeline Output Log ({runs.length})
            </h2>
            {runs.map((r, i) => <AnalysisCard key={i} result={r} />)}
          </div>
        )}

        {runs.length === 0 && lastStatus && (
          <div>
            <h2 className="text-sm font-semibold tracking-tight text-muted-foreground uppercase mb-4">
              Last Local Output Node
            </h2>
            <AnalysisCard result={lastStatus} />
          </div>
        )}

        {runs.length === 0 && !lastStatus && (
          <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed text-center">
            <div className="mx-auto flex max-w-[420px] flex-col items-center justify-center text-center">
              <h2 className="mt-6 text-xl font-semibold">No simulation metrics detected</h2>
              <p className="mb-8 mt-2 text-center text-sm font-normal leading-6 text-muted-foreground">
                Select a hardware pipeline module and initialize it above.
              </p>
            </div>
          </div>
        )}
      </main>
    </Layout>
  )
}
