import { useEffect, useRef } from 'react'
import { createChart, LineSeries } from 'lightweight-charts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { PropertyResult } from '../types/analysis'

export function YieldChart({ properties }: { properties: PropertyResult[] }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current || properties.length === 0) return
    const chart = createChart(ref.current, { width: ref.current.clientWidth, height: 300 })
    const strSeries = chart.addSeries(LineSeries, { color: '#3b82f6' })
    const ltrSeries = chart.addSeries(LineSeries, { color: '#10b981' })

    const sorted = [...properties]
      .sort((a, b) => (b.str_net_yield_pct ?? 0) - (a.str_net_yield_pct ?? 0))
      .slice(0, 20)

    strSeries.setData(sorted.map((p, i) => ({ time: (i + 1) as unknown as import('lightweight-charts').Time, value: p.str_net_yield_pct ?? 0 })))
    ltrSeries.setData(sorted.map((p, i) => ({ time: (i + 1) as unknown as import('lightweight-charts').Time, value: p.ltr_net_yield_pct ?? 0 })))
    chart.timeScale().fitContent()
    return () => chart.remove()
  }, [properties])

  return (
    <Card>
      <CardHeader>
        <CardTitle>STR vs LTR Net Yield</CardTitle>
        <p className="text-xs text-muted-foreground">Blue = STR · Green = LTR · Top 20 properties by STR yield</p>
      </CardHeader>
      <CardContent><div ref={ref} /></CardContent>
    </Card>
  )
}
