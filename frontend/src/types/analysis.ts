export interface AnalysisRequest {
  location: string
  budget_eur: number
  property_type: 'apartment' | 'house' | 'any'
  bedrooms: number
  min_size_m2: number
  parking: boolean
  terrace: boolean
  floor_preference?: 'ground' | 'low' | 'mid' | 'high' | 'top' | 'any'
  building_type?: 'new-build' | 'resale' | 'any'
  min_net_yield_pct?: number
  min_capital_growth_pct?: number
}

export interface Property {
  id: string
  address: string
  price_eur: number
  size_m2: number
  floor: string
  rooms: number
  url: string
  str_annual_revenue_eur: number | null
  str_gross_yield_pct: number | null
  str_net_yield_pct: number | null
  occupancy_rate_pct: number | null
  monthly_distributions: number[] | null
  ltr_monthly_rent_eur: number | null
  ltr_net_yield_pct: number | null
  preferred_rental_type: 'STR' | 'LTR' | null
  capital_growth_pct: number | null
  investment_score: number | null
  verdict: 'BUY' | 'WATCH' | 'SKIP'
}

export interface MarketData {
  yoy_appreciation_pct: number | null
  ccaa: string | null
  data_year: number | null
  vft_risk: 'low' | 'medium' | 'high' | null
  ltr_avg_rent_eur: number | null
  ltr_comparables: number | null
}

export interface AnalysisResult {
  run_id: string
  status: 'running' | 'completed' | 'failed'
  location: string
  criteria: Omit<AnalysisRequest, 'location'>
  generated_at: string
  total_scraped: number
  total_passing: number
  properties: Property[]
  market: MarketData | null
  error?: string
}
