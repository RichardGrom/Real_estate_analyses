import pytest
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
