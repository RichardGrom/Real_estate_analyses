# Real Estate Investment Analyzer — Multi-Agent System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a fully automated multi-agent real estate investment analysis system where the user inputs a location and receives a React web dashboard with capital value growth metrics, STR yield analysis, and per-property buy/skip recommendations.

**Architecture:** Two-layer system — outer layer uses Claude Code native skills/agents (`.claude/`) to orchestrate work in a fan-out/fan-in pattern; inner layer is a FastAPI backend (async) + React frontend. Agents coordinate, Python computes, React displays.

**Tech Stack:**
- Backend: Python 3.11, FastAPI, Uvicorn, uv (dependency manager), requests, python-dotenv, pandas
- Frontend: React, TypeScript, Vite, Tailwind CSS, shadcn-ui, lightweight-charts
- Data sources: Apify REST API (Idealista scraper), AirROI REST API
- Agents: Claude Code skills + agents

**Standards:** Follow `0_instructions/.claude/CLAUDE.md` — SOLID, < 20 lines per function, type hints (Python 3.10+), uv exclusively, no pip.

**Two execution modes (by design):**
- `claude "analyze Marbella"` → full pipeline including market trends (WebSearch via Claude agent)
- `http://localhost:5173` → property analysis only (no market trends — Python can't do WebSearch)
- Dashboard clearly labels which data is available in each mode

---

## Directory Structure (target state)

```
Real_estate_analyses/
├── CLAUDE.md                        (update in Task 0)
├── 0_instructions/                  (existing — standards reference)
├── .env                             (stays at root — loaded by backend/src/config.py)
├── .gitignore                       (update in Task 0)
│
├── backend/
│   ├── pyproject.toml               (uv managed — replaces root requirements.txt)
│   ├── .venv/                       (uv venv — gitignored)
│   └── src/
│       ├── main.py                  # FastAPI app — async with BackgroundTasks
│       ├── config.py                # env, criteria constants — loads ../.env
│       ├── scrapers/
│       │   ├── __init__.py
│       │   └── idealista.py         # Apify REST client
│       ├── analyzers/
│       │   ├── __init__.py
│       │   ├── str_revenue.py       # AirROI REST client (parallel)
│       │   └── roi.py               # gross/net yield, investment score
│       ├── filters/
│       │   ├── __init__.py
│       │   └── property_filter.py   # hard criteria enforcement
│       └── reporters/
│           └── pipeline.py          # sync pipeline — called in thread pool
│   └── tests/
│       ├── conftest.py              # sys.path setup
│       ├── test_config.py
│       ├── test_idealista.py
│       ├── test_str_revenue.py
│       ├── test_roi.py
│       └── test_filter.py
│
├── frontend/
│   ├── package.json                 (npm)
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── ExecutiveSummary.tsx
│       │   ├── MarketOverview.tsx   # lightweight-charts price trend
│       │   ├── PropertyTable.tsx    # sortable shadcn-ui table
│       │   ├── YieldChart.tsx       # lightweight-charts bar chart
│       │   └── RiskIndicators.tsx
│       ├── hooks/
│       │   └── useAnalysis.ts       # fetch + polling state management
│       └── types/
│           └── analysis.ts          # shared TypeScript types
│
├── outputs/
│   └── data/                        # JSON handoff files between agents
│
├── .claude/
│   ├── settings.json                (exists ✓)
│   ├── skills/
│   │   └── analyze-market/
│   │       └── SKILL.md             # orchestrator skill
│   └── agents/
│       ├── listings-scraper.md
│       ├── market-researcher.md
│       ├── str-analyst.md
│       ├── roi-calculator.md
│       ├── property-filter.md
│       └── report-builder.md
│
└── docs/
    └── plans/
        └── 2026-04-15-multi-agent-system.md  (this file ✓)
```

---

## Data Flow

```
                    ┌─ Apify → listings
FastAPI endpoint ───┤─ AirROI (parallel) → str_revenue   →  roi → filter → JSON response
                    └─ (no market data — Python only)

Claude agent ───────┌─ Apify → listings
"analyze Marbella"  ├─ AirROI (parallel) → str_revenue   →  roi → filter
                    └─ WebSearch → market_trends.json     → full dashboard
```

**FastAPI endpoints:**
- `POST /api/analysis` — starts analysis as background task, returns `{run_id, status: "running"}`
- `GET /api/analysis/{run_id}` — poll status: `running | completed | failed` + results when done
- `GET /api/health` — health check

---

## Prerequisites (before Task 1)

```bash
# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set git identity (fixes commit warnings)
git config user.name "Richard Grom"
git config user.email "your@email.com"
```

---

## Phase 0 — Cleanup & CLAUDE.md Update

### Task 0: Remove orphan files, update gitignore and CLAUDE.md

**Files:**
- Delete: `requirements.txt` (replaced by `backend/pyproject.toml`)
- Modify: `.gitignore`
- Modify: `CLAUDE.md`

**Step 1:** Remove `requirements.txt`:
```bash
git rm requirements.txt
```

**Step 2:** Replace `.gitignore` with:
```
# Environment
.env
.env.*

# Python
.venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/

# Node
node_modules/
dist/

# Build / outputs
outputs/data/*.json

# OS
.DS_Store
Thumbs.db
```

**Step 3:** Update `CLAUDE.md` to reflect current architecture:
```markdown
# Real Estate Investment Analyzer

## Purpose
Multi-agent system for scraping Spanish real estate listings + STR revenue analysis
for investment decisions on Costa del Sol.

## Standards
Follow `0_instructions/.claude/CLAUDE.md` for all coding standards.
Python: uv exclusively. Frontend: React + shadcn-ui + lightweight-charts.

## Architecture
- Backend: FastAPI (Python 3.11, uv) in `backend/`
- Frontend: React + Vite + Tailwind CSS in `frontend/`
- Agents: `.claude/agents/` — 6 sub-agents orchestrated by `.claude/skills/analyze-market/`

## Running
```bash
# Backend
cd backend && uv run uvicorn src.main:app --reload

# Frontend
cd frontend && npm run dev

# Full pipeline via Claude Code
claude "analyze Marbella"
```

## Two execution modes
- Via React UI (`http://localhost:5173`): property analysis only
- Via Claude Code (`claude "analyze Marbella"`): full pipeline including market trends

## Investment Criteria (Costa del Sol)
| Parameter       | Value         |
|-----------------|---------------|
| Max price       | €320,000      |
| Min area        | 70 m² + terrace |
| Min net yield   | 5%            |
| VFT license     | required      |
| Ground floor    | forbidden     |

## API Keys
Loaded from `.env` at project root — never hardcode.
- APIFY_TOKEN
- AIRROI_API_KEY

## Agent output convention
All agents write to `outputs/data/*.json`.
`filtered_properties.json` is the canonical dataset — only it feeds the dashboard.
Error log format: `logger.error("Context: %s | Status: %s | Body: %s", ctx, status, body)`
```

**Step 4:** Commit:
```bash
git add -A
git commit -m "chore: remove requirements.txt, update .gitignore and CLAUDE.md"
```

---

## Phase 1 — Backend Foundation

### Task 1: Project setup with uv

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/__init__.py` and all sub-package `__init__.py` files
- Create: `backend/tests/conftest.py`
- Create: `outputs/data/.gitkeep`

**Step 1:** Create `backend/pyproject.toml`:
```toml
[project]
name = "real-estate-analyzer"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "requests>=2.32.0",
    "python-dotenv>=1.0.0",
    "pandas>=2.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

> Note: No `[build-system]` section — this is an application, not a library.

**Step 2:** Set up uv environment:
```bash
cd backend
uv venv
source .venv/bin/activate
uv sync --extra dev
```
Expected: `.venv/` created, all packages installed.

**Step 3:** Create `backend/tests/conftest.py`:
```python
# Ensures `from src.X import Y` works in all tests
```
(Empty — `pythonpath = ["."]` in pyproject.toml handles path.)

**Step 4:** Create all empty `__init__.py`:
`backend/src/`, `backend/src/scrapers/`, `backend/src/analyzers/`, `backend/src/filters/`, `backend/src/reporters/`, `backend/tests/`

**Step 5:** Create `outputs/data/.gitkeep`

**Step 6:** Commit:
```bash
git add backend/ outputs/
git commit -m "chore: scaffold backend with uv, pyproject.toml, package structure"
```

---

### Task 2: `backend/src/config.py`

**Files:**
- Create: `backend/src/config.py`
- Create: `backend/tests/test_config.py`

**Step 1:** Write failing test `backend/tests/test_config.py`:
```python
import os
import pytest

def test_config_loads(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    monkeypatch.setenv("AIRROI_API_KEY", "test_key")
    from src.config import Config
    cfg = Config()
    assert cfg.apify_token == "test_token"
    assert cfg.airroi_api_key == "test_key"
    assert cfg.criteria.max_price_eur == 320_000

def test_config_raises_on_missing_key(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    monkeypatch.setenv("AIRROI_API_KEY", "test_key")
    from importlib import reload
    import src.config as m
    reload(m)
    with pytest.raises(ValueError, match="APIFY_TOKEN"):
        m.Config()
```

**Step 2:** Run: `cd backend && uv run pytest tests/test_config.py -v` → FAIL

**Step 3:** Implement `backend/src/config.py`:
```python
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from project root (one level above backend/)
load_dotenv(Path(__file__).parent.parent.parent / ".env")


@dataclass(frozen=True)
class InvestmentCriteria:
    max_price_eur: int = 320_000
    min_size_m2: int = 70
    min_net_yield_pct: float = 5.0
    vft_required: bool = True
    ground_floor_allowed: bool = False


class Config:
    TRANSACTION_COST_PCT: float = 0.10
    OPERATING_COST_PCT: float = 0.25
    AIRROI_BASE_URL: str = "https://api.airroi.io/api/v1/calculator"
    APIFY_IDEALISTA_ACTOR_ID: str = "dtrungtin~idealista-scraper"
    APIFY_BASE_URL: str = "https://api.apify.com/v2"

    def __init__(self) -> None:
        self.apify_token: str = self._require("APIFY_TOKEN")
        self.airroi_api_key: str = self._require("AIRROI_API_KEY")
        self.criteria: InvestmentCriteria = InvestmentCriteria()

    def _require(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value
```

> Key fix: `load_dotenv(Path(__file__).parent.parent.parent / ".env")` — explicitly
> points to root `.env` regardless of where the process is started from.

**Step 4:** Run: `cd backend && uv run pytest tests/test_config.py -v` → PASS

**Step 5:** Commit: `git commit -m "feat: add Config with typed investment criteria and env validation"`

---

### Task 3: `backend/src/scrapers/idealista.py`

**Files:**
- Create: `backend/src/scrapers/idealista.py`
- Create: `backend/tests/test_idealista.py`

**Step 1:** Write failing test `backend/tests/test_idealista.py`:
```python
import pytest
from unittest.mock import MagicMock
from src.scrapers.idealista import IdealistaScraper, ScraperError

def test_normalize_listing_maps_fields():
    scraper = IdealistaScraper.__new__(IdealistaScraper)
    raw = {
        "propertyCode": "abc123", "url": "https://idealista.com/x",
        "address": "Calle Test 1", "price": 280000, "size": 82,
        "floor": "2", "rooms": 2, "bathrooms": 2,
        "latitude": 36.51, "longitude": -4.88, "date": "2025-03-01",
    }
    result = scraper._normalize_listing(raw)
    assert result["id"] == "abc123"
    assert result["price_eur"] == 280000
    assert result["size_m2"] == 82
    assert result["lat"] == 36.51

def test_handle_response_raises_on_error():
    scraper = IdealistaScraper.__new__(IdealistaScraper)
    mock_r = MagicMock(ok=False, status_code=403, text="Forbidden")
    with pytest.raises(ScraperError) as exc:
        scraper._handle_response(mock_r, "actor_id", "url")
    assert exc.value.status_code == 403
```

**Step 2:** Run: `cd backend && uv run pytest tests/test_idealista.py -v` → FAIL

**Step 3:** Implement `backend/src/scrapers/idealista.py`:
```python
import logging
import time

import requests

from src.config import Config

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    def __init__(self, actor_id: str, url: str, status_code: int, body: str) -> None:
        self.actor_id = actor_id
        self.url = url
        self.status_code = status_code
        self.body = body
        super().__init__(f"actor={actor_id} url={url} status={status_code}")


class IdealistaScraper:
    def __init__(self) -> None:
        self._cfg = Config()
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {self._cfg.apify_token}"

    def scrape(self, location: str, max_items: int = 200) -> list[dict]:
        criteria = self._cfg.criteria
        payload = {
            "location": location,
            "maxItems": max_items,
            "propertyType": "flat,house",
            "minSize": criteria.min_size_m2,
            "maxPrice": criteria.max_price_eur,
            "country": "es",
        }
        run_id = self._start_run(payload)
        self._await_run(run_id)
        return [self._normalize_listing(r) for r in self._fetch_items(run_id)]

    def _start_run(self, payload: dict) -> str:
        actor = self._cfg.APIFY_IDEALISTA_ACTOR_ID
        url = f"{self._cfg.APIFY_BASE_URL}/acts/{actor}/runs"
        r = self._session.post(url, json=payload)
        self._handle_response(r, actor, url)
        return r.json()["data"]["id"]

    def _await_run(self, run_id: str, timeout: int = 300) -> None:
        actor = self._cfg.APIFY_IDEALISTA_ACTOR_ID
        url = f"{self._cfg.APIFY_BASE_URL}/actor-runs/{run_id}"
        deadline = time.time() + timeout
        terminal = {"FAILED", "ABORTED", "TIMED-OUT"}
        while time.time() < deadline:
            r = self._session.get(url)
            self._handle_response(r, actor, url)
            status = r.json()["data"]["status"]
            if status == "SUCCEEDED":
                return
            if status in terminal:
                raise ScraperError(actor, url, 0, f"Run ended: {status}")
            time.sleep(10)
        raise ScraperError(actor, url, 0, f"Timed out after {timeout}s")

    def _fetch_items(self, run_id: str) -> list[dict]:
        actor = self._cfg.APIFY_IDEALISTA_ACTOR_ID
        url = f"{self._cfg.APIFY_BASE_URL}/actor-runs/{run_id}/dataset/items"
        r = self._session.get(url)
        self._handle_response(r, actor, url)
        return r.json()

    def _handle_response(self, r: requests.Response, actor: str, url: str) -> None:
        if not r.ok:
            logger.error("Scraper | actor=%s url=%s status=%s body=%s",
                         actor, url, r.status_code, r.text[:500])
            raise ScraperError(actor, url, r.status_code, r.text[:500])

    def _normalize_listing(self, raw: dict) -> dict:
        return {
            "id": str(raw.get("propertyCode", raw.get("id", ""))),
            "url": raw.get("url", ""),
            "address": raw.get("address", ""),
            "price_eur": raw.get("price", 0),
            "size_m2": raw.get("size", 0),
            "floor": str(raw.get("floor", "")),
            "floor_label": str(raw.get("floorLabel", raw.get("floor", ""))),
            "rooms": raw.get("rooms", 0),
            "bathrooms": raw.get("bathrooms", 0),
            "terrace_m2": raw.get("terraceArea", 0),
            "images": raw.get("images", []),
            "description": raw.get("description", ""),
            "lat": raw.get("latitude"),
            "lng": raw.get("longitude"),
            "community_fee_month": raw.get("communityFee", 150),
            "published_date": raw.get("date", ""),
            "location": raw.get("municipality", ""),
        }
```

**Step 4:** Run: `cd backend && uv run pytest tests/test_idealista.py -v` → PASS

**Step 5:** Commit: `git commit -m "feat: add Idealista/Apify scraper with typed error handling"`

---

## Phase 2 — Analysis Layer

### Task 4: `backend/src/analyzers/str_revenue.py`

**Files:**
- Create: `backend/src/analyzers/str_revenue.py`
- Create: `backend/tests/test_str_revenue.py`

**Step 1:** Write failing test `backend/tests/test_str_revenue.py`:
```python
from unittest.mock import patch
from src.analyzers.str_revenue import AirROIAnalyzer

def test_returns_revenue_estimate():
    analyzer = AirROIAnalyzer.__new__(AirROIAnalyzer)
    mock_resp = {"annual_revenue": 28500, "occupancy_rate": 0.72, "adr": 110}
    with patch.object(analyzer, "_call_api", return_value=mock_resp):
        result = analyzer.analyze_property(
            {"id": "p1", "lat": 36.5, "lng": -4.8, "rooms": 2, "size_m2": 80}
        )
    assert result["annual_revenue_eur"] == 28500
    assert result["property_id"] == "p1"
    assert result["error"] is None

def test_handles_api_error_gracefully():
    analyzer = AirROIAnalyzer.__new__(AirROIAnalyzer)
    with patch.object(analyzer, "_call_api", side_effect=Exception("timeout")):
        result = analyzer.analyze_property(
            {"id": "p1", "lat": 36.5, "lng": -4.8, "rooms": 2, "size_m2": 80}
        )
    assert result["annual_revenue_eur"] is None
    assert result["error"] == "timeout"
```

**Step 2:** Run: `cd backend && uv run pytest tests/test_str_revenue.py -v` → FAIL

**Step 3:** Implement `backend/src/analyzers/str_revenue.py`:
```python
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from src.config import Config

logger = logging.getLogger(__name__)


class AirROIAnalyzer:
    def __init__(self) -> None:
        self._cfg = Config()
        self._session = requests.Session()
        self._session.headers["X-API-Key"] = self._cfg.airroi_api_key

    def analyze_batch(self, listings: list[dict], workers: int = 5) -> list[dict]:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.analyze_property, l): l["id"] for l in listings}
            return [f.result() for f in as_completed(futures)]

    def analyze_property(self, listing: dict) -> dict:
        try:
            response = self._call_api(self._build_payload(listing))
            return self._parse_response(listing["id"], response)
        except Exception as exc:
            logger.error("AirROI | property_id=%s error=%s", listing["id"], exc)
            return self._error_result(listing["id"], str(exc))

    def _build_payload(self, listing: dict) -> dict:
        return {
            "lat": listing["lat"],
            "lng": listing["lng"],
            "bedrooms": listing.get("rooms", 2),
            "propertyType": "apartment",
            "size": listing.get("size_m2", 70),
        }

    def _call_api(self, payload: dict) -> dict:
        r = self._session.post(self._cfg.AIRROI_BASE_URL, json=payload, timeout=30)
        if not r.ok:
            raise Exception(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def _parse_response(self, property_id: str, data: dict) -> dict:
        return {
            "property_id": property_id,
            "annual_revenue_eur": data.get("annual_revenue"),
            "monthly_avg_revenue_eur": data.get("monthly_revenue"),
            "occupancy_rate_pct": round((data.get("occupancy_rate") or 0) * 100, 1),
            "adr_eur": data.get("adr"),
            "peak_season_revenue_eur": data.get("peak_revenue"),
            "low_season_revenue_eur": data.get("low_revenue"),
            "error": None,
        }

    def _error_result(self, property_id: str, error: str) -> dict:
        return {
            "property_id": property_id,
            "annual_revenue_eur": None,
            "monthly_avg_revenue_eur": None,
            "occupancy_rate_pct": None,
            "adr_eur": None,
            "peak_season_revenue_eur": None,
            "low_season_revenue_eur": None,
            "error": error,
        }
```

**Step 4:** Run: `cd backend && uv run pytest tests/test_str_revenue.py -v` → PASS

**Step 5:** Commit: `git commit -m "feat: add AirROI STR analyzer with parallel batch and graceful error handling"`

---

### Task 5: `backend/src/analyzers/roi.py`

**Files:**
- Create: `backend/src/analyzers/roi.py`
- Create: `backend/tests/test_roi.py`

**Step 1:** Write failing test `backend/tests/test_roi.py`:
```python
import pytest
from src.analyzers.roi import ROIAnalyzer

def test_gross_yield_calculation():
    analyzer = ROIAnalyzer()
    listing = {"id": "p1", "price_eur": 285000, "community_fee_month": 150}
    str_est = {"property_id": "p1", "annual_revenue_eur": 28500, "occupancy_rate_pct": 72, "error": None}
    result = analyzer.compute_property(listing, str_est)
    assert abs(result["gross_yield_pct"] - 10.0) < 0.1
    assert result["net_yield_pct"] > 5.0
    assert result["acquisition_cost"] == pytest.approx(285000 * 1.10)

def test_none_yield_when_revenue_missing():
    analyzer = ROIAnalyzer()
    listing = {"id": "p1", "price_eur": 200000, "community_fee_month": 120}
    str_est = {"property_id": "p1", "annual_revenue_eur": None, "error": "API failed"}
    result = analyzer.compute_property(listing, str_est)
    assert result["gross_yield_pct"] is None
    assert result["net_yield_pct"] is None
```

**Step 2:** Run → FAIL

**Step 3:** Implement `backend/src/analyzers/roi.py`:
```python
from src.config import Config


class ROIAnalyzer:
    def __init__(self) -> None:
        self._cfg = Config()

    def compute_all(self, listings: list[dict], str_data: list[dict]) -> list[dict]:
        str_by_id = {s["property_id"]: s for s in str_data}
        return [self.compute_property(l, str_by_id.get(l["id"], {})) for l in listings]

    def compute_property(self, listing: dict, str_est: dict) -> dict:
        price = listing["price_eur"]
        acq = round(price * (1 + self._cfg.TRANSACTION_COST_PCT), 2)
        revenue = str_est.get("annual_revenue_eur")
        if revenue is None:
            return self._no_revenue_result(listing["id"], price, acq, str_est.get("error"))
        return self._full_result(listing, str_est, price, acq, revenue)

    def _no_revenue_result(self, pid: str, price: float, acq: float, error: str | None) -> dict:
        return {
            "property_id": pid, "purchase_price": price, "acquisition_cost": acq,
            "gross_yield_pct": None, "net_yield_pct": None,
            "monthly_cashflow": None, "payback_years": None,
            "investment_score": None, "error": error or "No revenue data",
        }

    def _full_result(self, listing: dict, str_est: dict, price: float, acq: float, revenue: float) -> dict:
        opex = revenue * self._cfg.OPERATING_COST_PCT
        community = listing.get("community_fee_month", 150) * 12
        ibi = price * 0.60 * 0.005
        net_income = revenue - opex - community - ibi
        net_yield = (net_income / acq) * 100
        occupancy = str_est.get("occupancy_rate_pct") or 0
        score = round(min(net_yield / 10, 1) * 4 + min(occupancy / 100, 1) * 2, 1)
        return {
            "property_id": listing["id"],
            "purchase_price": price,
            "acquisition_cost": acq,
            "annual_revenue_eur": revenue,
            "gross_yield_pct": round((revenue / price) * 100, 2),
            "annual_opex": round(opex, 2),
            "community_fees_yr": community,
            "ibi_yr": round(ibi, 2),
            "net_income_yr": round(net_income, 2),
            "net_yield_pct": round(net_yield, 2),
            "monthly_cashflow": round(net_income / 12, 2),
            "payback_years": round(acq / net_income, 1) if net_income > 0 else None,
            "investment_score": score,
            "error": None,
        }
```

**Step 4:** Run → PASS

**Step 5:** Commit: `git commit -m "feat: add ROI calculator with gross/net yield and investment score"`

---

## Phase 3 — Filter + Async API

### Task 6: `backend/src/filters/property_filter.py`

**Files:**
- Create: `backend/src/filters/property_filter.py`
- Create: `backend/tests/test_filter.py`

**Step 1:** Write failing test `backend/tests/test_filter.py`:
```python
from src.filters.property_filter import PropertyFilter

BASE = {"id": "p1", "price_eur": 280000, "size_m2": 82, "floor": "2",
        "floor_label": "2ª planta", "terrace_m2": 15, "description": "con terraza"}
STR  = {"property_id": "p1", "annual_revenue_eur": 28500, "error": None}
ROI  = {"property_id": "p1", "net_yield_pct": 6.2, "investment_score": 7.5}

def test_passing_property_included():
    assert len(PropertyFilter().filter([BASE], [STR], [ROI])) == 1

def test_ground_floor_excluded():
    listing = {**BASE, "floor": "0", "floor_label": "Planta Baja"}
    assert len(PropertyFilter().filter([listing], [STR], [ROI])) == 0

def test_over_budget_excluded():
    assert len(PropertyFilter().filter([{**BASE, "price_eur": 350000}], [STR], [ROI])) == 0

def test_low_yield_excluded():
    assert len(PropertyFilter().filter([BASE], [STR], [{**ROI, "net_yield_pct": 3.5}])) == 0

def test_no_terrace_excluded():
    listing = {**BASE, "terrace_m2": 0, "description": "sin terraza"}
    assert len(PropertyFilter().filter([listing], [STR], [ROI])) == 0
```

**Step 2:** Run → FAIL

**Step 3:** Implement `backend/src/filters/property_filter.py`:
```python
from src.config import Config

_GROUND_LABELS = frozenset({"bajo", "planta baja", "pb", "0", "ground", "baja"})


class PropertyFilter:
    def __init__(self) -> None:
        self._criteria = Config().criteria

    def filter(self, listings: list[dict], str_data: list[dict], roi_data: list[dict]) -> list[dict]:
        str_by_id = {s["property_id"]: s for s in str_data}
        roi_by_id = {r["property_id"]: r for r in roi_data}
        return [
            {**l, **str_by_id.get(l["id"], {}), **roi_by_id.get(l["id"], {})}
            for l in listings
            if self._passes(l, roi_by_id.get(l["id"], {}))
        ]

    def _passes(self, listing: dict, roi: dict) -> bool:
        return (
            listing.get("price_eur", 0) <= self._criteria.max_price_eur
            and listing.get("size_m2", 0) >= self._criteria.min_size_m2
            and not self._is_ground_floor(listing)
            and self._has_terrace(listing)
            and (roi.get("net_yield_pct") or 0) >= self._criteria.min_net_yield_pct
        )

    def _is_ground_floor(self, listing: dict) -> bool:
        floor = str(listing.get("floor", "")).lower().strip()
        label = str(listing.get("floor_label", "")).lower().strip()
        return floor in _GROUND_LABELS or label in _GROUND_LABELS

    def _has_terrace(self, listing: dict) -> bool:
        if (listing.get("terrace_m2") or 0) > 0:
            return True
        desc = listing.get("description", "").lower()
        return "terraza" in desc or "terrace" in desc
```

**Step 4:** Run → PASS

**Step 5:** Commit: `git commit -m "feat: add property filter with hard investment criteria enforcement"`

---

### Task 7: `backend/src/reporters/pipeline.py` + `backend/src/main.py`

**Critical fix:** Analysis takes 3–5 minutes. FastAPI must not block. Pattern:
`POST /api/analysis` → starts background task → returns `run_id`
`GET /api/analysis/{run_id}` → poll until `status == "completed"`

**Files:**
- Create: `backend/src/reporters/pipeline.py`
- Create: `backend/src/main.py`

**Step 1:** Implement `backend/src/reporters/pipeline.py`:
```python
import json
import uuid
from datetime import datetime
from pathlib import Path

from src.scrapers.idealista import IdealistaScraper
from src.analyzers.str_revenue import AirROIAnalyzer
from src.analyzers.roi import ROIAnalyzer
from src.filters.property_filter import PropertyFilter

_runs: dict[str, dict] = {}  # in-memory store; replace with Redis/DB for production


def start_analysis(location: str) -> str:
    run_id = str(uuid.uuid4())[:8]
    _runs[run_id] = {"status": "running", "location": location, "started_at": datetime.now().isoformat()}
    return run_id


def run_analysis(run_id: str, location: str) -> None:
    """Blocking — must be called in a thread pool, not the event loop."""
    try:
        out = Path("outputs/data")
        out.mkdir(parents=True, exist_ok=True)

        listings = IdealistaScraper().scrape(location)
        _save(out / f"{run_id}_listings.json", listings)

        str_data = AirROIAnalyzer().analyze_batch(listings)
        _save(out / f"{run_id}_str.json", str_data)

        roi_data = ROIAnalyzer().compute_all(listings, str_data)
        _save(out / f"{run_id}_roi.json", roi_data)

        filtered = PropertyFilter().filter(listings, str_data, roi_data)
        _save(out / f"{run_id}_filtered.json", filtered)

        _runs[run_id] = {
            "status": "completed",
            "location": location,
            "generated_at": datetime.now().isoformat(),
            "total_scraped": len(listings),
            "total_passing": len(filtered),
            "properties": filtered,
            "market": None,  # populated by Claude agent via WebSearch
        }
    except Exception as exc:
        _runs[run_id] = {"status": "failed", "error": str(exc)}


def get_run(run_id: str) -> dict | None:
    return _runs.get(run_id)


def _save(path: Path, data: list[dict]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
```

**Step 2:** Implement `backend/src/main.py`:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.reporters.pipeline import start_analysis, run_analysis, get_run

app = FastAPI(title="Real Estate Investment Analyzer")
_executor = ThreadPoolExecutor(max_workers=3)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisRequest(BaseModel):
    location: str


@app.post("/api/analysis", status_code=202)
async def create_analysis(req: AnalysisRequest) -> dict:
    if not req.location.strip():
        raise HTTPException(status_code=400, detail="Location cannot be empty")
    location = req.location.strip()
    run_id = start_analysis(location)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, run_analysis, run_id, location)
    return {"run_id": run_id, "status": "running"}


@app.get("/api/analysis/{run_id}")
async def get_analysis(run_id: str) -> dict:
    result = get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
```

**Step 3:** Start server and verify both endpoints:
```bash
cd backend && uv run uvicorn src.main:app --reload
curl http://localhost:8000/api/health
# Expected: {"status": "ok"}

curl -X POST http://localhost:8000/api/analysis \
  -H "Content-Type: application/json" \
  -d '{"location": "Marbella"}'
# Expected: {"run_id": "abc12345", "status": "running"}
```

**Step 4:** Commit: `git commit -m "feat: add async FastAPI with background pipeline — non-blocking analysis"`

---

## Phase 4 — React Frontend

### Task 8: Frontend scaffold

**Files:**
- Create: `frontend/` — Vite + React + TypeScript + Tailwind + shadcn-ui

**Step 1:** Scaffold:
```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install lightweight-charts
npm install @radix-ui/react-slot class-variance-authority clsx tailwind-merge lucide-react
```

**Step 2:** Init shadcn-ui:
```bash
npx shadcn@latest init   # choose: TypeScript, Default style, CSS variables
npx shadcn@latest add table badge card
```

**Step 3:** Configure `vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
```

**Step 4:** `npm run dev` → Vite starts on `http://localhost:5173`

**Step 5:** Commit: `git commit -m "chore: scaffold React frontend with Vite, Tailwind, shadcn-ui"`

---

### Task 9: TypeScript types + polling hook

**Files:**
- Create: `frontend/src/types/analysis.ts`
- Create: `frontend/src/hooks/useAnalysis.ts`

**Step 1:** `frontend/src/types/analysis.ts`:
```typescript
export interface Property {
  id: string
  address: string
  price_eur: number
  size_m2: number
  floor: string
  rooms: number
  terrace_m2: number
  images: string[]
  url: string
  annual_revenue_eur: number | null
  occupancy_rate_pct: number | null
  gross_yield_pct: number | null
  net_yield_pct: number | null
  investment_score: number | null
  monthly_cashflow: number | null
  recommendation: 'BUY' | 'WATCH' | 'SKIP'
}

export interface MarketTrends {
  price_per_m2_history: Array<{ year: number; price_eur: number }>
  yoy_appreciation_pct: number | null
  vft_regulatory_risk: 'low' | 'medium' | 'high'
  vft_notes: string
  market_saturation_score: number | null
  liquidity_score: number | null
}

export interface AnalysisResult {
  run_id: string
  status: 'running' | 'completed' | 'failed'
  location: string
  generated_at: string
  total_scraped: number
  total_passing: number
  properties: Property[]
  market: MarketTrends | null
  error?: string
}
```

**Step 2:** `frontend/src/hooks/useAnalysis.ts` — polls every 5s until completed:
```typescript
import { useState, useRef } from 'react'
import type { AnalysisResult } from '../types/analysis'

type Status = 'idle' | 'loading' | 'polling' | 'success' | 'error'

export function useAnalysis() {
  const [status, setStatus] = useState<Status>('idle')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current)
  }

  const analyze = async (location: string) => {
    setStatus('loading')
    setError(null)
    try {
      const res = await fetch('/api/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ location }),
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
```

**Step 3:** Commit: `git commit -m "feat: add TypeScript types and polling useAnalysis hook"`

---

### Task 10: Dashboard components

**Files:**
- Create: `frontend/src/components/ExecutiveSummary.tsx`
- Create: `frontend/src/components/PropertyTable.tsx`
- Create: `frontend/src/components/MarketOverview.tsx`
- Create: `frontend/src/components/YieldChart.tsx`
- Create: `frontend/src/components/RiskIndicators.tsx`
- Update: `frontend/src/App.tsx`

**Step 1:** `ExecutiveSummary.tsx`:
```tsx
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AnalysisResult } from '../types/analysis'

const VARIANT = { BUY: 'default', WATCH: 'secondary', SKIP: 'destructive' } as const

export function ExecutiveSummary({ result }: { result: AnalysisResult }) {
  const top3 = [...result.properties]
    .sort((a, b) => (b.net_yield_pct ?? 0) - (a.net_yield_pct ?? 0))
    .slice(0, 3)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Executive Summary — {result.location}</CardTitle>
        <p className="text-sm text-muted-foreground">
          {result.total_passing} of {result.total_scraped} properties passed all criteria
        </p>
      </CardHeader>
      <CardContent className="flex gap-4 flex-wrap">
        {top3.map(p => (
          <div key={p.id} className="flex flex-col gap-1 min-w-48">
            <Badge variant={VARIANT[p.recommendation]}>{p.recommendation}</Badge>
            <span className="text-sm font-medium truncate">{p.address}</span>
            <span className="text-xs text-muted-foreground">
              Net yield: {p.net_yield_pct?.toFixed(1)}% · Score: {p.investment_score}/10
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
```

**Step 2:** `MarketOverview.tsx` — shows price trend chart OR "market data not available" notice:
```tsx
import { useEffect, useRef } from 'react'
import { createChart } from 'lightweight-charts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { MarketTrends } from '../types/analysis'

export function MarketOverview({ market, location }: { market: MarketTrends | null; location: string }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current || !market?.price_per_m2_history?.length) return
    const chart = createChart(ref.current, {
      height: 200,
      layout: { background: { color: 'transparent' } },
    })
    const series = chart.addLineSeries({ color: '#3b82f6' })
    series.setData(market.price_per_m2_history.map(p => ({ time: `${p.year}-01-01`, value: p.price_eur })))
    chart.timeScale().fitContent()
    return () => chart.remove()
  }, [market])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Market Overview — {location}</CardTitle>
      </CardHeader>
      <CardContent>
        {market ? (
          <>
            <div ref={ref} />
            <div className="flex gap-6 mt-4 text-sm">
              <span>YoY growth: <strong>{market.yoy_appreciation_pct?.toFixed(1)}%</strong></span>
              <span>VFT risk: <strong>{market.vft_regulatory_risk}</strong></span>
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            Market trend data requires Claude Code: <code>claude "analyze {location}"</code>
          </p>
        )}
      </CardContent>
    </Card>
  )
}
```

**Step 3:** `PropertyTable.tsx`:
```tsx
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { Property } from '../types/analysis'

const fmt = (n: number | null, d = 1) => n != null ? n.toFixed(d) : '—'
const VARIANT = { BUY: 'default', WATCH: 'secondary', SKIP: 'destructive' } as const

export function PropertyTable({ properties }: { properties: Property[] }) {
  const sorted = [...properties].sort((a, b) => (b.net_yield_pct ?? 0) - (a.net_yield_pct ?? 0))
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Address</TableHead>
          <TableHead className="text-right">Price €</TableHead>
          <TableHead className="text-right">m²</TableHead>
          <TableHead className="text-right">Gross %</TableHead>
          <TableHead className="text-right">Net %</TableHead>
          <TableHead className="text-right">Score</TableHead>
          <TableHead>Verdict</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map(p => (
          <TableRow key={p.id}>
            <TableCell className="max-w-48 truncate">
              <a href={p.url} target="_blank" rel="noreferrer" className="hover:underline">{p.address}</a>
            </TableCell>
            <TableCell className="text-right">{p.price_eur.toLocaleString()}</TableCell>
            <TableCell className="text-right">{p.size_m2}</TableCell>
            <TableCell className="text-right">{fmt(p.gross_yield_pct)}%</TableCell>
            <TableCell className="text-right font-medium">{fmt(p.net_yield_pct)}%</TableCell>
            <TableCell className="text-right">{fmt(p.investment_score)}</TableCell>
            <TableCell><Badge variant={VARIANT[p.recommendation]}>{p.recommendation}</Badge></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

**Step 4:** `YieldChart.tsx` — bar chart with 5% threshold line:
```tsx
import { useEffect, useRef } from 'react'
import { createChart } from 'lightweight-charts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Property } from '../types/analysis'

export function YieldChart({ properties }: { properties: Property[] }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current || !properties.length) return
    const chart = createChart(ref.current, { height: 180, layout: { background: { color: 'transparent' } } })
    const series = chart.addHistogramSeries({ color: '#22c55e' })
    const sorted = [...properties].sort((a, b) => (b.net_yield_pct ?? 0) - (a.net_yield_pct ?? 0))
    series.setData(sorted.map((p, i) => ({ time: (i + 1) as unknown as string, value: p.net_yield_pct ?? 0 })))
    chart.timeScale().fitContent()
    return () => chart.remove()
  }, [properties])
  return (
    <Card>
      <CardHeader><CardTitle>Net Yield Distribution (min 5% threshold)</CardTitle></CardHeader>
      <CardContent><div ref={ref} /></CardContent>
    </Card>
  )
}
```

**Step 5:** `RiskIndicators.tsx`:
```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { MarketTrends } from '../types/analysis'

function ScoreTile({ label, score }: { label: string; score: number | null }) {
  const color = !score ? 'text-muted-foreground' : score >= 7 ? 'text-green-500' : score >= 4 ? 'text-yellow-500' : 'text-red-500'
  return (
    <div className="flex flex-col items-center p-4 border rounded-lg">
      <span className={`text-3xl font-bold ${color}`}>{score ?? '—'}</span>
      <span className="text-xs text-muted-foreground text-center mt-1">{label}</span>
    </div>
  )
}

export function RiskIndicators({ market }: { market: MarketTrends | null }) {
  if (!market) return null
  return (
    <Card>
      <CardHeader><CardTitle>Risk Indicators (1–10, higher = better for investor)</CardTitle></CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <ScoreTile label="Market Saturation" score={market.market_saturation_score} />
        <ScoreTile label="Liquidity" score={market.liquidity_score} />
        <ScoreTile label="VFT Regulatory" score={market.vft_regulatory_risk === 'low' ? 8 : market.vft_regulatory_risk === 'medium' ? 5 : 2} />
      </CardContent>
    </Card>
  )
}
```

**Step 6:** Update `frontend/src/App.tsx`:
```tsx
import { useState } from 'react'
import { useAnalysis } from './hooks/useAnalysis'
import { ExecutiveSummary } from './components/ExecutiveSummary'
import { MarketOverview } from './components/MarketOverview'
import { PropertyTable } from './components/PropertyTable'
import { YieldChart } from './components/YieldChart'
import { RiskIndicators } from './components/RiskIndicators'

export default function App() {
  const [location, setLocation] = useState('')
  const { status, result, error, analyze } = useAnalysis()
  const isLoading = status === 'loading' || status === 'polling'

  return (
    <div className="min-h-screen bg-background text-foreground p-8 max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Real Estate Investment Analyzer</h1>
      <div className="flex gap-4 mb-8">
        <input
          className="border rounded px-4 py-2 flex-1 bg-background"
          placeholder="Enter location (e.g. Marbella)"
          value={location}
          onChange={e => setLocation(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && analyze(location)}
        />
        <button
          className="bg-primary text-primary-foreground px-6 py-2 rounded disabled:opacity-50"
          onClick={() => analyze(location)}
          disabled={isLoading || !location.trim()}
        >
          {status === 'loading' ? 'Starting…' : status === 'polling' ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>
      {error && <p className="text-destructive mb-4">{error}</p>}
      {result && result.status === 'completed' && (
        <div className="flex flex-col gap-6">
          <ExecutiveSummary result={result} />
          <MarketOverview market={result.market} location={result.location} />
          <PropertyTable properties={result.properties} />
          <YieldChart properties={result.properties} />
          <RiskIndicators market={result.market} />
        </div>
      )}
    </div>
  )
}
```

**Step 7:** `npm run build` — verify 0 TypeScript errors.

**Step 8:** Commit: `git commit -m "feat: add all dashboard components with market overview, yield chart, risk indicators"`

---

## Phase 5 — Agent Layer

### Task 11: Agent definitions + orchestrator skill

**Files:**
- Create: `.claude/agents/listings-scraper.md`
- Create: `.claude/agents/market-researcher.md`
- Create: `.claude/agents/str-analyst.md`
- Create: `.claude/agents/roi-calculator.md`
- Create: `.claude/agents/property-filter.md`
- Create: `.claude/agents/report-builder.md`
- Create: `.claude/skills/analyze-market/SKILL.md`

**Agent files** use frontmatter: `name`, `description` (with `<example>` blocks), `model`, `color`.
Each agent invokes its Python module via: `cd backend && uv run python -c "from src.X import Y; ..."`

**market-researcher.md** uses WebSearch — this is the only agent that produces `market_trends.json`.
After it completes, `report-builder` can call `PUT /api/analysis/{run_id}/market` to enrich the result.

Add to `backend/src/main.py`:
```python
@app.put("/api/analysis/{run_id}/market")
async def update_market(run_id: str, market_data: dict) -> dict:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run["market"] = market_data
    return {"status": "updated"}
```

**Orchestrator SKILL.md** fan-out:
1. Parse + confirm location
2. `POST /api/analysis` → get `run_id`
3. Launch `listings-scraper` + `market-researcher` IN PARALLEL
4. After listings → launch `str-analyst`
5. After STR → launch `roi-calculator` → `property-filter`
6. After market research → `PUT /api/analysis/{run_id}/market`
7. Report: top 3 properties, open `http://localhost:5173`

**Step commit:** `git commit -m "feat: add 6 agent definitions and analyze-market orchestrator skill"`

---

## Verification

**All backend tests:**
```bash
cd backend && uv run pytest tests/ -v
```
Expected: all pass.

**Backend health:**
```bash
cd backend && uv run uvicorn src.main:app --reload
curl http://localhost:8000/api/health
# {"status": "ok"}
```

**Frontend build:**
```bash
cd frontend && npm run build
# 0 TypeScript errors
```

**Full stack test (mock — no real API calls):**
1. Start backend + frontend
2. Open `http://localhost:5173`
3. Enter "Marbella", click Analyze
4. Status changes: Starting → Analyzing → results appear
5. Property table visible, MarketOverview shows "requires Claude Code" notice
6. BUY/WATCH/SKIP badges visible

**Via Claude Code (full pipeline with market data):**
```bash
claude "analyze Marbella"
```
Expected: agents run, market data populated, `PUT /api/analysis/{run_id}/market` called, React dashboard shows full data including price trend chart and risk indicators.
