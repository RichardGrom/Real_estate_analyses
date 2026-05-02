import pytest
from unittest.mock import MagicMock
from src.scrapers.idealista import IdealistaScraper, ScraperError
from src.models import UserCriteria

CRITERIA = UserCriteria(location="Marbella", budget_eur=320000, min_size_m2=70)

def test_normalize_listing_maps_fields():
    scraper = IdealistaScraper.__new__(IdealistaScraper)
    raw = {
        "propertyCode": "abc123", "url": "https://idealista.com/x",
        "address": "Calle Test 1", "price": 280000, "size": 82,
        "floor": "2", "rooms": 2, "bathrooms": 2,
        "latitude": 36.51, "longitude": -4.88,
        "features": {"hasTerrace": True},
        "parkingSpace": {"hasParkingSpace": True},
    }
    result = scraper._normalize_listing(raw)
    assert result["id"] == "abc123"
    assert result["price_eur"] == 280000
    assert result["size_m2"] == 82
    assert result["has_terrace"] is True
    assert result["has_parking"] is True
    assert result["bathrooms"] == 2
    assert result["community_fee_month"] == max(80, int(82 * 1.5))

def test_handle_response_raises_on_error():
    scraper = IdealistaScraper.__new__(IdealistaScraper)
    mock_r = MagicMock(ok=False, status_code=403, text="Forbidden")
    with pytest.raises(ScraperError) as exc:
        scraper._handle_response(mock_r, "actor_id", "url")
    assert exc.value.status_code == 403
