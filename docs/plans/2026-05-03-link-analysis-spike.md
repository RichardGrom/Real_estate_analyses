# Link-Based Property Extraction — Spike Test Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Run a comparison script that tests 3 property data extraction approaches on a real Idealista URL and outputs a side-by-side quality/speed/cost table so we can pick the best one.

**Architecture:** Single standalone script `backend/scripts/compare_approaches.py` — no changes to existing pipeline. Each approach is an isolated function returning a `dict` with extracted fields + metadata. After running, we pick the winner and redesign the pipeline in a follow-up plan.

**Tech Stack:** Python 3.11, uv, exa-py, anthropic SDK, playwright (sync API), requests (Apify already wired)

**Note:** This is a spike — NO TDD. The script is exploratory and temporary.

---

## Target URL

```
https://www.idealista.com/inmueble/111009537/
```

## Expected Fields

```python
FIELDS = ["price_eur", "size_m2", "rooms", "bathrooms",
          "address", "lat", "lng", "has_terrace", "has_parking",
          "floor", "description"]
```

---

## Task 0: Add dependencies + install Playwright

**Files:**
- Modify: `backend/pyproject.toml`

**Step 1:** Update `backend/pyproject.toml` — add `spike` optional group:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]
spike = [
    "exa-py>=1.1.0",
    "anthropic>=0.40.0",
    "playwright>=1.44.0",
]
```

**Step 2:** Install spike dependencies:

```bash
cd /Users/richardgrom/Documents/Richard\ /Real_estate_analyses/.worktrees/feature-multi-agent-v2/backend
uv sync --extra spike
```

Expected: packages installed without errors.

**Step 3:** Install Playwright browser:

```bash
uv run playwright install chromium
```

Expected: `Chromium ... downloaded` message.

**Step 4:** Add `ANTHROPIC_API_KEY` to `.env` (root of repo, not backend):

```
ANTHROPIC_API_KEY=sk-ant-...
```

Check that the key is already there:
```bash
grep ANTHROPIC_API_KEY /Users/richardgrom/Documents/Richard\ /Real_estate_analyses/.env
```

If missing, add it manually to `.env`.

**Step 5:** Commit:

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore: add spike dependencies — exa-py, anthropic, playwright"
```

---

## Task 1: Shared extraction prompt + Config update

**Files:**
- Modify: `backend/src/config.py`
- Create: `backend/scripts/__init__.py` (empty)
- Create: `backend/scripts/compare_approaches.py` (skeleton)

**Step 1:** Add `anthropic_api_key` to `backend/src/config.py`:

```python
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent.parent / ".env")


class Config:
    TRANSACTION_COST_PCT: float = 0.10
    STR_OPEX_PCT: float = 0.25
    LTR_OPEX_PCT: float = 0.15
    AIRROI_BASE_URL: str = "https://api.airroi.com/calculator/estimate"
    APIFY_IDEALISTA_ACTOR_ID: str = "igolaizola~idealista-scraper"
    APIFY_BASE_URL: str = "https://api.apify.com/v2"
    INE_IPV_TABLE_URL: str = "https://servicios.ine.es/wstempus/js/es/DATOS_TABLA/49300?tip=AM"

    def __init__(self) -> None:
        self.apify_token: str = self._require("APIFY_TOKEN")
        self.airroi_api_key: str = self._require("AIRROI_API_KEY")
        self.exa_api_key: str = self._require("EXA_API_KEY")
        self.anthropic_api_key: str = self._require("ANTHROPIC_API_KEY")

    def _require(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value
```

**Step 2:** Create empty `backend/scripts/__init__.py`.

**Step 3:** Create `backend/scripts/compare_approaches.py` skeleton:

