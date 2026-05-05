#!/usr/bin/env python3
"""
LTR approach comparison: Option A (claude -p) vs Option C (Playwright + Fotocasa)
Usage: uv run python scripts/compare_ltr_approaches.py <idealista_url>
"""
import sys
import time
sys.path.insert(0, ".")

DEFAULT_URL = "https://www.idealista.com/inmueble/102565466/"


def extract_listing(url: str) -> dict:
    from src.scrapers.link_scraper import LinkScraper
    print(f"  Scraping listing: {url}")
    return LinkScraper().scrape(url)


def run_option_a(location: str, size_m2: int) -> dict:
    from src.scrapers.claude_ltr_estimator import ClaudeLTREstimator
    t0 = time.time()
    result = ClaudeLTREstimator().estimate(location, size_m2)
    return {**result, "elapsed_s": round(time.time() - t0, 1)}


def run_option_c(location: str) -> dict:
    from src.scrapers.fotocasa_scraper import FotocasaScraper
    t0 = time.time()
    rentals = FotocasaScraper().scrape_rentals(location)
    elapsed = round(time.time() - t0, 1)
    if not rentals:
        return {
            "avg_monthly_rent_eur": None,
            "rent_per_m2_month": None,
            "comparables_count": 0,
            "elapsed_s": elapsed,
            "error": "no listings parsed",
        }
    prices = [r["price"] for r in rentals if r.get("price")]
    per_m2 = [
        r["price"] / r["size_m2"]
        for r in rentals
        if r.get("price") and r.get("size_m2", 0) > 0
    ]
    return {
        "avg_monthly_rent_eur": round(sum(prices) / len(prices)) if prices else None,
        "rent_per_m2_month": round(sum(per_m2) / len(per_m2), 2) if per_m2 else None,
        "comparables_count": len(prices),
        "elapsed_s": elapsed,
        "error": None,
    }


def _extract_city(address: str) -> str:
    if not address:
        return "Valencia"
    parts = [p.strip() for p in address.split(",") if p.strip()]
    return parts[-1] if parts else address


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    print(f"\n{'='*60}")
    print("LTR Approach Comparison Spike")
    print(f"{'='*60}")

    print("\n[1/3] Extracting listing data...")
    try:
        listing = extract_listing(url)
        location = _extract_city(listing.get("address", ""))
        size_m2 = listing.get("size_m2") or 80
        print(f"  address:  {listing.get('address')}")
        print(f"  location: {location}")
        print(f"  size_m2:  {size_m2}")
    except Exception as e:
        print(f"  ERROR extracting listing: {e}")
        sys.exit(1)

    print(f"\n[2/3] Option A — claude -p estimate (location={location}, size={size_m2}m2)...")
    try:
        a = run_option_a(location, size_m2)
        print(f"  avg_monthly_rent_eur: €{a.get('avg_monthly_rent_eur')}")
        print(f"  rent_per_m2_month:    €{a.get('rent_per_m2_month')}")
        print(f"  confidence:           {a.get('confidence')}")
        print(f"  elapsed:              {a.get('elapsed_s')}s")
        print(f"  notes:                {a.get('notes')}")
    except Exception as e:
        print(f"  ERROR: {e}")
        a = {}

    print(f"\n[3/3] Option C — Playwright + Fotocasa (location={location})...")
    try:
        c = run_option_c(location)
        print(f"  avg_monthly_rent_eur: €{c.get('avg_monthly_rent_eur')}")
        print(f"  rent_per_m2_month:    €{c.get('rent_per_m2_month')}")
        print(f"  comparables_count:    {c.get('comparables_count')}")
        print(f"  elapsed:              {c.get('elapsed_s')}s")
        if c.get("error"):
            print(f"  error:                {c.get('error')}")
    except Exception as e:
        print(f"  ERROR: {e}")
        c = {}

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Metric':<25} {'Option A':>15} {'Option C':>15}")
    print(f"{'-'*55}")
    print(f"{'avg_monthly_rent_eur':<25} {str(a.get('avg_monthly_rent_eur', '?')):>14}€ {str(c.get('avg_monthly_rent_eur', '?')):>14}€")
    print(f"{'rent_per_m2_month':<25} {str(a.get('rent_per_m2_month', '?')):>14}€ {str(c.get('rent_per_m2_month', '?')):>14}€")
    print(f"{'comparables_count':<25} {'(AI est.)':>15} {str(c.get('comparables_count', '?')):>15}")
    print(f"{'elapsed_s':<25} {str(a.get('elapsed_s', '?')):>14}s {str(c.get('elapsed_s', '?')):>14}s")
    print(f"{'confidence':<25} {str(a.get('confidence', '?')):>15} {'N/A':>15}")
    print()
