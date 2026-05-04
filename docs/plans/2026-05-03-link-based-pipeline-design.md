# Link-Based Pipeline — Design

**Date:** 2026-05-03
**Status:** Implemented

## Goal

Replace the search-based pipeline (location + budget parameters → list of listings) with a link-based pipeline: user provides one URL to a specific property listing, the system extracts all data from the page and returns a complete investment analysis.

## Spike Result

Approach C (Playwright + `claude -p` + Nominatim geocoding) validated on Fotocasa.es:
- 10/11 fields extracted correctly
- GPS acquired via Nominatim geocoding (OpenStreetMap, free)
- Cookie consent wall handled via button dismiss
- Total time: ~23s, cost: $0
- `claude` CLI at `/Users/richardgrom/.local/bin/claude` using subscription auth

## What Changes

| Layer | Before | After |
|---|---|---|
| Input model | `AnalysisRequest` (location, budget, 8 params) | `PropertyUrlRequest` (url: str) |
| Scraper | `IdealistaScraper` (Apify, paid) | `LinkScraper` (Playwright + claude -p, free) |
| GPS | from Apify response | page source scan → Nominatim fallback |
| Location for LTR/INE | `UserCriteria.location` | extracted from scraped listing address |
| Verdict | BUY/WATCH/SKIP (user thresholds) | removed — raw numbers only |
| Filter | filters list of listings | removed — single property |
| Output | list of properties | single property + full analysis |
| Frontend | 8-field form | single URL input |

## Pipeline After Change

```
URL
 └─► LinkScraper (Playwright + claude -p + Nominatim)
       └─► listing: {price_eur, size_m2, rooms, bathrooms, address, lat, lng,
                      has_terrace, has_parking, floor, description, location}
             ├─► AirROIAnalyzer   → str_annual_revenue_eur, str_net_yield_pct, occupancy_pct
             ├─► LTRAnalyzer      → ltr_monthly_rent_eur, ltr_net_yield_pct
             ├─► CapitalGrowthAnalyzer → yoy_appreciation_pct, ccaa, data_year
             └─► ROIAnalyzer      → str_net_yield_pct, ltr_net_yield_pct,
                                     preferred_rental_type, investment_score
```

## Output Fields (Dashboard)

| Field | Source |
|---|---|
| price_eur, size_m2, rooms, bathrooms | LinkScraper |
| address, lat, lng | LinkScraper + Nominatim |
| has_terrace, has_parking, floor | LinkScraper |
| str_annual_revenue_eur | AirROI API |
| str_net_yield_pct | ROIAnalyzer |
| ltr_monthly_rent_eur | LTR (Idealista rentals) |
| ltr_net_yield_pct | ROIAnalyzer |
| preferred_rental_type | ROIAnalyzer (higher yield wins) |
| yoy_appreciation_pct | INE IPV |
| investment_score (0–10) | ROIAnalyzer |

No verdict (BUY/WATCH/SKIP) — user sees raw numbers and decides.

## What Gets Removed

- `UserCriteria` dataclass (all search params)
- `AnalysisRequest` Pydantic model
- `PropertyFilter` class
- `min_net_yield_pct`, `min_capital_growth_pct` inputs
- `verdict` field from ROI output
- `IdealistaScraper.scrape()` (sale listings search)

## What Gets Added

- `backend/src/scrapers/link_scraper.py` — `LinkScraper` class
- `backend/src/models.py` — `PropertyUrlRequest`, `ExtractedListing`

## What Gets Modified

- `backend/src/models.py` — remove `UserCriteria`, `AnalysisRequest`
- `backend/src/reporters/pipeline.py` — use `LinkScraper` instead of `IdealistaScraper`
- `backend/src/main.py` — accept `PropertyUrlRequest` instead of `AnalysisRequest`
- `backend/src/analyzers/ltr_revenue.py` — accept `location: str` instead of `UserCriteria`
- `backend/src/analyzers/capital_growth.py` — no change (already accepts `location: str`)
- `backend/src/analyzers/roi.py` — remove `verdict`, remove `criteria` param
- `frontend/src/` — single URL input form, single result card

## LinkScraper Implementation

```python
class LinkScraper:
    def scrape(self, url: str) -> dict:
        # 1. Playwright: open URL, dismiss cookie consent, get page text
        # 2. claude -p: extract structured JSON from page text
        # 3. If lat/lng null: Nominatim geocoding from address
        # Returns: ExtractedListing dict
```

Cookie consent selectors (tested on Fotocasa):
```python
COOKIE_SELECTORS = [
    "#didomi-notice-agree-button", ".fc-cta-consent",
    "button:has-text('Aceptar')", "button:has-text('Accept')",
]
```

Extraction prompt extracts: `price_eur`, `size_m2`, `rooms`, `bathrooms`, `address`, `lat`, `lng`, `has_terrace`, `has_parking`, `floor`, `description`.

Location for LTR/INE derived from `address` field (city name extraction via claude -p or simple string split).

## Error Handling

- Page blocked / text < 200 chars → raise `ScraperError("blocked")`
- claude -p JSON parse fail → retry once, then raise `ScraperError("extraction_failed")`
- Nominatim returns no results → lat/lng remain null, AirROI skipped with warning
- AirROI null → STR fields null in output, LTR-only analysis proceeds
