import json
import pytest
from unittest.mock import patch, MagicMock
from src.scrapers.claude_ltr_estimator import ClaudeLTREstimator

MOCK_RESPONSE = {
    "avg_monthly_rent_eur": 900,
    "rent_per_m2_month": 11.25,
    "confidence": "high",
    "notes": "Valencia city centre, 80m2 apartment"
}


@patch("src.scrapers.claude_ltr_estimator.subprocess.run")
def test_estimate_returns_parsed_json(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(MOCK_RESPONSE))
    result = ClaudeLTREstimator().estimate("Valencia", 80)
    assert result["avg_monthly_rent_eur"] == 900
    assert result["rent_per_m2_month"] == 11.25
    assert result["confidence"] == "high"


@patch("src.scrapers.claude_ltr_estimator.subprocess.run")
def test_estimate_handles_markdown_wrapped_json(mock_run):
    wrapped = f"```json\n{json.dumps(MOCK_RESPONSE)}\n```"
    mock_run.return_value = MagicMock(returncode=0, stdout=wrapped)
    result = ClaudeLTREstimator().estimate("Malaga", 70)
    assert result["avg_monthly_rent_eur"] == 900


@patch("src.scrapers.claude_ltr_estimator.subprocess.run")
def test_estimate_raises_on_claude_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="timeout error", stdout="")
    with pytest.raises(RuntimeError, match="claude -p failed"):
        ClaudeLTREstimator().estimate("Madrid", 60)


@patch("src.scrapers.claude_ltr_estimator.subprocess.run")
def test_estimate_raises_on_unparseable_output(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="Sorry, I cannot help with that.")
    with pytest.raises(RuntimeError, match="Could not parse JSON"):
        ClaudeLTREstimator().estimate("Barcelona", 75)
