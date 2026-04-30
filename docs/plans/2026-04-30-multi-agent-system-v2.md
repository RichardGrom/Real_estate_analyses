# Real Estate Investment Advisor — Implementation Plan v2

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a personalized investment advisor for buying real estate in Spain. The user provides a location, budget, and return expectations. The system scrapes Idealista listings, fetches STR revenue via AirROI, fetches LTR average via Idealista rental, fetches capital growth via INE REST API, calculates yields, and returns a ranked dashboard with BUY/WATCH/SKIP verdicts.

**Architecture:** Async FastAPI backend + React frontend. User submits investment parameters → backend runs pipeline in thread pool (STR + LTR + capital growth in parallel) → frontend polls until complete → dashboard shows STR yield, LTR yield, capital growth, and verdict side-by-side.

**Supersedes:** `2026-04-15-multi-agent-system.md` — updated based on design decisions in `2026-04-30-pre-implementation-decisions.md`

**Tech Stack:**
- Backend: Python 3.11, FastAPI, Uvicorn, uv, requests, python-dotenv, pydantic
- Frontend: React, TypeScript, Vite, Tailwind CSS, shadcn-ui, lightweight-charts
- Data: Apify REST (Idealista sale + rental), AirROI REST API, INE REST API (public, no auth)
- Agents: Claude Code skills + agents (Phase 5+)

**Standards:** `0_instructions/.claude/CLAUDE.md` — SOLID, <20 lines/function, type hints (3.10+), uv only.

---

## User Input Parameters

| Parameter | Type | Required | Default | Example |
|---|---|---|---|---|
| `location` | str | ✓ | — | `"Marbella"` |
| `budget_eur` | int | ✓ | — | `300000` |
| `property_type` | str | — | `"any"` | `"apartment"` |
| `bedrooms` | int | — | `1` | `2` |
| `min_size_m2` | int | — | `70` | `70` |
| `parking` | bool | — | `false` | `true` |
| `terrace` | bool | — | `false` | `true` |
| `floor_preference` | str | — | `"any"` | `"top"` |
| `building_type` | str | — | `"any"` | `"new-build"` |
| `min_net_yield_pct` | float | — | `None` | `5.0` |
| `min_capital_growth_pct` | float | — | `None` | `3.0` |

---

## Directory Structure (target state)

```
Real_estate_analyses/
├── CLAUDE.md
├── 0_instructions/
├── .env                             (APIFY_TOKEN, AIRROI_API_KEY, EXA_API_KEY)
├── .gitignore
│
├── backend/
│   ├── pyproject.toml
│   ├── .venv/
│   └── src/
│       ├── main.py
│       ├── config.py
│       ├── models.py
│       ├── scrapers/
│       │   ├── __init__.py
│       │   └── idealista.py
│       ├── analyzers/
│       │   ├── __init__.py
│       │   ├── str_revenue.py
│       │   ├── ltr_revenue.py       # NEW — Idealista rental via Apify
│       │   ├── capital_growth.py    # NEW — INE REST API
│       │   └── roi.py
│       ├── filters/
│       │   ├── __init__.py
│       │   └── property_filter.py
│       └── reporters/
│           └── pipeline.py
│   └── tests/
│       ├── conftest.py
│       ├── test_config.py
│       ├── test_idealista.py
│       ├── test_str_revenue.py
│       ├── test_ltr_revenue.py      # NEW
│       ├── test_capital_growth.py   # NEW
│       ├── test_roi.py
│       └── test_filter.py
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── InvestmentForm.tsx
│       │   ├── ExecutiveSummary.tsx
│       │   ├── MarketOverview.tsx
│       │   ├── PropertyTable.tsx    # STR yield + LTR yield as separate columns
│       │   ├── YieldChart.tsx
│       │   └── RiskIndicators.tsx
│       ├── hooks/useAnalysis.ts
│       └── types/analysis.ts
│
└── outputs/
    ├── data/
    ├── tests/
    └── security/
```

---

## Data Flow

```
User: location + budget + yield_target + growth_target
        ↓
POST /api/analysis  →  run_id (202 Accepted)
        ↓ (background thread)
listings-scraper (Apify sale) → raw_listings
        ↓
        ├── AirROI REST → STR revenue per property
        ├── Apify rental (operation: rent) → LTR avg rent/m²    ← NEW
        └── INE REST API → YoY capital appreciation              ← NEW
        ↓ (all 3 parallel)
roi-calculator → gross_yield, str_net_yield, ltr_net_yield,
                 preferred_rental_type, investment_score (vs user targets)
        ↓
property-filter → hard exclusions + user thresholds
        ↓
GET /api/analysis/{run_id} → completed result
        ↓
React dashboard → PropertyTable: STR yield | LTR yield | capital growth | verdict
```

---

## Phase 0 — Cleanup

### Task 0: Remove orphan files, update .gitignore

**Step 1:** Remove `requirements.txt`:
```bash
cd /Users/richardgrom/Documents/Richard\ /Real_estate_analyses
git rm requirements.txt
```

**Step 2:** Replace `.gitignore` content:
```
.env
.env.*
.venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
node_modules/
dist/
outputs/data/*.json
.DS_Store
Thumbs.db
```

**Step 3:** Commit:
```bash
git add .gitignore
git commit -m "chore: remove requirements.txt, update .gitignore"
```

---

## Phase 1 — Backend Foundation

### Task 1: uv project setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/__init__.py` + all sub-package `__init__.py` files
- Create: `backend/tests/conftest.py`, `backend/tests/__init__.py`
- Create: `outputs/data/.gitkeep`

**Step 1:** Create `backend/pyproject.toml`:
```toml
[project]
name = "real-estate-advisor"
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

**Step 2:** Run:
```bash
cd /Users/richardgrom/Documents/Richard\ /Real_estate_analyses/backend
uv venv && source .venv/bin/activate && uv sync --extra dev
```
Expected: `.venv/` created, all packages installed.

**Step 3:** Create empty `__init__.py` in:
`backend/src/`, `backend/src/scrapers/`, `backend/src/analyzers/`,
`backend/src/filters/`, `backend/src/reporters/`, `backend/tests/`

**Step 4:** Create empty `backend/tests/conftest.py`

**Step 5:** Create `outputs/data/.gitkeep`, `outputs/tests/.gitkeep`, `outputs/security/.gitkeep`

**Step 6:** Commit:
```bash
git commit -m "chore: scaffold backend with uv and package structure"
```

---

### Task 2: `backend/src/config.py` + `backend/src/models.py`

**Files:**
- Create: `backend/src/config.py`
- Create: `backend/src/models.py`
- Create: `backend/tests/test_config.py`

**Step 1:** Write failing test `backend/tests/test_config.py`:
```python
import pytest

def test_config_loads(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "test_apify")
    monkeypatch.setenv("AIRROI_API_KEY", "test_airroi")
    monkeypatch.setenv("EXA_API_KEY", "test_exa")
    from src.config import Config
    cfg = Config()
    assert cfg.apify_token == "test_apify"
    assert cfg.airroi_api_key == "test_airroi"
    assert cfg.exa_api_key == "test_exa"

def test_config_raises_on_missing_apify(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    monkeypatch.setenv("AIRROI_API_KEY", "x")
    monkeypatch.setenv("EXA_API_KEY", "x")
    from importlib import reload
    import src.config as m
    reload(m)
    with pytest.raises(ValueError, match="APIFY_TOKEN"):
        m.Config()

def test_config_raises_on_missing_exa(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "x")
    monkeypatch.setenv("AIRROI_API_KEY", "x")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    from importlib import reload
    import src.config as m
    reload(m)
    with pytest.raises(ValueError, match="EXA_API_KEY"):
        m.Config()
```

**Step 2:** Run → FAIL:
```bash
cd backend && uv run pytest tests/test_config.py -v
```

**Step 3:** Implement `backend/src/config.py`:
```python
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent.parent / ".env")


