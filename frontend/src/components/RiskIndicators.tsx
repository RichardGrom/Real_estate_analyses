import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { MarketData } from '../types/analysis'

export function RiskIndicators({ market }: { market: MarketData | null }) {
  if (!market) return null
  return (
    <Card>
      <CardHeader><CardTitle>Risk Indicators</CardTitle></CardHeader>
      <CardContent className="flex gap-6 flex-wrap">
        <div>
          <p className="text-xs text-muted-foreground mb-1">VFT Regulatory</p>
          {market.vft_risk
            ? <Badge variant={market.vft_risk === 'low' ? 'default' : market.vft_risk === 'medium' ? 'secondary' : 'destructive'}>
                {market.vft_risk.toUpperCase()}
              </Badge>
            : <span className="text-sm text-muted-foreground">N/A — CLI only</span>}
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">Capital Growth Trend</p>
          <span className="text-sm font-medium">
            {market.yoy_appreciation_pct != null
              ? `${market.yoy_appreciation_pct > 5 ? '↑ Strong' : market.yoy_appreciation_pct > 2 ? '→ Moderate' : '↓ Slow'} (${market.yoy_appreciation_pct.toFixed(1)}%/yr)`
              : 'N/A'}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
