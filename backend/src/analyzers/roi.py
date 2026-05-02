from src.config import Config
from src.models import UserCriteria

_YIELD_REFERENCE_PCT = 10.0
_GROWTH_REFERENCE_PCT = 8.0
_YIELD_DEFAULT_THRESHOLD = 5.0
_GROWTH_DEFAULT_THRESHOLD = 2.0


class ROIAnalyzer:
    def __init__(self) -> None:
        self._cfg = Config()

    def compute_all(self, listings: list[dict], str_data: list[dict],
                    ltr_data: dict | None, criteria: UserCriteria,
                    capital_growth_pct: float | None = None) -> list[dict]:
        str_by_id = {s["property_id"]: s for s in str_data}
        return [
            self.compute_property(l, str_by_id.get(l["id"], {}), ltr_data,
                                  criteria, capital_growth_pct)
            for l in listings
        ]

    def compute_property(self, listing: dict, str_est: dict,
                         ltr_data: dict | None, criteria: UserCriteria,
                         capital_growth_pct: float | None = None) -> dict:
        price = listing["price_eur"]
        acq = round(price * (1 + self._cfg.TRANSACTION_COST_PCT), 2)
        str_revenue = str_est.get("annual_revenue_eur")
        ltr_monthly = ltr_data.get("avg_monthly_rent_eur") if ltr_data else None
        community = listing.get("community_fee_month", 150) * 12
        ibi = price * 0.60 * 0.005

        str_net_yield = self._str_yield(str_revenue, acq, community, ibi)
        ltr_net_yield = self._ltr_yield(ltr_monthly, acq, community, ibi)
        preferred = self._preferred(str_net_yield, ltr_net_yield)
        best_yield = str_net_yield if preferred == "STR" else (ltr_net_yield or str_net_yield)

        occupancy = str_est.get("occupancy_rate_pct") or 0
        score = self._score(best_yield or 0, occupancy, capital_growth_pct)
        verdict = self._verdict(best_yield or 0, capital_growth_pct, criteria)

        return {
            "property_id": listing["id"],
            "purchase_price": price,
            "acquisition_cost": acq,
            "str_annual_revenue_eur": str_revenue,
            "str_gross_yield_pct": round((str_revenue / price) * 100, 2) if str_revenue else None,
            "str_net_yield_pct": round(str_net_yield, 2) if str_net_yield is not None else None,
            "ltr_monthly_rent_eur": ltr_monthly,
            "ltr_net_yield_pct": round(ltr_net_yield, 2) if ltr_net_yield is not None else None,
            "preferred_rental_type": preferred,
            "community_fees_yr": community,
            "ibi_yr": round(ibi, 2),
            "capital_growth_pct": capital_growth_pct,
            "investment_score": score,
            "verdict": verdict,
        }

    def _str_yield(self, revenue: float | None, acq: float,
                   community: float, ibi: float) -> float | None:
        if revenue is None:
            return None
        opex = revenue * self._cfg.STR_OPEX_PCT
        net = revenue - opex - community - ibi
        return (net / acq) * 100

    def _ltr_yield(self, monthly_rent: float | None, acq: float,
                   community: float, ibi: float) -> float | None:
        if monthly_rent is None:
            return None
        annual = monthly_rent * 12
        opex = annual * self._cfg.LTR_OPEX_PCT
        net = annual - opex - community - ibi
        return (net / acq) * 100

    def _preferred(self, str_yield: float | None, ltr_yield: float | None) -> str:
        if str_yield is None:
            return "LTR"
        if ltr_yield is None:
            return "STR"
        return "STR" if str_yield >= ltr_yield else "LTR"

    def _score(self, net_yield: float, occupancy: float,
               capital_growth_pct: float | None) -> float:
        yield_score = min(net_yield / _YIELD_REFERENCE_PCT, 1.0)
        occ_score = min(occupancy / 100.0, 1.0)
        growth_score = min((capital_growth_pct or 0) / _GROWTH_REFERENCE_PCT, 1.0)
        return round((yield_score * 0.5 + occ_score * 0.3 + growth_score * 0.2) * 10, 1)

    def _verdict(self, net_yield: float, capital_growth_pct: float | None,
                 criteria: UserCriteria) -> str:
        yield_threshold = criteria.min_net_yield_pct or _YIELD_DEFAULT_THRESHOLD
        growth_threshold = criteria.min_capital_growth_pct or _GROWTH_DEFAULT_THRESHOLD
        yield_ok = net_yield >= yield_threshold
        growth_ok = (capital_growth_pct or 0) >= growth_threshold
        if yield_ok and growth_ok:
            return "BUY"
        if yield_ok or growth_ok:
            return "WATCH"
        return "SKIP"
