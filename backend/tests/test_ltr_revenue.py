import pytest
from unittest.mock import patch, MagicMock

MOCK_ESTIMATE = {
    "avg_monthly_rent_eur": 1800,
    "rent_per_m2_month": 20.0,
    "confidence": "high",
    "notes": "Marbella prime location estimate",
}


@patch("src.analyzers.ltr_revenue.ClaudeLTREstimator")
def test_ltr_analyze_computes_avg_rent(mock_estimator_cls):
    mock_estimator_cls.return_value.estimate.return_value = MOCK_ESTIMATE
    from src.analyzers.ltr_revenue import LTRAnalyzer
    result = LTRAnalyzer().analyze("Marbella", 95)
    assert result["avg_monthly_rent_eur"] == 1800
    assert result["error"] is None
    assert result["data_source"] == "Claude AI market estimate"


@patch("src.analyzers.ltr_revenue.ClaudeLTREstimator")
def test_ltr_analyze_returns_rent_per_m2(mock_estimator_cls):
    mock_estimator_cls.return_value.estimate.return_value = MOCK_ESTIMATE
    from src.analyzers.ltr_revenue import LTRAnalyzer
    result = LTRAnalyzer().analyze("Marbella", 95)
    assert result["rent_per_m2_month"] == pytest.approx(20.0)
    assert result["confidence"] == "high"


@patch("src.analyzers.ltr_revenue.ClaudeLTREstimator")
def test_ltr_analyze_handles_exception(mock_estimator_cls):
    mock_estimator_cls.return_value.estimate.side_effect = RuntimeError("claude -p failed")
    from src.analyzers.ltr_revenue import LTRAnalyzer
    result = LTRAnalyzer().analyze("Marbella", 95)
    assert result["avg_monthly_rent_eur"] is None
    assert "claude -p failed" in result["error"]


@patch("src.analyzers.ltr_revenue.ClaudeLTREstimator")
def test_ltr_analyze_passes_size_to_estimator(mock_estimator_cls):
    mock_estimator_cls.return_value.estimate.return_value = MOCK_ESTIMATE
    from src.analyzers.ltr_revenue import LTRAnalyzer
    LTRAnalyzer().analyze("Estepona", 74)
    mock_estimator_cls.return_value.estimate.assert_called_once_with("Estepona", 74)
