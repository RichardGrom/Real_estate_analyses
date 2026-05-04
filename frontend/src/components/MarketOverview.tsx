import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { MarketData } from '../types/analysis'

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
      </CardContent>
    </Card>
  )
}
