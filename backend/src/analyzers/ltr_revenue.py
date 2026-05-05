import logging

from src.scrapers.claude_ltr_estimator import ClaudeLTREstimator

logger = logging.getLogger(__name__)


class LTRAnalyzer:
    def __init__(self) -> None:
        self._estimator = ClaudeLTREstimator()

    def analyze(self, location: str, size_m2: int) -> dict:
        try:
            result = self._estimator.estimate(location, size_m2)
            return {
                "location": location,
                "avg_monthly_rent_eur": result.get("avg_monthly_rent_eur"),
                "rent_per_m2_month": result.get("rent_per_m2_month"),
                "comparables_count": None,
                "data_source": "Claude AI market estimate",
                "confidence": result.get("confidence"),
                "notes": result.get("notes"),
                "error": None,
            }
        except Exception as exc:
            logger.error("LTR | location=%s error=%s", location, exc)
            return self._error_result(location, str(exc))

    def _error_result(self, location: str, error: str) -> dict:
        return {
            "location": location,
            "avg_monthly_rent_eur": None,
            "rent_per_m2_month": None,
            "comparables_count": None,
            "data_source": "Claude AI market estimate",
            "confidence": None,
            "notes": None,
            "error": error,
        }