```python
"""
Spike: compare 3 property extraction approaches on a single Idealista URL.
Run: uv run python scripts/compare_approaches.py
"""
import json
import sys
import time
from dataclasses import dataclass, field

TEST_URL = "https://www.idealista.com/inmueble/111009537/"
FIELDS = ["price_eur", "size_m2", "rooms", "bathrooms",
          "address", "lat", "lng", "has_terrace", "has_parking",
          "floor", "description"]

EXTRACTION_PROMPT = """
Extract property listing data from the text below and return ONLY valid JSON.
Use null for any field you cannot find.

Required fields:
- price_eur: integer (sale price in euros)
- size_m2: integer (area in square metres)
- rooms: integer (number of bedrooms)
- bathrooms: integer
- address: string (full address or location description)
- lat: float (GPS latitude, e.g. 36.51)
- lng: float (GPS longitude, e.g. -4.88)
- has_terrace: boolean
- has_parking: boolean
- floor: string (e.g. "2nd floor", "ground floor", "penthouse")
- description: string (first 300 chars of property description)

Return only the JSON object, no markdown, no explanation.

TEXT:
{text}
"""


@dataclass
class ApproachResult:
    name: str
    data: dict = field(default_factory=dict)
    elapsed_s: float = 0.0
    cost_usd: float = 0.0
    error: str | None = None

    def completeness(self) -> int:
        return sum(1 for f in FIELDS if self.data.get(f) is not None)


def print_results(results: list[ApproachResult]) -> None:
    print("\n" + "=" * 70)
    print(f"{'FIELD':<20}", end="")
    for r in results:
        print(f"{r.name:<22}", end="")
    print()
    print("-" * 70)
    for f in FIELDS:
        print(f"{f:<20}", end="")
        for r in results:
            val = r.data.get(f)
            cell = str(val)[:18] if val is not None else "✗ null"
            print(f"{cell:<22}", end="")
        print()
    print("-" * 70)
    print(f"{'Completeness':<20}", end="")
    for r in results:
        print(f"{r.completeness()}/{len(FIELDS):<19}", end="")
    print()
    print(f"{'Time (s)':<20}", end="")
    for r in results:
        print(f"{r.elapsed_s:.1f}s{'':<19}", end="")
    print()
    print(f"{'Est. cost':<20}", end="")
    for r in results:
        print(f"${r.cost_usd:.4f}{'':<16}", end="")
    print()
    print(f"{'Error':<20}", end="")
    for r in results:
        err = (r.error or "none")[:20]
        print(f"{err:<22}", end="")
    print()
    print("=" * 70)


if __name__ == "__main__":
    print(f"Testing URL: {TEST_URL}\n")
    results = []
    # approaches added in Tasks 2, 3, 4
    print_results(results)
```

**Step 4:** Verify the skeleton runs:

```bash
cd backend && uv run python scripts/compare_approaches.py
```

Expected: prints empty table with headers.

**Step 5:** Commit:

```bash
git add backend/src/config.py backend/scripts/
git commit -m "spike: add comparison script skeleton + ANTHROPIC_API_KEY to Config"
```

---

## Task 2: Approach A — Exa.ai + Claude

**Files:**
- Modify: `backend/scripts/compare_approaches.py`

**Step 1:** Add `run_approach_a()` function after the `print_results` function:

```python
def run_approach_a(url: str) -> ApproachResult:
    """Exa.ai getContents → Claude JSON extraction."""
    import anthropic
    from exa_py import Exa
    from src.config import Config

    cfg = Config()
    t0 = time.time()
    try:
        exa = Exa(api_key=cfg.exa_api_key)
        contents = exa.get_contents([url], text=True)
        page_text = contents.results[0].text if contents.results else ""
        if not page_text:
            return ApproachResult("A: Exa+Claude", error="Exa returned empty text")

        client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(text=page_text[:8000])}],
        )
        raw = msg.content[0].text.strip()
        data = json.loads(raw)

        # rough cost: input ~2k tokens + output ~200 tokens at Haiku pricing
        input_tokens = msg.usage.input_tokens
        output_tokens = msg.usage.output_tokens
        cost = (input_tokens / 1_000_000) * 0.25 + (output_tokens / 1_000_000) * 1.25

        return ApproachResult("A: Exa+Claude", data=data,
                               elapsed_s=round(time.time() - t0, 1), cost_usd=round(cost, 5))
    except Exception as exc:
        return ApproachResult("A: Exa+Claude", elapsed_s=round(time.time() - t0, 1), error=str(exc)[:80])
```

**Step 2:** Call it in `__main__`:

```python
if __name__ == "__main__":
    print(f"Testing URL: {TEST_URL}\n")
    results = []
    print("Running Approach A (Exa + Claude)...")
    results.append(run_approach_a(TEST_URL))
    print_results(results)
```

**Step 3:** Run:

```bash
cd backend && uv run python scripts/compare_approaches.py
```

Expected: table with Approach A results. Check `lat`/`lng` especially — they are required for AirROI.

**Step 4:** Commit:

```bash
git add backend/scripts/compare_approaches.py
git commit -m "spike: add Approach A — Exa getContents + Claude extraction"
```

---

## Task 3: Approach B — Apify startUrls

**Files:**
- Modify: `backend/scripts/compare_approaches.py`

**Step 1:** Add `run_approach_b()` after `run_approach_a`:

