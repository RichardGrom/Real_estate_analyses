import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { MarketData } from '../types/analysis'

const VFT_VARIANT = { low: 'default', medium: 'secondary', high: 'destructive' } as const

export function MarketOverview({ market, location }: { market: MarketData | null; location: string }) {
  if (!market) return null
  return (
    <Card>
      <CardHeader><CardTitle>Market — {location}</CardTitle></CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <p className="text-xs text-muted-foreground">Capital Growth (YoY)</p>
          <p className="text-xl font-bold">
            {market.yoy_appreciation_pct != null ? `${market.yoy_appreciation_pct.toFixed(1)}%` : '—'}
          </p>
          {market.data_year && <p className="text-xs text-muted-foreground">{market.ccaa} · {market.data_year}</p>}
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Avg LTR Rent</p>
          <p className="text-xl font-bold">
            {market.ltr_avg_rent_eur != null ? `€${market.ltr_avg_rent_eur.toLocaleString()}/mo` : '—'}
          </p>
          {market.ltr_comparables && <p className="text-xs text-muted-foreground">{market.ltr_comparables} comparables</p>}
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">VFT Regulatory Risk</p>
          {market.vft_risk
            ? <Badge variant={VFT_VARIANT[market.vft_risk]}>{market.vft_risk.toUpperCase()}</Badge>
            : <p className="text-sm text-muted-foreground">Run CLI for full analysis</p>}
        </div>
      </CardContent>
    </Card>
  )
}
