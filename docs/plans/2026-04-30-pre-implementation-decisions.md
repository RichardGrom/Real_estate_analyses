# Pre-Implementation Design Decisions

**Date:** 2026-04-30
**Context:** Resolving open questions before coding starts on the multi-agent real estate advisor.

---

## Decision 1: STR + LTR both in basic pipeline

**Problem:** `roi.py` referenced `OPERATING_COST_PCT` which doesn't exist. Pipeline only fetched STR data.

**Decision:** Option B — add LTR fetching (Apify Idealista `operation: rent`) directly to the basic pipeline, parallel with AirROI. ROI calculator computes both and returns `preferred_rental_type`.

**Impact:**
- `Config` uses `STR_OPEX_PCT = 0.25` and `LTR_OPEX_PCT = 0.15` separately
- `ROIAnalyzer.compute_property` accepts `str_est` and `ltr_data` as separate inputs
- React UI shows STR yield and LTR yield as separate columns from day one

---

## Decision 2: VFT filtering approach

**Problem:** Plan required VFT license zone filter but no implementation existed.

**Decision:** Option B — `vft_risk: "low" | "medium" | "high"` label per location, not a hard filter.

**Rationale:** VFT rules vary by neighbourhood — a hard filter would require a paid legal database. A risk label is honest and actionable for investors.

---

## Decision 3: VFT data source

**Decision:** Exa.ai (web search) + Playwright (municipal website scraping), handled by `capital-growth-analyst` agent.

**Scope:** VFT risk is agent-only (CLI mode). Basic pipeline returns `vft_risk: null`, agents enrich via `PUT /api/analysis/{run_id}/market`.

---

## Decision 4: Capital growth in React UI

**Problem:** `roi.py` accepted `capital_growth_pct` but basic pipeline never fetched it.

**Decision:** Option B — call INE REST API directly in the pipeline (no auth required):
```
GET https://servicios.ine.es/wstempus/js/es/DATOS_TABLA/49300?tip=AM
```

Filter by CCAA matching the requested location, extract latest YoY appreciation rate.

**Impact:** React UI shows complete BUY/WATCH/SKIP verdict (yield + growth) without needing agents.

---

## Decision 5: PropertyTable columns

**Decision:** Both STR and LTR yield as separate columns.

| Column | Source |
|--------|--------|
| Address | Idealista |
| Price (€) | Idealista |
| Size (m²) | Idealista |
| STR Net Yield (%) | AirROI + ROIAnalyzer |
| LTR Net Yield (%) | Idealista rental + ROIAnalyzer |
| Capital Growth (%/yr) | INE |
| Score (0–10) | ROIAnalyzer |
| Verdict | ROIAnalyzer (BUY/WATCH/SKIP) |

---

## Decision 6: EXA_API_KEY in Config

**Decision:** Add to `Config.__init__`:
```python
self.exa_api_key: str = self._require("EXA_API_KEY")
```
Key already present in `.env`.

---

## Decision 7: AirROI API corrections

**Confirmed:** API is live at `https://api.airroi.com/calculator/estimate`.

**Fixes required:**

1. `_build_params` must include `baths` (required by API):
```python
"baths": max(1, bedrooms - 1)
```

2. `_parse_response` must use `revenue` field directly (API returns it, no need to calculate):
```python
revenue = data.get("revenue") or 0  # not occupancy * adr * 365
```

3. API also returns `monthly_revenue_distributions` (12 monthly coefficients) — store for seasonality display.

4. Tests must be updated to match real API response structure.
