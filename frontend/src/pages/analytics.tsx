import Layout from '@/components/Layout'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const MODULES = [
  {
    title: 'QSAR Modeling',
    description: 'Train predictive models using Random Forest or Linear Regression algorithms.',
    endpoint: '/analytics/qsar/train'
  },
  {
    title: 'Dose-Response Curves',
    description: 'Fit 4-parameter logistic curves to calculate IC50 values across assays.',
    endpoint: '/analytics/dose-response/fit'
  },
  {
    title: 'Similarity Search',
    description: 'Find similar compounds out of the main database using Tanimoto similarity.',
    endpoint: '/similarity/search'
  }
]

export default function Analytics() {
  return (
    <Layout>
      <main className="container mx-auto px-6 py-12 max-w-5xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Analytics</h1>
          <p className="text-muted-foreground text-sm">Train predictive models and run computational modules.</p>
        </div>

        <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-8">
          <h2 className="text-xl font-semibold tracking-tight mb-6">Available Modules</h2>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {MODULES.map((item) => (
              <div
                key={item.title}
                className="flex flex-col justify-between rounded-lg border bg-muted/30 p-6 transition-colors hover:bg-muted/50"
              >
                <div>
                  <h3 className="font-semibold text-foreground mb-2">{item.title}</h3>
                  <p className="text-sm text-muted-foreground mb-6 leading-relaxed">{item.description}</p>
                </div>
                <div className="mt-auto">
                  <div className="rounded-md border bg-background px-3 py-2">
                    <code className="text-xs font-mono text-muted-foreground">
                      <span className="font-semibold text-foreground">POST</span> {item.endpoint}
                    </code>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 rounded-lg border bg-secondary/20 p-4 flex items-start gap-4">
            <div className="text-muted-foreground font-semibold">Docs</div>
            <p className="text-sm text-muted-foreground flex-1">
              Refer to the{' '}
              <a
                href={`${API}/docs`}
                className="font-medium underline underline-offset-4 text-foreground"
                target="_blank"
                rel="noopener noreferrer"
              >
                API Schema
              </a>
              {' '}for detailed payload parameters, dataset requirements, and response formatting for the computational analytics engine.
            </p>
          </div>
        </div>
      </main>
    </Layout>
  )
}
