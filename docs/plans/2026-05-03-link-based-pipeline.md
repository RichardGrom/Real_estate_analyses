# Link-Based Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the search-based pipeline (8 params → list of listings) with a link-based pipeline (one URL → single property full analysis), using Playwright + `claude -p` CLI + Nominatim geocoding — zero external API cost.

**Architecture:** `LinkScraper` replaces `IdealistaScraper`; scrapes any classified site URL with Playwright, extracts structured data via `claude -p` subprocess, geocodes address via Nominatim if GPS missing. `PropertyFilter` and `verdict` are removed. Pipeline runs the same STR/LTR/INE/ROI analyzers on the single extracted listing. Frontend changes from 8-field form to single URL input + single result card.

**Tech Stack:** Python 3.11, uv, playwright (sync API), subprocess (`claude -p`), requests (Nominatim), FastAPI, React + TypeScript + Vite + Tailwind + shadcn

**Worktree:** `/Users/richardgrom/Documents/Richard /Real_estate_analyses/.worktrees/feature-multi-agent-v2/`

All `pytest` commands run from `backend/`. All `npm` commands run from `frontend/`.

---

## Task 1: LinkScraper — tests first

**Files:**
- Create: `backend/tests/test_link_scraper.py`
- Create: `backend/src/scrapers/link_scraper.py`

### Step 1: Write failing tests

Create `backend/tests/test_link_scraper.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock


SAMPLE_PAGE_TEXT = """
Piso en venta en Calle Mayor 10, Marbella, Málaga
Precio: 450.000 €
Superficie: 95 m²
Habitaciones: 3 | Baños: 2
Planta: 3ª | Terraza: Sí | Garaje: No
"""

EXTRACTED_JSON = {
    "price_eur": 450000,
    "size_m2": 95,
    "rooms": 3,
    "bathrooms": 2,
    "address": "Calle Mayor 10, Marbella, Málaga",
    "lat": None,
    "lng": None,
    "has_terrace": True,
    "has_parking": False,
    "floor": "3rd floor",
    "description": "Piso en venta en Calle Mayor 10",
}

NOMINATIM_RESPONSE = [{"lat": "36.5100", "lon": "-4.8800"}]


def _mock_playwright_page(text: str):
    page = MagicMock()
    page.evaluate.side_effect = lambda expr: text if "innerText" in expr else None
    page.locator.return_value.first.is_visible.return_value = False
    return page


def _mock_claude_output(data: dict) -> MagicMock:
    result = MagicMock()
    result.returncode = 0
    result.stdout = json.dumps(data)
    return result


@patch("src.scrapers.link_scraper.urllib.request.urlopen")
@patch("src.scrapers.link_scraper.subprocess.run")
@patch("src.scrapers.link_scraper.sync_playwright")
def test_scrape_extracts_fields(mock_pw, mock_claude, mock_urlopen):
    """LinkScraper returns all expected fields from page + geocoding."""
    page = _mock_playwright_page(SAMPLE_PAGE_TEXT)
    mock_pw.return_value.__enter__.return_value.chromium.launch.return_value \
        .new_page.return_value = page

    mock_claude.return_value = _mock_claude_output(EXTRACTED_JSON)

    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(NOMINATIM_RESPONSE).encode()
    mock_urlopen.return_value = cm

    from src.scrapers.link_scraper import LinkScraper
    result = LinkScraper().scrape("https://example.com/listing/123")

    assert result["price_eur"] == 450000
    assert result["size_m2"] == 95
    assert result["rooms"] == 3
    assert result["lat"] == 36.51
    assert result["lng"] == -4.88
    assert result["has_terrace"] is True
    assert result["id"] == "example.com/listing/123"


@patch("src.scrapers.link_scraper.subprocess.run")
@patch("src.scrapers.link_scraper.sync_playwright")
def test_scrape_raises_on_blocked_page(mock_pw, mock_claude):
    """Raises ScraperError when page text is too short (anti-bot blocked)."""
    page = _mock_playwright_page("Access denied")
    mock_pw.return_value.__enter__.return_value.chromium.launch.return_value \
        .new_page.return_value = page

    from src.scrapers.link_scraper import LinkScraper, ScraperError
    with pytest.raises(ScraperError, match="blocked"):
        LinkScraper().scrape("https://example.com/listing/456")


@patch("src.scrapers.link_scraper.subprocess.run")
@patch("src.scrapers.link_scraper.sync_playwright")
def test_scrape_raises_on_claude_failure(mock_pw, mock_claude):
    """Raises ScraperError when claude -p returns non-zero exit code."""
    page = _mock_playwright_page(SAMPLE_PAGE_TEXT)
    mock_pw.return_value.__enter__.return_value.chromium.launch.return_value \
        .new_page.return_value = page

    mock_claude.return_value.returncode = 1
    mock_claude.return_value.stderr = "auth error"

    from src.scrapers.link_scraper import LinkScraper, ScraperError
    with pytest.raises(ScraperError, match="extraction_failed"):
        LinkScraper().scrape("https://example.com/listing/789")
```

