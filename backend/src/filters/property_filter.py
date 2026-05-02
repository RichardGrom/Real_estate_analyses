from src.models import UserCriteria

_FLOOR_LABELS: dict[str, set[str]] = {
    "ground": {"bajo", "planta baja", "pb", "0", "ground"},
    "low": {"1", "2", "primera", "segunda"},
    "mid": {"3", "4", "5", "tercera", "cuarta", "quinta"},
    "high": {"6", "7", "8", "sexta", "séptima"},
    "top": {"atico", "ático", "top", "penthouse"},
}


class PropertyFilter:
    def filter(self, listings: list[dict], roi_data: list[dict],
               criteria: UserCriteria) -> list[dict]:
        roi_by_id = {r["property_id"]: r for r in roi_data}
        return [
            {**l, **roi_by_id.get(l["id"], {})}
            for l in listings
            if self._passes(l, roi_by_id.get(l["id"], {}), criteria)
        ]

    def _passes(self, listing: dict, roi: dict, criteria: UserCriteria) -> bool:
        checks = [
            listing.get("price_eur", 0) <= criteria.budget_eur,
            listing.get("size_m2", 0) >= criteria.min_size_m2,
            listing.get("rooms", 0) >= criteria.bedrooms,
        ]
        if criteria.terrace:
            checks.append(bool(listing.get("has_terrace")))
        if criteria.parking:
            checks.append(bool(listing.get("has_parking")))
        if criteria.floor_preference and criteria.floor_preference != "any":
            checks.append(self._matches_floor(listing, criteria.floor_preference))
        if criteria.min_net_yield_pct:
            best = max(
                roi.get("str_net_yield_pct") or 0,
                roi.get("ltr_net_yield_pct") or 0,
            )
            checks.append(best >= criteria.min_net_yield_pct)
        return all(checks)

    def _matches_floor(self, listing: dict, preference: str) -> bool:
        floor_label = str(listing.get("floor_label", "")).lower()
        return any(label in floor_label for label in _FLOOR_LABELS.get(preference, set()))
