import { useAnalysis } from './hooks/useAnalysis'
import { InvestmentForm } from './components/InvestmentForm'
import { ExecutiveSummary } from './components/ExecutiveSummary'
import { MarketOverview } from './components/MarketOverview'
import { YieldChart } from './components/YieldChart'

export default function App() {
  const { status, result, error, analyze } = useAnalysis()
  const isLoading = status === 'loading' || status === 'polling'

  return (
    <div className="min-h-screen bg-background text-foreground p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Real Estate Investment Advisor</h1>
      <p className="text-muted-foreground mb-8">Paste a listing URL to get a full STR + LTR + capital growth analysis</p>
      <InvestmentForm onSubmit={analyze} loading={isLoading} />
      {status === 'polling' && (
        <p className="text-sm text-muted-foreground mt-4 animate-pulse">
          Scraping listing, fetching STR revenue, LTR rentals, and capital growth data…
        </p>
      )}
      {error && <p className="text-destructive mt-4">{error}</p>}
      {result?.status === 'completed' && result.property && (
        <div className="flex flex-col gap-6 mt-8">
          <ExecutiveSummary result={result} />
          <MarketOverview market={result.market} location={result.property.address} />
          <YieldChart properties={[result.property]} />
        </div>
      )}
    </div>
  )
}