### Step 2: Run to verify tests fail

```bash
cd backend && uv run pytest tests/test_link_scraper.py -v
```

Expected: `ImportError` — `link_scraper` module not found.

### Step 3: Implement LinkScraper

Create `backend/src/scrapers/link_scraper.py`:

```python
import json
import logging
import re
import subprocess
import urllib.parse
import urllib.request
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

COOKIE_SELECTORS = [
    "#didomi-notice-agree-button",
    ".fc-cta-consent",
    "button[id*='accept']",
    "button:has-text('Aceptar')",
    "button:has-text('Accept')",
]

EXTRACTION_PROMPT = """Extract property listing data from the text below and return ONLY valid JSON.
Use null for any field you cannot find.

Required fields:
- price_eur: integer (sale price in euros)
- size_m2: integer (area in square metres)
- rooms: integer (number of bedrooms)
- bathrooms: integer
- address: string (full address or location description)
- lat: float (GPS latitude) or null
- lng: float (GPS longitude) or null
- has_terrace: boolean
- has_parking: boolean
- floor: string (e.g. "3rd floor", "ground floor", "penthouse") or null
- description: string (first 300 chars of property description)

Return only the JSON object, no markdown, no explanation.

TEXT:
{text}
"""


class ScraperError(Exception):
    pass


class LinkScraper:
    def scrape(self, url: str) -> dict:
        page_text, geo = self._fetch_page(url)
        if len(page_text) < 200:
            raise ScraperError(f"blocked: page text too short ({len(page_text)} chars)")
        data = self._extract(page_text)
        if geo:
            data["lat"] = geo["lat"]
            data["lng"] = geo["lng"]
        elif not data.get("lat") and data.get("address"):
            data["lat"], data["lng"] = self._geocode(data["address"])
        data["id"] = self._listing_id(url)
        data["url"] = url
        return data

    def _fetch_page(self, url: str) -> tuple[str, dict | None]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36"
            )
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            self._dismiss_cookies(page)
            page_text = page.evaluate("document.body.innerText")
            geo = self._extract_geo_from_page(page)
            browser.close()
        return page_text, geo

    def _dismiss_cookies(self, page) -> None:
        for selector in COOKIE_SELECTORS:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                continue

    def _extract_geo_from_page(self, page) -> dict | None:
        try:
            return page.evaluate("""() => {
                for (const el of document.querySelectorAll('script[type="application/ld+json"]')) {
                    try {
                        const d = JSON.parse(el.textContent);
                        const objs = Array.isArray(d) ? d : [d];
                        for (const o of objs) {
                            if (o.geo) return {lat: o.geo.latitude, lng: o.geo.longitude};
                            if (o.location && o.location.geo)
                                return {lat: o.location.geo.latitude, lng: o.location.geo.longitude};
                        }
                    } catch {}
                }
                for (const el of document.querySelectorAll('script:not([src])')) {
                    const m = el.textContent.match(
                        /"latitude"\\s*:\\s*([\\d.\\-]+)[\\s\\S]{0,50}"longitude"\\s*:\\s*([\\d.\\-]+)/
                    );
                    if (m) return {lat: parseFloat(m[1]), lng: parseFloat(m[2])};
                }
                return null;
            }""")
        except Exception:
            return None

    def _extract(self, page_text: str) -> dict:
        prompt = EXTRACTION_PROMPT.format(text=page_text[:8000])
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise ScraperError(f"extraction_failed: {result.stderr[:200]}")
        raw = result.stdout.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ScraperError("extraction_failed: could not parse JSON from claude output")

    def _geocode(self, address: str) -> tuple[float | None, float | None]:
        try:
            encoded = urllib.parse.quote(address)
            req = urllib.request.Request(
                f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1",
                headers={"User-Agent": "re-investment-advisor/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            if data:
                return round(float(data[0]["lat"]), 6), round(float(data[0]["lon"]), 6)
        except Exception as exc:
            logger.warning("Nominatim geocoding failed: %s", exc)
        return None, None

    def _listing_id(self, url: str) -> str:
        return re.sub(r'^https?://', '', url).rstrip('/')
```

