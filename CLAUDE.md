# Real Estate Investment Advisor — Spain

## Purpose

A personalized investment advisor for buying real estate in Spain.
The user provides their location of interest, budget, and return expectations.
The system researches available properties, calculates STR revenue potential,
and evaluates whether each property meets the user's investment goals.

**Core question answered:** *"Given my budget and return expectations,
which properties in [location] are worth buying as an investment?"*

## User Input (required for each analysis)

| Parameter | Description | Example |
|---|---|---|
| `location` | City or area in Spain | Marbella, Estepona, Costa del Sol |
| `budget_eur` | Maximum purchase price | €320,000 |
| `min_net_yield_pct` | Minimum expected annual net yield | 5% |
| `min_capital_growth_pct` | Minimum expected annual capital appreciation | 3% |
| `property_type` | Type of property sought | apartment, house, any |
| `min_size_m2` | Minimum property size | 70 |

These parameters drive all filtering, scoring, and recommendations.
**There are no hardcoded investment criteria** — every analysis is user-specific.

## How It Works

```
User inputs budget + expectations
        ↓
Scrape Idealista listings in location (Apify)
        ↓
Fetch STR revenue estimate per property (AirROI)
        ↓
Calculate net yield, capital growth potential, investment score
        ↓
Filter: keep only properties meeting user's thresholds
        ↓
Dashboard: ranked property list with BUY / WATCH / SKIP verdict
```

## Scoring Logic

Each property receives an **investment score (0–10)** based on:
- Net yield vs. user's `min_net_yield_pct` target (40%)
- Capital growth potential vs. user's `min_capital_growth_pct` target (25%)
- STR occupancy rate (20%)
- Market liquidity (15%)

**Verdict:**
- `BUY` — meets or exceeds all user targets
- `WATCH` — meets yield target but not capital growth (or vice versa)
- `SKIP` — fails to meet user's minimum thresholds

## Hard Exclusions (Spain-specific, not user-configurable)

| Rule | Reason |
|---|---|
| No ground floor | Security and rental demand |
| Terrace required | Key STR rental factor in Spain |
| VFT license zone | Legal requirement for short-term rental |

## ROI Calculation

```
gross_yield    = (annual_str_revenue / purchase_price) * 100
acquisition    = purchase_price * 1.10  (+ 10% Spanish transaction costs: ITP + notary)
net_income     = annual_revenue - opex (25%) - community fees - IBI (property tax)
net_yield      = (net_income / acquisition) * 100
```

## Architecture

- **Backend:** FastAPI (Python 3.11, uv) in `backend/`
- **Frontend:** React + Vite + Tailwind CSS in `frontend/`
- **Agents:** `.claude/agents/` — 6 sub-agents orchestrated by `.claude/skills/analyze-market/`
- **Data:** JSON handoff files in `outputs/data/`

## Standards

Follow `0_instructions/.claude/CLAUDE.md` for all coding standards.
Python: `uv` exclusively. Frontend: React + shadcn-ui + lightweight-charts.

## Running

```bash
# Backend
cd backend && uv run uvicorn src.main:app --reload

# Frontend
cd frontend && npm run dev

# Full pipeline via Claude Code (includes market trend research)
claude "analyze Marbella budget 300000 yield 5% growth 4%"
```

## Two Execution Modes

| Mode | How | Market Trends |
|---|---|---|
| React UI (`http://localhost:5173`) | FastAPI pipeline | Not available |
| Claude Code (`claude "analyze ..."`) | Multi-agent pipeline | Available via WebSearch |

## Data Sources

| Source | Method | What it provides |
|---|---|---|
| Idealista (via Apify) | REST — Apify Actor | Listings: price, size, floor, location, images |
| AirROI | REST — `/api/v1/calculator` | STR revenue, occupancy rate, ADR |
| WebSearch (Claude agent) | Claude WebSearch | Price/m² history, market trends, VFT status |

## API Keys

Loaded from `.env` at project root — **never hardcode**.

```
APIFY_TOKEN=...
AIRROI_API_KEY=...
```

## Output Fields (every property in filtered output must contain)

`address`, `price_eur`, `size_m2`, `annual_revenue_eur`,
`gross_yield_pct`, `net_yield_pct`, `capital_growth_pct`, `investment_score`, `verdict`

## Agent Output Convention

- All agents write to `outputs/data/*.json`
- `filtered_properties.json` is the canonical dataset — only it feeds the dashboard
- Error log format: `logger.error("Context: %s | Status: %s | Body: %s", ctx, status, body)`
- Never silently skip API errors — always log with full context
