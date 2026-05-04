import json
import pytest
from unittest.mock import patch, MagicMock


SAMPLE_PAGE_TEXT = """
Piso en venta en Calle Mayor 10, Marbella, Málaga
Precio: 450.000 €
Superficie: 95 m² | Planta: 3ª
Habitaciones: 3 | Baños: 2
Terraza: Sí | Garaje: No

Descripción: Magnífico piso en el corazón de Marbella con vistas al mar. Amplio salón comedor, cocina equipada, 3 dormitorios con armarios empotrados y 2 baños completos. Terraza de 15 m². Comunidad: 150 €/mes. Referencia: MRB-2024-789.
"""

EXTRACTED_JSON = {
    "price_eur": 450000,
    "size_m2": 95,
    "rooms": 3,
    "bathrooms": 2,
    "address": "Calle Mayor 10, Marbella, Málaga",
    "lat": None,
    "lng": None,
    "has_terrace": True,
    "has_parking": False,
    "floor": "3rd floor",
    "description": "Piso en venta en Calle Mayor 10",
}

NOMINATIM_RESPONSE = [{"lat": "36.5100", "lon": "-4.8800"}]


def _mock_playwright_page(text: str):
    page = MagicMock()
    page.evaluate.side_effect = lambda expr: text if "innerText" in expr else None
    page.locator.return_value.first.is_visible.return_value = False
    return page


def _mock_claude_output(data: dict) -> MagicMock:
    result = MagicMock()
    result.returncode = 0
    result.stdout = json.dumps(data)
    return result


@patch("src.scrapers.link_scraper.urllib.request.urlopen")
@patch("src.scrapers.link_scraper.subprocess.run")
@patch("src.scrapers.link_scraper.sync_playwright")
def test_scrape_extracts_fields(mock_pw, mock_claude, mock_urlopen):
    """LinkScraper returns all expected fields from page + geocoding."""
    page = _mock_playwright_page(SAMPLE_PAGE_TEXT)
    mock_pw.return_value.__enter__.return_value.chromium.launch.return_value \
        .new_page.return_value = page

    mock_claude.return_value = _mock_claude_output(EXTRACTED_JSON)

    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(NOMINATIM_RESPONSE).encode()
    mock_urlopen.return_value = cm

    from src.scrapers.link_scraper import LinkScraper
    result = LinkScraper().scrape("https://example.com/listing/123")

    assert result["price_eur"] == 450000
    assert result["size_m2"] == 95
    assert result["rooms"] == 3
    assert result["lat"] == 36.51
    assert result["lng"] == -4.88
    assert result["has_terrace"] is True
    assert result["id"] == "example.com/listing/123"


@patch("src.scrapers.link_scraper.subprocess.run")
@patch("src.scrapers.link_scraper.sync_playwright")
def test_scrape_raises_on_blocked_page(mock_pw, mock_claude):
    """Raises ScraperError when page text is too short (anti-bot blocked)."""
    page = _mock_playwright_page("Access denied")
    mock_pw.return_value.__enter__.return_value.chromium.launch.return_value \
        .new_page.return_value = page

    from src.scrapers.link_scraper import LinkScraper, ScraperError
    with pytest.raises(ScraperError, match="blocked"):
        LinkScraper().scrape("https://example.com/listing/456")


@patch("src.scrapers.link_scraper.subprocess.run")
@patch("src.scrapers.link_scraper.sync_playwright")
def test_scrape_raises_on_claude_failure(mock_pw, mock_claude):
    """Raises ScraperError when claude -p returns non-zero exit code."""
    page = _mock_playwright_page(SAMPLE_PAGE_TEXT)
    mock_pw.return_value.__enter__.return_value.chromium.launch.return_value \
        .new_page.return_value = page

    mock_claude.return_value.returncode = 1
    mock_claude.return_value.stderr = "auth error"

    from src.scrapers.link_scraper import LinkScraper, ScraperError
    with pytest.raises(ScraperError, match="extraction_failed"):
        LinkScraper().scrape("https://example.com/listing/789")