### Step 4: Run tests to verify they pass

```bash
cd backend && uv run pytest tests/test_link_scraper.py -v
```

Expected: 3 tests PASS.

### Step 5: Commit

```bash
git add backend/src/scrapers/link_scraper.py backend/tests/test_link_scraper.py
git commit -m "feat: add LinkScraper — Playwright + claude -p + Nominatim geocoding"
```

---

## Task 2: Update models — remove UserCriteria, add ExtractedListing

**Files:**
- Modify: `backend/src/models.py`
- Modify: `backend/tests/test_roi.py`

### Step 1: Write failing test for new request model

Add to `backend/tests/test_roi.py` (or create `backend/tests/test_models.py`):

```python
def test_property_url_request_validates_url():
    from src.models import PropertyUrlRequest
    req = PropertyUrlRequest(url="https://www.fotocasa.es/es/comprar/123")
    assert req.url == "https://www.fotocasa.es/es/comprar/123"

def test_property_url_request_rejects_empty():
    import pytest
    from pydantic import ValidationError
    from src.models import PropertyUrlRequest
    with pytest.raises(ValidationError):
        PropertyUrlRequest(url="")
```

### Step 2: Run to verify fail

```bash
cd backend && uv run pytest tests/test_models.py -v 2>/dev/null || uv run pytest tests/test_roi.py::test_property_url_request_validates_url -v
```

Expected: ImportError — `PropertyUrlRequest` not found.

### Step 3: Replace models.py

Replace the entire content of `backend/src/models.py` with:

```python
from pydantic import BaseModel, Field, HttpUrl


class PropertyUrlRequest(BaseModel):
    url: str = Field(..., min_length=10, examples=["https://www.fotocasa.es/es/comprar/123"])


class ExtractedListing(BaseModel):
    id: str
    url: str
    price_eur: int
    size_m2: int
    rooms: int
    bathrooms: int
    address: str
    lat: float | None = None
    lng: float | None = None
    has_terrace: bool = False
    has_parking: bool = False
    floor: str | None = None
    description: str | None = None
```

### Step 4: Run tests

```bash
cd backend && uv run pytest tests/test_models.py -v 2>/dev/null || uv run pytest tests/ -k "model" -v
```

Expected: PASS.

### Step 5: Delete obsolete test files

```bash
cd backend && rm tests/test_filter.py tests/test_idealista.py
```

### Step 6: Commit

```bash
git add backend/src/models.py backend/tests/
git commit -m "refactor: replace UserCriteria+AnalysisRequest with PropertyUrlRequest+ExtractedListing, remove filter+idealista tests"
```

---

## Task 3: Update LTRAnalyzer — accept location string instead of UserCriteria

**Files:**
- Modify: `backend/src/analyzers/ltr_revenue.py`
- Modify: `backend/tests/test_ltr_revenue.py`

### Step 1: Read current test to understand what to update

```bash
cat backend/tests/test_ltr_revenue.py
```

### Step 2: Update the test — change signature from `UserCriteria` to `location: str`

In `backend/tests/test_ltr_revenue.py`, replace any `UserCriteria` usage with a plain location string. For example, where the test calls `analyzer.analyze(criteria)`, change to `analyzer.analyze("Marbella", 95)`.

