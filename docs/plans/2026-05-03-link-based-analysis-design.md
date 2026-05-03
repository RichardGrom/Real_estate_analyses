# Link-Based Property Analysis — Design

**Date:** 2026-05-03
**Replaces:** Search-based pipeline (location + budget parameters)

## Goal

Replace the current search-based flow with a link-based flow: user provides a URL to a specific property listing, the system extracts structured property data from that page, and runs the full investment analysis (STR yield, LTR yield, capital growth, verdict).

## Spike Test First

Before committing to one extraction approach, run a comparison script `scripts/compare_approaches.py` on a real URL (`https://www.idealista.com/inmueble/111009537/`) to evaluate all 3 candidates.

## Extraction Approaches Under Test

### Approach A — Exa.ai getContents + Claude
1. `exa.get_contents(url)` returns clean text/markdown of the page
2. Claude API extracts structured JSON from the text
3. Works on any website

### Approach B — Apify startUrls
1. Existing `igolaizola~idealista-scraper` actor called with `{"startUrls": [{"url": "..."}]}`
2. Wait for run (~60–120s), fetch first dataset item
3. Already returns structured JSON — no Claude extraction needed
4. Idealista only

### Approach C — Playwright + Claude
1. Headless Chrome opens the URL, extracts `document.body.innerText`
2. Claude API extracts structured JSON (same prompt as Approach A)
3. Works on any website, requires local Playwright install

## Fields to Extract

| Field | Required for |
|---|---|
| `price_eur` | ROI calculation |
| `size_m2` | Filtering, LTR rent/m² |
| `rooms` | AirROI params |
| `bathrooms` | AirROI params |
| `address` | Display |
| `lat` | AirROI API (STR revenue) |
| `lng` | AirROI API (STR revenue) |
| `has_terrace` | Display |
| `has_parking` | Display |
| `floor` | Display |
| `description` | Display |

## Comparison Output Format

```
APPROACH A (Exa + Claude)    — Xs    ~$0.00X
  price_eur:    ✓/✗
  size_m2:      ✓/✗
  lat/lng:      ✓/✗
  completeness: X/11 fields

APPROACH B (Apify startUrls) — Xs    ~$0.00X
  ...

APPROACH C (Playwright)      — Xs    $0
  ...
```

## Decision Criteria

1. **lat/lng present** — hard requirement (AirROI needs it)
2. **Completeness** — how many of 11 fields extracted correctly
3. **Speed** — time to result
4. **Cost** — API cost per analysis
5. **Generality** — works only on Idealista, or any website

## Architecture After Spike

The winner replaces `IdealistaScraper.scrape()`. Everything downstream (AirROI, LTR, INE, ROI calculator, dashboard) stays unchanged. The new input model changes from `UserCriteria` (location + budget) to a `PropertyUrl` (single URL string).

The frontend form changes from multi-parameter search to a single URL input field.
