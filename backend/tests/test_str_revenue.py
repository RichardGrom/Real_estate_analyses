import pytest
from unittest.mock import patch
from src.analyzers.str_revenue import AirROIAnalyzer

MOCK_RESPONSE = {
    "revenue": 28429.15,
    "average_daily_rate": 156.22,
    "occupancy": 0.513,
    "monthly_revenue_distributions": [0.055, 0.057, 0.063, 0.065, 0.074, 0.100,
                                        0.140, 0.153, 0.103, 0.077, 0.053, 0.053],
}

def test_returns_revenue_from_api_field():
    analyzer = AirROIAnalyzer.__new__(AirROIAnalyzer)
    with patch.object(analyzer, "_call_api", return_value=MOCK_RESPONSE):
        result = analyzer.analyze_property(
            {"id": "p1", "lat": 36.5, "lng": -4.8, "rooms": 2, "bathrooms": 1, "size_m2": 80}
        )
    assert result["annual_revenue_eur"] == pytest.approx(28429.15, abs=0.01)
    assert result["occupancy_rate_pct"] == 51.3
    assert result["adr_eur"] == pytest.approx(156.22, abs=0.01)
    assert result["property_id"] == "p1"
    assert result["monthly_distributions"] is not None
    assert len(result["monthly_distributions"]) == 12
    assert result["error"] is None

def test_build_params_includes_baths():
    analyzer = AirROIAnalyzer.__new__(AirROIAnalyzer)
    params = analyzer._build_params({"lat": 36.5, "lng": -4.8, "rooms": 3, "bathrooms": 2, "size_m2": 90})
    assert params["bedrooms"] == 3
    assert params["baths"] == 2
    assert params["guests"] == 6

def test_build_params_baths_fallback():
    analyzer = AirROIAnalyzer.__new__(AirROIAnalyzer)
    params = analyzer._build_params({"lat": 36.5, "lng": -4.8, "rooms": 3, "size_m2": 90})
    assert params["baths"] == max(1, 3 - 1)

def test_handles_api_error_gracefully():
    analyzer = AirROIAnalyzer.__new__(AirROIAnalyzer)
    with patch.object(analyzer, "_call_api", side_effect=Exception("timeout")):
        result = analyzer.analyze_property(
            {"id": "p1", "lat": 36.5, "lng": -4.8, "rooms": 2, "bathrooms": 1, "size_m2": 80}
        )
    assert result["annual_revenue_eur"] is None
    assert result["error"] == "timeout"