The updated test should look like:

```python
from unittest.mock import patch, MagicMock
import pytest

RENTAL_LISTINGS = [
    {"price": 1800, "size": 90},
    {"price": 2000, "size": 100},
    {"price": 1600, "size": 80},
]


@patch("src.analyzers.ltr_revenue.IdealistaScraper")
def test_ltr_analyze_computes_avg_rent(mock_scraper_cls):
    mock_scraper_cls.return_value.scrape_rentals.return_value = RENTAL_LISTINGS
    from src.analyzers.ltr_revenue import LTRAnalyzer
    result = LTRAnalyzer().analyze("Marbella", 95)
    assert result["avg_monthly_rent_eur"] == pytest.approx(1800.0)
    assert result["comparables_count"] == 3
    assert result["error"] is None


@patch("src.analyzers.ltr_revenue.IdealistaScraper")
def test_ltr_analyze_empty_returns_error(mock_scraper_cls):
    mock_scraper_cls.return_value.scrape_rentals.return_value = []
    from src.analyzers.ltr_revenue import LTRAnalyzer
    result = LTRAnalyzer().analyze("Marbella", 95)
    assert result["avg_monthly_rent_eur"] is None
    assert result["error"] is not None
```

### Step 3: Run to verify fail

```bash
cd backend && uv run pytest tests/test_ltr_revenue.py -v
```

Expected: FAIL — `analyze()` takes wrong number of args.

### Step 4: Update LTRAnalyzer

Replace `backend/src/analyzers/ltr_revenue.py` with:

```python
import logging
from src.scrapers.idealista import IdealistaScraper

logger = logging.getLogger(__name__)


class LTRAnalyzer:
    def __init__(self) -> None:
        self._scraper = IdealistaScraper()

    def analyze(self, location: str, size_m2: int) -> dict:
        try:
            rentals = self._scraper.scrape_rentals_by_location(location, max_items=50)
            if not rentals:
                return self._error_result(location, "No rental listings found")
            return self._compute(location, rentals)
        except Exception as exc:
            logger.error("LTR | location=%s error=%s", location, exc)
            return self._error_result(location, str(exc))

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

Also add `scrape_rentals_by_location` to `IdealistaScraper` in `backend/src/scrapers/idealista.py`. Add this method (it's the same as `scrape_rentals` but takes `location: str` directly):

```python
def scrape_rentals_by_location(self, location: str, max_items: int = 50) -> list[dict]:
    payload = {
        "location": location,
        "operation": "rent",
        "propertyType": "flat,house",
        "country": "es",
        "maxItems": max_items,
    }
    run_id = self._start_run(payload)
    self._await_run(run_id)
    return self._fetch_items(run_id)
```

### Step 5: Run tests

```bash
cd backend && uv run pytest tests/test_ltr_revenue.py -v
```

Expected: PASS.

### Step 6: Commit

```bash
git add backend/src/analyzers/ltr_revenue.py backend/src/scrapers/idealista.py backend/tests/test_ltr_revenue.py
git commit -m "refactor: LTRAnalyzer.analyze() accepts location string instead of UserCriteria"
```

---

## Task 4: Update ROIAnalyzer — remove verdict, remove criteria param

**Files:**
- Modify: `backend/src/analyzers/roi.py`
- Modify: `backend/tests/test_roi.py`

### Step 1: Read current ROI tests

```bash
cat backend/tests/test_roi.py
```

### Step 2: Update test — remove verdict assertions, update call signature

Replace `backend/tests/test_roi.py` with:

```python
import pytest
from src.analyzers.roi import ROIAnalyzer

LISTING = {
    "id": "test-1",
    "price_eur": 300000,
    "size_m2": 90,
    "rooms": 2,
    "bathrooms": 1,
    "community_fee_month": 150,
}

STR_EST = {
    "property_id": "test-1",
    "annual_revenue_eur": 24000,
    "occupancy_rate_pct": 70,
}

LTR_DATA = {
    "avg_monthly_rent_eur": 1400,
    "error": None,
}


def test_roi_computes_str_yield():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, capital_growth_pct=3.0)
    assert result["str_net_yield_pct"] is not None
    assert result["str_net_yield_pct"] > 0


