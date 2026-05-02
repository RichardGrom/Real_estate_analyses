import pytest


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "test_apify")
    monkeypatch.setenv("AIRROI_API_KEY", "test_airroi")
    monkeypatch.setenv("EXA_API_KEY", "test_exa")
