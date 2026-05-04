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