def test_roi_computes_ltr_yield():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, capital_growth_pct=3.0)
    assert result["ltr_net_yield_pct"] is not None
    assert result["ltr_net_yield_pct"] > 0


def test_roi_preferred_type_str_wins():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, capital_growth_pct=3.0)
    assert result["preferred_rental_type"] == "STR"


def test_roi_no_verdict_field():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, capital_growth_pct=3.0)
    assert "verdict" not in result


def test_roi_investment_score_range():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, capital_growth_pct=3.0)
    assert 0 <= result["investment_score"] <= 10


def test_roi_handles_null_str():
    result = ROIAnalyzer().compute_property(
        LISTING, {"property_id": "test-1", "annual_revenue_eur": None, "occupancy_rate_pct": None},
        LTR_DATA, capital_growth_pct=None
    )
    assert result["str_net_yield_pct"] is None
    assert result["ltr_net_yield_pct"] is not None
```

### Step 3: Run to verify fail

```bash
cd backend && uv run pytest tests/test_roi.py -v
```

Expected: FAIL on signature mismatch.

### Step 4: Update ROIAnalyzer

Replace `backend/src/analyzers/roi.py` with:

```python
from src.config import Config

_YIELD_REFERENCE_PCT = 10.0
_GROWTH_REFERENCE_PCT = 8.0


class ROIAnalyzer:
    def __init__(self) -> None:
        self._cfg = Config()

    def compute_property(self, listing: dict, str_est: dict,
                         ltr_data: dict | None,
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
```

### Step 5: Run tests

```bash
cd backend && uv run pytest tests/test_roi.py -v
```

Expected: all PASS.

### Step 6: Commit

```bash
git add backend/src/analyzers/roi.py backend/tests/test_roi.py
git commit -m "refactor: ROIAnalyzer removes verdict and criteria param — outputs raw numbers only"
```

---

## Task 5: Update pipeline.py — wire up LinkScraper, remove filter

**Files:**
- Modify: `backend/src/reporters/pipeline.py`

No new tests for pipeline (integration-level, tested end-to-end). Just update the implementation.

### Step 1: Replace pipeline.py

Replace the entire content of `backend/src/reporters/pipeline.py`:

```python
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from src.scrapers.link_scraper import LinkScraper
from src.analyzers.str_revenue import AirROIAnalyzer
from src.analyzers.ltr_revenue import LTRAnalyzer
from src.analyzers.capital_growth import CapitalGrowthAnalyzer
from src.analyzers.roi import ROIAnalyzer

_runs: dict[str, dict] = {}


def start_run(url: str) -> str:
    run_id = str(uuid.uuid4())[:8]
    _runs[run_id] = {
        "status": "running",
        "url": url,
        "started_at": datetime.now().isoformat(),
    }
    return run_id


def run_pipeline(run_id: str, url: str) -> None:
    """Blocking — must run in thread pool, not event loop."""
    try:
        out = Path("outputs/data")
        out.mkdir(parents=True, exist_ok=True)

        listing = LinkScraper().scrape(url)
        _save(out / f"{run_id}_listing.json", listing)

        location = _extract_city(listing.get("address", ""))

        with ThreadPoolExecutor(max_workers=3) as pool:
            str_future = pool.submit(AirROIAnalyzer().analyze_batch, [listing])
            ltr_future = pool.submit(LTRAnalyzer().analyze, location, listing.get("size_m2", 80))
            growth_future = pool.submit(CapitalGrowthAnalyzer().analyze, location)
            str_data = str_future.result()
            ltr_data = ltr_future.result()
            growth_data = growth_future.result()

        str_est = str_data[0] if str_data else {}
        capital_growth_pct = growth_data.get("yoy_appreciation_pct")
        roi = ROIAnalyzer().compute_property(listing, str_est, ltr_data, capital_growth_pct)

        property_result = {**listing, **roi}

        _runs[run_id].update({
            "status": "completed",
            "generated_at": datetime.now().isoformat(),
            "property": property_result,
            "market": {
                "yoy_appreciation_pct": capital_growth_pct,
                "ccaa": growth_data.get("ccaa"),
                "data_year": growth_data.get("data_year"),
                "ltr_avg_rent_eur": ltr_data.get("avg_monthly_rent_eur"),
                "ltr_comparables": ltr_data.get("comparables_count"),
            },
        })
    except Exception as exc:
        _runs[run_id].update({"status": "failed", "error": str(exc)})


def get_run(run_id: str) -> dict | None:
    return _runs.get(run_id)


def _extract_city(address: str) -> str:
    """Best-effort: take last non-empty comma-separated part as city."""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) >= 2:
        return parts[-2]
    return parts[-1] if parts else address


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
```

### Step 2: Verify no import errors

```bash
cd backend && uv run python -c "from src.reporters.pipeline import run_pipeline; print('OK')"
```

Expected: `OK`.

### Step 3: Delete obsolete files

```bash
cd backend && rm src/filters/property_filter.py src/filters/__init__.py
rmdir src/filters
```

### Step 4: Commit

```bash
git add backend/src/reporters/pipeline.py backend/src/
git commit -m "refactor: pipeline uses LinkScraper + single property flow, removes PropertyFilter"
```

---

## Task 6: Update main.py — new endpoint signature

**Files:**
- Modify: `backend/src/main.py`

### Step 1: Replace main.py

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.models import PropertyUrlRequest
from src.reporters.pipeline import start_run, run_pipeline, get_run

app = FastAPI(title="Real Estate Investment Advisor")
_executor = ThreadPoolExecutor(max_workers=3)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/analysis", status_code=202)
async def create_analysis(req: PropertyUrlRequest) -> dict:
    run_id = start_run(req.url)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, run_pipeline, run_id, req.url)
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

### Step 2: Verify import

```bash
cd backend && uv run python -c "from src.main import app; print('OK')"
```

Expected: `OK`.

### Step 3: Commit

```bash
git add backend/src/main.py
git commit -m "refactor: main.py accepts PropertyUrlRequest, wires new pipeline"
```

---

## Task 7: Update frontend — types + URL form + single result

**Files:**
- Modify: `frontend/src/types/analysis.ts`
- Modify: `frontend/src/components/InvestmentForm.tsx`
- Modify: `frontend/src/hooks/useAnalysis.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/ExecutiveSummary.tsx`

### Step 1: Replace types/analysis.ts

```typescript
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
```

### Step 2: Replace InvestmentForm.tsx — single URL input

Replace the entire file:

```tsx
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import type { PropertyUrlRequest } from '../types/analysis'

