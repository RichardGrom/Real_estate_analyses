import pytest
from unittest.mock import patch
from src.analyzers.capital_growth import CapitalGrowthAnalyzer

MOCK_INE_RESPONSE = [
    {"Nombre": "Tasa de Variación - Andalucía", "Data": [
        {"Anyo": 2023, "Valor": 11.2},
        {"Anyo": 2024, "Valor": 13.1},
    ]},
    {"Nombre": "Índice General - Andalucía", "Data": [
        {"Anyo": 2024, "Valor": 198.5},
    ]},
    {"Nombre": "Tasa de Variación - Cataluña", "Data": [
        {"Anyo": 2024, "Valor": 9.8},
    ]},
]

def test_extracts_yoy_for_andalucia():
    analyzer = CapitalGrowthAnalyzer.__new__(CapitalGrowthAnalyzer)
    with patch.object(analyzer, "_fetch_ine", return_value=MOCK_INE_RESPONSE):
        result = analyzer.analyze("Marbella")
    assert result["yoy_appreciation_pct"] == pytest.approx(13.1, abs=0.1)
    assert result["ccaa"] == "Andalucía"
    assert result["location"] == "Marbella"
    assert result["error"] is None

def test_extracts_yoy_for_cataluna():
    analyzer = CapitalGrowthAnalyzer.__new__(CapitalGrowthAnalyzer)
    with patch.object(analyzer, "_fetch_ine", return_value=MOCK_INE_RESPONSE):
        result = analyzer.analyze("Barcelona")
    assert result["yoy_appreciation_pct"] == pytest.approx(9.8, abs=0.1)
    assert result["ccaa"] == "Cataluña"

def test_unknown_location_returns_none():
    analyzer = CapitalGrowthAnalyzer.__new__(CapitalGrowthAnalyzer)
    with patch.object(analyzer, "_fetch_ine", return_value=MOCK_INE_RESPONSE):
        result = analyzer.analyze("UnknownCity")
    assert result["yoy_appreciation_pct"] is None
    assert result["error"] == "Location not mapped to CCAA"

def test_handles_ine_error():
    analyzer = CapitalGrowthAnalyzer.__new__(CapitalGrowthAnalyzer)
    with patch.object(analyzer, "_fetch_ine", side_effect=Exception("timeout")):
        result = analyzer.analyze("Marbella")
    assert result["yoy_appreciation_pct"] is None
    assert "timeout" in result["error"]
