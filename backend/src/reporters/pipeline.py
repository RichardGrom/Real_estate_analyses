import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from src.models import UserCriteria
from src.scrapers.idealista import IdealistaScraper
from src.analyzers.str_revenue import AirROIAnalyzer
from src.analyzers.ltr_revenue import LTRAnalyzer
from src.analyzers.capital_growth import CapitalGrowthAnalyzer
from src.analyzers.roi import ROIAnalyzer
from src.filters.property_filter import PropertyFilter

_runs: dict[str, dict] = {}


def start_run(criteria: UserCriteria) -> str:
    run_id = str(uuid.uuid4())[:8]
    _runs[run_id] = {
        "status": "running",
        "location": criteria.location,
        "criteria": {
            "budget_eur": criteria.budget_eur,
            "min_net_yield_pct": criteria.min_net_yield_pct,
            "min_capital_growth_pct": criteria.min_capital_growth_pct,
            "property_type": criteria.property_type,
            "min_size_m2": criteria.min_size_m2,
        },
        "started_at": datetime.now().isoformat(),
    }
    return run_id


def run_pipeline(run_id: str, criteria: UserCriteria) -> None:
    """Blocking — must run in thread pool, not event loop."""
    try:
        out = Path("outputs/data")
        out.mkdir(parents=True, exist_ok=True)

        listings = IdealistaScraper().scrape(criteria)
        _save(out / f"{run_id}_listings.json", listings)

        with ThreadPoolExecutor(max_workers=3) as pool:
            str_future = pool.submit(AirROIAnalyzer().analyze_batch, listings)
            ltr_future = pool.submit(LTRAnalyzer().analyze, criteria)
            growth_future = pool.submit(CapitalGrowthAnalyzer().analyze, criteria.location)
            str_data = str_future.result()
            ltr_data = ltr_future.result()
            growth_data = growth_future.result()

        _save(out / f"{run_id}_str.json", str_data)
        _save(out / f"{run_id}_ltr.json", [ltr_data])
        _save(out / f"{run_id}_capital_growth.json", [growth_data])

        capital_growth_pct = growth_data.get("yoy_appreciation_pct")
        roi_data = ROIAnalyzer().compute_all(listings, str_data, ltr_data, criteria, capital_growth_pct)
        _save(out / f"{run_id}_roi.json", roi_data)

        filtered = PropertyFilter().filter(listings, roi_data, criteria)
        _save(out / f"{run_id}_filtered.json", filtered)

        _runs[run_id].update({
            "status": "completed",
            "generated_at": datetime.now().isoformat(),
            "total_scraped": len(listings),
            "total_passing": len(filtered),
            "properties": filtered,
            "market": {
                "yoy_appreciation_pct": capital_growth_pct,
                "ccaa": growth_data.get("ccaa"),
                "data_year": growth_data.get("data_year"),
                "vft_risk": None,
                "ltr_avg_rent_eur": ltr_data.get("avg_monthly_rent_eur"),
                "ltr_comparables": ltr_data.get("comparables_count"),
            },
        })
    except Exception as exc:
        _runs[run_id].update({"status": "failed", "error": str(exc)})


def get_run(run_id: str) -> dict | None:
    return _runs.get(run_id)


def update_market(run_id: str, market_data: dict) -> bool:
    if run_id not in _runs:
        return False
    _runs[run_id]["market"] = {**(_runs[run_id].get("market") or {}), **market_data}
    return True


def _save(path: Path, data: list[dict] | dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
