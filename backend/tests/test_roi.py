import pytest
from src.analyzers.roi import ROIAnalyzer

LISTING = {
    "id": "test-1",
    "price_eur": 300000,
    "size_m2": 90,
    "rooms": 2,
    "bathrooms": 1,
    "community_fee_month": 150,
}

STR_EST = {
    "property_id": "test-1",
    "annual_revenue_eur": 24000,
    "occupancy_rate_pct": 70,
}

LTR_DATA = {
    "avg_monthly_rent_eur": 1400,
    "error": None,
}


def test_roi_computes_str_yield():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, capital_growth_pct=3.0)
    assert result["str_net_yield_pct"] is not None
    assert result["str_net_yield_pct"] > 0


def test_roi_computes_ltr_yield():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, capital_growth_pct=3.0)
    assert result["ltr_net_yield_pct"] is not None
    assert result["ltr_net_yield_pct"] > 0


def test_roi_preferred_type_str_wins():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, capital_growth_pct=3.0)
    assert result["preferred_rental_type"] == "STR"


def test_roi_no_verdict_field():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, capital_growth_pct=3.0)
    assert "verdict" not in result


def test_roi_investment_score_range():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, capital_growth_pct=3.0)
    assert 0 <= result["investment_score"] <= 10


def test_roi_handles_null_str():
    result = ROIAnalyzer().compute_property(
        LISTING,
        {"property_id": "test-1", "annual_revenue_eur": None, "occupancy_rate_pct": None},
        LTR_DATA,
        capital_growth_pct=None,
    )
    assert result["str_net_yield_pct"] is None
    assert result["ltr_net_yield_pct"] is not None


def test_roi_handles_null_ltr():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, None, capital_growth_pct=3.0)
    assert result["ltr_net_yield_pct"] is None
    assert result["preferred_rental_type"] == "STR"


def test_roi_gross_yield_calculation():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, capital_growth_pct=None)
    assert result["str_gross_yield_pct"] == pytest.approx(8.0, abs=0.1)