interface Props { onSubmit: (req: PropertyUrlRequest) => void; loading: boolean }

export function InvestmentForm({ onSubmit, loading }: Props) {
  const [url, setUrl] = useState('')

  return (
    <Card>
      <CardHeader><CardTitle>Property URL</CardTitle></CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div>
          <Label>Paste a listing URL (Fotocasa, Idealista, Pisos.com…)</Label>
          <Input
            placeholder="https://www.fotocasa.es/es/comprar/…"
            value={url}
            onChange={e => setUrl(e.target.value)}
          />
        </div>
        <div className="flex justify-end">
          <Button onClick={() => onSubmit({ url })} disabled={loading || url.trim().length < 10}>
            {loading ? 'Analyzing…' : 'Analyze Property'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
```

### Step 3: Update useAnalysis.ts — new request/result types

Replace the entire file:

```typescript
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
```

### Step 4: Replace ExecutiveSummary.tsx — single property card

Replace the entire file:

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AnalysisResult } from '../types/analysis'

function fmt(n: number | null | undefined, decimals = 1, suffix = '') {
  if (n == null) return 'N/A'
  return n.toFixed(decimals) + suffix
}

export function ExecutiveSummary({ result }: { result: AnalysisResult }) {
  const p = result.property
  if (!p) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>{p.address}</CardTitle>
        <p className="text-sm text-muted-foreground">
          {p.size_m2} m² · {p.rooms} bed · {p.bathrooms} bath
          {p.floor ? ` · ${p.floor}` : ''}
          {p.has_terrace ? ' · Terrace' : ''}
          {p.has_parking ? ' · Parking' : ''}
        </p>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Metric label="Price" value={`€${p.price_eur.toLocaleString()}`} />
        <Metric label="STR Net Yield" value={fmt(p.str_net_yield_pct, 1, '%')} highlight />
        <Metric label="LTR Net Yield" value={fmt(p.ltr_net_yield_pct, 1, '%')} highlight />
        <Metric label="Preferred" value={p.preferred_rental_type ?? 'N/A'} />
        <Metric label="STR Revenue/yr" value={p.str_annual_revenue_eur ? `€${p.str_annual_revenue_eur.toLocaleString()}` : 'N/A'} />
        <Metric label="LTR Rent/mo" value={p.ltr_monthly_rent_eur ? `€${p.ltr_monthly_rent_eur.toLocaleString()}` : 'N/A'} />
        <Metric label="Capital Growth" value={fmt(p.capital_growth_pct, 1, '%/yr')} />
        <Metric label="Investment Score" value={p.investment_score != null ? `${p.investment_score}/10` : 'N/A'} highlight />
      </CardContent>
    </Card>
  )
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={`text-lg font-semibold ${highlight ? 'text-primary' : ''}`}>{value}</span>
    </div>
  )
}
```

### Step 5: Update App.tsx — remove PropertyTable/YieldChart for list, show single result

Replace `App.tsx`:

```tsx
import { useAnalysis } from './hooks/useAnalysis'
import { InvestmentForm } from './components/InvestmentForm'
import { ExecutiveSummary } from './components/ExecutiveSummary'
import { MarketOverview } from './components/MarketOverview'
import { YieldChart } from './components/YieldChart'

export default function App() {
  const { status, result, error, analyze } = useAnalysis()
  const isLoading = status === 'loading' || status === 'polling'

  return (
    <div className="min-h-screen bg-background text-foreground p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Real Estate Investment Advisor</h1>
      <p className="text-muted-foreground mb-8">Paste a listing URL to get a full STR + LTR + capital growth analysis</p>
      <InvestmentForm onSubmit={analyze} loading={isLoading} />
      {status === 'polling' && (
        <p className="text-sm text-muted-foreground mt-4 animate-pulse">
          Scraping listing, fetching STR revenue, LTR rentals, and capital growth data…
        </p>
      )}
      {error && <p className="text-destructive mt-4">{error}</p>}
      {result?.status === 'completed' && result.property && (
        <div className="flex flex-col gap-6 mt-8">
          <ExecutiveSummary result={result} />
          <MarketOverview market={result.market} location={result.property.address} />
          <YieldChart properties={[result.property]} />
        </div>
      )}
    </div>
  )
}
```

### Step 6: Run TypeScript check

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Fix any type errors before committing. Common fix: `YieldChart` and `MarketOverview` may need prop type updates — check their interfaces and adjust if they reference `Property` (old type) vs `PropertyResult` (new).

### Step 7: Commit

```bash
git add frontend/src/
git commit -m "feat: replace 8-field form with URL input, single property result card"
```

---

## Task 8: Full integration smoke test

### Step 1: Run all backend tests

```bash
cd backend && uv run pytest tests/ -v
```

Expected: all pass (test_config, test_capital_growth, test_ltr_revenue, test_roi, test_str_revenue, test_link_scraper). `test_filter` and `test_idealista` were deleted in Task 2.

### Step 2: Start backend

```bash
cd backend && uv run uvicorn src.main:app --reload
```

### Step 3: Start frontend (separate terminal)

```bash
cd frontend && npm run dev
```

### Step 4: Open browser at http://localhost:5173

Paste: `https://www.fotocasa.es/es/comprar/vivienda/obra-nueva/marbella/20561853/189207445`

Click **Analyze Property**. Wait ~30s.

Expected: ExecutiveSummary card shows price 660 000 €, STR yield %, LTR yield %, investment score.

### Step 5: Commit memory update

Update `docs/plans/2026-05-03-link-based-pipeline-design.md` status to `Implemented`.

```bash
git add docs/plans/2026-05-03-link-based-pipeline-design.md
git commit -m "docs: mark link-based pipeline design as implemented"
```
