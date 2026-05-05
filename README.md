# Real Estate Investment Advisor — Spain

A tool that analyses any Spanish property listing URL and tells you whether the property is worth buying as an investment. Paste a link from Fotocasa or Pisos.com, and within ~30 seconds you get a full breakdown: rental income estimates, net yields, capital growth, and an investment score.

---

## What it does

1. You paste a property URL into the web app.
2. The backend scrapes the listing (using a headless browser + Claude AI extraction).
3. Three analyses run in parallel:
   - **STR revenue** — short-term rental income via AirROI API (occupancy, average daily rate)
   - **LTR revenue** — long-term monthly rent estimate via Claude AI
   - **Capital growth** — Spanish housing price index (INE) for the relevant region
4. The ROI engine calculates net yields and produces an **investment score from 0 to 10**.
5. Results appear in a React dashboard.

---

## Architecture

```
Browser (React + Vite)
    │
    │  POST /api/analysis { url }  →  returns run_id
    │  GET  /api/analysis/{run_id} →  polls for result
    │
FastAPI backend (Python 3.11, uv)
    │
    ├── LinkScraper (Playwright + Claude CLI + Nominatim)
    │
    ├── [parallel] AirROIAnalyzer   → STR revenue
    ├── [parallel] LTRAnalyzer      → LTR revenue
    └── [parallel] CapitalGrowthAnalyzer → YoY price growth
                │
            ROIAnalyzer → net yields, score, preferred rental type
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, shadcn-ui |
| Backend | FastAPI, Python 3.11, uv |
| Scraping | Playwright, playwright-stealth |
| AI extraction | Claude CLI (`claude -p` subprocess) |
| Charts | lightweight-charts |
| Data sources | AirROI API, INE REST API, Nominatim (OpenStreetMap) |

---

## Scoring logic

The investment score (0–10) is a weighted combination:

| Factor | Weight | Reference benchmark |
|---|---|---|
| Net rental yield | 50% | 10% reference yield |
| STR occupancy rate | 30% | 100% occupancy |
| Capital growth (YoY) | 20% | 8% reference growth |

---

## Getting started

### Requirements

- Python 3.11+
- Node.js 18+
- [`uv`](https://docs.astral.sh/uv/) (Python package manager)
- Claude CLI in your PATH (`claude`)
- AirROI API key

### 1. Clone the repo

```bash
git clone https://github.com/RichardGrom/Real_estate_analyses.git
cd Real_estate_analyses
```

### 2. Set up environment variables

Create a `.env` file in the project root:

```env
AIRROI_API_KEY=your_airroi_key_here
EXA_API_KEY=your_exa_key_here        # optional
APIFY_TOKEN=your_apify_token_here    # optional
```

### 3. Start the backend

```bash
cd backend
uv sync
uv run uvicorn src.main:app --reload --port 8000
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Usage

1. Go to the web app.
2. Paste a property listing URL (Fotocasa.es or Pisos.com recommended).
3. Click **Analyze**.
4. Wait ~30 seconds for the full analysis to complete.
5. Review the investment summary: yields, rental income, capital growth, score.

> **Note:** Idealista.com is currently blocked by their anti-bot system (DataDome). Use Fotocasa.es or Pisos.com instead.

---

## Running tests

```bash
cd backend
uv run pytest
```

Tests cover the scraper, all analyzers, ROI calculations, models, and config loading.

---

## Project structure

```
Real_estate_analyses/
├── backend/
│   ├── src/
│   │   ├── main.py                 # FastAPI app, API endpoints
│   │   ├── models.py               # Pydantic models
│   │   ├── config.py               # Configuration, .env loading
│   │   ├── scrapers/
│   │   │   ├── link_scraper.py     # Playwright + Claude + geocoding
│   │   │   └── claude_ltr_estimator.py
│   │   ├── analyzers/
│   │   │   ├── str_revenue.py      # AirROI API
│   │   │   ├── ltr_revenue.py      # LTR wrapper
│   │   │   ├── capital_growth.py   # INE housing price index
│   │   │   └── roi.py              # Yield calculation & scoring
│   │   └── reporters/
│   │       └── pipeline.py         # Pipeline orchestration
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/             # React components
│       ├── hooks/                  # useAnalysis polling hook
│       └── types/                  # TypeScript interfaces
├── docs/                           # Design documents
├── outputs/data/                   # Analysis results (JSON, gitignored)
└── .env                            # API keys (gitignored)
```

---

## Example output

A real analysis of a 2-bedroom apartment in Barcelona's Eixample district (€350,000) produced the following result. The full JSON is in [`docs/example/example_analysis.json`](docs/example/example_analysis.json).

### Property extracted from Fotocasa

| Field | Value |
|---|---|
| Address | Carrer del Consell de Cent 312, Eixample, Barcelona |
| Price | €350,000 |
| Size | 75 m² |
| Rooms / Bathrooms | 2 / 1 |
| Floor | 3rd |
| Terrace | Yes |

### Investment analysis

| Metric | STR (Airbnb) | LTR (long-term) |
|---|---|---|
| Annual revenue | €28,140 | €19,800 (€1,650/mo) |
| Gross yield | 8.04% | — |
| **Net yield** | **4.71%** | **3.63%** |

| | |
|---|---|
| Capital growth (Cataluña, 2024) | +8.2% YoY |
| Preferred rental type | **STR** |
| **Investment score** | **6.7 / 10** |

> Acquisition cost includes 10% transaction taxes (ITP + AJD + notary). Net yield deducts operating expenses, community fees, and IBI property tax.

---

## Known limitations

- Only tested thoroughly on **Fotocasa.es** (extracts 10/11 fields reliably)
- LTR rent estimates are AI-based, not sourced from live rental comps
- Capital growth data is at CCAA (regional) level, not city/neighbourhood level
- Results are stored in memory — restarting the server clears in-progress runs

---

## License

Private project. Not for redistribution.
