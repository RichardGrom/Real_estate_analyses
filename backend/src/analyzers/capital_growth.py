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