class Config:
    TRANSACTION_COST_PCT: float = 0.10
    STR_OPEX_PCT: float = 0.25        # STR: management + cleaning + supplies
    LTR_OPEX_PCT: float = 0.15        # LTR: vacancy + maintenance
    AIRROI_BASE_URL: str = "https://api.airroi.com/calculator/estimate"
    APIFY_IDEALISTA_ACTOR_ID: str = "igolaizola~idealista-scraper"
    APIFY_BASE_URL: str = "https://api.apify.com/v2"
    INE_IPV_TABLE_URL: str = "https://servicios.ine.es/wstempus/js/es/DATOS_TABLA/49300?tip=AM"

    def __init__(self) -> None:
        self.apify_token: str = self._require("APIFY_TOKEN")
        self.airroi_api_key: str = self._require("AIRROI_API_KEY")
        self.exa_api_key: str = self._require("EXA_API_KEY")

    def _require(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value
```

**Step 4:** Implement `backend/src/models.py`:
```python
from dataclasses import dataclass
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class UserCriteria:
    """User-provided investment parameters. Drives all filtering and scoring."""
    location: str
    budget_eur: int
    property_type: str = "any"
    bedrooms: int = 1
    min_size_m2: int = 70
    parking: bool = False
    terrace: bool = False
    floor_preference: str = "any"
    building_type: str = "any"
    min_net_yield_pct: float | None = None
    min_capital_growth_pct: float | None = None


class AnalysisRequest(BaseModel):
    location: str = Field(..., min_length=2, examples=["Marbella"])
    budget_eur: int = Field(..., gt=0, examples=[320000])
    property_type: str = Field("any", examples=["apartment"])
    bedrooms: int = Field(1, gt=0, examples=[2])
    min_size_m2: int = Field(70, gt=0, examples=[70])
    parking: bool = Field(False)
    terrace: bool = Field(False)
    floor_preference: str = Field("any")
    building_type: str = Field("any")
    min_net_yield_pct: float | None = Field(None, gt=0, examples=[5.0])
    min_capital_growth_pct: float | None = Field(None, gt=0, examples=[3.0])

    def to_criteria(self) -> UserCriteria:
        return UserCriteria(
            location=self.location.strip(),
            budget_eur=self.budget_eur,
            property_type=self.property_type,
            bedrooms=self.bedrooms,
            min_size_m2=self.min_size_m2,
            parking=self.parking,
            terrace=self.terrace,
            floor_preference=self.floor_preference,
            building_type=self.building_type,
            min_net_yield_pct=self.min_net_yield_pct,
            min_capital_growth_pct=self.min_capital_growth_pct,
        )
```

**Step 5:** Run → PASS:
```bash
cd backend && uv run pytest tests/test_config.py -v
```

**Step 6:** Commit:
```bash
git commit -m "feat: add Config with EXA_API_KEY and UserCriteria models"
```

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
from src.models import UserCriteria

CRITERIA = UserCriteria(location="Marbella", budget_eur=320000, min_size_m2=70)

def test_normalize_listing_maps_fields():
    scraper = IdealistaScraper.__new__(IdealistaScraper)
    raw = {
        "propertyCode": "abc123", "url": "https://idealista.com/x",
        "address": "Calle Test 1", "price": 280000, "size": 82,
        "floor": "2", "rooms": 2, "bathrooms": 2,
        "latitude": 36.51, "longitude": -4.88,
        "features": {"hasTerrace": True},
        "parkingSpace": {"hasParkingSpace": True},
    }
    result = scraper._normalize_listing(raw)
    assert result["id"] == "abc123"
    assert result["price_eur"] == 280000
    assert result["size_m2"] == 82
    assert result["has_terrace"] is True
    assert result["has_parking"] is True
    assert result["bathrooms"] == 2
    assert result["community_fee_month"] == max(80, int(82 * 1.5))

def test_handle_response_raises_on_error():
    scraper = IdealistaScraper.__new__(IdealistaScraper)
    mock_r = MagicMock(ok=False, status_code=403, text="Forbidden")
    with pytest.raises(ScraperError) as exc:
        scraper._handle_response(mock_r, "actor_id", "url")
    assert exc.value.status_code == 403
```

**Step 2:** Run → FAIL

**Step 3:** Implement `backend/src/scrapers/idealista.py`:
```python
import logging
import time

import requests

from src.config import Config
from src.models import UserCriteria

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

    def scrape(self, criteria: UserCriteria, max_items: int = 200) -> list[dict]:
        payload = {
            "location": criteria.location,
            "operation": "sale",
            "propertyType": self._map_property_type(criteria.property_type),
            "country": "es",
            "maxItems": max_items,
            "minSize": criteria.min_size_m2,
            "maxPrice": criteria.budget_eur,
            "garage": criteria.parking,
        }
        run_id = self._start_run(payload)
        self._await_run(run_id)
        return [self._normalize_listing(r) for r in self._fetch_items(run_id)]

    def scrape_rentals(self, criteria: UserCriteria, max_items: int = 50) -> list[dict]:
        payload = {
            "location": criteria.location,
            "operation": "rent",
            "propertyType": self._map_property_type(criteria.property_type),
            "country": "es",
            "maxItems": max_items,
        }
        run_id = self._start_run(payload)
        self._await_run(run_id)
        return self._fetch_items(run_id)

    def _map_property_type(self, prop_type: str) -> str:
        mapping = {"apartment": "flat", "house": "house", "any": "flat,house"}
        return mapping.get(prop_type, "flat,house")

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
            logger.error("Scraper | actor=%s status=%s body=%s", actor, r.status_code, r.text[:500])
            raise ScraperError(actor, url, r.status_code, r.text[:500])

    def _normalize_listing(self, raw: dict) -> dict:
        size = raw.get("size", 70)
        return {
            "id": str(raw.get("propertyCode", raw.get("id", ""))),
            "url": raw.get("url", ""),
            "address": raw.get("address", ""),
            "price_eur": raw.get("price", 0),
            "size_m2": size,
            "floor": str(raw.get("floor", "")),
            "floor_label": str(raw.get("floor", "")),
            "rooms": raw.get("rooms", 0),
            "bathrooms": raw.get("bathrooms", 1),
            "has_terrace": raw.get("features", {}).get("hasTerrace", False),
            "has_parking": raw.get("parkingSpace", {}).get("hasParkingSpace", False),
            "community_fee_month": max(80, int(size * 1.5)),
            "new_development": raw.get("newDevelopment", False),
            "description": raw.get("description", ""),
            "lat": raw.get("latitude"),
            "lng": raw.get("longitude"),
            "location": raw.get("municipality", ""),
        }
```

**Step 4:** Run → PASS

**Step 5:** Commit:
```bash
git commit -m "feat: add Idealista scraper with sale and rental modes"
```

---

## Phase 2 — Analysis Layer

### Task 4: `backend/src/analyzers/str_revenue.py`

**Note:** AirROI API confirmed live. Required params: `lat`, `lng`, `bedrooms`, `baths`, `guests`. Response includes `revenue` directly (not calculated).

**Files:**
- Create: `backend/src/analyzers/str_revenue.py`
- Create: `backend/tests/test_str_revenue.py`

**Step 1:** Write failing test `backend/tests/test_str_revenue.py`:
```python
import pytest
from unittest.mock import patch
from src.analyzers.str_revenue import AirROIAnalyzer

MOCK_RESPONSE = {
    "revenue": 28429.15,
    "average_daily_rate": 156.22,
    "occupancy": 0.513,
    "monthly_revenue_distributions": [0.055, 0.057, 0.063, 0.065, 0.074, 0.100,
                                        0.140, 0.153, 0.103, 0.077, 0.053, 0.053],
}

def test_returns_revenue_from_api_field():
    analyzer = AirROIAnalyzer.__new__(AirROIAnalyzer)
    with patch.object(analyzer, "_call_api", return_value=MOCK_RESPONSE):
        result = analyzer.analyze_property(
            {"id": "p1", "lat": 36.5, "lng": -4.8, "rooms": 2, "bathrooms": 1, "size_m2": 80}
        )
    assert result["annual_revenue_eur"] == pytest.approx(28429.15, abs=0.01)
    assert result["occupancy_rate_pct"] == 51.3
    assert result["adr_eur"] == pytest.approx(156.22, abs=0.01)
    assert result["property_id"] == "p1"
    assert result["monthly_distributions"] is not None
    assert len(result["monthly_distributions"]) == 12
    assert result["error"] is None

def test_build_params_includes_baths():
    analyzer = AirROIAnalyzer.__new__(AirROIAnalyzer)
    params = analyzer._build_params({"lat": 36.5, "lng": -4.8, "rooms": 3, "bathrooms": 2, "size_m2": 90})
    assert params["bedrooms"] == 3
    assert params["baths"] == 2
    assert params["guests"] == 6

def test_build_params_baths_fallback():
    """When bathrooms missing, derive from bedrooms."""
    analyzer = AirROIAnalyzer.__new__(AirROIAnalyzer)
    params = analyzer._build_params({"lat": 36.5, "lng": -4.8, "rooms": 3, "size_m2": 90})
    assert params["baths"] == max(1, 3 - 1)

def test_handles_api_error_gracefully():
    analyzer = AirROIAnalyzer.__new__(AirROIAnalyzer)
    with patch.object(analyzer, "_call_api", side_effect=Exception("timeout")):
        result = analyzer.analyze_property(
            {"id": "p1", "lat": 36.5, "lng": -4.8, "rooms": 2, "bathrooms": 1, "size_m2": 80}
        )
    assert result["annual_revenue_eur"] is None
    assert result["error"] == "timeout"
```

**Step 2:** Run → FAIL

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
            response = self._call_api(self._build_params(listing))
            return self._parse_response(listing["id"], response)
        except Exception as exc:
            logger.error("AirROI | property_id=%s error=%s", listing["id"], exc)
            return self._error_result(listing["id"], str(exc))

    def _build_params(self, listing: dict) -> dict:
        bedrooms = listing.get("rooms", 2)
        baths = listing.get("bathrooms") or max(1, bedrooms - 1)
        return {
            "lat": listing["lat"],
            "lng": listing["lng"],
            "bedrooms": bedrooms,
            "baths": baths,
            "guests": bedrooms * 2,
        }

    def _call_api(self, params: dict) -> dict:
        r = self._session.get(self._cfg.AIRROI_BASE_URL, params=params, timeout=30)
        if not r.ok:
            raise Exception(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def _parse_response(self, property_id: str, data: dict) -> dict:
        revenue = data.get("revenue") or 0
        occupancy = data.get("occupancy") or 0
        adr = data.get("average_daily_rate") or 0
        return {
            "property_id": property_id,
            "annual_revenue_eur": round(revenue, 2),
            "monthly_avg_revenue_eur": round(revenue / 12, 2),
            "occupancy_rate_pct": round(occupancy * 100, 1),
            "adr_eur": round(adr, 2),
            "monthly_distributions": data.get("monthly_revenue_distributions"),
            "error": None,
        }

    def _error_result(self, property_id: str, error: str) -> dict:
        return {
            "property_id": property_id,
            "annual_revenue_eur": None,
            "monthly_avg_revenue_eur": None,
            "occupancy_rate_pct": None,
            "adr_eur": None,
            "monthly_distributions": None,
            "error": error,
        }
```

**Step 4:** Run → PASS

**Step 5:** Commit:
```bash
git commit -m "feat: add AirROI STR analyzer — uses revenue field directly, includes baths param"
```

---

### Task 5: `backend/src/analyzers/ltr_revenue.py`

**Files:**
- Create: `backend/src/analyzers/ltr_revenue.py`
- Create: `backend/tests/test_ltr_revenue.py`

**Step 1:** Write failing test `backend/tests/test_ltr_revenue.py`:
```python
from unittest.mock import patch
from src.analyzers.ltr_revenue import LTRAnalyzer
from src.models import UserCriteria

CRITERIA = UserCriteria(location="Marbella", budget_eur=320000, min_size_m2=70)

MOCK_RENTALS = [
    {"price": 1800, "size": 80},
    {"price": 2000, "size": 90},
    {"price": 1600, "size": 75},
]

def test_computes_avg_monthly_rent():
    analyzer = LTRAnalyzer.__new__(LTRAnalyzer)
    with patch.object(analyzer, "_fetch_rentals", return_value=MOCK_RENTALS):
        result = analyzer.analyze(CRITERIA)
    assert result["avg_monthly_rent_eur"] == pytest.approx(1800.0, abs=1.0)
    assert result["location"] == "Marbella"
    assert result["comparables_count"] == 3
    assert result["error"] is None

def test_computes_rent_per_m2():
    analyzer = LTRAnalyzer.__new__(LTRAnalyzer)
    with patch.object(analyzer, "_fetch_rentals", return_value=MOCK_RENTALS):
        result = analyzer.analyze(CRITERIA)
    expected = (1800/80 + 2000/90 + 1600/75) / 3
    assert result["rent_per_m2_month"] == pytest.approx(expected, abs=0.1)

def test_returns_error_on_empty_results():
    analyzer = LTRAnalyzer.__new__(LTRAnalyzer)
    with patch.object(analyzer, "_fetch_rentals", return_value=[]):
        result = analyzer.analyze(CRITERIA)
    assert result["avg_monthly_rent_eur"] is None
    assert result["error"] == "No rental listings found"

def test_handles_scraper_exception():
    analyzer = LTRAnalyzer.__new__(LTRAnalyzer)
    with patch.object(analyzer, "_fetch_rentals", side_effect=Exception("timeout")):
        result = analyzer.analyze(CRITERIA)
    assert result["avg_monthly_rent_eur"] is None
    assert "timeout" in result["error"]
```

**Step 2:** Run → FAIL

**Step 3:** Implement `backend/src/analyzers/ltr_revenue.py`:
```python
import logging

from src.models import UserCriteria
from src.scrapers.idealista import IdealistaScraper

logger = logging.getLogger(__name__)


class LTRAnalyzer:
    def __init__(self) -> None:
        self._scraper = IdealistaScraper()

    def analyze(self, criteria: UserCriteria) -> dict:
        try:
            rentals = self._fetch_rentals(criteria)
            if not rentals:
                return self._error_result(criteria.location, "No rental listings found")
            return self._compute(criteria.location, rentals)
        except Exception as exc:
            logger.error("LTR | location=%s error=%s", criteria.location, exc)
            return self._error_result(criteria.location, str(exc))

    def _fetch_rentals(self, criteria: UserCriteria) -> list[dict]:
        return self._scraper.scrape_rentals(criteria, max_items=50)

    def _compute(self, location: str, rentals: list[dict]) -> dict:
        prices = [r["price"] for r in rentals if r.get("price")]
        per_m2 = [r["price"] / r["size"] for r in rentals
                  if r.get("price") and r.get("size", 0) > 0]
        avg_rent = sum(prices) / len(prices)
        avg_per_m2 = sum(per_m2) / len(per_m2) if per_m2 else None
        return {
            "location": location,
            "avg_monthly_rent_eur": round(avg_rent, 2),
            "rent_per_m2_month": round(avg_per_m2, 2) if avg_per_m2 else None,
            "comparables_count": len(prices),
            "data_source": "Idealista rental listings via Apify",
            "error": None,
        }

    def _error_result(self, location: str, error: str) -> dict:
        return {
            "location": location,
            "avg_monthly_rent_eur": None,
            "rent_per_m2_month": None,
            "comparables_count": 0,
            "data_source": "Idealista rental listings via Apify",
            "error": error,
        }
```

**Step 4:** Run → PASS

**Step 5:** Commit:
```bash
git commit -m "feat: add LTR analyzer — Idealista rental scraper with avg rent/m²"
```

---

### Task 6: `backend/src/analyzers/capital_growth.py`

**Note:** INE REST API is public, no auth required. URL: `https://servicios.ine.es/wstempus/js/es/DATOS_TABLA/49300?tip=AM`

**Files:**
- Create: `backend/src/analyzers/capital_growth.py`
- Create: `backend/tests/test_capital_growth.py`

**Step 1:** Write failing test `backend/tests/test_capital_growth.py`:
```python
import pytest
from unittest.mock import patch
from src.analyzers.capital_growth import CapitalGrowthAnalyzer

MOCK_INE_RESPONSE = [
    {"Nombre": "Tasa de Variación - Andalucía", "Data": [
        {"Anyo": 2023, "Valor": 11.2},
        {"Anyo": 2024, "Valor": 13.1},
    ]},
    {"Nombre": "Índice General - Andalucía", "Data": [
        {"Anyo": 2024, "Valor": 198.5},
    ]},
    {"Nombre": "Tasa de Variación - Cataluña", "Data": [
        {"Anyo": 2024, "Valor": 9.8},
    ]},
]

def test_extracts_yoy_for_andalucia():
    analyzer = CapitalGrowthAnalyzer.__new__(CapitalGrowthAnalyzer)
    with patch.object(analyzer, "_fetch_ine", return_value=MOCK_INE_RESPONSE):
        result = analyzer.analyze("Marbella")
    assert result["yoy_appreciation_pct"] == pytest.approx(13.1, abs=0.1)
    assert result["ccaa"] == "Andalucía"
    assert result["location"] == "Marbella"
    assert result["error"] is None

def test_extracts_yoy_for_cataluna():
    analyzer = CapitalGrowthAnalyzer.__new__(CapitalGrowthAnalyzer)
    with patch.object(analyzer, "_fetch_ine", return_value=MOCK_INE_RESPONSE):
        result = analyzer.analyze("Barcelona")
    assert result["yoy_appreciation_pct"] == pytest.approx(9.8, abs=0.1)
    assert result["ccaa"] == "Cataluña"

def test_unknown_location_returns_none():
    analyzer = CapitalGrowthAnalyzer.__new__(CapitalGrowthAnalyzer)
    with patch.object(analyzer, "_fetch_ine", return_value=MOCK_INE_RESPONSE):
        result = analyzer.analyze("UnknownCity")
    assert result["yoy_appreciation_pct"] is None
    assert result["error"] == "Location not mapped to CCAA"

def test_handles_ine_error():
    analyzer = CapitalGrowthAnalyzer.__new__(CapitalGrowthAnalyzer)
    with patch.object(analyzer, "_fetch_ine", side_effect=Exception("timeout")):
        result = analyzer.analyze("Marbella")
    assert result["yoy_appreciation_pct"] is None
    assert "timeout" in result["error"]
```

**Step 2:** Run → FAIL

**Step 3:** Implement `backend/src/analyzers/capital_growth.py`:
```python
import logging

import requests

from src.config import Config

logger = logging.getLogger(__name__)

LOCATION_TO_CCAA: dict[str, str] = {
    "marbella": "Andalucía", "estepona": "Andalucía", "málaga": "Andalucía",
    "malaga": "Andalucía", "nerja": "Andalucía", "torremolinos": "Andalucía",
    "barcelona": "Cataluña", "sitges": "Cataluña", "tarragona": "Cataluña",
    "madrid": "Comunidad de Madrid", "alcalá": "Comunidad de Madrid",
    "valencia": "Comunitat Valenciana", "alicante": "Comunitat Valenciana",
    "benidorm": "Comunitat Valenciana", "dénia": "Comunitat Valenciana",
    "palma": "Illes Balears", "ibiza": "Illes Balears", "menorca": "Illes Balears",
}


class CapitalGrowthAnalyzer:
    def __init__(self) -> None:
        self._cfg = Config()

    def analyze(self, location: str) -> dict:
        ccaa = LOCATION_TO_CCAA.get(location.lower().strip())
        if not ccaa:
            return self._result(location, None, None, "Location not mapped to CCAA")
        try:
            data = self._fetch_ine()
            yoy = self._extract_yoy(data, ccaa)
            data_year = self._extract_year(data, ccaa)
            return self._result(location, ccaa, yoy, None, data_year)
        except Exception as exc:
            logger.error("INE | location=%s error=%s", location, exc)
            return self._result(location, ccaa, None, str(exc))

    def _fetch_ine(self) -> list[dict]:
        r = requests.get(self._cfg.INE_IPV_TABLE_URL, timeout=30)
        r.raise_for_status()
        return r.json()

    def _extract_yoy(self, data: list[dict], ccaa: str) -> float | None:
        for series in data:
            name = series.get("Nombre", "")
            if ccaa in name and "Tasa" in name and series.get("Data"):
                latest = max(series["Data"], key=lambda d: d.get("Anyo", 0))
                return latest.get("Valor")
        return None

    def _extract_year(self, data: list[dict], ccaa: str) -> int | None:
        for series in data:
            name = series.get("Nombre", "")
            if ccaa in name and "Tasa" in name and series.get("Data"):
                latest = max(series["Data"], key=lambda d: d.get("Anyo", 0))
                return latest.get("Anyo")
        return None

    def _result(self, location: str, ccaa: str | None, yoy: float | None,
                error: str | None, data_year: int | None = None) -> dict:
        return {
            "location": location,
            "ccaa": ccaa,
            "yoy_appreciation_pct": yoy,
            "data_year": data_year,
            "data_source": "INE IPV tabla 49300",
            "error": error,
        }
```

**Step 4:** Run → PASS

**Step 5:** Commit:
```bash
git commit -m "feat: add capital growth analyzer via INE REST API"
```

---

### Task 7: `backend/src/analyzers/roi.py`

**Key change:** Accepts both `str_est` and `ltr_data`. Computes STR net yield, LTR net yield, and `preferred_rental_type`. Scoring remains on absolute scale (independent of user thresholds).

**Files:**
- Create: `backend/src/analyzers/roi.py`
- Create: `backend/tests/test_roi.py`

**Step 1:** Write failing test `backend/tests/test_roi.py`:
```python
import pytest
from src.analyzers.roi import ROIAnalyzer
from src.models import UserCriteria

CRITERIA_BARE = UserCriteria(location="Marbella", budget_eur=320000)
CRITERIA_WITH = UserCriteria(location="Marbella", budget_eur=320000,
                              min_net_yield_pct=5.0, min_capital_growth_pct=3.0)

LISTING = {"id": "p1", "price_eur": 285000, "community_fee_month": 150}
STR_EST = {"property_id": "p1", "annual_revenue_eur": 28500, "occupancy_rate_pct": 72, "error": None}
LTR_DATA = {"avg_monthly_rent_eur": 1800, "error": None}

def test_gross_yield_calculation():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, CRITERIA_BARE)
    assert abs(result["str_gross_yield_pct"] - 10.0) < 0.1
    assert result["acquisition_cost"] == pytest.approx(285000 * 1.10)

def test_ltr_net_yield_computed():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, CRITERIA_BARE)
    assert result["ltr_net_yield_pct"] is not None
    assert result["ltr_net_yield_pct"] > 0

def test_preferred_rental_type_str_when_str_higher():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, CRITERIA_BARE)
    assert result["preferred_rental_type"] in {"STR", "LTR"}

def test_score_is_capped_at_10():
    listing = {"id": "p1", "price_eur": 200000, "community_fee_month": 100}
    str_est = {"property_id": "p1", "annual_revenue_eur": 40000, "occupancy_rate_pct": 95, "error": None}
    result = ROIAnalyzer().compute_property(listing, str_est, LTR_DATA, CRITERIA_BARE)
    assert result["investment_score"] <= 10.0

def test_score_independent_of_user_threshold():
    result_a = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, CRITERIA_BARE)
    result_b = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, CRITERIA_WITH)
    assert result_a["investment_score"] == result_b["investment_score"]

def test_verdict_buy_when_exceeds_thresholds():
    listing = {"id": "p1", "price_eur": 250000, "community_fee_month": 120}
    str_est = {"property_id": "p1", "annual_revenue_eur": 30000, "occupancy_rate_pct": 80, "error": None}
    result = ROIAnalyzer().compute_property(listing, str_est, LTR_DATA, CRITERIA_WITH,
                                             capital_growth_pct=4.0)
    assert result["verdict"] == "BUY"

def test_verdict_skip_when_below_yield():
    listing = {"id": "p1", "price_eur": 310000, "community_fee_month": 200}
    str_est = {"property_id": "p1", "annual_revenue_eur": 10000, "occupancy_rate_pct": 40, "error": None}
    result = ROIAnalyzer().compute_property(listing, str_est, LTR_DATA, CRITERIA_WITH)
    assert result["verdict"] == "SKIP"

def test_none_str_yield_falls_back_to_ltr():
    str_est = {"property_id": "p1", "annual_revenue_eur": None, "error": "API failed"}
    result = ROIAnalyzer().compute_property(LISTING, str_est, LTR_DATA, CRITERIA_BARE)
    assert result["str_net_yield_pct"] is None
    assert result["ltr_net_yield_pct"] is not None

def test_none_ltr_data_handled():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, None, CRITERIA_BARE)
    assert result["ltr_net_yield_pct"] is None
    assert result["preferred_rental_type"] == "STR"
```

**Step 2:** Run → FAIL

**Step 3:** Implement `backend/src/analyzers/roi.py`:
```python
from src.config import Config
from src.models import UserCriteria

_YIELD_REFERENCE_PCT = 10.0
_GROWTH_REFERENCE_PCT = 8.0
_YIELD_DEFAULT_THRESHOLD = 5.0
_GROWTH_DEFAULT_THRESHOLD = 2.0


class ROIAnalyzer:
    def __init__(self) -> None:
        self._cfg = Config()

    def compute_all(self, listings: list[dict], str_data: list[dict],
                    ltr_data: dict | None, criteria: UserCriteria,
                    capital_growth_pct: float | None = None) -> list[dict]:
        str_by_id = {s["property_id"]: s for s in str_data}
        return [
            self.compute_property(l, str_by_id.get(l["id"], {}), ltr_data,
                                  criteria, capital_growth_pct)
            for l in listings
        ]

    def compute_property(self, listing: dict, str_est: dict,
                         ltr_data: dict | None, criteria: UserCriteria,
                         capital_growth_pct: float | None = None) -> dict:
        price = listing["price_eur"]
        acq = round(price * (1 + self._cfg.TRANSACTION_COST_PCT), 2)
        str_revenue = str_est.get("annual_revenue_eur")
        ltr_monthly = ltr_data.get("avg_monthly_rent_eur") if ltr_data else None
        community = listing.get("community_fee_month", 150) * 12
        ibi = price * 0.60 * 0.005

        str_net_yield = self._str_yield(str_revenue, acq, community, ibi)
        ltr_net_yield = self._ltr_yield(ltr_monthly, acq, community, ibi)
        preferred = self._preferred(str_net_yield, ltr_net_yield)
        best_yield = str_net_yield if preferred == "STR" else (ltr_net_yield or str_net_yield)

        occupancy = str_est.get("occupancy_rate_pct") or 0
        score = self._score(best_yield or 0, occupancy, capital_growth_pct)
        verdict = self._verdict(best_yield or 0, capital_growth_pct, criteria)

        return {
            "property_id": listing["id"],
            "purchase_price": price,
            "acquisition_cost": acq,
            "str_annual_revenue_eur": str_revenue,
            "str_gross_yield_pct": round((str_revenue / price) * 100, 2) if str_revenue else None,
            "str_net_yield_pct": round(str_net_yield, 2) if str_net_yield is not None else None,
            "ltr_monthly_rent_eur": ltr_monthly,
            "ltr_net_yield_pct": round(ltr_net_yield, 2) if ltr_net_yield is not None else None,
            "preferred_rental_type": preferred,
            "community_fees_yr": community,
            "ibi_yr": round(ibi, 2),
            "capital_growth_pct": capital_growth_pct,
            "investment_score": score,
            "verdict": verdict,
        }

    def _str_yield(self, revenue: float | None, acq: float,
                   community: float, ibi: float) -> float | None:
        if revenue is None:
            return None
        opex = revenue * self._cfg.STR_OPEX_PCT
        net = revenue - opex - community - ibi
        return (net / acq) * 100

    def _ltr_yield(self, monthly_rent: float | None, acq: float,
                   community: float, ibi: float) -> float | None:
        if monthly_rent is None:
            return None
        annual = monthly_rent * 12
        opex = annual * self._cfg.LTR_OPEX_PCT
        net = annual - opex - community - ibi
        return (net / acq) * 100

    def _preferred(self, str_yield: float | None, ltr_yield: float | None) -> str:
        if str_yield is None:
            return "LTR"
        if ltr_yield is None:
            return "STR"
        return "STR" if str_yield >= ltr_yield else "LTR"

    def _score(self, net_yield: float, occupancy: float,
               capital_growth_pct: float | None) -> float:
        yield_score = min(net_yield / _YIELD_REFERENCE_PCT, 1.0)
        occ_score = min(occupancy / 100.0, 1.0)
        growth_score = min((capital_growth_pct or 0) / _GROWTH_REFERENCE_PCT, 1.0)
        return round((yield_score * 0.5 + occ_score * 0.3 + growth_score * 0.2) * 10, 1)

    def _verdict(self, net_yield: float, capital_growth_pct: float | None,
                 criteria: UserCriteria) -> str:
        yield_threshold = criteria.min_net_yield_pct or _YIELD_DEFAULT_THRESHOLD
        growth_threshold = criteria.min_capital_growth_pct or _GROWTH_DEFAULT_THRESHOLD
        yield_ok = net_yield >= yield_threshold
        growth_ok = (capital_growth_pct or 0) >= growth_threshold
        if yield_ok and growth_ok:
            return "BUY"
        if yield_ok or growth_ok:
            return "WATCH"
        return "SKIP"
```

**Step 4:** Run → PASS

**Step 5:** Commit:
```bash
git commit -m "feat: add ROI calculator with STR + LTR dual yield and preferred_rental_type"
```

---

## Phase 3 — Filter + Async API

### Task 8: `backend/src/filters/property_filter.py`

**Files:**
- Create: `backend/src/filters/property_filter.py`
- Create: `backend/tests/test_filter.py`

**Step 1:** Write failing test `backend/tests/test_filter.py`:
```python
from src.filters.property_filter import PropertyFilter
from src.models import UserCriteria

CRITERIA = UserCriteria(
    location="Marbella", budget_eur=300000,
    property_type="apartment", bedrooms=2, min_size_m2=70,
    parking=True, terrace=True,
)
BASE = {"id": "p1", "price_eur": 280000, "size_m2": 82, "rooms": 2,
        "floor_label": "2ª planta", "has_terrace": True, "has_parking": True}
ROI = {"property_id": "p1", "str_net_yield_pct": 6.2, "ltr_net_yield_pct": 4.1,
       "investment_score": 7.5, "verdict": "BUY"}

def test_passing_property_included():
    assert len(PropertyFilter().filter([BASE], [ROI], CRITERIA)) == 1

def test_over_budget_excluded():
    c = UserCriteria("Marbella", 200000, "apartment", 2, 70, parking=True, terrace=True)
    assert len(PropertyFilter().filter([BASE], [ROI], c)) == 0

def test_no_terrace_excluded():
    listing = {**BASE, "has_terrace": False}
    assert len(PropertyFilter().filter([listing], [ROI], CRITERIA)) == 0

def test_no_parking_excluded():
    listing = {**BASE, "has_parking": False}
    assert len(PropertyFilter().filter([listing], [ROI], CRITERIA)) == 0

def test_floor_preference_top_matches():
    listing = {**BASE, "floor_label": "ático"}
    c = UserCriteria("Marbella", 300000, "apartment", 2, 70,
                     parking=True, terrace=True, floor_preference="top")
    assert len(PropertyFilter().filter([listing], [ROI], c)) == 1

def test_floor_preference_top_excludes_mid():
    c = UserCriteria("Marbella", 300000, "apartment", 2, 70,
                     parking=True, terrace=True, floor_preference="top")
    assert len(PropertyFilter().filter([BASE], [ROI], c)) == 0
```

**Step 2:** Run → FAIL

**Step 3:** Implement `backend/src/filters/property_filter.py`:
```python
from src.models import UserCriteria

_FLOOR_LABELS: dict[str, set[str]] = {
    "ground": {"bajo", "planta baja", "pb", "0", "ground"},
    "low": {"1", "2", "primera", "segunda"},
    "mid": {"3", "4", "5", "tercera", "cuarta", "quinta"},
    "high": {"6", "7", "8", "sexta", "séptima"},
    "top": {"atico", "ático", "top", "penthouse"},
}


class PropertyFilter:
    def filter(self, listings: list[dict], roi_data: list[dict],
               criteria: UserCriteria) -> list[dict]:
        roi_by_id = {r["property_id"]: r for r in roi_data}
        return [
            {**l, **roi_by_id.get(l["id"], {})}
            for l in listings
            if self._passes(l, roi_by_id.get(l["id"], {}), criteria)
        ]

    def _passes(self, listing: dict, roi: dict, criteria: UserCriteria) -> bool:
        checks = [
            listing.get("price_eur", 0) <= criteria.budget_eur,
            listing.get("size_m2", 0) >= criteria.min_size_m2,
            listing.get("rooms", 0) >= criteria.bedrooms,
        ]
        if criteria.terrace:
            checks.append(bool(listing.get("has_terrace")))
        if criteria.parking:
            checks.append(bool(listing.get("has_parking")))
        if criteria.floor_preference and criteria.floor_preference != "any":
            checks.append(self._matches_floor(listing, criteria.floor_preference))
        if criteria.min_net_yield_pct:
            best = max(
                roi.get("str_net_yield_pct") or 0,
                roi.get("ltr_net_yield_pct") or 0,
            )
            checks.append(best >= criteria.min_net_yield_pct)
        return all(checks)

    def _matches_floor(self, listing: dict, preference: str) -> bool:
        floor_label = str(listing.get("floor_label", "")).lower()
        return any(label in floor_label for label in _FLOOR_LABELS.get(preference, set()))
```

**Step 4:** Run → PASS

**Step 5:** Commit:
```bash
git commit -m "feat: add property filter with STR+LTR yield threshold check"
```

---

### Task 9: `backend/src/reporters/pipeline.py` + `backend/src/main.py`

**Step 1:** Implement `backend/src/reporters/pipeline.py`:
```python
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from src.models import UserCriteria
from src.scrapers.idealista import IdealistaScraper
from src.analyzers.str_revenue import AirROIAnalyzer
from src.analyzers.ltr_revenue import LTRAnalyzer
from src.analyzers.capital_growth import CapitalGrowthAnalyzer
from src.analyzers.roi import ROIAnalyzer
from src.filters.property_filter import PropertyFilter

_runs: dict[str, dict] = {}


def start_run(criteria: UserCriteria) -> str:
    run_id = str(uuid.uuid4())[:8]
    _runs[run_id] = {
        "status": "running",
        "location": criteria.location,
        "criteria": {
            "budget_eur": criteria.budget_eur,
            "min_net_yield_pct": criteria.min_net_yield_pct,
            "min_capital_growth_pct": criteria.min_capital_growth_pct,
            "property_type": criteria.property_type,
            "min_size_m2": criteria.min_size_m2,
        },
        "started_at": datetime.now().isoformat(),
    }
    return run_id


def run_pipeline(run_id: str, criteria: UserCriteria) -> None:
    """Blocking — must run in thread pool, not event loop."""
    try:
        out = Path("outputs/data")
        out.mkdir(parents=True, exist_ok=True)

        listings = IdealistaScraper().scrape(criteria)
        _save(out / f"{run_id}_listings.json", listings)

        # STR, LTR, and capital growth run in parallel
        with ThreadPoolExecutor(max_workers=3) as pool:
            str_future = pool.submit(AirROIAnalyzer().analyze_batch, listings)
            ltr_future = pool.submit(LTRAnalyzer().analyze, criteria)
            growth_future = pool.submit(CapitalGrowthAnalyzer().analyze, criteria.location)
            str_data = str_future.result()
            ltr_data = ltr_future.result()
            growth_data = growth_future.result()

        _save(out / f"{run_id}_str.json", str_data)
        _save(out / f"{run_id}_ltr.json", [ltr_data])
        _save(out / f"{run_id}_capital_growth.json", [growth_data])

        capital_growth_pct = growth_data.get("yoy_appreciation_pct")
        roi_data = ROIAnalyzer().compute_all(listings, str_data, ltr_data, criteria, capital_growth_pct)
        _save(out / f"{run_id}_roi.json", roi_data)

        filtered = PropertyFilter().filter(listings, roi_data, criteria)
        _save(out / f"{run_id}_filtered.json", filtered)

        _runs[run_id].update({
            "status": "completed",
            "generated_at": datetime.now().isoformat(),
            "total_scraped": len(listings),
            "total_passing": len(filtered),
            "properties": filtered,
            "market": {
                "yoy_appreciation_pct": capital_growth_pct,
                "ccaa": growth_data.get("ccaa"),
                "data_year": growth_data.get("data_year"),
                "vft_risk": None,   # enriched later by agents
                "ltr_avg_rent_eur": ltr_data.get("avg_monthly_rent_eur"),
                "ltr_comparables": ltr_data.get("comparables_count"),
            },
        })
    except Exception as exc:
        _runs[run_id].update({"status": "failed", "error": str(exc)})


def get_run(run_id: str) -> dict | None:
    return _runs.get(run_id)


def update_market(run_id: str, market_data: dict) -> bool:
    if run_id not in _runs:
        return False
    _runs[run_id]["market"] = {**(_runs[run_id].get("market") or {}), **market_data}
    return True


def _save(path: Path, data: list[dict] | dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
```

**Step 2:** Implement `backend/src/main.py`:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.models import AnalysisRequest
from src.reporters.pipeline import start_run, run_pipeline, get_run, update_market

app = FastAPI(title="Real Estate Investment Advisor")
_executor = ThreadPoolExecutor(max_workers=3)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/analysis", status_code=202)
async def create_analysis(req: AnalysisRequest) -> dict:
    criteria = req.to_criteria()
    run_id = start_run(criteria)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, run_pipeline, run_id, criteria)
    return {"run_id": run_id, "status": "running"}


@app.get("/api/analysis/{run_id}")
async def get_analysis(run_id: str) -> dict:
    result = get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@app.put("/api/analysis/{run_id}/market")
async def enrich_market(run_id: str, market_data: dict) -> dict:
    if not update_market(run_id, market_data):
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "updated"}


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
```

**Step 3:** Verify:
```bash
cd backend && uv run uvicorn src.main:app --reload
curl http://localhost:8000/api/health
# {"status": "ok"}
```

**Step 4:** Commit:
```bash
git commit -m "feat: async pipeline with STR + LTR + capital growth running in parallel"
```

---

## Phase 4 — React Frontend

### Task 10: Frontend scaffold

```bash
cd /Users/richardgrom/Documents/Richard\ /Real_estate_analyses/frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install lightweight-charts
npm install @radix-ui/react-slot class-variance-authority clsx tailwind-merge lucide-react
npx shadcn@latest init
npx shadcn@latest add table badge card input label button
```

`vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
```

Commit: `git commit -m "chore: scaffold React frontend"`

---

### Task 11: TypeScript types + polling hook

**Files:**
- Create: `frontend/src/types/analysis.ts`
- Create: `frontend/src/hooks/useAnalysis.ts`

**Step 1:** `frontend/src/types/analysis.ts`:
```typescript
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
  // STR
  str_annual_revenue_eur: number | null
  str_gross_yield_pct: number | null
  str_net_yield_pct: number | null
  occupancy_rate_pct: number | null
  monthly_distributions: number[] | null
  // LTR
  ltr_monthly_rent_eur: number | null
  ltr_net_yield_pct: number | null
  // Combined
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
```

**Step 2:** `frontend/src/hooks/useAnalysis.ts`:
```typescript
import { useState, useRef } from 'react'
import type { AnalysisRequest, AnalysisResult } from '../types/analysis'

