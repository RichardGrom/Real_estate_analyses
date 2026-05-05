# Real Estate Investment Advisor — Spain

## Purpose

A personalized investment advisor for buying real estate in Spain.
The user pastes a URL to a specific property listing; the system extracts all data from the page and returns a complete STR + LTR + capital growth investment analysis.

**Core question answered:** *"Is this specific property worth buying as an investment?"*

## How It Works

```
URL (any Spanish listing site)
 └─► LinkScraper (Playwright + claude -p + Nominatim)
       └─► ExtractedListing: {price_eur, size_m2, rooms, bathrooms,
                              address, lat, lng, has_terrace, has_parking,
                              floor, description}
             ├─► AirROIAnalyzer   → str_annual_revenue_eur, occupancy_pct
             ├─► LTRAnalyzer      → ltr_monthly_rent_eur, ltr_net_yield_pct
             ├─► CapitalGrowthAnalyzer → yoy_appreciation_pct, ccaa, data_year
             └─► ROIAnalyzer      → str_net_yield_pct, ltr_net_yield_pct,
                                     preferred_rental_type, investment_score
```

**API flow:**
```
POST /api/analysis {url} → {run_id} (202 Accepted)
        ↓ (background thread)
     pipeline runs...
        ↓
GET /api/analysis/{run_id} → React dashboard (single property card)
```

## Input Model

```python
class PropertyUrlRequest(BaseModel):
    url: str = Field(..., min_length=10)
```

No budget, no location, no filter thresholds — URL only.

## LinkScraper

`backend/src/scrapers/link_scraper.py`

Three-step extraction:
1. **Playwright** — headless Chromium, cookie consent dismissed, `document.body.innerText` extracted
2. **`claude -p`** — subprocess call extracts structured JSON from page text
3. **Nominatim** — OpenStreetMap geocoding fallback if GPS not found in page source

```python
class LinkScraper:
    def scrape(self, url: str) -> dict:  # returns ExtractedListing dict
```

Tested on Fotocasa.es — **10/11 fields** extracted, ~23s, $0 cost.
**Idealista.com is blocked by DataDome** — use Fotocasa.es or Pisos.com.

Error handling:
- Page text < 200 chars → `ScraperError("blocked")`
- `claude -p` non-zero exit → `ScraperError("extraction_failed")`
- Nominatim no result → `lat`/`lng` remain null, AirROI skipped with warning

## Scoring Logic

Each property receives an **investment score (0–10)**:
- STR/LTR net yield / 10% reference (50%) — capped at 1.0
- STR occupancy rate (30%) — capped at 1.0
- Capital growth / 8% reference (20%) — capped at 1.0

**No BUY/WATCH/SKIP verdict** — user sees raw numbers and decides.

## ROI Calculation

```
# STR
acquisition         = price_eur * 1.10          (ITP/IVA + AJD + notary)
community_fees_yr   = community_fee_month * 12   (from listing or default 150/mo)
ibi_yr              = price_eur * 0.60 * 0.005
net_income_str      = annual_str_revenue * (1 - STR_OPEX_PCT) - community_fees_yr - ibi_yr
str_net_yield_pct   = (net_income_str / acquisition) * 100

# LTR
annual_ltr_revenue  = avg_monthly_rent * 12
net_income_ltr      = annual_ltr_revenue * (1 - LTR_OPEX_PCT) - community_fees_yr - ibi_yr
ltr_net_yield_pct   = (net_income_ltr / acquisition) * 100
```

## Architecture

- **Backend:** FastAPI (Python 3.11, uv) in `backend/`
- **Frontend:** React + Vite + Tailwind + shadcn-ui in `frontend/`
- **MCP:** `.claude/mcp.json` — Exa.ai (market reports), Playwright (fallback)
- **Data:** JSON handoff files in `outputs/data/`

## Data Sources

