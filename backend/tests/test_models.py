import pytest


def test_property_url_request_validates_url():
    from src.models import PropertyUrlRequest
    req = PropertyUrlRequest(url="https://www.fotocasa.es/es/comprar/123")
    assert req.url == "https://www.fotocasa.es/es/comprar/123"


def test_property_url_request_rejects_empty():
    from pydantic import ValidationError
    from src.models import PropertyUrlRequest
    with pytest.raises(ValidationError):
        PropertyUrlRequest(url="")


def test_extracted_listing_optional_fields_default():
    from src.models import ExtractedListing
    listing = ExtractedListing(
        id="test-1",
        url="https://example.com",
        price_eur=300000,
        size_m2=90,
        rooms=3,
        bathrooms=2,
        address="Calle Mayor, Marbella",
    )
    assert listing.lat is None
    assert listing.lng is None
    assert listing.has_terrace is False
    assert listing.has_parking is False
