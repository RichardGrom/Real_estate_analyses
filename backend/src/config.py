from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent.parent / ".env")


class Config:
    TRANSACTION_COST_PCT: float = 0.10
    STR_OPEX_PCT: float = 0.25
    LTR_OPEX_PCT: float = 0.15
    AIRROI_BASE_URL: str = "https://api.airroi.com/calculator/estimate"
    INE_IPV_TABLE_URL: str = "https://servicios.ine.es/wstempus/js/es/DATOS_TABLA/49300?tip=AM"

    def __init__(self) -> None:
        self.airroi_api_key: str = self._require("AIRROI_API_KEY")
        self.exa_api_key: str = self._require("EXA_API_KEY")

    def _require(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value
