import pytest
from unittest.mock import patch, MagicMock

RENTAL_LISTINGS = [
    {"price": 1800, "size": 90},
    {"price": 2000, "size": 100},
    {"price": 1600, "size": 80},
]


@patch("src.analyzers.ltr_revenue.IdealistaScraper")
def test_ltr_analyze_computes_avg_rent(mock_scraper_cls):
    mock_scraper_cls.return_value.scrape_rentals_by_location.return_value = RENTAL_LISTINGS
    from src.analyzers.ltr_revenue import LTRAnalyzer
    result = LTRAnalyzer().analyze("Marbella", 95)
    assert result["avg_monthly_rent_eur"] == pytest.approx(1800.0)
    assert result["comparables_count"] == 3
    assert result["error"] is None


@patch("src.analyzers.ltr_revenue.IdealistaScraper")
def test_ltr_analyze_empty_returns_error(mock_scraper_cls):
    mock_scraper_cls.return_value.scrape_rentals_by_location.return_value = []
    from src.analyzers.ltr_revenue import LTRAnalyzer
    result = LTRAnalyzer().analyze("Marbella", 95)
    assert result["avg_monthly_rent_eur"] is None
    assert result["error"] is not None


@patch("src.analyzers.ltr_revenue.IdealistaScraper")
def test_ltr_analyze_computes_rent_per_m2(mock_scraper_cls):
    mock_scraper_cls.return_value.scrape_rentals_by_location.return_value = RENTAL_LISTINGS
    from src.analyzers.ltr_revenue import LTRAnalyzer
    result = LTRAnalyzer().analyze("Marbella", 95)
    expected = (1800 / 90 + 2000 / 100 + 1600 / 80) / 3
    assert result["rent_per_m2_month"] == pytest.approx(expected, abs=0.1)


@patch("src.analyzers.ltr_revenue.IdealistaScraper")
def test_ltr_analyze_handles_exception(mock_scraper_cls):
    mock_scraper_cls.return_value.scrape_rentals_by_location.side_effect = Exception("timeout")
    from src.analyzers.ltr_revenue import LTRAnalyzer
    result = LTRAnalyzer().analyze("Marbella", 95)
    assert result["avg_monthly_rent_eur"] is None
    assert "timeout" in result["error"]
