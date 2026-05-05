import pytest


def test_config_loads(monkeypatch):
    monkeypatch.setenv("AIRROI_API_KEY", "test_airroi")
    monkeypatch.setenv("EXA_API_KEY", "test_exa")
    from src.config import Config
    cfg = Config()
    assert cfg.airroi_api_key == "test_airroi"
    assert cfg.exa_api_key == "test_exa"


def test_config_raises_on_missing_exa(monkeypatch):
    monkeypatch.setenv("AIRROI_API_KEY", "x")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    from src.config import Config
    with pytest.raises(ValueError, match="EXA_API_KEY"):
        Config()
