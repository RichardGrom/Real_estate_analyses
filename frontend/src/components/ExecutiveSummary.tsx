import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AnalysisResult } from '../types/analysis'

const VARIANT = { BUY: 'default', WATCH: 'secondary', SKIP: 'destructive' } as const

export function ExecutiveSummary({ result }: { result: AnalysisResult }) {
  const top3 = [...result.properties]
    .sort((a, b) => (b.investment_score ?? 0) - (a.investment_score ?? 0))
    .slice(0, 3)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Results — {result.location}</CardTitle>
        <p className="text-sm text-muted-foreground">
          {result.total_passing} of {result.total_scraped} properties match criteria
          · Budget €{result.criteria.budget_eur.toLocaleString()}
          {result.criteria.min_net_yield_pct && ` · Yield ≥${result.criteria.min_net_yield_pct}%`}
          {result.criteria.min_capital_growth_pct && ` · Growth ≥${result.criteria.min_capital_growth_pct}%/yr`}
        </p>
      </CardHeader>
      <CardContent className="flex gap-4 flex-wrap">
        {top3.map(p => (
          <div key={p.id} className="flex flex-col gap-1 min-w-52">
            <Badge variant={VARIANT[p.verdict]}>{p.verdict}</Badge>
            <span className="text-sm font-medium truncate">{p.address}</span>
            <span className="text-xs text-muted-foreground">
              €{p.price_eur.toLocaleString()}
              · STR {p.str_net_yield_pct?.toFixed(1) ?? 'N/A'}%
              · LTR {p.ltr_net_yield_pct?.toFixed(1) ?? 'N/A'}%
              · Score {p.investment_score}/10
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
