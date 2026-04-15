# Real Estate Investment Analyzer

## Purpose

Evaluate investment potential of apartments, flats, and houses based on location.
The system scrapes property listings via Apify (Idealista), fetches short-term rental
revenue estimates via AirROI, and calculates ROI metrics to support buy/skip decisions.

Core question answered: **"Is this property worth buying as an investment in this location?"**

## Standards

Follow `0_instructions/.claude/CLAUDE.md` for all coding standards.
Python: `uv` exclusively. Frontend: React + shadcn-ui + lightweight-charts.

## Architecture

- **Backend:** FastAPI (Python 3.11, uv) in `backend/`
- **Frontend:** React + Vite + Tailwind CSS in `frontend/`
- **Agents:** `.claude/agents/` — 6 sub-agents orchestrated by `.claude/skills/analyze-market/`
- **Data:** JSON handoff files in `outputs/data/`

## Running

```bash
# Backend
cd backend && uv run uvicorn src.main:app --reload

# Frontend
cd frontend && npm run dev

# Full pipeline via Claude Code (includes market trend research)
claude "analyze Marbella"
```

## Two Execution Modes

| Mode | How | Market Trends |
|---|---|---|
| React UI (`http://localhost:5173`) | FastAPI pipeline | Not available (Python only) |
| Claude Code (`claude "analyze X"`) | Multi-agent pipeline | Available via WebSearch |

When market data is absent, the dashboard displays a notice:
*"Market trend data requires running via `claude "analyze [location]"`"*

## Data Sources

| Source | Method | What it provides |
|---|---|---|
| Idealista (via Apify) | REST — Apify Actor | Property listings: price, size, floor, location, images |
| AirROI | REST — `/api/v1/calculator` | STR revenue estimate, occupancy rate, ADR |
| WebSearch (Claude agent) | Claude WebSearch tool | Historical price/m², market trends, VFT regulatory status |

## Investment Evaluation Criteria (Costa del Sol)

| Parameter | Value | Hard filter |
|---|---|---|
| Max purchase price | €320,000 | Yes |
| Min area | 70 m² + terrace | Yes |
| Min net yield | 5% | Yes |
| VFT license zone | Required | Yes |
| Ground floor | Forbidden | Yes |

Properties not meeting **all** hard filters are excluded before output.

## ROI Calculation

```
gross_yield    = (annual_revenue / purchase_price) * 100
acquisition    = purchase_price * 1.10  (+ 10% transaction costs)
net_income     = annual_revenue - opex (25%) - community fees - IBI
net_yield      = (net_income / acquisition) * 100
```

## Output Fields (every property in filtered output must contain)

`address`, `price_eur`, `size_m2`, `annual_revenue_eur`, `gross_yield_pct`, `net_yield_pct`, `investment_score`

## API Keys

Loaded from `.env` at project root — **never hardcode**.

```
APIFY_TOKEN=...
AIRROI_API_KEY=...
```

## Agent Output Convention

- All agents write to `outputs/data/*.json`
- `filtered_properties.json` is the canonical dataset — only it feeds the dashboard
- Error log format: `logger.error("Context: %s | Status: %s | Body: %s", ctx, status, body)`
- Never silently skip API errors — always log with full context