type Status = 'idle' | 'loading' | 'polling' | 'success' | 'error'

export function useAnalysis() {
  const [status, setStatus] = useState<Status>('idle')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current)
  }

  const analyze = async (req: AnalysisRequest) => {
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
```

Commit: `git commit -m "feat: add TypeScript types with STR+LTR fields and polling hook"`

---

### Task 12: Frontend components

**Files:**
- Create: `frontend/src/components/InvestmentForm.tsx`
- Create: `frontend/src/components/ExecutiveSummary.tsx`
- Create: `frontend/src/components/PropertyTable.tsx`
- Create: `frontend/src/components/MarketOverview.tsx`
- Create: `frontend/src/components/YieldChart.tsx`
- Create: `frontend/src/components/RiskIndicators.tsx`
- Update: `frontend/src/App.tsx`

**Step 1:** `InvestmentForm.tsx`:
```tsx
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import type { AnalysisRequest } from '../types/analysis'

interface Props { onSubmit: (req: AnalysisRequest) => void; loading: boolean }

export function InvestmentForm({ onSubmit, loading }: Props) {
  const [form, setForm] = useState<AnalysisRequest>({
    location: '', budget_eur: 320000, property_type: 'any',
    bedrooms: 2, min_size_m2: 70, parking: false, terrace: false,
  })

  const set = (key: keyof AnalysisRequest) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const numInt = ['budget_eur', 'min_size_m2', 'bedrooms']
      const numFloat = ['min_net_yield_pct', 'min_capital_growth_pct']
      const bools = ['parking', 'terrace']
      let value: string | number | boolean | undefined = e.target.value
      if (numInt.includes(key)) value = parseInt(e.target.value) || 0
      else if (numFloat.includes(key)) value = e.target.value ? parseFloat(e.target.value) : undefined
      else if (bools.includes(key)) value = (e.target as HTMLInputElement).checked
      setForm(prev => ({ ...prev, [key]: value }))
    }

  return (
    <Card>
      <CardHeader><CardTitle>Investment Parameters</CardTitle></CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="col-span-2 sm:col-span-1">
          <Label>Location</Label>
          <Input placeholder="Marbella" value={form.location} onChange={set('location')} />
        </div>
        <div>
          <Label>Max Budget (€)</Label>
          <Input type="number" value={form.budget_eur} onChange={set('budget_eur')} />
        </div>
        <div>
          <Label>Bedrooms</Label>
          <Input type="number" value={form.bedrooms} onChange={set('bedrooms')} />
        </div>
        <div>
          <Label>Min Size (m²)</Label>
          <Input type="number" value={form.min_size_m2} onChange={set('min_size_m2')} />
        </div>
        <div>
          <Label>Min Net Yield (%)</Label>
          <Input type="number" step="0.5" placeholder="5.0" onChange={set('min_net_yield_pct')} />
        </div>
        <div>
          <Label>Min Capital Growth (%/yr)</Label>
          <Input type="number" step="0.5" placeholder="3.0" onChange={set('min_capital_growth_pct')} />
        </div>
        <div>
          <Label>Property Type</Label>
          <select className="w-full border rounded px-3 py-2 bg-background text-sm"
                  value={form.property_type} onChange={set('property_type')}>
            <option value="any">Any</option>
            <option value="apartment">Apartment</option>
            <option value="house">House</option>
          </select>
        </div>
        <div className="flex items-center gap-4 col-span-2 sm:col-span-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.parking} onChange={set('parking')} />
            Parking required
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.terrace} onChange={set('terrace')} />
            Terrace required
          </label>
        </div>
        <div className="col-span-2 sm:col-span-3 flex justify-end">
          <Button onClick={() => onSubmit(form)} disabled={loading || !form.location.trim()}>
            {loading ? 'Analyzing…' : 'Find Investments'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
```

**Step 2:** `ExecutiveSummary.tsx`:
```tsx
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AnalysisResult } from '../types/analysis'

const VARIANT = { BUY: 'default', WATCH: 'secondary', SKIP: 'destructive' } as const

export function ExecutiveSummary({ result }: { result: AnalysisResult }) {
  const top3 = [...result.properties]
    .sort((a, b) => (b.investment_score ?? 0) - (a.investment_score ?? 0))
    .slice(0, 3)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Results — {result.location}</CardTitle>
        <p className="text-sm text-muted-foreground">
          {result.total_passing} of {result.total_scraped} properties match criteria
          · Budget €{result.criteria.budget_eur.toLocaleString()}
          {result.criteria.min_net_yield_pct && ` · Yield ≥${result.criteria.min_net_yield_pct}%`}
          {result.criteria.min_capital_growth_pct && ` · Growth ≥${result.criteria.min_capital_growth_pct}%/yr`}
        </p>
      </CardHeader>
      <CardContent className="flex gap-4 flex-wrap">
        {top3.map(p => (
          <div key={p.id} className="flex flex-col gap-1 min-w-52">
            <Badge variant={VARIANT[p.verdict]}>{p.verdict}</Badge>
            <span className="text-sm font-medium truncate">{p.address}</span>
            <span className="text-xs text-muted-foreground">
              €{p.price_eur.toLocaleString()}
              · STR {p.str_net_yield_pct?.toFixed(1) ?? 'N/A'}%
              · LTR {p.ltr_net_yield_pct?.toFixed(1) ?? 'N/A'}%
              · Score {p.investment_score}/10
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
```

**Step 3:** `PropertyTable.tsx`:
```tsx
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Property } from '../types/analysis'

const VERDICT_VARIANT = { BUY: 'default', WATCH: 'secondary', SKIP: 'destructive' } as const
const fmt = (n: number | null, suffix = '') => n != null ? `${n.toFixed(1)}${suffix}` : '—'

export function PropertyTable({ properties }: { properties: Property[] }) {
  const sorted = [...properties].sort((a, b) => (b.investment_score ?? 0) - (a.investment_score ?? 0))

  return (
    <Card>
      <CardHeader><CardTitle>Properties</CardTitle></CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground border-b">
              <th className="pb-2 pr-4">Address</th>
              <th className="pb-2 pr-4">Price</th>
              <th className="pb-2 pr-4">Size</th>
              <th className="pb-2 pr-4">STR Yield</th>
              <th className="pb-2 pr-4">LTR Yield</th>
              <th className="pb-2 pr-4">Growth</th>
              <th className="pb-2 pr-4">Score</th>
              <th className="pb-2">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(p => (
              <tr key={p.id} className="border-b last:border-0">
                <td className="py-2 pr-4">
                  <a href={p.url} target="_blank" rel="noreferrer"
                     className="hover:underline text-primary max-w-48 block truncate">
                    {p.address}
                  </a>
                </td>
                <td className="py-2 pr-4">€{p.price_eur.toLocaleString()}</td>
                <td className="py-2 pr-4">{p.size_m2} m²</td>
                <td className="py-2 pr-4 font-medium">{fmt(p.str_net_yield_pct, '%')}</td>
                <td className="py-2 pr-4 font-medium">{fmt(p.ltr_net_yield_pct, '%')}</td>
                <td className="py-2 pr-4">{fmt(p.capital_growth_pct, '%')}</td>
                <td className="py-2 pr-4">{fmt(p.investment_score)}/10</td>
                <td className="py-2">
                  <Badge variant={VERDICT_VARIANT[p.verdict]}>{p.verdict}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}
```

**Step 4:** `MarketOverview.tsx`:
```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { MarketData } from '../types/analysis'

const VFT_VARIANT = { low: 'default', medium: 'secondary', high: 'destructive' } as const

export function MarketOverview({ market, location }: { market: MarketData | null; location: string }) {
  if (!market) return null
  return (
    <Card>
      <CardHeader><CardTitle>Market — {location}</CardTitle></CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <p className="text-xs text-muted-foreground">Capital Growth (YoY)</p>
          <p className="text-xl font-bold">
            {market.yoy_appreciation_pct != null ? `${market.yoy_appreciation_pct.toFixed(1)}%` : '—'}
          </p>
          {market.data_year && <p className="text-xs text-muted-foreground">{market.ccaa} · {market.data_year}</p>}
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Avg LTR Rent</p>
          <p className="text-xl font-bold">
            {market.ltr_avg_rent_eur != null ? `€${market.ltr_avg_rent_eur.toLocaleString()}/mo` : '—'}
          </p>
          {market.ltr_comparables && <p className="text-xs text-muted-foreground">{market.ltr_comparables} comparables</p>}
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">VFT Regulatory Risk</p>
          {market.vft_risk
            ? <Badge variant={VFT_VARIANT[market.vft_risk]}>{market.vft_risk.toUpperCase()}</Badge>
            : <p className="text-sm text-muted-foreground">Run CLI for full analysis</p>}
        </div>
      </CardContent>
    </Card>
  )
}
```

**Step 5:** `YieldChart.tsx`:
```tsx
import { useEffect, useRef } from 'react'
import { createChart } from 'lightweight-charts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Property } from '../types/analysis'

export function YieldChart({ properties }: { properties: Property[] }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current || properties.length === 0) return
    const chart = createChart(ref.current, { width: ref.current.clientWidth, height: 300 })
    const strSeries = chart.addBarSeries({ color: '#3b82f6' })
    const ltrSeries = chart.addBarSeries({ color: '#10b981' })

    const sorted = [...properties]
      .sort((a, b) => (b.str_net_yield_pct ?? 0) - (a.str_net_yield_pct ?? 0))
      .slice(0, 20)

    strSeries.setData(sorted.map((p, i) => ({ time: i + 1 as any, value: p.str_net_yield_pct ?? 0 })))
    ltrSeries.setData(sorted.map((p, i) => ({ time: i + 1 as any, value: p.ltr_net_yield_pct ?? 0 })))
    chart.timeScale().fitContent()
    return () => chart.remove()
  }, [properties])

  return (
    <Card>
      <CardHeader>
        <CardTitle>STR vs LTR Net Yield</CardTitle>
        <p className="text-xs text-muted-foreground">Blue = STR · Green = LTR · Top 20 properties by STR yield</p>
      </CardHeader>
      <CardContent><div ref={ref} /></CardContent>
    </Card>
  )
}
```

**Step 6:** `RiskIndicators.tsx`:
```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { MarketData } from '../types/analysis'

export function RiskIndicators({ market }: { market: MarketData | null }) {
  if (!market) return null
  return (
    <Card>
      <CardHeader><CardTitle>Risk Indicators</CardTitle></CardHeader>
      <CardContent className="flex gap-6 flex-wrap">
        <div>
          <p className="text-xs text-muted-foreground mb-1">VFT Regulatory</p>
          {market.vft_risk
            ? <Badge variant={market.vft_risk === 'low' ? 'default' : market.vft_risk === 'medium' ? 'secondary' : 'destructive'}>
                {market.vft_risk.toUpperCase()}
              </Badge>
            : <span className="text-sm text-muted-foreground">N/A — CLI only</span>}
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">Capital Growth Trend</p>
          <span className="text-sm font-medium">
            {market.yoy_appreciation_pct != null
              ? `${market.yoy_appreciation_pct > 5 ? '↑ Strong' : market.yoy_appreciation_pct > 2 ? '→ Moderate' : '↓ Slow'} (${market.yoy_appreciation_pct.toFixed(1)}%/yr)`
              : 'N/A'}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
```

**Step 7:** `App.tsx`:
```tsx
import { useAnalysis } from './hooks/useAnalysis'
import { InvestmentForm } from './components/InvestmentForm'
import { ExecutiveSummary } from './components/ExecutiveSummary'
import { MarketOverview } from './components/MarketOverview'
import { PropertyTable } from './components/PropertyTable'
import { YieldChart } from './components/YieldChart'
import { RiskIndicators } from './components/RiskIndicators'

export default function App() {
  const { status, result, error, analyze } = useAnalysis()
  const isLoading = status === 'loading' || status === 'polling'

  return (
    <div className="min-h-screen bg-background text-foreground p-8 max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Real Estate Investment Advisor</h1>
      <p className="text-muted-foreground mb-8">Find STR and LTR investment properties in Spain</p>
      <InvestmentForm onSubmit={analyze} loading={isLoading} />
      {status === 'polling' && (
        <p className="text-sm text-muted-foreground mt-4 animate-pulse">
          Analyzing listings, STR revenue, LTR rentals, and capital growth…
        </p>
      )}
      {error && <p className="text-destructive mt-4">{error}</p>}
      {result?.status === 'completed' && (
        <div className="flex flex-col gap-6 mt-8">
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

**Step 8:** Build check:
```bash
cd frontend && npm run build
```
Expected: 0 TypeScript errors.

**Step 9:** Commit:
```bash
git commit -m "feat: complete dashboard with STR/LTR columns, market overview, yield chart"
```

---

## Verification

**All backend tests:**
```bash
cd backend && uv run pytest tests/ -v
```
Expected: all pass.

**FastAPI smoke test:**
```bash
cd backend && uv run uvicorn src.main:app --reload
curl -X POST http://localhost:8000/api/analysis \
  -H "Content-Type: application/json" \
  -d '{"location":"Marbella","budget_eur":320000,"min_net_yield_pct":5.0,"min_capital_growth_pct":3.0}'
# {"run_id": "abc12345", "status": "running"}
```

**Frontend full flow:**
1. `cd frontend && npm run dev`
2. Open `http://localhost:5173`
3. Fill: Marbella · €320k · 5% yield · 3% growth · Apartment
4. Click "Find Investments"
5. Status shows "Analyzing listings, STR revenue, LTR rentals, and capital growth…"
6. Results: PropertyTable shows STR Yield + LTR Yield as separate columns, MarketOverview shows YoY appreciation from INE

---

## Phase 5+ — Agent Layer

See `2026-04-15-multi-agent-system.md` Phase 5 and 6 — agent definitions remain unchanged except:

- `capital-growth-analyst` now **enriches** existing INE data with Exa.ai VFT risk (basic pipeline already fetched YoY from INE)
- `ltr-yield-analyst` agent enriches with deeper comparable analysis (basic pipeline already has avg rent)
- VFT risk field populated via `PUT /api/analysis/{run_id}/market` with `{"vft_risk": "low"|"medium"|"high"}`
