export interface PropertyUrlRequest {
  url: string
}

export interface PropertyResult {
  id: string
  url: string
  address: string
  price_eur: number
  size_m2: number
  rooms: number
  bathrooms: number
  has_terrace: boolean
  has_parking: boolean
  floor: string | null
  description: string | null
  lat: number | null
  lng: number | null
  str_annual_revenue_eur: number | null
  str_gross_yield_pct: number | null
  str_net_yield_pct: number | null
  occupancy_rate_pct: number | null
  ltr_monthly_rent_eur: number | null
  ltr_annual_revenue_eur: number | null
  ltr_net_yield_pct: number | null
  preferred_rental_type: 'STR' | 'LTR' | null
  capital_growth_pct: number | null
  investment_score: number | null
}

export interface MarketData {
  yoy_appreciation_pct: number | null
  ccaa: string | null
  data_year: number | null
  ltr_avg_rent_eur: number | null
  ltr_comparables: number | null
}

export interface AnalysisResult {
  run_id: string
  status: 'running' | 'completed' | 'failed'
  url: string
  generated_at: string
  property: PropertyResult | null
  market: MarketData | null
  error?: string
}