```python
def run_approach_b(url: str) -> ApproachResult:
    """Apify Idealista actor with startUrls parameter."""
    import requests
    from src.config import Config
    from src.scrapers.idealista import IdealistaScraper, ScraperError

    cfg = Config()
    t0 = time.time()
    try:
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {cfg.apify_token}"
        actor = cfg.APIFY_IDEALISTA_ACTOR_ID
        payload = {
            "startUrls": [{"url": url}],
            "operation": "sale",
            "country": "es",
            "maxItems": 1,
        }
        run_url = f"{cfg.APIFY_BASE_URL}/acts/{actor}/runs"
        r = session.post(run_url, json=payload)
        if not r.ok:
            return ApproachResult("B: Apify URL", elapsed_s=round(time.time() - t0, 1),
                                   error=f"HTTP {r.status_code}: {r.text[:100]}")
        run_id = r.json()["data"]["id"]

        # Poll for completion
        status_url = f"{cfg.APIFY_BASE_URL}/actor-runs/{run_id}"
        terminal = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}
        while True:
            status_r = session.get(status_url)
            status = status_r.json()["data"]["status"]
            if status in terminal:
                break
            time.sleep(5)

        if status != "SUCCEEDED":
            return ApproachResult("B: Apify URL", elapsed_s=round(time.time() - t0, 1),
                                   error=f"Run ended: {status}")

        items_url = f"{cfg.APIFY_BASE_URL}/actor-runs/{run_id}/dataset/items"
        items_r = session.get(items_url)
        items = items_r.json()
        if not items:
            return ApproachResult("B: Apify URL", elapsed_s=round(time.time() - t0, 1),
                                   error="Empty dataset")

        raw = items[0]
        size = raw.get("size", 0)
        data = {
            "price_eur": raw.get("price"),
            "size_m2": size,
            "rooms": raw.get("rooms"),
            "bathrooms": raw.get("bathrooms"),
            "address": raw.get("address"),
            "lat": raw.get("latitude"),
            "lng": raw.get("longitude"),
            "has_terrace": raw.get("features", {}).get("hasTerrace"),
            "has_parking": raw.get("parkingSpace", {}).get("hasParkingSpace"),
            "floor": raw.get("floor"),
            "description": (raw.get("description") or "")[:300] or None,
        }
        # Apify charges ~$0.006 per 1000 results; 1 result ≈ $0.000006
        cost = 0.000006
        return ApproachResult("B: Apify URL", data=data,
                               elapsed_s=round(time.time() - t0, 1), cost_usd=cost)
    except Exception as exc:
        return ApproachResult("B: Apify URL", elapsed_s=round(time.time() - t0, 1), error=str(exc)[:80])
```

**Step 2:** Add to `__main__`:

```python
    print("Running Approach B (Apify startUrls)...")
    results.append(run_approach_b(TEST_URL))
    print_results(results)
```

**Step 3:** Run:

```bash
cd backend && uv run python scripts/compare_approaches.py
```

Expected: Approach B takes 60–120s. Check if `lat`/`lng` are populated.

**Step 4:** Commit:

```bash
git add backend/scripts/compare_approaches.py
git commit -m "spike: add Approach B — Apify startUrls"
```

---

## Task 4: Approach C — Playwright + Claude

**Files:**
- Modify: `backend/scripts/compare_approaches.py`

**Step 1:** Add `run_approach_c()` after `run_approach_b`:

```python
def run_approach_c(url: str) -> ApproachResult:
    """Playwright headless Chrome → Claude JSON extraction."""
    import anthropic
    from playwright.sync_api import sync_playwright
    from src.config import Config

    cfg = Config()
    t0 = time.time()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36"
            )
            page.goto(url, wait_until="networkidle", timeout=30000)
            page_text = page.evaluate("document.body.innerText")
            browser.close()

        if not page_text or len(page_text) < 100:
            return ApproachResult("C: Playwright", elapsed_s=round(time.time() - t0, 1),
                                   error="Page text too short — likely blocked")

        client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(text=page_text[:8000])}],
        )
        raw = msg.content[0].text.strip()
        data = json.loads(raw)

        input_tokens = msg.usage.input_tokens
        output_tokens = msg.usage.output_tokens
        cost = (input_tokens / 1_000_000) * 0.25 + (output_tokens / 1_000_000) * 1.25

        return ApproachResult("C: Playwright", data=data,
                               elapsed_s=round(time.time() - t0, 1), cost_usd=round(cost, 5))
    except Exception as exc:
        return ApproachResult("C: Playwright", elapsed_s=round(time.time() - t0, 1), error=str(exc)[:80])
```

**Step 2:** Add to `__main__`:

```python
    print("Running Approach C (Playwright + Claude)...")
    results.append(run_approach_c(TEST_URL))
    print_results(results)
```

**Step 3:** Run the full comparison:

```bash
cd backend && uv run python scripts/compare_approaches.py
```

Expected: all 3 approaches in the final table. Total run time ~2–3 minutes (Apify is the bottleneck).

**Step 4:** Commit:

```bash
git add backend/scripts/compare_approaches.py
git commit -m "spike: add Approach C — Playwright + Claude extraction"
```

---

## Task 5: Run full comparison + decide

**Step 1:** Run the final script and capture output:

```bash
cd backend && uv run python scripts/compare_approaches.py 2>&1 | tee ../outputs/tests/spike_results.txt
```

**Step 2:** Review the table. Decision criteria in order:

1. **`lat` and `lng` both non-null** — hard requirement. Any approach missing these is eliminated.
2. **Completeness** — higher is better (max 11/11).
3. **Speed** — faster is better for UX.
4. **Cost** — lower is better.
5. **Generality** — if we ever need non-Idealista URLs, eliminate Apify-only approaches.

**Step 3:** Note the winner and report back. The follow-up plan will replace `IdealistaScraper` with the winning approach.

**Step 4:** Commit results:

```bash
git add outputs/tests/spike_results.txt
git commit -m "spike: record comparison results"
```
