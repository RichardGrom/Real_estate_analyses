import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Property } from '../types/analysis'

const VERDICT_VARIANT = { BUY: 'default', WATCH: 'secondary', SKIP: 'destructive' } as const
const fmt = (n: number | null, suffix = '') => n != null ? `${n.toFixed(1)}${suffix}` : '—'

export function PropertyTable({ properties }: { properties: Property[] }) {
  const sorted = [...properties].sort((a, b) => (b.investment_score ?? 0) - (a.investment_score ?? 0))

  return (
    <Card>
      <CardHeader><CardTitle>Properties</CardTitle></CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground border-b">
              <th className="pb-2 pr-4">Address</th>
              <th className="pb-2 pr-4">Price</th>
              <th className="pb-2 pr-4">Size</th>
              <th className="pb-2 pr-4">STR Yield</th>
              <th className="pb-2 pr-4">LTR Yield</th>
              <th className="pb-2 pr-4">Growth</th>
              <th className="pb-2 pr-4">Score</th>
              <th className="pb-2">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(p => (
              <tr key={p.id} className="border-b last:border-0">
                <td className="py-2 pr-4">
                  <a href={p.url} target="_blank" rel="noreferrer"
                     className="hover:underline text-primary max-w-48 block truncate">
                    {p.address}
                  </a>
                </td>
                <td className="py-2 pr-4">€{p.price_eur.toLocaleString()}</td>
                <td className="py-2 pr-4">{p.size_m2} m²</td>
                <td className="py-2 pr-4 font-medium">{fmt(p.str_net_yield_pct, '%')}</td>
                <td className="py-2 pr-4 font-medium">{fmt(p.ltr_net_yield_pct, '%')}</td>
                <td className="py-2 pr-4">{fmt(p.capital_growth_pct, '%')}</td>
                <td className="py-2 pr-4">{fmt(p.investment_score)}/10</td>
                <td className="py-2">
                  <Badge variant={VERDICT_VARIANT[p.verdict]}>{p.verdict}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}
