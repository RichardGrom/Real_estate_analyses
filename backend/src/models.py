from pydantic import BaseModel, Field


class PropertyUrlRequest(BaseModel):
    url: str = Field(..., min_length=10, examples=["https://www.fotocasa.es/es/comprar/123"])


class ExtractedListing(BaseModel):
    id: str
    url: str
    price_eur: int
    size_m2: int
    rooms: int
    bathrooms: int
    address: str
    lat: float | None = None
    lng: float | None = None
    has_terrace: bool = False
    has_parking: bool = False
    floor: str | None = None
    description: str | None = None
