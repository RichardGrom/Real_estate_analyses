import { useState, useRef } from 'react'
import type { PropertyUrlRequest, AnalysisResult } from '../types/analysis'

type Status = 'idle' | 'loading' | 'polling' | 'success' | 'error'

export function useAnalysis() {
  const [status, setStatus] = useState<Status>('idle')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current)
  }

  const analyze = async (req: PropertyUrlRequest) => {
    setStatus('loading')
    setError(null)
    try {
      const res = await fetch('/api/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      })
      if (!res.ok) throw new Error(`API error: ${res.status}`)
      const { run_id } = await res.json()
      setStatus('polling')
      pollRef.current = setInterval(async () => {
        const poll = await fetch(`/api/analysis/${run_id}`)
        const data: AnalysisResult = await poll.json()
        if (data.status === 'completed') {
          stopPolling()
          setResult(data)
          setStatus('success')
        } else if (data.status === 'failed') {
          stopPolling()
          setError(data.error ?? 'Analysis failed')
          setStatus('error')
        }
      }, 5000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setStatus('error')
    }
  }

  return { status, result, error, analyze }
}
