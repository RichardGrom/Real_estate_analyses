import pytest
from src.analyzers.roi import ROIAnalyzer
from src.models import UserCriteria

CRITERIA_BARE = UserCriteria(location="Marbella", budget_eur=320000)
CRITERIA_WITH = UserCriteria(location="Marbella", budget_eur=320000,
                              min_net_yield_pct=5.0, min_capital_growth_pct=3.0)

LISTING = {"id": "p1", "price_eur": 285000, "community_fee_month": 150}
STR_EST = {"property_id": "p1", "annual_revenue_eur": 28500, "occupancy_rate_pct": 72, "error": None}
LTR_DATA = {"avg_monthly_rent_eur": 1800, "error": None}

def test_gross_yield_calculation():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, CRITERIA_BARE)
    assert abs(result["str_gross_yield_pct"] - 10.0) < 0.1
    assert result["acquisition_cost"] == pytest.approx(285000 * 1.10)

def test_ltr_net_yield_computed():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, CRITERIA_BARE)
    assert result["ltr_net_yield_pct"] is not None
    assert result["ltr_net_yield_pct"] > 0

def test_preferred_rental_type_str_when_str_higher():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, CRITERIA_BARE)
    assert result["preferred_rental_type"] in {"STR", "LTR"}

def test_score_is_capped_at_10():
    listing = {"id": "p1", "price_eur": 200000, "community_fee_month": 100}
    str_est = {"property_id": "p1", "annual_revenue_eur": 40000, "occupancy_rate_pct": 95, "error": None}
    result = ROIAnalyzer().compute_property(listing, str_est, LTR_DATA, CRITERIA_BARE)
    assert result["investment_score"] <= 10.0

def test_score_independent_of_user_threshold():
    result_a = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, CRITERIA_BARE)
    result_b = ROIAnalyzer().compute_property(LISTING, STR_EST, LTR_DATA, CRITERIA_WITH)
    assert result_a["investment_score"] == result_b["investment_score"]

def test_verdict_buy_when_exceeds_thresholds():
    listing = {"id": "p1", "price_eur": 250000, "community_fee_month": 120}
    str_est = {"property_id": "p1", "annual_revenue_eur": 30000, "occupancy_rate_pct": 80, "error": None}
    result = ROIAnalyzer().compute_property(listing, str_est, LTR_DATA, CRITERIA_WITH,
                                             capital_growth_pct=4.0)
    assert result["verdict"] == "BUY"

def test_verdict_skip_when_below_yield():
    listing = {"id": "p1", "price_eur": 310000, "community_fee_month": 200}
    str_est = {"property_id": "p1", "annual_revenue_eur": 10000, "occupancy_rate_pct": 40, "error": None}
    result = ROIAnalyzer().compute_property(listing, str_est, LTR_DATA, CRITERIA_WITH)
    assert result["verdict"] == "SKIP"

def test_none_str_yield_falls_back_to_ltr():
    str_est = {"property_id": "p1", "annual_revenue_eur": None, "error": "API failed"}
    result = ROIAnalyzer().compute_property(LISTING, str_est, LTR_DATA, CRITERIA_BARE)
    assert result["str_net_yield_pct"] is None
    assert result["ltr_net_yield_pct"] is not None

def test_none_ltr_data_handled():
    result = ROIAnalyzer().compute_property(LISTING, STR_EST, None, CRITERIA_BARE)
    assert result["ltr_net_yield_pct"] is None
    assert result["preferred_rental_type"] == "STR"
