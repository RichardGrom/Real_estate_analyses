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
