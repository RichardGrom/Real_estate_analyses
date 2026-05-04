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
