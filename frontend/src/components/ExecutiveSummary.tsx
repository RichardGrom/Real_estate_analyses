import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AnalysisResult } from '../types/analysis'

function fmt(n: number | null | undefined, decimals = 1, suffix = '') {
  if (n == null) return 'N/A'
  return n.toFixed(decimals) + suffix
}

export function ExecutiveSummary({ result }: { result: AnalysisResult }) {
  const p = result.property
  if (!p) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>{p.address}</CardTitle>
        <p className="text-sm text-muted-foreground">
          {p.size_m2} m² · {p.rooms} bed · {p.bathrooms} bath
          {p.floor ? ` · ${p.floor}` : ''}
          {p.has_terrace ? ' · Terrace' : ''}
          {p.has_parking ? ' · Parking' : ''}
        </p>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Metric label="Price" value={`€${p.price_eur.toLocaleString()}`} />
        <Metric label="STR Net Yield" value={fmt(p.str_net_yield_pct, 1, '%')} highlight />
        <Metric label="LTR Net Yield" value={fmt(p.ltr_net_yield_pct, 1, '%')} highlight />
        <Metric label="Preferred" value={p.preferred_rental_type ?? 'N/A'} />
        <Metric label="STR Revenue/yr" value={p.str_annual_revenue_eur ? `€${p.str_annual_revenue_eur.toLocaleString()}` : 'N/A'} />
        <Metric label="LTR Rent/mo" value={p.ltr_monthly_rent_eur ? `€${p.ltr_monthly_rent_eur.toLocaleString()}` : 'N/A'} />
        <Metric label="Capital Growth" value={fmt(p.capital_growth_pct, 1, '%/yr')} />
        <Metric label="Investment Score" value={p.investment_score != null ? `${p.investment_score}/10` : 'N/A'} highlight />
      </CardContent>
    </Card>
  )
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={`text-lg font-semibold ${highlight ? 'text-primary' : ''}`}>{value}</span>
    </div>
  )
}
