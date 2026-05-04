import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import type { PropertyUrlRequest } from '../types/analysis'

interface Props { onSubmit: (req: PropertyUrlRequest) => void; loading: boolean }

export function InvestmentForm({ onSubmit, loading }: Props) {
  const [url, setUrl] = useState('')

  return (
    <Card>
      <CardHeader><CardTitle>Property URL</CardTitle></CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div>
          <Label>Paste a listing URL (Fotocasa, Idealista, Pisos.com…)</Label>
          <Input
            placeholder="https://www.fotocasa.es/es/comprar/…"
            value={url}
            onChange={e => setUrl(e.target.value)}
          />
        </div>
        <div className="flex justify-end">
          <Button onClick={() => onSubmit({ url })} disabled={loading || url.trim().length < 10}>
            {loading ? 'Analyzing…' : 'Analyze Property'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
