import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import type { AnalysisRequest } from '../types/analysis'

interface Props { onSubmit: (req: AnalysisRequest) => void; loading: boolean }

export function InvestmentForm({ onSubmit, loading }: Props) {
  const [form, setForm] = useState<AnalysisRequest>({
    location: '', budget_eur: 320000, property_type: 'any',
    bedrooms: 2, min_size_m2: 70, parking: false, terrace: false,
  })

  const set = (key: keyof AnalysisRequest) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const numInt = ['budget_eur', 'min_size_m2', 'bedrooms']
      const numFloat = ['min_net_yield_pct', 'min_capital_growth_pct']
      const bools = ['parking', 'terrace']
      let value: string | number | boolean | undefined = e.target.value
      if (numInt.includes(key)) value = parseInt(e.target.value) || 0
      else if (numFloat.includes(key)) value = e.target.value ? parseFloat(e.target.value) : undefined
      else if (bools.includes(key)) value = (e.target as HTMLInputElement).checked
      setForm(prev => ({ ...prev, [key]: value }))
    }

  return (
    <Card>
      <CardHeader><CardTitle>Investment Parameters</CardTitle></CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="col-span-2 sm:col-span-1">
          <Label>Location</Label>
          <Input placeholder="Marbella" value={form.location} onChange={set('location')} />
        </div>
        <div>
          <Label>Max Budget (€)</Label>
          <Input type="number" value={form.budget_eur} onChange={set('budget_eur')} />
        </div>
        <div>
          <Label>Bedrooms</Label>
          <Input type="number" value={form.bedrooms} onChange={set('bedrooms')} />
        </div>
        <div>
          <Label>Min Size (m²)</Label>
          <Input type="number" value={form.min_size_m2} onChange={set('min_size_m2')} />
        </div>
        <div>
          <Label>Min Net Yield (%)</Label>
          <Input type="number" step="0.5" placeholder="5.0" onChange={set('min_net_yield_pct')} />
        </div>
        <div>
          <Label>Min Capital Growth (%/yr)</Label>
          <Input type="number" step="0.5" placeholder="3.0" onChange={set('min_capital_growth_pct')} />
        </div>
        <div>
          <Label>Property Type</Label>
          <select className="w-full border rounded px-3 py-2 bg-background text-sm"
                  value={form.property_type} onChange={set('property_type')}>
            <option value="any">Any</option>
            <option value="apartment">Apartment</option>
            <option value="house">House</option>
          </select>
        </div>
        <div className="flex items-center gap-4 col-span-2 sm:col-span-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.parking} onChange={set('parking')} />
            Parking required
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.terrace} onChange={set('terrace')} />
            Terrace required
          </label>
        </div>
        <div className="col-span-2 sm:col-span-3 flex justify-end">
          <Button onClick={() => onSubmit(form)} disabled={loading || !form.location.trim()}>
            {loading ? 'Analyzing…' : 'Find Investments'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
