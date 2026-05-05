import json
import logging
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from src.scrapers.link_scraper import LinkScraper

logger = logging.getLogger(__name__)
from src.analyzers.str_revenue import AirROIAnalyzer
from src.analyzers.ltr_revenue import LTRAnalyzer
from src.analyzers.capital_growth import CapitalGrowthAnalyzer
from src.analyzers.roi import ROIAnalyzer

_runs: dict[str, dict] = {}


def start_run(url: str) -> str:
    run_id = str(uuid.uuid4())[:8]
    _runs[run_id] = {
        "status": "running",
        "url": url,
        "started_at": datetime.now().isoformat(),
    }
    return run_id


def run_pipeline(run_id: str, url: str) -> None:
    """Blocking — must run in thread pool, not event loop."""
    try:
        out = Path(__file__).parent.parent.parent / "outputs" / "data"
        out.mkdir(parents=True, exist_ok=True)

        listing = LinkScraper().scrape(url)
        _save(out / f"{run_id}_listing.json", listing)

        location = _extract_city(listing.get("address") or "")

        with ThreadPoolExecutor(max_workers=3) as pool:
            str_future = pool.submit(AirROIAnalyzer().analyze_batch, [listing])
            ltr_future = pool.submit(LTRAnalyzer().analyze, location, listing.get("size_m2", 80))
            growth_future = pool.submit(CapitalGrowthAnalyzer().analyze, location)
            str_data = str_future.result()
            ltr_data = ltr_future.result()
            growth_data = growth_future.result()

        str_est = str_data[0] if str_data else {}
        capital_growth_pct = growth_data.get("yoy_appreciation_pct")
        roi = ROIAnalyzer().compute_property(listing, str_est, ltr_data, capital_growth_pct)

        property_result = {**listing, **roi}

        _runs[run_id].update({
            "status": "completed",
            "generated_at": datetime.now().isoformat(),
            "property": property_result,
            "market": {
                "yoy_appreciation_pct": capital_growth_pct,
                "ccaa": growth_data.get("ccaa"),
                "data_year": growth_data.get("data_year"),
                "ltr_avg_rent_eur": ltr_data.get("avg_monthly_rent_eur"),
                "ltr_comparables": ltr_data.get("comparables_count"),
            },
        })
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Pipeline failed: %s\n%s", exc, tb)
        _runs[run_id].update({"status": "failed", "error": str(exc), "traceback": tb})


def get_run(run_id: str) -> dict | None:
    return _runs.get(run_id)


def _extract_city(address: str) -> str:
    """Extract city from address. 4+ parts: skip province (use [-2]). 3 parts: city is last."""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) >= 4:
        return parts[-2]
    return parts[-1] if parts else address


def _save(path: Path, data: dict | list) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
