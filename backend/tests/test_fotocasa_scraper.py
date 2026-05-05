import json
import pytest
from unittest.mock import patch, MagicMock
from src.scrapers.fotocasa_scraper import FotocasaScraper

MOCK_LISTINGS = [
    {"price": 850, "size_m2": 75},
    {"price": 950, "size_m2": 90},
    {"price": 750, "size_m2": 65},
]

MOCK_PAGE_TEXT = "Alquiler pisos Valencia 850€ 75m2 | 950€ 90m2 | 750€ 65m2 " * 20  # >200 chars


def _make_playwright_mock(page_text: str):
    mock_page = MagicMock()
    mock_page.evaluate.return_value = page_text
    mock_page.locator.return_value.first.is_visible.return_value = False

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_playwright_instance = MagicMock()
    mock_playwright_instance.chromium.launch.return_value = mock_browser

    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_playwright_instance
    mock_ctx.__exit__.return_value = False

    return mock_ctx


@patch("src.scrapers.fotocasa_scraper.sync_playwright")
@patch("src.scrapers.fotocasa_scraper.subprocess.run")
def test_scrape_rentals_returns_listings(mock_run, mock_playwright):
    mock_playwright.return_value = _make_playwright_mock(MOCK_PAGE_TEXT)
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(MOCK_LISTINGS))

    result = FotocasaScraper().scrape_rentals("Valencia")

    assert len(result) == 3
    assert result[0]["price"] == 850
    assert result[1]["size_m2"] == 90


@patch("src.scrapers.fotocasa_scraper.sync_playwright")
@patch("src.scrapers.fotocasa_scraper.subprocess.run")
def test_scrape_raises_when_blocked(mock_run, mock_playwright):
    short_text = "Access denied"  # < 200 chars
    mock_playwright.return_value = _make_playwright_mock(short_text)

    with pytest.raises(RuntimeError, match="blocked"):
        FotocasaScraper().scrape_rentals("Valencia")


@patch("src.scrapers.fotocasa_scraper.sync_playwright")
@patch("src.scrapers.fotocasa_scraper.subprocess.run")
def test_scrape_returns_empty_when_no_listings_parsed(mock_run, mock_playwright):
    mock_playwright.return_value = _make_playwright_mock(MOCK_PAGE_TEXT)
    mock_run.return_value = MagicMock(returncode=0, stdout="[]")

    result = FotocasaScraper().scrape_rentals("Cuenca")
    assert result == []


def test_build_url_normalizes_location():
    scraper = FotocasaScraper()
    assert scraper._build_url("Valencia") == \
        "https://www.fotocasa.es/es/alquiler/casas/valencia-capital/todas-las-zonas/l"
    assert scraper._build_url("Las Palmas") == \
        "https://www.fotocasa.es/es/alquiler/casas/las-palmas-capital/todas-las-zonas/l"
