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


def run_approach_a(url: str) -> ApproachResult:
    """Exa.ai getContents → Claude CLI extraction (subscription auth)."""
    import subprocess
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

        prompt = EXTRACTION_PROMPT.format(text=page_text[:8000])
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            return ApproachResult("A: Exa+Claude", elapsed_s=round(time.time() - t0, 1),
                                   error=f"claude CLI error: {result.stderr[:80]}")
        raw = result.stdout.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        data = json.loads(raw)

        return ApproachResult("A: Exa+Claude", data=data,
                               elapsed_s=round(time.time() - t0, 1), cost_usd=0.0)
    except Exception as exc:
        return ApproachResult("A: Exa+Claude", elapsed_s=round(time.time() - t0, 1), error=str(exc)[:80])


def run_approach_b(url: str) -> ApproachResult:
    """Apify Idealista actor with startUrls parameter."""
    import requests
    from src.config import Config

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
        cost = 0.000006
        return ApproachResult("B: Apify URL", data=data,
                               elapsed_s=round(time.time() - t0, 1), cost_usd=cost)
    except Exception as exc:
        return ApproachResult("B: Apify URL", elapsed_s=round(time.time() - t0, 1), error=str(exc)[:80])


def run_approach_c(url: str) -> ApproachResult:
    """Playwright headless Chrome → Claude CLI extraction (subscription auth)."""
    import subprocess
    from playwright.sync_api import sync_playwright

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

        print(f"  [debug] Playwright page_text length: {len(page_text) if page_text else 0} chars")

        if not page_text or len(page_text) < 100:
            return ApproachResult("C: Playwright", elapsed_s=round(time.time() - t0, 1),
                                   error="Page text too short — likely blocked")

        prompt = EXTRACTION_PROMPT.format(text=page_text[:8000])
        result = subprocess.run(
            ["/Users/richardgrom/.local/bin/claude", "-p", prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            return ApproachResult("C: Playwright", elapsed_s=round(time.time() - t0, 1),
                                   error=f"claude CLI error: {result.stderr[:80]}")
        raw = result.stdout.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        data = json.loads(raw)

        return ApproachResult("C: Playwright", data=data,
                               elapsed_s=round(time.time() - t0, 1), cost_usd=0.0)
    except Exception as exc:
        return ApproachResult("C: Playwright", elapsed_s=round(time.time() - t0, 1), error=str(exc)[:80])


if __name__ == "__main__":
    print(f"Testing URL: {TEST_URL}\n")
    results = []
    print("Running Approach A (Exa + Claude)...")
    results.append(run_approach_a(TEST_URL))
    print("Running Approach B (Apify startUrls)...")
    results.append(run_approach_b(TEST_URL))
    print("Running Approach C (Playwright + Claude)...")
    results.append(run_approach_c(TEST_URL))
    print_results(results)
