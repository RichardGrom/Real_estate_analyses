import { useAnalysis } from './hooks/useAnalysis'
import { InvestmentForm } from './components/InvestmentForm'
import { ExecutiveSummary } from './components/ExecutiveSummary'
import { MarketOverview } from './components/MarketOverview'
import { PropertyTable } from './components/PropertyTable'
import { YieldChart } from './components/YieldChart'
import { RiskIndicators } from './components/RiskIndicators'

export default function App() {
  const { status, result, error, analyze } = useAnalysis()
  const isLoading = status === 'loading' || status === 'polling'

  return (
    <div className="min-h-screen bg-background text-foreground p-8 max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Real Estate Investment Advisor</h1>
      <p className="text-muted-foreground mb-8">Find STR and LTR investment properties in Spain</p>
      <InvestmentForm onSubmit={analyze} loading={isLoading} />
      {status === 'polling' && (
        <p className="text-sm text-muted-foreground mt-4 animate-pulse">
          Analyzing listings, STR revenue, LTR rentals, and capital growth…
        </p>
      )}
      {error && <p className="text-destructive mt-4">{error}</p>}
      {result?.status === 'completed' && (
        <div className="flex flex-col gap-6 mt-8">
          <ExecutiveSummary result={result} />
          <MarketOverview market={result.market} location={result.location} />
          <PropertyTable properties={result.properties} />
          <YieldChart properties={result.properties} />
          <RiskIndicators market={result.market} />
        </div>
      )}
    </div>
  )
}
