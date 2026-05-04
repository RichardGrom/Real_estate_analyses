import pytest


def test_config_loads(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "test_apify")
    monkeypatch.setenv("AIRROI_API_KEY", "test_airroi")
    monkeypatch.setenv("EXA_API_KEY", "test_exa")
    from src.config import Config
    cfg = Config()
    assert cfg.apify_token == "test_apify"
    assert cfg.airroi_api_key == "test_airroi"
    assert cfg.exa_api_key == "test_exa"


def test_config_raises_on_missing_apify(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    monkeypatch.setenv("AIRROI_API_KEY", "x")
    monkeypatch.setenv("EXA_API_KEY", "x")
    from importlib import reload
    import src.config as m
    reload(m)
    with pytest.raises(ValueError, match="APIFY_TOKEN"):
        m.Config()


def test_config_raises_on_missing_exa(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "x")
    monkeypatch.setenv("AIRROI_API_KEY", "x")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    from importlib import reload
    import src.config as m
    reload(m)
    with pytest.raises(ValueError, match="EXA_API_KEY"):
        m.Config()
