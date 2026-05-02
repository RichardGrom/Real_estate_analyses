from src.filters.property_filter import PropertyFilter
from src.models import UserCriteria

CRITERIA = UserCriteria(
    location="Marbella", budget_eur=300000,
    property_type="apartment", bedrooms=2, min_size_m2=70,
    parking=True, terrace=True,
)
BASE = {"id": "p1", "price_eur": 280000, "size_m2": 82, "rooms": 2,
        "floor_label": "2ª planta", "has_terrace": True, "has_parking": True}
ROI = {"property_id": "p1", "str_net_yield_pct": 6.2, "ltr_net_yield_pct": 4.1,
       "investment_score": 7.5, "verdict": "BUY"}

def test_passing_property_included():
    assert len(PropertyFilter().filter([BASE], [ROI], CRITERIA)) == 1

def test_over_budget_excluded():
    c = UserCriteria("Marbella", 200000, "apartment", 2, 70, parking=True, terrace=True)
    assert len(PropertyFilter().filter([BASE], [ROI], c)) == 0

def test_no_terrace_excluded():
    listing = {**BASE, "has_terrace": False}
    assert len(PropertyFilter().filter([listing], [ROI], CRITERIA)) == 0

def test_no_parking_excluded():
    listing = {**BASE, "has_parking": False}
    assert len(PropertyFilter().filter([listing], [ROI], CRITERIA)) == 0

def test_floor_preference_top_matches():
    listing = {**BASE, "floor_label": "ático"}
    c = UserCriteria("Marbella", 300000, "apartment", 2, 70,
                     parking=True, terrace=True, floor_preference="top")
    assert len(PropertyFilter().filter([listing], [ROI], c)) == 1

def test_floor_preference_top_excludes_mid():
    c = UserCriteria("Marbella", 300000, "apartment", 2, 70,
                     parking=True, terrace=True, floor_preference="top")
    assert len(PropertyFilter().filter([BASE], [ROI], c)) == 0