| Source | Method | What it provides |
|---|---|---|
| LinkScraper | Playwright + `claude -p` + Nominatim | Property fields from any listing page |
| AirROI | REST GET — `api.airroi.com/calculator/estimate` | STR occupancy (0–1), ADR |
| Idealista (via Apify MCP) | MCP — `igolaizola~idealista-scraper` | LTR rental listings: avg rent/m² |
| INE REST API | REST GET — `servicios.ine.es/wstempus/js/es/DATOS_TABLA/49300` | IPV housing price index YoY by CCAA |
| Exa.ai MCP | MCP — `mcp.exa.ai` | VFT regulations, market reports |

**Note on Idealista:** The `igolaizola~idealista-scraper` Apify actor requires an active rental (~€5/month). It is used only for **LTR rental listings** (not for sale listings — those come via LinkScraper).

## Standards

Follow `0_instructions/.claude/CLAUDE.md` for all coding standards.
Python: `uv` exclusively. Frontend: React + shadcn-ui.

## Running

```bash
# Backend
cd backend && uv run uvicorn src.main:app --reload

# Frontend
cd frontend && npm run dev
# Open http://localhost:5173 — paste a Fotocasa/Pisos.com URL, click Analyze
```

## API Keys

Loaded from `.env` at project root — **never hardcode**.

```
APIFY_TOKEN=...
AIRROI_API_KEY=...
EXA_API_KEY=...
```

## Output Fields (single property result)

`id`, `url`, `address`, `price_eur`, `size_m2`, `rooms`, `bathrooms`,
`has_terrace`, `has_parking`, `floor`, `lat`, `lng`,
`str_annual_revenue_eur`, `str_gross_yield_pct`, `str_net_yield_pct`, `occupancy_rate_pct`,
`ltr_monthly_rent_eur`, `ltr_annual_revenue_eur`, `ltr_net_yield_pct`,
`preferred_rental_type`, `capital_growth_pct`, `investment_score`

`ltr_annual_revenue_eur` = `ltr_monthly_rent_eur * 12` (computed in ROIAnalyzer).

## Removed from Original Design

| Removed | Reason |
|---|---|
| `UserCriteria` / `AnalysisRequest` | Replaced by `PropertyUrlRequest` |
| `IdealistaScraper.scrape()` (sale listings) | Replaced by `LinkScraper` |
| `PropertyFilter` | Not needed — single property, no filtering |
| `verdict` (BUY/WATCH/SKIP) | Removed — user sees raw numbers |
| `min_net_yield_pct`, `min_capital_growth_pct` inputs | No longer part of input model |
| 8-field search form | Replaced by single URL input |

## Known Bugs Fixed

### subprocess `claude -p` — stdin hang
All `subprocess.run(["claude", "-p", ...])` calls **must** include `stdin=subprocess.DEVNULL`.
Without it, the CLI waits 3 s for stdin before proceeding, which causes silent failures inside `ThreadPoolExecutor` threads (LTR returns N/A, scraper extraction unreliable).
Affected files: `backend/src/scrapers/link_scraper.py`, `backend/src/scrapers/claude_ltr_estimator.py`.

### `listing.get("address", "")` vs `or ""`
`dict.get(key, default)` only uses the default when the key is **absent**. If the scraper returns `address: null`, `.get("address", "")` still returns `None` → `NoneType.split()` crash in `_extract_city`.
Always use `listing.get("address") or ""` for nullable string fields passed to string methods.
Affected file: `backend/src/reporters/pipeline.py`.

### `price_eur` None — cryptic TypeError
If scraping fails to extract the price, `ROIAnalyzer.compute_property` raised a generic `TypeError`.
Now raises `ValueError("price_eur is missing from listing")` immediately.
Affected file: `backend/src/analyzers/roi.py`.

### uvicorn must be started with `--reload`
Running uvicorn without `--reload` means code changes are not picked up without a manual restart.
Always start with: `uv run uvicorn src.main:app --reload --port 8000`.

## Agent Output Convention

- All agents write to `outputs/data/*.json`
- `{run_id}_listing.json` — raw extracted listing
- `{run_id}_result.json` — final property + ROI + market data
- Error log format: `logger.error("Context: %s | Status: %s | Body: %s", ctx, status, body)`
- Never silently skip API errors — always log with full context
